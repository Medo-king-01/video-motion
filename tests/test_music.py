"""The procedural music engine: determinism, BPM, layers, presets, sample rates, sections.

A bed is only useful if it is *predictable*: the same seed has to give the same samples, the length
has to be exact (the reel is cut to the picture, not to the music), and asking for 48 kHz must change
the rate and nothing else. Each test here pins one of those promises with a short bed (≤ 6 s) so the
normal cycle stays fast.
"""
from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))

PRESETS = ("tech", "minimal", "corporate", "energetic", "cinematic", "ambient")


def rms(x) -> float:
    return float(np.sqrt(np.mean(np.asarray(x, np.float64) ** 2)))


def test_the_data_file_exists_and_is_complete():
    data = json.loads((SKILL / "motion" / "music-presets.json").read_text(encoding="utf-8"))
    assert set(data["presets"]) == set(PRESETS)
    for name, preset in data["presets"].items():
        for key in ("bpm", "key", "scale", "progression", "sections", "layers", "groove", "tone", "why"):
            assert key in preset, f"preset {name} is missing {key}"
        assert 40 <= preset["bpm"] <= 220
        assert preset["key"] in data["keys"]["values"]
        assert preset["scale"] in data["scales"]
        assert preset["progression"], f"{name}: needs a chord progression"
        assert any(v > 0 for v in preset["layers"].values()), f"{name}: every layer is muted"
    for name, scale in data["scales"].items():
        assert 5 <= len(scale["semitones"]) <= 7, name
        assert scale["semitones"][0] == 0 and all(0 <= s < 12 for s in scale["semitones"])


def test_presets_differ_musically_not_just_in_volume():
    """The acceptance criterion: six presets that are actually six different pieces of music."""
    import music

    data = music.presets()
    signatures = {}
    for name in PRESETS:
        p = data[name]
        signatures[name] = (p["bpm"], p["key"], p["scale"], tuple(p["progression"]),
                            tuple(sorted((k, v) for k, v in p["layers"].items() if v > 0)),
                            tuple(sorted(p["groove"].items())))
    assert len(set(signatures.values())) == len(PRESETS), "two presets are the same arrangement"
    # no two presets may share key+scale (that is the whole point of a musical difference)
    tonal = [(p["key"], p["scale"]) for p in data.values()]
    assert len(set(tonal)) == len(PRESETS)


def test_renders_are_deterministic_and_float32_stereo():
    import music

    cfg = music.MusicConfig(preset="tech", duration=4.0, seed=11)
    a = music.render_music(cfg)
    b = music.render_music(cfg)
    assert a.dtype == np.float32 and a.ndim == 2 and a.shape[1] == 2
    np.testing.assert_array_equal(a, b)
    assert np.all(np.isfinite(a)) and np.max(np.abs(a)) <= 1.0


def test_a_different_seed_gives_different_audio():
    import music

    a = music.render_music(music.MusicConfig(preset="tech", duration=4.0, seed=1))
    b = music.render_music(music.MusicConfig(preset="tech", duration=4.0, seed=2))
    assert not np.array_equal(a, b)
    assert float(np.corrcoef(a.mean(1), b.mean(1))[0, 1]) < 0.999


@pytest.mark.parametrize("duration", [3.0, 7.5, 12.0])
def test_duration_is_exact(duration):
    import music

    for name in ("tech", "ambient"):
        audio = music.render_music(music.MusicConfig(preset=name, duration=duration))
        assert audio.shape[0] == int(round(duration * 44100)), name


def test_bpm_sets_the_bar_length_and_the_grid():
    import music

    slow = music.music_info(music.MusicConfig(preset="tech", duration=8.0, bpm=90))
    fast = music.music_info(music.MusicConfig(preset="tech", duration=8.0, bpm=140))
    assert slow["barSeconds"] == pytest.approx(240 / 90)
    assert fast["barSeconds"] == pytest.approx(240 / 140)
    assert slow["sixteenthSeconds"] == pytest.approx(60 / 90 / 4, rel=1e-4)


