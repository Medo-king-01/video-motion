// Transitions for engine K — identical geometry to engine P (templates/procedural-reels/transition.py).
//
// A transition is a pure function of progress: `transitionLayer('wipe', p)` returns the mask for that
// instant and `compositeTransition(...)` applies it between two pre-rendered layers. No CSS animation,
// no timing state — a 0.5 s transition is just 15 deterministic frames.
//
// Geometry is normalised (x/w of frame width, y/h of frame height, circle radius of width), so
// medo-motion/motion/transitions.json is the single description of what both engines draw.
// Kinds/names are inspired by the MIT gl-transitions collection (gl-transitions.com).
import { ease, clamp } from './motion.js';

// Embedded copy so a project (which only receives templates/) behaves identically.
// tests/test_transitions.py fails if this drifts from medo-motion/motion/transitions.json.
export const TRANSITIONS = {
  wipe: { kind: 'reveal', ease: 'easeInOut', sfx: 'whoosh', params: { dir: 'right' } },
  wipeUp: { kind: 'reveal', ease: 'easeInOut', sfx: 'whoosh', params: { dir: 'up' } },
  diagonal: { kind: 'reveal', ease: 'easeInOut', sfx: 'swipe', params: { dir: 'diagonal', cols: 12 } },
  iris: { kind: 'circle', ease: 'backOut', sfx: 'pop', params: {} },
  irisClose: { kind: 'circle', ease: 'easeInOut', sfx: 'whoosh', params: { mode: 'close' } },
  slide: { kind: 'slide', ease: 'easeInOut', sfx: 'swipe', params: { push: true } },
  cover: { kind: 'slide', ease: 'expoOut', sfx: 'swipe', params: { push: false } },
  blinds: { kind: 'blinds', ease: 'easeInOut', sfx: 'tick', params: { bars: 8 } },
  checker: { kind: 'checker', ease: 'easeInOut', sfx: 'pop', params: { cols: 6, rows: 10 } },
  bands: { kind: 'bands', ease: 'easeInOut', sfx: 'whoosh', params: { bands: 6 } },
  dissolve: { kind: 'fade', ease: 'linear', sfx: 'noise', params: {} },
  zoom: { kind: 'zoom', ease: 'expoOut', sfx: 'whoosh', params: {} },
  glitch: { kind: 'slices', ease: 'linear', sfx: 'glitch', params: { slices: 12 } },
  flash: { kind: 'flash', ease: 'easeInOut', sfx: 'impact', params: {} },
};
export const TRANSITION_NAMES = Object.keys(TRANSITIONS);
export const PAPER = '#F3F2F1';

/** Deterministic 0..1 hash — identical to hash01() in transition.py. */
export const hash01 = i => ((i * 1103515245 + 12345) % 2147483647) / 2147483647;

export function transitionLayer(name, p) {
  const spec = TRANSITIONS[name] || TRANSITIONS.wipe;
  const e = ease(spec.ease || 'easeInOut', clamp(p));
  const prm = spec.params || {};
  const out = { name, p: e, rects: [], circles: [], alpha: 1, scaleB: 1, aDx: 0, aDy: 0, invert: false, paperFlash: 0,
    // a masked transition with an empty mask means "nothing revealed yet", not "blend all"
    masked: ['reveal', 'circle', 'slide', 'blinds', 'checker', 'bands', 'slices'].includes(spec.kind) };
  const rect = (x, y, w, h, dx = 0, dy = 0) => ({ x, y, w, h, dx, dy });
  switch (spec.kind) {
    case 'reveal': {
      if (prm.dir === 'up') out.rects.push(rect(0, 1 - e, 1, e));
      else if (prm.dir === 'diagonal') {
        const cols = prm.cols ?? 12;
        for (let i = 0; i < cols; i++) {
          const h = clamp(e * 1.5 - (i / cols) * 0.5);
          if (h > 0) out.rects.push(rect(i / cols, 0, 1 / cols, h));
        }
      } else out.rects.push(rect(0, 0, e, 1));
      break;
    }
    case 'circle':
      out.circles.push({ cx: 0.5, cy: 0.5, r: e * 1.7, dx: 0, dy: 0 });
      out.invert = prm.mode === 'close';
      break;
    case 'slide':
      // the incoming frame only exists where it has arrived; the rest keeps the outgoing frame
      out.rects.push(rect(1 - e, 0, e, 1, 1 - e));
      out.aDx = prm.push === false ? 0 : -e;
      break;
    case 'blinds': {
      // vertical slats opening from alternating top/bottom edges (bands is the horizontal cousin)
      const bars = prm.bars ?? 8, wid = 1 / bars;
      for (let i = 0; i < bars; i++) {
        const start = (i / bars) * 0.35, hh = clamp((e - start) / (1 - start));
        if (hh > 0) out.rects.push(rect(i * wid, i % 2 === 0 ? 0 : 1 - hh, wid, hh));
      }
      break;
    }
    case 'checker': {
      const cols = prm.cols ?? 6, rows = prm.rows ?? 10;
      for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
        const delay = (i / cols) * 0.5 + (j / rows) * 0.5;
        const u = clamp((e - delay * 0.8) / 0.2);
        if (u > 0) out.rects.push(rect(i / cols, j / rows, u / cols, 1 / rows));
      }
      break;
    }
    case 'bands': {
      const bands = prm.bands ?? 6, hgt = 1 / bands;
      for (let i = 0; i < bands; i++) {
        const w = clamp((e - i * 0.05) / 0.7);
        if (w > 0) out.rects.push(rect(i % 2 === 0 ? 0 : 1 - w, i * hgt, w, hgt));
      }
      break;
    }
    case 'fade':
      out.alpha = e;
      break;
    case 'zoom':
      out.alpha = e;
      out.scaleB = 1.12 - 0.12 * e;
      break;
    case 'slices': {
      const n = prm.slices ?? 12, hgt = 1 / n;
      for (let i = 0; i < n; i++) {
        if (e * 1.15 > hash01(i) * 0.9) {
          const jitter = (hash01(i + 977) - 0.5) * 0.22 * (1 - e);
          out.rects.push(rect(0, i * hgt, 1, hgt, jitter));
        }
      }
      break;
    }
    case 'flash':
      out.alpha = e > 0.5 ? 1 : 0;
      out.paperFlash = Math.sin(Math.PI * e) * 0.85;
      break;
    default:
      break;
  }
  return out;
}

