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


def layer(name: str, p: float) -> dict:
    """Mask + transform for `name` at raw progress `p` (0 → outgoing frame, 1 → incoming)."""
    spec = TRANSITIONS.get(name) or TRANSITIONS.get("wipe") or {"kind": "reveal", "ease": "easeInOut", "params": {}}
    e = ease(spec.get("ease", "easeInOut"), _clamp(p))
    kind = spec.get("kind", "reveal")
    prm = spec.get("params") or {}
    out = {"name": name, "p": e, "rects": [], "circles": [], "alpha": 1.0, "scaleB": 1.0,
           "aDx": 0.0, "aDy": 0.0, "invert": False, "paperFlash": 0.0,
           # a masked transition with an empty mask means "nothing revealed yet", not "blend all"
           "masked": kind in {"reveal", "circle", "slide", "blinds", "checker", "bands", "slices"}}

    if kind == "reveal":
        direction = prm.get("dir", "right")
        cols = int(prm.get("cols", 12))
        if direction == "up":
            out["rects"] = [_rect(0.0, 1.0 - e, 1.0, e)]
        elif direction == "diagonal":
            for i in range(cols):
                h = _clamp(e * 1.5 - (i / cols) * 0.5)
                if h > 0:
                    out["rects"].append(_rect(i / cols, 0.0, 1.0 / cols, h))
        else:
            out["rects"] = [_rect(0.0, 0.0, e, 1.0)]

    elif kind == "circle":
        r = e * 1.7
        out["circles"] = [{"cx": 0.5, "cy": 0.5, "r": r, "dx": 0.0, "dy": 0.0}]
        out["invert"] = prm.get("mode") == "close"

    elif kind == "slide":
        # the incoming frame only exists where it has arrived; the rest keeps the outgoing frame
        out["rects"] = [_rect(1.0 - e, 0.0, e, 1.0, dx=1.0 - e)]
        out["aDx"] = -e if prm.get("push", True) else 0.0

    elif kind == "blinds":
        # vertical slats opening from alternating top/bottom edges (bands is the horizontal cousin)
        bars = int(prm.get("bars", 8))
        wid = 1.0 / bars
        for i in range(bars):
            start = (i / bars) * 0.35
            h = _clamp((e - start) / (1.0 - start))
            if h > 0:
                y = 0.0 if i % 2 == 0 else 1.0 - h
                out["rects"].append(_rect(i * wid, y, wid, h))

    elif kind == "checker":
        cols, rows = int(prm.get("cols", 6)), int(prm.get("rows", 10))
        for j in range(rows):
            for i in range(cols):
                delay = (i / cols) * 0.5 + (j / rows) * 0.5
                u = _clamp((e - delay * 0.8) / 0.2)
                if u > 0:
                    out["rects"].append(_rect(i / cols, j / rows, u / cols, 1.0 / rows))

    elif kind == "bands":
        bands = int(prm.get("bands", 6))
        hgt = 1.0 / bands
        for i in range(bands):
            w = _clamp((e - i * 0.05) / 0.7)
            if w > 0:
                x = 0.0 if i % 2 == 0 else 1.0 - w
                out["rects"].append(_rect(x, i * hgt, w, hgt))

    elif kind == "fade":
        out["alpha"] = e

    elif kind == "zoom":
        out["alpha"] = e
        out["scaleB"] = 1.12 - 0.12 * e

    elif kind == "slices":
        n = int(prm.get("slices", 12))
        hgt = 1.0 / n
        for i in range(n):
            if e * 1.15 > hash01(i) * 0.9:
                jitter = (hash01(i + 977) - 0.5) * 0.22 * (1.0 - e)
                out["rects"].append(_rect(0.0, i * hgt, 1.0, hgt, dx=jitter))

    elif kind == "flash":
        out["alpha"] = 1.0 if e > 0.5 else 0.0
        out["paperFlash"] = math.sin(math.pi * e) * 0.85

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


def composite(a: np.ndarray, b: np.ndarray, name: str, p: float) -> np.ndarray:
    """Blend frame `a` into frame `b` through transition `name` at progress `p`."""
    lay = layer(name, p)
    h, w = a.shape[:2]
    out_a = a.astype(np.float32)
    if lay["aDx"] or lay["aDy"]:
        out_a = _shift(out_a.astype(np.uint8), lay["aDx"], lay["aDy"]).astype(np.float32)

    bimg = _scale(b.astype(np.uint8), lay["scaleB"])
    if not lay["masked"]:
        alpha = lay["alpha"]
        out = out_a * (1.0 - alpha) + bimg.astype(np.float32) * alpha
    else:
        out = out_a.copy()
        full = _mask({"rects": [{"x": 0, "y": 0, "w": 1, "h": 1}], "circles": [], "invert": False}, w, h)
        for r in lay["rects"]:
            local = _mask({"rects": [r], "circles": [], "invert": False}, w, h)
            if lay["invert"]:
                local = full - local
            src = _shift(bimg, r["dx"], r["dy"]).astype(np.float32) if (r["dx"] or r["dy"]) else bimg.astype(np.float32)
            m = (local > 0)[..., None]
            out = np.where(m, out * (1.0 - lay["alpha"]) + src * lay["alpha"], out)
        if lay["circles"]:
            local = _mask({"rects": [], "circles": lay["circles"], "invert": lay["invert"]}, w, h)[..., None]
            out = out * (1.0 - local * lay["alpha"]) + bimg.astype(np.float32) * (local * lay["alpha"])

    if lay["paperFlash"]:
        f = lay["paperFlash"]
        out = out * (1.0 - f) + np.array((243, 242, 241), np.float32) * f
    return np.clip(out, 0, 255).astype(np.uint8)


def duration(name: str, default: float = 0.5) -> float:
    return float((TRANSITIONS.get(name) or {}).get("duration", default))


def sfx_for(name: str) -> str | None:
    """The sound the catalogue pairs with this transition (used by the audio kit)."""
    return (TRANSITIONS.get(name) or {}).get("sfx")
