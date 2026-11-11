"""Procedural background music — original, offline, deterministic, and configurable.

The bed is built from **independent layers** (kick, clap, hats, bass, melody, synth pluck, pad/texture,
transition accents). Each layer is rendered once per pattern cell and placed on a beat grid, so:

- the same configuration + seed always produces the same samples (no wall clock, no global RNG);
- asking for 48 kHz instead of 44.1 kHz changes the rate, not the music;
- the length is exact, and the tail is not cut mid-note.

    from music import MusicConfig, render_music
    cfg = MusicConfig(preset="tech", bpm=112, duration=16.0, seed=7)
    bed = render_music(cfg)                      # stereo float32, exactly 16.0 s

Why this shape: a reel is cut to a BPM grid, so the bed must be quantised — never "a loop that
happens to be roughly the right length". The section model (intro/build/drop/break/outro/stop) is
what makes a 16-second explainer feel composed rather than looped.

Architecture adapted (re-written) from `majedphotos/video-ad-editor/motion/audio.py` (MIT);
see `assets/CREDITS.md` and `docs/audio-engine-audit.md`.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np

import audio_engine as ax



def _presets_path() -> Path:
    """`motion/music-presets.json`, found from wherever this file sits.

    The editable copy lives in `shared/py/` and an identical copy ships in the engine-P template,
    so the vocabulary is looked up by walking up to the studio root instead of a fixed depth.
    """
    here = Path(__file__).resolve()
    for base in here.parents:
        for candidate in (base / "medo-motion" / "motion" / "music-presets.json",
                          base / "motion" / "music-presets.json"):
            if candidate.is_file():
                return candidate
    return here.parents[2] / "motion" / "music-presets.json"


PRESETS_PATH = _presets_path()
SECTION_ORDER = ("intro", "build", "drop", "break", "outro", "stop")
LAYERS = ("kick", "clap", "hat", "bass", "pad", "pluck", "melody", "texture")

# The one absolute gain in the music renderer. Chosen so a typical full arrangement sits around
# -18 dBFS RMS — quiet enough to leave the voice-over room, loud enough to survive the mixer's own
# level control. Layer levels are relative to this, and the mixing stage owns loudness.
MASTER_GAIN = 0.30

DATA: dict = {}


def vocabulary() -> dict:
    """The preset/scale/section vocabulary (`motion/music-presets.json`), loaded once."""
    global DATA
    if not DATA:
        DATA = json.loads(PRESETS_PATH.read_text(encoding="utf-8"))
    return DATA


def presets() -> dict:
    return vocabulary()["presets"]


def preset_names() -> list[str]:
    return list(presets())


# --------------------------------------------------------------------------- music theory
def note_hz(semitone_from_c0: float) -> float:
    """MIDI-style semitone (C0 = 0) → Hz."""
    return 16.351597831287414 * 2.0 ** (float(semitone_from_c0) / 12.0)


def key_of(name: str) -> int:
    keys = vocabulary()["keys"]["values"]
    if name not in keys:
        raise ValueError(f"unknown key {name!r}; known: {', '.join(vocabulary()['keys']['names'])}")
    return int(keys[name])


def scale_of(name: str) -> tuple[int, ...]:
    scales = vocabulary()["scales"]
    if name not in scales:
        raise ValueError(f"unknown scale {name!r}; known: {', '.join(scales)}")
    return tuple(int(s) for s in scales[name]["semitones"])


def degree_to_semitone(degree: int, key: int, scale: tuple[int, ...], octave: int) -> int:
    """Scale degree (unbounded, may be negative) → absolute semitone from C0."""
    steps = len(scale)
    octave_offset, index = divmod(int(degree), steps)
    return 12 * (int(octave) + octave_offset) + int(key) + scale[index]


def chord_for(progression, bar: int, key: int, scale, octave: int, size: int = 3) -> list[int]:
    """Triad built on the progression degree for this bar (stacked in thirds of the scale)."""
    root = int(progression[bar % len(progression)])
    return [degree_to_semitone(root + 2 * i, key, scale, octave) for i in range(max(1, size))]


# --------------------------------------------------------------------------- config
@dataclass
class MusicConfig:
    """Everything that decides what the bed sounds like. Validated on construction."""

    preset: str = "tech"
    duration: float = 16.0
    bpm: float | None = None
    key: str | None = None
    scale: str | None = None
    mood: str | None = None
    energy: float = 1.0
    seed: int = 7
    sr: int = ax.SR
    channels: int = 2
    progression: list[int] | None = None
    sections: dict | None = None
    layers: dict | None = None
    groove: dict | None = None
    tone: dict | None = None
    top: dict | None = None
    swings: float = 0.0
    """0 = straight, up to 0.3 = swung 16ths (the second of each pair is delayed)."""
    bar_offset: float = 0.0
    fade_in: float = 0.8
    fade_out: float = 1.2
    level_trim_db: float | None = None
    """Override the preset's measured level correction (dB). `None` = use the data file."""

    def __post_init__(self) -> None:
        if self.preset not in presets():
            raise ValueError(f"unknown preset {self.preset!r}; known: {', '.join(preset_names())}")
        self.sr = ax.check_rate(self.sr)
        self.channels = ax.check_channels(self.channels)
        if not isinstance(self.duration, (int, float)) or isinstance(self.duration, bool):
            raise TypeError("duration must be a number of seconds")
        if not math.isfinite(float(self.duration)) or self.duration <= 0:
            raise ValueError("duration must be a positive, finite number of seconds")
        if self.bpm is not None and (not math.isfinite(float(self.bpm)) or not 40 <= float(self.bpm) <= 220):
            raise ValueError("bpm must be between 40 and 220")
        if not isinstance(self.seed, (int, np.integer)) or isinstance(self.seed, bool):
            raise TypeError("seed must be an integer")
        if not math.isfinite(float(self.energy)) or not 0.0 <= float(self.energy) <= 2.0:
            raise ValueError("energy must be between 0.0 and 2.0")
        if self.key is not None:
            key_of(self.key)                       # raises early with a clear message
        if self.scale is not None:
            scale_of(self.scale)
        if self.progression is not None and not all(isinstance(d, int) for d in self.progression):
            raise TypeError("progression must be a list of integer scale degrees")
        for name, level in (self.layers or {}).items():
            if name not in LAYERS:
                raise ValueError(f"unknown layer {name!r}; known: {', '.join(LAYERS)}")
            if not math.isfinite(float(level)) or not 0.0 <= float(level) <= 2.0:
                raise ValueError(f"layer {name} level must be between 0.0 and 2.0")
        for name, level in (self.sections or {}).items() if isinstance(self.sections, dict) else ():
            if name not in SECTION_ORDER:
                raise ValueError(f"unknown section {name!r}; known: {', '.join(SECTION_ORDER)}")
            if float(level) < 0:
                raise ValueError(f"section {name} ratio cannot be negative")
        if not 0.0 <= float(self.swings) <= 0.30:
            raise ValueError("swings must be between 0 and 0.3")

    # -- resolved (preset + overrides) --------------------------------------
    def resolved(self) -> dict:
        base = dict(presets()[self.preset])
        out = {
            "preset": self.preset,
            "duration": float(self.duration),
            "bpm": float(self.bpm if self.bpm is not None else base["bpm"]),
            "key": self.key or base["key"],
            "scale": self.scale or base["scale"],
            "mood": self.mood or base.get("mood", ""),
            "progression": list(self.progression if self.progression is not None else base["progression"]),
            "sections": (list(self.sections) if isinstance(self.sections, list)
                         else dict(self.sections if self.sections is not None else base["sections"])),
            "layers": dict(base["layers"], **(self.layers or {})),
            "groove": dict(base["groove"], **(self.groove or {})),
            "tone": dict(base["tone"], **(self.tone or {})),
            "top": dict(base["top"], **(self.top or {})),
            "energy": float(self.energy),
            "seed": int(self.seed),
            "sr": int(self.sr),
            "channels": int(self.channels),
            "swings": float(self.swings),
            "bar_offset": float(self.bar_offset),
            "fade_in": float(self.fade_in),
            "fade_out": float(self.fade_out),
            # measured loudness correction for this arrangement (data file, not taste)
            "trim_db": float(self.level_trim_db if self.level_trim_db is not None
                             else base.get("levelTrimDb", 0.0)),
        }
        if out["key"] not in vocabulary()["keys"]["values"]:
            raise ValueError(f"unknown key {out['key']!r}")
        scale_of(out["scale"])
        for name, level in out["layers"].items():
            if name not in LAYERS:
                raise ValueError(f"unknown layer {name!r}; known: {', '.join(LAYERS)}")
            if not 0.0 <= float(level) <= 2.0:
                raise ValueError(f"layer {name} level must be between 0.0 and 2.0")
        return out

    def describe(self) -> dict:
        """A JSON-safe summary, good for a plan file or a log line."""
        r = self.resolved()
        return {k: v for k, v in r.items() if k not in ("sr",)} | {"sr": r["sr"]}


