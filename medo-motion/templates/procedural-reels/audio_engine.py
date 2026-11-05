"""Shared, sample-rate-safe DSP core for the procedural audio engine.

Everything the SFX kit and the music engine need to agree on lives here, once:

- a sample rate that is passed explicitly instead of read from a module constant, so 44.1 kHz and
  48 kHz both work without touching global state;
- filters built from that rate (the old `sfx.bp()` baked `SR / 2` in at import time);
- deterministic randomness helpers (the same seed → the same samples on any machine);
- envelope followers with **attack, release and lookahead**, which is what makes ducking inaudible;
- a stereo-linked lookahead limiter, so the master can be protected without clipping distortion.

Nothing in this module reads a file, calls ffmpeg or knows about a project. It is pure NumPy/SciPy,
which is why it can be unit-tested with a few thousand samples.

Adapted (re-written, credited) from `majedphotos/video-ad-editor` (MIT) —
see `assets/CREDITS.md` and `docs/audio-engine-audit.md`.
"""
from __future__ import annotations

import numpy as np
from scipy import signal as _signal

SR = 44100
"""Default sample rate, kept for backward compatibility with the original kit."""

RATES = (44100, 48000)
"""Sample rates this engine guarantees. Both are covered by tests."""

TAU = 2.0 * np.pi


# --------------------------------------------------------------------------- rates
def check_rate(sr) -> int:
    """Validate a sample rate and return it as ``int``.

    Only finite positive integers are accepted; the rate must be one the filters can band-limit
    against (> 8 kHz), and the two production rates are recognised so tools can report them.
    """
    if isinstance(sr, bool) or not isinstance(sr, (int, np.integer)):
        raise TypeError(f"sample rate must be an integer, got {type(sr).__name__}")
    sr = int(sr)
    if sr < 8000 or sr > 384000:
        raise ValueError(f"sample rate {sr} Hz is outside the supported 8000-384000 range")
    return sr


def check_channels(channels) -> int:
    if isinstance(channels, bool) or not isinstance(channels, (int, np.integer)):
        raise TypeError("channel count must be an integer")
    channels = int(channels)
    if channels not in (1, 2):
        raise ValueError(f"only mono (1) or stereo (2) is supported, got {channels}")
    return channels


# --------------------------------------------------------------------------- basics
def rng(seed) -> np.random.Generator:
    """Deterministic generator. Same seed → same stream, independent of global NumPy state."""
    return np.random.default_rng(int(seed) + 11)


def tvec(duration, sr=SR) -> np.ndarray:
    """``0 .. duration`` in seconds at ``sr``."""
    sr = check_rate(sr)
    return np.arange(max(0, int(round(duration * sr)))) / sr


def db(decibels) -> float:
    """Decibels → linear gain."""
    return float(10.0 ** (np.asarray(decibels, dtype=float) / 20.0))


def to_db(gain: float) -> float:
    """Linear gain → decibels (``-inf`` for silence)."""
    return float(20.0 * np.log10(max(float(gain), 1e-12)))


def norm(x: np.ndarray, peak: float = 1.0) -> np.ndarray:
    """Scale to ``peak`` without changing the shape. Silent input stays silent."""
    m = float(np.max(np.abs(x))) if x.size else 0.0
    return x if m <= 1e-12 else x * (peak / m)


def soft(x: np.ndarray, drive: float = 1.0) -> np.ndarray:
    """tanh saturation that keeps unity gain at low level."""
    drive = max(1e-3, float(drive))
    return np.tanh(np.asarray(x, dtype=np.float64) * drive) / np.tanh(drive)


def st(x: np.ndarray, pan=0.0) -> np.ndarray:
    """Mono → stereo with constant-power panning (``pan`` may be a scalar or a per-sample array)."""
    x = np.asarray(x, dtype=np.float64)
    p = np.clip(np.asarray(pan, dtype=np.float64), -1.0, 1.0)
    if p.ndim == 0:
        p = np.full(x.shape, float(p))
    a = (p + 1.0) * np.pi / 4.0
    return np.stack([x * np.cos(a), x * np.sin(a)], axis=-1)


