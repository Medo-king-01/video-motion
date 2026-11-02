// Rhythm for engine K — a beat grid, identical to presenter's `beat.py`.
//
// Nothing here holds state: give it a `t` and a `bpm` and you get the same answer on every machine,
// which is what makes a reel scrubbable frame by frame. A cut that lands 80 ms off the beat reads as
// a mistake even when nobody can name it — build at a tempo, then quantise the cuts and hits.
//
//   import { grid, quantize, ping } from './beat.js';
//   grid(1.7, 120)            // { beat: 3, phase: .4, bar: 0, barPhase: .85, spb: .5 }
//   quantize(1.44, 120, 2)    // 1.5  (eighth notes)
export const BEATS_PER_BAR = 4;

/** Where `t` sits in the tempo grid. */
export function grid(t, bpm = 120, offset = 0) {
  const spb = 60 / bpm;
  const pos = (t - offset) / spb;
  const beat = Math.floor(pos);
  const phase = pos - beat;
  const bar = Math.floor(beat / BEATS_PER_BAR);
  return { beat, phase, bar, barPhase: bar / BEATS_PER_BAR + phase / BEATS_PER_BAR, pos, spb, bpm };
}

/** Snap `t` to `div` steps per beat (4 = sixteenths, 2 = eighths, 1 = beats). */
export function quantize(t, bpm = 120, div = 4, offset = 0, mode = 'nearest') {
  if (!(div >= 1)) throw new Error('div must be >= 1 (steps per beat)');
  const step = 60 / bpm / div;
  const x = (t - offset) / step;
  const k = mode === 'floor' ? Math.floor(x) : mode === 'ceil' ? Math.ceil(x)
    : mode === 'nearest' ? Math.floor(x + 0.5) : (() => { throw new Error('mode must be nearest, floor or ceil'); })();
  return Math.round((offset + k * step) * 1e6) / 1e6;
}

/** Signed distance from `t` to the nearest grid line (seconds). */
export const offsetOf = (t, bpm = 120, div = 4, offset = 0) =>
  Math.round((t - quantize(t, bpm, div, offset)) * 1e6) / 1e6;

/** A spike that is 1 exactly on the beat and decays before the next one. */
export function ping(t, bpm = 120, offset = 0, curve = 14) {
  const g = grid(t, bpm, offset);
  return Math.exp(-g.phase * g.spb * curve);
}

/** Half-sine per beat: 0 at the beat, 1 in the middle, 0 at the next beat. */
export function swell(t, bpm = 120, offset = 0, power = 1) {
  const g = grid(t, bpm, offset);
  return Math.sin(Math.PI * g.phase) ** power;
}

/** Sawtooth inside one beat, quantised to `div` steps. */
export function ladder(t, bpm = 120, offset = 0, div = 4) {
  const g = grid(t, bpm, offset);
  const steps = Math.max(1, Math.floor(div));
  return steps > 1 ? Math.min(1, Math.floor(g.phase * steps) / (steps - 1)) : 1;
}

/** `n` consecutive grid times — a stagger for a list, a row of tiles or a run of hits. */
export function onGrid(n, bpm = 120, div = 4, offset = 0, start = 0) {
  const step = 60 / bpm / div;
  return Array.from({ length: n }, (_, i) => Math.round((offset + (start + i) * step) * 1e6) / 1e6);
}

/** Length of `beats` beats in seconds. */
export const barSeconds = (bpm = 120, beats = BEATS_PER_BAR) => (beats * 60) / bpm;