# --------------------------------------------------------------------------- timing
def beat_times(cfg: dict) -> tuple[float, float, int]:
    """(seconds per beat, seconds per bar, beats per bar)."""
    spb = 60.0 / float(cfg["bpm"])
    return spb, spb * 4.0, 4


def section_spans(cfg: dict, duration: float) -> list[dict]:
    """Turn the section ratios or explicit list into contiguous spans that fill `duration` exactly.

    Ratios are converted to whole bars when that is possible, so a section boundary always lands on
    a bar line — a cut in the edit will not fall mid-phrase. A section that the preset weights at
    all gets at least one bar; when the bed is too short to hold every section, the *least* weighted
    ones are dropped (the preset itself says what matters), never the drop.
    """
    spb, bar, _ = beat_times(cfg)
    raw = cfg["sections"]
    if isinstance(raw, list):
        spans = []
        for entry in raw:
            start = float(entry.get("start", 0.0))
            end = float(entry.get("end", duration))
            name = str(entry.get("name", "drop"))
            if name not in SECTION_ORDER:
                raise ValueError(f"unknown section {name!r}")
            spans.append({"name": name, "start": start, "end": end})
        return _normalise_spans(spans, duration)

    ratios = {name: float(v) for name, v in raw.items() if float(v) > 0}
    if not ratios:
        return [{"name": "drop", "start": 0.0, "end": float(duration)}]
    total_bars = max(1, int(math.floor(duration / bar)))
    names = [n for n in SECTION_ORDER if n in ratios]
    # too short for the full arrangement: lose the least-weighted sections first
    while len(names) > total_bars:
        names.remove(min(names, key=lambda n: (ratios[n], SECTION_ORDER.index(n))))
    bars = _allocate_bars(names, ratios, total_bars)
    spans, t = [], 0.0
    for name in names:
        length = bars[name] * bar
        if length <= 0:
            continue
        spans.append({"name": name, "start": round(t, 6), "end": round(t + length, 6)})
        t += length
    if not spans:
        return [{"name": "drop", "start": 0.0, "end": float(duration)}]
    spans[-1]["end"] = float(duration)          # the outro absorbs the sub-bar remainder
    return _normalise_spans(spans, duration)


