"""Raster adapter checks for deterministic visual effects."""
from __future__ import annotations

import sys

import numpy as np
from PIL import Image

from conftest import SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
from effects_render import draw_light_sweep  # noqa: E402


def test_light_sweep_composites_pixels_without_mutating_source():
    source = Image.new("RGB", (160, 90), (20, 20, 20))
    result = draw_light_sweep(source, 0.36)
    assert source.getpixel((80, 45)) == (20, 20, 20)
    assert result.mode == "RGB"
    assert result.size == source.size
    assert np.asarray(result).max() > 20


def test_light_sweep_endpoints_are_pixel_identical():
    source = Image.new("RGBA", (80, 48), (10, 20, 30, 255))
    for time in (0.0, 0.72):
        result = draw_light_sweep(source, time)
        assert np.array_equal(np.asarray(result), np.asarray(source))