def mix_into(buf: np.ndarray, sig: np.ndarray, at: int, gain: float = 1.0) -> int:
    """Add ``sig * gain`` into ``buf`` starting at sample ``at``; negative starts are trimmed.

    Returns how many samples were actually written, so a caller can detect truncation instead of
    silently losing a transient (a defect this module fixes).
    """
    if at >= buf.shape[0] or sig.size == 0:
        return 0
    sig = np.asarray(sig)
    if at < 0:
        sig = sig[-at:]
        at = 0
    n = min(int(sig.shape[0]), int(buf.shape[0] - at))
    if n <= 0:
        return 0
    sig = sig[:n]
    if buf.ndim == 2 and sig.ndim == 1:          # mono source into a stereo bus
        sig = sig[:, None]
    buf[at:at + n] += sig * gain
    return n


# --------------------------------------------------------------------------- filters
def _nyquist_guard(sr: int) -> float:
    return sr * 0.475


def sos(kind: str, freq, sr=SR, order: int = 2) -> np.ndarray:
    """Butterworth SOS, with the band clamped inside Nyquist instead of overflowing it."""
    sr = check_rate(sr)
    hi = _nyquist_guard(sr)
    if np.ndim(freq) == 0:
        f = [max(20.0, min(hi, float(freq)))]
    else:
        f = [max(20.0, min(hi, float(v))) for v in np.atleast_1d(freq)]
        if len(f) == 2 and f[1] <= f[0]:
            f[1] = min(hi, f[0] * 1.01)
    return _signal.butter(order, f if len(f) == 2 else f[0], btype=kind, fs=sr, output="sos")


def filt(x: np.ndarray, kind: str, freq, sr=SR, order: int = 2) -> np.ndarray:
    """One-shot Butterworth filtering at an explicit sample rate."""
    return _signal.sosfilt(sos(kind, freq, sr, order), np.asarray(x, dtype=np.float64), axis=0)


def lp(x, f, sr=SR, order=2):
    return filt(x, "lowpass", f, sr, order)


def hp(x, f, sr=SR, order=2):
    return filt(x, "highpass", f, sr, order)


def bp(x, lo, hi, sr=SR, order=2):
    return filt(x, "bandpass", [lo, hi], sr, order)


def sweep(x: np.ndarray, kind: str, freq_of_t, sr=SR, block: int = 256, order: int = 2, q: float = 1.6,
          bandpass_range=None) -> np.ndarray:
    """Filter whose cutoff follows ``freq_of_t(seconds)``, applied block-wise with carried state.

    This is how a whoosh gets its centre frequency to travel without clicks: 256-sample blocks at
    44.1 kHz are 5.8 ms, far below the ear's ability to hear the steps, and the filter state is
    carried so there is no discontinuity at the block edges.

    ``kind='bandpass'`` builds the band from a centre frequency and a Q-style width ``q``.
    """
    sr = check_rate(sr)
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    out = np.zeros_like(x)
    zi = None
    for i in range(0, x.shape[0], block):
        centre = float(freq_of_t((i + block / 2) / sr))
        if kind == "bandpass":
            lo, hi = centre / q, centre * q
            if bandpass_range is not None:
                lo, hi = max(bandpass_range[0], lo), min(bandpass_range[1], hi)
            s = sos("bandpass", [lo, hi], sr, order)
        else:
            s = sos(kind, centre, sr, order)
        if zi is None:
            zi = np.zeros((s.shape[0], 2) + x.shape[1:], dtype=x.dtype)
        seg = x[i:i + block]
        y, zi = _signal.sosfilt(s, seg, axis=0, zi=zi)
        out[i:i + block] = y
    return out


def polyblep_saw(freq, n: int, sr=SR, phase0: float = 0.0) -> np.ndarray:
    """Alias-reduced sawtooth (PolyBLEP). ``freq`` may be a scalar or a per-sample array."""
    sr = check_rate(sr)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (int(n),))
    dt = f / sr
    p = (phase0 + np.cumsum(dt)) % 1.0
    y = 2.0 * p - 1.0
    m1 = p < dt
    if np.any(m1):
        t1 = p[m1] / dt[m1]
        y[m1] -= t1 + t1 - t1 * t1 - 1.0
    m2 = p > 1.0 - dt
    if np.any(m2):
        t2 = (p[m2] - 1.0) / dt[m2]
        y[m2] -= t2 * t2 + t2 + t2 + 1.0
    return y


