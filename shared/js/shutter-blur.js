// Deterministic shutter-angle temporal motion blur for fast camera moves & one-take transitions.
// Pure function of `t`: no cross-frame state, so chunked rendering and `--replay` remain exact.

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v));
}

export function isInBlurWindow(t, windows) {
  if (!Array.isArray(windows)) return true;
  for (const w of windows) {
    const s = Array.isArray(w) ? w[0] : w?.start;
    const e = Array.isArray(w) ? w[1] : w?.end;
    if (Number.isFinite(s) && Number.isFinite(e) && t >= s && t <= e) return true;
  }
  return false;
}

export function shutterTimes(t, {
  fps = 30,
  shutter = 0.5,
  samples = 5,
  duration = Infinity,
  windows = null,
} = {}) {
  const n = Math.max(1, Math.floor(samples));
  const sh = clamp(Number(shutter) || 0, 0, 1);
  if (n <= 1 || sh <= 1e-4 || !isInBlurWindow(t, windows)) return [Math.max(0, t)];
  const span = sh / Math.max(1, fps);
  const out = [];
  for (let i = 0; i < n; i += 1) {
    const frac = (i / (n - 1)) - 0.5;
    out.push(clamp(t + frac * span, 0, Number.isFinite(duration) ? duration : Infinity));
  }
  return out;
}

function makeScratchCanvas(w, h, factory) {
  if (typeof factory === 'function') return factory(w, h);
  if (typeof OffscreenCanvas !== 'undefined') return new OffscreenCanvas(w, h);
  if (typeof document !== 'undefined') {
    const c = document.createElement('canvas');
    c.width = w;
    c.height = h;
    return c;
  }
  throw new Error('renderShutterBlur requires OffscreenCanvas, document, or a scratchFactory(w, h)');
}

/**
 * Render `drawFrame(subCtx, subT)` across sub-frame shutter timestamps and accumulate
 * equal-weight exposures onto `ctx` using incremental alpha (`1 / (i + 1)`).
 */
export function renderShutterBlur(ctx, t, drawFrame, {
  fps = 30,
  shutter = 0.5,
  samples = 5,
  duration = Infinity,
  windows = null,
  scratchFactory = null,
} = {}) {
  const times = shutterTimes(t, { fps, shutter, samples, duration, windows });
  if (times.length === 1) {
    drawFrame(ctx, times[0]);
    return 1;
  }
  const w = ctx.canvas.width;
  const h = ctx.canvas.height;
  const scratch = makeScratchCanvas(w, h, scratchFactory);
  const subCtx = scratch.getContext('2d');

  ctx.save();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, w, h);
  for (let i = 0; i < times.length; i += 1) {
    subCtx.setTransform(1, 0, 0, 1, 0, 0);
    subCtx.globalAlpha = 1;
    subCtx.clearRect(0, 0, w, h);
    drawFrame(subCtx, times[i]);
    // Incremental arithmetic mean: after step i, every frame 0..i has weight 1/(i+1).
    ctx.globalAlpha = 1 / (i + 1);
    ctx.drawImage(scratch, 0, 0);
  }
  ctx.restore();
  return times.length;
}
