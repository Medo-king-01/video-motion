// Deterministic, frame-addressable element moves for engines K and R.
// The matching Python implementation lives in procedural-reels/moves.py.
// Nothing here draws or holds state: a move maps (status, time) -> numbers.
//
// Two rules the tests enforce:
//  * a move is a pure function of its arguments (same input, same output, no RNG);
//  * an unknown or nonsensical argument throws instead of silently falling back.
import { clamp } from './motion.js';

const easeOutCubic = p => 1 - Math.pow(1 - p, 3);

const finite = (value, name) => {
  const n = Number(value);
  if (!Number.isFinite(n)) throw new TypeError(`${name} must be a finite number`);
  return n;
};

const nonNegative = (value, name) => {
  const n = finite(value, name);
  if (n < 0) throw new RangeError(`${name} must be >= 0`);
  return n;
};

const positive = (value, name) => {
  const n = finite(value, name);
  if (!(n > 0)) throw new RangeError(`${name} must be > 0`);
  return n;
};

/**
 * One item of a "pixel list": rows arrive in reading order, each after `stagger`,
 * rising from below and sliding in horizontally, with the offset snapped to whole
 * pixels of `fontSize` so a scrub never leaves half-pixel text.
 *
 * Returns { opacity, x, y, scale, pixelStep } where x/y are in em (multiply by the
 * font size), y is already snapped, and pixelStep is the snap grid in em.
 */
export function pixelListItem(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const stagger = nonNegative(options.stagger ?? 0.09, 'stagger');
  const enter = positive(options.enter ?? 0.42, 'enter');
  const rise = finite(options.rise ?? 0.6, 'rise');
  const from = finite(options.from ?? 0.72, 'from');
  const fontSize = positive(options.fontSize ?? 40, 'fontSize');

  const local = t - i * stagger;
  const p = local <= 0 ? 0 : local >= enter ? 1 : easeOutCubic(local / enter);
  const pixelStep = 1 / fontSize;
  const snapped = value => Math.round(value * fontSize) / fontSize;
  return {
    opacity: p,
    x: snapped(from * (1 - p)),
    y: snapped(-rise * (1 - p)),
    scale: 1,
    pixelStep,
  };
}

/**
 * One parallax layer. `progress` is the camera's normalized travel (0..1) and `depth`
 * is how strongly the layer follows it (0 = background pinned, 1 = foreground moves fully).
 * Returns { x, y, scale } in em / unitless.
 */
export function parallaxLayer(depth, progress, options = {}) {
  const d = finite(depth, 'depth');
  if (d < 0 || d > 1) throw new RangeError('depth must be within 0..1');
  const camera = clamp(finite(progress, 'progress'), 0, 1);
  const panX = finite(options.panX ?? 0.8, 'panX');
  const panY = finite(options.panY ?? 0.0, 'panY');
  const zoom = nonNegative(options.zoom ?? 0.04, 'zoom');
  return {
    x: -panX * d * camera,
    y: -panY * d * camera,
    scale: 1 + zoom * d * camera,
  };
}

/**
 * Convenience for a scene that wants progress from absolute time.
 * Returns 0 before `start`, 1 after `start + duration`, eased in between.
 */
export function cameraProgress(elapsed, start = 0, duration = 1) {
  const t = finite(elapsed, 'elapsed');
  const s = finite(start, 'start');
  const dur = positive(duration, 'duration');
  if (t <= s) return 0;
  if (t >= s + dur) return 1;
  return easeOutCubic((t - s) / dur);
}

/** Normalized progress helper shared by the moves below (clamped, eased). */
function windowProgress(elapsed, start, duration) {
  const t = finite(elapsed, 'elapsed');
  const s = finite(start, 'start');
  const dur = positive(duration, 'duration');
  if (t <= s) return 0;
  if (t >= s + dur) return 1;
  return easeOutCubic((t - s) / dur);
}

/** Deterministic 32-bit hash shared with Python; no Math.random. */
function hash01(value) {
  return ((Math.imul(value | 0, 1664525) + 1013904223) >>> 0) / 4294967296;
}

