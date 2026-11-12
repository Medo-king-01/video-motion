#!/usr/bin/env python3
"""Frame-sequence delivery (B6د): a project becomes PNG frames plus a verifiable manifest.

No encoder is involved, so this works everywhere: each frame goes through the same reference renderer the
timeline uses, the manifest records the pixel hash and the file hash, and `check` re-verifies the manifest
without re-rendering. Any NLE or encoder can ingest the folder; nothing here pretends to be an MP4.

    python3 tools/sequence_export.py build project.json -o out/frames/
    python3 tools/sequence_export.py build project.json -o out/frames/ --frames 0,15,30
    python3 tools/sequence_export.py check out/frames/sequence.json

Exit codes: 0 ok · 1 project/frame refused (Q-codes) · 2 unreadable file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402
from unified_project_time import frame_ticks  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402

VERSION = 1
MAX_FRAMES = 900
FIELDS = {"index", "tick", "pixelSha256", "file", "fileSha256"}
ROOT_FIELDS = {"version", "source", "profile", "timebase", "frameTicks", "frames", "files", "totals"}


class SequenceError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def project_frames(project: dict) -> int:
    ticks = frame_ticks(project)
    return -(-project["duration"] // ticks)


def build(project: dict, root: Path, out_dir: Path, *, frames: list[int] | None = None,
          max_frames: int = MAX_FRAMES) -> dict:
    """Render the requested frames (default: all) and write them beside a manifest."""
    errors = validate(project)
    if errors:
        raise SequenceError("Q01", "project is invalid: " + "; ".join(errors))
    total = project_frames(project)
    chosen = list(range(total)) if frames is None else list(frames)
    if not chosen:
        raise SequenceError("Q03", "no frames requested")
    if len(chosen) > max_frames:
        raise SequenceError("Q03", f"{len(chosen)} frames exceed the {max_frames}-frame cap")
    if any(isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < total
           for index in chosen):
        raise SequenceError("Q03", f"frame indices must be integers within 0..{total - 1}")
    if len(set(chosen)) != len(chosen):
        raise SequenceError("Q03", "duplicate frame indices")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - Pillow ships with the studio
        raise SequenceError("Q04", "Pillow is required to write PNG frames") from exc

    files = []
    for index in sorted(chosen):
        try:
            frame = render_frame(project, Path(root), index)
        except PreviewError as exc:
            raise SequenceError("Q02", f"frame {index}: {exc.code} {exc.path} {exc.message}") from exc
        name = f"frame-{index:04d}.png"
        path = out_dir / name
        Image.frombytes("RGBA", (frame["width"], frame["height"]), frame["pixels"]).save(path, format="PNG")
        files.append({"index": index, "tick": frame["tick"], "pixelSha256": _sha(frame["pixels"]),
                      "file": name, "fileSha256": _sha(path.read_bytes())})

    manifest = {
        "version": VERSION,
        "source": {"name": project.get("name") or project["id"],
                   "sha256": _sha(json.dumps(project, ensure_ascii=False, sort_keys=True).encode("utf-8"))},
        "profile": {"width": project["profile"]["width"], "height": project["profile"]["height"],
                    "fps": dict(project["profile"]["fps"])},
        "timebase": project["timebase"],
        "frameTicks": frame_ticks(project),
        "frames": total,
        "files": files,
        "totals": {"written": len(files)},
    }
    (out_dir / "sequence.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                           encoding="utf-8")
    return manifest


def validate_manifest(data: dict) -> list[str]:
    """Q05: the manifest must describe files that are still there and still hash the same."""
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return [f"Q01 version: only version {VERSION} is accepted"]
    if set(data) != ROOT_FIELDS:
        return [f"Q01 root: needs exactly {sorted(ROOT_FIELDS)}"]
    files = data.get("files")
    if not isinstance(files, list) or not files:
        return ["Q01 files: non-empty list required"]
    errors: list[str] = []
    if data["totals"].get("written") != len(files):
        errors.append(f"Q05 totals.written: says {data['totals'].get('written')} but {len(files)} files listed")
    seen = set()
    for index, item in enumerate(files):
        where = f"files[{index}]"
        if not isinstance(item, dict) or set(item) != FIELDS:
            errors.append(f"Q01 {where}: needs exactly {sorted(FIELDS)}")
            continue
        if item["index"] in seen:
            errors.append(f"Q05 {where}.index: duplicate {item['index']}")
        seen.add(item["index"])
        if item["index"] >= data["frames"]:
            errors.append(f"Q05 {where}.index: beyond the project's {data['frames']} frames")
        if item["tick"] != item["index"] * data["frameTicks"]:
            errors.append(f"Q05 {where}.tick: {item['tick']} is not {item['index']} × {data['frameTicks']}")
        for key in ("pixelSha256", "fileSha256"):
            if not isinstance(item[key], str) or len(item[key]) != 64:
                errors.append(f"Q05 {where}.{key}: 64 hex characters required")
    return errors


def verify(manifest: dict, folder: Path) -> list[str]:
    """Re-read the PNGs: a missing or edited frame is reported, not silently accepted."""
    errors = validate_manifest(manifest)
    if errors:
        return errors
    for item in manifest["files"]:
        path = Path(folder) / item["file"]
        if not path.is_file():
            errors.append(f"Q05 {item['file']}: missing")
            continue
        if _sha(path.read_bytes()) != item["fileSha256"]:
            errors.append(f"Q05 {item['file']}: bytes no longer match the manifest")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a project to PNG frames with a verified manifest.")
    sub = parser.add_subparsers(dest="command", required=True)

    build_cmd = sub.add_parser("build", help="project.json → frames/ + sequence.json")
    build_cmd.add_argument("project", type=Path)
    build_cmd.add_argument("-o", "--out", type=Path, required=True)
    build_cmd.add_argument("--frames", default=None, help="comma-separated selection, e.g. 0,15,30")
    build_cmd.add_argument("--max", dest="max_frames", type=int, default=MAX_FRAMES)

    check = sub.add_parser("check", help="verify a sequence manifest against the folder")
    check.add_argument("manifest", type=Path)
    check.add_argument("--dir", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
            return 2
        folder = args.dir or args.manifest.parent
        errors = verify(data, folder)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid sequence · {data['totals']['written']} frames · "
              f"{data['profile']['width']}×{data['profile']['height']} · {data['profile']['fps']['num']} fps")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    frames = None
    if args.frames:
        try:
            frames = [int(part) for part in args.frames.split(",") if part.strip()]
        except ValueError:
            print("error: --frames must be comma-separated integers", file=sys.stderr)
            return 2
    try:
        manifest = build(project, args.project.parent, args.out, frames=frames, max_frames=args.max_frames)
    except SequenceError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"wrote {args.out} · {manifest['totals']['written']} frames · "
          f"{manifest['profile']['width']}×{manifest['profile']['height']} · "
          f"{manifest['profile']['fps']['num']} fps · sequence.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
