"""The rhythm layer: a beat grid both engines agree on, and cue sheets generated from it.

A reel is built at a tempo — cuts, hits and micro-actions are quantised onto the grid, so nothing
drifts off the beat. These tests pin the maths (P and K must agree to the last digit) and the
generator that turns a pattern into a cue sheet.
"""
from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path

import beat
import pytest
import sfx

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
BEAT_JS = SKILL / "templates" / "render" / "lib" / "beat.js"


def test_grid_is_a_pure_function_of_time():
    g = beat.grid(1.7, 120)
    assert g["spb"] == pytest.approx(0.5)
    assert g["beat"] == 3 and g["phase"] == pytest.approx(0.4)
    assert g["bar"] == 0
    assert beat.grid(0.0, 120)["phase"] == 0
    # a full bar of four beats is one bar
    assert beat.grid(2.0, 120)["bar"] == 1 and beat.grid(1.99, 120)["bar"] == 0
    # offset shifts the grid, not the maths
    assert beat.grid(1.7, 120, offset=0.2)["phase"] == pytest.approx(0.0)
    # the same call twice is identical: nothing is stored between frames
    assert beat.grid(3.33, 96.5) == beat.grid(3.33, 96.5)


def test_quantize_snaps_both_ways():
    assert beat.quantize(1.44, 120, 2) == pytest.approx(1.5)      # eighth notes
    assert beat.quantize(1.44, 120, 4) == pytest.approx(1.5)      # sixteenths land on .5 too
    assert beat.quantize(1.31, 120, 4) == pytest.approx(1.25)
    assert beat.quantize(1.31, 120, 4, mode="floor") == pytest.approx(1.25)
    assert beat.quantize(1.31, 120, 4, mode="ceil") == pytest.approx(1.375)
    assert beat.offset_of(1.44, 120, 2) == pytest.approx(-0.06)
    with pytest.raises(ValueError):
        beat.quantize(1.0, 120, 4, mode="sideways")
    with pytest.raises(ValueError):
        beat.quantize(1.0, 120, 0)


def test_ping_and_swell_stay_in_range():
    for t in (0.0, 0.13, 0.5, 0.99, 7.77):
        assert 0.0 <= beat.ping(t, 120) <= 1.0
        assert 0.0 <= beat.swell(t, 120) <= 1.0
    assert beat.ping(0.0, 120) == pytest.approx(1.0)             # exactly on the beat
    assert beat.ping(0.49, 120) < 0.01                           # dead before the next beat
    assert beat.ping(0.5, 120) == pytest.approx(1.0)             # ...and 1 again on the next one
    assert beat.swell(0.25, 120) == pytest.approx(1.0)           # half way through the beat


def test_on_grid_and_bars():
    assert beat.on_grid(3, 120, 4) == pytest.approx([0.0, 0.125, 0.25])
    assert beat.on_grid(2, 120, 1, start=2) == pytest.approx([1.0, 1.5])
    assert beat.bar_seconds(120) == pytest.approx(2.0)
    assert beat.bar_seconds(90, beats=2) == pytest.approx(60 / 90 * 2)


def test_snap_bounds_only_moves_close_cuts():
    bounds = [0.0, 1.44, 3.25, 4.4]
    snapped, moved = beat.snap_bounds(bounds, 120, 2, tol=0.12)
    assert snapped[0] == 0.0 and snapped[-1] == 4.4              # the VO's ends are not the grid's
    assert snapped[1] == pytest.approx(1.5) and moved == 1
    assert snapped[2] == pytest.approx(3.25)                     # 0.25 s away: left alone
    # a cut that would land on top of the previous one is never forced
    tight, moved2 = beat.snap_bounds([0.0, 0.46, 0.55, 1.0], 120, 1, tol=0.5)
    assert moved2 == 1 and tight[1] < tight[2]


