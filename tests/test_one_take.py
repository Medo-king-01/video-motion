"""Phase 2C One-Take contract, P/JS parity, native adapters and opt-in short render smokes."""
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
EXAMPLE = SKILL / "examples" / "one-take"
sys.path.insert(0, str(P))

import one_take  # noqa: E402

RENDER_SMOKE = os.environ.get("ONE_TAKE_RENDER_SMOKE") == "1"
render_smoke = pytest.mark.skipif(not RENDER_SMOKE, reason="Opt-in short P/K/R renders: ONE_TAKE_RENDER_SMOKE=1")


def spec_fixture() -> dict:
    return {
        "version": 1,
        "id": "unit-take",
        "clock": "vo",
        "duration": 2,
        "canvas": {"w": 270, "h": 480, "fps": 30},
        "backgroundRole": "ink_shadow",
        "elements": [
            {"id": "card", "kind": "rect", "w": 60, "h": 40, "radius": 6, "role": "paper"},
            {"id": "dot", "kind": "circle", "w": 20, "h": 20, "role": "red"},
        ],
        "states": [
            {"id": "start", "time": 0, "camera": {"x": 135, "y": 240, "zoom": 1}, "elements": {
                "card": {"x": 45, "y": 80}, "dot": {"x": 200, "y": 200, "scale": 0.5, "opacity": 0},
            }},
            {"id": "middle", "time": 1, "ease": "linear", "camera": {"x": 150, "y": 230, "zoom": 2}, "elements": {
                "card": {"x": 105, "y": 140, "scale": 1.5, "rotation": 90, "opacity": 0.5},
                "dot": {"x": 200, "y": 200, "scale": 1, "opacity": 1},
            }},
            {"id": "end", "time": 2, "ease": "cubicInOut", "camera": {"x": 135, "y": 240, "zoom": 1}, "elements": {
                "card": {"x": 45, "y": 80, "scale": 1, "rotation": 180, "opacity": 1},
                "dot": {"x": 200, "y": 200, "scale": 1.5, "opacity": 0.2},
            }},
        ],
        "cursor": {
            "size": 20,
            "points": [
                {"time": 0, "x": 20, "y": 400},
                {"time": 1, "x": 100, "y": 300, "ease": "linear"},
                {"time": 2, "x": 200, "y": 400},
            ],
            "clicks": [{"time": 0.5, "duration": 0.4}],
        },
    }


def example_spec() -> dict:
    return json.loads((EXAMPLE / "plan" / "one-take.json").read_text())


def element(state: dict, element_id: str) -> dict:
    return next(item for item in state["elements"] if item["id"] == element_id)


def snapshot(state: dict) -> dict:
    return {
        "time": state["time"], "segmentIndex": state["segmentIndex"],
        "fromState": state["fromState"], "toState": state["toState"],
        "rawProgress": state["rawProgress"], "progress": state["progress"], "camera": state["camera"],
        "elements": [{"id": item["id"], "x": item["x"], "y": item["y"], "scale": item["scale"],
                      "rotation": item["rotation"], "opacity": item["opacity"],
                      "screen": item["screen"], "aabb": item["aabb"]} for item in state["elements"]],
        "cursor": state["cursor"],
    }