/** Offscreen layer at full resolution (transitions must not alias). */
export function makeLayer(W, H, draw) {
  const canvas = document.createElement('canvas');
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  draw(ctx);
  return canvas;
}

function drawScaled(ctx, img, W, H, scale) {
  if (scale === 1) { ctx.drawImage(img, 0, 0); return; }
  ctx.save();
  ctx.translate(W / 2, H / 2); ctx.scale(scale, scale); ctx.translate(-W / 2, -H / 2);
  ctx.drawImage(img, 0, 0);
  ctx.restore();
}

/** Draw `a` transitioned into `b` (both canvases) onto ctx at progress p. */
export function compositeTransition(ctx, a, b, name, p, W, H) {
  const lay = transitionLayer(name, p);
  ctx.save();
  ctx.clearRect(0, 0, W, H);
  ctx.drawImage(a, Math.round(lay.aDx * W), Math.round(lay.aDy * H));

  const blit = (dx = 0, dy = 0) => {
    if (!dx && !dy) { drawScaled(ctx, b, W, H, lay.scaleB); return; }
    ctx.save(); ctx.translate(Math.round(dx * W), Math.round(dy * H));
    drawScaled(ctx, b, W, H, lay.scaleB); ctx.restore();
  };

  if (!lay.masked) {
    ctx.globalAlpha = lay.alpha; blit(); ctx.globalAlpha = 1;
  } else if (lay.circles.length) {
    ctx.save();
    ctx.beginPath();
    for (const c of lay.circles) { ctx.moveTo((c.cx + c.r) * W, c.cy * H); ctx.arc(c.cx * W, c.cy * H, c.r * W, 0, Math.PI * 2); }
    ctx.clip();
    ctx.globalAlpha = lay.alpha; blit(); ctx.globalAlpha = 1;
    ctx.restore();
    if (lay.invert) {  // the mask is the *outside*: redraw A inside the circle
      ctx.save();
      ctx.beginPath();
      for (const c of lay.circles) { ctx.moveTo((c.cx + c.r) * W, c.cy * H); ctx.arc(c.cx * W, c.cy * H, c.r * W, 0, Math.PI * 2); }
      ctx.clip();
      ctx.drawImage(a, Math.round(lay.aDx * W), Math.round(lay.aDy * H));
      ctx.restore();
    }
  } else {
    if (lay.invert) { ctx.globalAlpha = lay.alpha; blit(); ctx.globalAlpha = 1; }
    for (const r of lay.rects) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(r.x * W, r.y * H, r.w * W, r.h * H);
      ctx.clip();
      if (lay.invert) ctx.drawImage(a, Math.round(lay.aDx * W), Math.round(lay.aDy * H));
      else { ctx.globalAlpha = lay.alpha; blit(r.dx, r.dy); }
      ctx.restore();
    }
  }
  if (lay.paperFlash) {
    ctx.globalAlpha = lay.paperFlash; ctx.fillStyle = PAPER; ctx.fillRect(0, 0, W, H); ctx.globalAlpha = 1;
  }
  ctx.restore();
}

export const transitionDuration = (name, fallback = 0.5) => TRANSITIONS[name]?.duration ?? fallback;
export const sfxFor = name => TRANSITIONS[name]?.sfx ?? null;
