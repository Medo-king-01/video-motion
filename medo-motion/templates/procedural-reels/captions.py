"""Word-by-word Arabic captions for engine P (unboxed, brand colors).

Word onsets/offsets are MEASURED (tools/caption_align.py); this module never
estimates timing. `style` is REQUIRED and must be an explicit, agent-chosen value
from plan/text-direction.json — there is no default look.
"""
from __future__ import annotations

import functools

import cv2
import numpy as np

from caption_motion import caption_transform
from lib import INK, WHITE, YEL, paste, text_sprite
from text_direction import font_for, text_style_for

try:
    import layout_p as _layout_p
except ImportError:  # pragma: no cover - standalone partial copy fallback
    _layout_p = None


def active_word_at(words, t):
    if not isinstance(words, (list, tuple)) or t is None:
        return None
    for w in words:
        if w["start"] <= t < w["end"]:
            return w
    return None


def validate_word_timeline(words):
    if not isinstance(words, (list, tuple)):
        raise TypeError("Caption words must be a list")
    prev = 0.0
    for i, w in enumerate(words):
        if not isinstance(w.get("text"), str) or not w["text"].strip():
            raise ValueError(f"Word {i} has no text")
        s, e = float(w["start"]), float(w["end"])
        if s < 0 or e <= s:
            raise ValueError(f"Word {i} has invalid timing")
        if i and s < prev:
            raise ValueError(f"Word {i} overlaps or is out of order")
        prev = e
    return True


@functools.lru_cache(maxsize=512)
def _word_sprite(text, size, color, family=None, weight=800):
    return text_sprite(text, size, color, True, 6, INK, family, weight)


def _karaoke_sprite(text, size, p, theme, family=None, weight=800):
    base = _word_sprite(text, size, WHITE if theme == "dark" else INK, family, weight).copy()
    base[..., 3:4] *= 0.38
    acc = _word_sprite(text, size, YEL if theme == "dark" else (203, 39, 27), family, weight)
    h, w = base.shape[:2]
    # RTL sweep: the lit region grows from the right edge toward the left.
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    pos = max(0.0, min(1.0, 1.0 - p))
    mask = np.clip((xs - (pos - 0.12)) / 0.24, 0.0, 1.0)
    return base * (1.0 - mask) + acc * mask


def draw_word_caption(fr, t, words, *, style, size=76, y=1455, color=WHITE,
                      accent=YEL, theme="dark"):
    """Draw the active spoken word, unboxed. Returns the word or None."""
    word = active_word_at(words, t)
    if word is None:
        return None
    elapsed = max(0.0, t - word["start"])
    dur = max(0.05, word["end"] - word["start"])
    m = caption_transform(style, elapsed, dur)
    cx = fr.shape[1] / 2 + m["x"] * size
    cy = y + m["y"] * size

    if m["karaokeP"] >= 0:
        spr = _karaoke_sprite(word["text"], size, m["karaokeP"], theme)
    else:
        spr = _word_sprite(word["text"], size, color)
    if m["blur"] * size > 0.2:
        k = max(1, int(round(m["blur"] * size)) | 1)
        spr = cv2.GaussianBlur(spr, (k, k), 0)
    paste(fr, spr, cx, cy, scale=m["scale"], rot=m["rotate"], alpha=m["opacity"])
    if _layout_p is not None and _layout_p.is_capturing():
        box = _layout_p.sprite_aabb(spr, cx, cy, scale=m["scale"], rot=m["rotate"])
        _layout_p.record_text(
            word["text"], box,
            box_id=str(word.get("id") or f"caption@{word['start']:.2f}"),
            zone="caption", alpha=m["opacity"],
        )

    if m["underlineP"] > 0:
        tw = spr.shape[1] * m["scale"]
        uw = tw * m["underlineP"]
        uy = cy + size * 0.62 * m["scale"]
        col = accent if theme == "dark" else (203, 39, 27)
        cv2.line(fr, (int(cx + uw / 2), int(uy)), (int(cx - uw / 2), int(uy)),
                 col, max(4, int(size * 0.07)), cv2.LINE_AA)
    return word


def draw_directed_text(fr, text, *, direction, scene, role, element_id=None,
                       t, start, end, cx, cy, size=64, color=WHITE,
                       accent=YEL, theme="dark", rtl=True, stroke=0, zone=None):
    """Draw ANY on-screen text (title, keyword, number, CTA, label, UI) using the
    agent's explicit motion choice from plan/text-direction.json. `text` may be a
    string or a list of lines. There is no default style: a missing direction or
    role raises before anything is drawn.
    """
    style = text_style_for(direction, scene, role, element_id)
    font = font_for(direction, scene, role, element_id)
    family, weight = font["family"], font["weight"]
    lines = text.split("\n") if isinstance(text, str) else list(text)
    elapsed = max(0.0, t - start)
    dur = max(0.05, end - start)
    m = caption_transform(style, elapsed, dur)
    line_h = size * 1.35
    top = cy - (len(lines) - 1) * line_h / 2
    target_zone = zone or ("hud" if role == "hud" else "content")
    base_id = element_id or f"s{scene}-{role}"
    for i, line in enumerate(lines):
        if not line:
            continue
        y = top + i * line_h + m["y"] * size
        x = cx + m["x"] * size
        if m["karaokeP"] >= 0:
            spr = _karaoke_sprite(line, size, m["karaokeP"], theme, family, weight)
        else:
            spr = text_sprite(line, size, color, rtl, stroke, INK, family, weight)
        if m["blur"] * size > 0.2:
            k = max(1, int(round(m["blur"] * size)) | 1)
            spr = cv2.GaussianBlur(spr, (k, k), 0)
        paste(fr, spr, x, y, scale=m["scale"], rot=m["rotate"], alpha=m["opacity"])
        if _layout_p is not None and _layout_p.is_capturing():
            box = _layout_p.sprite_aabb(spr, x, y, scale=m["scale"], rot=m["rotate"])
            line_id = base_id if len(lines) == 1 else f"{base_id}#{i + 1}"
            _layout_p.record_text(line, box, box_id=line_id, zone=target_zone, alpha=m["opacity"])
        if m["underlineP"] > 0:
            tw = spr.shape[1] * m["scale"]
            uw = tw * m["underlineP"]
            uy = y + size * 0.62 * m["scale"]
            col = accent if theme == "dark" else (203, 39, 27)
            cv2.line(fr, (int(x + uw / 2), int(uy)), (int(x - uw / 2), int(uy)),
                     col, max(4, int(size * 0.07)), cv2.LINE_AA)
    return style