def test_sections_fill_the_duration_and_keep_their_order():
    import music

    for name in PRESETS:
        info = music.music_info(music.MusicConfig(preset=name, duration=20.0))
        spans = info["sections"]
        assert spans[0]["start"] == 0.0
        assert spans[-1]["end"] == pytest.approx(20.0, abs=1e-6)
        for a, b in zip(spans, spans[1:]):
            assert a["end"] == pytest.approx(b["start"], abs=1e-6), f"{name}: gap between sections"
        order = [spans.index(s) for s in spans]
        assert order == sorted(order)
        assert any(s["name"] == "drop" for s in spans), f"{name}: a bed without a drop is a pad"


def test_explicit_sections_are_respected():
    import music

    cfg = music.MusicConfig(preset="tech", duration=8.0, sections=[
        {"name": "drop", "start": 0, "end": 3}, {"name": "stop", "start": 3, "end": 4},
        {"name": "drop", "start": 4, "end": 8}])
    info = music.music_info(cfg)
    assert [s["name"] for s in info["sections"]] == ["drop", "stop", "drop"]
    audio = music.render_music(cfg)
    sr = 44100
    quiet = audio[int(3.05 * sr):int(3.95 * sr)]
    assert float(np.max(np.abs(quiet))) < 1e-6, "a stop section must be true silence"
    assert rms(audio[int(4.1 * sr):int(5.0 * sr)]) > 0.01, "and the music must come back"


def test_layers_are_independently_mixable():
    import music

    base = dict(preset="tech", duration=6.0, seed=5)
    full = music.render_music(music.MusicConfig(**base))
    for layer in music.LAYERS:
        solo = music.render_music(music.MusicConfig(
            **{**base, "layers": {name: (1.0 if name == layer else 0.0) for name in music.LAYERS}}))
        assert rms(solo) > 1e-3, f"layer {layer} produced silence"
        # a solo layer must not be *louder* than the whole arrangement: that would mean peak
        # normalisation is doing the mixing and the layer controls are meaningless
        assert rms(solo) <= rms(full) * 1.25, f"layer {layer} alone is louder than the full bed"
    muted = music.render_music(music.MusicConfig(
        **{**base, "layers": {name: 0.0 for name in music.LAYERS}}))
    assert rms(muted) < 1e-4, "every layer muted must be silent"


def test_louder_layer_level_really_changes_the_balance():
    import music

    base = dict(preset="tech", duration=6.0, seed=5)
    quiet_hat = music.render_music(music.MusicConfig(**base, layers={"hat": 0.05}))
    loud_hat = music.render_music(music.MusicConfig(**base, layers={"hat": 1.0}))
    # the hats live above 6 kHz: a spectral test is the only fair one
    def high_energy(x):
        spec = np.abs(np.fft.rfft(x.mean(1)))
        freq = np.fft.rfftfreq(len(x), 1 / 44100)
        return float(spec[freq > 6000].sum())

    assert high_energy(loud_hat) > high_energy(quiet_hat) * 1.2


def test_both_sample_rates_produce_the_same_music():
    import music

    cfg = music.MusicConfig(preset="cinematic", duration=5.0, seed=3)
    a = music.render_music(cfg)
    b = music.render_music(music.MusicConfig(**{**cfg.__dict__, "sr": 48000}))
    assert b.shape[0] == int(round(5.0 * 48000))
    assert abs(a.shape[0] / 44100 - b.shape[0] / 48000) < 1e-9
    # same piece of music: compare coarse energy over the same time windows
    for i in range(5):
        wa = a[int(i * 44100):int((i + 1) * 44100)]
        wb = b[int(i * 48000):int((i + 1) * 48000)]
        assert abs(rms(wa) - rms(wb)) < 0.02, f"second {i} differs between rates"


def test_energy_and_swing_are_audible_controls():
    import music

    calm = music.render_music(music.MusicConfig(preset="tech", duration=6.0, energy=0.2))
    hot = music.render_music(music.MusicConfig(preset="tech", duration=6.0, energy=1.8))
    assert not np.allclose(calm, hot)
    straight = music.render_music(music.MusicConfig(preset="tech", duration=6.0, swings=0.0))
    swung = music.render_music(music.MusicConfig(preset="tech", duration=6.0, swings=0.25))
    assert not np.array_equal(straight, swung)


