"""Engine P's soft glow is blurred where the halo can still see it, not on the full canvas.

`circle_spr(r, color, glow)` draws a blurred disc behind a solid one. The old version allocated the
whole supersampled canvas (4104x4104 px for a 600 px radius at SS=3), filled an ellipse into it, and
Gaussian-blurred it with sigma = 96. A sigma-96 Gaussian has no detail finer than 96 px, so 60x more
pixels were processed than the result could carry: profiling a master chunk put `gaussian_blur` at
3.07 s of 8.34 s (37% of the render), with `resize` another 20%.

The halo is now drawn on the coarsest grid that still resolves its gradient (sigma ~= 4 px), blurred
there, upscaled, and composited under the disc at *logical* size. Measured on the same 9-frame
master chunk: 9.2-9.7 s before, 5.0-5.2 s after (1.85x), and a real 1080x1920 frame differs by
MAE 0.48/255 (PSNR 42.0 dB) - the change is in the halo feather, not the layout.

These tests pin what makes it safe: the blur happens off the full canvas, the sprite keeps its shape
and its solid core, and the result is deterministic and cached.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest
from conftest import ENGINE_P, FONTS, ROOT  # noqa: F401 - ROOT kept for symmetry with the sibling test

FONT = FONTS / "Cairo_800ExtraBold.ttf"


def engine_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"REEL_SS"}}
    if FONT.is_file():
        env["REEL_FONT"] = str(FONT)
    env["REEL_DIR"] = str(ENGINE_P)
    env.update(extra)
    return env


def run_lib(code: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(ENGINE_P),
        capture_output=True,
        text=True,
        env=engine_env(**extra),
        timeout=300,
    )


def test_the_halo_is_blurred_off_the_full_canvas():
    """Regression guard for the 60x waste: the blur must see a reduced grid, not 4104x4104."""
    code = """
import json, PIL.Image as I, lib
seen = []
real = I.Image.filter
def spy(self, flt, *a, **k):
    from PIL import ImageFilter
    if isinstance(flt, ImageFilter.GaussianBlur):
        seen.append({'size': list(self.size), 'sigma': round(float(flt.radius), 2)})
    return real(self, flt, *a, **k)
I.Image.filter = spy
spr = lib.circle_spr(600, (203, 39, 27), 40)
print(json.dumps({'sprite': list(spr.shape), 'blurs': seen}))
"""
    result = run_lib(code, REEL_SS="3")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["blurs"], "the glow path stopped blurring entirely - check circle_spr"
    sprite_h, sprite_w = payload["sprite"][:2]
    for blur in payload["blurs"]:
        w, h = blur["size"]
        assert w <= sprite_w / 8 and h <= sprite_h / 8, (
            f"a {w}x{h} canvas was blurred for a {sprite_w}x{sprite_h} sprite: the halo is being "
            "computed at supersampled resolution again"
        )
        # and the sigma is still the visually correct one, only measured on a coarser grid
        assert 1.0 <= blur["sigma"] <= 12.0, f"blur sigma {blur['sigma']} px is not a coarse-grid blur"


def test_the_glow_sprite_keeps_its_shape_and_solid_core():
    """Compare against the exact full-resolution blur on a small sprite: same shape, same core."""
    code = """
import json, numpy as np, PIL.Image as I, PIL.ImageDraw as ID, PIL.ImageFilter as F, lib
from lib import D, SS

def exact(r, color, glow):
    pad = glow * 2 + 4
    d = D(2 * r + 2 * pad, 2 * r + 2 * pad)
    g = I.new('RGBA', d.im.size, (0, 0, 0, 0))
    ID.Draw(g).ellipse([pad * SS, pad * SS, (pad + 2 * r) * SS, (pad + 2 * r) * SS], fill=color + (150,))
    g = g.filter(F.GaussianBlur(glow * SS * 0.8))
    d.im.alpha_composite(g)
    d.circ(pad + r, pad + r, r, fill=color)
    return d.done()

lib.circle_spr.cache_clear()
a = exact(60, (203, 39, 27), 8)
b = lib.circle_spr(60, (203, 39, 27), 8)
print(json.dumps({'shape': [list(a.shape), list(b.shape)], 'diff': float(np.abs(a - b).mean() / 255)}))
np.save('/tmp/glow_exact.npy', a); np.save('/tmp/glow_fast.npy', b)
"""
    result = run_lib(code, REEL_SS="3")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["shape"][0] == payload["shape"][1], f"the sprite changed size: {payload['shape']}"
    assert payload["diff"] < 0.01, f"mean difference {payload['diff'] * 255:.2f}/255 is a visual change"

    import numpy as np  # noqa: PLC0415 - only this test needs the arrays

    a = np.load("/tmp/glow_exact.npy", allow_pickle=False).astype(np.float32)
    b = np.load("/tmp/glow_fast.npy", allow_pickle=False).astype(np.float32)
    for path in ("/tmp/glow_exact.npy", "/tmp/glow_fast.npy"):
        os.unlink(path)

    def bbox(alpha):
        ys, xs = np.nonzero(alpha > 0)
        return ys.min(), ys.max(), xs.min(), xs.max()

    assert max(abs(x - y) for x, y in zip(bbox(a[..., 3]), bbox(b[..., 3]), strict=True)) <= 2, (
        "the halo grew or shrank instead of being resampled"
    )
    core = (a[..., 3] == 255) & (b[..., 3] == 255)
    # r=60 inside a 160x160 sprite is ~44% of the canvas; both versions must agree on that disc.
    assert core.mean() > 0.35, "the two sprites barely overlap - the solid disc moved"
    core_diff = np.abs(a[..., :3] - b[..., :3])[core]
    assert core_diff.mean() < 1.0, f"solid pixels differ by {core_diff.mean():.2f}/255"
    # Only the feather may differ, and only slightly: no pixel jumps by a visible amount.
    assert np.abs(a[..., 3] - b[..., 3]).max() <= 40, "the halo edge moved further than a resample can explain"


def test_the_glow_sprite_is_cached_and_deterministic():
    code = """
import hashlib, lib
lib.circle_spr.cache_clear()
first = lib.circle_spr(90, (203, 39, 27), 14)
second = lib.circle_spr(90, (203, 39, 27), 14)
again = lib.circle_spr(90, (203, 39, 27), 14)
assert first is second is again, 'circle_spr is no longer served from its cache'
print(hashlib.sha256(first.tobytes()).hexdigest())
"""
    first = run_lib(code, REEL_SS="3")
    second = run_lib(code, REEL_SS="3")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout.strip() == second.stdout.strip(), "the same sprite hashes differently across runs"


@pytest.mark.parametrize("supersample", ["1", "2", "3"])
def test_the_glow_works_at_every_supersample(supersample):
    """Draft (SS=1) and master (SS=3) must both produce a halo, sized for their own scale."""
    code = """
import json, lib
spr = lib.circle_spr(40, (203, 39, 27), 8)
print(json.dumps({'shape': list(spr.shape), 'alpha_max': int(spr[..., 3].max())}))
"""
    result = run_lib(code, REEL_SS=supersample)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["alpha_max"] == 255, f"SS={supersample} lost the solid disc"
    size = payload["shape"][0]
    assert size == 2 * 40 + 2 * (8 * 2 + 4), f"SS={supersample} changed the sprite geometry: {size}"
