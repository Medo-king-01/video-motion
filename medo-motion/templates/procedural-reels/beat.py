"""Rhythm for engine P — a beat grid that every other timing decision can be quantised onto.

Identical maths to engine K (`templates/render/lib/beat.js`). Nothing here holds state: give it a
`t` and a `bpm` and you get the same answer on every machine, which is what makes a reel scrubbable
frame by frame.

Why a grid at all: a cut that lands 80 ms off the beat reads as a mistake even when nobody can name
it. Build the reel at a tempo, then put the cuts, the hits and the micro-actions on the grid.

    from beat import grid, quantize, ping
    grid(1.7, 120)          # {'beat': 3, 'phase': .4, 'bar': 0, 'bar_phase': .85, 'spb': .5}
    quantize(1.44, 120, 2)  # 1.5   (eighth notes)
    ping(1.7, 120, curve=18)  # 0.027 -> a 1-at-the-beat spike that decays before the next beat
"""
from __future__ import annotations

import math

BEATS_PER_BAR = 4


def grid(t: float, bpm: float = 120.0, offset: float = 0.0) -> dict:
    """Where `t` sits in the tempo grid.

    `beat` counts from the first beat, `phase` is 0→1 through that beat, `bar`/`bar_phase` do the
    same for 4/4 bars. `spb` is seconds per beat, `pos` the position in beats (fractional).
    """
    spb = 60.0 / float(bpm)
    pos = (float(t) - float(offset)) / spb
    beat = math.floor(pos)
    phase = pos - beat
    bar = math.floor(beat / BEATS_PER_BAR)
    return {
        "beat": beat,
        "phase": phase,
        "bar": bar,
        "bar_phase": bar / BEATS_PER_BAR + phase / BEATS_PER_BAR,
        "pos": pos,
        "spb": spb,
        "bpm": float(bpm),
    }


def quantize(t: float, bpm: float = 120.0, div: int = 4, offset: float = 0.0,
             mode: str = "nearest") -> float:
    """Snap `t` to the grid: `div` steps per beat (4 = sixteenths, 2 = eighths, 1 = beats).

    `mode` is 'nearest', 'floor' or 'ceil'. Times before `offset` snap to `offset`.
    """
    if div < 1:
        raise ValueError("div must be >= 1 (steps per beat)")
    step = 60.0 / float(bpm) / div
    x = (float(t) - float(offset)) / step
    if mode == "floor":
        k = math.floor(x)
    elif mode == "ceil":
        k = math.ceil(x)
    elif mode == "nearest":
        k = math.floor(x + 0.5)
    else:
        raise ValueError("mode must be nearest, floor or ceil")
    return round(offset + k * step, 6)


def offset_of(t: float, bpm: float = 120.0, div: int = 4, offset: float = 0.0) -> float:
    """Signed distance from `t` to the nearest grid line (seconds) — a QA number for cut lists."""
    return round(float(t) - quantize(t, bpm, div, offset), 6)


def ping(t: float, bpm: float = 120.0, offset: float = 0.0, curve: float = 14.0) -> float:
    """A spike that is 1 exactly on the beat and decays before the next one (1 → ~0)."""
    g = grid(t, bpm, offset)
    return math.exp(-g["phase"] * g["spb"] * curve)


def swell(t: float, bpm: float = 120.0, offset: float = 0.0, power: float = 1.0) -> float:
    """Half-sine per beat: 0 at the beat, 1 in the middle, 0 at the next beat."""
    g = grid(t, bpm, offset)
    return math.sin(math.pi * g["phase"]) ** power


def ladder(t: float, bpm: float = 120.0, offset: float = 0.0, div: int = 4) -> float:
    """Sawtooth inside one beat, quantised to `div` steps — a stepped counter that never overshoots."""
    g = grid(t, bpm, offset)
    steps = max(1, int(div))
    return min(1.0, math.floor(g["phase"] * steps) / (steps - 1)) if steps > 1 else 1.0


def on_grid(n: int, bpm: float = 120.0, div: int = 4, offset: float = 0.0, start: int = 0) -> list[float]:
    """`n` consecutive grid times — the stagger for a list, a row of tiles or a run of hits."""
    step = 60.0 / float(bpm) / div
    return [round(offset + (start + i) * step, 6) for i in range(int(n))]


def snap_bounds(bounds: list[float], bpm: float = 120.0, div: int = 2, offset: float = 0.0,
                tol: float = 0.12) -> tuple[list[float], int]:
    """Move each interior cut to the nearest grid line when it is within `tol` seconds.

    The first and last bound are the VO's start and end — those belong to the voice, never the grid.
    Returns the new bounds and how many cuts actually moved.
    """
    if len(bounds) < 3:
        return list(bounds), 0
    out, moved = [bounds[0]], 0
    for b in bounds[1:-1]:
        q = quantize(b, bpm, div, offset)
        if abs(q - b) <= tol and q > out[-1]:
            out.append(q)
            moved += int(abs(q - b) > 1e-9)     # a cut already on the grid did not move
        else:
            out.append(b)
    out.append(bounds[-1])
    return out, moved


def bar_seconds(bpm: float = 120.0, beats: int = BEATS_PER_BAR) -> float:
    """Length of `beats` beats in seconds — loop lengths, music beds, pattern buffers."""
    return beats * 60.0 / float(bpm)
