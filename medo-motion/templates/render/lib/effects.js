// Deterministic, frame-addressable effect states for engine K.
// The matching Python implementation lives in procedural-reels/effects.py.
import { clamp, ease, progress } from './motion.js';

/** Normalized diagonal highlight-band state; the renderer paints the returned band. */
export function lightSweep(t, start = 0, duration = 0.72, width = 0.18, angle = -0.22, intensity = 0.72) {
  const p = progress(t, start, duration);
  const travel = ease('smoothstep', p);
  return {
    progress: p,
    center_x: -width + (1 + 2 * width) * travel,
    width,
    angle,
    alpha: intensity * Math.sin(Math.PI * p),
  };
}

/** Normalized pan offset, analytic velocity, and bounded blur distance. */
export function whipPan(t, start = 0, duration = 0.42, direction = 1, distance = 1.15,
                        shutter = 0.055, maxBlur = 0.16) {
  const p = progress(t, start, duration);
  const eased = ease('smoothstep', p);
  const safeDuration = Math.max(Number(duration), 1e-9);
  const velocity_x = -direction * distance * (6 * p * (1 - p)) / safeDuration;
  const blur_distance = Math.min(Math.abs(velocity_x) * shutter, maxBlur);
  return {
    progress: p,
    offset_x: direction * distance * (1 - eased),
    velocity_x,
    blur_distance,
  };
}

/** 32-bit integer hash shared with Python; no Math.random or mutable RNG state. */
function hash01(value) {
  return ((Math.imul(value, 1664525) + 1013904223) >>> 0) / 4294967296;
}

/** Stable normalized particle field whose opacity decays over the dissolve. */
export function particleDissolve(t, start = 0, duration = 0.72, count = 96, seed = 18) {
  const p = progress(t, start, duration);
  const total = Math.max(1, Math.min(256, Math.floor(count)));
  const particles = [];
  for (let i = 0; i < total; i++) {
    const key = Math.trunc(seed) * 1024 + i * 4;
    const x = hash01(key + 1);
    const y = hash01(key + 2);
    const radius = 0.004 + hash01(key + 3) * 0.006;
    const delay = hash01(key) * 0.35;
    const local = clamp((p - delay) / (1 - delay));
    const faded = ease('smoothstep', local);
    particles.push({
      x: x + (x - 0.5) * 0.08 * faded,
      y: y + (y - 0.5) * 0.08 * faded,
      radius: radius * (1 + 0.4 * faded),
      alpha: 1 - faded,
    });
  }
  return { progress: p, particles };
}
