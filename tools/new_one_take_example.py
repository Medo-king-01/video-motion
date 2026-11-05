#!/usr/bin/env python3
"""Scaffold the complete Phase 2C One-Take example into a real P, K or R project (stdlib only)."""
import argparse
import shutil
from pathlib import Path

from new_project import scaffold, slugify

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "medo-motion" / "examples" / "one-take"


def create_one_take_example(slug: str, engine: str, out: str, force: bool = False) -> Path:
    project = scaffold(slugify(slug), engine, out, force)
    for plan in EXAMPLE.joinpath("plan").glob("*.json"):
        shutil.copy2(plan, project / "plan" / plan.name)
    if engine == "p":
        shutil.copy2(EXAMPLE / "p" / "scenes.py", project / "scenes.py")
    elif engine == "k":
        shutil.copy2(EXAMPLE / "k" / "data.js", project / "src" / "data.js")
        shutil.copy2(EXAMPLE / "k" / "one-take.js", project / "src" / "scenes" / "one-take.js")
    elif engine == "r":
        shutil.copy2(EXAMPLE / "r" / "Root.tsx", project / "src" / "Root.tsx")
        shutil.copy2(EXAMPLE / "r" / "OneTakeExample.tsx", project / "src" / "OneTakeExample.tsx")
    else:
        raise ValueError("The one-take example supports one native engine at a time: p, k or r")
    return project


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug")
    parser.add_argument("--engine", required=True, choices=["p", "k", "r"])
    parser.add_argument("--out", required=True, help="new project directory (outside Git is recommended)")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    project = create_one_take_example(args.slug, args.engine, args.out, args.force)
    print(f"created {project}  (engine={args.engine}, example=one-take)")
    print("silent preview: 8 seconds / 30 fps; replace timing only from measured VO in a production project")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