def test_example_is_complete_original_one_scene_contract() -> None:
    spec = example_spec()
    assert one_take.validate_one_take_spec(spec, duration=8) == []
    normalized = one_take.normalize_one_take(spec)
    assert len(normalized["states"]) == 8
    assert len(normalized["elements"]) == 24
    assert len(normalized["cursor"]["clicks"]) == 2
    assert normalized["states"][0]["time"] == 0 and normalized["states"][-1]["time"] == 8
    assert any("overlap" in error or "duration" in error
               for error in one_take.validate_one_take_spec(spec, duration=7))


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda s: s.update(duration=0), "duration"),
        (lambda s: s["canvas"].update(w=0), "canvas.w"),
        (lambda s: s["elements"].append(copy.deepcopy(s["elements"][0])), "duplicate element"),
        (lambda s: s["elements"][0].update(role="#ffffff"), "locked brand"),
        (lambda s: s["elements"][0].update(w=0), "w/h"),
        (lambda s: s["states"][1].update(time=0), "strictly increasing"),
        (lambda s: s["states"][-1].update(time=1.9), "last state time"),
        (lambda s: s["states"][1]["elements"].update(missing={"x": 0}), "unknown element"),
        (lambda s: s["states"][1].update(ease="random"), "ease"),
        (lambda s: s["states"][1]["camera"].update(zoom=0), "zoom"),
        (lambda s: s["states"][1]["elements"]["card"].update(opacity=2), "opacity"),
        (lambda s: s["cursor"]["points"].__setitem__(1, {"time": -1, "x": 0, "y": 0}), "inside the scene"),
        (lambda s: s["cursor"]["clicks"].append({"time": 0.6, "duration": 0.4}), "non-overlapping"),
        (lambda s: s.update(viewport={"x": -1, "y": 0, "w": 100, "h": 100}), "canvas"),
    ],
)
def test_validation_rejects_invalid_and_conflicting_definitions(mutation, message) -> None:
    spec = spec_fixture()
    mutation(spec)
    errors = one_take.validate_one_take_spec(spec)
    assert any(message in error for error in errors), errors
    with pytest.raises(ValueError):
        one_take.normalize_one_take(spec)


def test_text_element_validation_and_missing_direction_fail_loudly() -> None:
    spec = spec_fixture()
    spec["elements"].append({"id": "label", "kind": "text", "w": 100, "h": 40, "text": ""})
    assert any("text must be" in error for error in one_take.validate_one_take_spec(spec))
    spec["elements"][-1].update(text="Hello", fontRole="unknown")
    assert any("fontRole" in error for error in one_take.validate_one_take_spec(spec))
    spec["elements"][-1]["fontRole"] = "body"
    with pytest.raises(ValueError, match="direction plan"):
        one_take.create_one_take(spec)


def test_start_end_and_out_of_range_evaluation_are_exact() -> None:
    spec = spec_fixture()
    for t in (-1, 0):
        state = one_take.one_take_state_at(spec, t)
        assert state["time"] == 0 and state["rawProgress"] == 0
        assert state["camera"] == {"x": 135, "y": 240, "zoom": 1}
        assert element(state, "card")["x"] == 45
    for t in (2, 3):
        state = one_take.one_take_state_at(spec, t)
        assert state["time"] == 2 and state["rawProgress"] == 1
        assert state["camera"] == {"x": 135, "y": 240, "zoom": 1}
        assert element(state, "card")["rotation"] == 180
        assert element(state, "dot")["opacity"] == pytest.approx(0.2)


def test_camera_zoom_and_object_transform_interpolation() -> None:
    state = one_take.one_take_state_at(spec_fixture(), 0.5)
    assert state["camera"]["x"] == pytest.approx(142.5)
    assert state["camera"]["y"] == pytest.approx(235)
    assert state["camera"]["zoom"] == pytest.approx(math.sqrt(2), abs=1e-12)  # logarithmic zoom
    card = element(state, "card")
    assert (card["x"], card["y"], card["scale"], card["rotation"], card["opacity"]) == (
        75, 110, 1.25, 45, 0.75,
    )
    assert card["screen"]["scale"] == pytest.approx(1.25 * math.sqrt(2))
    assert all(math.isfinite(value) for value in card["aabb"].values())
    assert card["aabb"]["w"] > 0 and card["aabb"]["h"] > 0


def test_semantic_state_boundaries_are_continuous() -> None:
    spec = spec_fixture()
    for boundary in (1, 2):
        before = one_take.one_take_state_at(spec, boundary - 1e-6)
        at = one_take.one_take_state_at(spec, boundary)
        after = one_take.one_take_state_at(spec, boundary + 1e-6) if boundary < 2 else at
        for key in ("x", "y", "zoom"):
            assert before["camera"][key] == pytest.approx(at["camera"][key], abs=2e-5)
            assert after["camera"][key] == pytest.approx(at["camera"][key], abs=2e-5)
        for element_id in ("card", "dot"):
            for key in ("x", "y", "scale", "rotation", "opacity"):
                assert element(before, element_id)[key] == pytest.approx(element(at, element_id)[key], abs=2e-5)
                assert element(after, element_id)[key] == pytest.approx(element(at, element_id)[key], abs=2e-5)