def _allocate_bars(names: list[str], ratios: dict, total_bars: int) -> dict:
    """Largest-remainder allocation with a **minimum of one bar** for every kept section."""
    ideal = {n: total_bars * ratios[n] / sum(ratios[m] for m in names) for n in names}
    bars = {n: max(1, int(math.floor(ideal[n]))) for n in names}
    spare = total_bars - sum(bars.values())
    order = sorted(names, key=lambda n: -(ideal[n] - math.floor(ideal[n])))
    i = 0
    while spare > 0 and order:                  # any surplus goes to drop first, then biggest
        bars[order[i % len(order)]] += 1
        spare -= 1
        i += 1
    while sum(bars.values()) > total_bars:      # never overrun: take from the largest
        biggest = max(names, key=lambda n: bars[n])
        if bars[biggest] <= 1:
            break
        bars[biggest] -= 1
    return bars


def _normalise_spans(spans: list[dict], duration: float) -> list[dict]:
    out, cursor = [], 0.0
    for span in spans:
        start = max(cursor, float(span["start"]))
        end = min(float(duration), float(span["end"]))
        if end - start <= 1e-6:
            continue
        out.append({"name": span["name"], "start": start, "end": end})
        cursor = end
    if not out:
        return [{"name": "drop", "start": 0.0, "end": float(duration)}]
    if out[0]["start"] > 0:
        out[0]["start"] = 0.0
    out[-1]["end"] = float(duration)
    return out


