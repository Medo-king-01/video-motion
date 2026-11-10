"""Alpha compositing for hybrid layers: Engine K's transparent frames over another engine."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL, requires_toolkit
from PIL import Image

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

TOOLS = ROOT / "tools"
for _path in (TOOLS, TOOLS / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import media_bin  # noqa: E402  - needs tools/lib on the path
from render_hybrid import composite_overlay  # noqa: E402

W, H, FPS, FRAMES = 1080, 1920, 30, 3


@pytest.fixture(scope="module")
def ffmpeg() -> str:
    binary = media_bin.ffmpeg()
    if not binary:
        pytest.skip("ffmpeg is required for the hybrid compositor")
    return binary


def _base(tmp_path, ffmpeg) -> object:
    out = tmp_path / "base.mp4"
    subprocess.run(
        [ffmpeg, "-y", "-v", "error", "-f", "lavfi", "-i", f"color=c=red:s={W}x{H}:r={FPS}",
         "-frames:v", str(FRAMES), "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out)],
        check=True,
    )
    return out


def _overlay_frames(tmp_path, *, count=FRAMES, transparent=True):
    directory = tmp_path / "frames"
    directory.mkdir()
    for index in range(count):
        image = Image.new("RGBA", (W, H), (0, 0, 0, 0) if transparent else (0, 0, 255, 255))
        if transparent:
            image.paste((0, 0, 255, 255), (100, 100, 300, 300))
        image.save(directory / f"{index:05d}.png")
    return directory


def _frame(path, ffmpeg, index=0) -> np.ndarray:
    raw = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{index})",
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.uint8).reshape(H, W, 3)


def test_transparent_areas_keep_the_base_and_opaque_areas_replace_it(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    frames = _overlay_frames(tmp_path)
    composite_overlay(ffmpeg, base, frames, FRAMES, ROOT, {"PATH": "/usr/bin:/bin"}, label="test composite")

    pixel = _frame(base, ffmpeg)
    assert tuple(int(v) for v in pixel[900, 540]) == pytest.approx((255, 0, 0), abs=12)  # untouched base
    assert tuple(int(v) for v in pixel[200, 200]) == pytest.approx((0, 0, 255), abs=12)  # overlay wins


def test_a_frame_count_mismatch_is_refused(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    frames = _overlay_frames(tmp_path, count=2)
    with pytest.raises(RuntimeError, match="expected 3"):
        composite_overlay(ffmpeg, base, frames, FRAMES, ROOT, {"PATH": "/usr/bin:/bin"}, label="test composite")


@requires_toolkit
def test_engine_k_renders_a_transparent_png_sequence(tmp_path):
    """The overlay half of the contract: alpha survives the canvas → PNG → disk trip."""
    project = tmp_path / "project"
    shutil.copytree(SKILL / "templates" / "render", project / "src")
    (project / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    (project / "src" / "data.js").write_text(
        "export const W=1080,H=1920,FPS=30,DURATION=0.2,scenes=[{id:'alpha',start:0,end:0.2}];\n",
        encoding="utf-8",
    )
    (project / "src" / "scenes" / "alpha.js").write_text(
        "export function draw(ctx){ctx.fillStyle='#00FF00';ctx.fillRect(100,100,200,200);}\n",
        encoding="utf-8",
    )
    config = json.loads(subprocess.check_output(
        ["node", str(ROOT / "tools" / "chromium.mjs"), "--json"], text=True))
    env = {
        **os.environ,
        "MEDO_TOOLKIT": str(ROOT / "tools" / "toolkit"),
        "MEDO_CHROMIUM": config["executablePath"],
        "LD_LIBRARY_PATH": ":".join(filter(None, [config.get("libraryPath"), os.environ.get("LD_LIBRARY_PATH")])),
    }
    frames = project / "frames"
    result = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30",
         "--scale", "1", "--alpha", "--out", str(frames)],
        cwd=project, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    made = sorted(frames.glob("*.png"))
    assert len(made) == 6
    image = Image.open(made[0])
    assert image.mode == "RGBA" and image.size == (W, H)
    assert image.getpixel((900, 500))[3] == 0          # untouched area stays transparent
    assert image.getpixel((200, 200)) == (0, 255, 0, 255)  # the drawn box is opaque