def sine(freq, n: int, sr=SR, phase0: float = 0.0) -> np.ndarray:
    """Phase-accumulated sine — accepts a per-sample frequency array (for glides and sweeps)."""
    sr = check_rate(sr)
    f = np.broadcast_to(np.asarray(freq, dtype=np.float64), (int(n),))
    return np.sin(TAU * (np.cumsum(f) / sr) + phase0)


def noise(n: int, seed=0, stereo: bool = False) -> np.ndarray:
    """Deterministic white noise, mono or decorrelated stereo."""
    r = rng(seed)
    return r.standard_normal((int(n), 2)) if stereo else r.standard_normal(int(n))


def sweep_tone(f0: float, f1: float, duration: float, sr=SR, curve: float = 6.0) -> np.ndarray:
    """Exponential frequency sweep as a pure tone (the original kit's ``sweep()``)."""
    sr = check_rate(sr)
    t = tvec(duration, sr)
    if t.size == 0:
        return t
    f = f1 + (f0 - f1) * np.exp(-t * curve / max(duration, 1e-6))
    return np.sin(TAU * np.cumsum(f) / sr)


# --------------------------------------------------------------------------- space
_IR_CACHE: dict = {}


def reverb_ir(rt=1.6, sr=SR, pre=0.012, bright=6000, seed=3) -> np.ndarray:
    """Decorrelated stereo impulse response: exponentially decaying noise, band-limited."""
    sr = check_rate(sr)
    key = (round(float(rt), 4), sr, round(float(pre), 4), int(bright), int(seed))
    if key not in _IR_CACHE:
        n = max(1, int((float(rt) + float(pre)) * sr))
        t = np.arange(n) / sr
        ir = rng(seed).standard_normal((n, 2)) * np.exp(-6.91 * t / max(float(rt), 1e-3))[:, None]
        ir[:int(pre * sr)] = 0.0
        ir = lp(ir, bright, sr)
        ir = hp(ir, 180, sr)
        ir /= np.sqrt(np.sum(ir ** 2, axis=0, keepdims=True)) + 1e-9
        _IR_CACHE[key] = ir
    return _IR_CACHE[key]


def reverb(x: np.ndarray, rt=1.6, mix_ratio=0.25, sr=SR, pre=0.012, bright=6000, seed=3) -> np.ndarray:
    """Convolution reverb. Returns ``len(x) + len(ir) - 1`` samples so tails are not lost."""
    sr = check_rate(sr)
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        x = st(x)
    ir = reverb_ir(rt, sr, pre, bright, seed)
    wet = np.stack([_signal.fftconvolve(x[:, 0], ir[:, 0]), _signal.fftconvolve(x[:, 1], ir[:, 1])], axis=1)
    out = np.zeros_like(wet)
    out[:x.shape[0]] += x * (1.0 - mix_ratio * 0.5)
    out += wet * mix_ratio
    return out


# --------------------------------------------------------------------------- envelopes
def adsr(n: int, attack=0.005, decay=0.05, sustain=0.7, release=0.1, sr=SR) -> np.ndarray:
    """Linear ADSR of exactly ``n`` samples (no allocation beyond the output)."""
    sr = check_rate(sr)
    n = int(n)
    if n <= 0:
        return np.zeros(0)
    a = min(n, max(1, int(attack * sr)))
    d = min(n - a, max(1, int(decay * sr)))
    r = min(n - a - d, max(1, int(release * sr)))
    s = max(0, n - a - d - r)
    env = np.concatenate([
        np.linspace(0.0, 1.0, a, endpoint=False),
        np.linspace(1.0, sustain, d, endpoint=False),
        np.full(s, float(sustain)),
        np.linspace(sustain, 0.0, r),
    ])
    return env[:n] if env.size >= n else np.pad(env, (0, n - env.size))


def exp_decay(n: int, tau: float, sr=SR) -> np.ndarray:
    """``exp(-t/tau)`` over ``n`` samples."""
    sr = check_rate(sr)
    return np.exp(-np.arange(int(n)) / sr / max(float(tau), 1e-6))


