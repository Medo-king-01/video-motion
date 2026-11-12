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
import unified_project_edit as edit  # noqa: E402
import unified_project_store as store  # noqa: E402
from unified_project_history import History  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402

EDITOR_DIR = Path(__file__).resolve().parents[1] / "editor"


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


def _caption(project, text_id, **fields):
    """Edit or add a text block; a caption is data, so changing it needs no re-render of the rest."""
    project = json.loads(json.dumps(project))
    texts = project.setdefault("texts", [])
    for text in texts:
        if text["id"] == text_id:
            text.update({key: value for key, value in fields.items() if value is not None})
            return project
    raise ValueError(f"unknown text {text_id!r}")


def perform(session: Session, payload: dict):
    op = payload.get("op")
    if op == "split":
        return session.apply(edit.split_clip, payload["clipId"], int(payload["at"]), payload["newId"])
    if op == "trim":
        return session.apply(edit.trim_clip, payload["clipId"], int(payload["start"]), int(payload["end"]))
    if op == "move":
        return session.apply(edit.move_clip, payload["clipId"], payload["trackId"], int(payload["start"]))
    if op == "ripple":
        return session.apply(edit.ripple_delete, int(payload["start"]), int(payload["end"]),
                             payload["trackIds"])
    if op == "caption":
        return session.apply(_caption, payload["textId"], value=payload.get("value"),
                             size=payload.get("size"), color=payload.get("color"),
                             align=payload.get("align"))
    if op == "undo":
        return session.undo()
    if op == "redo":
        return session.redo()
    raise ValueError(f"unknown op {op!r}")


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
                payload = self._body()
            except ValueError as exc:
                return self._json({"error": f"unreadable body: {exc}"}, HTTPStatus.BAD_REQUEST)
            try:
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
