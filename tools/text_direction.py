#!/usr/bin/env python3
"""Validate / initialise the agent-authored text direction for a reel project.

The agent chooses an explicit caption + on-screen text style per scene and records
it in plan/text-direction.json. There is no default look and no random picker.

    python3 tools/text_direction.py projects/<slug> --init     # draft skeleton from beats
    python3 tools/text_direction.py projects/<slug> --check    # errors block a render
    python3 tools/text_direction.py projects/<slug> --json out/qa/text-direction.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENGINE_P = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(ENGINE_P))

import text_direction as td  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("project", type=Path)
    ap.add_argument("--init", action="store_true", help="write a draft skeleton mirroring plan/beats.json")
    ap.add_argument("--check", action="store_true", help="validate; exit 1 on errors")
    ap.add_argument("--json", type=Path, help="write the validation report as JSON")
    a = ap.parse_args()

    beats_p = a.project / "plan" / "beats.json"
    beats = json.loads(beats_p.read_text(encoding="utf-8")) if beats_p.is_file() else {}
    dir_p = a.project / "plan" / "text-direction.json"

    if a.init:
        draft = td.init_draft(beats)
        dir_p.parent.mkdir(parents=True, exist_ok=True)
        dir_p.write_text(json.dumps(draft, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote draft {dir_p} — the agent must fill every captionStyle/textStyles and rationale")
        return 0

    direction = td.load(a.project)
    report = td.validate(direction, beats, td.load_copy(a.project), td.load_fonts(a.project) or None)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for e in report["errors"]:
        print(f"!! {e}")
    for w in report["warnings"]:
        print(f" ? {w}")
    if not report["errors"] and not report["warnings"]:
        print("text-direction OK — every scene has an explicit, justified style")
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
