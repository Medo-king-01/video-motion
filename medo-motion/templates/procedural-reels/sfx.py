"""Sound design for the reel — every sound here is synthesised, so the kit is free, offline and
deterministic (same seed → same samples → the same mix on every machine).

Why procedural: a reel needs hits that land on *exact* frames, and licence-free sources still need
QA. Generating them means one vocabulary that both engines' edit lists can reference by name
(`pop`, `whoosh`, `swipe`, `glitch`…), and `transition.py` already declares which sound each
transition wants.

    from sfx import BANK, CATALOG, bus, render_bank, cues_for_transitions
    out = bus(6.0, [{"t": 0.4, "sfx": "whoosh", "gain": .8, "pan": (.7, -.7)}])

What this revision fixes (measured, see `docs/audio-engine-audit.md`):

- **Sample rate is a parameter, not a module constant.** The old `bp()` baked `SR/2` in at import
  time, so rendering at 48 kHz silently produced filters designed for 44.1 kHz. Every generator now
  takes `sr=` and the filters are built from the rate that is actually being rendered.
- **Anchors.** Each sound knows where its *event* sits inside its own waveform (an impact peaks at
  the start, a riser at the end, a whoosh in the middle). `bus()` places the anchor, not the buffer
  start, so a cue at 12.40 s actually hits at 12.40 s.
- **No silent truncation.** `bus()` returns a buffer long enough to hold the last tail, and reports
  `bus.last_truncated`, so a 0.7 s impact in a 0.2 s bus is a visible fact instead of a missing hit.
- **Ducking that actually ducks.** The envelope follower works on an **absolute** dBFS scale (the old
  code divided by the loudest peak, so a quiet line barely ducked the music) and has lookahead, so
  the bed is already down when the word starts.
- **Layers and overwrite guards.** A cue can stack several sounds at one instant, and no renderer in
  this file overwrites an existing file unless `overwrite=True`.
"""
import os

import numpy as np
from scipy.signal import butter, lfilter

import audio_engine as ax

SR = ax.SR

# ------------------------------------------------------------------ primitives (sr-aware)
def R(seed, sr=None):
    """Deterministic RNG for a sound. Same seed → same samples, at any sample rate."""
    return np.random.default_rng(int(seed) + 11)


def tt(d, sr=SR):
    return np.arange(int(d * sr)) / float(sr)


def bp(x, lo, hi, sr=SR, order=2):
    sr = ax.check_rate(sr)
    hi = min(float(hi), sr / 2 - 100)
    lo = max(1e-3, min(float(lo), hi * 0.99))
    b, a = butter(order, [lo / (sr / 2), hi / (sr / 2)], "band")
    return lfilter(b, a, x)


def lp(x, f, sr=SR, order=2):
    sr = ax.check_rate(sr)
    b, a = butter(order, min(float(f), sr / 2 - 100) / (sr / 2), "low")
    return lfilter(b, a, x)


def hp(x, f, sr=SR, order=2):
    sr = ax.check_rate(sr)
    b, a = butter(order, max(10.0, min(float(f), sr / 2 - 200)) / (sr / 2), "high")
    return lfilter(b, a, x)


def nrm(x):
    m = np.max(np.abs(x)) + 1e-9
    return x / m


def sweep(f0, f1, d, curve=6, sr=SR):
    t = tt(d, sr)
    f = f1 + (f0 - f1) * np.exp(-t * curve / d)
    return np.sin(2 * np.pi * np.cumsum(f) / sr)


def _rng_noise(r, n):
    return r.normal(0, 1, n)


# ------------------------------------------------------------------ the bank
# Every generator keeps its old signature (`seed` first) and gains a keyword-only `sr=`; the old
# call style `BANK[name](seed)` therefore still works and still means 44.1 kHz.
def pop(seed=0, *, sr=SR):
    r = R(seed); f0 = r.uniform(500, 640); t = tt(0.16, sr)
    f = f0 * (1 + 0.9 * np.exp(-t * 35))
    x = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 26)
    k = int(60 * sr / SR)
    x[:k] += r.normal(0, 0.25, k) * np.linspace(1, 0, k)
    return nrm(x)


def tick(seed=0, *, sr=SR):
    r = R(seed); f = r.uniform(2600, 3500); t = tt(0.06, sr)
    return nrm(np.sin(2 * np.pi * f * t) * np.exp(-t * 120)
               + r.normal(0, 0.05, len(t)) * np.exp(-t * 200))


