#!/usr/bin/env python3
"""A local, dependency-free editor server for a unified project.

This is the first visible layer over the core that already existed: the same `split_clip`,
`trim_clip`, `move_clip`, `ripple_delete`, `History`, `store` and `render_frame` the CLI uses,
reachable through a small JSON API and a single HTML page. It binds to loopback by default because
it has no authentication; pass `--host 0.0.0.0` only when a preview proxy needs it.

Endpoints (all JSON unless stated):
  GET  /                     the editor page
  GET  /api/project          project + revision + autosave state + history flags
  POST /api/op               {"op": "split"|"trim"|"move"|"ripple"|"undo"|"redo"|"caption", ...}
  POST /api/save             write the project (revision-checked) and drop the autosave
  GET  /api/frame?index=N    one preview frame as PNG
  GET  /api/capabilities     engine P preflight for the current project
  POST /api/export           encode MP4 (engine P frames + measured WAV when audio exists)
  GET  /api/recover          autosave candidate, if any
  POST /api/recover          {"action": "apply"|"discard"}

Exit codes: 0 stopped cleanly, 2 bad arguments/project.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))

import adapter_p  # noqa: E402
import editor_ops as ops  # noqa: E402
from unified_project_author import set_track_enabled  # noqa: E402
import unified_project_edit as edit  # noqa: E402
import unified_project_store as store  # noqa: E402
from unified_project_history import History  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402

EDITOR_DIR = Path(__file__).resolve().parents[1] / "editor"
MAX_UPLOAD = 64 * 1024 * 1024
MEDIA_DIR = "media"


class Session:
    """One open project, its undo history and its autosave."""

    def __init__(self, path: Path):
        self.path = Path(path)
        project, revision = store.load(self.path)
        self.history = History(project)
        self.revision = revision
        self.lock = threading.Lock()

    @property
    def project(self):
        return self.history.project

    def snapshot(self):
        candidate = store.recover(self.path)
        return {
            "project": self.project,
            "revision": self.revision,
            "undo": self.history.can_undo,
            "redo": self.history.can_redo,
            "autosave": None if candidate is None else {
                "savedAt": candidate["savedAt"], "stale": candidate["stale"]},
        }

    def apply(self, operation, *args, **kwargs):
        with self.lock:
            result = self.history.apply(operation, *args, **kwargs)
            store.autosave(self.path, result, base_revision=self.revision)
            return result

    def undo(self):
        with self.lock:
            result = self.history.undo()
            store.autosave(self.path, result, base_revision=self.revision)
            return result

    def redo(self):
        with self.lock:
            result = self.history.redo()
            store.autosave(self.path, result, base_revision=self.revision)
            return result

    def save(self):
        with self.lock:
            revision = store.save(self.path, self.project, expected_revision=self.revision)
            self.revision = revision
            store.discard_autosave(self.path)
            return revision


def _speed(payload):
    if payload.get("speedNum") is None or payload.get("speedDen") is None:
        return None
    return {"num": int(payload["speedNum"]), "den": int(payload["speedDen"])}


def perform(session: Session, payload: dict):
    """Dispatch one editor operation onto the pure core; unknown ops are a diagnosis."""
    op = payload.get("op")
    table = {
        "split": lambda: session.apply(edit.split_clip, payload["clipId"], int(payload["at"]), payload["newId"]),
        "trim": lambda: session.apply(edit.trim_clip, payload["clipId"], int(payload["start"]), int(payload["end"])),
        "move": lambda: session.apply(edit.move_clip, payload["clipId"], payload["trackId"], int(payload["start"])),
        "ripple": lambda: session.apply(edit.ripple_delete, int(payload["start"]), int(payload["end"]),
                                        payload["trackIds"]),
        "update_clip": lambda: session.apply(ops.update_clip, payload["clipId"],
                                             start=payload.get("start"), duration=payload.get("duration"),
                                             source_in=payload.get("sourceIn"), speed=_speed(payload)),
        "caption": lambda: session.apply(ops.set_text, payload["textId"], value=payload.get("value"),
                                         size=payload.get("size"), color=payload.get("color"),
                                         align=payload.get("align"), wrap=payload.get("wrap"),
                                         animation=payload.get("animation")),
        "text": lambda: session.apply(ops.set_text, payload["textId"],
                                      **{key: payload[key] for key in ("value", "size", "color", "align",
                                                                       "wrap", "animation", "font")
                                         if key in payload}),
        "add_text": lambda: session.apply(ops.add_text, payload["textId"], payload["value"],
                                          **{key: payload[key] for key in ("font", "size", "color", "align",
                                                                           "direction", "wrap", "animation")
                                             if key in payload}),
        "add_text_clip": lambda: session.apply(ops.add_text_clip, payload["trackId"], payload["clipId"],
                                               payload["textId"], int(payload["start"]), int(payload["duration"])),
        "add_track": lambda: session.apply(ops.add_track, payload["trackId"], payload["kind"],
                                           position=payload.get("position")),
        "remove_track": lambda: session.apply(ops.remove_track, payload["trackId"]),
        "enabled": lambda: session.apply(set_track_enabled, payload["trackId"], bool(payload["enabled"])),
        "add_clip": lambda: session.apply(ops.add_clip, payload["trackId"], payload["clipId"],
                                          payload["assetId"], int(payload["start"]), int(payload["duration"]),
                                          source_in=int(payload.get("sourceIn", 0))),
        "delete_clip": lambda: session.apply(ops.delete_clip, payload["clipId"]),
        "project": lambda: session.apply(ops.set_project, name=payload.get("name"),
                                         duration=payload.get("duration"), seed=payload.get("seed")),
        "add_effect": lambda: session.apply(ops.add_effect, payload["clipId"], payload["effect"]),
        "set_effect": lambda: session.apply(ops.set_effect_value, payload["clipId"], payload["effectId"],
                                            int(payload["value"])),
        "remove_effect": lambda: session.apply(ops.remove_effect, payload["clipId"], payload["effectId"]),
        "add_keyframe": lambda: session.apply(ops.add_keyframe, payload["clipId"], payload["effectId"],
                                              int(payload["tick"]), int(payload["value"]),
                                              payload.get("interpolation", "linear")),
        "remove_keyframe": lambda: session.apply(ops.remove_keyframe, payload["clipId"], payload["effectId"],
                                                 int(payload["tick"])),
        "undo": session.undo,
        "redo": session.redo,
    }
    if op not in table:
        raise ValueError(f"unknown op {op!r}")
    return table[op]()


def _safe_name(name: str) -> str:
    cleaned = "".join(char for char in Path(name).name if char.isalnum() or char in "-_. ")
    cleaned = cleaned.strip().replace(" ", "-")
    if not cleaned or cleaned.startswith("."):
        raise ValueError("a media file needs a usable name")
    return cleaned


def import_media(session: Session, *, filename: str, payload: bytes) -> dict:
    """Copy bytes into the project's media folder, hash them, and attach them as an asset."""
    import hashlib

    if not payload:
        raise ValueError("empty upload")
    if len(payload) > MAX_UPLOAD:
        raise ValueError(f"upload larger than {MAX_UPLOAD} bytes")
    name = _safe_name(filename)
    folder = session.path.parent / MEDIA_DIR
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / name
    digest = hashlib.sha256(payload).hexdigest()
    if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
        stem, suffix = target.stem, target.suffix
        counter = 2
        while target.exists():
            target = folder / f"{stem}-{counter}{suffix}"
            counter += 1
        name = target.name
    target.write_bytes(payload)
    kind = _kind_of(name, payload)
    asset = {"id": _asset_id(session.project, name), "kind": kind,
             "uri": f"{MEDIA_DIR}/{name}", "sha256": digest}
    if kind != "image":
        asset["duration"] = int(session.project["duration"])
    session.apply(ops.add_asset, asset)
    return asset


