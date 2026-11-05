#!/usr/bin/env python3
"""Generate brand-locked 9:16 reel covers and 16:9 YouTube thumbnails.

Examples:
  python3 tools/cover_generator.py --title "أداة هتغيّر شغلك" --out-dir out/cover
  python3 tools/cover_generator.py --title "Claude Code" --subtitle "شرح عملي" \
      --frame projects/demo/out/master.mp4 --at 4.2 --pose explain --out-dir projects/demo/out/cover
  python3 tools/cover_generator.py --title "أفضل أدوات AI" --style blueprint --pose phone-show

The tool creates static PNG assets only. It does not modify a video or add a default
series name, logo, episode number, or other unrequested copy.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
BRAND_PATH = SKILL / "brand" / "brand.json"
POSES_PATH = ROOT / "assets" / "poses" / "poses.json"
FONTS_PATH = ROOT / "assets" / "fonts" / "fonts.json"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

STYLES = {
    "tech-editorial": {"theme": "dark", "grid": True, "glow": True, "font_ar": "Alexandria",
                       "font_latin": "Space Grotesk", "weight": 800},
    "keynote": {"theme": "light", "grid": False, "glow": False, "font_ar": "Tajawal",
                "font_latin": "Inter", "weight": 800},
    "blueprint": {"theme": "dark", "grid": True, "glow": False, "font_ar": "IBM Plex Sans Arabic",
                  "font_latin": "IBM Plex Sans", "weight": 600},
    "terminal": {"theme": "dark", "grid": True, "glow": False, "font_ar": "IBM Plex Sans Arabic",
                 "font_latin": "IBM Plex Mono", "weight": 600},
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def palette() -> dict[str, tuple[int, int, int]]:
    data = _read_json(BRAND_PATH)
    colors = {key: tuple(value["rgb"]) for key, value in data["palette"].items()}
    colors["ink_shadow"] = tuple(data["derived"]["ink_shadow"]["rgb"])
    return colors


def _safe_input(path: Path) -> Path:
    """Reject symlinks and missing inputs before opening user-supplied media."""
    absolute = Path(os.path.abspath(path))
    current = absolute
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"Refusing symlink input: {current}")
        current = current.parent
    if not absolute.is_file():
        raise FileNotFoundError(f"Input file not found: {absolute}")
    return absolute


def _font_file(family: str, weight: int) -> Path:
    registry = _read_json(FONTS_PATH)["families"]
    if family not in registry:
        raise ValueError(f"Unknown font family {family!r}; choose one from assets/fonts/fonts.json")
    weights = registry[family]["weights"]
    chosen = min(weights, key=lambda item: abs(int(item["weight"]) - weight))
    path = ROOT / "assets" / "fonts" / family / chosen["file"]
    if not path.is_file():
        raise FileNotFoundError(f"Font file is missing: {path}")
    return path


def _load_font(family: str, weight: int, size: int) -> ImageFont.FreeTypeFont:
    path = _font_file(family, weight)
    try:
        return ImageFont.truetype(str(path), size=size, layout_engine=ImageFont.Layout.RAQM)
    except (AttributeError, ValueError):
        return ImageFont.truetype(str(path), size=size)


def _is_arabic(text: str) -> bool:
    return any("\u0600" <= char <= "\u06ff" or "\u0750" <= char <= "\u077f" for char in text)


def _text_options(text: str) -> dict[str, str]:
    return {"direction": "rtl", "language": "ar"} if _is_arabic(text) else {"direction": "ltr"}


def _text_length(font: ImageFont.FreeTypeFont, text: str) -> float:
    try:
        return font.getlength(text, **_text_options(text))
    except (KeyError, TypeError, ValueError):
        return font.getlength(text)


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str,
               font: ImageFont.FreeTypeFont, **kwargs: Any) -> None:
    try:
        draw.text(xy, text, font=font, **kwargs, **_text_options(text))
    except (KeyError, ValueError):
        # Older Pillow builds without libraqm cannot accept direction/language options.
        draw.text(xy, text, font=font, **kwargs)


def _wrap(text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _text_length(font, candidate) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _fit_lines(text: str, family: str, weight: int, max_width: int, max_height: int,
               start_size: int, min_size: int = 30) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    for size in range(start_size, min_size - 1, -2):
        font = _load_font(family, weight, size)
        lines = _wrap(text, font, max_width)
        spacing = int(size * 0.22)
        height = len(lines) * size + max(0, len(lines) - 1) * spacing
        if lines and max(_text_length(font, line) for line in lines) <= max_width and height <= max_height:
            return font, lines, spacing
    font = _load_font(family, weight, min_size)
    lines = _wrap(text, font, max_width)
    spacing = int(min_size * 0.2)
    height = len(lines) * min_size + max(0, len(lines) - 1) * spacing
    if not lines or max(_text_length(font, line) for line in lines) > max_width or height > max_height:
        raise ValueError("Title or subtitle is too long for the selected layout; shorten the copy.")
    return font, lines, spacing


def _cover_crop(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    width, height = size
    scale = max(width / image.width, height / image.height)
    resized = image.resize((math.ceil(image.width * scale), math.ceil(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _extract_frame(path: Path, at: float) -> Image.Image:
    src = _safe_input(path)
    if src.suffix.lower() in IMAGE_EXTS:
        with Image.open(src) as image:
            return image.convert("RGB")
    if src.suffix.lower() not in VIDEO_EXTS:
        raise ValueError(f"Unsupported input type: {src.suffix}")
    ffmpeg = os.environ.get("FFMPEG_BIN", "ffmpeg")
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", str(max(0.0, at)),
               "-i", str(src), "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode or not result.stdout:
        raise RuntimeError(f"Could not extract frame from {src}: {result.stderr.decode(errors='replace')}")
    from io import BytesIO
    return Image.open(BytesIO(result.stdout)).convert("RGB")


def _background(size: tuple[int, int], style: dict[str, Any], frame: Image.Image | None,
                colors: dict[str, tuple[int, int, int]]) -> Image.Image:
    width, height = size
    theme = style["theme"]
    top = colors["paper"] if theme == "light" else colors["ink"]
    bottom = colors["gray_1"] if theme == "light" else colors["ink_shadow"]
    if frame is not None:
        base = _cover_crop(frame, size).filter(ImageFilter.GaussianBlur(radius=max(12, width // 45)))
        base = ImageEnhance.Brightness(base).enhance(0.52 if theme == "dark" else 0.72)
        overlay = Image.new("RGBA", size, (*top, 112 if theme == "dark" else 72))
        base = Image.alpha_composite(base.convert("RGBA"), overlay)
    else:
        arr = np.zeros((height, width, 3), dtype=np.uint8)
        for y in range(height):
            t = y / max(1, height - 1)
            arr[y, :, :] = [round(top[c] * (1 - t) + bottom[c] * t) for c in range(3)]
        base = Image.fromarray(arr, "RGB").convert("RGBA")
    draw = ImageDraw.Draw(base, "RGBA")
    accent = colors["red"]
    if style["glow"]:
        glow = Image.new("RGBA", size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        radius = int(width * 0.52)
        cx, cy = int(width * 0.82), int(height * 0.20)
        for r in range(radius, 0, -max(3, radius // 40)):
            alpha = int(16 * (1 - r / radius))
            gd.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(*accent, alpha))
        base = Image.alpha_composite(base, glow)
        draw = ImageDraw.Draw(base, "RGBA")
    if style["grid"]:
        step = max(32, width // 18)
        line = (*colors["ink_soft"], 30) if theme == "dark" else (*colors["ink_soft"], 42)
        for x in range(0, width, step):
            draw.line((x, 0, x, height), fill=line, width=1)
        for y in range(0, height, step):
            draw.line((0, y, width, y), fill=line, width=1)
    return base


def _pose_image(slug: str | None, pose_file: Path | None) -> Image.Image | None:
    if pose_file is not None:
        path = _safe_input(pose_file)
    elif slug:
        poses = _read_json(POSES_PATH)["poses"]
        if slug not in poses:
            raise ValueError(f"Unknown pose {slug!r}; inspect assets/poses/poses.json")
        path = ROOT / "assets" / "poses" / poses[slug]["file"]
        if not path.is_file():
            raise FileNotFoundError(f"Pose asset is missing: {path}")
    else:
        return None
    with Image.open(path) as image:
        return image.convert("RGBA")


def _draw_copy(canvas: Image.Image, *, title: str, subtitle: str | None, eyebrow: str | None,
               style: dict[str, Any], colors: dict[str, tuple[int, int, int]],
               box: tuple[int, int, int, int], title_family: str | None = None) -> None:
    draw = ImageDraw.Draw(canvas)
    x0, y0, x1, y1 = box
    width, height = x1 - x0, y1 - y0
    arabic = _is_arabic(title)
    family = title_family or (style["font_ar"] if arabic else style["font_latin"])
    weight = int(style["weight"])
    if eyebrow:
        eyebrow_family = style["font_ar"] if _is_arabic(eyebrow) else style["font_latin"]
        eyebrow_font = _load_font(eyebrow_family, 600, max(22, int(width * 0.035)))
        eyebrow_color = colors["salmon"] if style["theme"] == "dark" else colors["red"]
        _draw_text(draw, (x1, y0), eyebrow.upper(), eyebrow_font, fill=eyebrow_color, anchor="ra")
        y0 += int(eyebrow_font.size * 1.9)
        height -= int(eyebrow_font.size * 1.9)
    title_font, lines, spacing = _fit_lines(title, family, weight, width, int(height * 0.72),
                                            int(width * 0.105), 32)
    line_height = title_font.size + spacing
    y = y0
    for line in lines:
        color = colors["paper"] if style["theme"] == "dark" else colors["ink"]
        _draw_text(draw, (x1, y), line, title_font, fill=color, anchor="ra")
        y += line_height
    accent_y = min(y + int(title_font.size * 0.34), y1 - 4)
    draw.rounded_rectangle((x1 - int(width * 0.22), accent_y, x1, accent_y + max(6, title_font.size // 16)),
                           radius=4, fill=colors["red"])
    if subtitle:
        sub_family = style["font_ar"] if _is_arabic(subtitle) else style["font_latin"]
        sy = accent_y + int(title_font.size * 0.72)
        available = y1 - sy
        sub_font, sub_lines, sub_spacing = _fit_lines(subtitle, sub_family, 600, width,
                                                       available, int(width * 0.043), 22)
        if len(sub_lines) > 2:
            raise ValueError("Subtitle must fit in two lines; shorten the supporting copy.")
        sub_color = colors["gray_4"] if style["theme"] == "dark" else colors["ink_soft"]
        for line in sub_lines:
            _draw_text(draw, (x1, sy), line, sub_font, fill=sub_color, anchor="ra")
            sy += sub_font.size + sub_spacing


def _place_pose(canvas: Image.Image, pose: Image.Image | None, *, mode: str) -> None:
    if pose is None:
        return
    width, height = canvas.size
    max_h = int(height * (0.43 if mode == "portrait" else 0.78))
    max_w = int(width * (0.48 if mode == "portrait" else 0.38))
    scale = min(max_w / pose.width, max_h / pose.height)
    resized = pose.resize((max(1, round(pose.width * scale)), max(1, round(pose.height * scale))),
                          Image.Resampling.LANCZOS)
    # Keep the complete transparent PNG inside the canvas; never crop the head or feet.
    x = width - resized.width - int(width * 0.055)
    y = height - resized.height - int(height * (0.045 if mode == "portrait" else 0.035))
    canvas.alpha_composite(resized, (max(0, x), max(0, y)))


def render_artwork(*, size: tuple[int, int], title: str, subtitle: str | None = None,
                   eyebrow: str | None = None, frame: Image.Image | None = None,
                   pose: Image.Image | None = None, style_name: str = "tech-editorial",
                   title_font: str | None = None) -> Image.Image:
    if style_name not in STYLES:
        raise ValueError(f"Unknown style {style_name!r}")
    if not title.strip():
        raise ValueError("A user-provided title is required; the tool never invents a title")
    style = STYLES[style_name]
    colors = palette()
    mode = "portrait" if size[1] > size[0] else "landscape"
    canvas = _background(size, style, frame, colors)
    width, height = size
    if mode == "portrait":
        box = (int(width * 0.08), int(height * 0.17), int(width * 0.91), int(height * (0.52 if pose else 0.70)))
    else:
        box = (int(width * 0.055), int(height * 0.16), int(width * (0.64 if pose else 0.93)),
               int(height * 0.78))
    _draw_copy(canvas, title=title.strip(), subtitle=subtitle.strip() if subtitle else None,
               eyebrow=eyebrow.strip() if eyebrow else None, style=style, colors=colors,
               box=box, title_family=title_font)
    _place_pose(canvas, pose, mode=mode)
    return canvas.convert("RGB")


def _reject_output_symlinks(paths: tuple[Path, ...]) -> None:
    """Reject pre-existing symlink targets before writing generated assets."""
    for path in paths:
        if path.is_symlink():
            raise ValueError(f"Refusing symlink output file: {path}")


def _safe_output_dir(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    current = absolute
    while current != current.parent:
        if current.is_symlink():
            raise ValueError(f"Refusing symlink output path: {current}")
        current = current.parent
    resolved = absolute.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("Output directory must stay inside the repository (for example cache/covers or projects/<slug>/out).") from exc
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def generate(args: argparse.Namespace) -> tuple[Path, Path]:
    out_dir = _safe_output_dir(Path(args.out_dir))
    frame = _extract_frame(Path(args.frame), args.at) if args.frame else None
    pose = _pose_image(args.pose, Path(args.pose_file) if args.pose_file else None)
    cover = render_artwork(size=(1080, 1920), title=args.title, subtitle=args.subtitle,
                           eyebrow=args.eyebrow, frame=frame, pose=pose, style_name=args.style,
                           title_font=args.font)
    thumb = render_artwork(size=(1280, 720), title=args.title, subtitle=args.subtitle,
                            eyebrow=args.eyebrow, frame=frame, pose=pose, style_name=args.style,
                            title_font=args.font)
    cover_path, thumb_path = out_dir / "cover-9x16.png", out_dir / "thumbnail-16x9.png"
    _reject_output_symlinks((cover_path, thumb_path))
    cover.save(cover_path, format="PNG", optimize=True)
    thumb.save(thumb_path, format="PNG", optimize=True)
    return cover_path, thumb_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a 9:16 reel cover and 16:9 thumbnail in Medo's locked brand.")
    parser.add_argument("--title", required=True, help="Exact user-approved title; no copy is invented.")
    parser.add_argument("--subtitle", help="Optional user-provided supporting line.")
    parser.add_argument("--eyebrow", help="Optional short label supplied by the user.")
    parser.add_argument("--frame", help="Optional local image/video used as a blurred background.")
    parser.add_argument("--at", type=float, default=0.0, help="Frame timestamp when --frame is a video.")
    parser.add_argument("--pose", help="Pose slug from assets/poses/poses.json.")
    parser.add_argument("--pose-file", help="Optional local transparent PNG; mutually exclusive with --pose.")
    parser.add_argument("--style", choices=sorted(STYLES), default="tech-editorial")
    parser.add_argument("--font", help="Optional family name from assets/fonts/fonts.json.")
    parser.add_argument("--out-dir", default="cache/covers")
    args = parser.parse_args()
    if args.pose and args.pose_file:
        parser.error("Use either --pose or --pose-file, not both.")
    if not math.isfinite(args.at) or args.at < 0:
        parser.error("--at must be a finite, non-negative timestamp.")
    try:
        cover, thumb = generate(args)
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        parser.error(str(exc))
    print(f"Cover: {cover}")
    print(f"Thumbnail: {thumb}")


if __name__ == "__main__":
    main()
