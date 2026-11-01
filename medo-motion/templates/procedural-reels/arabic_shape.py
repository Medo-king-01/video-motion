"""Real Arabic shaping for the procedural engine (HarfBuzz + FreeType).

Why this file exists
--------------------
Pillow's RAQM layout engine is the preferred path (`lib.py` uses it when the
installed Pillow has it). Many Pillow wheels are built **without** libraqm, and
without it Pillow cannot join Arabic letters or set RTL runs: words come out as
isolated letters in the wrong order.

This module is the fallback. It shapes each run with HarfBuzz (real contextual
joining, ligatures, RTL ordering) and rasterises the resulting **glyph ids**
with FreeType. It is deliberately NOT `arabic_reshaper` + `python-bidi`:
no presentation-form faking, no per-letter drawing, words are never split.
Mixed Arabic + Latin + digits are handled by splitting the paragraph into
directional runs and laying them out RTL.

Public API (mirrors what lib.py needs)
--------------------------------------
    text_sprite(font_path, text, size, color, rtl, stroke, stroke_color)
        -> premultiplied RGBA float32 (h, w, 4), like lib.text_sprite
    draw(pil_image, xy, font_path, text, size, fill, rtl, anchor)
        -> draws onto a PIL image in place
    measure(font_path, text, size, rtl=..., stroke=0) -> (w, h)
"""
from __future__ import annotations

import functools
import unicodedata

import freetype
import numpy as np
import uharfbuzz as hb
from PIL import Image

__all__ = ['text_sprite', 'draw', 'measure', 'LAYOUT_NAME']