def _kind_of(name: str, payload: bytes) -> str:
    suffix = Path(name).suffix.lower()
    if suffix in (".ppm", ".png", ".jpg", ".jpeg"):
        return "image"
    if suffix in (".mp4", ".mov", ".mkv", ".webm"):
        return "video"
    if suffix in (".wav", ".mp3", ".flac", ".m4a", ".aiff"):
        return "audio"
    if payload[4:8] == b"ftyp":
        return "video"
    raise ValueError(f"unsupported media type {suffix or 'unknown'}")


def _asset_id(project, name: str) -> str:
    stem = "".join(char if char.isalnum() else "-" for char in Path(name).stem).strip("-").lower() or "media"
    candidate, counter = stem, 2
    taken = {asset["id"] for asset in project["assets"]}
    while candidate in taken:
        candidate = f"{stem}-{counter}"
        counter += 1
    return candidate


def thumbnail(root: Path, asset: dict, height: int = 180) -> bytes:
    """A small PNG for the media bin: decoded through the same verified reader as the preview."""
    import hashlib
    import io as _io

    from PIL import Image  # noqa: PLC0415

    from unified_project_media import _local_file
    from unified_reference_preview import _read_image, _read_video

    payload = _local_file(Path(root), asset["uri"]).read_bytes()
    if hashlib.sha256(payload).hexdigest() != asset["sha256"]:
        raise ValueError("media SHA-256 does not match the asset")
    if asset["kind"] == "image" and payload.startswith(b"P6"):
        header = payload.split(b"\n", 3)
        width, tall = (int(value) for value in header[1].split())
        pixels = _read_image(Path(root), asset, width, tall, "$.asset")
        image = Image.frombytes("RGBA", (width, tall), pixels)
    elif asset["kind"] == "image":
        image = Image.open(_io.BytesIO(payload)).convert("RGBA")
    elif asset["kind"] == "video":
        width, tall = 320, 180
        pixels = _read_video(Path(root), asset, width, tall, 0, "$.asset")
        image = Image.frombytes("RGBA", (width, tall), pixels)
    else:
        image = Image.new("RGBA", (160, 90), (30, 30, 33, 255))
    ratio = height / max(1, image.height)
    image = image.resize((max(1, int(image.width * ratio)), height))
    buffer = _io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def make_handler(session: Session, *, exporter):
    class Handler(BaseHTTPRequestHandler):
        server_version = "medo-editor/1.0"

        def log_message(self, fmt, *args):  # keep the console readable in a live preview
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

        def _json(self, payload, status=HTTPStatus.OK):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _bytes(self, payload, content_type):
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)

        def _body(self):
            length = int(self.headers.get("Content-Length") or 0)
            if not length:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def do_GET(self):  # noqa: N802 - http.server API
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                page = (EDITOR_DIR / "index.html").read_bytes()
                return self._bytes(page, "text/html; charset=utf-8")
            if url.path == "/api/project":
                return self._json(session.snapshot())
            if url.path == "/api/frame":
                query = parse_qs(url.query)
                index = int(query.get("index", ["0"])[0])
                try:
                    frame = render_frame(session.project, session.path.parent, index)
                except PreviewError as exc:
                    return self._json({"error": f"{exc.code} {exc.path}: {exc.message}"},
                                      HTTPStatus.BAD_REQUEST)
                try:
                    from PIL import Image  # noqa: PLC0415
                except ImportError:
                    return self._json({"error": "Pillow is required for PNG previews"}, HTTPStatus.SERVER_ERROR)
                image = Image.frombytes("RGBA", (frame["width"], frame["height"]), frame["pixels"])
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG")
                return self._bytes(buffer.getvalue(), "image/png")
            if url.path == "/api/media":
                query = parse_qs(url.query)
                asset_id = query.get("asset", [None])[0]
                if asset_id is None:
                    return self._json({"assets": session.project["assets"]})
                asset = next((asset for asset in session.project["assets"] if asset["id"] == asset_id), None)
                if asset is None:
                    return self._json({"error": f"unknown asset {asset_id!r}"}, HTTPStatus.NOT_FOUND)
                try:
                    return self._bytes(thumbnail(session.path.parent, asset), "image/png")
                except (ValueError, OSError) as exc:
                    return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            if url.path == "/api/capabilities":
                adapter = adapter_p.PAdapter()
                graph = adapter.compile(session.project)
                return self._json({"capabilities": adapter.capabilities(), "preflight": adapter.preflight(graph)})
            if url.path == "/api/recover":
                candidate = store.recover(session.path)
                if candidate is None:
                    return self._json({"candidate": None})
                return self._json({"candidate": {k: v for k, v in candidate.items() if k != "project"}})
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

        def do_POST(self):  # noqa: N802 - http.server API
            url = urlparse(self.path)
            try:
                if url.path == "/api/media/upload":
                    # raw bytes, not JSON: read them once, here, before anything parses a body
                    name = self.headers.get("X-Filename") or "upload.bin"
                    length = int(self.headers.get("Content-Length") or 0)
                    if length <= 0:
                        return self._json({"error": "empty upload"}, HTTPStatus.BAD_REQUEST)
                    payload = self.rfile.read(length)
                    asset = import_media(session, filename=name, payload=payload)
                    return self._json({"asset": asset, "assets": session.project["assets"]})
                try:
                    payload = self._body()
                except ValueError as exc:
                    return self._json({"error": f"unreadable body: {exc}"}, HTTPStatus.BAD_REQUEST)
                if url.path == "/api/op":
                    project = perform(session, payload)
                    return self._json({"project": project, "undo": session.history.can_undo,
                                       "redo": session.history.can_redo})
                if url.path == "/api/save":
                    revision = session.save()
                    return self._json({"revision": revision, "saved": True})
                if url.path == "/api/export":
                    result = exporter(session, payload)
                    return self._json(result)
                if url.path == "/api/recover":
                    action = payload.get("action")
                    candidate = store.recover(session.path)
                    if candidate is None:
                        return self._json({"error": "no autosave"}, HTTPStatus.BAD_REQUEST)
                    if action == "discard":
                        store.discard_autosave(session.path)
                        return self._json({"discarded": True})
                    if action != "apply":
                        return self._json({"error": "action must be apply or discard"}, HTTPStatus.BAD_REQUEST)
                    if candidate["stale"]:
                        return self._json({"error": "autosave belongs to an older revision"}, HTTPStatus.CONFLICT)
                    session.history = History(candidate["project"])
                    return self._json({"applied": True, "project": session.project})
            except (ValueError, KeyError) as exc:
                return self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # noqa: BLE001 - the page must show the reason, not die
                return self._json({"error": f"{type(exc).__name__}: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    return Handler


def export_mp4(session: Session, payload: dict) -> dict:
    """Encode the current project; engine P draws the frames, video_export publishes them."""
    import video_export  # noqa: PLC0415

    audio = payload.get("audio")
    out = Path(payload.get("out") or (session.path.parent / f"{session.path.stem}.mp4"))
    result = video_export.build(session.project, session.path.parent, out,
                                audio=Path(audio) if audio else None)
    return {"file": out.name, "bytes": result["file"]["bytes"], "frames": result["video"]["frames"],
            "sha256": result["file"]["sha256"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8777)
    args = parser.parse_args(argv)
    try:
        session = Session(args.project)
    except (OSError, ValueError) as exc:
        print(f"cannot open {args.project}: {exc}", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer((args.host, args.port), make_handler(session, exporter=export_mp4))
    host, port = server.server_address[:2]
    print(f"editor on http://{host}:{port}  ({args.project})", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
