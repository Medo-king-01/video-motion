#!/usr/bin/env python3
"""The first real render backend: engine P executes the unified graph, offscreen.

`docs/editor-architecture.md` §7 froze the interface; this module is one honest
implementation of it. What it does and does not do is declared, not implied:

* it **renders**: still-image tracks, crossfades, Arabic text overlays and opacity from the
  same `render_frame` the preview uses, so an exported frame is the previewed frame;
* it **refuses** what it cannot draw — clip speed, video/audio decoding, keyframed
  opacity — with an `R` diagnostic naming the clip, before a single frame is written;
* it publishes **atomically**: frames go to a temporary directory and are renamed only
  when the whole range finished, and cancelling leaves no half artifact behind.

The capability manifest (`medo-motion/schema/backend-capabilities.json`) must agree with
`capabilities()`; `tests/test_adapter_p.py` and `tools/render_backend.py --check` compare them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import backend_capabilities as capabilities  # noqa: E402
import unified_project_check  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402
from unified_render_graph import compile_project, graph_digest  # noqa: E402

BACKEND = "P"
VERSION = "1.0.0"


class AdapterError(RuntimeError):
    """A diagnosed refusal to render."""

    def __init__(self, code, path, message):
        self.code, self.path, self.message = code, path, message
        super().__init__(f"{code} {path}: {message}")


class Cancelled(AdapterError):
    def __init__(self, frame):
        super().__init__("R09", "$", f"cancelled at frame {frame}")


def _unsupported(project):
    """Diagnostics for what this backend must not pretend to draw."""
    problems = []
    for ti, track in enumerate(project["tracks"]):
        if not track["enabled"]:
            continue
        path = f"$.tracks[{ti}]"
        if track["kind"] == "audio":
            if track["clips"]:
                problems.append({"code": "R02", "path": path, "message":
                                 "audio decoding is not implemented; export the mix with audio_export"})
            continue
        if track["kind"] not in ("video", "text"):
            problems.append({"code": "R02", "path": path, "message": f"{track['kind']} tracks are not drawn"})
            continue
        for ci, clip in enumerate(track["clips"]):
            clip_path = f"{path}.clips[{ci}]"
            speed = clip.get("speed")
            if speed and (speed["num"], speed["den"]) != (1, 1):
                problems.append({"code": "R03", "path": clip_path + ".speed",
                                 "message": "clip speed is not implemented"})
            if clip["keyframes"]:
                problems.append({"code": "R04", "path": clip_path + ".keyframes",
                                 "message": "keyframed effects are not implemented"})
            if track["kind"] == "video":
                asset_id = clip.get("assetId")
                asset = next((a for a in project["assets"] if a["id"] == asset_id), None)
                if asset is not None and asset["kind"] != "image":
                    problems.append({"code": "R05", "path": clip_path + ".assetId",
                                     "message": f"{asset['kind']} decoding is not implemented; stills only"})
                for ei, effect in enumerate(clip["effects"]):
                    if effect["type"] != "opacity":
                        problems.append({"code": "R06", "path": f"{clip_path}.effects[{ei}]",
                                         "message": "only opacity is implemented on video"})
        for tk, transition in enumerate(track.get("transitions") or []):
            if transition["kind"] != "crossfade":
                problems.append({"code": "R07", "path": f"{path}.transitions[{tk}]",
                                 "message": f"{transition['kind']} is not implemented; crossfade only"})
    return problems


class PAdapter:
    """Engine P behind the frozen render-backend contract."""

    backend = BACKEND
    version = VERSION

    def __init__(self, manifest=None):
        self._entry = (manifest or capabilities.load())["backends"][BACKEND]
        self._cancelled = threading.Event()

    # -- contract ---------------------------------------------------------
    def capabilities(self):
        return {"backend": self.backend, "backendVersion": VERSION, "features": self._entry["features"]}

    def compile(self, project):
        graph = compile_project(project)
        graph["executable"] = True
        graph["backend"] = {"name": BACKEND, "version": VERSION}
        graph["graphSha256"] = graph_digest(graph)
        return graph

    def preflight(self, graph):
        project = graph["project"]
        problems = _unsupported(project)
        return {
            "backend": self.backend, "graphVersion": graph.get("graphVersion"),
            "status": "unsupported" if problems else "supported",
            "diagnostics": problems,
        }

    def render(self, graph, frames, out, options=None):
        options = options or {}
        project = graph["project"]
        problems = _unsupported(project)
        if problems:
            first = problems[0]
            raise AdapterError(first["code"], first["path"],
                               "; ".join(problem["message"] for problem in problems))
        start, stop = frames
        total = graph["clock"]["frameCount"]
        if not 0 <= start <= stop <= total:
            raise AdapterError("R08", "$", f"frame range {start}..{stop} outside 0..{total}")
        root = Path(options.get("root") or ".")
        progress = options.get("progress")
        out = Path(out)
        out.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(tempfile.mkdtemp(prefix=".p-render-", dir=out.parent))
        written = []
        try:
            for index in range(start, stop):
                if self._cancelled.is_set():
                    raise Cancelled(index)
                try:
                    frame = render_frame(project, root, index)
                except PreviewError as exc:
                    raise AdapterError(exc.code, exc.path, exc.message) from exc
                payload = bytes(frame["pixels"])
                name = f"frame-{index:05d}.rgba"
                (staging / name).write_bytes(payload)
                written.append({"frame": index, "file": name, "sha256": hashlib.sha256(payload).hexdigest()})
                if callable(progress):
                    progress(index - start + 1, stop - start)
            manifest = {
                "backend": BACKEND, "backendVersion": VERSION,
                "graphVersion": graph.get("graphVersion"), "graphSha256": graph.get("graphSha256"),
                "frames": [start, stop], "width": project["profile"]["width"],
                "height": project["profile"]["height"], "format": "RGBA8",
                "written": written,
            }
            (staging / "render.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                                 encoding="utf-8")
            if out.exists() and any(out.iterdir()):
                raise AdapterError("R10", str(out), "refusing to overwrite a non-empty output folder")
            if out.exists():
                out.rmdir()
            shutil.move(str(staging), str(out))
            staging = None
            return {"artifact": str(out), "log": [f"{len(written)} frames"], "progress": len(written),
                    "frames": [start, stop], "manifest": manifest}
        finally:
            if staging is not None:
                shutil.rmtree(staging, ignore_errors=True)
            self._cancelled.clear()

    def cancel(self):
        self._cancelled.set()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--root", type=Path, default=None, help="folder that asset URIs are relative to")
    parser.add_argument("--out", type=Path, help="output folder for the rendered frames")
    parser.add_argument("--frames", default=None, help="half-open range, e.g. 0:30")
    parser.add_argument("--preflight", action="store_true", help="report readiness and stop")
    parser.add_argument("--capabilities", action="store_true", help="print the declared capabilities")
    args = parser.parse_args(argv)
    adapter = PAdapter()
    if args.capabilities:
        print(json.dumps(adapter.capabilities(), ensure_ascii=False, indent=2))
        return 0
    project = json.loads(args.project.read_text(encoding="utf-8"))
    graph = adapter.compile(project)
    readiness = adapter.preflight(graph)
    if args.preflight or not args.out:
        print(json.dumps(readiness, ensure_ascii=False, indent=2))
        return 0 if readiness["status"] == "supported" else 1
    start, stop = (int(part) for part in (args.frames or f"0:{graph['clock']['frameCount']}").split(":"))
    result = adapter.render(graph, (start, stop), args.out,
                            {"root": args.root or args.project.parent})
    print(json.dumps({k: v for k, v in result.items() if k != "manifest"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
