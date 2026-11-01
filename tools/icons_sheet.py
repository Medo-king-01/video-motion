#!/usr/bin/env python3
"""Render every registered icon to one contact sheet (engine P painter) — visual QA for the icon layer.

    python3 tools/icons_sheet.py [--out icons-sheet.png] [--size 128]

Green means "this icon lost its stroke" at a glance: each row is one time step, each column one icon.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))

from icons import ICONS, draw_icon  # noqa: E402

INK = (71, 57, 56)
PAPER = (243, 242, 241)
RED = (203, 39, 27)
SALMON = (217, 127, 104)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="icons-sheet.png")
    ap.add_argument("--size", type=int, default=128)
    ap.add_argument("--times", default="0.25,0.5,0.9,1.4,2.2")
    args = ap.parse_args()

    names = list(ICONS)
    times = [float(t) for t in args.times.split(",")]
    cell = args.size + 36
    sheet = np.zeros((len(times) * cell, len(names) * cell, 3), dtype=np.float32)
    sheet[:, :, :] = INK

    for r, t in enumerate(times):
        for c, name in enumerate(names):
            # dark cell on even rows, light cell on odd rows: proves the icon works on both surfaces
            patch = np.zeros((cell - 12, cell - 12, 3), dtype=np.float32)
            patch[:, :, :] = (INK if r % 2 == 0 else PAPER)
            draw_icon(patch, name, t, (cell - 12) / 2, (cell - 12) / 2,
                      size=args.size, color=(PAPER if r % 2 == 0 else INK),
                      accent=(SALMON if r % 2 == 0 else RED), loop=False)
            sheet[r * cell + 6:r * cell + cell - 6, c * cell + 6:c * cell + cell - 6] = patch

    out = Path(args.out)
    Image.fromarray(np.clip(sheet, 0, 255).astype(np.uint8)).save(out)
    print(f"icons: {len(names)} icons × {len(times)} times -> {out}")
    print("       columns:", ", ".join(names))
    print(f"       dark cells: {PAPER} stroke + {SALMON} accent · light cells: {INK} stroke + {RED} accent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
