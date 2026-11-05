"""Raster adapter checks for deterministic visual effects."""
from __future__ import annotations

import sys

import numpy as np
from conftest import SKILL
from PIL import Image

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
from effects_render import draw_light_sweep, draw_particle_dissolve, draw_whip_pan  # noqa: E402


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


def test_whip_pan_translates_frame_without_mutating_source():
    source = Image.new("RGB", (80, 40), (0, 0, 0))
    for x in range(8):
        for y in range(10, 30):
            source.putpixel((x, y), (255, 255, 255))

    result = draw_whip_pan(source, 0.21)
    assert source.getpixel((2, 20)) == (255, 255, 255)
    assert result.getpixel((2, 20)) == (0, 0, 0)
    assert result.getpixel((48, 20))[0] > 100
    assert result.size == source.size



def test_particle_dissolve_samples_source_pixels_without_mutating_source():
    source = Image.new("RGB", (120, 80))
    for y in range(80):
        for x in range(120):
            source.putpixel((x, y), (x * 2, y * 3, (x + y) % 256))
    original = source.copy()

    middle = draw_particle_dissolve(source, 0.18, count=256, seed=7)
    end = draw_particle_dissolve(source, 0.72, count=256, seed=7)

    assert source.tobytes() == original.tobytes()
    assert middle.mode == "RGBA"
    assert middle.size == source.size
    assert middle.getchannel("A").getbbox() is not None
    assert end.getchannel("A").getbbox() is None
