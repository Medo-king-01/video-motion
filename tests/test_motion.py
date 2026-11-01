"""The motion grammar: one set of curves, three renderers, and a bridge from Theatre.js."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

import pytest
from conftest import ROOT, SKILL

MOTION = SKILL / "motion"
EASINGS = json.loads((MOTION / "easings.json").read_text(encoding="utf-8"))
JS = (SKILL / "templates" / "render" / "lib" / "motion.js").read_text(encoding="utf-8")
REMOTION_JS = (SKILL / "templates" / "remotion" / "src" / "lib" / "motion.js").read_text(encoding="utf-8")
EXAMPLE = json.loads((MOTION / "examples" / "card-entrance.json").read_text(encoding="utf-8"))

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))


def test_remotion_uses_the_same_motion_grammar_as_engine_k():
    assert REMOTION_JS == JS, "sync engine R from templates/render/lib/motion.js"


def test_easing_table_matches_json_in_both_engines():
    from motion import CUBIC_BEZIER, SPRING_PRESETS  # noqa: PLC0415

    assert CUBIC_BEZIER == EASINGS["cubicBezier"]
    assert SPRING_PRESETS == EASINGS["springPresets"]
    for name, pts in EASINGS["cubicBezier"].items():
        m = re.search(re.escape(name) + r"\s*:\s*\[([-\d.,\s]+)\]", JS)
        assert m, f"{name} missing from lib/motion.js"
        assert [float(v) for v in m.group(1).split(",")] == pts, name
    for name, conf in EASINGS["springPresets"].items():
        m = re.search(re.escape(name) + r":\s*\{\s*stiffness:\s*(\d+),\s*damping:\s*(\d+),\s*mass:\s*(\d+)", JS)
        assert m, f"{name} missing from lib/motion.js spring presets"
        assert [int(m.group(i)) for i in (1, 2, 3)] == [conf["stiffness"], conf["damping"], conf["mass"]]


def test_easing_endpoints_and_monotonic_curves():
    from motion import ease  # noqa: PLC0415

    for name in EASINGS["cubicBezier"]:
        assert ease(name, 0.0) == pytest.approx(0.0, abs=1e-6), name
        assert ease(name, 1.0) == pytest.approx(1.0, abs=1e-6), name
    for name in ("easeIn", "easeOut", "easeInOut", "circIn", "circOut"):
        values = [ease(name, i / 20) for i in range(21)]
        assert values == sorted(values), f"{name} should be monotonic"
    assert ease("backOut", 0.5) > 1.0, "backOut must overshoot"


def test_spring_settles_and_overshoots():
    from motion import spring, spring_duration  # noqa: PLC0415

    assert spring(0) == 0
    assert spring(spring_duration("default") * 2) == pytest.approx(1.0, abs=0.02)
    assert max(spring(t / 100) for t in range(1, 60)) > 1.0, "default spring should overshoot"
    assert spring_duration("snappy") < spring_duration("bouncy") < spring_duration("default")
    assert all(0.2 < spring_duration(n) < 2.0 for n in EASINGS["springPresets"])


def test_keyframe_tracks_clamp_and_interpolate():
    from motion import keyframes  # noqa: PLC0415

    track = EXAMPLE["tracks"]["card.opacity"]
    assert keyframes(track, -1) == track[0]["v"]
    assert keyframes(track, 99) == track[-1]["v"]
    mid = keyframes(track, 0.15)
    assert track[0]["v"] < mid < track[-1]["v"]
    # backOut overshoots on purpose (motion.dev's backOut peaks above 1 before settling)
    scale = EXAMPLE["tracks"]["card.scale"]
    assert max(keyframes(scale, i / 100) for i in range(101)) > 1.0


def test_colour_tracks_interpolate():
    from motion import keyframes  # noqa: PLC0415

    track = [{"t": 0, "v": [203, 39, 27]}, {"t": 1, "v": [217, 127, 104], "ease": "linear"}]
    mid = keyframes(track, 0.5)
    assert len(mid) == 3
    assert 203 < mid[0] < 217 and 39 < mid[1] < 127


def test_timeline_shape_matches_example():
    from motion import timeline  # noqa: PLC0415

    tl = timeline(EXAMPLE)
    assert tl.duration == EXAMPLE["duration"]
    values = tl.at(0.75)
    assert set(values) == set(EXAMPLE["tracks"])
    assert values["card.opacity"] == pytest.approx(1.0)
    assert tl.start_of("bar.width") == 0.35


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_and_python_agree_numerically(tmp_path):
    """The shared math is verified across P and both JS-based renderers."""
    from motion import timeline  # noqa: PLC0415

    script = tmp_path / "check.mjs"
    script.write_text(
        "import { timeline } from " + json.dumps(str(SKILL / "templates" / "render" / "lib" / "motion.js")) + ";\n"
        "import { readFile } from 'node:fs/promises';\n"
        "const spec = JSON.parse(await readFile(process.argv[2], 'utf8'));\n"
        "const tl = timeline(spec);\n"
        "console.log(JSON.stringify([0, 0.15, 0.4, 0.75, 1.0, 1.5].map(t => tl.at(t))));\n",
        encoding="utf-8",
    )
    r = subprocess.run(["node", str(script), str(MOTION / "examples" / "card-entrance.json")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js_values = json.loads(r.stdout)
    tl = timeline(EXAMPLE)
    for t, js in zip([0, 0.15, 0.4, 0.75, 1.0, 1.5], js_values, strict=True):
        py = tl.at(t)
        for key in py:
            assert py[key] == pytest.approx(js[key], abs=1e-3), f"{key} @ {t}"


THEATRE_STATE = {
    "sheetsById": {
        "Hero": {
            "sequence": {
                "length": 3,
                "tracksByObject": {
                    "Card": {
                        "trackIdByPropPath": {'["y"]': "track-y", '["opacity"]': "track-op"},
                        "trackData": {
                            "track-y": {"keyframes": [
                                {"position": 0, "value": 260, "handles": [[0.5, 0.5], [0.5, 0.5]]},
                                {"position": 0.8, "value": 0, "handles": [[0.34, 1.56], [0.5, 0.5]]},
                            ]},
                            "track-op": {"keyframes": [
                                {"position": 0, "value": 0, "handles": [[0.5, 0.5], [0.5, 0.5]]},
                                {"position": 0.3, "value": 1, "handles": [[0.42, 0], [0.58, 1]]},
                            ]},
                        },
                    }
                },
            }
        }
    }
}


def test_theatre_import_converts_tracks(tmp_path):
    src = tmp_path / "state.json"
    src.write_text(json.dumps(THEATRE_STATE), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "theatre_import.py"), str(src), "--offset", "18.5"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads((tmp_path / "state.timeline.json").read_text(encoding="utf-8"))
    assert set(out["tracks"]) == {"Card.y", "Card.opacity"}
    assert out["tracks"]["Card.y"][0]["t"] == pytest.approx(18.5)
    assert out["tracks"]["Card.y"][1]["t"] == pytest.approx(19.3)
    # outgoing handle of the start keyframe + incoming handle of the end keyframe
    assert out["tracks"]["Card.y"][1]["ease"] == [0.5, 0.5, 0.5, 0.5]
    assert out["tracks"]["Card.opacity"][1]["ease"] == [0.5, 0.5, 0.58, 1.0]
    assert out["duration"] == pytest.approx(21.5)  # the sheet lasts 3 s, offset by 18.5 s


def test_theatre_import_splits_vector_props(tmp_path):
    keyframes = [
        {"position": 0, "value": {"x": 10, "y": 20}, "handles": [[0.5, 0.5], [0.5, 0.5]]},
        {"position": 1, "value": {"x": 30, "y": 60}, "handles": [[0.5, 0.5], [0.5, 0.5]]},
    ]
    obj = {"trackIdByPropPath": {'["position"]': "t1"},
           "trackData": {"t1": {"keyframes": keyframes}}}
    state = {"sheetsById": {"Hero": {"sequence": {"length": 1, "tracksByObject": {"Medo": obj}}}}}
    src = tmp_path / "vec.json"
    src.write_text(json.dumps(state), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "theatre_import.py"), str(src)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads((tmp_path / "vec.timeline.json").read_text(encoding="utf-8"))
    assert set(out["tracks"]) == {"Medo.position.x", "Medo.position.y"}
    assert [k["v"] for k in out["tracks"]["Medo.position.y"]] == [20.0, 60.0]

    from motion import timeline  # noqa: PLC0415

    assert timeline(out).at(0.5)["Medo.position.x"] == pytest.approx(20.0, abs=1.0)
    assert timeline(out).at(1.0)["Medo.position.y"] == pytest.approx(60.0)


def test_theatre_import_list_and_error_paths(tmp_path):
    src = tmp_path / "empty.json"
    src.write_text(json.dumps({"sheetsById": {}}), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "theatre_import.py"), str(src)],
                       capture_output=True, text=True)
    assert r.returncode == 1 and "no keyframe tracks" in r.stdout


def test_studio_page_is_offline_and_wired():
    page = (ROOT / "tools" / "motion_studio.html").read_text(encoding="utf-8")
    assert "../medo-motion/templates/render/lib/motion.js" in page
    assert not re.search(r"https?://(?!127\.0\.0\.1|localhost)", page), "the studio must work offline"
    assert "timeline(spec)" in page


def test_engine_k_demo_uses_the_timeline():
    scene = (SKILL / "templates" / "render" / "scenes" / "motion-example.js").read_text(encoding="utf-8")
    assert "from '../lib/motion.js'" in scene
    assert "timeline(" in scene and "tl.at(" in scene
    assert "motion-example" in (SKILL / "templates" / "render" / "data.js").read_text(encoding="utf-8")
