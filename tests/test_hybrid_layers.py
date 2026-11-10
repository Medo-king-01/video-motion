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
from PIL import Image, ImageDraw

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

TOOLS = ROOT / "tools"
for _path in (TOOLS, TOOLS / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import media_bin  # noqa: E402  - needs tools/lib on the path
from render_hybrid import composite_overlay, composite_stack  # noqa: E402

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


def _opaque_overlay_frames(tmp_path, colour=(0, 0, 255)):
    """A full-frame opaque overlay: without a mask it hides the base completely."""
    directory = tmp_path / "opaque"
    directory.mkdir()
    for index in range(FRAMES):
        Image.new("RGB", (W, H), colour).save(directory / f"{index:05d}.png")
    return directory


def test_a_rect_mask_hands_the_presenter_area_back_to_the_base(tmp_path, ffmpeg):
    """The v2.1 promise: type behind the presenter, not over his face."""
    base = _base(tmp_path, ffmpeg)
    frames = _opaque_overlay_frames(tmp_path)
    composite_overlay(ffmpeg, base, frames, FRAMES, ROOT, {"PATH": "/usr/bin:/bin"},
                      label="masked composite",
                      mask={"type": "rect", "x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4, "feather": 0.0})
    pixel = _frame(base, ffmpeg)
    assert tuple(int(v) for v in pixel[960, 540]) == pytest.approx((255, 0, 0), abs=12)   # inside: base
    assert tuple(int(v) for v in pixel[100, 100]) == pytest.approx((0, 0, 255), abs=12)   # outside: overlay


def test_a_feathered_rect_edge_is_soft_not_a_hard_cut(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    frames = _opaque_overlay_frames(tmp_path)
    composite_overlay(ffmpeg, base, frames, FRAMES, ROOT, {"PATH": "/usr/bin:/bin"},
                      label="feathered composite",
                      mask={"type": "rect", "x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4, "feather": 24.0})
    pixel = _frame(base, ffmpeg).astype(int)
    edge = pixel[560:600, 540, 2]  # blue channel across the top edge of the rectangle
    assert edge.min() < 200 and edge.max() > 40, edge.tolist()
    assert len(set(edge.tolist())) > 3, "a feathered edge must ramp, not switch"


def test_a_matte_image_hands_back_exactly_the_painted_area(tmp_path, ffmpeg):
    project = tmp_path / "project"
    (project / "assets").mkdir(parents=True)
    matte = Image.new("L", (W, H), 0)
    ImageDraw.Draw(matte).ellipse((340, 660, 740, 1260), fill=255)
    matte.save(project / "assets" / "presenter-matte.png")

    base = _base(tmp_path, ffmpeg)
    frames = _opaque_overlay_frames(tmp_path)
    composite_overlay(ffmpeg, base, frames, FRAMES, project, {"PATH": "/usr/bin:/bin"},
                      label="matte composite",
                      mask={"type": "image", "path": "assets/presenter-matte.png"})
    pixel = _frame(base, ffmpeg)
    assert tuple(int(v) for v in pixel[960, 540]) == pytest.approx((255, 0, 0), abs=12)  # in the ellipse
    assert tuple(int(v) for v in pixel[50, 50]) == pytest.approx((0, 0, 255), abs=12)    # outside it


def test_a_missing_matte_fails_before_touching_the_base(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    frames = _opaque_overlay_frames(tmp_path)
    before = base.read_bytes()
    with pytest.raises(RuntimeError, match="mask matte not found"):
        composite_overlay(ffmpeg, base, frames, FRAMES, tmp_path, {"PATH": "/usr/bin:/bin"},
                          label="matte composite",
                          mask={"type": "image", "path": "assets/absent.png"})
    assert base.read_bytes() == before


def test_a_frame_count_mismatch_is_refused(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    frames = _overlay_frames(tmp_path, count=2)
    with pytest.raises(RuntimeError, match="expected 3"):
        composite_overlay(ffmpeg, base, frames, FRAMES, ROOT, {"PATH": "/usr/bin:/bin"}, label="test composite")


def _box_frames(tmp_path, name, box, colour):
    """A transparent sequence that paints one box in one colour."""
    directory = tmp_path / name
    directory.mkdir()
    for index in range(FRAMES):
        image = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(image).rectangle(box, fill=(*colour, 255))
        image.save(directory / f"{index:05d}.png")
    return directory


def test_two_overlays_stack_in_plan_order_and_encode_once(tmp_path, ffmpeg):
    """Bottom overlay paints the frame, the top one paints its box — in one FFmpeg pass."""
    base = _base(tmp_path, ffmpeg)                       # red base, never visible
    bottom = _opaque_overlay_frames(tmp_path)            # blue, full frame
    top = _box_frames(tmp_path, "top", (400, 800, 700, 1100), (0, 255, 0))
    composite_stack(ffmpeg, base, [{"frames_dir": bottom}, {"frames_dir": top}], FRAMES,
                    ROOT, {"PATH": "/usr/bin:/bin"}, label="stack composite")
    pixel = _frame(base, ffmpeg)
    assert tuple(int(v) for v in pixel[950, 550]) == pytest.approx((0, 255, 0), abs=12)   # top wins
    assert tuple(int(v) for v in pixel[200, 200]) == pytest.approx((0, 0, 255), abs=12)   # bottom
    assert tuple(int(v) for v in pixel[1700, 1000]) == pytest.approx((0, 0, 255), abs=12)


def test_a_mask_on_the_top_overlay_lets_the_lower_one_through(tmp_path, ffmpeg):
    base = _base(tmp_path, ffmpeg)
    bottom = _opaque_overlay_frames(tmp_path)                              # blue
    top = _box_frames(tmp_path, "top", (0, 0, W, H), (0, 255, 0))          # green, full frame
    composite_stack(ffmpeg, base,
                    [{"frames_dir": bottom},
                     {"frames_dir": top,
                      "mask": {"type": "rect", "x": 0.3, "y": 0.3, "w": 0.4, "h": 0.4,
                               "feather": 0.0}}],
                    FRAMES, ROOT, {"PATH": "/usr/bin:/bin"}, label="masked stack")
    pixel = _frame(base, ffmpeg)
    assert tuple(int(v) for v in pixel[960, 540]) == pytest.approx((0, 0, 255), abs=12)  # green removed
    assert tuple(int(v) for v in pixel[100, 100]) == pytest.approx((0, 255, 0), abs=12)  # green kept


@requires_toolkit
def test_engine_k_can_render_only_the_scenes_an_overlay_owns(tmp_path):
    """`--only` is what makes two overlays different pictures out of one K project."""
    project = tmp_path / "project"
    shutil.copytree(SKILL / "templates" / "render", project / "src")
    (project / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    (project / "src" / "data.js").write_text(
        "export const W=1080,H=1920,FPS=30,DURATION=0.2,"
        "scenes=[{id:'first',start:0,end:0.1},{id:'second',start:0.1,end:0.2}];\n",
        encoding="utf-8",
    )
    (project / "src" / "scenes" / "first.js").write_text(
        "export function draw(ctx){ctx.fillStyle='#FF0000';ctx.fillRect(100,100,200,200);}\n",
        encoding="utf-8",
    )
    (project / "src" / "scenes" / "second.js").write_text(
        "export function draw(ctx){ctx.fillStyle='#00FF00';ctx.fillRect(600,600,200,200);}\n",
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
    frames = project / "only-second"
    result = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--scale", "1",
         "--alpha", "--only", "second", "--out", str(frames)],
        cwd=project, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    made = sorted(frames.glob("*.png"))
    assert len(made) == 6
    early = Image.open(made[0])    # t = 0: 'first' owns this moment, so nothing is drawn
    late = Image.open(made[3])     # t = 0.1: 'second' draws its box
    assert early.getpixel((700, 700))[3] == 0 and early.getpixel((200, 200))[3] == 0
    assert late.getpixel((700, 700)) == (0, 255, 0, 255)
    assert late.getpixel((200, 200))[3] == 0


@requires_toolkit
def test_engine_k_rejects_an_unknown_scene_id(tmp_path):
    project = tmp_path / "project"
    shutil.copytree(SKILL / "templates" / "render", project / "src")
    (project / "package.json").write_text('{"type":"module"}', encoding="utf-8")
    (project / "src" / "data.js").write_text(
        "export const W=1080,H=1920,FPS=30,DURATION=0.2,scenes=[{id:'only',start:0,end:0.2}];\n",
        encoding="utf-8",
    )
    (project / "src" / "scenes" / "only.js").write_text(
        "export function draw(ctx){ctx.fillStyle='#00FF00';ctx.fillRect(0,0,10,10);}\n",
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
    result = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.1", "--fps", "30", "--scale", "1",
         "--alpha", "--only", "ghost", "--out", str(project / "ghost")],
        cwd=project, env=env, capture_output=True, text=True, timeout=180,
    )
    assert result.returncode != 0
    assert "unknown scene id(s) in only: ghost" in result.stdout + result.stderr


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
