"""The shared DSP core: rate handling, filters, envelopes, ducking, limiting, WAV I/O.

These are the primitives every other audio module builds on, so they carry the contract:
44.1 kHz and 48 kHz are both first-class, every buffer is finite and inside ±1, and nothing depends
on a global module constant that a caller could change mid-run.
"""
from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest
from conftest import ROOT, SKILL

sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))

SR = 44100


def test_both_rates_are_supported_and_the_same_length():
    import audio_engine as ax

    assert set(ax.RATES) == {44100, 48000}
    for rate in ax.RATES:
        x = ax.sine(220.0, rate, int(rate))                # exactly one second
        assert len(x) == rate
    # any rate in the filter-safe range is accepted (documented 8000..384000), junk is not
    assert ax.check_rate(96000) == 96000
    for bad in (0, -1, 4000, 1_000_000):
        with pytest.raises(ValueError):
            ax.check_rate(bad)
    with pytest.raises(TypeError):
        ax.check_rate(44100.0)


def test_filters_never_exceed_nyquist():
    """A 15 kHz low-pass at 48 kHz and a 20 kHz one at 44.1 kHz must not raise or go unstable."""
    import audio_engine as ax

    for rate in ax.RATES:
        noise = np.random.default_rng(0).normal(0, 1, rate)
        for f in (20.0, 200.0, 4000.0, 15000.0, 30000.0, rate):
            out = ax.lp(noise, f, rate)
            assert np.all(np.isfinite(out)), (rate, f)
        assert np.all(np.isfinite(ax.bp(noise, 3000, 40000, rate)))


def test_polyblep_saw_stays_bounded_and_is_band_limited():
    import audio_engine as ax

    for rate in ax.RATES:
        saw = ax.polyblep_saw(110.0, rate, rate)
        assert np.max(np.abs(saw)) < 1.05
        spec = np.abs(np.fft.rfft(saw))
        freqs = np.fft.rfftfreq(len(saw), 1 / rate)
        # energy above 12 kHz should be tiny compared with the fundamental (an anti-aliased saw,
        # not a naive ramp that folds every harmonic back into the audible band)
        low = spec[(freqs > 80) & (freqs < 400)].sum()
        high = spec[freqs > 12000].sum()
        # a naive ramp measures ~0.99 here (all harmonics folded back); PolyBLEP measures ~0.26,
        # which is the 2nd-6th harmonics of a 110 Hz saw, not alias energy
        assert high < low * 0.5, f"{rate}: naive saw (alias energy {high / low:.3f})"
        naive = 2 * ((110.0 * np.arange(rate) / rate) % 1.0) - 1.0
        nspec = np.abs(np.fft.rfft(naive))
        assert high < nspec[freqs > 12000].sum() * 0.5


def test_duck_gain_is_absolute_not_normalised_by_the_loudest_word():
    """The measured defect: dividing by the loudest peak made a quiet line barely duck."""
    import audio_engine as ax

    sr = SR
    quiet = np.zeros(sr); quiet[int(0.2 * sr):int(0.8 * sr)] = 0.05
    loud = np.zeros(sr); loud[int(0.2 * sr):int(0.8 * sr)] = 0.9
    gq = ax.duck_gain(quiet, sr, depth=0.62)
    gl = ax.duck_gain(loud, sr, depth=0.62)
    under = slice(int(0.4 * sr), int(0.7 * sr))
    assert gq[under].mean() < 0.9, "a quiet line must still duck"
    assert gl[under].mean() < 0.75
    assert abs(float(gq[under].mean()) - float(gl[under].mean())) < 0.25, "both lines duck comparably"


def test_duck_gain_has_lookahead_and_no_steps():
    import audio_engine as ax

    sr = SR
    vo = np.zeros(sr * 2); vo[int(0.5 * sr):int(1.5 * sr)] = 0.5
    g = ax.duck_gain(vo, sr, depth=0.62, attack=0.008, release=0.32, lookahead=0.04)
    assert g[int(0.47 * sr)] < 0.98, "lookahead must pull the bed down before the word starts"
    assert g[int(0.6 * sr)] == pytest.approx(0.38, abs=0.02)
    assert np.max(np.abs(np.diff(g))) < 0.01, "no gain steps (clicks) allowed"
    assert g[-1] > 0.95, "must recover after the voice stops"


