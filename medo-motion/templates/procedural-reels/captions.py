"""Word-by-word and phrase-chunk Arabic captions for engine P (unboxed, brand colors).

Word onsets/offsets are MEASURED (tools/caption_align.py); this module never
estimates timing. `style` is REQUIRED and must be an explicit, agent-chosen value
from plan/text-direction.json — there is no default look.
"""
from __future__ import annotations

import functools
import re

import cv2
import numpy as np

from arabic_shape import visual_word_order
from caption_motion import caption_transform, resolve_text_style
from lib import INK, RED, SCALE, WHITE, YEL, paste, text_sprite
from text_direction import font_for, text_style_for

try:
    import layout_p as _layout_p
except ImportError:  # pragma: no cover - standalone partial copy fallback
    _layout_p = None

ARABIC_GLUE_WORDS = frozenset({
    "في", "من", "على", "إلى", "الى", "عن", "مع", "كل", "مش", "ما", "لا",
    "لن", "لم", "إن", "أن", "ان", "لو", "يا", "ده", "دي", "اللي", "بس",
    "ولا", "أو", "او", "حتى", "عشان", "علشان", "لأن", "كان", "غير", "بين",
})
_HARD_PUNCT_RE = re.compile(r"[،؛.؟!,:;…]$")
_STRIP_DIACRITICS_RE = re.compile(r"[\u064B-\u065F\u0670\u0640]")
_STRIP_EDGE_PUNCT_RE = re.compile(r"^[^\w]+|[^\w]+$", re.UNICODE)


def _clean_glue_token(word: str) -> str:
    s = _STRIP_DIACRITICS_RE.sub("", str(word or ""))
    return _STRIP_EDGE_PUNCT_RE.sub("", s)


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, float(v)))


def _ease_out_cubic(u: float) -> float:
    x = _clamp01(u)
    return 1.0 - (1.0 - x) ** 3


def is_hidden_at(t: float, hide_ranges) -> bool:
    """Return True when `t` lies inside any hero-text suppression window."""
    if not hide_ranges or t is None:
        return False
    for r in hide_ranges:
        if isinstance(r, dict):
            s, e = r.get("start"), r.get("end")
        else:
            s, e = r[0], r[1]
        if s is not None and e is not None and float(s) <= t < float(e):
            return True
    return False


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


def group_caption_chunks(
    words,
    *,
    max_words: int = 4,
    max_gap: float = 0.45,
    max_duration: float = 2.2,
    hold_after: float = 0.35,
    bridge_gap: float = 0.28,
) -> list[dict]:
    """Group measured word timings into natural 2–4 word RTL phrase chunks.

    Never orphans Arabic prepositions/particles (`في`, `من`, `على`, `مش`, `اللي`...)
    at the end of a chunk unless forced by a pause > `max_gap` or terminal punctuation.
    """
    validate_word_timeline(words)
    if not words:
        return []
    cap = max(1, int(max_words))
    raw_chunks: list[list[dict]] = []
    cur: list[dict] = []

    for w in words:
        if not cur:
            cur.append(w)
            continue
        prev = cur[-1]
        gap = float(w["start"]) - float(prev["end"])
        span = float(w["end"]) - float(cur[0]["start"])
        prev_punct = bool(_HARD_PUNCT_RE.search(prev["text"].strip()))
        prev_is_glue = _clean_glue_token(prev["text"]) in ARABIC_GLUE_WORDS
        over_words = len(cur) >= cap
        hard_limit = len(cur) >= cap + 1

        should_split = False
        if gap > max_gap or prev_punct:
            should_split = True
        elif hard_limit or (span > max_duration and not prev_is_glue):
            should_split = True
        elif over_words and not prev_is_glue:
            should_split = True

        if should_split:
            raw_chunks.append(cur)
            cur = [w]
        else:
            cur.append(w)
    if cur:
        raw_chunks.append(cur)

    out: list[dict] = []
    for idx, group in enumerate(raw_chunks):
        start = float(group[0]["start"])
        last_end = float(group[-1]["end"])
        next_start = float(raw_chunks[idx + 1][0]["start"]) if idx + 1 < len(raw_chunks) else float("inf")
        gap_to_next = next_start - last_end
        end = next_start if gap_to_next <= bridge_gap else min(next_start, last_end + max(0.0, hold_after))
        out.append({
            "index": idx,
            "start": start,
            "spoken_end": last_end,
            "end": end,
            "text": " ".join(x["text"] for x in group),
            "words": list(group),
        })
    return out


def active_chunk_at(chunks, t):
    if not isinstance(chunks, (list, tuple)) or t is None:
        return None
    for c in chunks:
        if c["start"] <= t < c["end"]:
            return c
    return None