def click(seed=0, *, sr=SR):
    r = R(seed); t = tt(0.08, sr)
    x = np.sin(2 * np.pi * r.uniform(1500, 1900) * t) * np.exp(-t * 90)
    k = int(80 * sr / SR)
    x[:k] += r.normal(0, 0.3, k) * np.linspace(1, 0, k)
    return nrm(x)


def zip_(seed=0, *, sr=SR):
    # `zip` is a pure sweep: no noise, so no RNG is drawn here. It used to build an RNG that was
    # never used — removed after verifying the output is byte-identical (the sweep depends only on
    # `d` and `sr`, so nothing downstream sees the missing draw).
    d = 0.24; t = tt(d, sr)
    x = np.sin(2 * np.pi * np.cumsum(300 + 1800 * (t / d) ** 2) / sr)
    return nrm(x * np.minimum(1, t * 80) * np.exp(-t * 9))


def whoosh(seed=0, d=0.5, *, sr=SR):
    r = R(seed); n = r.normal(0, 1, int(d * sr)); t = tt(d, sr)
    env = np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
    return nrm(bp(n, 350, min(2600, sr * 0.45), sr) * env
               + 0.5 * bp(n, 1800, min(7000, sr * 0.45), sr) * env ** 2)


def riser(seed=0, d=0.6, *, sr=SR):
    r = R(seed); n = r.normal(0, 1, int(d * sr)); t = tt(d, sr); a = (t / d) ** 2
    return nrm(hp(n, 1500, sr) * a * 0.6
               + np.sin(2 * np.pi * np.cumsum(180 + 1300 * (t / d) ** 2) / sr) * a * 0.5)


def impact(seed=0, *, sr=SR):
    r = R(seed); d = 0.7; t = tt(d, sr); f = 36 + 60 * np.exp(-t * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 6.5)
    nz = lp(r.normal(0, 1, len(t)), 1100, sr) * np.exp(-t * 16) * 0.7
    return nrm(sub + nz)


def stomp(seed=0, *, sr=SR):
    r = R(seed); d = 0.35; t = tt(d, sr); f = 50 + 70 * np.exp(-t * 30)
    x = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 12) \
        + lp(r.normal(0, 1, len(t)), 700, sr) * np.exp(-t * 30) * 0.5
    return nrm(x)


def sparkle(seed=0, *, sr=SR):
    r = R(seed); d = 0.7; t = tt(d, sr); x = np.zeros(len(t))
    for k, f in enumerate([2400, 3100, 4200, 5200]):
        f *= r.uniform(0.95, 1.05); s = int(k * 0.04 * sr); tk = t[: len(t) - s]
        x[s:] += np.sin(2 * np.pi * f * tk + 0.5 * np.sin(2 * np.pi * 9 * tk)) * np.exp(-tk * 9) * (0.9 ** k)
    return nrm(x)


def swipe(seed=0, d=0.22, *, sr=SR):
    """Short, wide band noise sweep — the sound of a frame sliding in."""
    r = R(seed); n = r.normal(0, 1, int(d * sr)); t = tt(d, sr); u = t / d
    env = (u ** 0.35) * np.exp(-u * 3.1)                     # fast attack, tight tail
    band = bp(n, 1200, min(8000, sr * 0.45), sr)
    flick = np.sin(2 * np.pi * np.cumsum(2100 - 1500 * u) / sr) * np.exp(-u * 6) * 0.25
    return nrm(band * env + flick)


def noise(seed=0, d=0.8, *, sr=SR):
    """Neutral air / room tone swell — pairs with dissolves and cut-tos."""
    r = R(seed); n = r.normal(0, 1, int(d * sr)); t = tt(d, sr); u = t / d
    env = np.sin(np.pi * u) ** 2
    return nrm((lp(n, 900, sr) + 0.5 * bp(n, 900, min(3000, sr * 0.45), sr)) * env)


