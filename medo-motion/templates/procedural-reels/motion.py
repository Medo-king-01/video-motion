"""Motion grammar for engine P — deterministic, scrubbable, frame-independent.

Same vocabulary and the same maths as engine K (`templates/render/lib/motion.js`) and as motion.dev:
named cubic-beziers (`ease('backOut', p)`), springs with stiffness/damping/mass, and keyframe tracks
(`timeline({'tracks': {...}}).at(t)`). Everything is a pure function of `t`, so a frame renders the
same at any fps — that is exactly what a video pipeline needs and what real-time libraries can't give.

Curves live in `medo-motion/motion/easings.json`; `tests/test_motion.py` keeps both engines in sync.

    from motion import timeline, ease, spring
    tl = timeline({"tracks": {"card.y": [{"t": 0, 'v': 120}, {"t": .6, 'v': 0, 'ease': 'spring'}]}})
    y = tl.at(0.42)["card.y"]
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path

CUBIC_BEZIER = {
    "linear": [0, 0, 1, 1],
    "ease": [0.25, 0.1, 0.25, 1],
    "easeIn": [0.42, 0, 1, 1],
    "easeOut": [0, 0, 0.58, 1],
    "easeInOut": [0.42, 0, 0.58, 1],
    "circIn": [0.55, 0, 1, 0.45],
    "circOut": [0, 0.55, 0.45, 1],
    "circInOut": [0.85, 0, 0.15, 1],
    "backIn": [0.36, 0, 0.66, -0.56],
    "backOut": [0.34, 1.56, 0.64, 1],
    "backInOut": [0.68, -0.6, 0.32, 1.6],
    "anticipate": [0.36, 0, 0.66, -0.56],
}

SPRING_PRESETS = {
    "default": {"stiffness": 100, "damping": 10, "mass": 1},
    "soft": {"stiffness": 80, "damping": 18, "mass": 1},
    "snappy": {"stiffness": 220, "damping": 22, "mass": 1},
    "bouncy": {"stiffness": 260, "damping": 12, "mass": 1},
    "heavy": {"stiffness": 120, "damping": 26, "mass": 2},
}


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def lerp(a, b, p):
    return a + (b - a) * p


def progress(t, start, dur):
    if dur <= 0:
        return 1.0 if t >= start else 0.0
    return clamp((t - start) / dur)


def stagger(i, each=0.06, start=0.0):
    return start + i * each


@lru_cache(maxsize=64)
def _bezier(x1, y1, x2, y2):
    ax, bx, cx = 3 * x1 - 3 * x2 + 1, 3 * x2 - 6 * x1, 3 * x1
    ay, by, cy = 3 * y1 - 3 * y2 + 1, 3 * y2 - 6 * y1, 3 * y1

    def sample_x(t):
        return ((ax * t + bx) * t + cx) * t

    def sample_y(t):
        return ((ay * t + by) * t + cy) * t

    def slope_x(t):
        return (3 * ax * t + 2 * bx) * t + cx

    def fn(p):
        if p <= 0:
            return 0.0
        if p >= 1:
            return 1.0
        t = p
        for _ in range(8):
            x = sample_x(t) - p
            if abs(x) < 1e-6:
                return sample_y(t)
            d = slope_x(t)
            if abs(d) < 1e-6:
                break
            t -= x / d
        lo, hi, t = 0.0, 1.0, p
        for _ in range(40):
            x = sample_x(t)
            if abs(x - p) < 1e-6:
                break
            if x < p:
                lo = t
            else:
                hi = t
            t = (lo + hi) / 2
        return sample_y(t)

    return fn


def ease(spec, p):
    """ease('backOut', 0.4) · ease([0.34, 1.56, 0.64, 1], 0.4)"""
    if callable(spec):
        return spec(clamp(p))
    pts = spec if isinstance(spec, (list, tuple)) else CUBIC_BEZIER.get(spec, CUBIC_BEZIER["easeOut"])
    return _bezier(float(pts[0]), float(pts[1]), float(pts[2]), float(pts[3]))(clamp(p))


def spring(elapsed, params="default"):
    """Closed-form damped spring normalised so it settles at 1 (it overshoots on purpose)."""
    conf = params if isinstance(params, dict) else SPRING_PRESETS.get(params, SPRING_PRESETS["default"])
    stiffness = conf.get("stiffness", 100)
    damping = conf.get("damping", 10)
    mass = conf.get("mass", 1)
    velocity = conf.get("velocity", 0.0)
    if elapsed <= 0:
        return 0.0
    w0 = math.sqrt(stiffness / mass)
    zeta = damping / (2 * math.sqrt(stiffness * mass))
    if zeta < 1:
        wd = w0 * math.sqrt(1 - zeta * zeta)
        b = (zeta * w0 - velocity) / wd
        return 1 - math.exp(-zeta * w0 * elapsed) * (math.cos(wd * elapsed) + b * math.sin(wd * elapsed))
    e = math.exp(-w0 * elapsed)
    return 1 - e * (1 + (w0 - velocity) * elapsed)


def spring_duration(params="default", band=0.01):
    conf = params if isinstance(params, dict) else SPRING_PRESETS.get(params, SPRING_PRESETS["default"])
    w0 = math.sqrt(conf.get("stiffness", 100) / conf.get("mass", 1))
    zeta = conf.get("damping", 10) / (2 * math.sqrt(conf.get("stiffness", 100) * conf.get("mass", 1)))
    if zeta >= 1:
        return math.log(1 / band) / w0 + 1 / w0
    return math.log(1 / (band * math.sqrt(1 - zeta * zeta))) / (zeta * w0)


def _mix(a, b, p):
    if isinstance(a, (list, tuple)):
        return [lerp(c, b[i] if i < len(b) else c, p) for i, c in enumerate(a)]
    return lerp(a, b, p)


def keyframes(track, t):
    """Sample one keyframe track; the `ease` of a keyframe shapes the segment arriving at it."""
    if not track:
        return 0
    if t <= track[0]["t"]:
        return track[0]["v"]
    if t >= track[-1]["t"]:
        return track[-1]["v"]
    i = 0
    while i < len(track) - 1 and t >= track[i + 1]["t"]:
        i += 1
    a, b = track[i], track[i + 1]
    span = max(1e-6, b["t"] - a["t"])
    p = (t - a["t"]) / span
    spec = b.get("ease", "easeOut")
    if spec == "spring" or (isinstance(spec, dict) and spec.get("type") == "spring"):
        conf = spec if isinstance(spec, dict) else "default"
        return _mix(a["v"], b["v"], spring(t - a["t"], conf))
    if isinstance(spec, str) and spec in SPRING_PRESETS:
        return _mix(a["v"], b["v"], spring(t - a["t"], spec))
    return _mix(a["v"], b["v"], ease(spec, p))


class Timeline:
    """timeline({"duration": 3, "tracks": {...}}).at(t) → {track: value}"""

    def __init__(self, spec):
        self.tracks = spec.get("tracks", {})
        ends = [tr[-1]["t"] for tr in self.tracks.values() if tr]
        self.duration = spec.get("duration", max([0.0, *ends]))

    def at(self, t):
        return {name: keyframes(track, t) for name, track in self.tracks.items()}

    def start_of(self, name):
        track = self.tracks.get(name)
        return track[0]["t"] if track else 0.0


def timeline(spec):
    return Timeline(spec)


def load(path):
    """Read a timeline JSON (hand-written, or exported from tools/theatre_import.py)."""
    return timeline(json.loads(Path(path).read_text(encoding="utf-8")))


def reveal(t, start, dur, ease_name="easeOut"):
    return ease(ease_name, progress(t, start, dur))
