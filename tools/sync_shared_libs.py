#!/usr/bin/env python3
"""One source for the JS libraries both renderers ship (K canvas + R Remotion).

`shared/js/` is the only editable copy. The two engines keep real, committed copies
(`medo-motion/templates/render/lib/` and `.../remotion/src/lib/`) because a scaffolded
project must be self-contained and Remotion must not import from outside its root.
This script keeps those copies honest:

    python3 tools/sync_shared_libs.py --check     # CI gate: exit 1 on any drift
    python3 tools/sync_shared_libs.py --write     # copy shared/js -> both engines

`--check` fails on three different mistakes:
  * a shared file missing from an engine,
  * a shared file that differs from the engine copy,
  * a file that exists in *both* engines but not in `shared/js/` (someone duplicated a
    new library by hand; promote it instead).
"""
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = Path("shared") / "js"
TARGETS = (
    Path("medo-motion") / "templates" / "render" / "lib",
    Path("medo-motion") / "templates" / "remotion" / "src" / "lib",
)
SYNC_HINT = "python3 tools/sync_shared_libs.py --write"


def source_files(root: Path = ROOT) -> list[str]:
    directory = root / SOURCE
    if not directory.is_dir():
        return []
    return sorted(p.name for p in directory.glob("*.js") if p.is_file())


def engine_files(root: Path = ROOT, target: Path | None = None) -> list[str]:
    directories = TARGETS if target is None else (target,)
    names: set[str] = set()
    for relative in directories:
        directory = root / relative
        if directory.is_dir():
            names.update(p.name for p in directory.glob("*.js") if p.is_file())
    return sorted(names)


def shared_in_every_engine(root: Path = ROOT) -> list[str]:
    """Files that exist in two or more engine dirs — candidates for the shared set."""
    names = engine_files(root)
    return [name for name in names if all((root / target / name).is_file() for target in TARGETS)]


def drift(root: Path = ROOT) -> list[str]:
    """Human-readable list of every disagreement; empty means in sync."""
    problems: list[str] = []
    shared = source_files(root)
    if not shared:
        problems.append(f"no shared sources found in {SOURCE}/ (expected the JS libraries)")
    shared_set = set(shared)
    for name in shared:
        canonical = (root / SOURCE / name).read_bytes()
        for target in TARGETS:
            copy = root / target / name
            if not copy.is_file():
                problems.append(f"missing: {target / name}")
            elif copy.read_bytes() != canonical:
                problems.append(f"drift:   {target / name}")
    for name in shared_in_every_engine(root):
        if name not in shared_set:
            problems.append(f"unpromoted: {name} exists in both engines but not in {SOURCE}/")
    return problems


def sync(root: Path = ROOT, *, write: bool = False) -> int:
    problems = drift(root)
    if not write:
        for line in problems:
            print(line)
        if problems:
            print(f"{len(problems)} shared-lib problem(s) — run: {SYNC_HINT}")
            return 1
        print(
            f"OK shared/js matches both engines "
            f"({len(source_files(root))} files: render/lib + remotion/src/lib)"
        )
        return 0
    copied = 0
    for name in source_files(root):
        canonical = (root / SOURCE / name).read_bytes()
        for target in TARGETS:
            destination = root / target / name
            if not destination.is_file() or destination.read_bytes() != canonical:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(canonical)
                copied += 1
                print(f"updated {target / name}")
    remaining = drift(root)
    if remaining:
        for line in remaining:
            print(line)
        return 1
    print(f"OK synced {len(source_files(root))} shared files ({copied} copy/copies updated)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="verify the engines match shared/js (default)")
    mode.add_argument("--write", action="store_true", help="copy shared/js into both engines")
    parser.add_argument("--list", action="store_true", help="print the shared files and exit")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root (tests)")
    args = parser.parse_args(argv)
    if args.list:
        for name in source_files(args.root):
            print(name)
        return 0
    return sync(args.root, write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
