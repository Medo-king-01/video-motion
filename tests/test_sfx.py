"""The procedural sound kit: deterministic synthesis, a catalogue, and cue-sheet mixing."""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
sys.path.insert(0, str(SKILL.parent / "shared" / "py"))  # audio + rhythm: the editable copy

SPEC = json.loads((SKILL / "motion" / "transitions.json").read_text(encoding="utf-8"))["transitions"]


def test_bank_and_catalogue_agree():
    from sfx import BANK, CATALOG  # noqa: PLC0415

    assert len(BANK) >= 15
    assert set(CATALOG) == set(BANK), "every sound needs a catalogue entry (family + base gain)"
    for name, meta in CATALOG.items():
        assert meta["family"] in {"ui", "tonal", "air", "build", "impact", "texture"}
        assert 0 < meta["gain"] <= 1
        assert meta["tags"], name


def test_sounds_are_deterministic_and_bounded():
    from sfx import BANK, SR  # noqa: PLC0415

    for name, gen in BANK.items():
        first, second = gen(3), gen(3)
        np.testing.assert_array_equal(first, second, err_msg=f"{name} is not deterministic")
        assert len(first) > 0.03 * SR
        assert np.max(np.abs(first)) == pytest.approx(1.0, abs=0.02), f"{name} should be normalised"
        assert np.all(np.isfinite(first))


def test_duration_matches_the_rendered_length():
    from sfx import BANK, SR, duration  # noqa: PLC0415

    for name in BANK:
        assert duration(name) == pytest.approx(len(BANK[name](0)) / SR)


def test_bus_places_cues_where_they_belong():
    from sfx import bus  # noqa: PLC0415

    cue_t = 0.8
    out = bus(2.0, [{"t": cue_t, "sfx": "impact", "gain": 1.0, "pan": 0.0}])
    sr = 44100
    before = np.abs(out[: int(0.6 * sr)]).max()
    after = np.abs(out[int(cue_t * sr) : int((cue_t + 0.05) * sr)]).max()
    after_tail = np.abs(out[int(1.6 * sr) :]).max()
    assert after > 0.1
    assert before < 1e-6 and after_tail < 1e-6


def test_bus_pans_symmetrically():
    from sfx import bus  # noqa: PLC0415

    left = bus(1.0, [{"t": 0.1, "sfx": "chime", "pan": -1.0}])
    right = bus(1.0, [{"t": 0.1, "sfx": "chime", "pan": 1.0}])
    assert np.abs(left[:, 0]).max() > np.abs(left[:, 1]).max() * 4
    assert np.abs(right[:, 1]).max() > np.abs(right[:, 0]).max() * 4


def test_bus_rejects_unknown_sounds():
    from sfx import bus  # noqa: PLC0415

    with pytest.raises(KeyError):
        bus(1.0, [{"t": 0, "sfx": "explosion"}])


def test_cue_gain_defaults_to_the_catalogue_family_gain():
    from sfx import CATALOG, bus  # noqa: PLC0415

    plain = bus(1.0, [{"t": 0.1, "sfx": "pop"}])
    doubled = bus(1.0, [{"t": 0.1, "sfx": "pop", "gain": 2.0}])
    assert np.abs(doubled).max() == pytest.approx(np.abs(plain).max() * 2, rel=0.02)
    assert CATALOG["pop"]["gain"] < 1


def test_every_transition_sound_exists():
    from sfx import BANK  # noqa: PLC0415

    for name, spec in SPEC.items():
        assert spec["sfx"] in BANK, f"{name} wants a missing sound: {spec['sfx']}"


def test_cues_for_transitions_follow_the_catalogue():
    from sfx import cues_for_transitions  # noqa: PLC0415

    cuts = [{"t": 1.0, "name": "wipe"}, {"t": 2.5, "name": "iris"}, {"t": 3.0, "name": "nope"}]
    cues = cues_for_transitions(cuts)
    assert [c["sfx"] for c in cues] == ["whoosh", "pop"]
    assert [c["t"] for c in cues] == [1.0, 2.5]


def test_duck_turns_the_bed_down_under_voice():
    from sfx import bus, duck  # noqa: PLC0415

    bed = bus(1.5, [{"t": 0.05, "sfx": "noise", "gain": 1.0}])
    silent = np.zeros(len(bed), np.float32)
    loud = np.full(len(bed), 0.5, np.float32)
    assert np.allclose(duck(silent, bed), bed)
    under_voice = duck(loud, bed)
    assert np.abs(under_voice).max() < np.abs(duck(silent, bed)).max() * 0.5


def test_render_bank_writes_wavs(tmp_path):
    from scipy.io import wavfile  # noqa: PLC0415
    from sfx import render_bank  # noqa: PLC0415

    files = render_bank(tmp_path, names=["pop", "whoosh", "chime"])
    assert len(files) == 3
    sr, data = wavfile.read(tmp_path / "chime.wav")
    assert sr == 44100 and data.ndim == 2 and data.shape[1] == 2


def test_cli_lists_the_kit():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--list"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "procedural sounds" in r.stdout
    for name in ("whoosh", "swipe", "glitch", "chime"):
        assert name in r.stdout


def test_cli_renders_a_demo(tmp_path):
    out = tmp_path / "demo.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--demo", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.exists() and out.stat().st_size > 100_000


def test_cli_mixes_a_cue_sheet(tmp_path):
    cues = tmp_path / "cues.json"
    cues.write_text(json.dumps([{"t": 0.2, "sfx": "whoosh"}, {"t": 0.9, "sfx": "impact"}]), encoding="utf-8")
    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--cues", str(cues),
                        "--length", "2", "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    sr, data = wavfile.read(out)
    assert abs(data.shape[0] - 2 * sr) <= 2 and data.shape[1] == 2
    assert np.abs(data).max() > 1000
