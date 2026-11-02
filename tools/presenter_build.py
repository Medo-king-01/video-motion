#!/usr/bin/env python3
"""Cut the presenter poses out of their backgrounds, normalise them, and write the pose manifest.

The raw art arrives as light-background JPEGs (`assets/poses/raw/*.jpg`). A reel needs transparent,
consistently scaled cut-outs, so this tool does the boring part once and keeps it repeatable:

  1. background removal — border-connected light pixels, holes filled, largest figure kept, 1 px feed
  2. alpha trim + normalisation — every pose is scaled to the same figure height and its feet are
     put on the same baseline, so cutting between poses does not make Medo jump
  3. `assets/poses/poses.json` — slug, Arabic label, tags, size and the anchor the engines use
  4. a contact sheet on the brand background (`--sheet`) to eyeball the edges

    python3 tools/presenter_build.py                 # rebuild everything from raw/
    python3 tools/presenter_build.py --only wave,run # one or two poses
    python3 tools/presenter_build.py --sheet cache/poses.png

Both engines read the same manifest: `lib/presenter.js` (K) and `presenter.py` (P).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "assets" / "poses" / "raw"
OUT = ROOT / "assets" / "poses"
MANIFEST = OUT / "poses.json"

# Two framings, two normalisations:
#   full  — figure height normalised, soles on the ground line (1390): a wide/medium shot
#   bust  — the whole cut-out normalised by image height, hair line at the top guide (190): a close-up
# Cutting between them is a camera push-in, which is exactly what these two sets are for.
FRAMING = {"full": {"height": 1200, "place": "feet"}, "bust": {"height": 1180, "place": "top"}}
MARGIN = 8               # padding kept around the cut-out

# slug → Arabic label, English label, tags, facing, notes. `scale` is applied when drawing
# (a seated pose normalised to the same height would look oversized next to a standing one).
POSES = [
    ("neutral",       "طبيعي",              "neutral",        ["standing", "idle"],            "front", "وضعية الأساس — اليدين على الجانبين"),
    ("explain",       "شرح أو تفكير",        "explaining",     ["standing", "talk", "hands"],   "front", "يد مفتوحة + إصبع على الذقن"),
    ("point",         "بيشاور",              "pointing",       ["standing", "direct"],          "front", "بيشاور بإيد والثانية على الذقن"),
    ("welcome",       "الترحيب بالجمهور",    "welcome",        ["standing", "open arms"],       "front", "الدراعين مفتوحين للكاميرا"),
    ("wave",          "التلويح باليد",       "wave",           ["standing", "greeting"],        "front", "إيد مرفوعة — تتحرك بدورة إيقاعية"),
    ("clap",          "التسقيف",             "clapping",       ["standing", "celebration"],     "front", "إيدين متقابلين — تصفيق"),
    ("like",          "الاعجاب",             "delighted",      ["standing", "smile", "hands"],  "front", "إيدين على الصدر ووش مبسوط"),
    ("thinking",      "التفكير",             "thinking",       ["standing", "pause"],           "front", "إصبع على الذقن، جسم مستقيم"),
    ("thinking-deep", "التفكير العميق",      "thinking-deep",  ["sitting", "stool", "pause"],   "front", "قاعد على كرسي — لحظة تأمل طويلة"),
    ("puzzled",       "الحيرة",              "puzzled",        ["standing", "question"],        "front", "يد مفتوحة + علامة استفهام في الوش"),
    ("sad",           "حزين",                "sad",            ["standing", "down", "pockets"], "front", "بص لتحت وإيدين في الجيوب"),
    ("shocked",       "مصدوم",               "shocked",        ["standing", "impact", "wide"],  "front", "فزع/صدمة — للـimpact cuts"),
    ("walk",          "المشي",               "walking",        ["motion", "side"],              "left",  "خطوة مشي — loop أو cut"),
    ("run",           "الجري",               "running",        ["motion", "side"],              "left",  "جري — حركة سريعة/إلحاح"),
    # ---- batch 2: everyday beats ----
    ("waiting",       "إيدين في الجيوب",     "waiting",        ["standing", "idle", "pockets"], "front", "idle تانية — إيدين في الجيوب"),
    ("warm",          "دفء",                "warm",           ["standing", "sincere", "smile"], "front", "إيد على الصدر وابتسامة — جملة صادقة"),
    ("phone",         "ماسك موبايل",         "phone",          ["standing", "tech"],            "front", "بيقرأ/بيكتب على الموبايل"),
    ("unfold",        "بيفتح ورقة",          "unfold",         ["standing", "document"],        "front", "ورقة/سكريبت — بيقدّم فكرة"),
    ("point-up",      "بيشاور لفوق",         "point-up",       ["standing", "direct"],          "front", "إصبع لفوق — تأكيد نقطة"),
    ("seated-talk",   "قاعد بيتكلم",         "seated-talk",    ["sitting", "chair", "talk"],    "front", "قاعد على كرسي — كلام هادي"),
    # ---- batch 2: close-ups (camera push-in) ----
    ("close-neutral", "نصف جسد طبيعي",       "close-neutral",  ["bust", "idle"],                "front", "قريب — الأساس"),
    ("close-explain", "نصف جسد يشرح",        "close-explain",  ["bust", "talk"],                "front", "قريب — شرح بإيد مفتوحة"),
    ("close-point",   "نصف جسد يشير",        "close-point",    ["bust", "direct"],              "front", "قريب — إشارة"),
    ("close-thinking","نصف جسد يفكر",        "close-thinking", ["bust", "pause"],               "front", "قريب — تفكير"),
]

# Which poses are close-ups (everything else is a full shot).
BUST = {"close-neutral", "close-explain", "close-point", "close-thinking"}


SCALE = {"thinking-deep": 0.86, "run": 0.94, "walk": 0.97}

def _load(path: Path) -> np.ndarray:
    im = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if im is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(im, cv2.COLOR_BGR2RGB)


def cutout(im: np.ndarray, log: list[str]) -> np.ndarray:
    """RGB → RGBA with the light studio background removed (border flood + largest component)."""
    h, w = im.shape[:2]
    mx = im.max(2).astype(int)
    mn = im.min(2).astype(int)
    white = mn >= 228                                        # paper-white studio background
    shadow = (mx - mn < 16) & (mn > 120) & (mn <= 228)       # the soft grey contact shadow
    shadow[: int(h * 0.45)] = False                          # never above mid-frame
    # Treat *every* background-coloured pixel as background, not only the border-connected ones:
    # the studio white also shows through the gap between the stool legs, and there it is enclosed
    # by the figure (so a border flood leaves a white block behind).
    bg = white | shadow
    fg = ~bg
    fg = ndi.binary_opening(fg, iterations=1)

    # drop JPEG specks but keep small deliberate marks (sweat drops, sparkles)
    lab2, n2 = ndi.label(fg)
    if n2:
        sizes = ndi.sum(fg, lab2, range(1, n2 + 1))
        biggest = sizes.max()
        keep = [i + 1 for i, v in enumerate(sizes) if v > max(24, 0.002 * biggest)]
        fg = np.isin(lab2, keep)
        log.append(f"components={n2} kept={len(keep)}")

    # the figure's own enclosed whites (t-shirt, highlights) are holes in the silhouette → fill them,
    # but only up to 10% of the figure, so a real background gap stays transparent
    # Enclosed regions are either the figure's own whites (t-shirt: shaded, mean ≈242, std ≥3) or
    # studio background showing through a gap (arms/legs/stool: pure white, mean ≥252, std ≤2.5).
    # Fill the first, punch out the second.
    holes = ndi.binary_fill_holes(fg) & ~fg
    hl, hn = ndi.label(holes)
    fill_ids, punch_ids = [], []
    for i in range(1, hn + 1):
        m = hl == i
        area = int(m.sum())
        if area < 60:
            continue
        inner = ndi.binary_erosion(m, iterations=4)      # ignore the anti-aliased rim
        vals = im[inner if inner.any() else m].astype(np.float32)
        pure_white = float(vals.mean()) >= 250.5 and float(vals.std()) <= 4.0
        # pure white → the studio background showing through; anything shaded → part of the figure
        if pure_white:
            punch_ids.append(i)
        else:
            fill_ids.append(i)
    if fill_ids:
        fg = fg | np.isin(hl, fill_ids)
    if punch_ids:
        fg = fg & ~np.isin(hl, punch_ids)
    log.append(f"holes={hn} filled={len(fill_ids)} punched={len(punch_ids)}")

    alpha = ndi.binary_erosion(fg, iterations=1).astype(np.float32)
    alpha = cv2.GaussianBlur(alpha, (0, 0), 0.8)

    # de-halo: JPEG ringing leaves a light rim; pull the rim pixels toward the nearby figure colour
    rim = (alpha > 0.02) & (alpha < 0.85)
    if rim.any():
        blur = cv2.GaussianBlur(im.astype(np.float32), (0, 0), 2.2)
        im = im.astype(np.float32).copy()
        im[rim] = im[rim] * 0.35 + blur[rim] * 0.65
        im = np.clip(im, 0, 255).astype(np.uint8)

    return np.dstack([im, (alpha * 255).astype(np.uint8)])


def normalise(rgba: np.ndarray, target_h: int = 1200) -> np.ndarray:
    ys, xs = np.where(rgba[..., 3] > 8)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    crop = rgba[y0: y1 + 1, x0: x1 + 1]        # crop first — resizing the full frame squeezes it
    h, w = crop.shape[:2]
    scale = target_h / h
    nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
    im = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LANCZOS4)
    # trim again (resampling can add a 1 px halo row) and pad with a transparent margin
    a = im[..., 3]
    ys, xs = np.where(a > 8)
    im = im[ys.min(): ys.max() + 1, xs.min(): xs.max() + 1]
    out = np.zeros((im.shape[0] + 2 * MARGIN, im.shape[1] + 2 * MARGIN, 4), np.uint8)
    out[MARGIN: MARGIN + im.shape[0], MARGIN: MARGIN + im.shape[1]] = im
    return out


def build(only: list[str] | None = None) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"_doc": "Presenter cut-outs. Generated by tools/presenter_build.py from assets/poses/raw/. "
                        "Engines read this file: lib/presenter.js (K) and presenter.py (P). Split each file "
                        "into <slug>.png + poses.json; never hand-edit the PNGs.",
                "figureHeight": FRAMING["full"]["height"],
                "bustHeight": FRAMING["bust"]["height"],
                "topGuide": 190,
                "margin": MARGIN,
                "ground": 1390,
                "poses": {}}
    for slug, ar, en, tags, facing, note in POSES:
        if only and slug not in only:
            continue
        src = RAW / f"{slug}.jpg"
        if not src.exists():
            print(f"  skip {slug}: no {src.relative_to(ROOT)}")
            continue
        log: list[str] = []
        framing = "bust" if slug in BUST else "full"
        rgba = normalise(cutout(_load(src), log), FRAMING[framing]["height"])
        h, w = rgba.shape[:2]
        # PIL's optimiser packs the alpha much better than cv2's default PNG writer
        from PIL import Image  # noqa: PLC0415

        Image.fromarray(rgba, "RGBA").save(OUT / f"{slug}.png", optimize=True, compress_level=9)
        manifest["poses"][slug] = {
            "scale": SCALE.get(slug, 1.0),
            "ar": ar, "en": en, "file": f"{slug}.png", "tags": tags, "facing": facing, "note": note,
            "framing": framing,
            # how the engines place it: `feet` → soles on the ground line, `top` → hair on the top guide
            "place": FRAMING[framing]["place"],
            "w": int(w), "h": int(h),
            "feet": round((h - MARGIN) / h, 4),
            "center": round(0.5, 4),
        }
        print(f"  {slug:14s} {w}×{h}  {'; '.join(log)}")
    if MANIFEST.exists() and only:
        merged = json.loads(MANIFEST.read_text(encoding="utf-8"))
        merged["poses"].update(manifest["poses"])
        manifest["poses"] = merged["poses"]
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def sheet(manifest: dict, out: Path, cols: int = 7, cell_h: int = 420, background=(10, 10, 10)) -> Path:
    """Contact sheet on the brand's dark background — catches white halos and scale mismatches."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    poses = manifest["poses"]
    cell_w = int(cell_h * 0.62)
    rows = (len(poses) + cols - 1) // cols
    pad, label_h = 10, 24
    img = Image.new("RGB", (cols * (cell_w + pad) + pad, rows * (cell_h + label_h + pad) + pad + 30), background)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(sorted((ROOT / "assets" / "fonts").rglob("Cairo*Regular*.ttf"))[0]), 15)
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()
    n_bust = sum(1 for v in poses.values() if v.get("framing") == "bust")
    d.text((pad, 8),
           f"Medo — {len(poses)} poses: {len(poses) - n_bust} full (feet on {manifest['ground']}) "
           f"+ {n_bust} close-ups (hair on {manifest['topGuide']})",
           font=font, fill=(201, 197, 194))
    for i, (slug, meta) in enumerate(poses.items()):
        r, c = divmod(i, cols)
        x = pad + c * (cell_w + pad)
        y = 30 + pad + r * (cell_h + label_h + pad)
        im = Image.open(OUT / meta["file"]).convert("RGBA")
        s = min(cell_w / im.width, cell_h / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
        img.paste(im, (x + (cell_w - im.width) // 2, y + cell_h - im.height), im)
        d.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=(90, 74, 73))
        d.text((x + 2, y + cell_h + 4), f"{slug} · {meta['en']}", font=font, fill=(213, 174, 166))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma separated slugs")
    ap.add_argument("--sheet", nargs="?", const=str(ROOT / "cache" / "poses-sheet.png"), default=None)
    ap.add_argument("--cols", type=int, default=7)
    args = ap.parse_args()
    only = [s.strip() for s in args.only.split(",")] if args.only else None
    manifest = build(only)
    print(f"manifest -> {MANIFEST.relative_to(ROOT)} ({len(manifest['poses'])} poses)")
    if args.sheet:
        print(f"sheet    -> {sheet(manifest, Path(args.sheet), cols=args.cols)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
