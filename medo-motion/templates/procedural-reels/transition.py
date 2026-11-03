"""Transitions for engine P — the same geometry both engines rasterise.

A transition is a pure function of progress: `layer("wipe", p)` returns the mask/transform for that
instant, and `composite(a, b, "wipe", p)` applies it to two RGB frames. Frames stay exact at any fps,
which is what lets a 0.5 s transition be rendered as 15 deterministic frames.

Geometry is normalised (x/w in units of frame width, y/h of frame height, circle radius of width), so
`medo-motion/motion/transitions.json` describes exactly what engine K (`lib/transition.js`) draws.
Kinds and names are inspired by the MIT gl-transitions collection (https://gl-transitions.com); the
maths here is vector/CPU, not a shader, so there is no GPU or timing dependency.

    from transition import composite, layer, TRANSITIONS
    frame = composite(frame_a, frame_b, "wipe", 0.4)
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

try:  # same import trick as the rest of the template: works inside a project or from the skill
    from motion import ease
except ImportError:  # pragma: no cover
    from .motion import ease  # type: ignore

SPEC_PATH = Path(__file__).resolve().parents[2] / "motion" / "transitions.json"

# Embedded copy so a project (which only receives the templates/) behaves identically to the studio.
# tests/test_transitions.py fails if this drifts from medo-motion/motion/transitions.json.
EMBEDDED = {
    "wipe": {"kind": "reveal", "ease": "easeInOut", "sfx": "whoosh", "params": {"dir": "right"}},
    "wipeUp": {"kind": "reveal", "ease": "easeInOut", "sfx": "whoosh", "params": {"dir": "up"}},
    "diagonal": {"kind": "reveal", "ease": "easeInOut", "sfx": "swipe", "params": {"dir": "diagonal", "cols": 12}},
    "iris": {"kind": "circle", "ease": "backOut", "sfx": "pop", "params": {}},
    "irisClose": {"kind": "circle", "ease": "easeInOut", "sfx": "whoosh", "params": {"mode": "close"}},
    "slide": {"kind": "slide", "ease": "easeInOut", "sfx": "swipe", "params": {"push": True}},
    "cover": {"kind": "slide", "ease": "expoOut", "sfx": "swipe", "params": {"push": False}},
    "blinds": {"kind": "blinds", "ease": "easeInOut", "sfx": "tick", "params": {"bars": 8}},
    "checker": {"kind": "checker", "ease": "easeInOut", "sfx": "pop", "params": {"cols": 6, "rows": 10}},
    "bands": {"kind": "bands", "ease": "easeInOut", "sfx": "whoosh", "params": {"bands": 6}},
    "dissolve": {"kind": "fade", "ease": "linear", "sfx": "noise", "params": {}},
    "zoom": {"kind": "zoom", "ease": "expoOut", "sfx": "whoosh", "params": {}},
    "glitch": {"kind": "slices", "ease": "linear", "sfx": "glitch", "params": {"slices": 12}},
    "flash": {"kind": "flash", "ease": "easeInOut", "sfx": "impact", "params": {}},
}


def _load() -> dict:
    try:
        return json.loads(SPEC_PATH.read_text(encoding="utf-8"))["transitions"]
    except (OSError, KeyError, json.JSONDecodeError):
        return EMBEDDED


TRANSITIONS = _load()
NAMES = list(EMBEDDED)


def hash01(i: int) -> float:
    """Deterministic 0..1 hash — identical in JS (no RNG state, no drift between engines)."""
    return ((i * 1103515245 + 12345) % 2147483647) / 2147483647.0


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if v < lo else hi if v > hi else v


def _rect(x: float, y: float, w: float, h: float, dx: float = 0.0, dy: float = 0.0) -> dict:
    return {"x": x, "y": y, "w": w, "h": h, "dx": dx, "dy": dy}


# Kinds that paint the incoming frame through a mask. An empty mask means "nothing revealed
# yet", never "blend everything" — that distinction is what keeps a masked transition exact.
MASKED_KINDS = frozenset({"reveal", "circle", "slide", "blinds", "checker", "bands", "slices"})

# Fraction of the progress window each slat/cell/band may start late. Kept here so the
# stagger is visible in one place instead of being buried in the geometry.
_BLINDS_STAGGER = 0.35
_CHECKER_STAGGER = 0.5
_CHECKER_RAMP = 0.2
_CHECKER_LEAD = 0.8
_BANDS_STAGGER = 0.05
_BANDS_RAMP = 0.7
_DIAGONAL_STAGGER = 0.5
_DIAGONAL_OVERSHOOT = 1.5
_IRIS_RADIUS = 1.7
_ZOOM_FROM = 1.12
_ZOOM_RANGE = 0.12
_GLITCH_LEAD = 1.15
_GLITCH_JITTER = 0.22
_FLASH_HALF = 0.5
_FLASH_PEAK = 0.85
_PAPER = (243, 242, 241)


def _layer_state(name: str, kind: str) -> dict:
    """The neutral description every transition starts from and then fills in."""
    return {"name": name, "p": 0.0, "rects": [], "circles": [], "alpha": 1.0, "scaleB": 1.0,
            "aDx": 0.0, "aDy": 0.0, "invert": False, "paperFlash": 0.0,
            "masked": kind in MASKED_KINDS}


def _build_reveal(out: dict, e: float, prm: dict) -> None:
    """Wipe in one direction: a full-height band, a bottom-up band, or a column stagger."""
    direction = prm.get("dir", "right")
    if direction == "up":
        out["rects"] = [_rect(0.0, 1.0 - e, 1.0, e)]
        return
    if direction != "diagonal":
        out["rects"] = [_rect(0.0, 0.0, e, 1.0)]
        return
    cols = int(prm.get("cols", 12))
    for i in range(cols):
        height = _clamp(e * _DIAGONAL_OVERSHOOT - (i / cols) * _DIAGONAL_STAGGER)
        if height > 0:
            out["rects"].append(_rect(i / cols, 0.0, 1.0 / cols, height))


def _build_circle(out: dict, e: float, prm: dict) -> None:
    out["circles"] = [{"cx": 0.5, "cy": 0.5, "r": e * _IRIS_RADIUS, "dx": 0.0, "dy": 0.0}]
    out["invert"] = prm.get("mode") == "close"


def _build_slide(out: dict, e: float, prm: dict) -> None:
    # The incoming frame only exists where it has arrived; the rest keeps the outgoing frame.
    out["rects"] = [_rect(1.0 - e, 0.0, e, 1.0, dx=1.0 - e)]
    out["aDx"] = -e if prm.get("push", True) else 0.0


def _build_blinds(out: dict, e: float, prm: dict) -> None:
    """Vertical slats opening from alternating top/bottom edges (bands is the horizontal cousin)."""
    bars = int(prm.get("bars", 8))
    width = 1.0 / bars
    for i in range(bars):
        delay = (i / bars) * _BLINDS_STAGGER
        height = _clamp((e - delay) / (1.0 - delay))
        if height > 0:
            y = 0.0 if i % 2 == 0 else 1.0 - height
            out["rects"].append(_rect(i * width, y, width, height))


def _build_checker(out: dict, e: float, prm: dict) -> None:
    cols, rows = int(prm.get("cols", 6)), int(prm.get("rows", 10))
    for row in range(rows):
        for col in range(cols):
            delay = (col / cols) * _CHECKER_STAGGER + (row / rows) * _CHECKER_STAGGER
            cell = _clamp((e - delay * _CHECKER_LEAD) / _CHECKER_RAMP)
            if cell > 0:
                out["rects"].append(_rect(col / cols, row / rows, cell / cols, 1.0 / rows))


def _build_bands(out: dict, e: float, prm: dict) -> None:
    bands = int(prm.get("bands", 6))
    height = 1.0 / bands
    for i in range(bands):
        width = _clamp((e - i * _BANDS_STAGGER) / _BANDS_RAMP)
        if width > 0:
            x = 0.0 if i % 2 == 0 else 1.0 - width
            out["rects"].append(_rect(x, i * height, width, height))


def _build_fade(out: dict, e: float, prm: dict) -> None:
    out["alpha"] = e


def _build_zoom(out: dict, e: float, prm: dict) -> None:
    out["alpha"] = e
    out["scaleB"] = _ZOOM_FROM - _ZOOM_RANGE * e


def _build_slices(out: dict, e: float, prm: dict) -> None:
    """Deterministic glitch: horizontal slices arrive in a hashed order with a shrinking jitter."""
    count = int(prm.get("slices", 12))
    height = 1.0 / count
    for i in range(count):
        if e * _GLITCH_LEAD <= hash01(i) * 0.9:
            continue
        jitter = (hash01(i + 977) - 0.5) * _GLITCH_JITTER * (1.0 - e)
        out["rects"].append(_rect(0.0, i * height, 1.0, height, dx=jitter))


def _build_flash(out: dict, e: float, prm: dict) -> None:
    out["alpha"] = 1.0 if e > _FLASH_HALF else 0.0
    out["paperFlash"] = math.sin(math.pi * e) * _FLASH_PEAK


# One entry per `kind` in motion/transitions.json. Adding a transition kind = adding a builder
# plus its spec; `layer()` never grows again.
_KIND_BUILDERS = {
    "reveal": _build_reveal,
    "circle": _build_circle,
    "slide": _build_slide,
    "blinds": _build_blinds,
    "checker": _build_checker,
    "bands": _build_bands,
    "fade": _build_fade,
    "zoom": _build_zoom,
    "slices": _build_slices,
    "flash": _build_flash,
}


def layer(name: str, p: float) -> dict:
    """Mask + transform for `name` at raw progress `p` (0 → outgoing frame, 1 → incoming)."""
    spec = TRANSITIONS.get(name) or TRANSITIONS.get("wipe") or {"kind": "reveal", "ease": "easeInOut", "params": {}}
    kind = spec.get("kind", "reveal")
    builder = _KIND_BUILDERS.get(kind)
    if builder is None:  # an unknown kind is a catalogue bug, not something to render silently
        raise ValueError(f"transition {name!r}: unknown kind {kind!r} — known: {sorted(_KIND_BUILDERS)}")
    out = _layer_state(name, kind)
    eased = ease(spec.get("ease", "easeInOut"), _clamp(p))
    out["p"] = eased
    builder(out, eased, spec.get("params") or {})
    return out


def _shift(img: np.ndarray, dx: float, dy: float) -> np.ndarray:
    """Translate with edge repeat (no wrap-around artefacts)."""
    if dx == 0 and dy == 0:
        return img
    h, w = img.shape[:2]
    sx, sy = int(round(dx * w)), int(round(dy * h))
    out = np.empty_like(img)
    xs = np.clip(np.arange(w) - sx, 0, w - 1)
    ys = np.clip(np.arange(h) - sy, 0, h - 1)
    out[:] = img[ys][:, xs]
    return out


def _scale(img: np.ndarray, s: float) -> np.ndarray:
    if s == 1.0:
        return img
    try:
        import cv2  # noqa: PLC0415

        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
        return cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    except ImportError:  # pragma: no cover
        from PIL import Image  # noqa: PLC0415

        h, w = img.shape[:2]
        im = Image.fromarray(img).resize((int(w * s), int(h * s)), Image.LANCZOS)
        ox, oy = (im.width - w) // 2, (im.height - h) // 2
        return np.asarray(im.crop((ox, oy, ox + w, oy + h)))


def _mask(lay: dict, w: int, h: int) -> np.ndarray:
    m = np.zeros((h, w), np.float32)
    for r in lay["rects"]:
        x0 = max(0, int(round(r["x"] * w)))
        x1 = min(w, int(round((r["x"] + r["w"]) * w)))
        y0 = max(0, int(round(r["y"] * h)))
        y1 = min(h, int(round((r["y"] + r["h"]) * h)))
        if x1 > x0 and y1 > y0:
            m[y0:y1, x0:x1] = 1.0
    if lay["circles"]:
        yy, xx = np.mgrid[0:h, 0:w]
        for c in lay["circles"]:
            r = c["r"] * w
            if r <= 0:
                continue
            disk = ((xx - c["cx"] * w) ** 2 + (yy - c["cy"] * h) ** 2) <= r * r
            m[disk] = 1.0
    if lay["invert"]:
        m = 1.0 - m
    return m


def _blend(base: np.ndarray, incoming: np.ndarray, coverage: np.ndarray, alpha: float) -> np.ndarray:
    """Lay `incoming` over `base` where `coverage` is set, at the layer's global `alpha`."""
    weight = coverage[..., None] * alpha
    return base * (1.0 - weight) + incoming * weight


