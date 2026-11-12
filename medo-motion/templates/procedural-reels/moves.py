"""Deterministic element moves for engine P (mirror of shared/js/moves.js).

Same inputs, same numbers: `tests/test_moves_b1b.py` samples both implementations on a grid and
fails on any difference larger than 1e-9. Nothing here draws; a move is a pure function.
"""
from __future__ import annotations

import math


def _finite(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise TypeError(f"{name} must be a finite number")
    return number


def _positive(value, name: str) -> float:
    number = _finite(value, name)
    if not number > 0:
        raise ValueError(f"{name} must be > 0")
    return number


def _non_negative(value, name: str) -> float:
    number = _finite(value, name)
    if number < 0:
        raise ValueError(f"{name} must be >= 0")
    return number


def _clamp01(value: float) -> float:
    return 0.0 if value < 0.0 else 1.0 if value > 1.0 else value


def _ease_out_cubic(p: float) -> float:
    return 1.0 - (1.0 - p) ** 3


def _round_to_grid(value: float, size: float) -> float:
    """JS Math.round semantics (half towards +infinity), expressed with floor."""
    return math.floor(value * size + 0.5) / size


def pixel_list_item(index: int, elapsed: float, *, stagger: float = 0.09, enter: float = 0.42,
                    rise: float = 0.6, from_: float = 0.72, font_size: float = 40.0) -> dict:
    """One row of a pixel-snapped list reveal, in font-relative em."""
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError("index must be a nonnegative integer")
    t = _non_negative(elapsed, "elapsed")
    gap = _non_negative(stagger, "stagger")
    window = _positive(enter, "enter")
    lift = _finite(rise, "rise")
    slide = _finite(from_, "from")
    size = _positive(font_size, "fontSize")

    local = t - index * gap
    p = 0.0 if local <= 0 else 1.0 if local >= window else _ease_out_cubic(local / window)
    return {
        "opacity": p,
        "x": _round_to_grid(slide * (1.0 - p), size),
        "y": _round_to_grid(-lift * (1.0 - p), size),
        "scale": 1.0,
        "pixelStep": 1.0 / size,
    }


def parallax_layer(depth: float, progress: float, *, pan_x: float = 0.8, pan_y: float = 0.0,
                   zoom: float = 0.04) -> dict:
    """One parallax layer: depth 0 pins it, depth 1 follows the camera fully (em / unitless)."""
    d = _finite(depth, "depth")
    if d < 0.0 or d > 1.0:
        raise ValueError("depth must be within 0..1")
    camera = _clamp01(_finite(progress, "progress"))
    px = _finite(pan_x, "panX")
    py = _finite(pan_y, "panY")
    z = _non_negative(zoom, "zoom")
    return {
        "x": -px * d * camera,
        "y": -py * d * camera,
        "scale": 1.0 + z * d * camera,
    }


def camera_progress(elapsed: float, start: float = 0.0, duration: float = 1.0) -> float:
    t = _finite(elapsed, "elapsed")
    s = _finite(start, "start")
    window = _positive(duration, "duration")
    if t <= s:
        return 0.0
    if t >= s + window:
        return 1.0
    return _ease_out_cubic((t - s) / window)


def _window_progress(elapsed: float, start: float, duration: float) -> float:
    t = _finite(elapsed, "elapsed")
    s = _finite(start, "start")
    window = _positive(duration, "duration")
    if t <= s:
        return 0.0
    if t >= s + window:
        return 1.0
    return _ease_out_cubic((t - s) / window)


def _hash01(value: int) -> float:
    """Same 32-bit hash as shared/js/moves.js; no random module."""
    return ((value * 1664525 + 1013904223) & 0xFFFFFFFF) / 4294967296.0


def _positive_int(value, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _index(value, name: str = "index") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")
    return value


def orbit_item(index: int, elapsed: float, *, count: int = 6, radius: float = 1.2,
               speed: float = 0.35, start: float = 0.0, phase: float = 0.0,
               squash: float = 0.35) -> dict:
    i = _index(index)
    t = _non_negative(elapsed, "elapsed")
    n = _positive_int(count, "count")
    r = _positive(radius, "radius")
    v = _non_negative(speed, "speed")
    s = _finite(start, "start")
    ph = _finite(phase, "phase")
    sq = _positive(squash, "squash")
    angle = 2.0 * math.pi * (ph + max(0.0, t - s) * v) + (2.0 * math.pi * i) / n
    depth = math.sin(angle)
    return {"x": r * math.cos(angle), "y": r * sq * depth, "scale": 1.0 + 0.08 * depth,
            "angle": angle, "depth": depth, "opacity": 1.0}


def word_path_item(index: int, elapsed: float, *, stagger: float = 0.08, enter: float = 0.5,
                   from_x: float = -2.0, to_x: float = 0.0, from_y: float = 0.0,
                   to_y: float = 0.0, rotation: float = 0.0) -> dict:
    i = _index(index)
    t = _non_negative(elapsed, "elapsed")
    gap = _non_negative(stagger, "stagger")
    window = _positive(enter, "enter")
    p = _clamp01((t - i * gap) / window)
    eased = _ease_out_cubic(p)

    def lerp(a: float, b: float) -> float:
        return a + (b - a) * eased

    return {"x": lerp(_finite(from_x, "fromX"), _finite(to_x, "toX")),
            "y": lerp(_finite(from_y, "fromY"), _finite(to_y, "toY")),
            "rotation": _finite(rotation, "rotation") * (1.0 - eased),
            "opacity": eased, "progress": p}


def explode_part(index: int, elapsed: float, *, count: int = 6, start: float = 0.0,
                 duration: float = 0.6, hold: float = 0.4, back: float | None = None,
                 spread: float = 2.2, tilt: float = 8.0, phase: float = 0.0,
                 reassemble: bool = True) -> dict:
    i = _index(index)
    t = _non_negative(elapsed, "elapsed")
    n = _positive_int(count, "count")
    s = _finite(start, "start")
    enter = _positive(duration, "duration")
    hold_for = _non_negative(hold, "hold")
    back_for = _positive(enter if back is None else back, "back")
    distance = _positive(spread, "spread")
    angle_tilt = _finite(tilt, "tilt")
    ph = _finite(phase, "phase")
    local = t - s
    if local <= 0:
        p = 0.0
    elif local < enter:
        p = _ease_out_cubic(local / enter)
    elif (not reassemble) or local < enter + hold_for:
        p = 1.0
    elif local >= enter + hold_for + back_for:
        p = 0.0
    else:
        p = 1.0 - _ease_out_cubic((local - enter - hold_for) / back_for)
    angle = ph + (2.0 * math.pi * i) / n
    direction = 1.0 if i % 2 == 0 else -1.0
    return {"x": distance * p * math.cos(angle), "y": distance * 0.6 * p * math.sin(angle),
            "rotation": angle_tilt * p * direction, "opacity": 1.0, "progress": p}


def mask_wipe(elapsed: float, *, start: float = 0.0, duration: float = 0.5,
              direction: str = "ltr", feather: float = 0.0) -> dict:
    p = _window_progress(elapsed, start, duration)
    allowed = ("ltr", "rtl", "ttb", "btt")
    if direction not in allowed:
        raise ValueError(f"direction must be one of {', '.join(allowed)}")
    rect = {"p": p, "x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0,
            "feather": _non_negative(feather, "feather")}
    if direction == "ltr":
        rect["w"] = p
    elif direction == "rtl":
        rect["w"] = p
        rect["x"] = 1.0 - p
    elif direction == "ttb":
        rect["h"] = p
    else:
        rect["h"] = p
        rect["y"] = 1.0 - p
    return rect


def data_count(elapsed: float, *, start: float = 0.0, duration: float = 0.8,
               from_: float = 0.0, to: float = 100.0, decimals: int = 0) -> dict:
    p = _window_progress(elapsed, start, duration)
    a = _finite(from_, "from")
    b = _finite(to, "to")
    if isinstance(decimals, bool) or not isinstance(decimals, int) or not 0 <= decimals <= 6:
        raise ValueError("decimals must be an integer within 0..6")
    factor = 10 ** decimals
    value = math.floor((a + (b - a) * p) * factor + 0.5) / factor
    return {"p": p, "value": value}


def card_stack_item(index: int, elapsed: float, *, stagger: float = 0.07, enter: float = 0.45,
                    spread: float = 0.18, tilt: float = 3.0, lift: float = 0.06) -> dict:
    i = _index(index)
    t = _non_negative(elapsed, "elapsed")
    gap = _non_negative(stagger, "stagger")
    window = _positive(enter, "enter")
    dx = _finite(spread, "spread")
    rot = _finite(tilt, "tilt")
    up = _non_negative(lift, "lift")
    p = _clamp01((t - i * gap) / window)
    eased = _ease_out_cubic(p)
    return {"x": dx * i * (1.0 - eased), "y": -up * i, "scale": 1.0 - 0.05 * i,
            "rotation": -rot * i * (1.0 - eased), "opacity": eased, "progress": p}


def camera_push(elapsed: float, *, start: float = 0.0, duration: float = 1.2,
                from_scale: float = 1.0, to_scale: float = 1.08, from_x: float = 0.0,
                to_x: float = 0.0, from_y: float = 0.0, to_y: float = 0.0) -> dict:
    p = _window_progress(elapsed, start, duration)
    a = _positive(from_scale, "fromScale")
    b = _positive(to_scale, "toScale")

    def lerp(u: float, v: float) -> float:
        return u + (v - u) * p

    return {"p": p, "scale": lerp(a, b),
            "x": lerp(_finite(from_x, "fromX"), _finite(to_x, "toX")),
            "y": lerp(_finite(from_y, "fromY"), _finite(to_y, "toY"))}


def particle_burst(index: int, elapsed: float, *, count: int = 24, start: float = 0.0,
                   duration: float = 0.7, speed: float = 2.4, gravity: float = 1.6,
                   seed: int = 7) -> dict:
    i = _index(index)
    t = _non_negative(elapsed, "elapsed")
    n = _positive_int(count, "count")
    s = _finite(start, "start")
    window = _positive(duration, "duration")
    v = _positive(speed, "speed")
    g = _finite(gravity, "gravity")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    base = (2.0 * math.pi * i) / n
    jitter = _hash01(i * 31 + seed)
    angle = base + (jitter - 0.5) * 0.9
    local = max(0.0, t - s)
    p = _clamp01(local / window)
    travel = v * local * (0.7 + 0.6 * jitter)
    return {"x": travel * math.cos(angle),
            "y": travel * math.sin(angle) * 0.6 + 0.5 * g * local * local,
            "opacity": 1.0 - p, "size": 0.06 * (0.7 + 0.6 * jitter), "angle": angle}