def voice_envelope(vo: np.ndarray, sr=SR, hop=0.005, attack=0.008, release=0.320, lookahead=0.040,
                   threshold_db=-34.0) -> np.ndarray:
    """Speech activity envelope in ``[0, 1]``, at full sample resolution.

    Fixes the defect measured in the original `sfx.duck()`: the old version normalised the envelope
    by the **global peak**, so one loud word made every quieter line under-duck (a 0.05-peak line
    ducked only 6% instead of 62%). Here the gate is an **absolute dBFS threshold**, so the same
    line ducks the same amount no matter how loud the rest of the recording is.

    - 5 ms RMS hops keep the estimate stable;
    - attack/release are one-pole coefficients computed **from ``sr``**, not baked in;
    - a lookahead shift of ``lookahead`` seconds makes the gain start falling *before* the first
      phoneme, which is the difference between "ducked" and "pumping".
    """
    sr = check_rate(sr)
    vo = np.asarray(vo, dtype=np.float64)
    if vo.ndim > 1:
        vo = vo.mean(axis=1)
    if vo.size == 0:
        return np.zeros(0)
    hop_n = max(1, int(round(hop * sr)))
    frames = int(np.ceil(vo.size / hop_n))
    pad = np.zeros(frames * hop_n)
    pad[:vo.size] = vo
    rms = np.sqrt(np.mean(pad.reshape(frames, hop_n) ** 2, axis=1) + 1e-18)
    level = 20.0 * np.log10(rms + 1e-12)
    target = np.clip((level - float(threshold_db)) / 6.0, 0.0, 1.0)   # 6 dB soft knee above the floor
    a = float(np.exp(-hop / max(attack, 1e-6)))
    r = float(np.exp(-hop / max(release, 1e-6)))
    env = np.empty(frames)
    z = 0.0
    for i in range(frames):
        coeff = a if target[i] > z else r
        z = coeff * z + (1.0 - coeff) * target[i]
        env[i] = z
    shift = int(round(lookahead / hop))
    if shift > 0:
        env = np.concatenate([env[shift:], np.zeros(shift)])
    return np.interp(np.arange(vo.size), np.arange(frames) * hop_n, env)


def duck_gain(vo: np.ndarray, sr=SR, depth=0.62, attack=0.008, release=0.320, lookahead=0.040,
              threshold_db=-34.0) -> np.ndarray:
    """Per-sample gain curve (1 = untouched, ``1 - depth`` = fully ducked) for a voice track."""
    depth = float(np.clip(depth, 0.0, 1.0))
    env = voice_envelope(vo, sr, attack=attack, release=release, lookahead=lookahead,
                         threshold_db=threshold_db)
    return 1.0 - depth * env


# --------------------------------------------------------------------------- dynamics
def limiter(x: np.ndarray, ceiling=0.84, sr=SR, lookahead=0.005, release=0.080) -> np.ndarray:
    """Stereo-linked lookahead peak limiter — keeps ``|x| <= ceiling`` without clipping distortion."""
    from scipy.ndimage import maximum_filter1d, minimum_filter1d

    sr = check_rate(sr)
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return x
    ceiling = float(np.clip(ceiling, 1e-4, 1.0))
    mono = np.abs(x).max(axis=1) if x.ndim > 1 else np.abs(x)
    L = max(1, int(round(lookahead * sr)))
    need = np.minimum(1.0, ceiling / (maximum_filter1d(mono, size=2 * L + 1) + 1e-12))
    g = minimum_filter1d(need, size=2 * L + 1)
    hop = 48
    n = int(np.ceil(len(g) / hop))
    gp = np.ones(n * hop)
    gp[:len(g)] = g
    gf = gp.reshape(n, hop).min(axis=1)
    rr = float(np.exp(-hop / sr / max(release, 1e-6)))
    z = 1.0
    out = np.empty(n)
    for i in range(n):
        z = gf[i] if gf[i] < z else rr * z + (1.0 - rr) * gf[i]
        out[i] = z
    gs = np.interp(np.arange(len(g)), np.arange(n) * hop + hop / 2, out)
    gain = np.minimum(gs, need)
    return x * (gain[:, None] if x.ndim > 1 else gain)


