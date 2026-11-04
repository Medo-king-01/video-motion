"""Phase 2B Slide Wall contract, P/JS parity, adapters and opt-in real render smokes."""
from __future__ import annotations

import copy
import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import ROOT, SKILL
from PIL import Image, ImageChops

P = SKILL / "templates" / "procedural-reels"
K = SKILL / "templates" / "render"
R = SKILL / "templates" / "remotion"
TOOLS = ROOT / "tools"
EXAMPLE = SKILL / "examples" / "slide-wall"
sys.path.insert(0, str(P))

import layout_p  # noqa: E402
import slide_wall  # noqa: E402
from stage import normalize_stage_spec, stage_state_at, validate_stage_spec  # noqa: E402

RENDER_SMOKE = os.environ.get("SLIDE_WALL_RENDER_SMOKE") == "1"
render_smoke = pytest.mark.skipif(not RENDER_SMOKE, reason="Opt-in real P/K/R renders: SLIDE_WALL_RENDER_SMOKE=1")


def spec_fixture() -> dict:
    return {
        "version": 1,
        "id": "parity-wall",
        "clock": "vo",
        "canvas": {"w": 1080, "h": 1920, "fps": 30},
        "camera": {"fov": 32},
        "layout": {"slideSize": [3, 4], "gridColumns": 2, "gap": [0.45, 0.45], "depth": 0.12},
        "slides": [
            {"id": "a"},
            {"id": "b"},
            {"id": "c", "position": [6, -1, 0.3], "rotation": [0.2, -0.35, 0.15]},
        ],
        "timeline": [
            {"mode": "overview", "start": 0, "end": 1},
            {"mode": "move", "from": {"type": "overview"}, "to": {"type": "slide", "slide": "a"},
             "start": 1, "end": 2, "ease": "cubicInOut", "lift": 0.4},
            {"mode": "slide", "slide": "a", "start": 2, "end": 3},
            {"mode": "move", "from": {"type": "slide", "slide": "a"}, "to": {"type": "slide", "slide": "c"},
             "start": 3, "end": 4, "ease": "quintOut", "lift": 0.2},
            {"mode": "slide", "slide": "c", "start": 4, "end": 5},
            {"mode": "move", "from": {"type": "slide", "slide": "c"}, "to": {"type": "overview"},
             "start": 5, "end": 6, "ease": "sineInOut"},
        ],
    }


def opposite_camera_spec(rotation: float = math.pi) -> dict:
    return {
        "version": 1,
        "id": "opposite-camera",
        "canvas": {"w": 90, "h": 160, "fps": 30},
        "camera": {"fov": 32, "overview": {
            "position": [0, 0, 12], "target": [0, 0, 0], "up": [0, 1, 0], "roll": 0,
        }},
        "layout": {"slideSize": [3, 4]},
        "slides": [{"id": "a", "position": [0, 0, 0], "rotation": [0, 0, rotation]}],
        "timeline": [
            {"mode": "overview", "start": 0, "end": 0.25},
            {"mode": "move", "from": {"type": "overview"}, "to": {"type": "slide", "slide": "a"},
             "start": 0.25, "end": 1.25, "ease": "linear", "lift": 0.3},
            {"mode": "slide", "slide": "a", "start": 1.25, "end": 1.5},
        ],
    }


def test_example_contract_is_complete_and_cacheable() -> None:
    wall = json.loads((EXAMPLE / "plan" / "slide-wall.json").read_text())
    stage = json.loads((EXAMPLE / "plan" / "stage.json").read_text())
    assert slide_wall.validate_slide_wall_spec(wall, duration=6) == []
    assert validate_stage_spec(stage) == []
    norm = slide_wall.normalize_slide_wall(wall)
    assert [s["id"] for s in norm["slides"]] == ["slide-01", "slide-02", "slide-03", "slide-04"]
    assert norm["slides"][0]["position"] == [-1.725, 2.225, 0.0]
    assert [segment["mode"] for segment in norm["timeline"]] == ["overview", "move", "slide", "move", "slide", "move"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda s: s["slides"].append(copy.deepcopy(s["slides"][0])), "duplicate slide id"),
        (lambda s: s["slides"][0].update(size=[3, 0]), "size"),
        (lambda s: s["slides"][0].update(position=[0, float("nan"), 0]), "position"),
        (lambda s: s["slides"][0].update(rotation=[0, float("inf"), 0]), "rotation"),
        (lambda s: s["slides"][0].update(surfaceRole="#ffffff"), "locked brand"),
        (lambda s: s.update(viewport={"x": -1, "y": 0, "w": 100, "h": 100}), "viewport"),
        (lambda s: s["layout"].update(slideSize=[3, "bad"]), "slideSize"),
        (lambda s: s["layout"].update(bounds={"min": [-0.1, -5, -1], "max": [0.1, 5, 1]}), "bounds"),
    ],
)
def test_validation_rejects_bad_identity_geometry_roles_and_bounds(mutation, message) -> None:
    spec = spec_fixture()
    mutation(spec)
    errors = slide_wall.validate_slide_wall_spec(spec)
    assert any(message in error for error in errors), errors
    with pytest.raises(ValueError):
        slide_wall.normalize_slide_wall(spec)


