// Canvas2D raster adapters for deterministic visual effects (Engine K).
import { lightSweep } from './effects.js';

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
