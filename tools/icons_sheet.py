#!/usr/bin/env python3
"""Render every registered icon to one contact sheet (engine P painter) — visual QA for the icon layer.

    python3 tools/icons_sheet.py [--out icons-sheet.png] [--size 128]

Green means "this icon lost its stroke" at a glance: each row is one time step, each column one icon.
"""
from __future__ import annotations

import argparse
import json
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
    ap.add_argument("--group", default="", help="only icons in this group (house set, itshover, brand…)")
    ap.add_argument("--limit", type=int, default=0, help="sample at most N icons (0 = all)")
    ap.add_argument("--cols", type=int, default=0, help="columns (default: all names in one row)")
    args = ap.parse_args()

    meta = {i["id"]: i for i in json.loads((ROOT / "medo-motion" / "icons" / "manifest.json")
                                             .read_text(encoding="utf-8"))["icons"]}
    names = [n for n in ICONS if not args.group or meta.get(n, {}).get("group") == args.group]
    if args.limit and len(names) > args.limit:
        step = len(names) / args.limit
        names = [names[int(i * step)] for i in range(args.limit)]
    if not names:
        print("no icons matched"); return 1
    times = [float(t) for t in args.times.split(",")]
    cell = args.size + 36
    cols = args.cols or len(names)
    rows = (len(names) + cols - 1) // cols
    sheet = np.zeros((len(times) * rows + (len(times) - 1) * 0, len(times)), dtype=np.float32)  # placeholder
    sheet = np.zeros((len(times) * rows * cell, cols * cell, 3), dtype=np.float32)
    sheet[:, :, :] = INK

    for r, t in enumerate(times):
        for i, name in enumerate(names):
            c, row = i % cols, i // cols
            y0 = (r * rows + row) * cell
            x0 = c * cell
            dark = r % 2 == 0
            patch = np.zeros((cell - 12, cell - 12, 3), dtype=np.float32)
            patch[:, :, :] = (INK if dark else PAPER)
            draw_icon(patch, name, t, (cell - 12) / 2, (cell - 12) / 2,
                      size=args.size, color=(PAPER if dark else INK),
                      accent=(SALMON if dark else RED), loop=False)
            sheet[y0 + 6:y0 + cell - 6, x0 + 6:x0 + cell - 6] = patch

    out = Path(args.out)
    Image.fromarray(np.clip(sheet, 0, 255).astype(np.uint8)).save(out)
    print(f"icons: {len(names)} icons × {len(times)} times -> {out}")
    print("       columns:", ", ".join(names))
    print(f"       dark cells: {PAPER} stroke + {SALMON} accent · light cells: {INK} stroke + {RED} accent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
