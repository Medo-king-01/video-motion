"""Pure, frame-deterministic caption/text motion for engine P.

Mirrors templates/render/lib/caption-motion.js (engines K/R). Tests keep the
numbers in parity. No style is a default: the caller must pass an explicit,
agent-chosen style from plan/text-direction.json.
"""
from __future__ import annotations

import math

from caption_styles import CAPTION_ENTRANCES
from motion import keyframes

STYLE_ALIAS = {
    "fadeTilt": "fadetilt", "fadeTiltAlt": "fadetiltalt", "fadeTiltBlur": "fadetiltblur",
    "softFade": "softfade", "fadeDrop": "fadedrop", "fadeTiltScale": "fadetiltscale",
    "zoomPunch": "zoompunch", "wordPop": "wordpop", "impact": "impact", "elastic": "elastic",
    "rise": "slideup", "drop": "dropin", "beat": "beatpulse", "comic": "comic", "hookZoom": "hookzoom",
}
SPECIAL_STYLES = ("pop", "karaoke", "underline", "hormozi")


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


def _pop_scale(elapsed: float) -> float:
    return 0.94 + 0.06 * (1 - (1 - min(1.0, elapsed / 0.09)) ** 3)


def resolve_text_style(style) -> str:
    if not isinstance(style, str) or not style.strip():
        raise ValueError("Text style is required: the agent must choose a style per scene (plan/text-direction.json).")
    sid = STYLE_ALIAS.get(style, style)
    if sid in SPECIAL_STYLES or sid in CAPTION_ENTRANCES:
        return sid
    raise ValueError(f'Unknown text style "{style}". Choose from the caption-safe catalog (docs/text-animations.md).')


def caption_transform(style, elapsed: float, duration: float) -> dict:
    """Sample the chosen style. x/y/blur are font-relative em; rotate is degrees."""
    sid = resolve_text_style(style)
    dur = max(0.05, duration)
    opacity, x, y, rotate, scale, blur = 1.0, 0.0, 0.0, 0.0, 1.0, 0.0
    underline_p, karaoke_p = 0.0, -1.0

    if sid == "pop":
        scale = _pop_scale(elapsed)
    elif sid == "karaoke":
        karaoke_p = _clamp01(elapsed / max(0.15, dur * 0.7))
        scale = 1 + 0.08 * math.sin(_clamp01(elapsed / dur) * math.pi)
    elif sid == "underline":
        scale = _pop_scale(elapsed)
        underline_p = _clamp01(elapsed / max(0.2, dur * 0.8))
    else:
        preset = CAPTION_ENTRANCES["hormozipop"] if sid == "hormozi" else CAPTION_ENTRANCES[sid]
        t = min(elapsed, preset["enter"])
        v = {n: keyframes(tr, t) for n, tr in preset["tracks"].items()}
        opacity = v.get("word.opacity", 1.0)
        y = v.get("word.y", 0.0)
        x = v.get("word.x", 0.0)
        rotate = v.get("word.rotate", 0.0)
        scale = v.get("word.scale", 1.0)
        blur = v.get("word.blur", 0.0)
    return {"id": sid, "opacity": opacity, "x": x, "y": y, "rotate": rotate,
            "scale": scale, "blur": blur, "underlineP": underline_p, "karaokeP": karaoke_p}