def section_at(spans: list[dict], t: float) -> str:
    for span in spans:
        if span["start"] <= t < span["end"]:
            return span["name"]
    return spans[-1]["name"] if spans else "drop"


def hard_gate(spans: list[dict], n: int, sr: int, ramp: float = 0.004) -> np.ndarray:
    """Per-sample gain that is exactly 0 inside a `stop` section, with raised-cosine edges.

    Applied to the **summed** bed, after reverb and after the phone layer: a gate applied earlier
    lets a reverb tail or a pad release sound straight through a deliberate silence.
    """
    g = np.ones(n)
    r = max(1, int(ramp * sr))
    for span in spans:
        if span["name"] != "stop":
            continue
        a = max(0, min(n, int(round(span["start"] * sr))))
        b = max(a, min(n, int(round(span["end"] * sr))))
        if b <= a:
            continue
        if a > 0:                                  # fade out over `ramp`, reaching 0 at `a`
            lo = max(0, a - r)
            g[lo:a] = np.minimum(g[lo:a], 0.5 + 0.5 * np.cos(np.linspace(0.0, np.pi, a - lo)))
        g[a:b] = 0.0
        if b < n:                                  # fade in over `ramp`, rising from `b`
            hi = min(n, b + r)
            g[b:hi] = np.minimum(g[b:hi], 0.5 - 0.5 * np.cos(np.linspace(0.0, np.pi, hi - b)))
    return g


def grid_seconds(cfg: dict) -> float:
    """One sixteenth note in seconds."""
    spb, _, _ = beat_times(cfg)
    return spb / 4.0


def swing_offset(cfg: dict, step_index: int) -> float:
    """Delay applied to the second 16th of every pair when `swings` > 0."""
    if step_index % 2 == 0 or not cfg["swings"]:
        return 0.0
    return cfg["swings"] * grid_seconds(cfg)


# --------------------------------------------------------------------------- instruments
def _kick(cfg, r) -> np.ndarray:
    n = int(0.45 * cfg["sr"])
    t = np.arange(n) / cfg["sr"]
    body = ax.sine(46.0 + 110.0 * np.exp(-t / 0.035), n, cfg["sr"]) * np.exp(-t / 0.16) * 1.2
    click = ax.hp(r.standard_normal(n), 2500, cfg["sr"]) * np.exp(-t / 0.003) * 0.25
    return ax.soft(body + click, 1.4)


def _clap(cfg, r) -> np.ndarray:
    n = int(0.35 * cfg["sr"])
    t = np.arange(n) / cfg["sr"]
    env = np.zeros(n)
    for delay in (0.0, 0.011, 0.023):
        i = int(delay * cfg["sr"])
        env[i:] += np.exp(-t[: n - i] / (0.009 if delay < 0.02 else 0.09))
    x = r.standard_normal(n) * env
    x = ax.bp(x, 800, 4200, cfg["sr"])
    return ax.reverb(ax.st(x, 0.0), 0.9, 0.3, cfg["sr"], seed=int(cfg["seed"]))[:n]


def _hat(cfg, r, open_=False) -> np.ndarray:
    dur = 0.45 if open_ else 0.12
    n = int(dur * cfg["sr"])
    t = np.arange(n) / cfg["sr"]
    x = ax.hp(r.standard_normal(n), 6500 if open_ else 7500, cfg["sr"])
    return x * np.exp(-t / (0.14 if open_ else 0.022))


def _snare(cfg, r) -> np.ndarray:
    n = int(0.2 * cfg["sr"])
    t = np.arange(n) / cfg["sr"]
    body = ax.bp(r.standard_normal(n), 1200, 6000, cfg["sr"]) * np.exp(-t / 0.05)
    return body + ax.sine(190.0, n, cfg["sr"]) * np.exp(-t / 0.04) * 0.5


def _pad_chord(cfg, notes: list[int], length: float) -> np.ndarray:
    """Detuned PolyBLEP saws, one pair per note, low-passed by the section's tone."""
    sr = cfg["sr"]
    n = int((length + 1.2) * sr)
    t = np.arange(n) / sr
    out = np.zeros((n, 2))
    for i, semi in enumerate(notes):
        f = note_hz(semi)
        for chan, detune in ((0, -1.0), (1, 1.0)):
            for dv in (-7.0, 0.0, 7.0):
                out[:, chan] += ax.polyblep_saw(f * 2 ** ((dv + detune * 3.0) / 1200.0), n, sr,
                                                phase0=(i * 0.137 + chan * 0.31 + dv * 0.01) % 1.0) * (0.6 if dv else 0.8)
    cut = float(cfg["tone"].get("padCut", 2200))
    out = ax.lp(out, cut, sr)
    env = np.minimum(1.0, t / 0.25) * np.where(t > length, np.exp(-(t - length) / 0.35), 1.0)
    return out * env[:, None]