def true_peak(x: np.ndarray, sr=SR, oversample: int = 4) -> float:
    """Inter-sample peak in dBFS (a cheap 4x oversampled estimate, no ffmpeg needed)."""
    sr = check_rate(sr)
    x = np.asarray(x, dtype=np.float64)
    if x.size == 0:
        return float("-inf")
    # collapse channels by *magnitude*: `x.max(axis=1)` returns 0 for a symmetric L/R pair and
    # silently under-reports the true peak of exactly the material this limiter is meant to protect
    mono = x[np.arange(x.shape[0]), np.argmax(np.abs(x), axis=1)] if x.ndim > 1 else x
    if mono.size * oversample < 2_000_000:
        # Edge-reflect before oversampling: resample_poly assumes silence outside the buffer, so a
        # signal that is loud right up to the last sample "rings" up to +1.1 dB — a meter that
        # over-reads is worse than useless for a true-peak ceiling. Reflect, measure, trust the peak.
        pad = min(mono.size - 1, 64)
        padded = np.concatenate([mono[pad:0:-1], mono, mono[-2:-pad - 2:-1]]) if pad > 0 else mono
        up = _signal.resample_poly(padded, oversample, 1)
        # measure only where the original signal lives: the padding exists to make the *edges*
        # continuous, and the transition into the padding is not audio anyone will hear
        inner = up[pad * oversample:(pad + mono.size) * oversample] if pad > 0 else up
        peak = max(float(np.max(np.abs(mono))), float(np.max(np.abs(inner))) if inner.size else 0.0)
    else:
        peak = float(np.max(np.abs(mono)))
    return float(20.0 * np.log10(peak + 1e-12))


def fade(x: np.ndarray, sr=SR, fade_in=0.0, fade_out=0.0) -> np.ndarray:
    """Sample-accurate linear fades at both ends (never longer than the signal)."""
    sr = check_rate(sr)
    x = np.asarray(x, dtype=np.float64).copy()
    n = x.shape[0]
    fi = min(n, max(0, int(round(fade_in * sr))))
    fo = min(n - fi, max(0, int(round(fade_out * sr))))
    if fi:
        ramp = np.linspace(0.0, 1.0, fi)
        x[:fi] *= ramp[:, None] if x.ndim > 1 else ramp
    if fo:
        ramp = np.linspace(1.0, 0.0, fo)
        x[n - fo:] *= ramp[:, None] if x.ndim > 1 else ramp
    return x


# --------------------------------------------------------------------------- io
def write_wav(path, buf: np.ndarray, sr=SR, subtype: str = "PCM_16") -> str:
    """Write a WAV through SciPy at an explicit rate; mono or stereo, always clipped to [-1, 1]."""
    from scipy.io import wavfile

    sr = check_rate(sr)
    buf = np.asarray(buf, dtype=np.float64)
    data = np.clip(buf, -1.0, 1.0)
    if subtype == "PCM_16":
        data = (data * 32767.0).astype(np.int16)
    wavfile.write(str(path), sr, data)
    return str(path)


def read_wav_mono(path, target_sr=None) -> tuple[np.ndarray, int]:
    """Read a WAV as mono float64, optionally resampled to ``target_sr``."""
    from scipy.io import wavfile
    from scipy.signal import resample_poly

    sr, data = wavfile.read(str(path))
    x = np.asarray(data, dtype=np.float64)
    if np.issubdtype(np.asarray(data).dtype, np.integer):
        x = x / float(np.iinfo(np.asarray(data).dtype).max + 1)
    if x.ndim > 1:
        x = x.mean(axis=1)
    if target_sr and int(target_sr) != int(sr):
        target_sr = check_rate(int(target_sr))
        g = np.gcd(int(sr), target_sr)
        x = resample_poly(x, target_sr // g, int(sr) // g)
        sr = target_sr
    return x, int(sr)


def assert_clean(x: np.ndarray, name: str = "signal") -> None:
    """Fail loudly on NaN/inf or hard clipping — used by the engine and by tests."""
    x = np.asarray(x)
    if x.size == 0:
        raise ValueError(f"{name}: empty")
    if not np.all(np.isfinite(x)):
        raise ValueError(f"{name}: contains NaN or inf")
    peak = float(np.max(np.abs(x)))
    if peak > 1.0 + 1e-6:
        raise ValueError(f"{name}: clips at {peak:.4f} (> 1.0)")