def test_repeated_and_non_chronological_evaluation_is_identical() -> None:
    spec = spec_fixture()
    forward = [snapshot(one_take.one_take_state_at(spec, t)) for t in (0, 0.5, 1, 1.5, 2)]
    reverse = [snapshot(one_take.one_take_state_at(spec, t)) for t in (2, 1.5, 1, 0.5, 0)][::-1]
    assert forward == reverse
    assert snapshot(one_take.one_take_state_at(spec, 0.5)) == forward[1]


def test_cursor_click_press_ring_and_expiry_are_time_based() -> None:
    spec = spec_fixture()
    before = one_take.one_take_state_at(spec, 0.49)
    assert before["cursor"]["click"] is None and not before["cursor"]["press"]
    start = one_take.one_take_state_at(spec, 0.5)
    assert start["cursor"]["press"] and start["cursor"]["click"]["progress"] == 0
    during = one_take.one_take_state_at(spec, 0.65)
    assert not during["cursor"]["press"]
    assert during["cursor"]["click"]["progress"] == pytest.approx(0.375)
    assert during["cursor"]["click"]["opacity"] == pytest.approx(0.625)
    after = one_take.one_take_state_at(spec, 0.9)
    assert after["cursor"]["click"] is None


def test_reduced_motion_steps_to_target_without_travel_or_click_ring() -> None:
    spec = spec_fixture()
    reduced = one_take.one_take_state_at(spec, 0.25, motion_mode="reduced")
    target = one_take.one_take_state_at(spec, 1)
    assert reduced["progress"] == 1
    assert reduced["camera"] == target["camera"]
    for element_id in ("card", "dot"):
        for key in ("x", "y", "scale", "rotation", "opacity"):
            assert element(reduced, element_id)[key] == element(target, element_id)[key]
    assert reduced["cursor"]["click"] is None and not reduced["cursor"]["press"]


