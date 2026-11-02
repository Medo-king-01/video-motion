// Shared visual kit for RAM Episode 03 — same approved S01 v6 design language.
// Backgrounds: brand v2.6 mesh_dark/mesh_light + grid (per-scene cell/speed/direction) + 30 dust.
// The RAM module design is IDENTICAL across all scenes (BRIEF requirement).
import { PALETTE as C } from './brand.js';
import { family } from './fonts.js';

export const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
export const out = p => 1 - Math.pow(1 - clamp(p), 3);
export const back = p => { const c1 = 1.70158, c3 = c1 + 1; p = clamp(p); return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };

export function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }

// 30 dust particles, deterministic per scene seed (brand rule).
export function dustField(seed) {
  const r = rng(seed), a = [];
  for (let i = 0; i < 30; i++) a.push({ x: r() * 1080, y: r() * 1920, z: 0.35 + r() * 0.65, s: 1 + r() * 2.4, ph: r() * Math.PI * 2, sp: 6 + r() * 16 });
  return a;
}

// Approved mesh + grid + dust. theme: 'dark'|'light'; grid: {cell, speed, dir:'v'|'h'}
export function background(c, W, H, t, { theme = 'dark', grid = { cell: 40, speed: 5, dir: 'v' }, dust }) {
  const dark = theme === 'dark';
  const g = c.createLinearGradient(W * 0.55, 0, W * 0.45, H); // ~185deg
  g.addColorStop(0, dark ? C.ink : C.paper); g.addColorStop(1, dark ? C.inkShadow : C.gray1);
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  const glow = c.createRadialGradient(W * 0.5, H * 0.35, 20, W * 0.5, H * 0.35, W * 0.62);
  glow.addColorStop(0, dark ? 'rgba(203,39,27,0.08)' : 'rgba(213,174,166,0.15)');
  glow.addColorStop(1, dark ? 'rgba(203,39,27,0)' : 'rgba(213,174,166,0)');
  c.fillStyle = glow; c.fillRect(0, 0, W, H);
  c.save(); c.strokeStyle = dark ? 'rgba(201,197,194,0.08)' : 'rgba(113,113,122,0.12)'; c.lineWidth = 1;
  const cell = grid.cell, off = (t * grid.speed) % cell;
  if (grid.dir === 'h') {
    for (let x = -cell + off; x < W + cell; x += cell) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); }
    for (let y = 0; y <= H; y += cell) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); }
  } else {
    for (let x = 0; x <= W; x += cell) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); }
    for (let y = -cell + off; y < H + cell; y += cell) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); }
  }
  c.restore();
  if (dust) {
    c.save();
    for (const p of dust) {
      let y = (p.y - t * p.sp * p.z) % (H + 40); if (y < 0) y += H + 40;
      const x = p.x + Math.sin(t * 0.4 + p.ph) * 10 * p.z;
      c.globalAlpha = (dark ? 0.05 : 0.07) + 0.10 * p.z; c.fillStyle = dark ? C.gray2 : C.inkSoft;
      c.beginPath(); c.arc(x, y, p.s * p.z, 0, Math.PI * 2); c.fill();
    }
    c.restore();
  }
}

// Brand signature: big red circle, breathing + smooth entrance.
export function redCircle(c, W, H, t, { cx = W / 2, cy = 900, r = 440, at = 0.15, dur = 0.9 } = {}) {
  const p = clamp((t - at) / dur); if (!p) return;
  const e = out(p), breathe = 1 + 0.018 * Math.sin(t * 0.9);
  const R = r * (0.82 + 0.18 * e) * breathe;
  c.save(); c.globalAlpha = e;
  const g = c.createRadialGradient(cx - 70, cy - 90, 40, cx, cy, R);
  g.addColorStop(0, C.red); g.addColorStop(1, C.redDeep);
  c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, Math.PI * 2); c.fill();
  c.restore();
}

