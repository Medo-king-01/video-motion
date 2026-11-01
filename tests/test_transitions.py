"""The transition catalogue: one geometry, two engines, plus the sound each one is paired with."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import numpy as np
import pytest
from conftest import SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))

SPEC = json.loads((SKILL / "motion" / "transitions.json").read_text(encoding="utf-8"))["transitions"]
JS = (SKILL / "templates" / "render" / "lib" / "transition.js").read_text(encoding="utf-8")


def _frames(h=180, w=101):
    a = np.zeros((h, w, 3), np.uint8)
    a[..., 0] = 203           # outgoing: red
    b = np.zeros((h, w, 3), np.uint8)
    b[..., 1] = 242           # incoming: paper-ish
    return a, b


def test_embedded_catalogue_matches_the_spec():
    from transition import EMBEDDED, NAMES  # noqa: PLC0415

    assert set(EMBEDDED) == set(SPEC), "transition.py drifted from transitions.json"
    assert NAMES == list(EMBEDDED)
    for name, spec in SPEC.items():
        assert EMBEDDED[name]["kind"] == spec["kind"]
        assert EMBEDDED[name]["ease"] == spec["ease"]
        assert EMBEDDED[name]["sfx"] == spec["sfx"]
        assert EMBEDDED[name]["params"] == spec.get("params", {})
        assert name in JS, f"{name} missing from lib/transition.js"
        assert f"ease: '{spec['ease']}'" in JS or f"ease: '{spec['ease']}'" in JS, name


def test_every_transition_has_a_sound_and_a_known_easing():
    from motion import EASING_NAMES  # noqa: PLC0415
    from sfx import BANK  # noqa: PLC0415

    for name, spec in SPEC.items():
        assert spec["ease"] in EASING_NAMES, f"{name}: unknown easing {spec['ease']}"
        assert spec["sfx"] in BANK, f"{name}: unknown sfx {spec['sfx']}"


def test_layer_covers_the_frame_at_both_ends():
    from transition import layer  # noqa: PLC0415

    for name in SPEC:
        start, end = layer(name, 0.0), layer(name, 1.0)
        assert 0 <= start["alpha"] <= 1 and 0 <= end["alpha"] <= 1
        for key in ("rects", "circles"):
            for shape in start[key] + end[key]:
                assert -0.01 <= shape.get("x", shape.get("cx", 0)) <= 1.01
                assert -0.01 <= shape.get("y", shape.get("cy", 0)) <= 1.01


def test_geometry_is_monotonic_where_it_should_be():
    from transition import layer  # noqa: PLC0415

    widths = [layer("wipe", p)["rects"][0]["w"] for p in (0, 0.25, 0.5, 0.75, 1)]
    assert widths == sorted(widths) and widths[0] == 0 and widths[-1] == pytest.approx(1)
    radii = [layer("iris", p)["circles"][0]["r"] for p in (0, 0.25, 0.5)]
    assert radii == sorted(radii) and radii[0] == 0
    alphas = [layer("dissolve", p)["alpha"] for p in (0, 0.5, 1)]
    assert alphas[0] == 0 and alphas[1] == pytest.approx(0.5) and alphas[2] == 1


def test_composite_endpoints_are_the_source_frames():
    from transition import composite  # noqa: PLC0415

    a, b = _frames()
    for name in ("wipe", "wipeUp", "iris", "slide", "cover", "dissolve", "zoom", "checker", "blinds"):
        np.testing.assert_allclose(composite(a, b, name, 0.0), a, atol=1)
        np.testing.assert_allclose(composite(a, b, name, 1.0), b, atol=1)


def test_wipe_reveals_from_the_left_and_upwards():
    from transition import composite  # noqa: PLC0415

    a, b = _frames()
    out = composite(a, b, "wipe", 0.5)
    assert out[0, 0, 1] == 242 and out[0, -1, 0] == 203   # left = incoming, right = outgoing
    up = composite(a, b, "wipeUp", 0.5)
    assert up[-1, 0, 1] == 242 and up[0, 0, 0] == 203     # bottom in, top still old


def test_iris_close_inverts_the_mask():
    from transition import composite, layer  # noqa: PLC0415

    assert layer("irisClose", 0.5)["invert"] is True
    a, b = _frames(200, 120)
    out = composite(a, b, "irisClose", 0.5)
    centre, corner = out[100, 60], out[2, 2]
    assert corner[1] == pytest.approx(242, abs=2)          # outside = incoming
    assert centre[0] == pytest.approx(203, abs=2)          # inside still outgoing


def test_flash_dips_through_paper():
    from transition import layer  # noqa: PLC0415

    mid = layer("flash", 0.5)
    assert mid["paperFlash"] > 0.8
    assert layer("flash", 0.0)["paperFlash"] == 0 and layer("flash", 1.0)["paperFlash"] == pytest.approx(0)


def test_composite_never_throws_and_stays_in_range():
    from transition import composite  # noqa: PLC0415

    a, b = _frames(120, 68)
    for name in SPEC:
        for p in (0, 0.1, 0.33, 0.5, 0.77, 1):
            out = composite(a, b, name, p)
            assert out.shape == a.shape and out.dtype == np.uint8
            assert out.min() >= 0 and out.max() <= 255


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_and_python_build_the_same_geometry(tmp_path):
    from transition import layer  # noqa: PLC0415

    script = tmp_path / "geo.mjs"
    script.write_text(
        "import { transitionLayer, TRANSITIONS } from "
        + json.dumps(str(SKILL / "templates" / "render" / "lib" / "transition.js")) + ";\n"
        "const out = {};\n"
        "for (const name of Object.keys(TRANSITIONS))\n"
        "  out[name] = [0, .2, .5, .8, 1].map(p => transitionLayer(name, p));\n"
        "console.log(JSON.stringify(out));\n",
        encoding="utf-8",
    )
    r = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    js = json.loads(r.stdout)
    assert set(js) == set(SPEC)
    for name, samples in js.items():
        for p, ref in zip((0, 0.2, 0.5, 0.8, 1), samples, strict=True):
            py = layer(name, p)
            assert py["alpha"] == pytest.approx(ref["alpha"], abs=1e-6)
            assert py["scaleB"] == pytest.approx(ref["scaleB"], abs=1e-9)
            assert py["aDx"] == pytest.approx(ref["aDx"], abs=1e-9)
            assert py["invert"] == ref["invert"]
            assert len(py["rects"]) == len(ref["rects"]), f"{name} @ {p} rect count"
            for mine, theirs in zip(py["rects"], ref["rects"], strict=True):
                for k in ("x", "y", "w", "h", "dx", "dy"):
                    assert mine[k] == pytest.approx(theirs[k], abs=1e-6), f"{name}.{k} @ {p}"
            for mine, theirs in zip(py["circles"], ref["circles"], strict=True):
                assert mine["r"] == pytest.approx(theirs["r"], abs=1e-6)


def test_engine_k_scene_example_is_wired():
    """The demo scene in the template must go through compositeTransition, not hand-rolled masks."""
    scene = (SKILL / "templates" / "render" / "scenes" / "transition-example.js")
    if not scene.exists():
        pytest.skip("no transition demo scene")
    text = scene.read_text(encoding="utf-8")
    assert "compositeTransition" in text and "makeLayer" in text
    data = (SKILL / "templates" / "render" / "data.js").read_text(encoding="utf-8")
    assert "transition-example" in data
