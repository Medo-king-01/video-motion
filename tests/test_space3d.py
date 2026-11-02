"""Spatial vocabulary: a projection that both engines agree on, and a velocity-driven blur.

Nothing here is a 3D engine — it is just enough maths to make a card or a plate sit in real space and
turn instead of cutting, plus the blur that makes a fast move read as motion rather than a jump.
Both must be pure functions of `t` so a frame renders the same at any fps.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest
import space3d
from motion import blur_steps, velocity
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "medo-motion" / "templates" / "render" / "lib"


# ------------------------------------------------------------------ meshes & projection
def test_box_and_prism_topology():
    b = space3d.box(200)
    assert len(b["verts"]) == 8 and len(b["faces"]) == 6
    roles = [r for _f, r in b["faces"]]
    assert set(roles) == {"front", "back", "left", "right", "top", "bottom"}
    hexagon = [(math.cos(a) * 100, math.sin(a) * 100) for a in np.linspace(0, 2 * math.pi, 6, endpoint=False)]
    p = space3d.prism(hexagon, 40)
    assert len(p["verts"]) == 12 and len(p["faces"]) == 8        # 2 caps + 6 sides


def test_projection_centres_and_scales():
    cam = space3d.camera(dist=1000)
    W, H = 1080, 1920
    centre = space3d.project([(0, 0, 0)], cam, W, H)[0]
    assert (centre[0], centre[1]) == pytest.approx((W / 2, H / 2), abs=1e-6)
    right = space3d.project([(100, 0, 0)], cam, W, H)[0]
    up = space3d.project([(0, 100, 0)], cam, W, H)[0]
    assert right[0] > W / 2 and right[1] == pytest.approx(H / 2, abs=1e-6)
    assert up[1] < H / 2 and up[0] == pytest.approx(W / 2, abs=1e-6)
    # perspective: the same offset further away projects closer to the centre
    near = space3d.project([(100, 0, 500)], cam, W, H)[0]
    far = space3d.project([(100, 0, -500)], cam, W, H)[0]
    assert abs(near[0] - W / 2) > abs(far[0] - W / 2)
    # and nothing behind the camera is drawable
    assert space3d.project([(0, 0, 5000)], cam, W, H)[0][3] == 0


def test_rotation_is_a_pure_function():
    p = (30.0, 40.0, 50.0)
    assert space3d.rotate(p) == p
    # the inverse of Rz·Ry·Rx is Rx⁻¹·Ry⁻¹·Rz⁻¹: negate the angles in reverse order
    back = space3d.rotate(space3d.rotate(space3d.rotate(p, 0.4, 0.2, 0.1), 0, 0, -0.1), 0, -0.2, 0)
    back = space3d.rotate(back, -0.4, 0, 0)
    assert back == pytest.approx(p, abs=1e-9)
    assert space3d.rotate(space3d.rotate(p, math.pi, 0, 0), math.pi, 0, 0) == pytest.approx(p, abs=1e-9)


def test_painter_order_far_to_near():
    cam = space3d.camera(dist=900)
    m = space3d.box(200)
    order = space3d.sorted_faces(m, cam)
    depths = [z for z, _role, _idx in order]
    assert depths == sorted(depths, reverse=True)                 # far first, near last
    assert order[-1][0] < order[0][0]


def test_colours_and_shading():
    assert space3d.to_rgb("#CB271B") == (203, 39, 27)
    assert space3d.to_rgb("#c9c5c2") == (201, 197, 194)
    assert space3d.to_rgb((1, 2, 3)) == (1, 2, 3)
    with pytest.raises(ValueError):
        space3d.to_rgb("not-a-colour")
    lit = space3d.shade("#CB271B", (0.0, 0.0, 1.0), light=(0, 0, 1), ambient=0.4)
    unlit = space3d.shade("#CB271B", (0.0, 0.0, -1.0), light=(0, 0, 1), ambient=0.4)
    assert lit[0] > unlit[0] > 0 and lit[0] <= 255                 # facing the light is brighter
    assert space3d.shade((255, 255, 255), (0, 0, 1), ambient=1.0) == (255, 255, 255)   # clamped


def test_draw_mesh_culls_and_fills():
    W, H = 400, 400
    img = Image.new("RGB", (W, H), (3, 3, 3))
    draw = ImageDraw.Draw(img)
    cam = space3d.camera(dist=900, yaw=0.6, pitch=-0.2)
    drawn = space3d.draw_mesh(draw, space3d.box(200), cam, W, H,
                              {"front": "#CB271B", "side": "#71717A"}, outline=(3, 3, 3))
    assert 2 <= drawn <= 4                                         # never the back faces too
    a = np.asarray(img)
    assert (a != np.array([3, 3, 3])).any()                     # something was painted
    assert a[..., 0].max() > 120                                   # the red front face landed
    # drawing the same mesh twice on identical canvases is identical: no hidden state
    img2 = Image.new("RGB", (W, H), (3, 3, 3))
    space3d.draw_mesh(ImageDraw.Draw(img2), space3d.box(200), cam, W, H,
                      {"front": "#CB271B", "side": "#71717A"}, outline=(3, 3, 3))
    assert np.array_equal(np.asarray(img), np.asarray(img2))


# ------------------------------------------------------------------ velocity blur
def test_velocity_is_the_derivative_of_the_property():
    assert velocity(lambda t: 300 * t, 2.0) == pytest.approx(300, abs=1e-3)
    assert velocity(lambda t: 5.0, 1.0) == pytest.approx(0, abs=1e-9)
    assert velocity(lambda t: 100 * math.sin(t), 0.0) == pytest.approx(100, abs=1e-3)


def test_blur_steps_keep_the_exposure():
    assert blur_steps(0, 0) == [(0.0, 0.0, 1.0)]                   # still → a normal sharp draw
    steps = blur_steps(900, 0, samples=6, shutter=0.05, max_px=40)
    assert len(steps) == 6
    assert sum(w for _dx, _dy, w in steps) == pytest.approx(1.0, abs=1e-5)
    assert all(dx <= 0 and abs(dy) < 1e-9 for dx, dy, _w in steps)  # the trail falls behind +x
    assert max(abs(dx) for dx, _dy, _w in steps) <= 40 + 1e-6       # clamped
    up = blur_steps(0, -900, samples=4, shutter=0.05, max_px=40)
    assert all(dy > 0 for _dx, dy, _w in up)                       # moving up leaves a down trail
    assert blur_steps(2, 2) == [(0.0, 0.0, 1.0)]                   # sub-pixel movement stays sharp


def test_engine_k_matches_engine_p():
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    cam = space3d.camera(dist=900, yaw=0.55, pitch=-0.15)
    box = space3d.box(200, 240, 60)
    script = (
        f"const s = await import({json.dumps(str(LIB / 'space3d.js'))});\n"
        f"const m = await import({json.dumps(str(LIB / 'motion.js'))});\n"
        "const mesh = { verts: " + json.dumps([list(v) for v in box["verts"]]) + ",\n"
        "  faces: [['front', 0]] };\n"
        "const cam = s.camera({ dist: 900, yaw: 0.55, pitch: -0.15 });\n"
        "console.log(JSON.stringify({\n"
        "  pos: cam.pos, fwd: cam.fwd, right: cam.right, up: cam.up,\n"
        "  proj: s.project(mesh.verts, cam, 1080, 1920),\n"
        "  norm: s.faceNormal({ verts: mesh.verts, faces: [[[0,1,2,3], 'front']] }, [[0,1,2,3], 'front']),\n"
        "  rgb: s.toRgb('#CB271B'), shade: s.shade('#CB271B', [0,0,1], [0.35,0.75,0.55], 0.45),\n"
        "  blur: m.blurSteps(900, -240, 5, 0.055, 26),\n"
        "  vel: m.velocity((t) => 120 * t * t, 0.7),\n"
        "}));\n"
    )
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    ref = json.loads(r.stdout)
    assert ref["pos"] == pytest.approx(list(cam["pos"]), abs=1e-6)
    assert ref["fwd"] == pytest.approx(list(cam["fwd"]), abs=1e-9)
    assert ref["right"] == pytest.approx(list(cam["right"]), abs=1e-9)
    assert ref["up"] == pytest.approx(list(cam["up"]), abs=1e-9)
    py = space3d.project(box["verts"], cam, 1080, 1920)
    for a, b in zip(py, ref["proj"], strict=True):
        assert list(a) == pytest.approx(b, abs=1e-4)
    assert list(space3d.face_normal(box, ((0, 1, 2, 3), "front"))) == pytest.approx(ref["norm"], abs=1e-9)
    assert space3d.to_rgb("#CB271B") == tuple(ref["rgb"])
    assert space3d.shade("#CB271B", (0, 0, 1)) == pytest.approx(ref["shade"], abs=1e-9)
    steps = blur_steps(900, -240, 5, 0.055, 26)
    assert len(steps) == len(ref["blur"])
    for (dx, dy, w), js in zip(steps, ref["blur"], strict=True):
        assert [dx, dy, w] == pytest.approx(js, abs=1e-4)
    assert velocity(lambda t: 120 * t * t, 0.7) == pytest.approx(ref["vel"], abs=1e-6)


# ------------------------------------------------------------------ wiring
def test_kinetic_demo_is_registered_and_uses_the_vocabulary():
    scene = ROOT / "medo-motion" / "templates" / "render" / "scenes" / "kinetic-example.js"
    text = scene.read_text(encoding="utf-8")
    for token in ("beat.js", "space3d.js", "drawBlurred", "camera(", "prism("):
        assert token in text, token
    data = (ROOT / "medo-motion" / "templates" / "render" / "data.js").read_text(encoding="utf-8")
    assert "kinetic-example" in data
    # the scene must not carry a fixed duration of its own: it is placed on the reel timeline
    assert "DURATION" not in text