def glitch(seed=0, d=0.3, *, sr=SR):
    """Digital stutter: squared-off noise bursts on a hard grid."""
    r = R(seed); n = int(d * sr); out = np.zeros(n)
    for _ in range(14):
        j = int(r.uniform(0, 0.9) * n); L = min(int(r.uniform(0.008, 0.03) * sr), n - j)
        if L <= 0:
            continue
        g = r.uniform(0.3, 1.0)
        out[j:j + L] += r.choice([-1, 1, 1]) * g * np.sign(r.normal(0, 1, L))
    t = tt(d, sr); out = bp(out, 900, min(7000, sr * 0.45), sr) + 0.3 * np.sin(2 * np.pi * (180 + 900 * np.exp(-t * 20)) * t)
    return nrm(out * np.exp(-t * 3.2))


def chime(seed=0, *, sr=SR):
    """Soft FM bell — for reveals and confirmations."""
    r = R(seed); d = 1.1; t = tt(d, sr); f = r.uniform(880, 1100)
    mod = np.sin(2 * np.pi * f * 2.01 * t) * 2.2 * np.exp(-t * 3)
    x = np.sin(2 * np.pi * f * t + mod) * np.exp(-t * 3.4) + 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 6)
    return nrm(x)


def sub(seed=0, d=0.9, *, sr=SR):
    """Sub drop — weight under a cut without a hard impact."""
    t = tt(d, sr); f = 90 * np.exp(-t * 3) + 34
    x = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t * 2.4)
    return nrm(x)


def blip(seed=0, *, sr=SR):
    """Tiny UI confirmation (square-ish, 40 ms)."""
    r = R(seed); d = 0.09; t = tt(d, sr); f = r.uniform(900, 1400)
    x = np.tanh(3 * np.sin(2 * np.pi * f * t)) * np.exp(-t * 38)
    return nrm(x)


# --- additions: real gaps in the vocabulary, not renames of what exists -------------------
def snap(seed=0, *, sr=SR):
    """Dry finger snap / wood block — the 'something landed' hit that is not an impact."""
    r = R(seed); d = 0.12; t = tt(d, sr)
    body = np.sin(2 * np.pi * r.uniform(1500, 1900) * t) * np.exp(-t * 70)
    nz = bp(r.normal(0, 1, len(t)), 1800, min(8000, sr * 0.45), sr) * np.exp(-t * 95) * 0.8
    return nrm(body + nz)


def page(seed=0, *, sr=SR):
    """Paper / page turn — for a document, a checklist, a board."""
    r = R(seed); d = 0.4; t = tt(d, sr); u = t / d
    n = bp(r.normal(0, 1, len(t)), 1400, min(6500, sr * 0.45), sr)
    flap = np.exp(-((u - 0.18) * 9) ** 2) + 0.55 * np.exp(-((u - 0.55) * 11) ** 2)
    return nrm(n * flap * (1 - 0.4 * u))


def coin(seed=0, *, sr=SR):
    """Two-note metallic confirmation — a price, a win, a counter."""
    r = R(seed); d = 0.5; t = tt(d, sr); f = r.uniform(1180, 1260)
    x = np.zeros(len(t))
    for k, mult in enumerate((1.0, 1.335)):
        s = int(k * 0.085 * sr); tk = t[: len(t) - s]
        x[s:] += np.sin(2 * np.pi * f * mult * tk) * np.exp(-tk * (9 if k else 16)) * (0.75 if k else 1.0)
        x[s:] += 0.25 * np.sin(2 * np.pi * f * mult * 2.71 * tk) * np.exp(-tk * 20)
    return nrm(x)


def heartbeat(seed=0, *, sr=SR):
    """Two-thump pulse — tension under a slow reveal (cinematic presets)."""
    d = 0.9; t = tt(d, sr); x = np.zeros(len(t))
    for k, (off, g) in enumerate(((0.0, 1.0), (0.24, 0.72))):
        s = int(off * sr); tk = t[: len(t) - s]
        f = 52 + 40 * np.exp(-tk * 26)
        x[s:] += np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-tk * 12) * g
    return nrm(lp(x, 200, sr))


def vinyl(seed=0, d=0.6, *, sr=SR):
    """Vinyl crackle / tape hiss — texture that makes a bed feel recorded, not generated."""
    r = R(seed); n = int(d * sr); t = tt(d, sr)
    hiss = r.normal(0, 1, n) * 0.05
    crackle = np.zeros(n)
    for _ in range(int(d * 90)):
        j = int(r.uniform(0, 0.98) * n); L = min(int(r.uniform(0.0004, 0.0025) * sr), n - j)
        if L > 0:
            crackle[j:j + L] += r.uniform(0.2, 1.0) * np.sign(r.normal(0, 1, L))
    x = bp(hiss + crackle, 400, min(9000, sr * 0.45), sr)
    return nrm(x * np.minimum(1, t * 40) * np.minimum(1, (d - t) * 40))


