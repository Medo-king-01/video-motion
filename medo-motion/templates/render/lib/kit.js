// Explainer-reel component kit for the Canvas renderer. Guide: <skill>/reference/explainer-reel-system.md
// Every draw function depends only on its arguments and t (deterministic frames). Caches hold pure precomputed data.
// Arabic is drawn word by word or line by line (never letter by letter) and revealed with right→left wipes.
import { clamp01, inkBox } from './arabic.js';

// ---------- basics ----------
const AR = /[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]/;
export const isArabic = s => AR.test(s);
export const seg = (t, start, dur) => clamp01((t - start) / dur);
export const ease = {
  linear: u => clamp01(u),
  outCubic: u => 1 - Math.pow(1 - clamp01(u), 3),
  inOutCubic: u => { u = clamp01(u); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; },
  outExpo: u => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp01(u))),
  outBack: (u, s = 1.70158) => { u = clamp01(u) - 1; return 1 + (s + 1) * u * u * u + s * u * u; },
};
export function rng(seed = 1) {
  let a = seed >>> 0;
  return () => { a = (a + 0x6D2B79F5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}
// Brand lock: Cairo for everything Arabic. `mono` stays a system monospace
// unless the project ships JetBrains Mono. Never mix a second display face
// into a brand reel without explicit approval.
export const FONTS = { text: 'Cairo', mono: 'JetBrains Mono', accent: 'Cairo', heavy: 'Cairo', arUi: 'Cairo' };
export const font = (weight, size, ...families) => `${weight} ${size}px ${families.map(f => `"${f}"`).join(', ')}, sans-serif`;
function setDir(ctx, text, align) { ctx.direction = isArabic(text) ? 'rtl' : 'ltr'; ctx.textAlign = align; if ('letterSpacing' in ctx) ctx.letterSpacing = '0px'; }

export function rr(ctx, x, y, w, h, r) { ctx.beginPath(); ctx.roundRect(x, y, w, h, r); }
export function withShadow(ctx, fn, { blur = 36, y = 14, color = 'rgba(46,36,35,.18)' } = {}) {
  ctx.save(); ctx.shadowColor = color; ctx.shadowBlur = blur; ctx.shadowOffsetY = y; fn(); ctx.restore();
}
// Run fn inside a transform: pop scale s and rotation rot (degrees) around (cx, cy).
export function around(ctx, cx, cy, { s = 1, rot = 0, alpha = 1 } = {}, fn) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(cx, cy); ctx.rotate(rot * Math.PI / 180); ctx.scale(s, s); ctx.translate(-cx, -cy); fn(); ctx.restore();
}
// Standard entrance: returns {s, alpha, dy} for an element entering at `start`.
export function enter(t, start, { dur = 0.35, from = 0.8, rise = 40 } = {}) {
  const p = seg(t, start, dur), e = ease.outBack(p);
  return { p, s: from + (1 - from) * e, alpha: clamp01(p * 2.5), dy: rise * (1 - ease.outCubic(p)) };
}

// ---------- surfaces ----------
export function paperTile(seed = 7, { size = 256, grain = 0.07 } = {}) {
  const c = document.createElement('canvas'); c.width = c.height = size;
  const g = c.getContext('2d'), img = g.createImageData(size, size), r = rng(seed);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = r() < 0.5 ? 0 : 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = Math.round(r() * grain * 255);
  }
  g.putImageData(img, 0, 0); return c;
}
export function drawPaper(ctx, W, H, tile, base = '#F3F2F1') {
  ctx.fillStyle = base; ctx.fillRect(0, 0, W, H);
  if (tile) { ctx.fillStyle = ctx.createPattern(tile, 'repeat'); ctx.fillRect(0, 0, W, H); }
}
export function dotGrid(ctx, W, H, { gap = 36, r = 2, color = 'rgba(46,36,35,.12)' } = {}) {
  ctx.save(); ctx.fillStyle = color;
  for (let y = gap / 2; y < H; y += gap) for (let x = gap / 2; x < W; x += gap) { ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.fill(); }
  ctx.restore();
}

// Chapter transition overlay. p 0→0.5 dots cover the frame from `origin`; 0.5→1 they shrink away. Swap scenes at p = 0.5.
export function halftoneWipe(ctx, W, H, p, { cell = 44, color = '#473938', origin = [W / 2, H / 2] } = {}) {
  const q = p < 0.5 ? p * 2 : (1 - p) * 2;
  if (q <= 0) return;
  const maxD = Math.hypot(Math.max(origin[0], W - origin[0]), Math.max(origin[1], H - origin[1]));
  ctx.save(); ctx.fillStyle = color;
  for (let y = cell / 2; y < H + cell; y += cell) for (let x = cell / 2; x < W + cell; x += cell) {
    const k = clamp01(q * 1.8 - (Math.hypot(x - origin[0], y - origin[1]) / maxD) * 0.8);
    if (k > 0) { ctx.beginPath(); ctx.arc(x, y, cell * 0.75 * k, 0, Math.PI * 2); ctx.fill(); }
  }
  ctx.restore();
}

