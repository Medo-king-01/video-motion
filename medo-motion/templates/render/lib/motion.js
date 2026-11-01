// Motion grammar for engine K — deterministic, scrubbable, frame-independent.
//
// Why this file exists: motion.dev and Theatre.js are great, but they animate in *real time* on the
// DOM, while a reel is rendered frame-by-frame (seek to t → draw → encode). So instead of importing
// either library into the renderer, we keep their vocabulary and their maths:
//   * easing names + control points from motion.dev → `ease('backOut', p)`
//   * springs (stiffness / damping / mass)      → `spring(elapsed, {stiffness, damping})`
//   * keyframe tracks (Theatre.js sequences)    → `timeline({tracks}).at(t)`
// Everything here is a pure function of `t`: the same frame always looks the same, at any fps.
//
// Curves live in medo-motion/motion/easings.json (tests/test_motion.py keeps this file in sync).

export const CUBIC_BEZIER = {
  linear: [0, 0, 1, 1],
  ease: [0.25, 0.1, 0.25, 1],
  easeIn: [0.42, 0, 1, 1],
  easeOut: [0, 0, 0.58, 1],
  easeInOut: [0.42, 0, 0.58, 1],
  circIn: [0.55, 0, 1, 0.45],
  circOut: [0, 0.55, 0.45, 1],
  circInOut: [0.85, 0, 0.15, 1],
  backIn: [0.36, 0, 0.66, -0.56],
  backOut: [0.34, 1.56, 0.64, 1],
  backInOut: [0.68, -0.6, 0.32, 1.6],
  anticipate: [0.36, 0, 0.66, -0.56],
};

export const SPRING_PRESETS = {
  default: { stiffness: 100, damping: 10, mass: 1 },
  soft: { stiffness: 80, damping: 18, mass: 1 },
  snappy: { stiffness: 220, damping: 22, mass: 1 },
  bouncy: { stiffness: 260, damping: 12, mass: 1 },
  heavy: { stiffness: 120, damping: 26, mass: 2 },
};

export const clamp = (v, lo = 0, hi = 1) => (v < lo ? lo : v > hi ? hi : v);
export const lerp = (a, b, p) => a + (b - a) * p;
export const progress = (t, start, dur) => (dur <= 0 ? (t >= start ? 1 : 0) : clamp((t - start) / dur));
export const stagger = (i, each = 0.06, from = 0) => from + i * each;

/** Cubic-bezier(x1,y1,x2,y2) → (p) => eased p. Newton-Raphson with a bisection fallback. */
export function cubicBezier(x1, y1, x2, y2) {
  const ax = 3 * x1 - 3 * x2 + 1, bx = 3 * x2 - 6 * x1, cx = 3 * x1;
  const ay = 3 * y1 - 3 * y2 + 1, by = 3 * y2 - 6 * y1, cy = 3 * y1;
  const sampleX = t => ((ax * t + bx) * t + cx) * t;
  const sampleY = t => ((ay * t + by) * t + cy) * t;
  const slopeX = t => (3 * ax * t + 2 * bx) * t + cx;
  return p => {
    if (p <= 0) return 0;
    if (p >= 1) return 1;
    let t = p;
    for (let i = 0; i < 8; i++) {
      const x = sampleX(t) - p;
      if (Math.abs(x) < 1e-6) return sampleY(t);
      const d = slopeX(t);
      if (Math.abs(d) < 1e-6) break;
      t -= x / d;
    }
    let lo = 0, hi = 1;
    t = p;
    for (let i = 0; i < 40; i++) {
      const x = sampleX(t);
      if (Math.abs(x - p) < 1e-6) break;
      if (x < p) lo = t; else hi = t;
      t = (lo + hi) / 2;
    }
    return sampleY(t);
  };
}

const CACHE = new Map();
function curve(spec) {
  if (typeof spec === 'function') return spec;
  const key = Array.isArray(spec) ? spec.join(',') : String(spec);
  if (CACHE.has(key)) return CACHE.get(key);
  const pts = Array.isArray(spec) ? spec : (CUBIC_BEZIER[spec] || CUBIC_BEZIER.easeOut);
  const fn = cubicBezier(pts[0], pts[1], pts[2], pts[3]);
  CACHE.set(key, fn);
  return fn;
}

/** ease('backOut', 0.4) · ease([0.34,1.56,0.64,1], 0.4) */
export function ease(name, p) {
  return curve(name)(clamp(p));
}

