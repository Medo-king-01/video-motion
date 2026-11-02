#!/usr/bin/env python3
"""Render a specimen sheet of the type system — Arabic and Latin, on the brand backgrounds.

This is the QA artefact for choosing type, the same way `cache/poses-sheet.png` is the QA artefact for
the pose library: look at it, compare families on the real backgrounds, then pick by evidence.

    python3 tools/fonts_preview.py                      # cache/fonts-sheet.png
    python3 tools/fonts_preview.py --out x.png --light  # the same sheet on paper

Every string is rendered with real shaping (`arabic_shape.draw` → HarfBuzz), so what you see is what
the engines will draw — no isolated letters.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from PIL import ImageFont as PILFont

ROOT = Path(__file__).resolve().parents[1]
ENGINE_P = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(ENGINE_P))

import arabic_shape  # noqa: E402

FONTS = ROOT / "assets" / "fonts"
MANIFEST = FONTS / "fonts.json"

AR_SAMPLE = "النهاردة هنجرّب حاجة جديدة"
AR_DETAIL = "الأسعار ١٢٤٥ جنيه · 4.2K مشاهدة"
LAT_SAMPLE = "Sphinx of black quartz, judge my vow"
LAT_DETAIL = "DEFAULT 4.2K · 1080×1920 · 30 fps"

DARK = (3, 3, 3)
INK = (10, 10, 10)
PAPER = (243, 242, 241)
GRAY = (163, 162, 160)
SALMON = (217, 127, 104)
RED = (203, 39, 27)

PAIRS = [("Cairo", "Inter"), ("Tajawal", "Space Grotesk"), ("Alexandria", "Anton"),
         ("Kufam", "Space Grotesk"), ("El Messiri", "Inter"),
         ("IBM Plex Sans Arabic", "IBM Plex Mono"), ("Amiri", "Instrument Serif")]


def load() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def pick(meta: dict, want: int) -> Path:
    """The heaviest weight at or below `want` (fallback: the heaviest available)."""
    ws = sorted(meta["weights"], key=lambda w: w["weight"])
    fit = [w for w in ws if w["weight"] <= want] or ws
    return FONTS / meta["family_dir"] / fit[-1]["file"]


def family_file(manifest: dict, family: str, want: int = 800) -> Path:
    meta = dict(manifest["families"][family])
    meta["family_dir"] = family
    return pick(meta, want)


def _bg(w: int, h: int, top, bottom) -> Image.Image:
    img = Image.new("RGB", (w, h), top)
    d = ImageDraw.Draw(img)
    for i in range(h):
        k = i / max(1, h - 1)
        d.line([(0, i), (w, i)], fill=tuple(int(top[c] * (1 - k) + bottom[c] * k) for c in range(3)))
    return img


def sheet(light: bool = False, width: int = 1400) -> Image.Image:
    manifest = load()
    families = manifest["families"]
    arabic = [f for f, m in families.items() if m["script"] == "arabic"]
    latin = [f for f, m in families.items() if m["script"] == "latin"]
    row_h = 158
    head_h = 96
    pad = 48
    pair_h = 150
    height = head_h * 2 + row_h * (len(arabic) + len(latin)) + 40 + pair_h * len(PAIRS) + 120
    bg_top, bg_bot = ((243, 242, 241), (216, 215, 213)) if light else ((10, 10, 10), (3, 3, 3))
    fg, sub, accent = ((10, 10, 10), (113, 113, 122), RED) if light else ((243, 242, 241), GRAY, SALMON)
    img = _bg(width, height, bg_top, bg_bot).convert("RGBA")   # arabic_shape.draw composites RGBA
    d = ImageDraw.Draw(img)
    mono = family_file(manifest, "IBM Plex Mono", 600)
    label_font = PILFont.truetype(str(mono), 19)
    y = 34
    d.text((pad, y), "FREE TYPE SYSTEM  ·  14 FAMILIES  ·  SIL OFL 1.1  ·  commercial use, no attribution",
           font=label_font, fill=sub)
    y += 52

    def section(title: str) -> None:
        nonlocal y
        d.text((pad, y), title, font=PILFont.truetype(str(mono), 22), fill=accent)
        d.line([(pad, y + 34), (width - pad, y + 34)], fill=sub, width=1)
        y += 52

    def row(family: str, sample: str, detail: str, rtl: bool) -> None:
        nonlocal y
        meta = families[family]
        path = family_file(manifest, family, 800)
        weights = "/".join(str(w["weight"]) for w in meta["weights"])
        d.text((pad, y + 22), family, font=PILFont.truetype(str(mono), 22), fill=fg)
        d.text((pad, y + 52), f"{weights}   ·   {meta['tags'][0]}", font=PILFont.truetype(str(mono), 15), fill=sub)
        if rtl:
            arabic_shape.draw(img, (width - pad, y + 26), str(path), sample, 54, fg, rtl=True, anchor="rm")
            arabic_shape.draw(img, (width - pad, y + 106), str(path), detail, 26, sub, rtl=True, anchor="rm")
        else:
            pad_f = pick(meta | {"family_dir": family}, 800)
            d.text((360, y + 46), sample, font=PILFont.truetype(str(pad_f), 42), fill=fg, anchor="lm")
            d.text((360, y + 98), detail, font=PILFont.truetype(str(pad_f), 22), fill=sub, anchor="lm")
        y += row_h
        d.line([(pad, y - 12), (width - pad, y - 12)], fill=sub, width=1)

    section("ARABIC — 8 families")
    for f in arabic:
        row(f, AR_SAMPLE, AR_DETAIL, rtl=True)
    y += 24
    section("LATIN — 6 families")
    for f in latin:
        row(f, LAT_SAMPLE, LAT_DETAIL, rtl=False)

    y += 24
    section("PAIRINGS — Arabic × Latin that share proportions")
    for ar, la in PAIRS:
        ar_path = family_file(manifest, ar, 800)
        la_path = family_file(manifest, la, 700)
        d.text((pad, y + 26), f"{ar}  ×  {la}", font=PILFont.truetype(str(mono), 19), fill=sub)
        arabic_shape.draw(img, (width / 2 - 40, y + 76), str(ar_path), "السرعة", 56, fg, rtl=True,
                          anchor="rm")
        d.text((width / 2 + 40, y + 76), "SPEED", font=PILFont.truetype(str(la_path), 46), fill=accent,
               anchor="lm")
        d.text((width - pad, y + 30), "4.2K", font=PILFont.truetype(str(la_path), 34), fill=fg, anchor="ra")
        y += pair_h
    d.text((pad, height - 54), "The agent picks the face per scene/element — no forced default "
                               "(docs/fonts.md).", font=PILFont.truetype(str(mono), 17), fill=sub)
    return img


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "cache" / "fonts-sheet.png"))
    ap.add_argument("--light", action="store_true", help="render on the paper background instead")
    ap.add_argument("--width", type=int, default=1400)
    a = ap.parse_args()
    img = sheet(a.light, a.width).convert("RGB")
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    print(f"sheet -> {out}  ({img.width}×{img.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