def test_validation_rejects_xy_overlap_and_explicitly_permits_stacks() -> None:
    spec = spec_fixture()
    spec["slides"] = [{"id": "a", "position": [0, 0, 0]}, {"id": "b", "position": [0.2, 0.2, 9]},
                      {"id": "c", "position": [6, 0, 0]}]
    assert any("overlap" in error for error in slide_wall.validate_slide_wall_spec(spec))
    spec["layout"]["preventOverlap"] = False
    assert slide_wall.validate_slide_wall_spec(spec) == []


def test_rotation_aware_overlap_and_js_validation_parity() -> None:
    def fixture(rotation: float, prevent_overlap: bool = True) -> dict:
        spec = spec_fixture()
        spec["layout"]["preventOverlap"] = prevent_overlap
        spec["slides"] = [
            {"id": "a", "size": [2, 2], "position": [0, 0, 0], "rotation": [0, 0, rotation]},
            {"id": "b", "size": [2, 2], "position": [2.2, 0.8, 3], "rotation": [0, 0, rotation]},
        ]
        spec["timeline"] = [{"mode": "overview", "start": 0, "end": 6}]
        return spec

    separated = fixture(math.pi / 4)
    separated["slides"][1]["position"] = [4.5, 0.8, 3]
    cases = [fixture(0), fixture(math.pi / 4), separated, fixture(math.pi / 4, prevent_overlap=False)]
    expected = [False, True, False, False]  # before rotation, after rotation, separate, intentional stack
    actual = [any("overlap" in error for error in slide_wall.validate_slide_wall_spec(spec)) for spec in cases]
    assert actual == expected

    module = (K / "lib" / "slide-wall.js").as_uri()
    script = f"""
      import {{validateSlideWallSpec}} from {json.dumps(module)};
      const cases=JSON.parse(process.argv[1]);
      console.log(JSON.stringify(cases.map(spec=>validateSlideWallSpec(spec).some(e=>e.includes('overlap')))));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(cases)],
                            capture_output=True, text=True, check=True, timeout=60)
    assert json.loads(result.stdout) == expected


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda s: s["timeline"][1].update(start=1.1), "timing gap"),
        (lambda s: s["timeline"][1].update(start=0.9), "overlaps"),
        (lambda s: s["timeline"][1]["to"].update(slide="missing"), "known id"),
        (lambda s: s["timeline"][1].update(**{"from": {"type": "slide", "slide": "b"}}), "preceding segment endpoint"),
        (lambda s: s["timeline"][2].update(slide="b"), "preceding segment endpoint"),
        (lambda s: s["timeline"][1].update(ease="random"), "ease"),
        (lambda s: s["timeline"][0].update(start=0.1), "start at absolute VO time 0"),
    ],
)
def test_timeline_rejects_gaps_overlaps_bad_targets_and_discontinuity(mutation, message) -> None:
    spec = spec_fixture()
    mutation(spec)
    assert any(message in error for error in slide_wall.validate_slide_wall_spec(spec))
    assert any("duration" in error for error in slide_wall.validate_slide_wall_spec(spec_fixture(), duration=7))


def test_focus_fills_fixed_stage_window_even_for_rotated_offcentre_slide() -> None:
    spec = spec_fixture()
    viewport = {"x": 90, "y": 160, "w": 900, "h": 1200, "r": 48}
    state = slide_wall.slide_wall_state_at(spec, 4.5, viewport=viewport)
    item = next(item for item in state["slides"] if item["slide"]["id"] == "c")
    expected = [(90, 160), (990, 160), (990, 1360), (90, 1360)]
    assert item["visible"]
    for point, target in zip(item["front"], expected, strict=True):
        assert point[0] == pytest.approx(target[0], abs=0.002)
        assert point[1] == pytest.approx(target[1], abs=0.002)
        assert point[2] > 0


def test_overview_contains_all_slide_faces_and_repeat_evaluation_is_pure() -> None:
    spec = spec_fixture()
    state = slide_wall.slide_wall_state_at(spec, 0.5)
    for item in state["slides"]:
        assert item["visible"]
        for point in item["front"]:
            assert 0 <= point[0] <= 1080
            assert 0 <= point[1] <= 1920
            assert math.isfinite(point[2])
    again = slide_wall.slide_wall_state_at(spec, 0.5)
    assert np.array_equal(np.asarray(state["camera"]["pos"]), np.asarray(again["camera"]["pos"]))
    assert np.array_equal(np.asarray(state["slides"][0]["front"]), np.asarray(again["slides"][0]["front"]))


def test_visible_slide_aabb_is_finite_positive_and_matches_js() -> None:
    spec = spec_fixture()
    state = slide_wall.slide_wall_state_at(spec, 0.5)
    python_boxes = {}
    for item in state["slides"]:
        assert item["visible"]
        box = item["aabb"]
        assert all(math.isfinite(box[key]) for key in ("x", "y", "w", "h"))
        assert box["w"] > 0 and box["h"] > 0
        python_boxes[item["slide"]["id"]] = box

    module = (K / "lib" / "slide-wall.js").as_uri()
    script = f"""
      import {{slideWallStateAt}} from {json.dumps(module)};
      const state=slideWallStateAt(JSON.parse(process.argv[1]),0.5);
      console.log(JSON.stringify(Object.fromEntries(state.slides.map(item=>[item.slide.id,item.aabb]))));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(spec)],
                            capture_output=True, text=True, check=True, timeout=60)
    js_boxes = json.loads(result.stdout)
    assert js_boxes.keys() == python_boxes.keys()
    for slide_id, python_box in python_boxes.items():
        for key in ("x", "y", "w", "h"):
            assert js_boxes[slide_id][key] == pytest.approx(python_box[key], abs=1e-9)