def _pluck(freq: float, cfg, length: float = 0.35) -> np.ndarray:
    """FM-ish pluck: bright attack, fast decay, energy in the band a phone speaker can play."""
    sr = cfg["sr"]
    n = int(length * sr)
    t = np.arange(n) / sr
    phase = ax.TAU * freq * t + 1.6 * np.exp(-t / 0.03) * np.sin(ax.TAU * freq * 2.0 * t)
    x = (np.sin(phase) + 0.35 * np.sign(np.sin(phase)) * np.exp(-t / 0.02)) * np.exp(-t / 0.065) * np.minimum(1.0, t / 0.0015)
    cut = float(cfg["tone"].get("pluckCut", 4200))
    return ax.lp(ax.hp(x, 420, sr), cut, sr)


def _bass_note(freq: float, cfg, length: float) -> np.ndarray:
    sr = cfg["sr"]
    n = max(1, int(length * 0.92 * sr))
    t = np.arange(n) / sr
    x = ax.polyblep_saw(freq, n, sr) * 0.6 + ax.sine(freq, n, sr) * 0.8
    x = ax.soft(x, 1.5)
    x = ax.lp(x, float(cfg["tone"].get("bassCut", 380)), sr)
    env = np.minimum(1.0, t / 0.004) * np.exp(-t / max(0.02, length * 0.9))
    return x * env


def _sub_note(freq: float, cfg, length: float) -> np.ndarray:
    sr = cfg["sr"]
    n = max(1, int(length * 0.95 * sr))
    t = np.arange(n) / sr
    x = ax.soft(ax.sine(freq, n, sr) * 0.9 + ax.polyblep_saw(freq, n, sr) * 0.25, 1.3)
    x = ax.lp(x, 220, sr)
    return x * np.minimum(1.0, t / 0.01) * np.exp(-t / max(0.02, length * 0.8))


def _texture(cfg, r, length: float) -> np.ndarray:
    """Airy noise swell — the 'atmosphere' layer, decorrelated stereo."""
    sr = cfg["sr"]
    n = max(2, int(length * sr))
    noise = r.standard_normal((n, 2))
    t = np.arange(n) / sr
    env = np.sin(np.pi * np.clip(t / max(length, 1e-6), 0, 1)) ** 2
    band = ax.bp(noise, 300, min(9000, sr * 0.45), sr)
    return band * env[:, None]


def _crash(cfg, r) -> np.ndarray:
    sr = cfg["sr"]
    n = int(1.6 * sr)
    t = np.arange(n) / sr
    metal = sum(np.sign(np.sin(ax.TAU * f * t + (int(cfg["seed"]) % 7) * 0.9)) for f in (3120, 4260, 5350, 6980, 8470)) / 5.0
    body = ax.bp(r.standard_normal((n, 2)), 4000, min(11000, sr * 0.45), sr) * 0.8
    tone = ax.st(ax.bp(metal, 3000, min(10000, sr * 0.45), sr) * 0.5)
    return (body + tone) * (np.exp(-t / 0.38) * np.minimum(1.0, t / 0.002))[:, None] * 0.2


# --------------------------------------------------------------------------- arrangement
def _layer_active(cfg: dict, layer: str, section: str, energy: float) -> float:
    """How loud this layer is in this section (0 = silent). Layer level × density × energy."""
    vocab = vocabulary()["sections"]
    if section not in vocab:
        raise ValueError(f"unknown section {section!r}")
    if layer not in (vocab[section].get("layers") or []):
        return 0.0
    level = float(cfg["layers"].get(layer, 0.0))
    if level <= 0:
        return 0.0
    density = float(vocab[section].get("density", 1.0))
    # energy tilts the balance: >1 pushes rhythm layers, <1 pushes the pad/texture bed
    tilt = energy if layer in ("kick", "clap", "hat", "bass") else (2.0 - min(energy, 2.0) * 0.5)
    return max(0.0, level * density * tilt)