def test_js_validation_parity_for_same_invalid_fixtures() -> None:
    base = spec_fixture()
    cases = []
    mutations = [
        lambda s: s.update(duration=0),
        lambda s: s["states"][1].update(time=0),
        lambda s: s["states"][1]["elements"].update(missing={"x": 0}),
        lambda s: s["states"][1]["camera"].update(zoom=0),
        lambda s: s["cursor"]["clicks"].append({"time": 0.6, "duration": 0.4}),
    ]
    for mutation in mutations:
        spec = copy.deepcopy(base)
        mutation(spec)
        cases.append(spec)
    module = (K / "lib" / "one-take.js").as_uri()
    script = f"""
      import {{validateOneTakeSpec}} from {json.dumps(module)};
      const cases=JSON.parse(process.argv[1]);
      console.log(JSON.stringify(cases.map(spec=>validateOneTakeSpec(spec).length>0)));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(cases)],
                            capture_output=True, text=True, check=True, timeout=60)
    assert json.loads(result.stdout) == [True] * len(cases)
    assert all(one_take.validate_one_take_spec(spec) for spec in cases)


def assert_numeric_equal(actual, expected, atol=1e-9) -> None:
    """Compare cross-language numeric snapshots without pretending integers and floats have distinct values."""
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys()
        for key in expected:
            assert_numeric_equal(actual[key], expected[key], atol)
    elif isinstance(expected, (list, tuple)):
        assert len(actual) == len(expected)
        for left, right in zip(actual, expected, strict=True):
            assert_numeric_equal(left, right, atol)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        assert actual == pytest.approx(expected, abs=atol)
    else:
        assert actual == expected


def test_p_k_r_numeric_parity_and_identical_shared_core() -> None:
    spec = spec_fixture()
    module = (K / "lib" / "one-take.js").as_uri()
    script = f"""
      import {{oneTakeStateAt}} from {json.dumps(module)};
      const spec=JSON.parse(process.argv[1]);
      const snap=s=>({{time:s.time,segmentIndex:s.segmentIndex,fromState:s.fromState,toState:s.toState,
        rawProgress:s.rawProgress,progress:s.progress,camera:s.camera,
        elements:s.elements.map(e=>({{id:e.id,x:e.x,y:e.y,scale:e.scale,rotation:e.rotation,opacity:e.opacity,
          screen:e.screen,aabb:e.aabb}})),cursor:s.cursor}});
      console.log(JSON.stringify({{normal:[0,.25,.5,.999999,1,1.5,2,-1,3].map(t=>snap(oneTakeStateAt(spec,t))),
        reduced:snap(oneTakeStateAt(spec,.25,{{motionMode:'reduced'}}))}}));
    """
    result = subprocess.run(["node", "--input-type=module", "-e", script, json.dumps(spec)],
                            capture_output=True, text=True, check=True, timeout=60)
    actual = json.loads(result.stdout)
    times = [0, 0.25, 0.5, 0.999999, 1, 1.5, 2, -1, 3]
    for js_state, t in zip(actual["normal"], times, strict=True):
        assert_numeric_equal(js_state, snapshot(one_take.one_take_state_at(spec, t)))
    assert_numeric_equal(actual["reduced"], snapshot(one_take.one_take_state_at(spec, 0.25, motion_mode="reduced")))
    assert (K / "lib" / "one-take.js").read_bytes() == (R / "src" / "lib" / "one-take.js").read_bytes()


def test_project_loader_and_reel_lint_o00_o01(tmp_path: Path) -> None:
    sys.path.insert(0, str(TOOLS))
    import reel_lint  # noqa: PLC0415
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "one-take.json").write_text(json.dumps(spec_fixture()))
    assert one_take.load_project_one_take(tmp_path)["id"] == "unit-take"
    assert one_take.load_project_one_take(tmp_path / "missing") is None
    report = reel_lint.Report()
    reel_lint.lint_one_take(report, tmp_path, {"duration": 2})
    assert not report.errors and any(item["code"] == "O00" for item in report.items)
    bad = spec_fixture()
    bad["states"][1]["time"] = 0
    (tmp_path / "plan" / "one-take.json").write_text(json.dumps(bad))
    report = reel_lint.Report()
    reel_lint.lint_one_take(report, tmp_path, {"duration": 2})
    assert report.errors and all(item["code"] == "O01" for item in report.errors)
    (tmp_path / "plan" / "one-take.json").write_text('{"duration":NaN}')
    with pytest.raises(ValueError, match="non-finite"):
        one_take.load_project_one_take(tmp_path)


def test_native_p_adapter_render_is_deterministic_and_seek_independent() -> None:
    take = one_take.create_one_take(spec_fixture())
    first = take["render"](0.5)
    later = take["render"](1.5)
    repeated = take["render"](0.5)
    assert first.shape == (480, 270, 3) and first.dtype == np.uint8
    assert first.std() > 20 and np.isfinite(first).all()
    assert np.array_equal(first, repeated)
    assert not np.array_equal(first, later)
    assert np.count_nonzero(np.all(first == [243, 242, 241], axis=2)) > 0


def test_native_p_adapter_clips_dynamic_viewport_including_cursor() -> None:
    take = one_take.create_one_take(spec_fixture())
    viewport = {"x": 20, "y": 40, "w": 200, "h": 360, "r": 12}
    frame = take["render"](0.5, viewport=viewport)
    background = np.asarray(one_take.brand_rgb("ink_shadow"), dtype=np.uint8)
    changed = np.any(frame != background, axis=2)
    ys, xs = np.where(changed)
    assert len(xs) and xs.min() >= 20 and xs.max() < 220 and ys.min() >= 40 and ys.max() < 400
    assert np.array_equal(frame[0, 0], background)
    assert np.array_equal(frame[40, 20], background)  # rounded corner remains outside the content window
    with pytest.raises(ValueError, match="canvas"):
        take["render"](0.5, viewport={"x": -1, "y": 0, "w": 80, "h": 120})


def test_example_p_adapter_generates_real_ui_frame() -> None:
    direction = json.loads((EXAMPLE / "plan" / "text-direction.json").read_text())
    take = one_take.create_one_take(example_spec(), direction=direction)
    frame = take["render"](3.25)
    assert frame.shape == (1920, 1080, 3) and frame.std() > 20
    assert np.array_equal(frame, take["render"](3.25))
    assert not np.array_equal(frame, take["render"](7.9))


def _scaffold(engine: str, target: Path) -> Path:
    result = subprocess.run(
        [sys.executable, str(TOOLS / "new_one_take_example.py"), f"take-{engine}", "--engine", engine,
         "--out", str(target)], capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return target


def _browser_env() -> dict:
    result = subprocess.run(["node", str(TOOLS / "chromium.mjs"), "--json"], capture_output=True, text=True, timeout=90)
    if result.returncode:
        pytest.fail("Chromium unavailable for explicitly requested One-Take smoke: " + result.stderr)
    config = json.loads(result.stdout)
    return {
        **os.environ,
        "MEDO_TOOLKIT": str(TOOLS / "toolkit"),
        "MEDO_CHROMIUM": config["executablePath"],
        "REMOTION_BROWSER_EXECUTABLE": config["executablePath"],
        "LD_LIBRARY_PATH": (config.get("libraryPath") or "") + ":" + os.environ.get("LD_LIBRARY_PATH", ""),
    }


def _video_frames(path: Path):
    import av
    with av.open(str(path)) as container:
        return [frame.to_ndarray(format="rgb24") for frame in container.decode(video=0)]


@render_smoke
@pytest.mark.slow
def test_real_p_three_frame_render(tmp_path: Path) -> None:
    project = _scaffold("p", tmp_path / "p")
    output = tmp_path / "p.mp4"
    ffmpeg = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    assert ffmpeg, "ffmpeg is required for the explicitly requested P smoke"
    result = subprocess.run(
        [sys.executable, str(TOOLS / "render_p_segment.py"), "--project", str(project),
         "--from-frame", "60", "--to-frame", "63", "--ffmpeg", ffmpeg, "--out", str(output)],
        capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    frames = _video_frames(output)
    assert len(frames) == 3
    assert all(frame.shape == (1920, 1080, 3) and frame.std() > 20 for frame in frames)


@render_smoke
@pytest.mark.slow
def test_real_k_three_frame_render(tmp_path: Path) -> None:
    project = _scaffold("k", tmp_path / "k")
    output = tmp_path / "k-frames"
    result = subprocess.run(
        ["node", "src/render.js", "--from", "3.2", "--to", "3.3", "--fps", "30", "--jpg", "--out", str(output)],
        cwd=project, env=_browser_env(), capture_output=True, text=True, timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    paths = sorted(output.glob("*.jpg"))
    assert len(paths) == 3
    assert all(np.asarray(Image.open(path).convert("RGB")).std() > 20 for path in paths)


@render_smoke
@pytest.mark.slow
def test_real_r_typecheck_and_repeat_still(tmp_path: Path) -> None:
    modules_value = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    if not modules_value:
        pytest.fail("Set MEDO_REMOTION_TEST_NODE_MODULES for the explicitly requested R smoke")
    modules = Path(modules_value).resolve()
    for name in ("@remotion/cli", "@remotion/renderer", "typescript", "react", "esbuild"):
        assert (modules / name).is_dir(), f"Missing R test dependency: {name}"
    project = _scaffold("r", tmp_path / "r")
    (project / "node_modules").symlink_to(modules, target_is_directory=True)
    env = _browser_env()

    def run(command, timeout=180):
        result = subprocess.run(command, cwd=project, env=env, capture_output=True, text=True, timeout=timeout)
        assert result.returncode == 0, result.stdout + result.stderr

    run(["node", "node_modules/typescript/bin/tsc", "--noEmit"], timeout=120)
    for name in ("repeat-a.png", "repeat-b.png"):
        run(["node", "scripts/launch-remotion.mjs", "still", "src/index.ts", "OneTakeExample", name,
             "--frame=97", "--log=error"])
    first, second = Image.open(project / "repeat-a.png"), Image.open(project / "repeat-b.png")
    assert first.size == (1080, 1920) and np.asarray(first).std() > 20
    assert ImageChops.difference(first, second).getbbox() is None
