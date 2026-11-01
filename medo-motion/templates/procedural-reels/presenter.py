"""Medo, the presenter — engine P.

The poses come from `assets/poses/` (`<slug>.png` + `poses.json`, built by
`tools/presenter_build.py`). Every cut-out is normalised to the same figure height with the feet on
the same baseline, so switching pose never makes him jump.

What this module adds on top of the images:

* **idle life** — breathing, a slow bob and a little sway, all pure functions of `t`
  (`presenter.py` and `lib/presenter.js` use the same numbers, so both engines breathe identically)
* **pose acting** — `PoseTrack` cross-fades between poses on cue, with a settle, so a beat change
  reads as a performance rather than a slide show
* **placement** — `ground=` puts the feet on the brand's ground line (1390) at any height

    from presenter import draw, PoseTrack
    track = PoseTrack([{"t": 0, "pose": "neutral"}, {"t": 2.4, "pose": "explain"}])
    draw(fr, track.at(t)[0], t, x=0.62, height=0.62)
"""
from __future__ import annotations

import json
import math
import os
from functools import lru_cache

import numpy as np

W, H = 1080, 1920
GROUND = 1390      # soles land here for full shots
TOP_GUIDE = 190    # hair line for close-ups (the brand's content starts at 200)

# Embedded fallback so a project that only received the template still works; the manifest wins.
DEFAULT_POSES = {
    "neutral": {"file": "neutral.png", "en": "neutral", "scale": 1.0, "feet": 0.9934},
    "explain": {"file": "explain.png", "en": "explaining", "scale": 1.0, "feet": 0.9934},
    "point": {"file": "point.png", "en": "pointing", "scale": 1.0, "feet": 0.9934},
    "welcome": {"file": "welcome.png", "en": "welcome", "scale": 1.0, "feet": 0.9934},
    "wave": {"file": "wave.png", "en": "wave", "scale": 1.0, "feet": 0.9934},
    "clap": {"file": "clap.png", "en": "clapping", "scale": 1.0, "feet": 0.9934},
    "like": {"file": "like.png", "en": "delighted", "scale": 1.0, "feet": 0.9934},
    "thinking": {"file": "thinking.png", "en": "thinking", "scale": 1.0, "feet": 0.9934},
    "thinking-deep": {"file": "thinking-deep.png", "en": "thinking-deep", "scale": 0.86, "feet": 0.9934},
    "puzzled": {"file": "puzzled.png", "en": "puzzled", "scale": 1.0, "feet": 0.9934},
    "sad": {"file": "sad.png", "en": "sad", "scale": 1.0, "feet": 0.9934},
    "shocked": {"file": "shocked.png", "en": "shocked", "scale": 1.0, "feet": 0.9934},
    "walk": {"file": "walk.png", "en": "walking", "scale": 0.97, "feet": 0.9934},
    "run": {"file": "run.png", "en": "running", "scale": 0.94, "feet": 0.9934},
}

# Old scene code says `medo_wave`; the pose library says `wave`.
ALIASES = {
    "medo": "neutral", "medo_neutral": "neutral", "medo_wave": "wave", "medo_think": "thinking",
    "medo_thinking": "thinking", "medo_deep": "thinking-deep", "medo_point": "point",
    "medo_explain": "explain", "medo_welcome": "welcome", "medo_clap": "clap", "medo_like": "like",
    "medo_puzzled": "puzzled", "medo_sad": "sad", "medo_shocked": "shocked",
    "medo_walk": "walk", "medo_run": "run",
}


def _base_dir() -> str:
    return os.environ.get("REEL_DIR") or os.getcwd()


@lru_cache(maxsize=1)
def manifest() -> dict:
    """`assets/poses/poses.json` next to the render dir, or the studio copy, or the fallback."""
    here = os.path.dirname(os.path.abspath(__file__))
    for root in (_base_dir(), os.path.abspath(os.path.join(here, "..", "..", ".."))):
        path = os.path.join(root, "assets", "poses", "poses.json")
        if os.path.exists(path):
            try:
                return json.loads(open(path, encoding="utf-8").read())
            except (OSError, json.JSONDecodeError):
                pass
    return {"poses": DEFAULT_POSES, "_fallback": True}


def poses() -> dict:
    return manifest().get("poses", DEFAULT_POSES)


def resolve(name: str) -> str:
    name = ALIASES.get(name, name)
    return name if name in poses() else "neutral"


def available() -> list[str]:
    return list(poses())


@lru_cache(maxsize=None)
def sprite(name: str, height: int) -> np.ndarray:
    """Premultiplied RGBA sprite at the requested pixel height (cached)."""
    slug = resolve(name)
    meta = poses().get(slug, {})
    path = None
    for root in (_base_dir(), os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))):
        cand = os.path.join(root, "assets", "poses", meta.get("file", f"{slug}.png"))
        if os.path.exists(cand):
            path = cand
            break
    if path is None:  # last resort: draw a brand panel so nothing silently disappears
        return _missing(height)
    import cv2  # noqa: PLC0415   (already a dependency of engine P)

    im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if im is None:
        return _missing(height)
    im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    h = int(height)
    w = max(1, int(round(im.shape[1] * h / im.shape[0])))
    im = cv2.resize(im, (w, h), interpolation=cv2.INTER_AREA if h < im.shape[0] else cv2.INTER_LANCZOS4)
    a = im[..., 3:4].astype(np.float32) / 255.0
    out = im.astype(np.float32)
    out[..., :3] *= a
    return out


