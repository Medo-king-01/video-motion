// Canvas2D adapters for the element moves in moves.js (engine K).
// They own no timing: every number comes from the pure move functions, so a fake
// context in tests can pin the exact transforms without a browser.
import {
  pixelListItem, parallaxLayer, orbitItem, wordPathItem, explodePart,
  maskWipe, dataCount, cardStackItem, cameraPush, particleBurst,
} from './moves.js';

const requireCtx = (ctx, name) => {
  if (!ctx || typeof ctx.save !== 'function' || typeof ctx.restore !== 'function'
      || typeof ctx.translate !== 'function') {
    throw new TypeError(`${name} requires a Canvas2D context`);
  }
};

const requireDraw = (draw, name) => {
  if (typeof draw !== 'function') throw new TypeError(`${name} requires a draw callback`);
};

/**
 * Draw staggered list rows. `drawItem(ctx, item, state, index)` paints one row in local
 * coordinates (0,0 = that row's anchor); the adapter handles opacity and the pixel-snapped
 * offset. Returns the sampled states so a scene can log or test them.
 */
export function drawPixelList(ctx, items, t, options = {}, drawItem) {
  requireCtx(ctx, 'drawPixelList');
  requireDraw(drawItem, 'drawPixelList');
  if (!Array.isArray(items)) throw new TypeError('drawPixelList requires an array of items');
  const fontSize = options.fontSize ?? 64;
  const lineHeight = options.lineHeight ?? 1.35;
  const x = options.x ?? 0;
  const y = options.y ?? 0;
  const states = [];
  for (let i = 0; i < items.length; i++) {
    const state = pixelListItem(i, t, {
      stagger: options.stagger, enter: options.enter, rise: options.rise,
      from: options.from, fontSize,
    });
    states.push(state);
    ctx.save();
    ctx.globalAlpha = (ctx.globalAlpha ?? 1) * state.opacity;
    ctx.translate(x + state.x * fontSize, y + i * lineHeight * fontSize + state.y * fontSize);
    drawItem(ctx, items[i], state, i);
    ctx.restore();
  }
  return states;
}

/**
 * Draw layers with a shared camera progress. Scaling happens around the frame centre so a
 * foreground layer does not slide off the origin. Returns the sampled layer states.
 */
export function drawParallax(ctx, layers, progress, options = {}, drawLayer) {
  requireCtx(ctx, 'drawParallax');
  requireDraw(drawLayer, 'drawParallax');
  if (!Array.isArray(layers)) throw new TypeError('drawParallax requires an array of layers');
  const unit = options.unit ?? 40;
  const cx = (options.width ?? 1080) / 2;
  const cy = (options.height ?? 1920) / 2;
  const states = [];
  for (let i = 0; i < layers.length; i++) {
    const layer = layers[i];
    const state = parallaxLayer(layer?.depth ?? 0, progress, {
      panX: options.panX, panY: options.panY, zoom: options.zoom,
    });
    states.push(state);
    ctx.save();
    ctx.translate(-state.x * unit, -state.y * unit);
    if (state.scale !== 1) {
      ctx.translate(cx, cy);
      ctx.scale(state.scale, state.scale);
      ctx.translate(-cx, -cy);
    }
    drawLayer(ctx, layer, state, i);
    ctx.restore();
  }
  return states;
}

const requireRotate = (ctx, name) => {
  if (typeof ctx.rotate !== 'function') throw new TypeError(`${name} requires ctx.rotate()`);
};

/** Draw items around an ellipse. Local coordinates: (0,0) is the item centre. */
export function drawOrbit(ctx, items, t, options = {}, drawItem) {
  requireCtx(ctx, 'drawOrbit');
  requireDraw(drawItem, 'drawOrbit');
  if (!Array.isArray(items)) throw new TypeError('drawOrbit requires an array of items');
  const unit = options.unit ?? 40;
  const cx = options.x ?? 0;
  const cy = options.y ?? 0;
  const states = [];
  for (let i = 0; i < items.length; i++) {
    const state = orbitItem(i, t, { ...options, count: options.count ?? items.length });
    states.push(state);
    ctx.save();
    ctx.translate(cx + state.x * unit, cy + state.y * unit);
    ctx.scale(state.scale, state.scale);
    drawItem(ctx, items[i], state, i);
    ctx.restore();
  }
  return states.sort((a, b) => a.depth - b.depth).map(state => state.angle);
}

/** Draw words travelling a straight path; `drawWord` paints one word at local (0,0). */
export function drawWordPath(ctx, words, t, options = {}, drawWord) {
  requireCtx(ctx, 'drawWordPath');
  requireDraw(drawWord, 'drawWordPath');
  requireRotate(ctx, 'drawWordPath');
  if (!Array.isArray(words)) throw new TypeError('drawWordPath requires an array of words');
  const unit = options.unit ?? 40;
  const cx = options.x ?? 0;
  const cy = options.y ?? 0;
  const states = [];
  for (let i = 0; i < words.length; i++) {
    const state = wordPathItem(i, t, options);
    states.push(state);
    ctx.save();
    ctx.globalAlpha = (ctx.globalAlpha ?? 1) * state.opacity;
    ctx.translate(cx + state.x * unit, cy + state.y * unit);
    ctx.rotate((state.rotation * Math.PI) / 180);
    drawWord(ctx, words[i], state, i);
    ctx.restore();
  }
  return states;
}

