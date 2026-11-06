"""Deterministic effect-state parity across P, K and R."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest
from conftest import SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
from effects import light_sweep, particle_dissolve, whip_pan  # noqa: E402

K_EFFECTS = SKILL / "templates" / "render" / "lib" / "effects.js"
R_EFFECTS = SKILL / "templates" / "remotion" / "src" / "lib" / "effects.js"


def test_remotion_effect_grammar_matches_engine_k():
    assert R_EFFECTS.read_text(encoding="utf-8") == K_EFFECTS.read_text(encoding="utf-8")


def test_light_sweep_is_scrubbable_and_has_zero_alpha_at_endpoints():
    start = light_sweep(0.0)
    middle = light_sweep(0.36)
    end = light_sweep(0.72)
    assert start["alpha"] == pytest.approx(0.0, abs=1e-9)
    assert middle["alpha"] == pytest.approx(0.72, abs=1e-9)
    assert end["alpha"] == pytest.approx(0.0, abs=1e-9)
    assert start == light_sweep(0.0)


def test_whip_pan_velocity_and_blur_are_bounded():
    start = whip_pan(0.0)
    middle = whip_pan(0.21)
    end = whip_pan(0.42)
    assert start["offset_x"] == pytest.approx(1.15)
    assert middle["offset_x"] == pytest.approx(0.575)
    assert end["offset_x"] == pytest.approx(0.0, abs=1e-9)
    assert middle["velocity_x"] < 0
    assert 0 <= middle["blur_distance"] <= 0.16
    assert start["velocity_x"] == pytest.approx(0.0)


def test_particle_field_is_seeded_bounded_and_frame_independent():
    first = particle_dissolve(0.31, count=32, seed=18)
    repeated = particle_dissolve(0.31, count=32, seed=18)
    other_seed = particle_dissolve(0.31, count=32, seed=19)
    assert first == repeated
    assert first != other_seed
    assert len(first["particles"]) == 32
    assert all(-0.04 <= p["x"] <= 1.04 and -0.04 <= p["y"] <= 1.04 for p in first["particles"])
    assert all(0 <= p["alpha"] <= 1 for p in first["particles"])
    assert len(particle_dissolve(0.2, count=1000)["particles"]) == 256


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_python_and_javascript_effect_states_match(tmp_path):
    script = tmp_path / "effects-parity.mjs"
    script.write_text(
        "import { lightSweep, whipPan, particleDissolve } from "
        + json.dumps(str(K_EFFECTS))
        + ";\n"
        + "const times = [0, 0.11, 0.21, 0.36, 0.61, 0.72];\n"
        + "console.log(JSON.stringify(times.map(t => ({"
        + "light: lightSweep(t), whip: whipPan(t), particles: particleDissolve(t, 0, 0.72, 12, 18)"
        + "}))))\n",
        encoding="utf-8",
    )
    result = subprocess.run(["node", str(script)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    js_states = json.loads(result.stdout)
    times = [0, 0.11, 0.21, 0.36, 0.61, 0.72]
    for t, js in zip(times, js_states, strict=True):
        py = {
            "light": light_sweep(t),
            "whip": whip_pan(t),
            "particles": particle_dissolve(t, 0, 0.72, 12, 18),
        }
        assert py["light"] == pytest.approx(js["light"], abs=1e-6)
        assert py["whip"] == pytest.approx(js["whip"], abs=1e-6)
        assert py["particles"]["progress"] == pytest.approx(js["particles"]["progress"], abs=1e-6)
        for a, b in zip(py["particles"]["particles"], js["particles"]["particles"], strict=True):
            assert a == pytest.approx(b, abs=1e-6)
