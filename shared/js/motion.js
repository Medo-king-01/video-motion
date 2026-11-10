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

// Classic Penner equations (the MIT `easing-functions` implementation): the shapes a cubic-bezier
// simply cannot express — elastic, bounce — plus the exact quad/cubic/quart/quint/sine/expo families.
// Names never collide with the bezier vocabulary above, so `ease()` can dispatch on both.
const n1 = 7.5625, d1 = 2.75;
const bounceOut = t =>
  t < 1 / d1 ? n1 * t * t
    : t < 2 / d1 ? n1 * (t -= 1.5 / d1) * t + 0.75
      : t < 2.5 / d1 ? n1 * (t -= 2.25 / d1) * t + 0.9375
        : n1 * (t -= 2.625 / d1) * t + 0.984375;
export const FORMULAS = {
  smoothstep: t => t * t * (3 - 2 * t),
  smootherstep: t => t * t * t * (t * (t * 6 - 15) + 10),
  quadIn: t => t * t,
  quadOut: t => 1 - (1 - t) * (1 - t),
  quadInOut: t => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  cubicIn: t => t * t * t,
  cubicOut: t => 1 - Math.pow(1 - t, 3),
  cubicInOut: t => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  quartIn: t => t * t * t * t,
  quartOut: t => 1 - Math.pow(1 - t, 4),
  quartInOut: t => (t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2),
  quintIn: t => Math.pow(t, 5),
  quintOut: t => 1 - Math.pow(1 - t, 5),
  quintInOut: t => (t < 0.5 ? 16 * Math.pow(t, 5) : 1 - Math.pow(-2 * t + 2, 5) / 2),
  sineIn: t => 1 - Math.cos((t * Math.PI) / 2),
  sineOut: t => Math.sin((t * Math.PI) / 2),
  sineInOut: t => -(Math.cos(Math.PI * t) - 1) / 2,
  expoIn: t => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
  expoOut: t => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  expoInOut: t => (t === 0 ? 0 : t === 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2),
  elasticIn: t => (t === 0 ? 0 : t === 1 ? 1 : -Math.pow(2, 10 * t - 10) * Math.sin((t * 10 - 10.75) * ((2 * Math.PI) / 3))),
  elasticOut: t => (t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * ((2 * Math.PI) / 3)) + 1),
  elasticInOut: t => (t === 0 ? 0 : t === 1 ? 1
    : (t < 0.5
      ? -(Math.pow(2, 20 * t - 10) * Math.sin((20 * t - 11.125) * ((2 * Math.PI) / 4.5))) / 2
      : (Math.pow(2, -20 * t + 10) * Math.sin((20 * t - 11.125) * ((2 * Math.PI) / 4.5))) / 2 + 1)),
  bounceIn: t => 1 - bounceOut(1 - t),
  bounceOut,
  bounceInOut: t => (t < 0.5 ? (1 - bounceOut(1 - 2 * t)) / 2 : (1 + bounceOut(2 * t - 1)) / 2),
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
  if (!Array.isArray(spec) && !CUBIC_BEZIER[spec]) throw new Error(`unknown easing name: ${spec} (see medo-motion/motion/easings.json)`);
  const pts = Array.isArray(spec) ? spec : CUBIC_BEZIER[spec];   // no silent easeOut fallback
  const fn = cubicBezier(pts[0], pts[1], pts[2], pts[3]);
  CACHE.set(key, fn);
  return fn;
}

/** ease('backOut', 0.4) · ease([0.34,1.56,0.64,1], 0.4) */
export function ease(name, p) {
  if (typeof name === 'string' && FORMULAS[name]) return FORMULAS[name](clamp(p));
  return curve(name)(clamp(p));
}

/** Every easing name this engine understands (bezier vocabulary + equation vocabulary). */
export const EASING_NAMES = [...Object.keys(CUBIC_BEZIER), ...Object.keys(FORMULAS)];

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
  if (zeta < 1) {          // underdamped: oscillates
    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    const A = 1;
    const B = (zeta * w0 - velocity) / wd;
    return 1 - Math.exp(-zeta * w0 * elapsed) * (A * Math.cos(wd * elapsed) + B * Math.sin(wd * elapsed));
  }
  if (Math.abs(zeta - 1) < 1e-9) {   // critically damped: the repeated-root solution
    const e = Math.exp(-w0 * elapsed);
    return 1 - e * (1 + (w0 - velocity) * elapsed);
  }
  // overdamped (zeta > 1): two REAL roots — cosh/sinh, not the critical formula
  const wr = w0 * Math.sqrt(zeta * zeta - 1);
  const B = (zeta * w0 - velocity) / wr;
  return 1 - Math.exp(-zeta * w0 * elapsed) * (Math.cosh(wr * elapsed) + B * Math.sinh(wr * elapsed));
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

// ---------------------------------------------------------------- velocity & motion blur
/** Central-difference velocity of a scalar property (px or rad per second) — a pure function of t. */
export function velocity(fn, t, dt = 1 / 240) {
  const h = Math.max(1e-6, dt) / 2;
  return (fn(t + h) - fn(t - h)) / (2 * h);
}

/**
 * Offsets + weights for a directional motion blur, from a velocity in px/s.
 * `shutter` = virtual exposure (s), displacement = v · shutter clamped to `max_px`, weights uniform
 * and summing to 1 so `alpha * w` keeps the exposure. Zero velocity → [[0, 0, 1]] (a sharp draw).
 */
export function blurSteps(vx, vy, samples = 6, shutter = 0.055, maxPx = 26) {
  let dx = vx * shutter, dy = vy * shutter;
  let dist = Math.hypot(dx, dy);
  if (dist < 0.35 || samples < 2) return [[0, 0, 1]];
  if (dist > maxPx) { const k = maxPx / dist; dx *= k; dy *= k; }
  const n = Math.max(2, Math.floor(samples));
  const w = 1 / n;
  return Array.from({ length: n }, (_, i) => [
    Math.round((-dx * (i + 1) / n) * 1e4) / 1e4,
    Math.round((-dy * (i + 1) / n) * 1e4) / 1e4,
    Math.round(w * 1e6) / 1e6,
  ]);
}

/** Draw something N times along its own velocity. `draw(alpha)` receives the per-step opacity. */
export function drawBlurred(ctx, draw, vx, vy, opts = {}) {
  const steps = blurSteps(vx, vy, opts.samples ?? 6, opts.shutter ?? 0.055, opts.maxPx ?? 26);
  ctx.save();
  for (const [dx, dy, w] of steps) {
    ctx.save();
    ctx.translate(dx, dy);
    ctx.globalAlpha *= w * (opts.alpha ?? 1);
    draw(ctx);
    ctx.restore();
  }
  ctx.restore();
  return steps;
}
