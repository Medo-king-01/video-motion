#!/usr/bin/env python3
"""Mobile grid & platform UI safe-zone preview sheet for vertical 1080x1920 reels.

    python3 tools/phone_preview.py out/final.mp4 --out cache/phone-preview.png
    python3 tools/phone_preview.py out/cover.png --out cache/phone-preview.png --json
    python3 tools/phone_preview.py out/final.mp4 --at 1.5 --out cache/phone-s1.png --report cache/phone-s1.json

Renders a side-by-side QA sheet in locked Medo brand colours:
  1. 9:16 Reels / TikTok player (360x640) with translucent platform HUD, right-rail
     action buttons (`x:940..1080, y:1100..1500`), and bottom caption/scrub chrome (`y:1500..1920`).
  2. 3:4 Profile Grid crop (`y:240..1680` at 270x360) — what survives on the profile tab.
  3. 1:1 Square Feed safe crop (`y:420..1500` at 270x270).
  4. Real 13.5% Mobile Grid tile (`146x195`, iPhone 3-column grid scale) — arm's-length legibility test.

Also measures high-frequency detail (Sobel edge density) inside platform dead zones
so right-aligned Arabic hooks or low captions colliding with social buttons surface as warnings.
Inspired by mobile grid preview workflows in MIT-licensed `majedphotos/video-ad-editor` (see assets/CREDITS.md).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(SKILL / "scripts"))

import media_bin  # noqa: E402
from _safe_paths import checked_path  # noqa: E402

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

BRAND_DOC = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
PAL = {k: tuple(v["rgb"]) for k, v in BRAND_DOC["palette"].items()}
INK_SHADOW = tuple(BRAND_DOC["derived"]["ink_shadow"]["rgb"])


def _safe_abs(path: Path, *, tree: bool = False) -> Path:
    checked_path(Path(os.path.abspath(path)), tree=tree)
    return checked_path(path.resolve(), tree=tree)


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        ROOT / "assets" / "fonts" / "Inter" / ("Inter_700Bold.ttf" if bold else "Inter_500Medium.ttf"),
        ROOT / "assets" / "fonts" / "Cairo" / ("Cairo_800ExtraBold.ttf" if bold else "Cairo_600SemiBold.ttf"),
    ]
    for p in candidates:
        if p.is_file():
            try:
                return ImageFont.truetype(str(p), size)
            except OSError:
                continue
    return ImageFont.load_default()


def extract_frame_rgb(media_path: Path, at_sec: float = 0.0) -> tuple[np.ndarray, list[str]]:
    """Load an RGB uint8 frame from an image or video at `at_sec`, resized to 1080x1920 if needed."""
    src = _safe_abs(media_path)
    if not src.is_file():
        raise FileNotFoundError(f"Input file not found: {src}")
    ext = src.suffix.lower()
    notes: list[str] = []

    if ext in IMAGE_EXTS:
        with Image.open(src) as im:
            rgb = np.array(im.convert("RGB"), dtype=np.uint8)
    elif ext in VIDEO_EXTS:
        ffmpeg = media_bin.require_tool("ffmpeg")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = Path(tmp.name)
        try:
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-ss", f"{max(0.0, float(at_sec)):.3f}",
                "-i", str(src),
                "-frames:v", "1",
                str(tmp_png),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode != 0 or not tmp_png.is_file() or tmp_png.stat().st_size == 0:
                # Fallback to frame 0 if `--at` was slightly past stream end
                cmd_zero = [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-i", str(src), "-frames:v", "1", str(tmp_png),
                ]
                res2 = subprocess.run(cmd_zero, capture_output=True, text=True, check=False)
                if res2.returncode != 0 or not tmp_png.is_file() or tmp_png.stat().st_size == 0:
                    raise RuntimeError(f"ffmpeg failed to extract preview frame: {(res.stderr or res2.stderr).strip()}")
                notes.append(f"Timestamp {at_sec:.2f}s fell past last decodable frame; fell back to 0.00s.")
            with Image.open(tmp_png) as im:
                rgb = np.array(im.convert("RGB"), dtype=np.uint8)
        finally:
            tmp_png.unlink(missing_ok=True)
    else:
        raise ValueError(f"Unsupported media extension {ext!r}; pass an MP4/MOV video or PNG/JPG image")

    h, w = rgb.shape[:2]
    if (w, h) != (1080, 1920):
        notes.append(f"Source dimensions {w}x{h} normalised to 1080x1920 for safe-zone overlay.")
        rgb = cv2.resize(rgb, (1080, 1920), interpolation=cv2.INTER_AREA)
    return rgb, notes


def analyze_zones(rgb: np.ndarray) -> dict[str, Any]:
    """Measure edge density inside safe vs platform-occluded zones on a 1080x1920 RGB frame."""
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)
    strong = (mag >= 90.0).astype(np.float32)

    def pct(x0: int, y0: int, x1: int, y1: int) -> float:
        roi = strong[y0:y1, x0:x1]
        return round(float(roi.mean() * 100.0), 3) if roi.size else 0.0

    content_pct = pct(40, 200, 940, 1350)
    right_rail_pct = pct(940, 1100, 1080, 1500)
    bottom_ui_pct = pct(0, 1500, 1080, 1920)
    top_hud_pct = pct(0, 0, 1080, 200)
    grid_crop_top_lost = pct(40, 0, 1040, 240)
    grid_crop_bot_lost = pct(40, 1680, 1040, 1920)

    warnings: list[dict[str, str]] = []
    if right_rail_pct > max(3.8, content_pct * 0.75):
        warnings.append({
            "code": "P01",
            "zone": "right_rail",
            "msg": (
                f"High visual detail ({right_rail_pct:.1f}%) inside right-rail social buttons "
                "(x940..1080, y1100..1500); right-aligned RTL copy may be occluded by Like/Comment/Share."
            ),
        })
    if bottom_ui_pct > max(4.5, content_pct * 0.85):
        warnings.append({
            "code": "P02",
            "zone": "bottom_chrome",
            "msg": (
                f"High visual detail ({bottom_ui_pct:.1f}%) inside bottom platform chrome "
                "(y1500..1920); keep essential copy at y <= 1500."
            ),
        })
    if content_pct < 0.35:
        warnings.append({
            "code": "P03",
            "zone": "grid_3x4",
            "msg": "Safe content zone (y200..1350) has almost no sharp detail; cover may look empty on profile grids.",
        })

    return {
        "zones_strong_edge_pct": {
            "content_safe": content_pct,
            "right_rail_buttons": right_rail_pct,
            "bottom_chrome": bottom_ui_pct,
            "top_hud": top_hud_pct,
            "cropped_outside_3x4_top": grid_crop_top_lost,
            "cropped_outside_3x4_bottom": grid_crop_bot_lost,
        },
        "warnings": warnings,
    }


def _draw_reels_overlay(player_rgba: Image.Image) -> Image.Image:
    """Composite realistic semi-transparent Reels/TikTok HUD onto a 360x640 (1/3 scale) frame."""
    w, h = player_rgba.size  # 360 x 640 (exact 1/3 of 1080x1920)
    ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)

    ink = PAL["ink"]
    paper = PAL["paper"]
    salmon = PAL["salmon"]
    red = PAL["red"]
    gray4 = PAL["gray_4"]

    # Top status / camera chrome (y 0..200 -> 0..67)
    d.rectangle([0, 0, w, 67], fill=ink + (115,))
    # Bottom caption / audio bar chrome (y 1500..1920 -> 500..640)
    d.rectangle([0, 500, w, h], fill=ink + (145,))
    # Right-rail action column (x 940..1080 -> 313..360, y 1100..1500 -> 367..500)
    d.rounded_rectangle([313, 367, 356, 498], radius=10, fill=ink + (120,), outline=salmon + (190,), width=1)
    for idx in range(4):
        cy = 386 + idx * 28
        d.ellipse([325, cy - 9, 343, cy + 9], fill=paper + (190,))

    # Safe content guide (x 40..1040 -> 13..347, y 200..1350 -> 67..450)
    d.rectangle([13, 67, 347, 450], outline=paper + (95,), width=1)
    # Caption safe band (y 1350..1500 -> 450..500)
    d.rectangle([13, 450, 312, 500], outline=salmon + (130,), width=1)
    # Bottom progress scrub line
    d.line([(12, 628), (w - 12, 628)], fill=gray4 + (160,), width=2)
    d.line([(12, 628), (150, 628)], fill=red + (230,), width=2)

    return Image.alpha_composite(player_rgba, ov)


def render_preview_sheet(rgb: np.ndarray, analysis: dict[str, Any], *, title: str = "Reel Preview") -> Image.Image:
    """Build a 1360x920 brand-locked QA sheet with 9:16 HUD, 3:4 grid, 1:1 square, and 13.5% tile."""
    sheet_w, sheet_h = 1360, 920
    sheet = Image.new("RGBA", (sheet_w, sheet_h), INK_SHADOW + (255,))
    draw = ImageDraw.Draw(sheet)

    f_title = _load_font(26, bold=True)
    f_label = _load_font(18, bold=True)
    f_meta = _load_font(15, bold=False)

    paper = PAL["paper"]
    gray3 = PAL["gray_3"]
    gray4 = PAL["gray_4"]
    salmon = PAL["salmon"]
    blush = PAL["blush"]
    ink = PAL["ink"]
    ink_soft = PAL["ink_soft"]
    red = PAL["red"]

    # Header bar
    draw.rectangle([0, 0, sheet_w, 72], fill=ink + (255,))
    draw.text((36, 22), f"MOBILE & PLATFORM SAFE-ZONE QA  ·  {title}", font=f_title, fill=paper + (255,))
    status_ok = len(analysis["warnings"]) == 0
    badge_col = blush if status_ok else red
    badge_fg = ink if status_ok else paper
    badge_txt = "PASS" if status_ok else f"WARN ({len(analysis['warnings'])})"
    draw.rounded_rectangle([sheet_w - 176, 18, sheet_w - 36, 54], radius=18, fill=badge_col + (255,))
    draw.text((sheet_w - 106, 36), badge_txt, font=f_label, fill=badge_fg + (255,), anchor="mm")

    src_pil = Image.fromarray(rgb, "RGB").convert("RGBA")

    # Panel 1: 9:16 Full Player + Platform UI (360 x 640) at x=36, y=126
    p1 = src_pil.resize((360, 640), Image.LANCZOS)
    p1 = _draw_reels_overlay(p1)
    draw.text((36, 94), "1. 9:16 Reels / TikTok HUD", font=f_label, fill=paper + (255,))
    sheet.alpha_composite(p1, (36, 126))
    draw.rounded_rectangle([35, 125, 397, 767], radius=8, outline=ink_soft + (255,), width=2)
    draw.text((36, 780), "Salmon box = right-rail buttons (x940..1080)", font=f_meta, fill=gray3 + (255,))

    # Panel 2: 3:4 Profile Grid Crop (y 240..1680 -> 1080x1440 -> 270x360) at x=444, y=126
    crop_3x4 = src_pil.crop((0, 240, 1080, 1680)).resize((270, 360), Image.LANCZOS)
    draw.text((444, 94), "2. 3:4 Profile Grid Crop", font=f_label, fill=paper + (255,))
    sheet.alpha_composite(crop_3x4, (444, 126))
    draw.rectangle([443, 125, 715, 487], outline=ink_soft + (255,), width=2)
    draw.text((444, 498), "Crops y0..240 & y1680..1920", font=f_meta, fill=gray4 + (255,))

    # Panel 3: 1:1 Square Feed Safe Crop (y 420..1500 -> 1080x1080 -> 270x270) at x=756, y=126
    crop_1x1 = src_pil.crop((0, 420, 1080, 1500)).resize((270, 270), Image.LANCZOS)
    draw.text((756, 94), "3. 1:1 Feed Center Crop", font=f_label, fill=paper + (255,))
    sheet.alpha_composite(crop_1x1, (756, 126))
    draw.rectangle([755, 125, 1027, 397], outline=ink_soft + (255,), width=2)
    draw.text((756, 408), "Safe square y420..1500", font=f_meta, fill=gray4 + (255,))

    # Panel 4: Real 13.5% Mobile 3-Column Grid Tile (146 x 195) at x=1068, y=126
    tile_real = src_pil.crop((0, 240, 1080, 1680)).resize((146, 195), Image.LANCZOS)
    draw.text((1068, 94), "4. Real Grid Size (13.5%)", font=f_label, fill=salmon + (255,))
    sheet.alpha_composite(tile_real, (1068, 126))
    draw.rectangle([1067, 125, 1215, 322], outline=salmon + (255,), width=2)
    draw.text((1068, 334), "Arm's-length hook test:", font=f_meta, fill=paper + (255,))
    draw.text((1068, 356), "Arabic title >= 160px", font=f_meta, fill=gray3 + (255,))
    draw.text((1068, 378), "Subtitle >= 92px", font=f_meta, fill=gray3 + (255,))

    # Metrics & diagnostics card across bottom-right (x=444..1324, y=548..876)
    draw.rounded_rectangle([444, 548, 1324, 876], radius=12, fill=ink + (255,), outline=ink_soft + (255,), width=2)
    draw.text((468, 568), "ZONE EDGE DENSITY & READABILITY DIAGNOSTICS", font=f_label, fill=salmon + (255,))

    z = analysis["zones_strong_edge_pct"]
    metrics_lines = [
        f"Content safe (x40..940, y200..1350):  {z['content_safe']:5.2f}%",
        f"Right-rail UI (x940..1080, y1100..1500): {z['right_rail_buttons']:5.2f}%",
        f"Bottom chrome (y1500..1920):          {z['bottom_chrome']:5.2f}%",
        f"Top HUD (y0..200):                    {z['top_hud']:5.2f}%",
    ]
    for idx, line in enumerate(metrics_lines):
        draw.text((468, 606 + idx * 26), line, font=f_meta, fill=paper + (255,))

    if analysis["warnings"]:
        for idx, w_item in enumerate(analysis["warnings"][:3]):
            draw.text(
                (468, 730 + idx * 38),
                f"[{w_item['code']}] {w_item['msg'][:92]}",
                font=f_meta,
                fill=salmon + (255,),
            )
    else:
        draw.text(
            (468, 742),
            "No platform UI or 3:4 profile-grid occlusion spikes detected.",
            font=f_meta,
            fill=blush + (255,),
        )

    return sheet.convert("RGB")


def generate_phone_preview(
    media_path: Path,
    *,
    out_path: Path,
    at_sec: float = 0.0,
    report_path: Path | None = None,
) -> dict[str, Any]:
    src = _safe_abs(media_path)
    out = _safe_abs(out_path)
    rep = _safe_abs(report_path) if report_path is not None else None

    rgb, notes = extract_frame_rgb(src, at_sec=at_sec)
    analysis = analyze_zones(rgb)
    sheet = render_preview_sheet(rgb, analysis, title=f"{src.name} @ {max(0.0, float(at_sec)):.2f}s")

    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="PNG")

    payload: dict[str, Any] = {
        "version": 1,
        "status": "warn" if analysis["warnings"] else "pass",
        "source": str(src),
        "timestamp_s": round(max(0.0, float(at_sec)), 3),
        "preview_png": str(out),
        "sheet_size": [sheet.width, sheet.height],
        "zones_strong_edge_pct": analysis["zones_strong_edge_pct"],
        "warnings": analysis["warnings"],
        "notes": notes,
    }
    if rep is not None:
        rep.parent.mkdir(parents=True, exist_ok=True)
        rep.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("media", type=Path, help="rendered MP4/MOV video or 1080x1920 cover PNG/JPG")
    ap.add_argument("--out", required=True, type=Path, help="output PNG path for the mobile preview sheet")
    ap.add_argument("--at", type=float, default=0.0, help="timestamp in seconds when input is a video (default: 0.0 cover)")
    ap.add_argument("--report", type=Path, default=None, help="optional path to write JSON diagnostics")
    ap.add_argument("--json", action="store_true", help="print JSON diagnostics to stdout")
    ap.add_argument("--strict", action="store_true", help="exit non-zero when platform UI warnings are present")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = generate_phone_preview(
            args.media,
            out_path=args.out,
            at_sec=args.at,
            report_path=args.report,
        )
    except BaseException as error:  # noqa: BLE001
        if isinstance(error, SystemExit):
            raise
        if args.json:
            print(json.dumps({"version": 1, "status": "error", "error": str(error)}, ensure_ascii=False))
        else:
            print(f"phone_preview error: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"phone_preview [{payload['status'].upper()}] -> {payload['preview_png']}")
        for w_item in payload["warnings"]:
            print(f"  WARN [{w_item['code']}] {w_item['msg']}")
    if args.strict and payload["warnings"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
