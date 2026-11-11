#!/usr/bin/env python3
"""One source for the Python audio + rhythm libraries (`shared/py/`).

The synthesiser, the mixer, the music and SFX generators and the beat grid are not drawing code:
every engine's reel uses them through `tools/` (audio_mix, music_kit, sfx_kit, vo_length,
pipeline). They used to exist only inside the engine-P template, so the studio's tools depended on
one renderer's folder. `shared/py/` is now the only editable copy; the tools import from it.

Engine P keeps real, committed copies because a scaffolded P project is self-contained (it copies
the template and runs without the repository). This script keeps those copies honest:

    python3 tools/sync_shared_py.py --check     # CI gate: exit 1 on any drift
    python3 tools/sync_shared_py.py --write     # copy shared/py -> the engine-P template

Same contract as `tools/sync_shared_libs.py` (the JavaScript twin): edit the shared file, run
`--write`, commit both.
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("shared") / "py"
TARGETS = (Path("medo-motion") / "templates" / "procedural-reels",)
SYNC_HINT = "python3 tools/sync_shared_py.py --write"


def source_files(root: Path = ROOT) -> list[str]:
    directory = root / SOURCE
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.glob("*.py") if p.is_file())


def drift(root: Path = ROOT) -> list[str]:
    """Human-readable list of every disagreement; empty means in sync."""
    shared = source_files(root)
    problems = [] if shared else [f"no shared sources found in {SOURCE}/ (expected the audio/rhythm libraries)"]
    for name in shared:
        canonical = (root / SOURCE / name).read_bytes()
        for target in TARGETS:
            copy = root / target / name
            if not copy.is_file():
                problems.append(f"missing: {target / name}")
            elif copy.read_bytes() != canonical:
                problems.append(f"drift:   {target / name}")
    return problems


def sync(root: Path = ROOT, *, write: bool = False) -> int:
    if write:
        for name in source_files(root):
            canonical = (root / SOURCE / name).read_bytes()
            for target in TARGETS:
                destination = root / target / name
                if not destination.is_file() or destination.read_bytes() != canonical:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    destination.write_bytes(canonical)
                    print(f"updated {target / name}")
    problems = drift(root)
    for line in problems:
        print(line)
    if problems:
        print(f"{len(problems)} shared-py problem(s) — run: {SYNC_HINT}")
        return 1
    print(f"OK shared/py matches the engine-P template ({len(source_files(root))} files)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify the template matches shared/py (default)")
    mode.add_argument("--write", action="store_true", help="copy shared/py into the engine-P template")
    parser.add_argument("--list", action="store_true", help="print the shared files and exit")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (tests)")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(source_files(args.root)))
        return 0
    return sync(args.root, write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
