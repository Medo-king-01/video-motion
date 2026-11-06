"""Deterministic, frame-addressable effect states for engine P.

These functions describe geometry and per-element state; renderers remain responsible for
painting/compositing the returned values. Every result is derived only from the requested time
and explicit parameters, so arbitrary frame seeks do not depend on render order.
The API is mirrored by render/lib/effects.js and Remotion's copy.
"""
from __future__ import annotations

import math

from motion import clamp, ease, progress


def light_sweep(
    t: float,
    start: float = 0.0,
    duration: float = 0.72,
    width: float = 0.18,
    angle: float = -0.22,
    intensity: float = 0.72,
) -> dict:
    """Return a normalized diagonal highlight-band state for the requested time."""
    p = progress(t, start, duration)
    travel = ease("smoothstep", p)
    return {
        "progress": p,
        "center_x": -width + (1.0 + 2.0 * width) * travel,
        "width": width,
        "angle": angle,
        "alpha": intensity * math.sin(math.pi * p),
    }


def whip_pan(
    t: float,
    start: float = 0.0,
    duration: float = 0.42,
    direction: float = 1.0,
    distance: float = 1.15,
    shutter: float = 0.055,
    max_blur: float = 0.16,
) -> dict:
    """Return a normalized pan offset, analytic velocity, and bounded blur distance."""
    p = progress(t, start, duration)
    eased = ease("smoothstep", p)
    safe_duration = max(float(duration), 1e-9)
    velocity_x = -direction * distance * (6.0 * p * (1.0 - p)) / safe_duration
    blur_distance = min(abs(velocity_x) * shutter, max_blur)
    return {
        "progress": p,
        "offset_x": direction * distance * (1.0 - eased),
        "velocity_x": velocity_x,
        "blur_distance": blur_distance,
    }


def _hash01(value: int) -> float:
    """32-bit integer hash shared with JS; no random module or mutable RNG state."""
    return ((value * 1664525 + 1013904223) & 0xFFFFFFFF) / 4294967296.0


def particle_dissolve(
    t: float,
    start: float = 0.0,
    duration: float = 0.72,
    count: int = 96,
    seed: int = 18,
) -> dict:
    """Return a stable normalized particle field whose opacity decays over the dissolve."""
    p = progress(t, start, duration)
    total = max(1, min(256, int(count)))
    particles = []
    for i in range(total):
        key = int(seed) * 1024 + i * 4
        x = _hash01(key + 1)
        y = _hash01(key + 2)
        radius = 0.004 + _hash01(key + 3) * 0.006
        delay = _hash01(key) * 0.35
        local = clamp((p - delay) / (1.0 - delay))
        faded = ease("smoothstep", local)
        particles.append({
            "x": x + (x - 0.5) * 0.08 * faded,
            "y": y + (y - 0.5) * 0.08 * faded,
            "radius": radius * (1.0 + 0.4 * faded),
            "alpha": 1.0 - faded,
        })
    return {"progress": p, "particles": particles}
