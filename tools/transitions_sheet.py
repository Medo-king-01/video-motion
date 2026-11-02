#!/usr/bin/env python3
"""Render the transition catalogue: a contact sheet and an optional motion preview.

    python3 tools/transitions_sheet.py                       # cache/transitions-sheet.png
    python3 tools/transitions_sheet.py --video cache/transitions.mp4
    python3 tools/transitions_sheet.py --only wipe,iris --cols 2

Both frames are drawn with the brand palette (palette v2 only) and go through
`templates/procedural-reels/transition.py` — the same geometry engine K draws, so what you see here
is what the Canvas renderer produces at the same progress.
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
P_DIR = ROOT / "medo-motion" / "templates" / "procedural-reels"
sys.path.insert(0, str(P_DIR))

from transition import NAMES, composite, sfx_for  # noqa: E402

W, H = 1080, 1920
RED, RED_DEEP, INK, INK_SOFT = (203, 39, 27), (159, 8, 3), (10, 10, 10), (113, 113, 122)
PAPER, GRAY_2, GRAY_4, SHADOW = (243, 242, 241), (201, 197, 194), (163, 162, 160), (3, 3, 3)
SALMON, BLUSH = (217, 127, 104), (213, 174, 166)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    pat = "**/Cairo*ExtraBold*.ttf" if bold else "**/Cairo*Regular*.ttf"
    found = sorted(glob.glob(str(ROOT / "assets" / "fonts" / pat), recursive=True))
    if found:
        return ImageFont.truetype(found[0], size)
    return ImageFont.load_default()


def frame_a() -> np.ndarray:
    """Outgoing scene: dark, ink gradient, red bar, a big 'A'."""
    yy = np.linspace(0, 1, H)[:, None, None]
    img = np.repeat(np.array(INK, np.float32) * (1 - yy) + np.array(SHADOW, np.float32) * yy, W, 1)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 700, W - 90, 1220), 36, fill=INK, outline=RED, width=6)
    d.text((W // 2, 900), "A", font=_font(220, True), fill=PAPER, anchor="mm")
    d.text((W // 2, 1120), "outgoing scene", font=_font(52), fill=GRAY_4, anchor="mm")
    d.rectangle((90, 1300, 990, 1316), fill=RED)
    return np.asarray(im)


def frame_b() -> np.ndarray:
    """Incoming scene: paper, red circle, ink 'B'."""
    yy = np.linspace(0, 1, H)[:, None, None]
    img = np.repeat(np.array(PAPER, np.float32) * (1 - yy) + np.array(GRAY_2, np.float32) * yy, W, 1)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.ellipse((140, 560, W - 140, 560 + (W - 280)), fill=RED)
    d.text((W // 2, 560 + (W - 280) // 2), "B", font=_font(220, True), fill=PAPER, anchor="mm")
    d.text((W // 2, 1560), "incoming scene", font=_font(56), fill=INK_SOFT, anchor="mm")
    d.rectangle((90, 1300, 990, 1316), fill=BLUSH)
    return np.asarray(im)


def _thumb(arr: np.ndarray, w: int, h: int) -> Image.Image:
    return Image.fromarray(arr).resize((w, h), Image.LANCZOS)


def contact_sheet(names: list[str], out: Path, cols: int = 7, p: float = 0.45) -> Path:
    a, b = frame_a(), frame_b()
    cw = 150
    ch = int(cw * H / W)
    pad, label_h = 12, 26
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (cw + pad) + pad, rows * (ch + label_h + pad) + pad + 34), SHADOW)
    d = ImageDraw.Draw(sheet)
    d.text((pad, 8), f"transitions @ p={p:g} — engine P geometry, identical to engine K", font=_font(18), fill=GRAY_2)
    for i, name in enumerate(names):
        r, c = divmod(i, cols)
        x = pad + c * (cw + pad)
        y = 34 + pad + r * (ch + label_h + pad)
        sheet.paste(_thumb(composite(a, b, name, p), cw, ch), (x, y))
        d.rectangle((x, y, x + cw - 1, y + ch - 1), outline=(90, 74, 73))
        d.text((x, y + ch + 5), f"{name} · {sfx_for(name)}", font=_font(15), fill=GRAY_4)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def video(names: list[str], out: Path, hold: float = 0.25, trans: float = 0.6, fps: int = 30,
          width: int = 540, with_sfx: bool = True) -> Path:
    """Preview clip of every transition, cut to the sound each one declares in transitions.json."""
    ff = os.environ.get("FFMPEG_BIN") or "ffmpeg"
    h = int(width * H / W)
    a = np.asarray(Image.fromarray(frame_a()).resize((width, h), Image.LANCZOS))
    b = np.asarray(Image.fromarray(frame_b()).resize((width, h), Image.LANCZOS))
    tmp = out.parent / "_tr_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    for f in tmp.glob("*.jpg"):
        f.unlink()
    n, cuts = 0, []
    for name in names:
        cuts.append({"t": n / fps + hold * 0.5, "name": name})
        for _ in range(int(hold * fps)):
            Image.fromarray(a).save(tmp / f"{n:05d}.jpg", quality=88)
            n += 1
        steps = int(trans * fps)
        for i in range(steps):
            Image.fromarray(composite(a, b, name, i / (steps - 1))).save(tmp / f"{n:05d}.jpg", quality=88)
            n += 1
    audio = None
    if with_sfx:
        sys.path.insert(0, str(P_DIR))
        import sfx  # noqa: PLC0415

        cues = sfx.cues_for_transitions(cuts, gain=0.9, pan=(0.5, -0.5))
        bus = sfx.bus(n / fps + 0.5, cues)
        peak = float(np.max(np.abs(bus))) or 1.0
        audio = tmp / "sfx.wav"
        sfx.write_wav(audio, bus / peak * 0.7)
    cmd = [ff, "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(tmp / "%05d.jpg")]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += [str(out)]
    subprocess.run(cmd, check=True)
    for f in tmp.glob("*"):
        f.unlink()
    tmp.rmdir()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "cache" / "transitions-sheet.png"))
    ap.add_argument("--video", nargs="?", const=str(ROOT / "cache" / "transitions.mp4"), default=None)
    ap.add_argument("--only", help="comma separated names")
    ap.add_argument("--cols", type=int, default=7)
    ap.add_argument("--p", type=float, default=0.45, help="progress shown in the sheet")
    ap.add_argument("--no-sfx", action="store_true", help="silent preview clip")
    args = ap.parse_args()

    names = [n.strip() for n in args.only.split(",")] if args.only else list(NAMES)
    unknown = [n for n in names if n not in NAMES]
    if unknown:
        print(f"unknown transition(s): {', '.join(unknown)}\nknown: {', '.join(NAMES)}")
        return 2
    sheet = contact_sheet(names, Path(args.out), cols=args.cols, p=args.p)
    print(f"sheet -> {sheet}  ({len(names)} transitions)")
    if args.video:
        v = video(names, Path(args.video), with_sfx=not args.no_sfx)
        print(f"video -> {v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