// Printed-dot version of an image (screenshots, photos). Pass w/h with the image's aspect ratio.
const _ht = new Map();
export function halftoneImage(ctx, img, x, y, w, h, { cell = 9, ink = '#473938', paper = null, gamma = 1, key = '' } = {}) {
  const id = `${key || img.src}|${Math.round(w)}x${Math.round(h)}|${cell}|${gamma}`;
  let grid = _ht.get(id);
  if (!grid) {
    const cols = Math.ceil(w / cell), rows = Math.ceil(h / cell), c = document.createElement('canvas');
    c.width = cols; c.height = rows; const g = c.getContext('2d'); g.drawImage(img, 0, 0, cols, rows);
    const d = g.getImageData(0, 0, cols, rows).data, v = new Float32Array(cols * rows);
    for (let i = 0; i < v.length; i++) {
      const L = (0.2126 * d[i * 4] + 0.7152 * d[i * 4 + 1] + 0.0722 * d[i * 4 + 2]) / 255;
      v[i] = Math.pow(1 - L, gamma) * (d[i * 4 + 3] / 255);
    }
    grid = { v, cols, rows }; _ht.set(id, grid);
  }
  ctx.save();
  if (paper) { ctx.fillStyle = paper; ctx.fillRect(x, y, w, h); }
  ctx.fillStyle = ink;
  for (let r = 0; r < grid.rows; r++) for (let c = 0; c < grid.cols; c++) {
    const v = grid.v[r * grid.cols + c];
    if (v > 0.04) { ctx.beginPath(); ctx.arc(x + c * cell + cell / 2, y + r * cell + cell / 2, cell * 0.58 * Math.sqrt(v), 0, Math.PI * 2); ctx.fill(); }
  }
  ctx.restore();
}