def test_key_and_scale_change_the_notes():
    import music

    cfg = dict(preset="corporate", duration=4.0, layers={"pluck": 1.0, "pad": 0.0, "kick": 0.0})
    a = music.render_music(music.MusicConfig(**cfg, key="C", scale="major"))
    b = music.render_music(music.MusicConfig(**cfg, key="F#", scale="minor"))
    fa = float(np.argmax(np.abs(np.fft.rfft(a.mean(1))[10:800]))) + 10
    fb = float(np.argmax(np.abs(np.fft.rfft(b.mean(1))[10:800]))) + 10
    assert fa != fb, "transposing the bed must move the spectrum"


def test_bad_input_fails_early_and_clearly():
    import music

    with pytest.raises(ValueError):
        music.MusicConfig(preset="techno")
    with pytest.raises(ValueError):
        music.MusicConfig(duration=0)
    with pytest.raises(ValueError):
        music.MusicConfig(duration=-3)
    with pytest.raises(ValueError):
        music.MusicConfig(bpm=10)
    with pytest.raises(ValueError):
        music.MusicConfig(key="H")
    with pytest.raises(ValueError):
        music.MusicConfig(layers={"cowbell": 1.0})
    with pytest.raises(TypeError):
        music.MusicConfig(seed=1.5)


def test_the_phone_layer_keeps_the_pulse_above_150_hz():
    """A phone speaker deletes everything below ~150 Hz; the bed still has to have a beat there."""
    import music

    for name in ("tech", "energetic", "corporate"):
        audio = music.render_music(music.MusicConfig(preset=name, duration=6.0, seed=2))
        spec = np.abs(np.fft.rfft(audio.mean(1)))
        freq = np.fft.rfftfreq(len(audio), 1 / 44100)
        low = spec[(freq > 20) & (freq < 150)].sum()
        mid = spec[(freq > 400) & (freq < 3200)].sum()
        assert mid > low * 0.5, f"{name}: the bed would disappear on a phone ({mid / low:.2f})"


def test_cli_lists_presets_and_renders_a_bed(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "music_kit.py"), "--presets"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    for name in PRESETS:
        assert name in r.stdout
    out = tmp_path / "bed.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "music_kit.py"), "--render", str(out),
                        "--preset", "energetic", "--duration", "3", "--sr", "48000"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    sr, data = wavfile.read(out)
    assert sr == 48000 and data.shape == (3 * 48000, 2)


def test_cli_refuses_to_overwrite(tmp_path):
    out = tmp_path / "bed.wav"
    args = [sys.executable, str(ROOT / "tools" / "music_kit.py"), "--render", str(out), "--duration", "2"]
    assert subprocess.run(args, capture_output=True, text=True).returncode == 0
    again = subprocess.run(args, capture_output=True, text=True)
    assert again.returncode != 0 and "exists" in (again.stdout + again.stderr)
    assert subprocess.run(args + ["--force"], capture_output=True, text=True).returncode == 0


def test_cli_info_is_valid_json(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "music_kit.py"), "--info", "--preset", "minimal",
                        "--duration", "6"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    info = json.loads(r.stdout)
    assert info["preset"] == "minimal" and info["samples"] == int(6 * 44100)


def test_presets_are_level_matched_by_the_measured_trim():
    """`levelTrimDb` is measured, not taste: six presets must sit within a few dB of each other."""
    import audio_engine as ax
    import music

    levels = {}
    for name in PRESETS:
        audio = music.render_music(music.MusicConfig(preset=name, duration=8.0, seed=5))
        levels[name] = ax.to_db(float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))))
    spread = max(levels.values()) - min(levels.values())
    assert spread < 4.0, f"presets are not level matched: {[(k, round(v, 1)) for k, v in levels.items()]}"
    for name, preset in music.presets().items():
        assert "levelTrimDb" in preset, f"{name} has no measured level trim"


def test_a_short_bed_does_not_fade_itself_away():
    """A fixed 1.2 s fade-out on a 5 s sting silences a quarter of the music — fades are proportional."""
    import audio_engine as ax
    import music

    audio = music.render_music(music.MusicConfig(preset="tech", duration=5.0, fade_out=1.2))
    head = ax.to_db(float(np.sqrt(np.mean(audio[int(1.5 * 44100):int(2.5 * 44100)] ** 2))))
    tail = ax.to_db(float(np.sqrt(np.mean(audio[int(3.0 * 44100):int(3.5 * 44100)] ** 2))))
    assert tail > head - 14, f"the tail vanished on a short bed ({tail:.1f} vs {head:.1f} dBFS)"