/**
 * One item orbiting a centre on an ellipse. Returns { x, y, scale, angle, depth, opacity }
 * where x/y are em, depth is sin(angle) (negative = behind), scale shrinks with depth.
 */
export function orbitItem(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const count = options.count ?? 6;
  if (!Number.isInteger(count) || count < 1) throw new RangeError('count must be a positive integer');
  const radius = positive(options.radius ?? 1.2, 'radius');
  const speed = nonNegative(options.speed ?? 0.35, 'speed');
  const start = finite(options.start ?? 0, 'start');
  const phase = finite(options.phase ?? 0, 'phase');
  const squash = positive(options.squash ?? 0.35, 'squash');
  const angle = 2 * Math.PI * (phase + Math.max(0, t - start) * speed) + (2 * Math.PI * i) / count;
  const depth = Math.sin(angle);
  return {
    x: radius * Math.cos(angle),
    y: radius * squash * depth,
    scale: 1 + 0.08 * depth,
    angle,
    depth,
    opacity: 1,
  };
}

/**
 * One word travelling a straight path in em. Arbitrary polylines are not supported yet.
 * Returns { x, y, rotation, opacity, progress }.
 */
export function wordPathItem(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const stagger = nonNegative(options.stagger ?? 0.08, 'stagger');
  const enter = positive(options.enter ?? 0.5, 'enter');
  const p = clamp((t - i * stagger) / enter, 0, 1);
  const eased = easeOutCubic(p);
  const lerp = (a, b) => a + (b - a) * eased;
  return {
    x: lerp(finite(options.fromX ?? -2, 'fromX'), finite(options.toX ?? 0, 'toX')),
    y: lerp(finite(options.fromY ?? 0, 'fromY'), finite(options.toY ?? 0, 'toY')),
    rotation: finite(options.rotation ?? 0, 'rotation') * (1 - eased),
    opacity: eased,
    progress: p,
  };
}

/**
 * One part of an explode/assemble move: radial separation, optional return.
 * Returns { x, y, rotation, opacity, progress } with x/y in em.
 */
export function explodePart(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const count = options.count ?? 6;
  if (!Number.isInteger(count) || count < 1) throw new RangeError('count must be a positive integer');
  const start = finite(options.start ?? 0, 'start');
  const duration = positive(options.duration ?? 0.6, 'duration');
  const hold = nonNegative(options.hold ?? 0.4, 'hold');
  const back = positive(options.back ?? duration, 'back');
  const spread = positive(options.spread ?? 2.2, 'spread');
  const tilt = finite(options.tilt ?? 8, 'tilt');
  const phase = finite(options.phase ?? 0, 'phase');
  const local = t - start;
  let p;
  if (local <= 0) p = 0;
  else if (local < duration) p = easeOutCubic(local / duration);
  else if (options.reassemble === false || local < duration + hold) p = 1;
  else if (local >= duration + hold + back) p = 0;
  else p = 1 - easeOutCubic((local - duration - hold) / back);
  const angle = phase + (2 * Math.PI * i) / count;
  const direction = i % 2 === 0 ? 1 : -1;
  return {
    x: spread * p * Math.cos(angle),
    y: spread * 0.6 * p * Math.sin(angle),
    rotation: tilt * p * direction,
    opacity: 1,
    progress: p,
  };
}

/**
 * Normalized wipe rectangle for a clip mask. Returns { p, x, y, w, h } in 0..1 frame units.
 * `feather` is reported as-is; the renderer decides how to blur the edge.
 */
export function maskWipe(elapsed, options = {}) {
  const p = windowProgress(elapsed, options.start ?? 0, options.duration ?? 0.5);
  const direction = options.direction ?? 'ltr';
  const allowed = ['ltr', 'rtl', 'ttb', 'btt'];
  if (!allowed.includes(direction)) throw new RangeError(`direction must be one of ${allowed.join(', ')}`);
  const feather = nonNegative(options.feather ?? 0, 'feather');
  const rect = { p, x: 0, y: 0, w: 1, h: 1, feather };
  if (direction === 'ltr') rect.w = p;
  else if (direction === 'rtl') { rect.w = p; rect.x = 1 - p; }
  else if (direction === 'ttb') rect.h = p;
  else { rect.h = p; rect.y = 1 - p; }
  return rect;
}