@functools.lru_cache(maxsize=512)
def _word_sprite(text, size, color, family=None, weight=800):
    return text_sprite(text, size, color, True, 6, INK, family, weight)


def _karaoke_sprite(text, size, p, theme, family=None, weight=800):
    base = _word_sprite(text, size, WHITE if theme == "dark" else INK, family, weight).copy()
    base[..., 3:4] *= 0.38
    acc = _word_sprite(text, size, YEL if theme == "dark" else RED, family, weight)
    h, w = base.shape[:2]
    # RTL sweep: the lit region grows from the right edge toward the left.
    xs = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :, None]
    pos = max(0.0, min(1.0, 1.0 - p))
    mask = np.clip((xs - (pos - 0.12)) / 0.24, 0.0, 1.0)
    return base * (1.0 - mask) + acc * mask


def draw_word_caption(fr, t, words, *, style, size=76, y=1455, color=WHITE,
                      accent=YEL, theme="dark", still=False, hide_ranges=None):
    """Draw the active spoken word, unboxed. Returns the word or None."""
    resolve_text_style(style)
    if is_hidden_at(t, hide_ranges):
        return None
    word = active_word_at(words, t)
    if word is None:
        return None
    elapsed = max(0.0, t - word["start"])
    dur = max(0.05, word["end"] - word["start"])
    raw_m = caption_transform(style, elapsed, dur)
    m = (
        {**raw_m, "x": 0.0, "y": 0.0, "scale": 1.0, "rotate": 0.0, "blur": 0.0, "opacity": _clamp01(elapsed / 0.12)}
        if still
        else raw_m
    )
    # The layout math stays in the design space (the buffer is scaled at the write boundary).
    cx = fr.shape[1] / SCALE / 2 + m["x"] * size
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
        col = accent if theme == "dark" else RED
        t_d = max(4, int(size * 0.07))
        cv2.line(fr, (int((cx + uw / 2) * SCALE), int(uy * SCALE)),
                 (int((cx - uw / 2) * SCALE), int(uy * SCALE)),
                 col, max(1, int(round(t_d * SCALE))), cv2.LINE_AA)
    return word


def draw_phrase_caption(
    fr,
    t: float,
    words_or_chunks,
    *,
    style: str,
    size: int = 58,
    y: float = 1455,
    color=WHITE,
    accent=YEL,
    theme: str = "dark",
    family: str | None = None,
    weight: int = 800,
    still: bool = False,
    hide_ranges=None,
    max_words: int = 4,
    max_gap: float = 0.45,
):
    """Draw a 2–4 word single-line RTL phrase caption, unboxed, highlighting the active word."""
    resolve_text_style(style)
    if is_hidden_at(t, hide_ranges) or not words_or_chunks:
        return None
    first = words_or_chunks[0]
    chunks = (
        words_or_chunks
        if isinstance(first, dict) and isinstance(first.get("words"), list)
        else group_caption_chunks(words_or_chunks, max_words=max_words, max_gap=max_gap)
    )
    chunk = active_chunk_at(chunks, t)
    if chunk is None:
        return None

    elapsed = max(0.0, t - chunk["start"])
    dur = max(0.08, chunk["end"] - chunk["start"])
    base_m = (
        {"x": 0.0, "y": 0.0, "scale": 1.0, "rotate": 0.0, "opacity": _clamp01(elapsed / 0.14)}
        if still
        else caption_transform(style, elapsed, dur)
    )

    acc_col = accent if theme == "dark" else RED
    space = max(size * 0.24, 14.0)
    prepared = []
    for idx, w in enumerate(chunk["words"]):
        is_active = w["start"] <= t < w["end"]
        spr = _word_sprite(w["text"], size, acc_col if is_active else color, family, weight)
        ink_w = max(8.0, float(spr.shape[1] - 12))
        prepared.append({
            **w,
            "logical_index": idx,
            "spr": spr,
            "ink_w": ink_w,
            "is_active": is_active,
            "is_spoken": t >= w["end"],
        })

    ordered = visual_word_order(prepared)
    total_w = sum(item["ink_w"] for item in ordered) + space * max(0, len(ordered) - 1)
    max_line_w = float(fr.shape[1] / SCALE - 80)
    fit_scale = min(1.0, max_line_w / total_w) if total_w > 0 else 1.0
    group_scale = (1.0 if still else (1.0 + (base_m["scale"] - 1.0) * 0.35)) * fit_scale

    line_cx = fr.shape[1] / SCALE / 2.0 + (0.0 if still else base_m["x"] * size * 0.4)
    line_cy = y + (0.0 if still else base_m["y"] * size * 0.4)
    right = (total_w * group_scale) / 2.0

    for item in ordered:
        w_scaled = item["ink_w"] * group_scale
        cx = line_cx + right - w_scaled / 2.0
        word_boost = (
            1.0 + 0.06 * _ease_out_cubic(_clamp01((t - item["start"]) / 0.12))
            if (not still and item["is_active"])
            else 1.0
        )
        final_scale = group_scale * word_boost
        alpha = base_m["opacity"] * (1.0 if (item["is_active"] or item["is_spoken"]) else 0.56)
        paste(fr, item["spr"], cx, line_cy, scale=final_scale, alpha=alpha)
        if _layout_p is not None and _layout_p.is_capturing():
            box = _layout_p.sprite_aabb(item["spr"], cx, line_cy, scale=final_scale)
            _layout_p.record_text(
                item["text"],
                box,
                box_id=f"caption-{chunk['index']}-{item['logical_index']}",
                zone="caption",
                alpha=alpha,
            )
        right -= w_scaled + space * group_scale
    return chunk


