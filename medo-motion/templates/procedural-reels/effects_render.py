"""Pillow raster adapter for deterministic visual effects (Engine P)."""
from __future__ import annotations

import numpy as np
from PIL import Image

try:
    from effects import light_sweep
except ImportError:  # pragma: no cover
    from .effects import light_sweep  # type: ignore


def draw_light_sweep(image: Image.Image, t: float, **options) -> Image.Image:
    """Composite a soft diagonal white highlight onto an RGB/RGBA frame.

    Geometry comes from the shared frame-addressable light_sweep state. The input
    image is not mutated; its original RGB/RGBA mode is preserved.
    """
    if not isinstance(image, Image.Image) or image.mode not in ("RGB", "RGBA"):
        raise ValueError("light sweep target must be a PIL RGB or RGBA image")
    width, height = image.size
    if width <= 0 or height <= 0:
        raise ValueError("light sweep target must have positive dimensions")

    state = light_sweep(t, **options)
    if state["alpha"] <= 0:
        return image.copy()

    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    angle = float(state["angle"])
    # Signed distance in pixels keeps the angle consistent on portrait and landscape frames.
    signed_distance = (xx - state["center_x"] * width) * np.cos(angle) + (
        yy - height / 2.0
    ) * np.sin(angle)
    half_width = max(float(state["width"]) * width / 2.0, 1e-6)
    profile = np.clip(1.0 - np.abs(signed_distance) / half_width, 0.0, 1.0)
    alpha = np.clip(profile * float(state["alpha"]) * 0.82, 0.0, 1.0)
    rgba = np.zeros((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)

    base = image.convert("RGBA")
    result = Image.alpha_composite(base, Image.fromarray(rgba, mode="RGBA"))
    return result if image.mode == "RGBA" else result.convert("RGB")