/** Animated number for counters. Returns { p, value } rounded to `decimals`. */
export function dataCount(elapsed, options = {}) {
  const p = windowProgress(elapsed, options.start ?? 0, options.duration ?? 0.8);
  const from = finite(options.from ?? 0, 'from');
  const to = finite(options.to ?? 100, 'to');
  const decimals = options.decimals ?? 0;
  if (!Number.isInteger(decimals) || decimals < 0 || decimals > 6) {
    throw new RangeError('decimals must be an integer within 0..6');
  }
  const factor = Math.pow(10, decimals);
  return { p, value: Math.round((from + (to - from) * p) * factor) / factor };
}

/**
 * One card of a stack: index 0 is the front card. Returns { x, y, scale, rotation, opacity, progress }.
 * Positions are em / unitless and independent of the frame size.
 */
export function cardStackItem(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const stagger = nonNegative(options.stagger ?? 0.07, 'stagger');
  const enter = positive(options.enter ?? 0.45, 'enter');
  const spread = finite(options.spread ?? 0.18, 'spread');
  const tilt = finite(options.tilt ?? 3, 'tilt');
  const lift = nonNegative(options.lift ?? 0.06, 'lift');
  const p = clamp((t - i * stagger) / enter, 0, 1);
  const eased = easeOutCubic(p);
  return {
    x: spread * i * (1 - eased),
    y: -lift * i,
    scale: 1 - 0.05 * i,
    rotation: -tilt * i * (1 - eased),
    opacity: eased,
    progress: p,
  };
}

/** Camera push/pan. Returns { p, scale, x, y } — scale must stay positive. */
export function cameraPush(elapsed, options = {}) {
  const p = windowProgress(elapsed, options.start ?? 0, options.duration ?? 1.2);
  const fromScale = positive(options.fromScale ?? 1, 'fromScale');
  const toScale = positive(options.toScale ?? 1.08, 'toScale');
  const lerp = (a, b) => a + (b - a) * p;
  return {
    p,
    scale: lerp(fromScale, toScale),
    x: lerp(finite(options.fromX ?? 0, 'fromX'), finite(options.toX ?? 0, 'toX')),
    y: lerp(finite(options.fromY ?? 0, 'fromY'), finite(options.toY ?? 0, 'toY')),
  };
}

/**
 * One particle of a deterministic burst. Returns { x, y, opacity, size, angle } in em.
 * Positions use the same integer hash as the other effects — never Math.random.
 */
export function particleBurst(index, elapsed, options = {}) {
  const i = finite(index, 'index');
  if (!Number.isInteger(i) || i < 0) throw new RangeError('index must be a nonnegative integer');
  const t = nonNegative(elapsed, 'elapsed');
  const count = options.count ?? 24;
  if (!Number.isInteger(count) || count < 1) throw new RangeError('count must be a positive integer');
  const start = finite(options.start ?? 0, 'start');
  const duration = positive(options.duration ?? 0.7, 'duration');
  const speed = positive(options.speed ?? 2.4, 'speed');
  const gravity = finite(options.gravity ?? 1.6, 'gravity');
  const seed = options.seed ?? 7;
  if (!Number.isInteger(seed) || seed < 0) throw new RangeError('seed must be a nonnegative integer');
  const base = (2 * Math.PI * i) / count;
  const jitter = hash01(i * 31 + seed);
  const angle = base + (jitter - 0.5) * 0.9;
  const local = Math.max(0, t - start);
  const p = clamp(local / duration, 0, 1);
  const travel = speed * local * (0.7 + 0.6 * jitter);
  return {
    x: travel * Math.cos(angle),
    y: travel * Math.sin(angle) * 0.6 + 0.5 * gravity * local * local,
    opacity: 1 - p,
    size: 0.06 * (0.7 + 0.6 * jitter),
    angle,
  };
}
