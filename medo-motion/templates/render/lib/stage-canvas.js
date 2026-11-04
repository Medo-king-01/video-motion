// Engine K Canvas2D adapter for Fixed Stage (`UNDER` -> `CONTENT` clipped to `win(t)` -> `OVER` unclipped).
// Reuses `stage.js`, `backgrounds.js`, `captions.js`, and `layout.js` with zero duplicate abstractions.

import { backgroundFrame } from './backgrounds.js';
import { drawDirectedText, drawPhraseCaption } from './captions.js';
import { fontFor } from './text-direction.js';
import { setStageWindow, withStageLayer } from './layout.js';
import { brandHex, clampRadius, normalizeStageSpec, stageStateAt } from './stage.js';

function withAlphaHex(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

export function drawStageUnder(ctx, normSpec, state, { motionMode = 'normal' } = {}) {
  const { w, h } = normSpec.canvas;
  const under = normSpec.under;
  const ambT = motionMode === 'reduced' ? 0 : state.time;

  ctx.save();
  if (under.background) {
    backgroundFrame(ctx, w, h, ambT, under.background);
  } else {
    ctx.fillStyle = brandHex(under.surfaceRole);
    ctx.fillRect(0, 0, w, h);
  }

  const fr = under.frame;
  if (fr.enabled && fr.matAlpha > 0 && state.chromeOpacity > 0) {
    const wb = state.win;
    ctx.fillStyle = withAlphaHex(brandHex(fr.matRole), fr.matAlpha * state.chromeOpacity);
    ctx.beginPath();
    const r = clampRadius(wb.r + 4, wb.w + 16, wb.h + 16);
    if (r > 0) {
      ctx.roundRect(wb.x - 8, wb.y + 10, wb.w + 16, wb.h + 4, r);
    } else {
      ctx.rect(wb.x - 8, wb.y + 10, wb.w + 16, wb.h + 4);
    }
    ctx.fill();
  }
  ctx.restore();
}

export function drawStageWindowFrame(ctx, normSpec, state) {
  const fr = normSpec.under.frame;
  if (!fr.enabled || fr.strokeWidth <= 0 || state.chromeOpacity <= 0.005 || state.isFullscreen) {
    return;
  }
  const wb = state.win;
  const r = clampRadius(wb.r, wb.w, wb.h);
  ctx.save();
  ctx.globalAlpha *= state.chromeOpacity;
  ctx.strokeStyle = brandHex(fr.strokeRole);
  ctx.lineWidth = fr.strokeWidth;
  ctx.beginPath();
  if (r > 0) {
    ctx.roundRect(wb.x, wb.y, wb.w, wb.h, r);
  } else {
    ctx.rect(wb.x, wb.y, wb.w, wb.h);
  }
  ctx.stroke();
  ctx.restore();
}

export function drawStageHeader(ctx, normSpec, state, { direction = null, copyById = null } = {}) {
  const slot = state.activeHeader;
  if (!slot) return null;
  if (!copyById || typeof copyById[slot.copyId] !== 'string' || !copyById[slot.copyId].trim()) {
    throw new Error(`Header slot "${slot.id}" missing non-empty copyId "${slot.copyId}" in copyById`);
  }
  if (!direction) {
    throw new Error(`Header slot "${slot.id}" requires plan/text-direction.json`);
  }
  const text = copyById[slot.copyId];

  if (slot.pillRole) {
    const fontMeta = fontFor(direction, slot.scene, slot.role, slot.copyId);
    const lines = String(text).split('\n').filter(Boolean);
    ctx.save();
    ctx.font = `${fontMeta.weight} ${slot.size}px "${fontMeta.family}", sans-serif`;
    const maxTw = lines.reduce((acc, ln) => Math.max(acc, ctx.measureText(ln).width), 80);
    const pillW = Math.min(slot.maxWidth + 56, maxTw + 68);
    const pillH = lines.length * slot.size * 1.35 + 28;
    const px = slot.x - pillW / 2;
    const py = slot.y - pillH / 2;
    ctx.globalAlpha *= slot.pillAlpha;
    ctx.fillStyle = brandHex(slot.pillRole);
    ctx.beginPath();
    ctx.roundRect(px, py, pillW, pillH, pillH / 2);
    ctx.fill();
    if (slot.pillBorderRole) {
      ctx.strokeStyle = brandHex(slot.pillBorderRole);
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    ctx.restore();
  }

  drawDirectedText(ctx, text, {
    direction,
    scene: slot.scene,
    role: slot.role,
    elementId: slot.copyId,
    time: state.time,
    start: slot.start,
    end: slot.end,
    x: slot.x,
    y: slot.y,
    size: slot.size,
    maxWidth: slot.maxWidth,
    color: brandHex(slot.colorRole),
    accent: brandHex(slot.accentRole),
    theme: normSpec.theme,
    shadow: 'transparent',
    zone: 'hud',
  });
  return slot;
}

export function drawStageProgress(ctx, normSpec, progress) {
  const pb = normSpec.over.progressBar;
  if (!pb.enabled) return;
  const w = normSpec.canvas.w;
  const x0 = pb.marginX;
  const span = w - pb.marginX * 2;
  ctx.save();
  ctx.fillStyle = withAlphaHex(brandHex(pb.trackRole), pb.trackAlpha);
  ctx.fillRect(x0, pb.y, span, pb.height);
  const p = Math.max(0, Math.min(1, Number(progress) || 0));
  if (p > 0) {
    ctx.fillStyle = brandHex(pb.fillRole);
    ctx.fillRect(x0, pb.y, span * p, pb.height);
  }
  ctx.restore();
}

export async function renderFixedStage(ctx, spec, time, {
  drawContent,
  drawOver = null,
  drawUnder = null,
  duration = null,
  direction = null,
  copyById = null,
  words = null,
  captionStyle = null,
  motionMode = 'normal',
} = {}) {
  if (typeof drawContent !== 'function') {
    throw new Error('renderFixedStage requires a drawContent(ctx, state) callback');
  }
  const norm = spec && spec._normalized === true ? spec : normalizeStageSpec(spec);
  const state = stageStateAt(norm, time, { duration });
  const wb = state.win;
  setStageWindow(ctx, wb);

  if (state.isFullscreen) {
    await withStageLayer(ctx, 'content', wb, async () => {
      ctx.save();
      try {
        await drawContent(ctx, state);
      } finally {
        ctx.restore();
      }
    });
  } else {
    await withStageLayer(ctx, 'under', wb, async () => {
      drawStageUnder(ctx, norm, state, { motionMode });
      if (typeof drawUnder === 'function') {
        await drawUnder(ctx, state);
      }
    });

    await withStageLayer(ctx, 'content', wb, async () => {
      const r = clampRadius(wb.r, wb.w, wb.h);
      ctx.save();
      try {
        ctx.beginPath();
        if (r > 0) {
          ctx.roundRect(wb.x, wb.y, wb.w, wb.h, r);
        } else {
          ctx.rect(wb.x, wb.y, wb.w, wb.h);
        }
        ctx.clip();
        await drawContent(ctx, state);
      } finally {
        ctx.restore();
      }
    });

    drawStageWindowFrame(ctx, norm, state);
  }

  await withStageLayer(ctx, 'over', wb, async () => {
    drawStageHeader(ctx, norm, state, { direction, copyById });
    if (Array.isArray(words) && words.length > 0 && captionStyle && norm.over.captions.enabled) {
      drawPhraseCaption(ctx, state.time, words, {
        W: norm.canvas.w,
        H: norm.canvas.h,
        y: norm.over.captions.y,
        style: captionStyle,
        color: brandHex(norm.theme === 'dark' ? 'paper' : 'ink'),
        accent: brandHex(norm.theme === 'dark' ? 'salmon' : 'red'),
        theme: norm.theme,
      });
    }
    if (duration !== null && duration !== undefined) {
      drawStageProgress(ctx, norm, state.progress);
    }
    if (typeof drawOver === 'function') {
      await drawOver(ctx, state);
    }
  });

  return state;
}
