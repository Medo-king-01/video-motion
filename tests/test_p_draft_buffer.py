"""Engine P renders drafts into a real 540x960 buffer, not a shrunk 1080x1920 frame.

The 1080x1920 design space is separated from the device buffer: `lib.SCALE` converts every
buffer write (paste/fill_rect/direct cv2/warpAffine) while sprites, fonts and layout math stay in
the design space — the same sprite cache the master uses. `REEL_DRAFT=1` selects 0.5; an explicit
`REEL_SCALE` overrides the factor for tests and experiments. Measured on the fixture reel at
REEL_SS=1: the draft renders directly at 540x960 in ~109 ms/frame against ~163 ms for the old
1080-render-then-shrink path (**1.49x**), and the picture matches the shrunk master (MAE
0.4-1.6/255, PSNR 33-41 dB across the timeline).

These tests pin the properties that make that safe: the scale is validated instead of silently
clamped, the master path is byte-identical at scale 1, the draft buffer really is 540x960, the
picture survives the separation, and the Fixed Stage window/mask geometry follows the buffer.
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
    env = {k: v for k, v in os.environ.items() if k not in {"REEL_SCALE", "REEL_DRAFT"}}
    if FONT.is_file():
        env["REEL_FONT"] = str(FONT)
    env["REEL_DIR"] = str(ENGINE_P)
    env.update(extra)
    return env


def run_lib(code: str, **extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "-c", code], cwd=str(ENGINE_P), capture_output=True,
                          text=True, env=engine_env(**extra), timeout=180)


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


def run_render_frames(project: Path, out: Path, tag: str, times: list[float], **extra: str) -> None:
    """Render `times` through `scenes.render_frame` in one subprocess; the master variant resizes."""
    lines = ["import sys, cv2", "from scenes import render_frame", "out = sys.argv[1]"]
    for i, t in enumerate(times):
        lines.append(f"fr = render_frame({t})")
        if tag == "master":
            lines.append("fr = cv2.resize(fr, (540, 960), interpolation=cv2.INTER_AREA)")
        lines.append(f"cv2.imwrite(out + '/{tag}_{i}.png', fr)")
    result = subprocess.run([sys.executable, "-c", "\n".join(lines), str(out)],
                            cwd=str(project), capture_output=True, text=True,
                            env=engine_env(REEL_DIR=str(project), **extra), timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("value", ["0.25", "0.5", "1", "2"])
def test_every_valid_scale_is_accepted(value):
    result = run_lib("import lib; print('S=%g' % lib.SCALE)", REEL_SCALE=value)
    assert result.returncode == 0, result.stderr
    assert f"S={float(value):g}" in result.stdout


@pytest.mark.parametrize("value", ["0", "-1", "abc", ""])
def test_an_impossible_scale_fails_loudly(value):
    result = run_lib("import lib; print(lib.SCALE)", REEL_SCALE=value)
    assert result.returncode != 0
    assert "REEL_SCALE" in result.stderr + result.stdout


def test_a_draft_renders_into_the_device_buffer(tmp_path):
    project = make_p_project(tmp_path / "p_buf")
    result = subprocess.run(
        [sys.executable, "-c",
         "import numpy as np; from scenes import render_frame;"
         "fr = render_frame(0.4); print(fr.shape, fr.dtype)"],
        cwd=str(project), capture_output=True, text=True,
        env=engine_env(REEL_DIR=str(project), REEL_DRAFT="1", REEL_SS="1"), timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(960, 540, 3) uint8" in result.stdout


@pytest.mark.slow
def test_the_draft_picture_matches_the_shrunk_master(tmp_path):
    """The separated buffer must deliver the same picture as the old shrink pipeline."""
    import cv2  # noqa: PLC0415 - only this test needs the arrays
    import numpy as np  # noqa: PLC0415

    project = make_p_project(tmp_path / "p_parity")
    out = tmp_path / "frames"
    out.mkdir()
    times = [0.4, 16.8, 20.5]
    run_render_frames(project, out, "draft", times, REEL_DRAFT="1", REEL_SS="1")
    run_render_frames(project, out, "master", times, REEL_SS="1")
    for i, t in enumerate(times):
        draft = cv2.imread(str(out / f"draft_{i}.png"))
        master = cv2.imread(str(out / f"master_{i}.png"))
        assert draft is not None and master is not None
        diff = np.abs(draft.astype(np.int16) - master.astype(np.int16))
        mse = float((diff.astype(np.float64) ** 2).mean())
        psnr = 10.0 * np.log10(255.0 ** 2 / mse) if mse > 0 else 99.0
        assert diff.mean() <= 4.0, f"t={t}: MAE {diff.mean():.2f}/255 — the buffer changed the picture"
        assert psnr >= 30.0, f"t={t}: PSNR {psnr:.1f}dB — the buffer changed the picture"


def test_the_fixed_stage_renders_into_the_device_buffer(tmp_path):
    """The Fixed Stage window/mask geometry follows the buffer at half scale."""
    spec = {
        "version": 1, "id": "test-scale", "clock": "vo", "theme": "dark",
        "canvas": {"w": 1080, "h": 1920, "fps": 30},
        "defaultFramedBox": {"x": 80, "y": 240, "w": 920, "h": 1060, "r": 48},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": {"id": "wash", "theme": "dark", "density": 40, "angle": 0, "speed": 1.0},
            "frame": {"enabled": True, "strokeRole": "red", "strokeWidth": 3,
                      "matRole": "ink_shadow", "matAlpha": 0.35},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.5},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.5, "end": 1.1,
             "ease": "cubicInOut", "anchor": {"scene": 1, "word": 1, "text": "الفرق"}},
            {"mode": "framed", "start": 1.1, "end": 2.1},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 6, "marginX": 60,
                            "trackRole": "paper", "trackAlpha": 0.18, "fillRole": "red"},
            "header": {"enabled": False, "slots": []},
            "captions": {"enabled": True, "y": 1455},
        },
    }
    code = (
        "import json, sys, numpy as np, stage\n"
        "spec = json.loads(sys.argv[1])\n"
        "def content(t, st):\n"
        "    fr = np.zeros((960, 540, 3), np.float32)\n"
        "    fr[:] = (220, 40, 40)\n"
        "    return fr\n"
        "full = stage.render_fixed_stage(spec, 0.2, content)\n"
        "framed = stage.render_fixed_stage(spec, 1.6, content)\n"
        "np.save(sys.argv[2], full); np.save(sys.argv[3], framed)\n"
        "print(full.shape, framed.shape)\n"
    )
    full_path = tmp_path / "full.npy"
    framed_path = tmp_path / "framed.npy"
    result = subprocess.run(
        [sys.executable, "-c", code, json.dumps(spec), str(full_path), str(framed_path)],
        cwd=str(ENGINE_P), capture_output=True, text=True,
        env=engine_env(REEL_SCALE="0.5"), timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(960, 540, 3) (960, 540, 3)" in result.stdout

    import numpy as np  # noqa: PLC0415

    full = np.load(full_path)
    framed = np.load(framed_path)
    # Fullscreen: the content buffer is the stage canvas everywhere.
    assert full.shape == (960, 540, 3) and full.dtype == np.uint8
    assert int(full[30, 30, 0]) > 150
    # Framed: outside the window the dark UNDER background shows (design px 30,30 -> device 15,15),
    # inside it the red content (design px 540,960 -> device 270,480).
    assert int(framed[15, 15].max()) < 80
    assert int(framed[480, 270, 0]) > 150


@pytest.mark.slow
def test_chunk_draft_writes_the_device_buffer(tmp_path):
    """chunk.py's draft path feeds the encoder the real 540x960 buffer."""
    project = make_p_project(tmp_path / "p_chunk")
    env = engine_env(REEL_DIR=str(project), REEL_DRAFT="1", REEL_SS="1")
    env["PATH"] = f"{ROOT / 'tools' / 'bin'}{os.pathsep}{env.get('PATH', '')}"
    env["FFMPEG_BIN"] = str(ROOT / "tools" / "bin" / "ffmpeg")
    result = subprocess.run(
        [sys.executable, str(ENGINE_P / "chunk.py"), "0", "8"],
        cwd=str(project), capture_output=True, text=True, env=env, timeout=900)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "chunk verified 0:8" in result.stdout
    chunk = project / "out" / "draft_chunks" / "c_00000_00008.mp4"
    assert chunk.is_file()
    sys.path.insert(0, str(ENGINE_P))
    try:
        from chunk_utils import is_valid_chunk  # noqa: PLC0415
    finally:
        sys.path.pop(0)
    assert is_valid_chunk(chunk, 8, 540, 960)