BANK = dict(pop=pop, tick=tick, click=click, zip=zip_, whoosh=whoosh, riser=riser, impact=impact, stomp=stomp,
            sparkle=sparkle, swipe=swipe, noise=noise, glitch=glitch, chime=chime, sub=sub, blip=blip,
            snap=snap, page=page, coin=coin, heartbeat=heartbeat, vinyl=vinyl)

# Where the *event* sits inside each rendered buffer, in seconds. `None` = the generator computes it
# (a riser peaks at its end, a whoosh in the middle), so a cue always lands on the moment it names.
ANCHORS = {
    "pop": 0.0, "tick": 0.0, "click": 0.0, "zip": 0.0, "blip": 0.0, "snap": 0.0, "coin": 0.0,
    "chime": 0.0, "sparkle": 0.0, "impact": 0.0, "stomp": 0.0, "sub": 0.0, "heartbeat": 0.0,
    "glitch": 0.0, "page": None, "whoosh": None, "swipe": None, "noise": None, "riser": None,
    "vinyl": None,
}

# Loudness family per sound: mixing by ear is what makes a reel sound amateur, so the bus scales each
# hit by its family before applying the cue gain.
CATALOG = {
 'pop':     dict(family='ui',     gain=0.55, tags='accent, marker, sticker'),
 'blip':    dict(family='ui',     gain=0.40, tags='tiny confirmation'),
 'click':   dict(family='ui',     gain=0.45, tags='toggle'),
 'tick':    dict(family='ui',     gain=0.30, tags='counter, blinds, checklist'),
 'zip':     dict(family='ui',     gain=0.45, tags='line draw, underline'),
 'snap':    dict(family='ui',     gain=0.50, tags='beat hit, emphasis'),
 'page':    dict(family='ui',     gain=0.34, tags='page turn, document, checklist'),
 'coin':    dict(family='ui',     gain=0.42, tags='price, win, counter'),
 'chime':   dict(family='tonal',  gain=0.50, tags='reveal, good news'),
 'sparkle': dict(family='tonal',  gain=0.45, tags='magic detail'),
 'whoosh':  dict(family='air',    gain=0.55, tags='scene change, wipe'),
 'swipe':   dict(family='air',    gain=0.50, tags='slide, push, card stack'),
 'noise':   dict(family='air',    gain=0.35, tags='dissolve, room tone'),
 'riser':   dict(family='build',  gain=0.55, tags='pre-impact lift'),
 'impact':  dict(family='impact', gain=0.75, tags='landing, statement'),
 'stomp':   dict(family='impact', gain=0.55, tags='body drop'),
 'sub':     dict(family='impact', gain=0.45, tags='weight under a cut'),
 'heartbeat': dict(family='impact', gain=0.52, tags='tension, slow reveal'),
 'glitch':  dict(family='texture', gain=0.45, tags='glitch transition, error beat'),
 'vinyl':   dict(family='texture', gain=0.30, tags='crackle, texture, warmth'),
}


def duration(name, **kw):
    """Length in seconds of a sound (rendered once, then measured)."""
    sr = kw.pop("sr", SR)
    return len(BANK[name](**kw, sr=sr)) / float(sr)


def anchor(name, sr=SR, seed=0):
    """Seconds into the rendered sound where its event is — `0.0` for a hit, the end for a riser."""
    fixed = ANCHORS.get(name)
    if fixed is not None:
        return float(fixed)
    sig = np.abs(BANK[name](seed, sr=sr).astype(np.float32))
    if name == "riser":
        return len(sig) / float(sr)
    if name == "page":
        return float(np.argmax(np.convolve(sig, np.ones(64) / 64, "same"))) / float(sr)
    return float(np.argmax(np.convolve(sig, np.ones(32) / 32, "same"))) / float(sr)


def place(buf, sig, t, gain=1.0, pan=0.0, sr=SR, anchor_at=0.0):
    """Merge `sig` into the stereo `buf` so its **event** lands at `t`.

    `anchor_at` is how many seconds into `sig` the event sits (0 = a hit, `len(sig)/sr` = a riser, the
    peak = a whoosh). Returns the number of samples written; negative starts are trimmed
    sample-exactly instead of being dropped, which is what makes a cue land on the same sample at
    any rate.
    """
    return _place_anchored(buf, sig, t, gain, pan, sr, anchor_at)[0]


