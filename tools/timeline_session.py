#!/usr/bin/env python3
"""Timeline MVP (B5): open a project, edit it as a replayable command list, save, render, repeat.

The pieces already existed — `unified_project_edit` (split/trim/move/ripple), `unified_project_time`
(snap), `unified_project_history` (undo/redo), `unified_project_store` (revision-checked save) and
`unified_reference_preview` (frame bytes). This module is the session that makes them one workflow and
proves the loop: **open → edit → save → reopen → render the same bytes**.

A command list is data, so an edit session is reviewable and reproducible:

    {"commands": [
      {"op": "trim",  "clip": "c1", "start": 0, "end": 16000},
      {"op": "split", "clip": "c1", "at": 8000, "id": "c1b"},
      {"op": "move",  "clip": "c1b", "track": "v2", "start": 0},
      {"op": "undo"}
    ], "frames": [0, 1]}

CLI: `check`, `status`, `frame`, `script`, `export` (EDL). Exit codes: 0 ok · 1 invalid command/project ·
2 unreadable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_edit import move_clip, ripple_delete, split_clip, trim_clip  # noqa: E402
from unified_project_history import History  # noqa: E402
from unified_project_store import ConflictError, load, save  # noqa: E402
from unified_project_time import frame_ticks, snap  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402
from unified_render_graph import compile_project, graph_digest  # noqa: E402
import edl_export  # noqa: E402

COMMANDS = {
    "trim": (trim_clip, ("clip", "start", "end")),
    "split": (split_clip, ("clip", "at", "id")),
    "move": (move_clip, ("clip", "track", "start")),
    "ripple": (ripple_delete, ("start", "end", "tracks")),
}
QUERY_COMMANDS = {"snap": ("tick", "tolerance")}


class SessionError(ValueError):
    """A refused command or save, with a stable code the CLI can print."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class Session:
    """One editing session over one project file. Nothing here touches a renderer until `render()`."""

    def __init__(self, project: dict, *, revision: str | None = None, root: Path | None = None,
                 limit: int = 100):
        self._history = History(project, limit=limit)
        self._revision = revision
        self._path: Path | None = None
        self.root = Path(root) if root is not None else Path(".")
        self.log: list[dict] = []

    @classmethod
    def open(cls, path: Path, *, limit: int = 100) -> "Session":
        path = Path(path)
        project, revision = load(path)
        session = cls(project, revision=revision, root=path.parent, limit=limit)
        session.bind(path)
        return session

    @property
    def project(self) -> dict:
        return self._history.project

    @property
    def revision(self) -> str | None:
        return self._revision

    @property
    def can_undo(self) -> bool:
        return self._history.can_undo

    @property
    def can_redo(self) -> bool:
        return self._history.can_redo

    # -------------------------------------------------------------- commands
    def apply(self, command: dict) -> dict:
        """Run one command. On failure the project and history are untouched."""
        if not isinstance(command, dict):
            raise SessionError("T01", "a command must be an object")
        op = command.get("op")
        if op in QUERY_COMMANDS:
            return self._query(op, command)
        if op == "undo":
            self._expect(command, ())
            if not self.can_undo:
                raise SessionError("T04", "nothing to undo")
            self._history.undo()
            return self._record(op, command)
        if op == "redo":
            self._expect(command, ())
            if not self.can_redo:
                raise SessionError("T04", "nothing to redo")
            self._history.redo()
            return self._record(op, command)
        if op not in COMMANDS:
            raise SessionError("T01", f"unknown op {op!r}; expected one of {sorted(COMMANDS) + ['undo', 'redo', 'snap']}")
        func, fields = COMMANDS[op]
        self._expect(command, fields)
        try:
            self._history.apply(func, *[command[f] for f in fields])
        except ValueError as exc:
            raise SessionError("T03", f"{op}: {exc}") from exc
        return self._record(op, command)

    def _expect(self, command: dict, fields: tuple[str, ...]) -> None:
        extra = set(command) - set(fields) - {"op"}
        missing = set(fields) - set(command)
        if extra or missing:
            raise SessionError("T02", f"{command.get('op')}: unknown {sorted(extra)} missing {sorted(missing)}")

    def _record(self, op: str, command: dict) -> dict:
        entry = {"op": op, "command": command, "undo": self.can_undo, "redo": self.can_redo}
        self.log.append(entry)
        return entry

    def _query(self, op: str, command: dict) -> dict:
        fields = QUERY_COMMANDS[op]
        self._expect(command, fields)
        try:
            tick, kind, item = snap(self.project, command["tick"], command["tolerance"])
        except ValueError as exc:
            raise SessionError("T03", f"{op}: {exc}") from exc
        entry = {"op": op, "tick": tick, "kind": kind, "id": item, "undo": self.can_undo, "redo": self.can_redo}
        self.log.append({"op": op, "command": command, **{k: entry[k] for k in ("tick", "kind", "id")}})
        return entry

    # -------------------------------------------------------------- persistence
    def save(self, path: Path | None = None, *, autosave: bool = False) -> str:
        """Revision-checked atomic save; returns the new revision."""
        target = Path(path) if path is not None else self._path
        if target is None:
            raise SessionError("T05", "no path to save to")
        same_file = self._path is not None and target.resolve() == self._path.resolve()
        expected = self._revision if same_file else None
        try:
            revision = save(target, self.project, expected_revision=expected)
        except ConflictError as exc:
            raise SessionError("T05", f"save refused: {exc}") from exc
        self._revision = revision
        self._path = target
        if autosave:
            self.log.append({"op": "autosave", "revision": revision})
        return revision

    def bind(self, path: Path) -> None:
        """Remember where this session writes to (used by `open` and tests)."""
        self._path = Path(path)

    # -------------------------------------------------------------- delivery
    def to_edl(self, *, title: str | None = None) -> tuple[str, dict]:
        """The current edit as CMX3600 — the timeline is the single source, the EDL is a view of it."""
        try:
            return edl_export.build_edl(self.project, title=title)
        except edl_export.EdlError as exc:
            raise SessionError("T06", f"EDL refused: {exc}") from exc

    def export_edl(self, path: Path, *, title: str | None = None) -> dict:
        """Write `<path>` plus its `.json` sidecar; returns the manifest."""
        text, manifest = self.to_edl(title=title)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        sidecar = path.with_suffix(path.suffix + ".json")
        sidecar.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return manifest

    # -------------------------------------------------------------- render
    def render(self, frame_index: int, out_path: Path | None = None) -> dict:
        """Render one absolute frame; identity is the pixel hash, not the file format."""
        try:
            frame = render_frame(self.project, self.root, frame_index)
        except PreviewError as exc:
            raise SessionError(exc.code, f"render frame {frame_index}: {exc.message}") from exc
        pixels = frame["pixels"]
        payload = {
            "frame": frame["frameIndex"],
            "tick": frame["tick"],
            "width": frame["width"],
            "height": frame["height"],
            "pixelSha256": _sha(pixels),
            "file": None,
        }
        if out_path is not None:
            from PIL import Image  # noqa: PLC0415

            out_path = Path(out_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            Image.frombytes("RGBA", (frame["width"], frame["height"]), pixels).save(out_path, format="PNG")
            payload["file"] = str(out_path)
            payload["fileSha256"] = _sha(out_path.read_bytes())
        return payload

    # -------------------------------------------------------------- read-only views
    def status(self) -> dict:
        project = self.project
        ticks = frame_ticks(project)
        digest = graph_digest(compile_project(project))
        return {
            "id": project["id"],
            "name": project["name"],
            "duration": project["duration"],
            "frameTicks": ticks,
            "frames": -(-project["duration"] // ticks),
            "tracks": [{"id": t["id"], "kind": t["kind"], "enabled": t["enabled"], "clips": len(t["clips"])}
                       for t in project["tracks"]],
            "revision": self._revision,
            "canUndo": self.can_undo,
            "canRedo": self.can_redo,
            "graphDigest": digest,
        }


# ------------------------------------------------------------------ CLI
def _load_script(path: Path) -> dict:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SessionError("T02", f"cannot read script {path}: {exc}") from exc
    if isinstance(payload, list):
        payload = {"commands": payload, "frames": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("commands"), list):
        raise SessionError("T02", "script needs a commands[] array")
    frames = payload.get("frames", [])
    if not isinstance(frames, list) or any(isinstance(f, bool) or not isinstance(f, int) for f in frames):
        raise SessionError("T02", "script frames[] must be integers")
    return {"commands": payload["commands"], "frames": frames}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Timeline MVP: open, edit, save, render the same bytes.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="validate a project file")
    check.add_argument("project", type=Path)

    status = sub.add_parser("status", help="print the project summary as JSON")
    status.add_argument("project", type=Path)

    frame = sub.add_parser("frame", help="render one frame to PNG")
    frame.add_argument("project", type=Path)
    frame.add_argument("index", type=int)
    frame.add_argument("-o", "--out", type=Path, required=True)

    script = sub.add_parser("script", help="apply a command list, save, then render frames")
    script.add_argument("project", type=Path)
    script.add_argument("script", type=Path)
    script.add_argument("-o", "--out", type=Path, required=True)
    script.add_argument("--out-dir", type=Path, default=None)
    script.add_argument("--autosave", action="store_true")
    script.add_argument("--frames", default=None, help="comma-separated override, e.g. 0,15,30")
    script.add_argument("--edl", type=Path, default=None, help="also write a CMX3600 EDL after saving")

    export = sub.add_parser("export", help="write a CMX3600 EDL (+ sidecar) from a project")
    export.add_argument("project", type=Path)
    export.add_argument("-o", "--out", type=Path, required=True)
    export.add_argument("--title", default=None)

    args = parser.parse_args(argv)

    try:
        session = Session.open(args.project)
    except (OSError, ValueError) as exc:
        print(f"error: cannot open {args.project}: {exc}", file=sys.stderr)
        return 2

    if args.command == "check":
        print(f"Valid project · {session.status()['frames']} frames · "
              f"{sum(t['clips'] for t in session.status()['tracks'])} clips")
        return 0

    if args.command == "status":
        print(json.dumps(session.status(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "frame":
        try:
            result = session.render(args.index, args.out)
        except SessionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, ensure_ascii=False))
        return 0

    if args.command == "export":
        try:
            manifest = session.export_edl(args.out, title=args.title)
        except SessionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {args.out} · {manifest['totals']['events']} events · {manifest['fps']} fps · "
              f"{manifest['totals']['durationTc']} · {args.out.with_suffix(args.out.suffix + '.json')}")
        return 0

    # script
    try:
        script = _load_script(args.script)
    except SessionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    frames = script["frames"]
    if args.frames:
        frames = [int(part) for part in args.frames.split(",") if part.strip()]

    for command in script["commands"]:
        try:
            entry = session.apply(command)
        except SessionError as exc:
            print(f"error: {exc} (nothing written)", file=sys.stderr)
            return 1
        detail = ""
        if entry["op"] == "snap":
            detail = f" → {entry['tick']} ({entry['kind']} {entry['id']})".rstrip()
        print(f"ok {entry['op']}{detail}")
        if args.autosave:
            session.save(args.out, autosave=True)

    try:
        if not args.autosave:
            session.save(args.out)
    except SessionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.edl is not None:
        try:
            manifest = session.export_edl(args.edl)
        except SessionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {args.edl} · {manifest['totals']['events']} events · {manifest['fps']} fps")

    rendered = []
    out_dir = args.out_dir or args.out.with_suffix("")
    for index in frames:
        try:
            rendered.append(session.render(index, out_dir / f"frame-{index:04d}.png"))
        except SessionError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    manifest = {"project": str(args.out), "revision": session.revision,
                "frames": rendered, "log": session.log}
    manifest_path = args.out.with_suffix(".frames.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"saved {args.out} · {len(session.log)} commands · {len(rendered)} frames · {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