function rr(c, x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function poly(c, p, color) { c.beginPath(); c.moveTo(...p[0]); for (let i = 1; i < p.length; i++) c.lineTo(...p[i]); c.closePath(); c.fillStyle = color; c.fill(); }

// IDENTICAL module design to approved S01 (only capacity label varies). scale param for layout only.
export function module(c, cx, cy, t, at, label, { scale = 1, labelColor = C.paper } = {}) {
  const p = clamp((t - at) / 0.72); if (!p) return;
  const e = back(p), a = clamp(p * 2.2), s = (0.8 + 0.2 * e) * scale, rise = 90 * (1 - out(p));
  const bob = Math.sin(t * 1.3 + cx * 0.01) * 4 * clamp((t - at - 0.72) / 0.5);
  const w = 154, h = 570, x = cx - w / 2, y = cy - h / 2 + rise + bob;
  c.save(); c.globalAlpha = a;
  c.translate(cx, cy + rise + bob); c.scale(s, s); c.translate(-cx, -cy - rise - bob);
  c.save(); c.globalAlpha = a * 0.28; c.fillStyle = C.inkShadow;
  c.beginPath(); c.ellipse(cx, y + h + 20, w * 0.55, 15, 0, 0, Math.PI * 2); c.fill(); c.restore();
  poly(c, [[x + w, y + 18], [x + w + 18, y + 8], [x + w + 18, y + h - 20], [x + w, y + h]], C.inkShadow);
  poly(c, [[x + 9, y], [x + w, y + 18], [x + w + 18, y + 8], [x + 26, y - 10]], C.inkSoft);
  rr(c, x, y, w, h, 12); c.fillStyle = C.ink; c.fill(); c.lineWidth = 5; c.strokeStyle = C.inkSoft; c.stroke();
  c.fillStyle = C.gray3;
  for (let i = 0; i < 6; i++) { const yy = y + 62 + i * 72; rr(c, x + 29, yy, 96, 48, 7); c.fill(); c.fillStyle = C.gray1; rr(c, x + 39, yy + 9, 76, 30, 4); c.fill(); c.fillStyle = C.gray3; }
  c.fillStyle = C.inkShadow; rr(c, x + 57, y - 3, 42, 16, 5); c.fill();
  for (let i = 0; i < 9; i++) { rr(c, x + 12 + i * 15, y + h - 34, 9, 28, 2); c.fillStyle = i % 2 ? C.gray1 : C.blush; c.fill(); }
  c.fillStyle = C.red; rr(c, x + w - 9, y + 38, 5, 86, 2); c.fill();
  c.restore();
  c.save(); c.globalAlpha = a; c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
  c.font = `800 ${Math.round(72 * scale)}px ${family('Inter', 'latin')}`; c.fillStyle = labelColor;
  // label sits a scaled gap above the scaled body top (body top = cy - 285*scale)
  c.fillText(label, cx, cy + rise + bob - 353 * scale); c.restore();
}

// One impact per scene: ring + speed lines, kept above the caption safe line.
export function impactRing(c, W, H, t, at, { cx = W / 2, cy = 900, r0 = 450 } = {}) {
  const p = clamp((t - at) / 0.5); if (!p || p >= 1) return;
  c.save();
  c.globalAlpha = (1 - p) * 0.8; c.strokeStyle = C.paper; c.lineWidth = 6 * (1 - p) + 2;
  c.beginPath(); c.arc(cx, cy, r0 + 50 * out(p), 0, Math.PI * 2); c.stroke();
  c.globalAlpha = (1 - p) * 0.6; c.lineWidth = 3;
  for (let i = 0; i < 12; i++) {
    const ang = i / 12 * Math.PI * 2, a0 = r0 + 10 + 30 * out(p), a1 = a0 + 25 * (1 - p);
    c.beginPath(); c.moveTo(cx + Math.cos(ang) * a0, cy + Math.sin(ang) * a0); c.lineTo(cx + Math.cos(ang) * a1, cy + Math.sin(ang) * a1); c.stroke();
  }
  c.restore();
}

export function shake(t, at, amp = 9) {
  const p = clamp((t - at) / 0.3);
  if (p <= 0 || p >= 1) return [0, 0];
  const a = amp * (1 - p);
  return [Math.sin(t * 90) * a, Math.cos(t * 77) * a];
}

export function flash(c, W, H, t, at) {
  if (t >= at && t < at + 2 / 30) { c.fillStyle = 'rgba(243,242,241,0.45)'; c.fillRect(0, 0, W, H); }
}

// Small technical label (Inter, letter-spaced feel via size only).
export function techLabel(c, W, t, text, { y = 310, theme = 'dark', at = 0 } = {}) {
  c.save(); c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
  c.font = `800 30px ${family('Inter', 'latin')}`; c.fillStyle = theme === 'dark' ? C.gray4 : C.inkSoft;
  c.globalAlpha = clamp((t - at) / 0.6); c.fillText(text, W / 2, y); c.restore();
}

// Arabic headline word(s) — Cairo 800, unboxed. color per brand contrast rules.
export function arText(c, text, x, y, size, color, alpha = 1) {
  if (alpha <= 0) return;
  c.save(); c.globalAlpha = alpha; c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'rtl';
  c.font = `800 ${size}px ${family('Cairo', 'arabic')}`; c.fillStyle = color;
  c.fillText(text, x, y); c.restore();
}

// Rounded card with simple icon glyph + Arabic label; spring reveal.
export function card(c, cx, cy, w, h, t, at, { theme = 'dark', icon, label, accent = false }) {
  const p = clamp((t - at) / 0.6); if (!p) return;
  const e = back(p), a = clamp(p * 2.4), s = 0.85 + 0.15 * e;
  const dark = theme === 'dark';
  c.save(); c.globalAlpha = a;
  c.translate(cx, cy); c.scale(s, s); c.translate(-cx, -cy);
  c.save(); c.globalAlpha = a * 0.20; c.fillStyle = C.inkShadow;
  c.beginPath(); c.roundRect(cx - w / 2 + 6, cy - h / 2 + 10, w, h, 18); c.fill(); c.restore();
  c.beginPath(); c.roundRect(cx - w / 2, cy - h / 2, w, h, 18);
  c.fillStyle = dark ? C.ink : C.paper; c.fill();
  c.lineWidth = 3; c.strokeStyle = accent ? C.red : (dark ? C.inkSoft : C.gray2); c.stroke();
  if (icon) icon(c, cx, cy - h * 0.14, dark);
  if (label) arText(c, label, cx, cy + h * 0.28, 34, dark ? C.paper : C.ink, a);
  c.restore();
}

// Simple line icons (no stock, no HUD clutter). All strokes use brand tokens.
export const ICONS = {
  browser(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 44, y - 32, 88, 64, 8); c.stroke();
    c.beginPath(); c.moveTo(x - 44, y - 12); c.lineTo(x + 44, y - 12); c.stroke();
    c.fillStyle = col; c.beginPath(); c.arc(x - 32, y - 22, 4, 0, Math.PI * 2); c.fill();
    c.restore();
  },
  book(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.moveTo(x, y - 28); c.quadraticCurveTo(x - 24, y - 38, x - 44, y - 28); c.lineTo(x - 44, y + 28); c.quadraticCurveTo(x - 24, y + 18, x, y + 28); c.stroke();
    c.beginPath(); c.moveTo(x, y - 28); c.quadraticCurveTo(x + 24, y - 38, x + 44, y - 28); c.lineTo(x + 44, y + 28); c.quadraticCurveTo(x + 24, y + 18, x, y + 28); c.lineTo(x, y - 28); c.stroke();
    c.restore();
  },
  doc(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 32, y - 38, 64, 76, 6); c.stroke();
    c.lineWidth = 4;
    for (let i = 0; i < 3; i++) { c.beginPath(); c.moveTo(x - 18, y - 16 + i * 18); c.lineTo(x + 18, y - 16 + i * 18); c.stroke(); }
    c.restore();
  },
  feather(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.moveTo(x - 30, y + 32); c.quadraticCurveTo(x - 10, y - 30, x + 34, y - 36); c.quadraticCurveTo(x + 20, y + 6, x - 18, y + 20); c.stroke();
    c.beginPath(); c.moveTo(x - 30, y + 32); c.lineTo(x + 10, y - 8); c.stroke();
    c.restore();
  },
  multitask(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 42, y - 30, 52, 40, 6); c.stroke();
    c.beginPath(); c.roundRect(x - 8, y - 8, 52, 40, 6); c.stroke();
    c.restore();
  },
  code(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 6; c.lineCap = 'round';
    c.beginPath(); c.moveTo(x - 18, y - 24); c.lineTo(x - 40, y); c.lineTo(x - 18, y + 24); c.stroke();
    c.beginPath(); c.moveTo(x + 18, y - 24); c.lineTo(x + 40, y); c.lineTo(x + 18, y + 24); c.stroke();
    c.restore();
  },
  pen(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5; c.lineCap = 'round';
    c.beginPath(); c.moveTo(x - 32, y + 32); c.lineTo(x - 22, y + 4); c.lineTo(x + 22, y - 34); c.lineTo(x + 34, y - 22); c.lineTo(x - 4, y + 22); c.closePath(); c.stroke();
    c.restore();
  },
  film(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 42, y - 28, 84, 56, 6); c.stroke();
    c.lineWidth = 4;
    c.beginPath(); c.moveTo(x - 26, y - 28); c.lineTo(x - 26, y + 28); c.stroke();
    c.beginPath(); c.moveTo(x + 26, y - 28); c.lineTo(x + 26, y + 28); c.stroke();
    c.beginPath(); c.moveTo(x - 8, y - 12); c.lineTo(x + 12, y); c.lineTo(x - 8, y + 12); c.closePath(); c.stroke();
    c.restore();
  },
  cube(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5; c.lineJoin = 'round';
    c.beginPath(); c.moveTo(x, y - 36); c.lineTo(x + 34, y - 18); c.lineTo(x + 34, y + 18); c.lineTo(x, y + 36); c.lineTo(x - 34, y + 18); c.lineTo(x - 34, y - 18); c.closePath(); c.stroke();
    c.beginPath(); c.moveTo(x - 34, y - 18); c.lineTo(x, y); c.lineTo(x + 34, y - 18); c.stroke();
    c.beginPath(); c.moveTo(x, y); c.lineTo(x, y + 36); c.stroke();
    c.restore();
  },
  stack(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5; c.lineJoin = 'round';
    for (let i = 0; i < 3; i++) {
      const yy = y - 24 + i * 24;
      c.beginPath(); c.moveTo(x, yy - 12); c.lineTo(x + 38, yy); c.lineTo(x, yy + 12); c.lineTo(x - 38, yy); c.closePath(); c.stroke();
    }
    c.restore();
  },
  layers(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    for (let i = 0; i < 3; i++) { c.beginPath(); c.roundRect(x - 36 + i * 8, y - 30 + i * 14, 56, 40, 6); c.stroke(); }
    c.restore();
  },
  wallet(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 40, y - 26, 80, 56, 8); c.stroke();
    c.beginPath(); c.roundRect(x + 8, y - 6, 32, 20, 4); c.stroke();
    c.fillStyle = col; c.beginPath(); c.arc(x + 24, y + 4, 4, 0, Math.PI * 2); c.fill();
    c.restore();
  },
  gauge(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 6; c.lineCap = 'round';
    c.beginPath(); c.arc(x, y + 10, 36, Math.PI, 2 * Math.PI); c.stroke();
    c.beginPath(); c.moveTo(x, y + 10); c.lineTo(x + 20, y - 14); c.stroke();
    c.restore();
  },
  chat(c, x, y, dark) {
    const col = dark ? C.salmon : C.red;
    c.save(); c.strokeStyle = col; c.lineWidth = 5;
    c.beginPath(); c.roundRect(x - 40, y - 30, 80, 52, 12); c.stroke();
    c.beginPath(); c.moveTo(x - 12, y + 22); c.lineTo(x - 4, y + 38); c.lineTo(x + 6, y + 22); c.stroke();
    c.fillStyle = col;
    for (let i = -1; i <= 1; i++) { c.beginPath(); c.arc(x + i * 18, y - 4, 4, 0, Math.PI * 2); c.fill(); }
    c.restore();
  },
};