def test_engine_k_beat_matches_engine_p():
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    times = [0.0, 0.13, 0.5, 1.44, 3.33, 12.7]
    script = (
        f"const b = await import({json.dumps(str(BEAT_JS))});\n"
        f"const ts = {json.dumps(times)};\n"
        "console.log(JSON.stringify(ts.map(t => ({"
        "g: b.grid(t, 120), q2: b.quantize(t, 120, 2), q4: b.quantize(t, 120, 4),"
        "floor: b.quantize(t, 120, 4, 0, 'floor'), ping: b.ping(t, 120), swell: b.swell(t, 120),"
        "ladder: b.ladder(t, 120, 0, 3), off: b.offsetOf(t, 120, 2) }))));\n"
    )
    r = subprocess.run(["node", "--input-type=module", "-e", script], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for t, ref in zip(times, json.loads(r.stdout), strict=True):
        g = beat.grid(t, 120)
        assert ref["g"]["beat"] == g["beat"] and ref["g"]["phase"] == pytest.approx(g["phase"], abs=1e-9)
        assert ref["g"]["bar"] == g["bar"] and ref["g"]["spb"] == pytest.approx(g["spb"])
        assert ref["q2"] == pytest.approx(beat.quantize(t, 120, 2), abs=1e-6)
        assert ref["q4"] == pytest.approx(beat.quantize(t, 120, 4), abs=1e-6)
        assert ref["floor"] == pytest.approx(beat.quantize(t, 120, 4, mode="floor"), abs=1e-6)
        assert ref["ping"] == pytest.approx(beat.ping(t, 120), abs=1e-9)
        assert ref["swell"] == pytest.approx(beat.swell(t, 120), abs=1e-9)
        assert ref["ladder"] == pytest.approx(beat.ladder(t, 120, 0, 3), abs=1e-9)
        assert ref["off"] == pytest.approx(beat.offset_of(t, 120, 2), abs=1e-6)


def test_grid_cues_sit_exactly_on_the_sixteenths():
    cues = sfx.grid_cues("k.h.|k.hh|k.h.|k...", 120, bars=1)
    step = 60 / 120 / 4
    assert len(cues) == 8
    # every cue lands on a sixteenth of the grid
    for cue in cues:
        assert abs(cue["t"] / step - round(cue["t"] / step)) < 1e-6
    assert [c["sfx"] for c in cues][:3] == ["impact", "tick", "impact"]
    assert cues[0]["gain"] == 1.0 and cues[1]["gain"] < 1.0      # the kick is the loudest step
    # a short pattern tiles inside the 16-step bar, and `bars` really means bars
    two = sfx.grid_cues("k.h.", 120, bars=2)
    assert len(two) == 16
    assert two[8]["t"] - two[0]["t"] == pytest.approx(beat.bar_seconds(120))   # second bar repeats
    assert sfx.grid_cues("k.h.", 120, bars=1)[-1]["t"] < beat.bar_seconds(120)
    assert sfx.bars_seconds(120, 2) == pytest.approx(4.0)


def test_grid_cues_rejects_unknown_steps():
    with pytest.raises(ValueError, match="unknown grid step"):
        sfx.grid_cues("k.x.", 120, 1)


def test_grid_cues_feed_the_mixer(tmp_path):
    """End to end: a grid cue sheet mixes into a real bus of the VO's length."""
    cues = tmp_path / "cues.json"
    cues.write_text(json.dumps(sfx.grid_cues("k.h.k.h.", 120, bars=2)), encoding="utf-8")
    import numpy as np  # noqa: PLC0415

    bus = sfx.bus(sfx.bars_seconds(120, 2), json.loads(cues.read_text(encoding="utf-8")))
    sr = sfx.SR
    assert bus.shape[0] == pytest.approx(4.0 * sr, abs=2)
    assert np.abs(bus).max() > 0.05
    # the kick at t=0 actually starts inside the first milliseconds, not a beat late
    assert np.abs(bus[:400]).max() > 0.01
    assert math.isclose(float(np.abs(bus[-100:]).max()), float(np.abs(bus[-100:]).max()))