// ---------- HUD ----------
// Section label: style 'mono' («// ٠٢ · النظام») or 'tape' (dark tape sticker). rtl anchors at the right edge.
export function sectionLabel(ctx, text, { x, y, rtl = true, style = 'mono', size = 26, ink = '#473938', tape = '#473938', tapeText = '#F3F2F1', rot = -1.5, alpha = 1 } = {}) {
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.font = font(style === 'tape' ? 800 : 500, size, FONTS.mono, FONTS.arUi);
  setDir(ctx, text, rtl ? 'right' : 'left'); ctx.textBaseline = 'middle';
  if (style === 'tape') {
    const w = ctx.measureText(text).width + size * 1.4, h = size * 1.9, x0 = rtl ? x - w : x;
    around(ctx, x0 + w / 2, y, { rot }, () => {
      ctx.fillStyle = tape; ctx.beginPath();
      ctx.moveTo(x0, y - h / 2); ctx.lineTo(x0 + w, y - h / 2 + 3); ctx.lineTo(x0 + w - 6, y + h / 2); ctx.lineTo(x0 + 4, y + h / 2 - 2); ctx.closePath(); ctx.fill();
      ctx.fillStyle = tapeText; ctx.fillText(text, rtl ? x0 + w - size * 0.7 : x0 + size * 0.7, y + 1);
    });
  } else { ctx.fillStyle = ink; ctx.globalAlpha *= 0.75; ctx.fillText(text, x, y); }
  ctx.restore();
}
// Progress pips «● ● ○ ○» with an optional label («٢/٥»). done = count finished, active = index in progress.
export function progressPips(ctx, { x, y, total, done, active = -1, rtl = true, size = 16, ink = '#473938', accent = '#CB271B', label = '' } = {}) {
  ctx.save(); const gap = size * 0.8, w = size * 2.2;
  for (let i = 0; i < total; i++) {
    const px = rtl ? x - i * (w + gap) - w : x + i * (w + gap);
    rr(ctx, px, y - size / 2, w, size, size / 2);
    if (i < done) { ctx.fillStyle = ink; ctx.fill(); }
    else if (i === active) { ctx.fillStyle = accent; ctx.fill(); }
    else { ctx.lineWidth = 2.5; ctx.strokeStyle = ink; ctx.globalAlpha = 0.45; ctx.stroke(); ctx.globalAlpha = 1; }
  }
  if (label) {
    ctx.font = font(700, size * 1.5, FONTS.mono, FONTS.arUi); ctx.fillStyle = ink; ctx.textBaseline = 'middle';
    const end = rtl ? x - total * (w + gap) - size * 0.6 : x + total * (w + gap) + size * 0.6;
    setDir(ctx, label, rtl ? 'right' : 'left'); ctx.fillText(label, end, y + 1);
  }
  ctx.restore();
}
// Metaphor progress: a strip of sockets; slot i gets plugged at plugTimes[i] (a coloured plug drops on a cable).
export function slotStrip(ctx, t, { x, y, w, total = 4, plugTimes = [], colors = ['#8B6765', '#C9C5C2', '#D5AEA6', '#D97F68'], labels = [], rtl = true, body = '#F3F2F1', ink = '#473938' } = {}) {
  const h = w / (total + 1.6), r = h * 0.32;
  ctx.save();
  withShadow(ctx, () => { rr(ctx, x, y, w, h, h / 2); ctx.fillStyle = body; ctx.fill(); }, { blur: 20, y: 8 });
  rr(ctx, x, y, w, h, h / 2); ctx.lineWidth = 4; ctx.strokeStyle = ink; ctx.stroke();
  const sw = { x: rtl ? x + w - h * 0.75 : x + h * 0.25, y: y + h * 0.25 };
  rr(ctx, sw.x, sw.y, h * 0.5, h * 0.5, 8); ctx.fillStyle = '#CB271B'; ctx.fill();
  for (let i = 0; i < total; i++) {
    const cx = rtl ? x + w - h * 1.3 - i * (w - h * 1.6) / total - (w - h * 1.6) / total / 2 + h * 0.25
                   : x + h * 1.3 + i * (w - h * 1.6) / total + (w - h * 1.6) / total / 2 - h * 0.25;
    const cy = y + h / 2;
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.fillStyle = '#fff'; ctx.fill(); ctx.lineWidth = 3; ctx.strokeStyle = ink; ctx.stroke();
    const pt = plugTimes[i];
    if (pt !== undefined && t >= pt) {
      const p = ease.outBack(seg(t, pt, 0.4)), py = cy - (1 - p) * (cy + 40);
      ctx.strokeStyle = colors[i % colors.length]; ctx.lineWidth = 8; ctx.beginPath(); ctx.moveTo(cx, -10); ctx.lineTo(cx, py); ctx.stroke();
      ctx.beginPath(); ctx.arc(cx, py, r * 1.12, 0, Math.PI * 2); ctx.fillStyle = colors[i % colors.length]; ctx.fill();
      ctx.lineWidth = 3; ctx.strokeStyle = ink; ctx.stroke();
      ctx.fillStyle = '#fff'; ctx.font = font(800, r * 1.1, FONTS.mono, FONTS.arUi); ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(String(i + 1), cx, py + 2);
    }
    if (labels[i]) {
      ctx.fillStyle = ink; ctx.font = font(700, h * 0.2, FONTS.mono, FONTS.arUi); setDir(ctx, labels[i], 'center'); ctx.textBaseline = 'top';
      ctx.fillText(labels[i], cx, y + h + 10);
    }
  }
  ctx.restore();
}
export function handleTag(ctx, text, { x, y, size = 24, color = '#473938', alpha = 0.35, rtl = true } = {}) {
  ctx.save(); ctx.globalAlpha *= alpha; ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 3;
  const s = size * 1.2, ix = rtl ? x - s : x;
  rr(ctx, ix, y - s / 2, s, s, s * 0.3); ctx.stroke();
  ctx.beginPath(); ctx.arc(ix + s / 2, y, s * 0.24, 0, Math.PI * 2); ctx.stroke();
  ctx.font = font(700, size, FONTS.mono); ctx.direction = 'ltr'; ctx.textAlign = rtl ? 'right' : 'left'; ctx.textBaseline = 'middle';
  ctx.fillText(text, rtl ? ix - 10 : ix + s + 10, y + 1);
  ctx.restore();
}