def test_eased_move_endpoints_lift_and_reduced_motion_cut() -> None:
    spec = spec_fixture()
    before = slide_wall.slide_wall_state_at(spec, 1)
    start = slide_wall.slide_wall_state_at(spec, 1.000001)
    end = slide_wall.slide_wall_state_at(spec, 2)
    hold = slide_wall.slide_wall_state_at(spec, 2.1)
    for key in ("pos", "fwd", "right", "up"):
        assert np.allclose(before["camera"][key], start["camera"][key], atol=2e-5)
        assert np.allclose(end["camera"][key], hold["camera"][key], atol=1e-8)
    midpoint = slide_wall.slide_wall_state_at(spec, 1.5)
    linear_z = (before["camera"]["pos"][2] + end["camera"]["pos"][2]) / 2
    assert midpoint["camera"]["pos"][2] > linear_z + 0.39  # explicit lift, independent of easing
    reduced = slide_wall.slide_wall_state_at(spec, 1.25, motion_mode="reduced")
    assert reduced["progress"] == 1
    for key in ("pos", "fwd", "right", "up"):
        assert np.allclose(reduced["camera"][key], hold["camera"][key], atol=1e-8)


def test_opposite_camera_orientations_slerp_with_js_parity() -> None:
    """180-degree orientation move; Python/JS camera parity tolerance is 1e-8."""
    spec = opposite_camera_spec()
    fractions = [0.001, 0.01, 0.1, 0.25, 0.5, 0.75, 0.9, 0.99, 0.999]
    times = [0, 0.25, *[0.25 + fraction for fraction in fractions], 1.25, 1.5]
    states = [slide_wall.slide_wall_state_at(spec, t) for t in times]
    source, target = states[0]["camera"], states[-1]["camera"]
    keys = ("pos", "fwd", "right", "up", "target", "roll")
    for endpoint, expected in ((states[1]["camera"], source), (states[-2]["camera"], target)):
        for key in keys:
            assert np.allclose(endpoint[key], expected[key], atol=1e-12)

    for fraction, state in zip(fractions, states[2:-2], strict=True):
        camera = state["camera"]
        basis = np.asarray([camera["right"], camera["up"], camera["fwd"]], dtype=float)
        assert np.isfinite(basis).all()
        assert np.allclose(np.linalg.norm(basis, axis=1), 1, atol=1e-8)
        assert np.allclose(basis @ basis.T, np.eye(3), atol=1e-8)
        expected_pos = (1 - fraction) * np.asarray(source["pos"]) + fraction * np.asarray(target["pos"])
        expected_pos[2] += math.sin(math.pi * fraction) * 0.3
        assert np.allclose(camera["pos"], expected_pos, atol=1e-8)

    module = (K / "lib" / "slide-wall.js").as_uri()
    script = f"""
      import {{slideWallStateAt}} from {json.dumps(module)};
      const spec=JSON.parse(process.argv[1]), times=JSON.parse(process.argv[2]);
      console.log(JSON.stringify(times.map(t=>{{const c=slideWallStateAt(spec,t).camera;
        return Object.fromEntries(['pos','fwd','right','up','target','roll'].map(k=>[k,c[k]]));}})));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(spec), json.dumps(times)],
                            capture_output=True, text=True, check=True, timeout=60)
    for js_camera, state in zip(json.loads(result.stdout), states, strict=True):
        for key in keys:
            assert np.allclose(js_camera[key], state["camera"][key], atol=1e-8)


def test_small_rotation_move_preserves_legacy_normalized_lerp_path() -> None:
    spec = opposite_camera_spec(rotation=0.04)  # near-aligned poses retain normalized vector lerp
    norm = slide_wall.normalize_slide_wall(spec)
    source = slide_wall._overview_state(norm, norm["viewport"])
    target = slide_wall._focus_state(norm, "a", norm["viewport"])
    for fraction in (0.1, 0.25, 0.5, 0.75, 0.9):
        legacy = {key: [source[key][i] + (target[key][i] - source[key][i]) * fraction for i in range(3)]
                  for key in ("position", "target", "up")}
        expected = slide_wall.space3d.look_camera(
            legacy["position"], legacy["target"], norm["camera"]["fov"], 0, legacy["up"],
        )
        expected["pos"] = (*expected["pos"][:2], expected["pos"][2] + math.sin(math.pi * fraction) * 0.3)
        actual = slide_wall.slide_wall_state_at(norm, 0.25 + fraction)["camera"]
        for key in ("pos", "fwd", "right", "up", "target", "roll"):
            assert np.allclose(actual[key], expected[key], atol=1e-9)


def test_opposite_camera_midpoint_p_adapter_render_smoke() -> None:
    spec = opposite_camera_spec()

    def texture(slide, width, height):
        del slide
        rgba = np.full((height, width, 4), [243, 242, 241, 255], dtype=np.uint8)
        rgba[4:10, 4:-4] = [203, 39, 27, 255]
        return rgba

    wall = slide_wall.create_slide_wall(spec, texture, texture_width=32)
    frame = wall["render"](0.75)
    assert frame.shape == (160, 90, 3) and frame.dtype == np.uint8
    assert np.isfinite(frame).all() and frame.std() > 20


def test_homography_maps_all_source_corners() -> None:
    spec = spec_fixture()
    state = slide_wall.slide_wall_state_at(spec, 3.5)
    item = next(item for item in state["slides"] if item["slide"]["id"] == "c")
    matrix = np.asarray(slide_wall.slide_homography(450, 600, item["front"]))
    for source, target in zip([(0, 0), (450, 0), (450, 600), (0, 600)], item["front"], strict=True):
        projected = matrix @ np.array([*source, 1.0])
        projected = projected[:2] / projected[2]
        assert np.allclose(projected, target[:2], atol=1e-8)


def test_python_adapter_renders_textured_frames_deterministically() -> None:
    spec = spec_fixture()
    spec["canvas"] = {"w": 270, "h": 480, "fps": 30}
    spec["layout"]["slideSize"] = [1.5, 2]

    def texture(slide, width, height):
        del slide
        rgba = np.zeros((height, width, 4), dtype=np.uint8)
        rgba[:, :] = [243, 242, 241, 255]
        rgba[8:18, 8:-8] = [203, 39, 27, 255]
        return rgba

    wall = slide_wall.create_slide_wall(spec, texture, texture_width=45)
    first = wall["render"](2.5)
    again = wall["render"](2.5)
    moved = wall["render"](1.5)
    assert first.shape == (480, 270, 3) and first.dtype == np.uint8
    assert np.array_equal(first, again)
    assert not np.array_equal(first, moved)
    assert first.std() > 20 and np.isfinite(first).all()
    assert np.count_nonzero(np.all(first == [203, 39, 27], axis=2)) > 0


def test_python_projected_text_registration_passes_existing_layout_audit() -> None:
    spec = json.loads((EXAMPLE / "plan" / "slide-wall.json").read_text())
    stage = normalize_stage_spec(json.loads((EXAMPLE / "plan" / "stage.json").read_text()))

    def texture(slide, width, height):
        del slide
        rgba = np.empty((height, width, 4), dtype=np.uint8)
        rgba[:, :] = [243, 242, 241, 255]
        return rgba

    def text_rects(slide, width, height):
        return [{"id": "number", "text": slide["id"], "x": width * 0.18, "y": height * 0.40,
                 "w": width * 0.64, "h": height * 0.20}]

    wall = slide_wall.create_slide_wall(spec, texture, slide_layout=text_rects, texture_width=90)
    for t in (0, 1, 1.5, 2.5, 3.5, 4.5, 5.5, 5.9):
        win = stage_state_at(stage, t, duration=6)["win"]
        layout_p.begin_frame()
        try:
            layout_p.set_stage_window(win)
            with layout_p.with_stage_layer("content", win):
                wall["render"](t, viewport=win)
            boxes = layout_p.end_frame()
        finally:
            if layout_p.is_capturing():
                layout_p.end_frame()
        assert boxes, f"No projected P text registered at {t}"
        assert layout_p.audit_layout(boxes, stage_win=win) == [], f"P layout issue at {t}: {boxes}"


def test_project_loader_rejects_non_finite_json(tmp_path: Path) -> None:
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "slide-wall.json").write_text('{"version":1,"id":"x","slides":[],"timeline":[],"camera":{"fov":NaN}}')
    with pytest.raises(ValueError, match="non-finite"):
        slide_wall.load_project_slide_wall(tmp_path)
    assert slide_wall.load_project_slide_wall(tmp_path / "missing") is None


def test_reel_lint_w00_w01_gate(tmp_path: Path) -> None:
    sys.path.insert(0, str(TOOLS))
    import reel_lint  # noqa: PLC0415
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "slide-wall.json").write_text(json.dumps(spec_fixture()))
    report = reel_lint.Report()
    reel_lint.lint_slide_wall(report, tmp_path, {"duration": 6})
    assert not report.errors and any(item["code"] == "W00" for item in report.items)
    bad = spec_fixture()
    bad["timeline"][1]["start"] = 1.2
    (tmp_path / "plan" / "slide-wall.json").write_text(json.dumps(bad))
    report = reel_lint.Report()
    reel_lint.lint_slide_wall(report, tmp_path, {"duration": 6})
    assert report.errors and all(item["code"] == "W01" for item in report.errors)


def _snapshot(state: dict) -> dict:
    return {
        "mode": state["mode"],
        "progress": state["progress"],
        "camera": {key: state["camera"][key] for key in ("pos", "fwd", "right", "up", "fov", "target", "roll")},
        "slides": sorted([
            {
                "id": item["slide"]["id"], "visible": item["visible"], "depth": item["depth"],
                "front": item["front"], "homography": slide_wall.slide_homography(90, 120, item["front"]),
            }
            for item in state["slides"]
        ], key=lambda item: item["id"]),
    }


def test_js_validation_rejects_bad_contracts_before_either_browser_adapter() -> None:
    module = (K / "lib" / "slide-wall.js").as_uri()
    script = f"""
      import {{validateSlideWallSpec}} from {json.dumps(module)};
      const base=JSON.parse(process.argv[1]);
      const cases=[
        s=>s.slides.push({{...s.slides[0]}}),
        s=>s.slides[0].size=[3,0],
        s=>s.slides[0].position=[0,null,0],
        s=>s.slides[0].surfaceRole='#fff',
        s=>s.timeline[1].to.slide='missing',
        s=>s.timeline[1].start=1.2,
        s=>s.layout.bounds={{min:[-0.1,-5,-1],max:[0.1,5,1]}},
        s=>{{s.slides[0].position=[0,0,0];s.slides[1].position=[0,0,0];}},
      ];
      console.log(JSON.stringify(cases.map(mutate=>{{const spec=structuredClone(base);mutate(spec);
        return validateSlideWallSpec(spec,6).length>0;}})));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(spec_fixture())],
                            capture_output=True, text=True, check=True, timeout=60)
    assert json.loads(result.stdout) == [True] * 8


