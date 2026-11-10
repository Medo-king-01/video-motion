"""Contracts for `tools/audio_generate.py` — the SFX/bed generator had no tests at all.

These pin the parts other code depends on: the 48 kHz sample rate, the 24-bit WAV
round-trip with its sample-rate guard, the deterministic `SFX` generator and its
anchor values, the beat-synced bed length, `resolve_at` cue resolution, and the
`--audition` CLI path (which never touches ffmpeg).
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
from conftest import ROOT

TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import audio_generate as ag  # noqa: E402

AUDITION_KINDS = (
    "whoosh", "reverse-whoosh", "riser", "impact", "boom", "sub-drop", "glitch",
    "tick", "typing", "shimmer", "pop", "swoosh-pass", "scratch", "slide",
)


def timeline() -> dict:
    return {
        "duration": 6.0,
        "bpm": 120,
        "beatsPerBar": 4,
        "beatOffset": 0.25,
        "scenes": [
            {"id": "s1", "start": 0.0, "end": 2.0},
            {"id": "s2", "start": 2.0, "end": 4.0},
        ],
        "vo": [
            {"id": "l1", "start": 0.5, "end": 1.5, "words": [{"s": 0.5}, {"s": 0.9}]},
        ],
    }


# ── sample rate, helpers ─────────────────────────────────────────────────────
def test_the_project_runs_at_48k():
    assert ag.SR == 48000


def test_db_is_a_decibel_gain():
    assert ag.db(0) == pytest.approx(1.0)
    assert ag.db(-6) == pytest.approx(0.5012, abs=1e-4)
    assert ag.db(20) == pytest.approx(10.0)


def test_tvec_returns_exact_seconds():
    t = ag.tvec(0.5)
    assert t.shape == (24000,)
    assert t[0] == 0.0 and t[-1] == pytest.approx(23999 / 48000, abs=1e-9)


def test_st_makes_constant_power_stereo():
    mono = np.ones(64, dtype=np.float32)
    centre = ag.st(mono, 0.0)
    assert centre.shape == (64, 2)
    assert np.allclose(centre[0] ** 2 + centre[1] ** 2, 1.0, atol=1e-6)
    left = ag.st(mono, -1.0)
    assert left[0, 1] == pytest.approx(0.0, abs=1e-6) and left[0, 0] > 0.9


def test_norm_peaks_at_the_requested_level():
    x = np.array([[0.2, -0.4], [0.1, 0.05]], dtype=np.float32)
    assert np.max(np.abs(ag.norm(x, 0.8))) == pytest.approx(0.8, abs=1e-6)


def test_sine_has_the_requested_frequency():
    n = ag.SR // 2
    spectrum = np.abs(np.fft.rfft(ag.sine(1000.0, n)))
    peak_hz = np.fft.rfftfreq(n, 1 / ag.SR)[int(np.argmax(spectrum))]
    assert peak_hz == pytest.approx(1000.0, abs=2.0)


def test_polyblep_saw_stays_bounded_and_is_not_a_pure_sine():
    saw = ag.polyblep_saw(220.0, ag.SR)
    assert np.max(np.abs(saw)) <= 1.5
    assert np.std(np.diff(saw)) > 0


def test_env_ad_shape_and_range():
    env = ag.env_ad(1000, 0.01, 0.1)
    assert env.shape == (1000,)
    assert env.max() <= 1.0 + 1e-6 and env.min() >= -1e-6


# ── WAV io ───────────────────────────────────────────────────────────────────
def test_24bit_wav_roundtrip_keeps_the_signal(tmp_path):
    t = ag.tvec(0.1)
    x = ag.st(np.float32(0.5) * np.sin(ag.TAU * 440 * t))
    path = tmp_path / "tone.wav"
    ag.write_wav(path, x)
    with wave.open(str(path), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (48000, 2, 3)
    left = ag.read_wav_ch(path, 0)
    assert np.max(np.abs(left - x[:, 0])) < 1e-3
    assert np.max(np.abs(ag.read_wav(path) - x.mean(axis=1))) < 1e-3


def test_read_wav_rejects_a_foreign_sample_rate(tmp_path):
    path = tmp_path / "44k.wav"
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(44100)
        w.writeframes(np.zeros(100, dtype="<i2").tobytes())
    with pytest.raises(RuntimeError, match="44100"):
        ag.read_wav(path)


# ── SFX generator ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("kind", AUDITION_KINDS)
def test_every_documented_sfx_returns_stereo_and_an_anchor(kind):
    samples, anchor = ag.SFX(7).make(kind)
    assert samples.ndim == 2 and samples.shape[1] == 2
    assert samples.shape[0] > 0 and np.all(np.isfinite(samples))
    assert np.max(np.abs(samples)) <= 1.0
    assert isinstance(anchor, float) and anchor >= 0.0


def test_sfx_is_deterministic_for_a_seed():
    first = ag.SFX(11).make("whoosh")[0]
    second = ag.SFX(11).make("whoosh")[0]
    assert np.array_equal(first, second)


def test_a_different_seed_changes_noise_based_sfx():
    assert not np.array_equal(ag.SFX(1).make("glitch")[0], ag.SFX(2).make("glitch")[0])


def test_unknown_sfx_is_a_loud_error():
    with pytest.raises(SystemExit, match="نوع مؤثر"):
        ag.SFX(7).make("not-a-real-sfx")


def test_an_impact_anchors_on_its_transient():
    _, anchor = ag.SFX(7).make("impact")
    assert anchor == 0.0


# ── bed ──────────────────────────────────────────────────────────────────────
def test_bed_matches_the_video_length_and_is_stereo():
    bed = ag.build_bed(timeline(), {"level": -12}, 2.0, seed=5)
    assert bed.shape == (int(np.ceil(2.0 * ag.SR)), 2)
    assert np.all(np.isfinite(bed)) and np.max(np.abs(bed)) > 0


def test_bed_is_reproducible():
    tl = timeline()
    assert np.array_equal(
        ag.build_bed(tl, {}, 1.0, seed=3),
        ag.build_bed(tl, {}, 1.0, seed=3),
    )


# ── cue resolution ───────────────────────────────────────────────────────────
def test_sections_fall_back_to_the_last_one():
    secs = [{"name": "intro", "start": 0, "end": 1}, {"name": "drop", "start": 1, "end": 3}]
    assert ag.section_at(secs, 0.5) == "intro"
    assert ag.section_at(secs, 2.9) == "drop"
    assert ag.section_at(secs, 99.0) == "drop"


@pytest.mark.parametrize(
    ("at", "expected"),
    [
        (1.25, 1.25),
        ("scene:s2", 2.0),
        ("scene-end:s1", 2.0),
        ("line:l1", 0.5),
        ("line-end:l1", 1.5),
        ("word:l1:1", 0.9),
        ("beat:2", 1.25),
        ("bar:1", 2.25),
        ("scene:s1+0.5", 0.5),
        ("beat:0-0.25", 0.0),
    ],
)
def test_resolve_at_understands_every_cue_form(at, expected):
    assert ag.resolve_at(at, timeline()) == pytest.approx(expected)


def test_resolve_at_rejects_an_unknown_cue_kind():
    with pytest.raises(SystemExit, match="at غير مفهوم"):
        ag.resolve_at("mystery:s1", timeline())


# ── limiter ──────────────────────────────────────────────────────────────────
def test_limiter_holds_the_ceiling_without_hard_clipping():
    t = ag.tvec(0.1)
    loud = ag.st(np.float32(3.0) * np.sin(ag.TAU * 220 * t))
    limited = ag.limiter(loud, 0.7)
    assert np.max(np.abs(limited)) <= 0.7 + 1e-3
    assert np.unique(limited).size > 100  # gain-shaped, not a flat square wave
    assert np.corrcoef(limited[:, 0], loud[:, 0])[0, 1] > 0.9  # the waveform survives


# ── CLI ──────────────────────────────────────────────────────────────────────
def _project(tmp_path: Path) -> Path:
    project = tmp_path / "proj"
    (project / "renders").mkdir(parents=True)
    (project / "project.json").write_text(json.dumps({"music": {}}), encoding="utf-8")
    (project / "timeline.json").write_text(
        json.dumps({"duration": 1.0, "bpm": 120, "scenes": [{"id": "s1", "start": 0, "end": 1}]}),
        encoding="utf-8",
    )
    return project


def test_audition_writes_every_sfx_without_ffmpeg(tmp_path):
    project = _project(tmp_path)
    result = subprocess.run(
        [sys.executable, str(TOOLS / "audio_generate.py"), str(project), "--audition"],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        timeout=180,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    written = sorted(p.name for p in (project / "renders" / "audio").glob("sfx_*.wav"))
    assert written == sorted(f"sfx_{kind}.wav" for kind in AUDITION_KINDS)


def test_missing_project_json_fails_loudly_instead_of_writing_audio(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    result = subprocess.run(
        [sys.executable, str(TOOLS / "audio_generate.py"), str(empty)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "project.json" in result.stderr