// ---------- captions ----------
// Editorial top caption. words: [{w, s, key}] with s = spoken start (s). Keywords switch to the accent font/colour.
export function captionBlock(ctx, words, t, { x, y, maxWidth, size = 62, rtl = true, color = '#473938', keyColor = '#CB271B', family = FONTS.text, keyFamily = FONTS.accent, weight = 600, keyWeight = 700, lineHeight = 1.4, appear = 0.18, alpha = 1 } = {}) {
  const f = wd => wd.key ? font(keyWeight, size * 1.1, keyFamily, family) : font(weight, size, family);
  ctx.save(); ctx.globalAlpha *= alpha; ctx.textBaseline = 'alphabetic';
  ctx.font = font(weight, size, family); const space = ctx.measureText(' ').width;
  let cx = x, line = 0;
  for (const wd of words) {
    ctx.font = f(wd); const w = ctx.measureText(wd.w).width;
    const used = rtl ? x - cx : cx - x;
    if (used > 0 && used + w > maxWidth) { line++; cx = x; }
    const p = seg(t, wd.s, appear);
    if (t >= wd.s) {
      ctx.save(); ctx.globalAlpha *= clamp01(p * 2); ctx.fillStyle = wd.key ? keyColor : color;
      setDir(ctx, wd.w, rtl ? 'right' : 'left');
      ctx.fillText(wd.w, cx, y + line * size * lineHeight + 18 * (1 - ease.outCubic(p)));
      ctx.restore();
    }
    cx += rtl ? -(w + space) : w + space;
  }
  ctx.restore();
}
// Bottom keycap captions. groups: [{s, e, words: [{w, s, key}]}]. The latest spoken word in the group is highlighted.
export function keycaps(ctx, groups, t, { x, y, size = 64, rtl = true, gap = 18, face = '#F3F2F1', active = '#D97F68', dark = '#473938', family = FONTS.text } = {}) {
  const g = groups.find(gr => t >= gr.s && t < gr.e);
  if (!g) return;
  ctx.save(); ctx.font = font(800, size, family); ctx.textBaseline = 'middle';
  const padX = size * 0.42, h = size * 1.45, depth = size * 0.16;
  const items = g.words.map(wd => ({ ...wd, width: ctx.measureText(wd.w).width + padX * 2 }));
  const total = items.reduce((s, it) => s + it.width, 0) + gap * (items.length - 1);
  let cx = rtl ? x + total / 2 : x - total / 2;
  const current = items.filter(it => t >= it.s).at(-1);
  for (const it of items) {
    const kx = rtl ? cx - it.width : cx;
    if (t >= it.s) {
      const e = enter(t, it.s, { dur: 0.2, from: 0.85, rise: 12 });
      const isActive = it === current;
      const top = it.key ? dark : isActive ? active : face, ink = it.key ? (isActive ? active : '#fff') : dark;
      around(ctx, kx + it.width / 2, y, { s: e.s, alpha: e.alpha }, () => {
        rr(ctx, kx, y - h / 2 + depth, it.width, h, size * 0.22); ctx.fillStyle = 'rgba(46,36,35,.35)'; ctx.fill();
        rr(ctx, kx, y - h / 2, it.width, h, size * 0.22); ctx.fillStyle = top; ctx.fill();
        ctx.lineWidth = 3; ctx.strokeStyle = 'rgba(46,36,35,.25)'; ctx.stroke();
        ctx.fillStyle = ink; setDir(ctx, it.w, 'center'); ctx.fillText(it.w, kx + it.width / 2, y + 2);
      });
    }
    cx += rtl ? -(it.width + gap) : it.width + gap;
  }
  ctx.restore();
}