# ---------------------------------------------------------------- classification
ARABIC_RANGES = (
    (0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
)
# Arabic punctuation that belongs to the RTL run
ARABIC_PUNCT = set('،؛؟٪٫٬۔﴾﴿')
# Arabic-Indic digits read left-to-right inside an RTL paragraph
AN_DIGITS = ((0x0660, 0x0669), (0x06F0, 0x06F9))
# Explicit bidi controls travel with the neutral run, never with the words
BIDI_MARKS = frozenset('\u200e\u200f\u202a\u202b\u202c\u2066\u2067\u2068\u2069')
# Separators that belong INSIDE a number run: 25,000 / 12:30 / 3.5 / ٢٥٬٠٠٠
NUMBER_SEPARATORS = frozenset(',.:٬٫')


def _is_arabic(ch: str) -> bool:
    cp = ord(ch)
    if ch in ARABIC_PUNCT or ch == '\u200f':          # RLM
        return True
    return any(a <= cp <= b for a, b in ARABIC_RANGES)


def _is_number(ch: str) -> bool:
    cp = ord(ch)
    if ch.isdigit():
        return True
    return any(a <= cp <= b for a, b in AN_DIGITS)


def _is_neutral(ch: str) -> bool:
    if ch.isspace():
        return True
    if ch in BIDI_MARKS:
        return True
    cat = unicodedata.category(ch)
    return cat[0] in ('Z', 'P', 'S') and not _is_arabic(ch)


def _runs(text: str, base_rtl: bool) -> list[tuple[str, bool]]:
    """Split a paragraph into directional runs, returned in VISUAL order (L→R).

    Neutrals (spaces, punctuation) become their own runs with the base direction:
    that keeps the space between an Arabic word and an embedded number or Latin
    word on the correct side once the runs are reversed for RTL.
    """
    logical: list[list] = []            # [text, is_rtl, is_neutral]
    for i, ch in enumerate(text):
        prev_d = i > 0 and _is_number(text[i - 1])
        next_d = i + 1 < len(text) and _is_number(text[i + 1])
        if _is_arabic(ch) and not _is_number(ch):
            rtl, neutral = True, False
        elif ch in NUMBER_SEPARATORS and prev_d and next_d:
            rtl, neutral = False, False      # keep the number in one LTR run
        elif _is_neutral(ch):
            # Neutrals sit BETWEEN runs. Giving them the base direction keeps
            # spaces between an Arabic word and an embedded number/Latin word
            # on the correct side once the runs are reversed for RTL.
            rtl, neutral = base_rtl, True
        else:
            rtl, neutral = False, False
        if logical and logical[-1][1] == rtl and logical[-1][2] == neutral:
            logical[-1][0] += ch
        else:
            logical.append([ch, rtl, neutral])
    if base_rtl:
        visual = list(reversed(logical))
    else:
        visual = logical
    return [(t, r) for t, r, _n in visual if t]


# ---------------------------------------------------------------- shaping engine
@functools.lru_cache(maxsize=32)
def _font(path: str, size: int):
    with open(path, 'rb') as fh:
        data = fh.read()
    hb_face = hb.Face(data)
    hb_font = hb.Font(hb_face)
    upem = hb_face.upem
    hb_font.scale = (upem, upem)          # positions come back in font units
    ft = freetype.Face(path)
    ft.set_char_size(size * 64)           # size px at 72 dpi
    return hb_font, ft, upem


def _shape(text: str, hb_font, upem: int, size: int, rtl: bool):
    buf = hb.Buffer()
    buf.add_str(text)
    buf.direction = 'rtl' if rtl else 'ltr'
    buf.guess_segment_properties()
    if rtl:
        buf.script = 'Arab'
        buf.language = 'ar'
    hb.shape(hb_font, buf, {'kern': True, 'liga': True, 'calt': True})
    glyphs, pen = [], 0.0
    k = size / upem
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append((
            info.codepoint,
            pen + pos.x_offset * k,
            -pos.y_offset * k,
            pos.x_advance * k,
        ))
        pen += pos.x_advance * k
    return glyphs, pen


def _layout(font_path: str, text: str, size: int, rtl_para: bool):
    """Shape the paragraph. Returns (placements, width, ascender, descender)."""
    hb_font, ft, upem = _font(font_path, size)
    runs = _runs(text, rtl_para)
    x = 0.0
    placements = []
    for run_text, rtl in runs:
        glyphs, adv = _shape(run_text, hb_font, upem, size, rtl)
        for gid, gx, gy, _a in glyphs:
            placements.append((gid, x + gx, gy))
        x += adv
    asc = ft.size.ascender / 64.0
    desc = abs(ft.size.descender) / 64.0
    return placements, x, asc, desc, ft


def _mask(font_path: str, text: str, size: int, rtl: bool):
    """Rasterise to an L-coverage mask. Returns (mask, advance_width, asc, desc)."""
    placements, width, asc, desc, ft = _layout(font_path, text, size, rtl)
    pad = 3
    w = int(np.ceil(width)) + pad * 2
    h = int(np.ceil(asc + desc)) + pad * 2
    canvas = np.zeros((h, w), dtype=np.uint8)
    baseline = asc + pad
    for gid, gx, gy in placements:
        try:
            ft.load_glyph(int(gid), freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        except Exception:
            continue
        g = ft.glyph
        bm = g.bitmap
        if bm.width <= 0 or bm.rows <= 0:
            continue
        buf = np.array(bm.buffer, dtype=np.uint8).reshape(bm.rows, bm.pitch)[:, :bm.width]
        px = int(round(gx + g.bitmap_left)) + pad
        py = int(round(baseline - g.bitmap_top - gy))
        x0, y0 = max(px, 0), max(py, 0)
        x1, y1 = min(px + bm.width, w), min(py + bm.rows, h)
        if x1 <= x0 or y1 <= y0:
            continue
        src = buf[y0 - py:y1 - py, x0 - px:x1 - px]
        # glyph bitmaps are coverage masks: keep the strongest coverage
        np.maximum(canvas[y0:y1, x0:x1], src, out=canvas[y0:y1, x0:x1])
    return Image.fromarray(canvas, 'L'), width, asc, desc


def _compose(font_path, text, size, color, rtl, stroke, stroke_color, pad=0):
    """Colour the mask, add an outline layer behind it, optionally crop to ink."""
    if not text.strip():
        blank = Image.new('L', (max(1, int(size * 0.3)), max(1, size)), 0)
        img = Image.new('RGBA', blank.size, (0, 0, 0, 0))
        img.putalpha(blank)
        return img, 0, 0
    mask, width, asc, _desc = _mask(font_path, text, size, rtl)
    c = tuple(color[:3]) if isinstance(color, (tuple, list)) else (255, 255, 255)
    if stroke > 0:
        import cv2
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (stroke * 2 + 1, stroke * 2 + 1))
        dil = Image.fromarray(cv2.dilate(np.array(mask), k), 'L')
        sc = tuple(stroke_color[:3]) if isinstance(stroke_color, (tuple, list)) else (0, 0, 0)
        base = Image.new('RGBA', mask.size, sc + (0,))
        base.putalpha(dil)
        top = Image.new('RGBA', mask.size, c + (0,))
        top.putalpha(mask)
        img = Image.alpha_composite(base, top)
    else:
        img = Image.new('RGBA', mask.size, c + (0,))
        img.putalpha(mask)
    if pad:
        # Crop to the ink box: PIL's textbbox/textlength work on ink, and the
        # caption maths in scenes.py assumes a fixed 6px border.
        box = img.getbbox()
        if box:
            inked = img.crop(box)
            framed = Image.new('RGBA', (inked.width + pad * 2, inked.height + pad * 2), (0, 0, 0, 0))
            framed.alpha_composite(inked, (pad, pad))
            img = framed
    return img, width, asc


# ---------------------------------------------------------------- public API
LAYOUT_NAME = 'harfbuzz-fallback'


def text_sprite(font_path, text, size, color=(255, 255, 255), rtl=True,
                stroke=0, stroke_color=(0, 0, 0)):
    """Premultiplied RGBA float32 (h, w, 4) — drop-in for lib.text_sprite.

    Matches PIL semantics: ink-tight box plus a 6px (+stroke) border, so the
    existing caption maths (`shape[1]-12`) keeps working unchanged.
    """
    rgba, _, _ = _compose(font_path, text, size, color, rtl, stroke, stroke_color,
                          pad=6 + stroke)
    a = np.array(rgba).astype(np.float32)
    a[..., :3] *= a[..., 3:4] / 255.0
    return a


def measure(font_path, text, size, rtl=True, stroke=0):
    rgba, _, _ = _compose(font_path, text, size, (255, 255, 255), rtl, stroke, (0, 0, 0),
                          pad=6 + stroke)
    return rgba.size


def draw(img, xy, font_path, text, size, fill, rtl=False, anchor='mm'):
    """Draw shaped text onto a PIL RGBA image at xy using a Pillow-style anchor."""
    if not text:
        return
    color = tuple(fill[:3]) if isinstance(fill, (tuple, list)) else fill
    rgba, width, asc = _compose(font_path, text, size, color, rtl, 0, (0, 0, 0))
    w, h = rgba.size
    ax, ay = anchor[0], anchor[1]
    x = {'l': 0, 'm': w / 2, 'r': w}.get(ax, w / 2)
    # 'a' = ascender top, 'm' = middle, 's'/'b' = baseline-ish bottom
    y = {'a': 0, 't': 0, 'm': h / 2, 's': h, 'b': h}.get(ay, h / 2)
    img.alpha_composite(rgba, (int(round(xy[0] - x)), int(round(xy[1] - y))))