def test_p_k_r_numeric_parity_and_identical_js_core() -> None:
    spec = spec_fixture()
    module = (K / "lib" / "slide-wall.js").as_uri()
    script = f"""
      import {{normalizeSlideWall,slideWallStateAt,slideHomography}} from {json.dumps(module)};
      const spec=JSON.parse(process.argv[1]), norm=normalizeSlideWall(spec);
      const snapshot=(state)=>({{mode:state.mode,progress:state.progress,
        camera:Object.fromEntries(['pos','fwd','right','up','fov','target','roll'].map(k=>[k,state.camera[k]])),
        slides:state.slides.map(item=>({{id:item.slide.id,visible:item.visible,depth:item.depth,front:item.front,
          homography:slideHomography(90,120,item.front)}})).sort((a,b)=>a.id.localeCompare(b.id))}});
      console.log(JSON.stringify({{positions:norm.slides.map(s=>s.position),
        states:[0,1.25,1.5,2.5,3.5,4.5,5.5,6].map(t=>snapshot(slideWallStateAt(norm,t,{{viewport:{{x:90,y:160,w:900,h:1200,r:48}}}})))}}));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script, json.dumps(spec)],
        capture_output=True, text=True, check=True, timeout=60,
    )
    actual = json.loads(result.stdout)
    expected_norm = slide_wall.normalize_slide_wall(spec)
    assert actual["positions"] == [slide["position"] for slide in expected_norm["slides"]]
    times = [0, 1.25, 1.5, 2.5, 3.5, 4.5, 5.5, 6]
    for t, js_state in zip(times, actual["states"], strict=True):
        py_state = _snapshot(slide_wall.slide_wall_state_at(
            expected_norm, t, viewport={"x": 90, "y": 160, "w": 900, "h": 1200, "r": 48},
        ))
        assert js_state["mode"] == py_state["mode"]
        assert js_state["progress"] == pytest.approx(py_state["progress"], abs=1e-12)
        for key in py_state["camera"]:
            assert np.allclose(js_state["camera"][key], py_state["camera"][key], atol=1e-9)
        for js_item, py_item in zip(js_state["slides"], py_state["slides"], strict=True):
            assert js_item["id"] == py_item["id"] and js_item["visible"] == py_item["visible"]
            assert js_item["depth"] == pytest.approx(py_item["depth"], abs=1e-9)
            assert np.allclose(js_item["front"], py_item["front"], atol=1e-9)
            assert np.allclose(js_item["homography"], py_item["homography"], atol=1e-8)
    assert (K / "lib" / "slide-wall.js").read_bytes() == (R / "src" / "lib" / "slide-wall.js").read_bytes()
    assert (K / "lib" / "space3d.js").read_bytes() == (R / "src" / "lib" / "space3d.js").read_bytes()


def _browser_env() -> dict:
    result = subprocess.run(["node", str(TOOLS / "chromium.mjs"), "--json"], capture_output=True, text=True, timeout=90)
    if result.returncode:
        pytest.fail("Chromium unavailable for explicitly requested Slide Wall smoke: " + result.stderr)
    config = json.loads(result.stdout)
    env = {
        **os.environ,
        "MEDO_TOOLKIT": str(TOOLS / "toolkit"),
        "MEDO_CHROMIUM": config["executablePath"],
        "REMOTION_BROWSER_EXECUTABLE": config["executablePath"],
        "LD_LIBRARY_PATH": (config.get("libraryPath") or "") + ":" + os.environ.get("LD_LIBRARY_PATH", ""),
    }
    return env


def _scaffold(engine: str, target: Path) -> Path:
    result = subprocess.run(
        [sys.executable, str(TOOLS / "new_slide_wall_example.py"), f"wall-{engine}", "--engine", engine, "--out", str(target)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return target


def _video_frames(path: Path):
    import av
    with av.open(str(path)) as container:
        return [frame.to_ndarray(format="rgb24") for frame in container.decode(video=0)]


@render_smoke
@pytest.mark.slow
def test_real_p_full_example_render(tmp_path: Path) -> None:
    project = _scaffold("p", tmp_path / "p")
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg
    output = tmp_path / "p.mp4"
    result = subprocess.run(
        [sys.executable, str(TOOLS / "render_p_segment.py"), "--project", str(project),
         "--from-frame", "0", "--to-frame", "180", "--out", str(output), "--ffmpeg", ffmpeg],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    frames = _video_frames(output)
    assert len(frames) == 180
    assert all(frame.shape == (1920, 1080, 3) and frame.std() > 20 for frame in frames)
    assert not np.array_equal(frames[69], frames[129])
    red = frames[69]
    assert np.count_nonzero((red[:, :, 0] > 150) & (red[:, :, 1] < 100) & (red[:, :, 2] < 100)) > 100


@render_smoke
@pytest.mark.slow
def test_real_k_full_example_render_and_replay(tmp_path: Path) -> None:
    project = _scaffold("k", tmp_path / "k")
    env = _browser_env()
    frames_out = tmp_path / "k-frames"
    result = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "6", "--fps", "30", "--jpg", "--out", str(frames_out)],
        cwd=project, env=env, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    frame_paths = sorted(frames_out.glob("*.jpg"))
    assert len(frame_paths) == 180
    assert all(np.asarray(Image.open(path).convert("RGB")).std() > 20 for path in frame_paths)
    images = {i: Image.open(frames_out / f"{i:05d}.jpg").convert("RGB") for i in (0, 69, 129, 177)}
    assert all(np.asarray(image).std() > 20 for image in images.values())
    assert ImageChops.difference(images[69], images[129]).getbbox() is not None
    audit = tmp_path / "k-audit"
    result = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "6", "--fps", "30", "--audit", "--replay", "--every", "15", "--out", str(audit)],
        cwd=project, env=env, capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((audit / "report.json").read_text())
    assert report["status"] == "pass" and report["replay"]["status"] == "pass"
    assert report["replay"]["failedFrames"] == 0 and report["replay"]["checkedFrames"] == 13


@render_smoke
@pytest.mark.slow
def test_real_r_typecheck_full_example_render_and_repeat_still(tmp_path: Path) -> None:
    modules_value = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    if not modules_value:
        pytest.fail("Set MEDO_REMOTION_TEST_NODE_MODULES for the explicitly requested R smoke")
    modules = Path(modules_value).resolve()
    for name in ("@remotion/cli", "@remotion/renderer", "typescript", "react", "esbuild"):
        assert (modules / name).is_dir(), f"Missing R test dependency: {name}"
    project = _scaffold("r", tmp_path / "r")
    (project / "node_modules").symlink_to(modules, target_is_directory=True)
    env = _browser_env()

    def run(command, timeout=300):
        result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
        assert result.returncode == 0, result.stdout + result.stderr

    run(["node", "node_modules/typescript/bin/tsc", "--noEmit"], timeout=120)
    output = project / "wall.mp4"
    run(["node", "scripts/launch-remotion.mjs", "render", "src/index.ts", "SlideWallExample", str(output), "--log=error"])
    frames = _video_frames(output)
    assert len(frames) == 180
    assert all(frame.shape == (1920, 1080, 3) and frame.std() > 20 for frame in frames)
    assert not np.array_equal(frames[69], frames[129])
    for name in ("repeat-a.png", "repeat-b.png"):
        run(["node", "scripts/launch-remotion.mjs", "still", "src/index.ts", "SlideWallExample", name,
             "--frame=69", "--log=error"], timeout=180)
    assert ImageChops.difference(Image.open(project / "repeat-a.png"), Image.open(project / "repeat-b.png")).getbbox() is None