/** Draw exploded parts radially; `drawPart` paints one part at local (0,0). */
export function drawExplode(ctx, parts, t, options = {}, drawPart) {
  requireCtx(ctx, 'drawExplode');
  requireDraw(drawPart, 'drawExplode');
  requireRotate(ctx, 'drawExplode');
  if (!Array.isArray(parts)) throw new TypeError('drawExplode requires an array of parts');
  const unit = options.unit ?? 40;
  const cx = options.x ?? 0;
  const cy = options.y ?? 0;
  const states = [];
  for (let i = 0; i < parts.length; i++) {
    const state = explodePart(i, t, { ...options, count: options.count ?? parts.length });
    states.push(state);
    ctx.save();
    ctx.translate(cx + state.x * unit, cy + state.y * unit);
    ctx.rotate((state.rotation * Math.PI) / 180);
    drawPart(ctx, parts[i], state, i);
    ctx.restore();
  }
  return states;
}

/** Clip to the animated wipe rectangle and draw inside it. Returns the rect state. */
export function drawMaskWipe(ctx, elapsed, options = {}, drawContent) {
  requireCtx(ctx, 'drawMaskWipe');
  requireDraw(drawContent, 'drawMaskWipe');
  if (typeof ctx.beginPath !== 'function' || typeof ctx.rect !== 'function'
      || typeof ctx.clip !== 'function') {
    throw new TypeError('drawMaskWipe requires ctx.beginPath(), ctx.rect() and ctx.clip()');
  }
  const width = options.width ?? 1080;
  const height = options.height ?? 1920;
  if (!(width > 0) || !(height > 0)) throw new RangeError('drawMaskWipe dimensions must be positive');
  const state = maskWipe(elapsed, options);
  ctx.save();
  ctx.beginPath();
  ctx.rect(state.x * width, state.y * height, state.w * width, state.h * height);
  ctx.clip();
  drawContent(ctx, state);
  ctx.restore();
  return state;
}

/** Draw the stack front-to-back; index 0 is the front card. */
export function drawCardStack(ctx, cards, t, options = {}, drawCard) {
  requireCtx(ctx, 'drawCardStack');
  requireDraw(drawCard, 'drawCardStack');
  requireRotate(ctx, 'drawCardStack');
  if (!Array.isArray(cards)) throw new TypeError('drawCardStack requires an array of cards');
  const unit = options.unit ?? 40;
  const cx = options.x ?? 0;
  const cy = options.y ?? 0;
  const states = [];
  for (let i = cards.length - 1; i >= 0; i--) {
    const state = cardStackItem(i, t, options);
    states[i] = state;
    ctx.save();
    ctx.globalAlpha = (ctx.globalAlpha ?? 1) * state.opacity;
    ctx.translate(cx + state.x * unit, cy + state.y * unit);
    ctx.rotate((state.rotation * Math.PI) / 180);
    ctx.scale(state.scale, state.scale);
    drawCard(ctx, cards[i], state, i);
    ctx.restore();
  }
  return states;
}

/** Apply a camera push around the frame centre and draw the scene. */
export function drawCameraPush(ctx, elapsed, options = {}, drawFrame) {
  requireCtx(ctx, 'drawCameraPush');
  requireDraw(drawFrame, 'drawCameraPush');
  const width = options.width ?? 1080;
  const height = options.height ?? 1920;
  const state = cameraPush(elapsed, options);
  ctx.save();
  ctx.translate(width / 2 + state.x, height / 2 + state.y);
  ctx.scale(state.scale, state.scale);
  ctx.translate(-width / 2, -height / 2);
  drawFrame(ctx, state);
  ctx.restore();
  return state;
}

/** Draw a deterministic particle burst; `drawParticle` paints one particle at local (0,0). */
export function drawParticleBurst(ctx, t, options = {}, drawParticle) {
  requireCtx(ctx, 'drawParticleBurst');
  requireDraw(drawParticle, 'drawParticleBurst');
  const unit = options.unit ?? 40;
  const cx = options.x ?? 0;
  const cy = options.y ?? 0;
  const count = options.count ?? 24;
  if (!Number.isInteger(count) || count < 1) throw new RangeError('count must be a positive integer');
  const states = [];
  for (let i = 0; i < count; i++) {
    const state = particleBurst(i, t, { ...options, count });
    states.push(state);
    ctx.save();
    ctx.globalAlpha = (ctx.globalAlpha ?? 1) * state.opacity;
    ctx.translate(cx + state.x * unit, cy + state.y * unit);
    ctx.scale(state.size / 0.06, state.size / 0.06);
    drawParticle(ctx, state, i);
    ctx.restore();
  }
  return states;
}

/** Sample a counter and hand the value to `drawValue`; the counter draws no pixels itself. */
export function drawDataCount(ctx, elapsed, options = {}, drawValue) {
  if (!ctx || typeof ctx !== 'object') throw new TypeError('drawDataCount requires a context');
  requireDraw(drawValue, 'drawDataCount');
  const state = dataCount(elapsed, options);
  drawValue(ctx, state);
  return state;
}
