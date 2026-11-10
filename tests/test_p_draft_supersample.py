"""Engine P's draft stops paying for pixels nobody keeps.

A P frame is dominated by *sprite* work: every shape is drawn `SS`x larger (3x by default), blurred,
and LANCZOS-downsampled. That is the right price for a 1080x1920 master. A draft is delivered at
540x960 — half the buffer — so the third supersample is thrown away by the encoder anyway.

`REEL_SS` makes that a knob instead of a guess. Measured on the fixture reel (30 source frames):
874 ms/frame at SS=3 against 215 ms/frame at SS=1, with the two drafts visually identical
(MAE < 1/255, PSNR 36-38 dB). `render_p_segment.py --draft` therefore asks for SS=1 unless the
caller set `REEL_SS` themselves.

These tests pin the three properties that make that safe: the value is validated instead of silently
clamped, lowering it changes rasterisation but not geometry, and the draft render really passes the
knob (while an explicit caller value still wins).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import ENGINE_P, FONTS, ROOT

FIXTURE_PLAN = ROOT / "tests" / "fixtures" / "reel" / "good" / "plan"
FONT = FONTS / "Cairo_800ExtraBold.ttf"


def engine_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in {"REEL_SS"}}
    if FONT.is_file():
        env["REEL_FONT"] = str(FONT)
    env["REEL_DIR"] = str(ENGINE_P)
    env.update(extra)
    return env


def run_lib(code: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", code], cwd=str(ENGINE_P), capture_output=True,
                          text=True, env=engine_env(**extra), timeout=180)


@pytest.mark.parametrize("value", ["1", "2", "3", "4"])
def test_every_valid_supersample_is_accepted(value):
    result = run_lib("import lib; print('SS=%d' % lib.SS)", REEL_SS=value)
    assert result.returncode == 0, result.stderr
    assert f"SS={value}" in result.stdout


@pytest.mark.parametrize("value", ["0", "5", "abc", "-1", "2.5"])
def test_an_impossible_supersample_fails_loudly(value):
    result = run_lib("import lib; print(lib.SS)", REEL_SS=value)
    assert result.returncode != 0
    assert "REEL_SS" in result.stderr + result.stdout


def test_a_lower_supersample_changes_rasterisation_not_geometry():
    """Same sprite size, same colour, small per-pixel difference — an anti-aliasing change."""
    code = """
import json, numpy as np, lib
spr = lib.circle_spr(60, (203, 39, 27), 0)
np.save('/tmp/p_ss_%(tag)s.npy', spr)
print(json.dumps({'shape': list(spr.shape)}))
"""
    if not FONT.is_file():
        pytest.skip("Cairo font missing — run: bash tools/setup.sh")
    high = run_lib(code % {"tag": "high"}, REEL_SS="3")
    low = run_lib(code % {"tag": "low"}, REEL_SS="1")
    assert high.returncode == 0, high.stderr
    assert low.returncode == 0, low.stderr
    import numpy as np  # noqa: PLC0415 - only this test needs the arrays

    a = np.load("/tmp/p_ss_high.npy", allow_pickle=False).astype(np.float32)
    b = np.load("/tmp/p_ss_low.npy", allow_pickle=False).astype(np.float32)
    for path in ("/tmp/p_ss_high.npy", "/tmp/p_ss_low.npy"):
        Path(path).unlink(missing_ok=True)
    assert a.shape == b.shape, f"the sprite changed size: {a.shape} vs {b.shape}"

    def bbox(alpha):
        ys, xs = np.nonzero(alpha > 0)
        return ys.min(), ys.max(), xs.min(), xs.max()

    # A supersampled sprite feathers a little further out (measured: 3 px on a 128 px circle), but the
    # pixels both versions call solid are the same colour — this is anti-aliasing, not a redesign.
    interior = (a[..., 3] == 255) & (b[..., 3] == 255)
    assert interior.mean() > 0.6, "the two sprites barely overlap — something other than SS changed"
    interior_diff = np.abs(a[..., :3] - b[..., :3])[interior]
    assert interior_diff.mean() < 1.0, f"solid pixels differ by {interior_diff.mean():.2f}/255"
    assert max(abs(x - y) for x, y in zip(bbox(a[..., 3]), bbox(b[..., 3]), strict=True)) <= 4
    coverage_a, coverage_b = (a[..., 3] > 0).mean(), (b[..., 3] > 0).mean()
    assert abs(coverage_a - coverage_b) < 0.05, f"coverage moved {coverage_a:.3f} -> {coverage_b:.3f}"


def make_p_project(target: Path) -> Path:
    """A minimal engine-P project with the fixture's directed text plan."""
    if not FONT.is_file():
        pytest.skip("Cairo font missing — run: bash tools/setup.sh")
    target.mkdir(parents=True, exist_ok=True)
    for source in ENGINE_P.iterdir():
        if source.is_file():
            shutil.copy2(source, target / source.name)
    fonts_dir = target / "assets" / "fonts" / "Cairo"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    for font in FONTS.glob("*.ttf"):
        shutil.copy2(font, fonts_dir / font.name)
    (target / "plan").mkdir(exist_ok=True)
    for name in ("beats.json", "text-direction.json", "copy.json"):
        shutil.copy2(FIXTURE_PLAN / name, target / "plan" / name)
    return target


def render_draft(project: Path, out: Path, **extra: str) -> dict:
    profile = out.with_suffix(".json")
    env = engine_env(**extra)
    env["PATH"] = f"{ROOT / 'tools' / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "render_p_segment.py"), "--project", str(project),
         "--from-frame", "0", "--to-frame", "4", "--draft", "--out", str(out),
         "--ffmpeg", str(ROOT / "tools" / "bin" / "ffmpeg"), "--profile-out", str(profile)],
        capture_output=True, text=True, env=env, timeout=900,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(profile.read_text(encoding="utf-8"))


@pytest.mark.slow
def test_the_draft_render_asks_for_a_single_supersample(tmp_path):
    project = make_p_project(tmp_path / "p_draft")
    report = render_draft(project, project / "out" / "draft.mp4")
    assert report["draft"] is True
    assert report["supersample"] == 1
    assert report["frames"] == 2  # 4 source frames -> 2 draft frames


@pytest.mark.slow
def test_an_explicit_supersample_from_the_caller_wins(tmp_path):
    project = make_p_project(tmp_path / "p_draft_explicit")
    report = render_draft(project, project / "out" / "draft.mp4", REEL_SS="3")
    assert report["supersample"] == 3
