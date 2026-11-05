// Engine K adapter for Phase 2C One-Take: cached Canvas2D element faces + shared pure state.
import { drawDirectedText } from './captions.js';
import { protectBox, withLayout } from './layout.js';
import { normalizeOneTake, oneTakeStateAt } from './one-take.js';
import { brandHex } from './stage.js';

function paintShape(ctx, element) {
  const { w, h } = element;
  ctx.fillStyle = brandHex(element.role);
  ctx.strokeStyle = brandHex(element.strokeRole);
  ctx.lineWidth = element.strokeWidth;
  ctx.beginPath();
  if (element.kind === 'circle') ctx.ellipse(w / 2, h / 2, w / 2, h / 2, 0, 0, Math.PI * 2);
  else ctx.roundRect(0, 0, w, h, Math.min(element.radius, w / 2, h / 2));
  ctx.fill();
  if (element.strokeWidth > 0) ctx.stroke();
}

function drawPointer(ctx, state, cursorSpec) {
  const cursor = state.cursor;
  if (!cursor || cursorSpec.opacity <= 0) return;
  const size = cursorSpec.size;
  if (cursor.click) {
    const click = cursor.click;
    const radius = size * (0.6 + 2 * (1 - (1 - click.progress) ** 3)) * state.camera.zoom;
    ctx.save();
    ctx.globalAlpha = click.opacity * cursorSpec.opacity;
    ctx.strokeStyle = brandHex('red');
    ctx.lineWidth = Math.max(2, size / 8);
    ctx.beginPath();
    ctx.arc(click.screen.x, click.screen.y, radius, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
  const scale = state.camera.zoom * (cursor.press ? 0.86 : 1);
  ctx.save();
  ctx.globalAlpha = cursorSpec.opacity;
  ctx.translate(cursor.screen.x, cursor.screen.y);
  ctx.scale(scale, scale);
  ctx.fillStyle = brandHex('paper');
  ctx.strokeStyle = brandHex('ink');
  ctx.lineWidth = Math.max(1.5, size / 18);
  ctx.lineJoin = 'round';
  ctx.beginPath();
  ctx.moveTo(0, 0);
  ctx.lineTo(0, size * 1.08);
  ctx.lineTo(size * 0.30, size * 0.80);
  ctx.lineTo(size * 0.48, size * 1.20);
  ctx.lineTo(size * 0.64, size * 1.12);
  ctx.lineTo(size * 0.47, size * 0.70);
  ctx.lineTo(size * 0.76, size * 0.68);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

/** `direction` is required only when text elements exist. Call close() through scene resources. */
export function createOneTake(input, { direction = null } = {}) {
  const spec = normalizeOneTake(input);
  const sprites = new Map();
  spec.elements.forEach((element) => {
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.ceil(element.w));
    canvas.height = Math.max(1, Math.ceil(element.h));
    const ctx = canvas.getContext('2d', { alpha: true });
    if (!ctx) throw new Error(`element ${element.id}: Canvas2D context unavailable`);
    if (element.kind === 'text') {
      if (!direction) throw new Error(`element ${element.id}: directed text requires a direction plan`);
      drawDirectedText(ctx, element.text, {
        direction, scene: element.scene, role: element.fontRole, elementId: element.id,
        time: 1, start: 0, end: 1, x: canvas.width / 2, y: canvas.height / 2,
        size: Math.round(element.fontSize), maxWidth: canvas.width * 0.92,
        color: brandHex(element.role), accent: brandHex(element.accentRole),
        theme: ['ink', 'ink_soft'].includes(element.role) ? 'light' : 'dark', rtl: element.rtl,
      });
    } else paintShape(ctx, element);
    sprites.set(element.id, canvas);
  });

  function stateAt(time, { motionMode = 'normal', viewport = null } = {}) {
    return oneTakeStateAt(spec, time, { motionMode, viewport });
  }

  function draw(ctx, time, { motionMode = 'normal', viewport = null } = {}) {
    const state = stateAt(time, { motionMode, viewport });
    const { w: W, h: H } = spec.canvas;
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = brandHex(spec.backgroundRole);
    ctx.fillRect(0, 0, W, H);
    const win = state.viewport;
    ctx.beginPath();
    if (win.r > 0) ctx.roundRect(win.x, win.y, win.w, win.h, win.r);
    else ctx.rect(win.x, win.y, win.w, win.h);
    ctx.clip();
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    state.elements.forEach((element) => {
      const sprite = sprites.get(element.id);
      ctx.save();
      ctx.globalAlpha = element.opacity;
      ctx.translate(element.screen.x, element.screen.y);
      ctx.rotate(element.screen.rotation * Math.PI / 180);
      ctx.scale(element.screen.scale, element.screen.scale);
      ctx.drawImage(sprite, -sprite.width / 2, -sprite.height / 2);
      ctx.restore();
      if (element.kind === 'text' && element.opacity > 0.01) {
        const box = element.aabb;
        const x0 = Math.max(box.x, win.x), y0 = Math.max(box.y, win.y);
        const x1 = Math.min(box.x + box.w, win.x + win.w), y1 = Math.min(box.y + box.h, win.y + win.h);
        if (x1 - x0 > 1 && y1 - y0 > 1) {
          ctx.save();
          ctx.globalAlpha = element.opacity;
          const clipped = { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
          withLayout(ctx, { id: element.id, zone: 'content' }, () => protectBox(ctx, element.id, clipped, 'text'));
          ctx.restore();
        }
      }
    });
    drawPointer(ctx, state, spec.cursor);
    ctx.restore();
    return state;
  }

  function close() {
    sprites.forEach((canvas) => { canvas.width = 1; canvas.height = 1; });
    sprites.clear();
  }
  return { spec, sprites, stateAt, draw, close };
}
