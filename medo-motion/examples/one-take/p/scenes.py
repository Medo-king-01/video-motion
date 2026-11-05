"""Real Engine P example: one continuous eight-second One-Take UI journey."""
import os
from pathlib import Path

from one_take import create_one_take, load_project_one_take
from stage import _load_strict_json

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
SUPPORTS_REDUCED_MOTION = True
SPEC = load_project_one_take(ROOT)
if SPEC is None:
    raise RuntimeError("The one-take example requires plan/one-take.json")
DIRECTION = _load_strict_json(ROOT / "plan" / "text-direction.json")
MOTION_MODE = os.environ.get("MEDO_MOTION_MODE", "normal")
if MOTION_MODE not in {"normal", "reduced"}:
    raise ValueError("MEDO_MOTION_MODE must be normal or reduced")
TAKE = create_one_take(SPEC, direction=DIRECTION)


def render_frame(t: float):
    return TAKE["render"](t, motion_mode=MOTION_MODE)
