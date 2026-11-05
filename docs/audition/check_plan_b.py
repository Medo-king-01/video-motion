#!/usr/bin/env python3
"""Guard: the audition decisions must never be silently applied.

Reads the retained plans in this folder and checks that the live preset file still carries the
original values. Exits 1 with a list of every drifted value, 0 otherwise.

Kept as its own file rather than inlined into `verify.sh`: the first version compared JSON as
*strings*, so a plan value of 0.224 vs a hand edit of 0.22 reported "not applied" while the preset
had in fact moved. Numbers, with a tolerance, are the only honest comparison here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PRESETS = ROOT / "medo-motion" / "motion" / "music-presets.json"
PLAN = HERE / "plan_b_layers.json"
BASE = "82d8c3e"          # the commit that delivered the audio engine
TOL = 5e-3                # the plan stores 3 decimals; a hand edit rounding to 0.22 still counts


def load_base() -> dict:
    out = subprocess.run(["git", "show", f"{BASE}:{PRESETS.relative_to(ROOT)}"],
                         capture_output=True, text=True, cwd=ROOT)
    return json.loads(out.stdout) if out.returncode == 0 and out.stdout.strip() else {}


def layers(doc: dict, preset: str) -> dict:
    return (doc.get("presets", {}).get(preset, {}) or {}).get("layers", {}) or {}


def main() -> int:
    if not PLAN.exists():
        print(f"  SKIP  {'Plan B layer values':<56} (plan_b_layers.json missing)")
        return 0

    plan = json.loads(PLAN.read_text())
    now = json.loads(PRESETS.read_text())
    base = load_base()

    drifted = []
    for preset, want_layers in plan.items():
        for layer, want in want_layers.items():
            have = layers(now, preset).get(layer)
            was = layers(base, preset).get(layer)
            if have is None or was is None:
                continue
            moved = abs(float(was) - float(want)) > TOL     # the plan would change this value
            landed = abs(float(have) - float(want)) <= TOL  # and the file now sits on it
            if moved and landed:
                drifted.append(f"{preset}.{layer} = {have} (base {was}, plan {want})")

    if drifted:
        print("  FAIL  Plan B layer values  -> APPLIED:")
        for line in drifted:
            print(f"          {line}")
        return 1

    print(f"  PASS  {'Plan B layer values':<56} not applied")
    return 0


if __name__ == "__main__":
    sys.exit(main())