def draw_text_slot(
    fr,
    t: float,
    items,
    *,
    cx: float,
    cy: float,
    max_width: float = 900,
    size: int = 72,
    color=WHITE,
    family: str | None = None,
    weight: int = 800,
    transition_dur: float = 0.28,
    zone: str = "content",
    box_id: str = "slot",
):
    """Draw a vertical masked word-slot ticker (`items = [{'start': t0, 'text': '...'}, ...]`)."""
    if not items or t is None:
        return None
    active_idx = -1
    for i, item in enumerate(items):
        if t >= float(item["start"]):
            active_idx = i
    if active_idx < 0:
        return None

    cur = items[active_idx]
    prev = items[active_idx - 1] if active_idx > 0 else None
    u = _ease_out_cubic(_clamp01((t - float(cur["start"])) / max(0.05, transition_dur))) if prev else 1.0

    pad_top = size * 0.78
    pad_bot = size * 0.68
    slot_h = pad_top + pad_bot
    # Slot math stays in the design space; the masked save/restore regions follow the buffer.
    x0 = max(0, int(round(cx - max_width / 2)))
    x1 = min(fr.shape[1] / SCALE, int(round(cx + max_width / 2)))
    y0 = max(0, int(round(cy - pad_top)))
    y1 = min(fr.shape[0] / SCALE, int(round(cy + pad_bot)))
    if x1 <= x0 or y1 <= y0:
        return None

    dy0, dy1 = int(round(y0 * SCALE)), int(round(y1 * SCALE))
    saved_top = fr[:dy0].copy() if dy0 > 0 else None
    saved_bot = fr[dy1:].copy() if dy1 < fr.shape[0] else None

    if prev is not None and u < 1.0:
        prev_spr = _word_sprite(prev["text"], size, color, family, weight)
        prev_scale = min(1.0, max_width / max(1.0, float(prev_spr.shape[1])))
        paste(fr, prev_spr, cx, cy - u * slot_h * 0.82, scale=prev_scale, alpha=1.0 - u)

    cur_spr = _word_sprite(cur["text"], size, color, family, weight)
    cur_scale = min(1.0, max_width / max(1.0, float(cur_spr.shape[1])))
    cur_alpha = u if prev is not None else _clamp01((t - float(cur["start"])) / 0.16)
    cur_y = cy + (1.0 - u) * slot_h * 0.82 if prev is not None else cy
    paste(fr, cur_spr, cx, cur_y, scale=cur_scale, alpha=cur_alpha)

    if saved_top is not None:
        fr[:dy0] = saved_top
    if saved_bot is not None:
        fr[dy1:] = saved_bot

    if _layout_p is not None and _layout_p.is_capturing():
        raw_box = _layout_p.sprite_aabb(cur_spr, cx, cur_y, scale=cur_scale)
        clipped = {
            "x": max(float(x0), raw_box["x"]),
            "y": max(float(y0), raw_box["y"]),
            "w": max(1.0, min(float(x1), raw_box["x"] + raw_box["w"]) - max(float(x0), raw_box["x"])),
            "h": max(1.0, min(float(y1), raw_box["y"] + raw_box["h"]) - max(float(y0), raw_box["y"])),
        }
        _layout_p.record_text(cur["text"], clipped, box_id=box_id, zone=zone, alpha=cur_alpha)
    return cur


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
            col = accent if theme == "dark" else RED
            t_d = max(4, int(size * 0.07))
            cv2.line(fr, (int((x + uw / 2) * SCALE), int(uy * SCALE)),
                     (int((x - uw / 2) * SCALE), int(uy * SCALE)),
                     col, max(1, int(round(t_d * SCALE))), cv2.LINE_AA)
    return style
