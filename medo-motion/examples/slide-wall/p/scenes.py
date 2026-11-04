"""Real Engine P example: Slide Wall as Fixed Stage CONTENT (silent six-second preview)."""
import os
from pathlib import Path

import captions
import cv2
import numpy as np
import space3d
from slide_wall import create_slide_wall, load_project_slide_wall
from stage import _load_strict_json, brand_hex, load_project_stage, render_fixed_stage

ROOT = Path(__file__).resolve().parent
W, H, FPS = 1080, 1920, 30
SUPPORTS_REDUCED_MOTION = True
STAGE = load_project_stage(ROOT, include_manual=True)
WALL_SPEC = load_project_slide_wall(ROOT)
if STAGE is None or WALL_SPEC is None:
    raise RuntimeError("The slide-wall example requires enabled stage.json and slide-wall.json")
# load_project_stage intentionally returns text only; read copy metadata through the strict plan loader.
COPY = {item["id"]: item for item in _load_strict_json(ROOT / "plan" / "copy.json")["copy"]}
DIRECTION = STAGE["direction"]
MOTION_MODE = os.environ.get("MEDO_MOTION_MODE", "normal")
if MOTION_MODE not in {"normal", "reduced"}:
    raise ValueError("MEDO_MOTION_MODE must be normal or reduced")


def _rgb(role):
    return space3d.to_rgb(brand_hex(role))


def draw_slide(slide, width, height):
    """Static slide texture; all numbers still use the shared directed-text contract."""
    frame = np.empty((height, width, 3), dtype=np.float32)
    frame[:, :] = _rgb(slide["surfaceRole"])
    accent = _rgb(slide["accentRole"])
    cv2.rectangle(frame, (int(width * 0.1), int(height * 0.09)),
                  (int(width * 0.9), int(height * 0.105)), accent, -1)
    cv2.rectangle(frame, (int(width * 0.1), int(height * 0.82)),
                  (int(width * 0.62), int(height * 0.835)), _rgb("gray_2"), -1)
    item = COPY[slide["id"]]
    captions.draw_directed_text(
        frame, item["text"], direction=DIRECTION, scene=1, role="number", element_id=item["id"],
        t=1, start=0, end=1, cx=width / 2, cy=height * 0.5, size=int(width * 0.28),
        color=_rgb("ink"), accent=accent, theme="light", rtl=False,
    )
    rgb = np.clip(np.rint(frame), 0, 255).astype(np.uint8)
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    return np.concatenate((rgb, alpha), axis=2)


def slide_layout(slide, width, height):
    return [{"id": "number", "text": COPY[slide["id"]]["text"],
             "x": width * 0.18, "y": height * 0.40, "w": width * 0.64, "h": height * 0.20}]


WALL = create_slide_wall(WALL_SPEC, draw_slide, slide_layout=slide_layout, texture_width=450)


def render_frame(t: float) -> np.ndarray:
    def content(_layout_time, state):
        return WALL["render"](t, motion_mode=MOTION_MODE, viewport=state["win"])

    return render_fixed_stage(
        STAGE["spec"], t, content, duration=STAGE["duration"], direction=DIRECTION,
        copy_by_id=STAGE["copy_by_id"], words=None, caption_style=None, motion_mode=MOTION_MODE,
    )