// ---------- devices ----------
export function card(ctx, x, y, w, h, { r = 28, fill = '#fff', stroke = null, lw = 4, rot = 0, shadow = true, s = 1, alpha = 1 } = {}, inside = null) {
  around(ctx, x + w / 2, y + h / 2, { s, rot, alpha }, () => {
    if (shadow) withShadow(ctx, () => { rr(ctx, x, y, w, h, r); ctx.fillStyle = fill; ctx.fill(); });
    else { rr(ctx, x, y, w, h, r); ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { rr(ctx, x, y, w, h, r); ctx.lineWidth = lw; ctx.strokeStyle = stroke; ctx.stroke(); }
    if (inside) { ctx.save(); rr(ctx, x, y, w, h, r); ctx.clip(); inside(x, y, w, h); ctx.restore(); }
  });
}
// Phone mock-up. drawScreen(sx, sy, sw, sh) paints the screen inside a clip. Height = w * 2.05.
export function phone(ctx, x, y, w, drawScreen, { frame = '#473938', screen = '#F3F2F1', rot = 0, s = 1, alpha = 1 } = {}) {
  const h = w * 2.05, r = w * 0.16, inset = w * 0.035;
  around(ctx, x + w / 2, y + h / 2, { s, rot, alpha }, () => {
    withShadow(ctx, () => { rr(ctx, x, y, w, h, r); ctx.fillStyle = frame; ctx.fill(); }, { blur: 50, y: 22, color: 'rgba(46,36,35,.25)' });
    const sx = x + inset, sy = y + inset, sw = w - inset * 2, sh = h - inset * 2;
    ctx.save(); rr(ctx, sx, sy, sw, sh, r - inset); ctx.clip(); ctx.fillStyle = screen; ctx.fillRect(sx, sy, sw, sh);
    drawScreen?.(sx, sy, sw, sh); ctx.restore();
    rr(ctx, x + w / 2 - w * 0.16, sy + w * 0.035, w * 0.32, w * 0.075, w * 0.04); ctx.fillStyle = frame; ctx.fill();
  });
}
// App / terminal window with three dots and a title. body(bx, by, bw, bh) draws the content.
export function appWindow(ctx, x, y, w, h, { title = '', dark = true, body = null, r = 22, rot = 0, s = 1, alpha = 1 } = {}) {
  const bg = dark ? '#2E2423' : '#F3F2F1', bar = dark ? '#473938' : '#D8D7D5', fg = dark ? '#BFBAB7' : '#8B6765', head = 54;
  around(ctx, x + w / 2, y + h / 2, { s, rot, alpha }, () => {
    withShadow(ctx, () => { rr(ctx, x, y, w, h, r); ctx.fillStyle = bg; ctx.fill(); }, { blur: 44, y: 18, color: 'rgba(46,36,35,.28)' });
    ctx.save(); rr(ctx, x, y, w, h, r); ctx.clip();
    ctx.fillStyle = bar; ctx.fillRect(x, y, w, head);
    ['#CB271B', '#D5AEA6', '#8B6765'].forEach((c, i) => { ctx.beginPath(); ctx.arc(x + 30 + i * 26, y + head / 2, 8, 0, Math.PI * 2); ctx.fillStyle = c; ctx.fill(); });
    if (title) { ctx.font = font(500, 22, FONTS.mono, FONTS.arUi); ctx.fillStyle = fg; setDir(ctx, title, 'center'); ctx.textBaseline = 'middle'; ctx.fillText(title, x + w / 2, y + head / 2 + 1); }
    body?.(x, y + head, w, h - head);
    ctx.restore();
  });
}
// Terminal typing. Latin/code types per character; Arabic lines are revealed right→left as whole shaped lines.
export function typeLines(ctx, lines, t, { x, y, w, size = 28, lineH = 1.55, color = '#F3F2F1', accent = '#D97F68', start = 0, cps = 38, gapAfter = 0.15 } = {}) {
  ctx.save(); ctx.textBaseline = 'alphabetic';
  let clock = start;
  lines.forEach((ln, i) => {
    const text = typeof ln === 'string' ? ln : ln.text, col = (typeof ln === 'object' && ln.color) || color;
    const dur = Math.max(0.2, text.length / cps), p = seg(t, clock, dur), ly = y + i * size * lineH;
    if (t >= clock) {
      const ar = isArabic(text);
      ctx.font = font(500, size, FONTS.mono, FONTS.arUi); ctx.fillStyle = col;
      if (ar) {
        ctx.direction = 'rtl'; ctx.textAlign = 'right';
        const b = inkBox(ctx, text, x + w, ly), vis = b.w * ease.outCubic(p);
        ctx.save(); ctx.beginPath(); ctx.rect(b.x + b.w - vis, b.y, vis, b.h); ctx.clip(); ctx.fillText(text, x + w, ly); ctx.restore();
      } else {
        ctx.direction = 'ltr'; ctx.textAlign = 'left';
        const shown = text.slice(0, Math.floor(text.length * p));
        ctx.fillText(shown, x, ly);
        if (p < 1 && Math.floor(t * 2.5) % 2 === 0) { const cw = ctx.measureText(shown).width; ctx.fillStyle = accent; ctx.fillRect(x + cw + 4, ly - size * 0.8, size * 0.55, size); }
      }
    }
    clock += dur + gapAfter;
  });
  ctx.restore();
}
// Checklist of steps: pending → spinner → tick. items: [{title, sub}]; step i runs from start + i*step.
export function checklist(ctx, items, t, { x, y, w, rowH = 92, size = 32, start = 0, step = 0.7, dark = true, accent = '#CB271B', rtl = true } = {}) {
  const fg = dark ? '#F3F2F1' : '#473938', dim = dark ? 'rgba(243,242,241,.45)' : 'rgba(46,36,35,.45)';
  items.forEach((it, i) => {
    const ry = y + i * rowH, s0 = start + i * step, state = t < s0 ? 0 : t < s0 + step ? 1 : 2;
    const ix = rtl ? x + w - 34 : x + 34, iy = ry + rowH / 2;
    if (state === 1) { rr(ctx, x, ry + 6, w, rowH - 12, 14); ctx.fillStyle = dark ? 'rgba(243,242,241,.07)' : 'rgba(46,36,35,.05)'; ctx.fill();
      ctx.fillStyle = accent; ctx.fillRect(rtl ? x + w - 6 : x, ry + 14, 6, rowH - 28); }
    ctx.lineWidth = 4;
    if (state === 0) { ctx.beginPath(); ctx.arc(ix, iy, 15, 0, Math.PI * 2); ctx.strokeStyle = dim; ctx.stroke(); }
    if (state === 1) { const a = t * 7; ctx.beginPath(); ctx.arc(ix, iy, 15, a, a + Math.PI * 1.4); ctx.strokeStyle = accent; ctx.stroke(); }
    if (state === 2) {
      const p = ease.outBack(seg(t, s0 + step, 0.25));
      around(ctx, ix, iy, { s: p }, () => {
        ctx.beginPath(); ctx.arc(ix, iy, 16, 0, Math.PI * 2); ctx.fillStyle = accent; ctx.fill();
        ctx.beginPath(); ctx.moveTo(ix - 7, iy); ctx.lineTo(ix - 2, iy + 6); ctx.lineTo(ix + 8, iy - 6); ctx.strokeStyle = '#fff'; ctx.lineWidth = 4; ctx.stroke();
      });
    }
    const tx = rtl ? ix - 34 : ix + 34;
    ctx.fillStyle = state === 0 ? dim : fg; ctx.font = font(700, size, FONTS.text, FONTS.mono);
    setDir(ctx, it.title, rtl ? 'right' : 'left'); ctx.textBaseline = 'alphabetic';
    ctx.fillText(it.title, tx, iy + (it.sub ? -2 : size * 0.35));
    if (it.sub) { ctx.fillStyle = dim; ctx.font = font(500, size * 0.62, FONTS.mono, FONTS.arUi); setDir(ctx, it.sub, rtl ? 'right' : 'left'); ctx.fillText(it.sub, tx, iy + size * 0.85); }
  });
}
// Folder with file tabs sticking out. p 0→1 lifts the papers. Height ≈ w * 0.72.
export function folder(ctx, x, y, w, { color = '#8B6765', label = '', tabs = [], p = 1, rot = 0, s = 1, alpha = 1 } = {}) {
  const h = w * 0.72, lift = 60 * ease.outBack(p);
  around(ctx, x + w / 2, y + h / 2, { s, rot, alpha }, () => {
    rr(ctx, x, y + h * 0.08, w, h * 0.92, 26); ctx.fillStyle = shade(color, -0.18); ctx.fill();
    rr(ctx, x + w * 0.06, y, w * 0.32, h * 0.2, 14); ctx.fill();
    tabs.slice(0, 3).forEach((tb, i) => {
      const px = x + w * (0.1 + i * 0.28), py = y + h * 0.1 - lift * (1 - i * 0.15);
      around(ctx, px + w * 0.15, py + h * 0.3, { rot: (i - 1) * 6 }, () => {
        withShadow(ctx, () => { rr(ctx, px, py, w * 0.3, h * 0.6, 10); ctx.fillStyle = '#F3F2F1'; ctx.fill(); }, { blur: 12, y: 4 });
        ctx.fillStyle = '#473938'; ctx.font = font(600, w * 0.04, FONTS.mono, FONTS.arUi); setDir(ctx, tb, 'center'); ctx.fillText(tb, px + w * 0.15, py + h * 0.1);
        ctx.fillStyle = 'rgba(46,36,35,.15)'; for (let k = 0; k < 3; k++) ctx.fillRect(px + w * 0.04, py + h * (0.18 + k * 0.08), w * 0.22, 6);
      });
    });
    withShadow(ctx, () => { rr(ctx, x, y + h * 0.3, w, h * 0.7, 26); ctx.fillStyle = color; ctx.fill(); }, { blur: 30, y: 12 });
    if (label) { ctx.fillStyle = '#fff'; ctx.font = font(700, w * 0.1, FONTS.text, FONTS.mono); setDir(ctx, label, 'center'); ctx.textBaseline = 'middle'; ctx.fillText(label, x + w / 2, y + h * 0.66); }
  });
}
export function chip(ctx, text, { x, y, size = 28, bg = '#F3F2F1', fg = '#473938', stroke = null, align = 'center', s = 1, alpha = 1 } = {}) {
  ctx.save(); ctx.font = font(700, size, FONTS.mono, FONTS.arUi);
  const w = ctx.measureText(text).width + size * 1.4, h = size * 1.8, x0 = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
  around(ctx, x0 + w / 2, y, { s, alpha }, () => {
    withShadow(ctx, () => { rr(ctx, x0, y - h / 2, w, h, h / 2); ctx.fillStyle = bg; ctx.fill(); }, { blur: 16, y: 6 });
    if (stroke) { rr(ctx, x0, y - h / 2, w, h, h / 2); ctx.lineWidth = 3; ctx.strokeStyle = stroke; ctx.stroke(); }
    ctx.fillStyle = fg; setDir(ctx, text, 'center'); ctx.textBaseline = 'middle'; ctx.fillText(text, x0 + w / 2, y + 2);
  });
  ctx.restore();
}
// Rubber stamp that slams in at `start` (scale 1.7→1, short shake). Rendered once to a cached, distressed bitmap.
const _stamps = new Map();
export function stamp(ctx, text, t, { x, y, start = 0, size = 150, color = '#CB271B', rot = -7, family = FONTS.heavy, weight = 900, seed = 3 } = {}) {
  if (t < start) return;
  const id = `${text}|${size}|${color}|${family}|${seed}`;
  let bmp = _stamps.get(id);
  if (!bmp) {
    const m = document.createElement('canvas').getContext('2d'); m.font = font(weight, size, family);
    const tw = m.measureText(text).width, pad = size * 0.35, bw = Math.ceil(tw + pad * 2), bh = Math.ceil(size * 1.6);
    const c = document.createElement('canvas'); c.width = bw; c.height = bh; const g = c.getContext('2d');
    g.strokeStyle = color; g.lineWidth = size * 0.07; g.strokeRect(size * 0.08, size * 0.08, bw - size * 0.16, bh - size * 0.16);
    g.fillStyle = color; g.font = font(weight, size, family); g.textAlign = 'center'; g.textBaseline = 'middle';
    g.direction = isArabic(text) ? 'rtl' : 'ltr'; g.fillText(text, bw / 2, bh / 2 + size * 0.06);
    g.globalCompositeOperation = 'destination-out'; const r = rng(seed);
    for (let i = 0; i < (bw * bh) / 900; i++) { g.globalAlpha = 0.3 + r() * 0.7; g.beginPath(); g.arc(r() * bw, r() * bh, 1 + r() * size * 0.03, 0, Math.PI * 2); g.fill(); }
    bmp = c; _stamps.set(id, bmp);
  }
  const p = seg(t, start, 0.25), sc = 1.7 - 0.7 * ease.outExpo(p);
  const shake = t - start > 0.25 && t - start < 0.4 ? Math.sin((t - start) * 120) * 3 : 0;
  around(ctx, x + shake, y, { s: sc, rot, alpha: clamp01(p * 3) }, () => ctx.drawImage(bmp, x + shake - bmp.width / 2, y - bmp.height / 2));
}
export function burst(ctx, x, y, t, { start = 0, r = 90, n = 8, len = 34, color = '#473938', lw = 6, spread = Math.PI * 2, angle = -Math.PI / 2 } = {}) {
  const p = seg(t, start, 0.3); if (p <= 0 || p >= 1) return;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.globalAlpha = 1 - p;
  for (let i = 0; i < n; i++) {
    const a = angle - spread / 2 + spread * (i + 0.5) / n, d0 = r + 20 * ease.outCubic(p);
    ctx.beginPath(); ctx.moveTo(x + Math.cos(a) * d0, y + Math.sin(a) * d0); ctx.lineTo(x + Math.cos(a) * (d0 + len), y + Math.sin(a) * (d0 + len)); ctx.stroke();
  }
  ctx.restore();
}
// Hand-drawn ellipse around something; p 0→1 draws it.
export function circleMark(ctx, x, y, w, h, { p = 1, color = '#D97F68', lw = 7 } = {}) {
  if (p <= 0) return;
  ctx.save(); ctx.strokeStyle = color; ctx.lineWidth = lw; ctx.lineCap = 'round'; ctx.beginPath();
  const steps = 60, end = Math.floor(steps * 1.15 * clamp01(p));
  for (let i = 0; i <= end; i++) {
    const a = -Math.PI * 0.6 + (i / steps) * Math.PI * 2, wob = 1 + 0.04 * Math.sin(i * 0.9);
    const px = x + w / 2 + Math.cos(a) * w / 2 * wob, py = y + h / 2 + Math.sin(a) * h / 2 * wob;
    i ? ctx.lineTo(px, py) : ctx.moveTo(px, py);
  }
  ctx.stroke(); ctx.restore();
}
// Counter text for p 0→1 (ease-out). digits: 'western' | 'arabic'.
export function rolling(from, to, p, { digits = 'western', decimals = 0, sep = true } = {}) {
  const v = from + (to - from) * ease.outCubic(p);
  let s = v.toFixed(decimals);
  if (sep) { const [a, b] = s.split('.'); s = a.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (b ? '.' + b : ''); }
  if (digits === 'arabic') s = s.replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[d]).replace(/,/g, '٬').replace('.', '٫');
  return s;
}
// End card: a comment field types the keyword, the comment posts, then a DM card arrives with the gift.
export function commentCTA(ctx, t, { x, y, w, keyword, start = 0, placeholder = 'أضف تعليقاً…', dmTitle = 'وصلتك رسالة جديدة', dmBody = '', accent = '#CB271B', dark = false } = {}) {
  const bg = dark ? '#2E2423' : '#F3F2F1', fg = dark ? '#F3F2F1' : '#473938', dim = dark ? 'rgba(243,242,241,.45)' : 'rgba(46,36,35,.4)';
  const lt = t - start; if (lt < 0) return;
  const fieldY = y + 390, h = 96;
  // DM card
  const dm = enter(lt, 1.7, { dur: 0.4, from: 0.9, rise: -60 });
  if (lt >= 1.7) card(ctx, x, y + dm.dy, w, 190, { r: 30, fill: bg, s: dm.s, alpha: dm.alpha }, (cx, cy, cw) => {
    ctx.beginPath(); ctx.arc(cx + cw - 70, cy + 95, 40, 0, Math.PI * 2); ctx.fillStyle = accent; ctx.fill();
    ctx.fillStyle = '#fff'; ctx.font = font(800, 40, FONTS.text); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText('✉', cx + cw - 70, cy + 97);
    ctx.fillStyle = fg; ctx.font = font(700, 36, FONTS.text); setDir(ctx, dmTitle, 'right'); ctx.textBaseline = 'alphabetic'; ctx.fillText(dmTitle, cx + cw - 130, cy + 85);
    if (dmBody) { ctx.fillStyle = dim; ctx.font = font(500, 28, FONTS.text, FONTS.mono); setDir(ctx, dmBody, 'right'); ctx.fillText(dmBody, cx + cw - 130, cy + 135); }
  });
  // posted comment
  const posted = enter(lt, 1.2, { dur: 0.3, rise: 30 });
  if (lt >= 1.2) {
    ctx.save(); ctx.globalAlpha *= posted.alpha;
    ctx.beginPath(); ctx.arc(x + w - 40, fieldY - 100 + posted.dy, 30, 0, Math.PI * 2); ctx.fillStyle = '#C9C5C2'; ctx.fill();
    ctx.fillStyle = fg; ctx.font = font(800, 48, FONTS.text); setDir(ctx, keyword, 'right'); ctx.textBaseline = 'middle';
    ctx.fillText(keyword, x + w - 90, fieldY - 96 + posted.dy); ctx.restore();
  }
  // field + typing
  const fIn = enter(lt, 0, { dur: 0.3, rise: 40 });
  around(ctx, x + w / 2, fieldY + h / 2, { s: fIn.s, alpha: fIn.alpha }, () => {
    withShadow(ctx, () => { rr(ctx, x, fieldY, w, h, h / 2); ctx.fillStyle = bg; ctx.fill(); }, { blur: 24, y: 10 });
    const typing = seg(lt, 0.35, 0.6), sent = lt >= 1.2;
    ctx.textBaseline = 'middle'; ctx.font = font(700, 40, FONTS.text);
    if (typing <= 0 || sent) { ctx.fillStyle = dim; ctx.font = font(500, 32, FONTS.text); setDir(ctx, placeholder, 'right'); ctx.fillText(placeholder, x + w - 40, fieldY + h / 2 + 2); }
    else {
      ctx.fillStyle = fg; ctx.direction = 'rtl'; ctx.textAlign = 'right';
      const b = inkBox(ctx, keyword, x + w - 40, fieldY + h / 2 + 2), vis = b.w * typing;
      ctx.save(); ctx.beginPath(); ctx.rect(b.x + b.w - vis, b.y, vis, b.h); ctx.clip(); ctx.fillText(keyword, x + w - 40, fieldY + h / 2 + 2); ctx.restore();
    }
    const pulse = lt > 0.95 && lt < 1.25 ? 1 + 0.15 * Math.sin((lt - 0.95) * 20) : 1;
    around(ctx, x + 60, fieldY + h / 2, { s: pulse }, () => {
      ctx.beginPath(); ctx.arc(x + 60, fieldY + h / 2, 34, 0, Math.PI * 2); ctx.fillStyle = accent; ctx.fill();
      ctx.fillStyle = '#fff'; ctx.font = font(800, 34, FONTS.text); ctx.textAlign = 'center'; ctx.fillText('↑', x + 60, fieldY + h / 2 + 2);
    });
  });
}
// Lighten (+) or darken (−) a #RRGGBB colour by amount −1..1.
export function shade(hex, amt) {
  const n = parseInt(hex.slice(1), 16), f = c => Math.round(Math.min(255, Math.max(0, amt < 0 ? c * (1 + amt) : c + (255 - c) * amt)));
  return '#' + [n >> 16, (n >> 8) & 255, n & 255].map(f).map(v => v.toString(16).padStart(2, '0')).join('');
}