def _composite_masked(out_a: np.ndarray, bimg: np.ndarray, lay: dict, w: int, h: int) -> np.ndarray:
    """Apply each rect/circle mask separately, so the incoming frame can shift per shape."""
    out = out_a
    full = _mask({"rects": [{"x": 0, "y": 0, "w": 1, "h": 1}], "circles": [], "invert": False}, w, h)
    for rect in lay["rects"]:
        local = _mask({"rects": [rect], "circles": [], "invert": False}, w, h)
        if lay["invert"]:
            local = full - local
        source = _shift(bimg, rect["dx"], rect["dy"]) if (rect["dx"] or rect["dy"]) else bimg
        out = _blend(out, source.astype(np.float32), local > 0, lay["alpha"])
    if lay["circles"]:
        coverage = _mask({"rects": [], "circles": lay["circles"], "invert": lay["invert"]}, w, h)
        out = _blend(out, bimg.astype(np.float32), coverage, lay["alpha"])
    return out


def composite(a: np.ndarray, b: np.ndarray, name: str, p: float) -> np.ndarray:
    """Blend frame `a` into frame `b` through transition `name` at progress `p`."""
    lay = layer(name, p)
    h, w = a.shape[:2]
    out_a = a.astype(np.float32)
    if lay["aDx"] or lay["aDy"]:
        out_a = _shift(a, lay["aDx"], lay["aDy"]).astype(np.float32)

    bimg = _scale(b, lay["scaleB"])
    if lay["masked"]:
        out = _composite_masked(out_a, bimg, lay, w, h)
    else:
        alpha = lay["alpha"]
        out = out_a * (1.0 - alpha) + bimg.astype(np.float32) * alpha

    flash = lay["paperFlash"]
    if flash:
        out = out * (1.0 - flash) + np.array(_PAPER, np.float32) * flash
    return np.clip(out, 0, 255).astype(np.uint8)


def duration(name: str, default: float = 0.5) -> float:
    return float((TRANSITIONS.get(name) or {}).get("duration", default))


def sfx_for(name: str) -> str | None:
    """The sound the catalogue pairs with this transition (used by the audio kit)."""
    return (TRANSITIONS.get(name) or {}).get("sfx")