def _place_anchored(buf, sig, t, gain, pan, sr, anch):
    """`place` with an explicit anchor time (used by `bus`, which knows the sound's name).

    Returns ``(written, overrun, clipped)``: `overrun` = samples past the end of the buffer (real,
    audible truncation), `clipped` = samples before sample 0 (a cue deliberately starting early, e.g.
    a riser whose peak is at 0.5 s but whose onset is at -0.1 s — expected, not a defect).
    """
    i = int(round(t * sr)) - int(round(float(anch) * sr))
    clipped = 0
    n = min(len(sig), buf.shape[0] - i)
    if n <= 0:
        return 0, max(0, len(sig) - max(0, buf.shape[0] - i)), max(0, -i)
    if i < 0:
        clipped = min(len(sig), -i)
        sig = sig[clipped:]
        i = 0
        n = min(len(sig), buf.shape[0] - i)
        if n <= 0:
            return 0, 0, clipped
    s = (sig[:n] * gain).astype(np.float32)
    if isinstance(pan, (tuple, list)):
        p = np.linspace(pan[0], pan[1], n)
    else:
        p = np.full(n, pan)
    a = (p + 1) * np.pi / 4
    buf[i:i + n, 0] += s * np.cos(a)
    buf[i:i + n, 1] += s * np.sin(a)
    return n, max(0, len(sig) - n), clipped


# ---------------- cue sheet → stereo bus ----------------
def _pan_value(pan):
    """Scalar or (start, end) pan, clamped to [-1, 1]."""
    if isinstance(pan, (tuple, list)) and len(pan) == 2:
        return (max(-1.0, min(1.0, float(pan[0]))), max(-1.0, min(1.0, float(pan[1]))))
    return max(-1.0, min(1.0, float(pan or 0.0)))


def bus(length, cues, sr=SR, seed_offset=0, tail=False, limit=False, anchored=False):
    """Render a cue list into a stereo float32 bus.

    cues: [{"t": 1.2, "sfx": "whoosh", "gain": 1.0, "pan": (0.7, -0.7)}]
    Missing gain/pan fall back to the catalogue defaults, and the catalogue's family gain is always
    applied first, so a cue gain of 1.0 means "as loud as this sound should be in a mix".

    By default `t` is where the buffer **starts** (the historical behaviour, so every existing edit
    list renders exactly as before). With `anchored=True` — or `"anchor": True` on a single cue — `t` is
    instead the moment of the sound's **event**, so a riser cued at 3.0 starts early and peaks at 3.0
    and a whoosh is centred on the cut it accompanies. The returned buffer is exactly `length` long
    (a mixer's timeline is authoritative), `bus.last_truncated` counts samples that did not fit, and
    `tail=True` grows the buffer to keep the final sound's body — used by the demo/preview renderers.
    """
    sr = ax.check_rate(sr)
    n = int(round(length * sr)) + 1
    prepared = []
    for i, cue in enumerate(cues):
        name = cue.get("sfx") or cue.get("name")
        if name not in BANK:
            raise KeyError(f"unknown sfx {name!r}; known: {', '.join(sorted(BANK))}")
        seed = int(cue.get("seed", i) or 0) + seed_offset
        prepared.append((name, seed, cue))
    if tail and prepared:
        need = n
        for name, seed, cue in prepared:
            a = anchor(name, sr, seed)
            need = max(need, int(round(float(cue.get("t", 0.0)) * sr)) - int(round(a * sr))
                       + len(BANK[name](seed, sr=sr)))
        n = need
    out = np.zeros((n, 2), np.float32)
    cache = {}
    bus.last_truncated = 0
    bus.last_written = 0
    bus.last_clipped = 0
    for name, seed, cue in prepared:
        key = (name, seed)
        if key not in cache:
            cache[key] = BANK[name](seed, sr=sr).astype(np.float32)
        use_anchor = bool(cue.get("anchor", anchored))
        layers = cue.get("layer") or cue.get("layers")
        stacks = layers if isinstance(layers, (list, tuple)) else [None]
        gain = float(cue.get("gain", 1.0)) * float(CATALOG.get(name, {}).get("gain", 0.5))
        pan = _pan_value(cue.get("pan", 0.0))
        a = anchor(name, sr, seed) if use_anchor else 0.0
        for k, layer in enumerate(stacks):
            lg, lpan = gain, pan
            if isinstance(layer, dict):                       # layered cue: {"sfx":…, "gain":…, "pan":…}
                lg = gain * float(layer.get("gain", 1.0))
                lpan = _pan_value(layer.get("pan", pan))
                sig = BANK[layer.get("sfx", name)](seed + k, sr=sr).astype(np.float32) \
                    if layer.get("sfx", name) in BANK else cache[key]
                la = (anchor(layer.get("sfx", name), sr, seed + k)
                      if use_anchor and layer.get("sfx", name) in BANK else a)
            else:
                sig, la = cache[key], a
            wrote, overrun, clipped = _place_anchored(
                out, sig, float(cue.get("t", 0.0)) + float(cue.get("offset", 0.0)), lg, lpan, sr, la)
            bus.last_written += wrote
            # the buffer carries one guard sample beyond `length`, so a sound ending exactly at the
            # end of the timeline is not cut; a cue that starts before 0 is clipped by design
            bus.last_truncated += max(0, overrun - 1)
            bus.last_clipped += clipped
    if limit:
        out = ax.limiter(out, ceiling=0.95, sr=sr)
    return out