def render_music(cfg: MusicConfig | None = None, **overrides) -> np.ndarray:
    """Render the bed. Returns ``(samples, channels)`` float32 in ``[-1, 1]``, exactly ``duration`` long.

    Layers are independent: each is written into its own bus, then summed with its section gain.
    That is what makes "turn the hats down" a one-line change and keeps every layer testable.
    """
    if cfg is None:
        cfg = MusicConfig(**overrides)
    elif overrides:
        cfg = MusicConfig(**{**asdict(cfg), **overrides})
    r = cfg.resolved()
    sr, dur = r["sr"], r["duration"]
    n = int(round(dur * sr))
    if n <= 0:
        raise ValueError("duration produced zero samples")
    energy = r["energy"]
    spans = section_spans(r, dur)
    step = grid_seconds(r)
    spb, bar, bpb = beat_times(r)
    key = key_of(r["key"])
    scale = scale_of(r["scale"])
    prog = r["progression"]
    rs = ax.rng(r["seed"])

    buses = {name: np.zeros((n, 2)) for name in LAYERS}

    def put(layer: str, sig: np.ndarray, at: float, gain: float = 1.0) -> None:
        if gain <= 0:
            return
        i = int(round((at + r["bar_offset"]) * sr))
        ax.mix_into(buses[layer], sig, i, gain)

    # ---- one-shots (rendered once, reused) --------------------------------
    kick = ax.st(_kick(r, rs), 0.0)
    clap = _clap(r, rs)
    hat_c = ax.st(_hat(r, rs, False), 0.35)
    hat_o = ax.st(_hat(r, rs, True), -0.2)
    snare = _snare(r, rs)

    # ---- drum grid (16ths) ------------------------------------------------
    kicks: list[float] = []
    n16 = int(math.ceil((dur + spb) / step)) + 1
    for s16 in range(n16):
        t = s16 * step + swing_offset(r, s16)
        if t < 0 or t >= dur:
            continue
        sec = section_at(spans, t)
        beat, sub = divmod(s16, bpb)
        in_bar = beat % bpb
        nxt = next((s for s in spans if s["start"] > t), None)
        bars_left = ((nxt["start"] - t) / bar) if nxt else 99.0
        groove = r["groove"]

        # kick
        kpat = groove.get("kick", "four")
        kick_on = {
            "four": sub == 0,
            "half": sub == 0 and in_bar % 2 == 0,
            "off": False,
            "offbeat": sub == 2,
            "syncopated": (sub == 0) or (sub == 3 and in_bar % 2 == 1),
        }.get(kpat, sub == 0)
        if kick_on:
            g = _layer_active(r, "kick", sec, energy)
            if g > 0:
                put("kick", kick * (0.55 if sec == "intro" else 1.0), t, g)
                kicks.append(t)

        # clap on the backbeat
        cpat = groove.get("clap", "backbeat")
        clap_on = {"backbeat": sub == 0 and in_bar in (1, 3), "off": False,
                   "quarter": sub == 0, "all": sub == 0}.get(cpat, False)
        if clap_on and sec in ("drop", "outro"):
            g = _layer_active(r, "clap", sec, energy)
            if g > 0:
                put("clap", clap, t, g)

        # hats
        hpat = groove.get("hat", "eighth")
        hat_on = {"sixteenth": True, "eighth": sub % 2 == 0, "quarter": sub == 0,
                  "off": False}.get(hpat, sub % 2 == 0)
        if hat_on:
            g = _layer_active(r, "hat", sec, energy)
            if g > 0:
                accent = 1.0 if sub == 0 else (0.8 if sub == 2 else 0.5)
                put("hat", hat_c, t, g * accent * (0.7 if sec == "intro" else 1.0))
                if sub == 2 and in_bar == bpb - 1 and sec == "drop":
                    put("hat", hat_o, t, g * 0.4)

        # snare roll into the next section
        if sec == "build" and bars_left <= 1.0:
            rate = 2 if bars_left > 0.5 else 4
            if s16 % rate == 0:
                put("kick" if False else "hat", snare * (0.25 + 0.6 * (1.0 - min(bars_left, 1.0))), t,
                    _layer_active(r, "hat", sec, energy) * 0.6)

    # ---- per-bar tonal layers ---------------------------------------------
    nbars = int(math.ceil(dur / bar)) + 1
    for b in range(nbars):
        t0 = b * bar
        if t0 >= dur:
            break
        sec = section_at(spans, max(0.0, t0 + 1e-3))
        if sec == "stop":
            continue
        notes = chord_for(prog, b, key, scale, 3, 3)

        # pad
        g = _layer_active(r, "pad", sec, energy)
        if g > 0:
            put("pad", _pad_chord(r, notes, bar), t0, g * 0.05)

        # bass
        g = _layer_active(r, "bass", sec, energy)
        if g > 0:
            root = degree_to_semitone(int(prog[b % len(prog)]), key, scale, 1)
            f = note_hz(root)
            if sec == "break":
                for k2 in range(2):                     # two half-bar notes: the low end never vanishes
                    put("bass", ax.st(_sub_note(f, r, bar / 2) * 0.55), t0 + k2 * bar / 2, g)
            else:
                pattern = r["groove"].get("bass", "eighth")
                div = {"whole": 1, "half": 2, "quarter": 4, "eighth": 8, "sixteenth": 16}.get(pattern, 8)
                L = bar / div
                for k in range(div):
                    tb = t0 + k * L
                    if tb >= dur:
                        break
                    if sec == "build" and k % 2:
                        continue
                    octave = 2 if (sec == "drop" and k % 4 == 3) else 1
                    put("bass", ax.st(_bass_note(f * octave, r, L) * 0.5), tb, g)

        # pluck arpeggio
        g = _layer_active(r, "pluck", sec, energy)
        if g > 0:
            pattern = r["groove"].get("pluck", "eighth")
            div = {"whole": 1, "half": 2, "quarter": 4, "eighth": 8, "sixteenth": 16}.get(pattern, 8)
            L = bar / div
            seq = [0, 1, 2, 1]
            for k in range(div):
                ta = t0 + k * L
                if ta >= dur:
                    break
                semi = notes[seq[k % len(seq)] % len(notes)] + 24
                put("pluck", ax.st(_pluck(note_hz(semi), r), 0.45 if k % 2 else -0.45), ta, g * 0.35)

        # melody: a sparse, higher line (only where the arrangement asks for it)
        g = _layer_active(r, "melody", sec, energy)
        if g > 0:
            for k, degree in enumerate((0, 4, 2, 5)):
                ta = t0 + k * bar / 4
                if ta >= dur:
                    break
                semi = degree_to_semitone(int(prog[b % len(prog)]) + degree, key, scale, 4)
                put("melody", ax.st(_pluck(note_hz(semi), r, 0.5), 0.25 if k % 2 else -0.25), ta, g * 0.30)

        # texture
        g = _layer_active(r, "texture", sec, energy)
        if g > 0:
            put("texture", _texture(r, rs, bar * 1.2), t0, g * 0.5)

    # ---- section accents ---------------------------------------------------
    for span in spans:
        if span["name"] == "drop" and span["start"] > 0.05:
            put("texture", _crash(r, rs), span["start"], 0.5)

    # ---- kick-driven sidechain pump ---------------------------------------
    if kicks:
        tt = np.arange(n) / sr
        ks = np.array(sorted(kicks))
        index = np.searchsorted(ks, tt, side="right") - 1
        since = np.where(index >= 0, tt - ks[np.maximum(index, 0)], 10.0)
        pump = 1.0 - 0.55 * np.exp(-since / 0.11)
        for name in ("pad", "bass", "pluck", "melody"):
            buses[name] *= pump[:, None]

    # ---- space + balance ---------------------------------------------------
    tone = r["tone"]
    rt = 2.6 if r["preset"] == "cinematic" else 1.8
    for name in ("pad", "pluck", "melody"):
        buses[name] = ax.reverb(buses[name], rt, float(tone.get("reverb", 0.2)), sr, seed=r["seed"])[:n]
    buses["texture"] = ax.reverb(buses["texture"], 3.4, 0.45, sr, seed=r["seed"] + 1)[:n]

    mix = np.zeros((n, 2))
    for name, bus in buses.items():
        if name == "texture":
            mix += bus * 0.35
        else:
            mix += bus
    # phone/top layer: kick+bass+pad are < 150 Hz and vanish on a phone speaker.
    top = r["top"]
    if any(float(v) != 0.0 for v in top.values()):
        top_bus = np.zeros((n, 2))
        for s16 in range(n16):
            t = s16 * step + swing_offset(r, s16)
            if t >= dur:
                continue
            sec = section_at(spans, t)
            if sec == "stop":
                continue
            g = _layer_active(r, "pluck", sec, energy)
            if g <= 0:
                continue
            if s16 % 2 == 0:
                b = int(t // bar)
                notes = chord_for(prog, b, key, scale, 5, 3)
                pattern = [0, 2, 1, 2]
                semi = notes[pattern[(s16 // 2) % len(pattern)] % len(notes)]
                ax.mix_into(top_bus, ax.st(_pluck(note_hz(semi), r, 0.22), 0.3 if (s16 // 2) % 2 else -0.3),
                            int(round(t * sr)), g * ax.db(float(top.get("pluck", 0.0))))
            g_hat = _layer_active(r, "hat", sec, energy)
            if g_hat > 0 and s16 % 2 == 1:
                ax.mix_into(top_bus, hat_c, int(round(t * sr)),
                            g_hat * 0.35 * ax.db(float(top.get("hat", 0.0))))
        mix += top_bus

    # ---- master chain ------------------------------------------------------
    # Fixed gain staging, NOT peak normalisation. Normalising to the peak means a bed with one layer
    # left is turned up to the same peak as the full arrangement — so "turn the hats down" makes the
    # hats louder, and `level_db` in the mixer means nothing. The bed is rendered at a stable level
    # (a full arrangement lands near -18 dBFS RMS) and the limiter is a safety net, not a mixer.
    mix = ax.hp(ax.lp(mix, min(15500, sr * 0.46), sr), 28, sr)
    mix = ax.soft(mix * MASTER_GAIN * float(ax.db(r["trim_db"])), float(tone.get("drive", 1.3)))
    # Fades are *proportional*: a fixed 1.2 s fade-out would eat a quarter of a 5 s sting, and the
    # mix reports the level of the bed as the listener hears it (per second), so the curve matters.
    fi = min(r["fade_in"], 0.25 * dur)
    fo = min(r["fade_out"], 0.20 * dur)
    mix = ax.fade(mix, sr, fade_in=fi, fade_out=fo)
    mix *= hard_gate(spans, n, sr)[:, None]
    mix = ax.limiter(mix, ceiling=0.89, sr=sr)
    if r["channels"] == 1:
        mix = mix.mean(axis=1, keepdims=True)
    return np.ascontiguousarray(np.clip(mix, -1.0, 1.0), dtype=np.float32)


def music_info(cfg: MusicConfig | None = None, **overrides) -> dict:
    """A deterministic description of what `render_music` will produce (no audio rendered)."""
    if cfg is None:
        cfg = MusicConfig(**overrides)
    r = cfg.resolved()
    spb, bar, bpb = beat_times(r)
    spans = section_spans(r, r["duration"])
    return {
        "preset": r["preset"],
        "duration": r["duration"],
        "bpm": r["bpm"],
        "barSeconds": round(bar, 6),
        "beatsPerBar": bpb,
        "sixteenthSeconds": round(grid_seconds(r), 6),
        "key": r["key"],
        "scale": r["scale"],
        "progression": r["progression"],
        "sections": [{"name": s["name"], "start": s["start"], "end": s["end"]} for s in spans],
        "layers": r["layers"],
        "energy": r["energy"],
        "levelTrimDb": round(float(r["trim_db"]), 2),
        "seed": r["seed"],
        "sr": r["sr"],
        "channels": r["channels"],
        "samples": int(round(r["duration"] * r["sr"])),
    }


def write_music(path, cfg: MusicConfig | None = None, **overrides) -> tuple[str, np.ndarray]:
    """Render and write a WAV; returns the path and the samples (so a caller can reuse them)."""
    if cfg is None:
        cfg = MusicConfig(**overrides)
    elif overrides:
        cfg = MusicConfig(**{**asdict(cfg), **overrides})
    audio = render_music(cfg)
    ax.write_wav(path, audio, cfg.sr)
    return str(path), audio