def _missing(height: int) -> np.ndarray:
    h = int(height)
    w = max(1, int(h * 0.45))
    out = np.zeros((h, w, 4), np.float32)
    out[..., 0] = 71.0
    out[..., 3] = 255.0
    out[int(h * 0.1): int(h * 0.9), int(w * 0.15): int(w * 0.85), 0] = 159.0
    return out


# ---------------- idle motion (identical in lib/presenter.js) ----------------
def breathe(t: float) -> float:
    """1 ± 0.8% — a chest-level pulse that never distracts."""
    return 1.0 + 0.008 * math.sin(2 * math.pi * 0.28 * t)


def bob(t: float, amount: float = 2.5) -> float:
    return amount * math.sin(2 * math.pi * 0.22 * t)


def sway(t: float, amount: float = 2.0) -> float:
    return amount * math.sin(2 * math.pi * 0.13 * t + 0.7)


def lean(name: str, t: float) -> float:
    """A tiny rotation that gives the pose its own rhythm (degrees)."""
    slug = resolve(name)
    if slug == "wave":
        return 1.1 * math.sin(2 * math.pi * 1.05 * t)
    if slug == "clap":
        return 0.6 * math.sin(2 * math.pi * 2.2 * t)
    if slug in ("run", "walk"):
        return 1.4 * math.sin(2 * math.pi * 1.6 * t)
    if slug in ("thinking", "thinking-deep"):
        return 0.35 * math.sin(2 * math.pi * 0.09 * t)
    if slug == "shocked":
        return 0.9 * math.sin(2 * math.pi * 7.0 * t) * math.exp(-((t % 1.0) * 6))
    return 0.25 * math.sin(2 * math.pi * 0.11 * t)


def pulse(name: str, t: float) -> float:
    """Extra vertical hit for the energetic poses (running, shocked)."""
    slug = resolve(name)
    if slug == "run":
        return 7.0 * abs(math.sin(2 * math.pi * 1.6 * t))
    if slug == "walk":
        return 3.5 * abs(math.sin(2 * math.pi * 1.0 * t))
    if slug == "shocked":
        return 4.0 * max(0.0, math.sin(2 * math.pi * 3.0 * t)) * math.exp(-((t % 1.0) * 4))
    return 0.0


def draw(fr: np.ndarray, name: str, t: float, x: float = 0.5, height: float = 0.62,
         ground: int = GROUND, top: int = TOP_GUIDE, alpha: float = 1.0, flip: bool = False,
         idle: bool = True, scale: float | None = None) -> None:
    """Composite a pose onto an RGB frame. `x` is the horizontal centre (0..1 of the width).

    Full shots are placed by their soles (`ground`); close-ups by their hair line (`top`), so a cut
    from a wide shot to a close-up is a clean camera push-in.
    """
    slug = resolve(name)
    meta = poses().get(slug, {})
    h = max(8, int(height * H * float(scale if scale is not None else meta.get("scale", 1.0))))
    spr = sprite(slug, h)
    feet = float(meta.get("feet", 0.9934))
    from lib import paste  # noqa: PLC0415  (same folder; avoids a circular import at module load)

    cx = x * W
    if meta.get("place") == "top":
        cy = top + h / 2.0                  # close-up: the hair sits on the top guide
    else:
        cy = ground - (feet - 0.5) * h      # feet fraction → put the soles on the ground line
    if idle:
        cy -= bob(t) + pulse(slug, t)
        cx += sway(t)
        paste(fr, spr, cx, cy, scale=breathe(t), rot=lean(slug, t), alpha=alpha, flipx=flip)
    else:
        paste(fr, spr, cx, cy, alpha=alpha, flipx=flip)


class PoseTrack:
    """A cue list of poses with a cross-fade — the acting layer for a scene.

    `PoseTrack([{"t": 0, "pose": "neutral"}, {"t": 2.4, "pose": "explain"}])`
    then `.at(t)` → `{"pose", "prev", "blend", "settle"}`: draw `prev` then `pose` at `blend`.
    """

    def __init__(self, cues: list[dict], fade: float = 0.12):
        # keep the raw name and resolve at draw time (the manifest may not be loaded yet)
        self.cues = sorted(({"t": float(c.get("t", 0.0)), "pose": c.get("pose", "neutral")}
                            for c in cues), key=lambda c: c["t"])
        self.fade = fade

    @property
    def duration(self) -> float:
        return self.cues[-1]["t"] if self.cues else 0.0

    def at(self, t: float) -> dict:
        prev, cur = None, self.cues[0]["pose"] if self.cues else "neutral"
        start = 0.0
        for cue in self.cues:
            if cue["t"] <= t + 1e-9:
                prev, cur, start = cur, cue["pose"], cue["t"]
            else:
                break
        blend = 1.0 if prev is None or prev == cur else min(1.0, max(0.0, (t - start) / max(1e-6, self.fade)))
        settle = 1.0 + 0.02 * (1.0 - blend) ** 2      # a 2% dip while the pose changes
        fading = blend < 1.0 and prev is not None and prev != cur
        return {"pose": resolve(cur), "prev": resolve(prev) if fading else None,
                "blend": blend, "settle": settle}

    def draw(self, fr: np.ndarray, t: float, **kw) -> dict:
        state = self.at(t)
        alpha = float(kw.pop("alpha", 1.0))
        # shaped, not a straight dissolve: out by 60%, in from 40% — a pose change reads as a beat cut
        out = max(0.0, 1.0 - state["blend"] / 0.6)
        into = min(1.0, max(0.0, (state["blend"] - 0.4) / 0.6))
        if state["prev"] is not None and out > 0:
            draw(fr, state["prev"], t, alpha=alpha * out, **kw)
        draw(fr, state["pose"], t, alpha=alpha * into, **kw)
        return state
