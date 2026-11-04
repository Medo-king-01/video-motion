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
directional runs and laying them out RTL (preserving multi-word LTR phrases
per Unicode UAX #9 N1).

Also provides Unicode ArabicShaping-safe kashida stretching (`kashida_slots`,
`insert_kashida`, `stretch_kashida`), word-level `visual_word_order`, and
`fix_ruqaa_taa_marbuta` (see assets/CREDITS.md).

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
import re
import unicodedata

import numpy as np
from PIL import Image

try:
    import freetype
    import uharfbuzz as hb
except ImportError:  # pragma: no cover - RAQM-only installs still use pure-Unicode helpers
    freetype = None  # type: ignore[assignment]
    hb = None  # type: ignore[assignment]

__all__ = [
    'text_sprite', 'draw', 'measure', 'LAYOUT_NAME',
    'visual_word_order', 'kashida_slots', 'insert_kashida',
    'stretch_kashida', 'fix_ruqaa_taa_marbuta',
]

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

# Unicode ArabicShaping Joining_Type=D (dual-joining) vs Joining_Type=R (right-only).
DUAL_JOIN = frozenset(
    'بتثجحخسشصضطظعغفقكلمنهيئپچڤگکی'
)
RIGHT_JOIN = frozenset(
    'اأإآٱدذرزوؤةءىژ'
)
STRETCH_TEETH = frozenset('سشصض')
ALEF_FORMS = frozenset('اأإآٱ')
_HARAKAT_RANGES = ((0x064B, 0x065F), (0x0670, 0x0670), (0x06D6, 0x06ED))
_LATIN_OR_DIGIT_RE = re.compile(r'[A-Za-z0-9]')


def _is_harakat(ch: str) -> bool:
    cp = ord(ch)
    return any(a <= cp <= b for a, b in _HARAKAT_RANGES)


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

    Neutrals (spaces, punctuation) adjacent to an RTL run take `base_rtl` so the
    space between an Arabic word and an embedded number/Latin word lands on the
    correct side once reversed. Neutrals flanked on BOTH sides by strong LTR runs
    (e.g. `"Claude Code"`, `"DDR5 16GB"`, UAX #9 rule N1) resolve to LTR so
    multi-word English/number phrases stay in natural left-to-right order.
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
            rtl, neutral = base_rtl, True
        else:
            rtl, neutral = False, False
        if logical and logical[-1][1] == rtl and logical[-1][2] == neutral:
            logical[-1][0] += ch
        else:
            logical.append([ch, rtl, neutral])

    # UAX #9 N1: a neutral run flanked by two strong runs of the SAME opposite
    # direction adopts that direction and merges with its neighbours.
    merged: list[list] = []
    idx = 0
    while idx < len(logical):
        cur = logical[idx]
        if (
            cur[2]
            and merged
            and not merged[-1][2]
            and idx + 1 < len(logical)
            and not logical[idx + 1][2]
            and merged[-1][1] == logical[idx + 1][1]
        ):
            same_rtl = merged[-1][1]
            merged[-1][0] += cur[0] + logical[idx + 1][0]
            merged[-1][1] = same_rtl
            idx += 2
            continue
        merged.append([cur[0], cur[1], cur[2]])
        idx += 1

    visual = list(reversed(merged)) if base_rtl else merged
    return [(t, r) for t, r, _n in visual if t]


def _is_ltr_token(word: str) -> bool:
    return bool(_LATIN_OR_DIGIT_RE.search(word)) and not any(_is_arabic(ch) and not _is_number(ch) for ch in word)


def visual_word_order(words) -> list[dict]:
    """Order word tokens for right-to-left stepping while keeping contiguous
    multi-word LTR runs in natural left-to-right visual order on screen.
    Preserves `logical_index` so staggered entrances fire in spoken order.
    """
    items = []
    for idx, entry in enumerate(words):
        if isinstance(entry, str):
            items.append({'text': entry, 'logical_index': idx, 'ltr': _is_ltr_token(entry)})
        else:
            d = dict(entry)
            txt = str(d.get('text', ''))
            d.setdefault('logical_index', idx)
            d['ltr'] = _is_ltr_token(txt)
            items.append(d)
    out: list[dict] = []
    i = 0
    while i < len(items):
        if not items[i]['ltr']:
            out.append(items[i])
            i += 1
            continue
        j = i + 1
        while j < len(items) and items[j]['ltr']:
            j += 1
        for k in range(j - 1, i - 1, -1):
            out.append(items[k])
        i = j
    return out


def kashida_slots(word: str) -> list[dict]:
    """Return Unicode-safe tatweel (U+0640) insertion slots in `word`, ordered by priority.

    - Never inserts after right-only letters (ا أ إ آ د ذ ر ز و ؤ ة ء ى).
    - Never splits mandatory Lam+Alef ligatures (لا / لأ / لإ / لآ / لٱ).
    - Inserts AFTER any harakat/shadda cluster attached to the left-joining letter.
    """
    s = str(word)
    bases: list[tuple[str, int, int]] = []
    idx = 0
    while idx < len(s):
        ch = s[idx]
        if _is_harakat(ch) or ch in ('\u0640', '\u200d'):
            idx += 1
            continue
        after_harakat = idx + 1
        while after_harakat < len(s) and _is_harakat(s[after_harakat]):
            after_harakat += 1
        bases.append((ch, idx, after_harakat))
        idx = after_harakat

    slots: list[dict] = []
    for b in range(len(bases) - 1):
        cur_ch, _cur_i, insert_at = bases[b]
        nxt_ch, _nxt_i, _nxt_after = bases[b + 1]
        if cur_ch not in DUAL_JOIN:
            continue
        if not (nxt_ch in DUAL_JOIN or (nxt_ch in RIGHT_JOIN and nxt_ch != 'ء')):
            continue
        if cur_ch == 'ل' and nxt_ch in ALEF_FORMS:
            continue
        if cur_ch in STRETCH_TEETH:
            priority = 3
        elif b + 1 == len(bases) - 1:
            priority = 3
        elif b == 0:
            priority = 1
        else:
            priority = 2
        slots.append({'index': insert_at, 'priority': priority, 'order': b})
    slots.sort(key=lambda item: (-item['priority'], -item['order']))
    return slots


def insert_kashida(text: str, count: int = 1) -> str:
    """Deterministically insert `count` tatweels (U+0640) across valid Arabic connection slots."""
    n = max(0, int(count))
    if n == 0 or not text:
        return str(text)
    parts = re.split(r'(\s+)', str(text))
    candidates = []
    for pi, tok in enumerate(parts):
        if not tok or tok.isspace():
            continue
        slots = kashida_slots(tok)
        if slots:
            candidates.append({'part_index': pi, 'slots': slots, 'counts': [0] * len(slots)})
    if not candidates:
        return str(text)
    for k in range(n):
        wc = candidates[k % len(candidates)]
        slot_idx = (k // len(candidates)) % len(wc['slots'])
        wc['counts'][slot_idx] += 1
    for wc in candidates:
        edits = sorted(
            ((slot['index'], wc['counts'][si]) for si, slot in enumerate(wc['slots']) if wc['counts'][si] > 0),
            key=lambda pair: -pair[0],
        )
        word = parts[wc['part_index']]
        for pos, add in edits:
            word = word[:pos] + ('\u0640' * add) + word[pos:]
        parts[wc['part_index']] = word
    return ''.join(parts)


def stretch_kashida(
    font_path: str,
    text: str,
    size: int,
    target_width: float,
    *,
    max_tatweels: int = 16,
    max_scale_x: float = 1.06,
    stroke: int = 0,
    measure_fn=None,
) -> dict:
    """Measure and stretch `text` toward `target_width` using valid tatweels + gentle residual scale_x."""
    raw = str(text)
    width_of = measure_fn or (lambda s: float(measure(font_path, s, size, rtl=True, stroke=stroke)[0]))
    nat_w = float(width_of(raw))
    if target_width <= nat_w or nat_w <= 0:
        return {'text': raw, 'natural_width': nat_w, 'width': nat_w, 'scale_x': 1.0, 'tatweels': 0}
    best_text = raw
    best_w = nat_w
    best_c = 0
    for c in range(1, max_tatweels + 1):
        cand = insert_kashida(raw, c)
        if cand == best_text:
            break
        w = float(width_of(cand))
        if w <= target_width:
            best_text, best_w, best_c = cand, w, c
        else:
            break
    scale_x = min(max_scale_x, max(1.0, target_width / best_w)) if best_w > 0 else 1.0
    return {
        'text': best_text,
        'natural_width': nat_w,
        'width': best_w * scale_x,
        'scale_x': scale_x,
        'tatweels': best_c,
    }


def fix_ruqaa_taa_marbuta(text: str) -> str:
    """Insert ZWJ before isolated ة after a right-only letter for calligraphic Ruqaa faces."""
    s = str(text)
    out: list[str] = []
    for i, ch in enumerate(s):
        if ch == 'ة' and i > 0:
            p = i - 1
            while p >= 0 and _is_harakat(s[p]):
                p -= 1
            if p >= 0 and s[p] in RIGHT_JOIN and s[i - 1] != '\u200d':
                out.append('\u200d')
        out.append(ch)
    return ''.join(out)


# ---------------------------------------------------------------- shaping engine
@functools.lru_cache(maxsize=32)
def _font(path: str, size: int):
    if hb is None or freetype is None:
        raise RuntimeError('Arabic shaping backend missing: python -m pip install uharfbuzz freetype-py')
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