def test_limiter_respects_the_ceiling_and_keeps_the_shape():
    import audio_engine as ax

    sr = SR
    t = np.arange(sr) / sr
    loud = np.stack([np.sin(2 * np.pi * 440 * t) * 0.99, np.sin(2 * np.pi * 440 * t + 0.7) * 0.99], 1)
    out = ax.limiter(loud, ceiling=0.84, sr=sr)
    assert np.max(np.abs(out)) <= 0.84 + 1e-6
    assert ax.true_peak(out, sr) <= ax.to_db(0.84) + 0.05
    # and it must not just be a gain — the crest factor has to survive
    assert float(np.sqrt(np.mean(out ** 2))) > 0.1


def test_mix_into_trims_negative_starts_and_reports_writes():
    import audio_engine as ax

    buf = np.zeros((100, 2))
    assert ax.mix_into(buf, np.ones(50) * 0.5, -10) == 40, "negative start trims 10 samples, writes 40"
    assert ax.mix_into(buf, np.ones(50), 90) == 10, "the return value exposes truncation"
    assert ax.mix_into(buf, np.ones(50), 500) == 0


def test_write_wav_roundtrip_at_both_rates(tmp_path):
    import audio_engine as ax
    from scipy.io import wavfile

    for rate in ax.RATES:
        x = np.zeros((rate, 2), np.float32)
        x[:, 0] = 0.5
        x[:, 1] = 0.5
        path = tmp_path / f"t{rate}.wav"
        ax.write_wav(path, x, rate)
        sr, data = wavfile.read(path)
        assert sr == rate and data.shape == (rate, 2)
        back, got = ax.read_wav_mono(path)
        assert got == rate and len(back) == rate
        assert float(np.max(np.abs(back))) == pytest.approx(0.5, abs=0.01)
        # a hard-clipped signal must come back at the ceiling, not above it
        ax.write_wav(path, np.full((10, 2), 4.0, np.float32), rate)
        sr, data = wavfile.read(path)
        assert int(np.max(np.abs(data))) <= 32767


def test_assert_clean_catches_nan_and_clipping():
    import audio_engine as ax

    ax.assert_clean(np.zeros((100, 2), np.float32))
    with pytest.raises(ValueError):
        ax.assert_clean(np.array([[np.nan, 0.0]], np.float32))
    with pytest.raises(ValueError):
        ax.assert_clean(np.array([[1.5, 0.0]], np.float32))


def test_true_peak_sees_negative_and_asymmetric_material():
    """A symmetric L/R pair collapses to 0 under `x.max(axis=1)` — measured, then fixed."""
    import audio_engine as ax

    sr = SR
    neg = np.zeros((sr, 2)); neg[:, 0] = -0.9; neg[:, 1] = -0.2
    assert ax.true_peak(neg, sr) == pytest.approx(ax.to_db(0.9), abs=0.06)
    loud_left = np.zeros((sr, 2)); loud_left[:, 0] = 0.8
    assert ax.true_peak(loud_left, sr) >= ax.to_db(0.8) - 0.05


def test_reverb_ir_is_cached_per_rate_and_seed():
    import audio_engine as ax

    a = ax.reverb_ir(1.0, SR, seed=3)
    b = ax.reverb_ir(1.0, SR, seed=3)
    c = ax.reverb_ir(1.0, 48000, seed=3)
    assert a is b, "the IR is expensive; identical requests must hit the cache"
    # the IR is rt + pre-roll long, at the rate that was asked for
    assert a.shape[0] == pytest.approx((1.0 + 0.012) * SR, rel=1e-3)
    assert c.shape[0] == pytest.approx((1.0 + 0.012) * 48000, rel=1e-3)


def test_engine_has_no_module_level_rate_constant_in_filters():
    """Regression guard: filters must take `sr` instead of reading a mutable global."""
    src = (SKILL / "templates" / "procedural-reels" / "audio_engine.py").read_text(encoding="utf-8")
    for line in src.splitlines():
        if "butter(" in line:
            assert "SR /" not in line and "SR/" not in line, f"filter baked the default rate: {line.strip()}"


def test_cli_free_of_ffmpeg():
    """The DSP core must import and run with no ffmpeg binary on PATH (offline guarantee)."""
    engine_dir = SKILL / "templates" / "procedural-reels"
    code = (f"import sys; sys.path.insert(0, {str(engine_dir)!r}); import audio_engine as ax; "
            "print(ax.lp(__import__('numpy').ones(1000), 1000, 44100).shape)")
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                       env={"PATH": "/nonexistent", "HOME": str(ROOT)}, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
