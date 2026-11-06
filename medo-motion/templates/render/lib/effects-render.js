// Canvas2D raster adapters for deterministic visual effects (Engine K).
import { lightSweep, whipPan, particleDissolve } from './effects.js';

/**
 * Composite a soft diagonal highlight into the current Canvas2D frame.
 * Call after drawing the content that should receive the sweep.
 */
export function drawLightSweep(ctx, t, width, height, options = {}) {
  if (!ctx || typeof ctx.save !== 'function') {
    throw new TypeError('drawLightSweep requires a Canvas2D context');
  }
  if (!(width > 0) || !(height > 0)) {
    throw new RangeError('light sweep dimensions must be positive');
  }
  const state = lightSweep(t, options.start ?? 0, options.duration ?? 0.72,
    options.width ?? 0.18, options.angle ?? -0.22, options.intensity ?? 0.72);
  if (state.alpha <= 0) return state;

  const bandWidth = Math.max(1, state.width * width);
  const extent = Math.hypot(width, height) * 1.5;
  ctx.save();
  ctx.translate(state.center_x * width, height / 2);
  ctx.rotate(state.angle);
  const gradient = ctx.createLinearGradient(-bandWidth / 2, 0, bandWidth / 2, 0);
  gradient.addColorStop(0, 'rgba(255,255,255,0)');
  gradient.addColorStop(0.28, 'rgba(255,255,255,0.10)');
  gradient.addColorStop(0.5, 'rgba(255,255,255,0.82)');
  gradient.addColorStop(0.72, 'rgba(255,255,255,0.10)');
  gradient.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.globalAlpha *= state.alpha;
  ctx.fillStyle = gradient;
  ctx.fillRect(-bandWidth / 2, -extent / 2, bandWidth, extent);
  ctx.restore();
  return state;
}


/**
 * Draw a scene through a deterministic whip-pan camera transform.
 * drawFrame receives the transformed context and should paint the full scene.
 */
export function drawWhipPan(ctx, t, width, height, drawFrame, options = {}) {
  if (!ctx || typeof ctx.save !== 'function' || typeof drawFrame !== 'function') {
    throw new TypeError('drawWhipPan requires a Canvas2D context and draw callback');
  }
  if (!(width > 0) || !(height > 0)) {
    throw new RangeError('drawWhipPan dimensions must be positive');
  }
  const state = whipPan(t, options.start ?? 0, options.duration ?? 0.42,
    options.direction ?? 1, options.distance ?? 1.15,
    options.shutter ?? 0.055, options.maxBlur ?? 0.16);
  const blur = Math.min(width * 0.08, state.blur_distance * width * 0.25);
  ctx.save();
  ctx.beginPath();
  ctx.rect(0, 0, width, height);
  ctx.clip();
  ctx.translate(state.offset_x * width, 0);
  if ('filter' in ctx) ctx.filter = blur > 0 ? `blur(${blur}px)` : 'none';
  drawFrame(ctx);
  ctx.restore();
  return state;
}


/**
 * Render a source frame as deterministic, fading sampled-color particles.
 * sourceCtx must expose the unmodified source pixels; ctx is the output context.
 * The destination is cleared before drawing, so use a separate source canvas/context.
 */
export function drawParticleDissolve(ctx, sourceCtx, t, width, height, options = {}) {
  if (!ctx || typeof ctx.save !== 'function' ||
      !sourceCtx || typeof sourceCtx.getImageData !== 'function') {
    throw new TypeError('drawParticleDissolve requires output and readable source Canvas2D contexts');
  }
  if (!(width > 0) || !(height > 0)) {
    throw new RangeError('drawParticleDissolve dimensions must be positive');
  }
  const state = particleDissolve(t, options.start ?? 0, options.duration ?? 0.72,
    options.count ?? 96, options.seed ?? 18);
  const source = sourceCtx.getImageData(0, 0, width, height);
  ctx.save();
  ctx.clearRect(0, 0, width, height);
  if (Array.isArray(options.background)) {
    const [r, g, b] = options.background;
    ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
    ctx.fillRect(0, 0, width, height);
  }
  for (const particle of state.particles) {
    const alpha = Math.max(0, Math.min(1, particle.alpha));
    if (alpha <= 0) continue;
    const sx = Math.max(0, Math.min(width - 1, Math.floor(particle.x * width)));
    const sy = Math.max(0, Math.min(height - 1, Math.floor(particle.y * height)));
    const offset = (sy * width + sx) * 4;
    const a = source.data[offset + 3] / 255 * alpha;
    if (a <= 0) continue;
    ctx.globalAlpha = a;
    ctx.fillStyle = `rgb(${source.data[offset]}, ${source.data[offset + 1]}, ${source.data[offset + 2]})`;
    ctx.beginPath();
    ctx.arc(particle.x * width, particle.y * height,
      Math.max(1, particle.radius * width), 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
  return state;
}