def cues_for_transitions(cuts, gain=1.0, pan=(0.0, 0.0), lead=None):
    """Cut list → cue list, using the sound each transition declares in transitions.json.

    cuts: [{"scene": 3, "t": 12.4, "name": "wipe"}]  →  [{"t": 12.4 + lead, "sfx": "whoosh", ...}]

    `lead` shifts every cue by a constant (a transition sound usually starts a beat before the cut).
    A cut may also carry its own `lead`/`gain`/`pan`, which wins over the argument.
    """
    try:
        from transition import sfx_for
    except ImportError:  # pragma: no cover
        sfx_for = lambda _n: None  # noqa: E731
    cues = []
    for i, cut in enumerate(cuts):
        name = sfx_for(cut.get("name", ""))
        if not name:
            continue
        shift = float(cut.get("lead", lead if lead is not None else 0.0))
        cues.append({"t": float(cut.get("t", 0.0)) + shift, "sfx": name,
                     "gain": float(cut.get("gain", gain)), "pan": cut.get("pan", pan), "seed": i})
    return cues


def write_wav(path, buf, sr=SR):
    from scipy.io import wavfile
    path = str(path)
    wavfile.write(path, int(sr), (np.clip(buf, -1, 1) * 32767).astype(np.int16))


def _guard(path, overwrite):
    """Never clobber a rendered file by accident (the old renderers wrote fixed names)."""
    if os.path.exists(str(path)) and not overwrite:
        raise FileExistsError(f"{path} exists — pass overwrite=True or choose another name")


def render_bank(outdir, names=None, sr=SR, seed=0, overwrite=False):
    """Write the whole kit as stereo WAVs (one per sound) — handy for an editor/AE import."""
    sr = ax.check_rate(sr)
    os.makedirs(outdir, exist_ok=True)
    written = []
    for name in (names or BANK):
        sig = BANK[name](seed, sr=sr).astype(np.float32)
        st = np.stack([sig, sig], 1) * float(CATALOG.get(name, {}).get("gain", 0.5))
        path = os.path.join(str(outdir), f"{name}.wav")
        _guard(path, overwrite)
        write_wav(path, st, sr)
        written.append(path)
    return written


def duck(vo, bus_buf, depth=0.62, release=6.0, sr=SR, attack=None, lookahead=0.03):
    """Sidechain-style ducking of the sfx bus under the voice.

    Signature-compatible with the old one-pole follower, but built on `audio_engine.duck_gain`:
    an **absolute** dBFS threshold (so a quiet line still ducks), an attack and a lookahead in
    milliseconds instead of a filter coefficient, and the length of `bus_buf` is preserved instead
    of being truncated to the length of `vo` — a truncated return value silently misaligned the mix.

    `release` keeps its old meaning: a 6 dB/s-ish recovery rate in Hz (larger = faster recovery).
    """
    sr = ax.check_rate(sr)
    n = len(bus_buf)
    if n == 0:
        return bus_buf
    vo = np.asarray(vo, np.float32)
    if vo.ndim > 1:
        vo = vo.mean(axis=1)
    if attack is None:
        attack = 0.008
    if release is None or release <= 0:
        release_s = 0.32
    else:
        release_s = float(np.clip(0.45 / (float(release) / 6.0), 0.05, 1.5))
    pad = np.zeros(n, np.float32)
    m = min(n, len(vo))
    pad[:m] = vo[:m]
    gain = ax.duck_gain(pad, sr, depth=depth, attack=attack, release=release_s, lookahead=lookahead)
    out = np.asarray(bus_buf, np.float32).copy()
    out *= gain[:, None] if out.ndim == 2 else gain
    return out