/**
 * Closed-form damped spring, normalised so it settles at 1 (it overshoots on purpose).
 * `elapsed` is in seconds — a spring has its own timing, exactly like motion.dev's type: "spring".
 */
export function spring(elapsed, params = {}) {
  let conf = params;
  if (typeof params === 'string') conf = SPRING_PRESETS[params] || SPRING_PRESETS.default;
  const stiffness = conf.stiffness ?? 100;
  const damping = conf.damping ?? 10;
  const mass = conf.mass ?? 1;
  const velocity = conf.velocity ?? 0;
  if (elapsed <= 0) return 0;
  const w0 = Math.sqrt(stiffness / mass);
  const zeta = damping / (2 * Math.sqrt(stiffness * mass));
  if (zeta < 1) {
    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    const A = 1;
    const B = (zeta * w0 - velocity) / wd;
    return 1 - Math.exp(-zeta * w0 * elapsed) * (A * Math.cos(wd * elapsed) + B * Math.sin(wd * elapsed));
  }
  const e = Math.exp(-w0 * elapsed);
  return 1 - e * (1 + (w0 - velocity) * elapsed);
}

/** Seconds until the spring is within `band` (default 1%) of its resting value. */
export function springDuration(params = {}, band = 0.01) {
  const conf = typeof params === 'string' ? (SPRING_PRESETS[params] || SPRING_PRESETS.default) : params;
  const w0 = Math.sqrt((conf.stiffness ?? 100) / (conf.mass ?? 1));
  const zeta = (conf.damping ?? 10) / (2 * Math.sqrt((conf.stiffness ?? 100) * (conf.mass ?? 1)));
  if (zeta >= 1) return Math.log(1 / band) / w0 + 1 / w0;
  return Math.log(1 / (band * Math.sqrt(1 - zeta * zeta))) / (zeta * w0);
}

const isColor = v => Array.isArray(v);
const mix = (a, b, p) => (isColor(a) ? a.map((c, i) => lerp(c, b[i] ?? c, p)) : lerp(a, b, p));

/**
 * Sample one keyframe track at time t.
 * track: [{ t: 0, v: 120 }, { t: 0.6, v: 0, ease: 'spring' | 'backOut' | [x1,y1,x2,y2] | {type:'spring', stiffness…} }]
 * The `ease` of a keyframe shapes the segment that *arrives* at it.
 */
export function keyframes(track, t) {
  if (!track || !track.length) return 0;
  if (t <= track[0].t) return track[0].v;
  const last = track[track.length - 1];
  if (t >= last.t) return last.v;
  let i = 0;
  while (i < track.length - 1 && t >= track[i + 1].t) i++;
  const a = track[i], b = track[i + 1];
  const span = Math.max(1e-6, b.t - a.t);
  const p = (t - a.t) / span;
  const spec = b.ease ?? 'easeOut';
  if (spec === 'spring' || (spec && typeof spec === 'object' && spec.type === 'spring')) {
    const conf = typeof spec === 'object' && spec.type === 'spring' ? spec : {};
    return mix(a.v, b.v, spring(t - a.t, conf));
  }
  if (typeof spec === 'string' && SPRING_PRESETS[spec]) {
    return mix(a.v, b.v, spring(t - a.t, spec));
  }
  return mix(a.v, b.v, ease(spec, p));
}

/**
 * timeline({ duration: 3, tracks: { 'card.y': [...], 'card.opacity': [...] } })
 *   .at(t)  → { 'card.y': 0, 'card.opacity': 1, … }
 */
export function timeline(spec) {
  const tracks = spec.tracks ?? {};
  const duration = spec.duration ?? Math.max(0, ...Object.values(tracks).map(tr => (tr.length ? tr[tr.length - 1].t : 0)));
  return {
    duration,
    tracks,
    at(t) {
      const out = {};
      for (const [name, track] of Object.entries(tracks)) out[name] = keyframes(track, t);
      return out;
    },
    /** first time any keyframe exists for this track (handy for staggering entrances) */
    startOf(name) {
      const track = tracks[name];
      return track && track.length ? track[0].t : 0;
    },
  };
}

/** 0→1 entrance helper: reveal(0.42, 0.15, 0.5, 'backOut') */
export function reveal(t, start, dur, easeName = 'easeOut') {
  return ease(easeName, progress(t, start, dur));
}
