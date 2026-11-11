"""The SFX upgrades: anchors, honest truncation, real ducking, layers, overwrite guards, rate honesty.

`tests/test_sfx.py` pins the *old* contract (15 generators, catalogue, bus, duck, grid cues) and must
keep passing untouched. This file pins what was added and what was fixed, and — importantly — that
every one of those additions is backward compatible.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
sys.path.insert(0, str(SKILL.parent / "shared" / "py"))  # audio + rhythm: the editable copy

SR = 44100
# The 15 generators that existed before this work. Losing one is a regression, not a refactor.
LEGACY = ("pop", "tick", "click", "zip", "whoosh", "riser", "impact", "stomp", "sparkle",
          "swipe", "noise", "glitch", "chime", "sub", "blip")


def test_every_original_generator_survives():
    import sfx

    for name in LEGACY:
        assert name in sfx.BANK, f"{name} disappeared from the kit"
        assert name in sfx.CATALOG
        first, second = sfx.BANK[name](3), sfx.BANK[name](3)
        np.testing.assert_array_equal(first, second)
        assert np.max(np.abs(first)) == pytest.approx(1.0, abs=0.02)


def test_new_sounds_fill_real_gaps_and_are_catalogued():
    import sfx

    added = set(sfx.BANK) - set(LEGACY)
    assert added == {"snap", "page", "coin", "heartbeat", "vinyl"}
    for name in added:
        assert sfx.CATALOG[name]["tags"], name
        assert 0 < sfx.CATALOG[name]["gain"] <= 1
        assert sfx.duration(name) > 0.01


def test_generators_render_natively_at_48k():
    """The defect: `bp()` baked SR/2 in at import, so 48 kHz silently used 44.1 kHz filters."""
    import sfx

    for name in sfx.BANK:
        a = sfx.BANK[name](0, sr=48000)
        assert len(a) == pytest.approx(len(sfx.BANK[name](0)) * 48000 / SR, rel=0.02), name
        assert np.all(np.isfinite(a)) and np.max(np.abs(a)) <= 1.001, name


def test_filters_follow_the_rate_they_are_given():
    import sfx

    noise = np.random.default_rng(0).normal(0, 1, 48000)
    out = sfx.bp(noise, 1200, 8000, 48000)          # must not raise and must not be silent
    assert np.all(np.isfinite(out)) and np.std(out) > 0
    # above Nyquist at 8 kHz: clamped, not an exception
    assert np.all(np.isfinite(sfx.lp(noise[:8000], 20000, 8000)))


def test_anchors_put_the_event_where_the_cue_says():
    import sfx

    assert sfx.anchor("impact") == 0.0 and sfx.anchor("pop") == 0.0
    assert sfx.anchor("riser") == pytest.approx(sfx.duration("riser"), rel=0.01)
    for name in ("whoosh", "swipe", "page"):
        a = sfx.anchor(name)
        assert 0.0 < a < sfx.duration(name), name


def test_bus_is_anchored_only_when_asked_so_existing_edits_do_not_move():
    import sfx

    plain = sfx.bus(2.0, [{"t": 1.0, "sfx": "whoosh"}])
    anchored = sfx.bus(2.0, [{"t": 1.0, "sfx": "whoosh"}], tail=True, anchored=True)

    def peak_time(buf):
        env = np.convolve(np.abs(buf).mean(1), np.ones(128) / 128, "same")
        return float(np.argmax(env)) / SR

    assert peak_time(plain) > 1.15, "default behaviour must stay 'the buffer starts at t'"
    assert peak_time(anchored) == pytest.approx(1.0, abs=0.12), "anchored: the event lands at t"


def test_truncation_is_reported_instead_of_silently_eaten():
    import sfx

    short = sfx.bus(0.2, [{"t": 0.0, "sfx": "impact"}])
    assert short.shape[0] == int(0.2 * SR) + 1
    assert sfx.bus.last_truncated > 0, "a 0.7 s impact in a 0.2 s bus must be visible"
    full = sfx.bus(0.2, [{"t": 0.0, "sfx": "impact"}], tail=True)
    assert full.shape[0] > short.shape[0]
    assert sfx.bus.last_truncated == 0


def test_duck_keeps_the_bus_length_and_ducks_quiet_audio():
    import sfx

    bed = sfx.bus(1.5, [{"t": 0.05, "sfx": "noise", "gain": 1.0}])
    vo = np.zeros(int(1.0 * SR), np.float32)          # shorter than the bus — the old bug
    vo[int(0.2 * SR):int(0.9 * SR)] = 0.03            # and quiet
    out = sfx.duck(vo, bed)
    assert out.shape == bed.shape, "duck() truncated the bus to the length of the voice"
    seg = slice(int(0.35 * SR), int(0.8 * SR))
    ratio = float(np.abs(out[seg]).mean() / max(np.abs(bed[seg]).mean(), 1e-12))
    assert ratio < 0.9, f"a quiet narration line did not duck the bed (ratio {ratio:.3f})"


def test_duck_accepts_the_old_keyword_arguments():
    import sfx

    bed = sfx.bus(1.0, [{"t": 0.0, "sfx": "noise"}])
    vo = np.full(len(bed), 0.4, np.float32)
    for kw in ({"depth": 0.62}, {"depth": 0.62, "release": 6.0}, {"depth": 0.5, "attack": 0.02}):
        out = sfx.duck(vo, bed, **kw)
        assert out.shape == bed.shape and np.all(np.isfinite(out))


def test_layered_cues_stack_sounds_at_one_instant():
    import sfx

    plain = sfx.bus(1.0, [{"t": 0.1, "sfx": "click"}])
    layered = sfx.bus(1.0, [{"t": 0.1, "sfx": "click",
                             "layer": [{"sfx": "click"}, {"sfx": "tick", "gain": 0.8}]}])
    assert np.abs(layered).sum() > np.abs(plain).sum()
    win = slice(int(0.1 * SR), int(0.2 * SR))
    assert np.abs(layered[win]).max() > np.abs(plain[win]).max()


def test_render_bank_never_overwrites_by_accident(tmp_path):
    import sfx

    sfx.render_bank(tmp_path, names=["pop"])
    with pytest.raises(FileExistsError):
        sfx.render_bank(tmp_path, names=["pop"])
    assert sfx.render_bank(tmp_path, names=["pop"], overwrite=True)
    assert sfx.render_bank(tmp_path, names=["pop"], sr=48000, overwrite=True)


def test_render_bank_can_render_at_48k(tmp_path):
    import sfx
    from scipy.io import wavfile

    sfx.render_bank(tmp_path, names=["whoosh"], sr=48000)
    sr, data = wavfile.read(tmp_path / "whoosh.wav")
    assert sr == 48000 and data.shape[1] == 2


def test_transition_sfx_still_come_from_transitions_json_and_can_be_accented():
    import sfx

    cuts = [{"t": 1.0, "name": "flash"}, {"t": 2.0, "name": "wipe"}, {"t": 3.0, "name": "nope"}]
    assert [c["sfx"] for c in sfx.cues_for_transitions(cuts)] == ["impact", "whoosh"]
    accented = sfx.accent_cues(cuts, moment="beat")
    beats = [c for c in accented if c["sfx"]]           # flash+beat has an accent, wipe+beat does not
    assert [c["sfx"] for c in accented] == ["stomp"]
    for cue in beats:
        assert cue["layer"] and len(cue["layer"]) >= 2
    assert sfx.accent_cues(cuts, moment="nonexistent") == []


def test_cues_for_transitions_lead_shifts_every_cue():
    import sfx

    cuts = [{"t": 2.0, "name": "wipe"}, {"t": 4.0, "name": "iris"}]
    assert [c["t"] for c in sfx.cues_for_transitions(cuts, lead=-0.18)] == [1.82, 3.82]
    assert [c["t"] for c in sfx.cues_for_transitions(cuts)] == [2.0, 4.0]


def test_grid_cues_still_snap_to_the_beat():
    import sfx

    cues = sfx.grid_cues("k.h.|k.h.", 120, bars=2)
    assert cues[0]["t"] == 0.0 and cues[1]["t"] == pytest.approx(0.25)
    assert sfx.bars_seconds(120, 2) == pytest.approx(4.0)


def test_cli_can_render_the_bank_at_48k(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--bank", str(tmp_path),
                        "--sr", "48000"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    for name in ("impact", "whoosh"):
        sr, data = wavfile.read(tmp_path / f"{name}.wav")
        assert sr == 48000 and data.shape[1] == 2


def test_cli_json_catalogue_matches_the_module():
    import sfx

    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--list", "--json"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert set(data) == set(sfx.BANK)
    for name, meta in data.items():
        assert meta["family"] == sfx.CATALOG[name]["family"]
        assert meta["seconds"] == pytest.approx(sfx.duration(name), abs=1e-3)


def test_an_early_riser_is_clipped_not_reported_as_truncated():
    """A riser anchored at 0.5 s starts at -0.1 s on purpose; that is not a defect."""
    import sfx

    sfx.bus(20.0, [{"t": 0.5, "sfx": "riser", "anchor": True}])
    assert sfx.bus.last_truncated == 0, "a cue starting before 0 must not read as truncation"
    assert sfx.bus.last_clipped > 0, "and the clipped head must still be reported separately"
    sfx.bus(0.2, [{"t": 0.0, "sfx": "impact"}])
    assert sfx.bus.last_truncated > 0, "a real overrun is still truncation"
    assert sfx.bus.last_clipped == 0