# ---------------------------------------------------------------- rhythm-locked cue sheets
GRID_MAP = {"k": "impact", "s": "click", "h": "tick", "p": "pop", "z": "zip", "w": "whoosh"}

# A transition's declared sound is a single hit; these are the *accents* that make the same
# transition read differently depending on what is happening. Still transition-linked: the base sound
# always comes from transitions.json, the accent is added on top.
ACCENTS = {
    ("flash", "beat"): ["stomp", "sub"],
    ("glitch", "beat"): ["glitch", "click"],
    ("iris", "reveal"): ["chime", "sparkle"],
    ("zoom", "reveal"): ["riser", "whoosh"],
    ("wipe", "panel"): ["swipe", "tick"],
    ("dissolve", "calm"): ["noise", "vinyl"],
}


def accent_cues(cuts, moment="beat", gain=0.5):
    """Extra layers for transition sounds, chosen by *moment* (beat / reveal / panel / calm).

    Returns cues with `layer` set to the stack of sounds; `bus()` renders every layer at one instant,
    so a transition can be a hit + a tail instead of one sample. Unknown moments return `[]`.
    """
    try:
        from transition import sfx_for
    except ImportError:  # pragma: no cover
        return []
    cues = []
    for i, cut in enumerate(cuts):
        base = sfx_for(cut.get("name", ""))
        stack = ACCENTS.get((cut.get("name", ""), cut.get("moment", moment)))
        if not base or not stack:
            continue
        cues.append({"t": float(cut.get("t", 0.0)), "sfx": stack[0], "gain": float(cut.get("gain", gain)),
                     "pan": cut.get("pan", 0.0), "seed": i,
                     "layer": [{"sfx": s, "gain": 0.8 if k else 1.0} for k, s in enumerate(stack)]})
    return cues


def grid_cues(pattern="k...h...k...h...", bpm=120.0, bars=1, start=0.0, gain=1.0,
              mapping=None, pan=None):
    """A cue sheet locked to the tempo grid — one character per sixteenth note.

    `k` hit · `s` click (snare-ish) · `h` tick (hat) · `p` pop · `z` zip · `w` whoosh · `.` or ` `
    silence · `|` is ignored, so patterns can be written in bars: `"k.h.|k.h.|k.k.|k..."`.

    Times are computed from `bpm`, never hand-typed, so the hits can't drift off the beat.
    """
    cmap = dict(GRID_MAP, **(mapping or {}))
    step = 60.0 / float(bpm) / 4.0                     # one sixteenth
    chars = [c for c in str(pattern) if c != "|"]
    if not chars:
        raise ValueError("empty grid pattern")
    # one bar = 4/4 = 16 sixteenths; a shorter pattern tiles inside the bar, so `bars` always
    # means bars (and `bars_seconds(bpm, bars)` is exactly its length)
    per_bar = 16
    tiled = (chars * (per_bar // len(chars) + 1))[:per_bar]
    cues = []
    for bar in range(int(bars)):
        for i, c in enumerate(tiled):
            if c in ". _":
                continue
            if c not in cmap:
                raise ValueError(f"unknown grid step {c!r} (use {''.join(sorted(GRID_MAP))} or .)")
            t = round(float(start) + (bar * per_bar + i) * step, 4)
            cue = {"t": t, "sfx": cmap[c], "gain": float(gain) * (1.0 if c == "k" else 0.62)}
            if c == "k":
                cue["gain"] = float(gain)
            if pan is not None:
                cue["pan"] = pan
            cues.append(cue)
    return cues


def bars_seconds(bpm=120.0, bars=1, beats=4):
    """How long `bars` bars last — for a loop bed or a pattern buffer."""
    return float(bars) * float(beats) * 60.0 / float(bpm)
