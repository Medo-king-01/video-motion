// S01 — three consistent RAM modules on the brand red-circle backdrop.
// Approved background (brand v2.6): mesh_dark + grid_dark + 30 dust particles.
// Depth: red-circle backdrop + 3D modules + parallax dust + drop shadows.
// Motion: spring reveals (back-out), breathing circle, drifting grid/dust,
//         slow camera push, one impact (ring + speed lines + shake + flash).
// Reveal times are provisional editorial beats — refine against word alignment.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts, family } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S01 } from '../captions-s01.js';

const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const out = p => 1 - Math.pow(1 - clamp(p), 3);
const back = p => { const c1 = 1.70158, c3 = c1 + 1; p = clamp(p); return 1 + c3 * Math.pow(p - 1, 3) + c1 * Math.pow(p - 1, 2); };

// Deterministic dust field (30 particles, brand rule). Pure data, seeded once.
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
const DUST = (() => { const r = rng(31); const a = []; for (let i = 0; i < 30; i++) a.push({ x: r() * 1080, y: r() * 1920, z: 0.35 + r() * 0.65, s: 1 + r() * 2.4, ph: r() * Math.PI * 2, sp: 6 + r() * 16 }); return a; })();

const MODS = [ { x: 820, at: 1.2, label: '8GB' }, { x: 540, at: 4.4, label: '16GB' }, { x: 260, at: 7.6, label: '32GB' } ];
const IMPACT_T = 8.15, SCAN_T = 9.7, SCENE_END = 12.358;

function rr(c, x, y, w, h, r) { c.beginPath(); c.roundRect(x, y, w, h, r); }
function poly(c, p, color) { c.beginPath(); c.moveTo(...p[0]); for (let i = 1; i < p.length; i++) c.lineTo(...p[i]); c.closePath(); c.fillStyle = color; c.fill(); }

export async function init() { await useFonts([['Inter', 800], ['Inter', 400], ['Cairo', 800]]); }

// Approved mesh_dark + grid_dark + 30 dust (brand.json backgrounds.v2_6_specs).
function background(c, W, H, t) {
  const g = c.createLinearGradient(W * 0.55, 0, W * 0.45, H); // ~185deg
  g.addColorStop(0, C.ink); g.addColorStop(1, C.inkShadow);
  c.fillStyle = g; c.fillRect(0, 0, W, H);
  const glow = c.createRadialGradient(W * 0.5, H * 0.35, 20, W * 0.5, H * 0.35, W * 0.62);
  glow.addColorStop(0, 'rgba(203,39,27,0.08)'); glow.addColorStop(1, 'rgba(203,39,27,0)');
  c.fillStyle = glow; c.fillRect(0, 0, W, H);
  // grid_dark: gray_2 8%, 40px cell, slow vertical drift
  c.save(); c.strokeStyle = 'rgba(201,197,194,0.08)'; c.lineWidth = 1;
  const off = (t * 5) % 40;
  for (let x = 0; x <= W; x += 40) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, H); c.stroke(); }
  for (let y = -40 + off; y < H + 40; y += 40) { c.beginPath(); c.moveTo(0, y); c.lineTo(W, y); c.stroke(); }
  c.restore();
  // 30 dust particles, parallax drift (deeper = slower + dimmer)
  c.save();
  for (const p of DUST) {
    let y = (p.y - t * p.sp * p.z) % (H + 40); if (y < 0) y += H + 40;
    const x = p.x + Math.sin(t * 0.4 + p.ph) * 10 * p.z;
    c.globalAlpha = 0.05 + 0.10 * p.z; c.fillStyle = C.gray2;
    c.beginPath(); c.arc(x, y, p.s * p.z, 0, Math.PI * 2); c.fill();
  }
  c.restore();
}

// Brand signature #1: big red circle behind the hero, breathing + smooth entrance.
function redCircle(c, W, H, t) {
  const p = clamp((t - 0.15) / 0.9); if (!p) return;
  const e = out(p), breathe = 1 + 0.018 * Math.sin(t * 0.9);
  const R = 440 * (0.82 + 0.18 * e) * breathe, cx = W * 0.5, cy = 900;
  c.save(); c.globalAlpha = e;
  const g = c.createRadialGradient(cx - 70, cy - 90, 40, cx, cy, R);
  g.addColorStop(0, C.red); g.addColorStop(1, C.redDeep);
  c.fillStyle = g; c.beginPath(); c.arc(cx, cy, R, 0, Math.PI * 2); c.fill();
  c.restore();
}

// One consistent RAM module design; only the capacity label varies.
function module(c, cx, cy, t, at, label) {
  const p = clamp((t - at) / 0.72); if (!p) return;
  const e = back(p), a = clamp(p * 2.2), s = 0.8 + 0.2 * e, rise = 90 * (1 - out(p));
  const bob = Math.sin(t * 1.3 + cx * 0.01) * 4 * clamp((t - at - 0.72) / 0.5);
  const w = 154, h = 570, x = cx - w / 2, y = cy - h / 2 + rise + bob;
  c.save(); c.globalAlpha = a;
  c.translate(cx, cy + rise + bob); c.scale(s, s); c.translate(-cx, -cy - rise - bob);
  // drop shadow on the circle
  c.save(); c.globalAlpha = a * 0.28; c.fillStyle = C.inkShadow;
  c.beginPath(); c.ellipse(cx, y + h + 20, w * 0.55, 15, 0, 0, Math.PI * 2); c.fill(); c.restore();
  // 3D side faces
  poly(c, [[x + w, y + 18], [x + w + 18, y + 8], [x + w + 18, y + h - 20], [x + w, y + h]], C.inkShadow);
  poly(c, [[x + 9, y], [x + w, y + 18], [x + w + 18, y + 8], [x + 26, y - 10]], C.inkSoft);
  rr(c, x, y, w, h, 12); c.fillStyle = C.ink; c.fill(); c.lineWidth = 5; c.strokeStyle = C.inkSoft; c.stroke();
  c.fillStyle = C.gray3;
  for (let i = 0; i < 6; i++) { const yy = y + 62 + i * 72; rr(c, x + 29, yy, 96, 48, 7); c.fill(); c.fillStyle = C.gray1; rr(c, x + 39, yy + 9, 76, 30, 4); c.fill(); c.fillStyle = C.gray3; }
  c.fillStyle = C.inkShadow; rr(c, x + 57, y - 3, 42, 16, 5); c.fill();
  for (let i = 0; i < 9; i++) { rr(c, x + 12 + i * 15, y + h - 34, 9, 28, 2); c.fillStyle = i % 2 ? C.gray1 : C.blush; c.fill(); }
  c.fillStyle = C.red; rr(c, x + w - 9, y + 38, 5, 86, 2); c.fill();
  c.restore();
  // capacity label — paper for contrast on the red circle
  c.save(); c.globalAlpha = a; c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
  c.font = `800 72px ${family('Inter', 'latin')}`; c.fillStyle = C.paper; c.fillText(label, cx, y - 68); c.restore();
}

// One impact per scene: expanding ring + speed lines (shake + flash handled in draw).
function impact(c, W, H, t) {
  const p = clamp((t - IMPACT_T) / 0.5); if (!p || p >= 1) return;
  const cx = W * 0.5, cy = 900;
  c.save();
  c.globalAlpha = (1 - p) * 0.8; c.strokeStyle = C.paper; c.lineWidth = 6 * (1 - p) + 2;
  c.beginPath(); c.arc(cx, cy, 450 + 180 * out(p), 0, Math.PI * 2); c.stroke();
  c.globalAlpha = (1 - p) * 0.6; c.lineWidth = 3;
  for (let i = 0; i < 12; i++) { const ang = i / 12 * Math.PI * 2, r0 = 480 + 120 * out(p), r1 = r0 + 40 * (1 - p);
    c.beginPath(); c.moveTo(cx + Math.cos(ang) * r0, cy + Math.sin(ang) * r0); c.lineTo(cx + Math.cos(ang) * r1, cy + Math.sin(ang) * r1); c.stroke(); }
  c.restore();
}

// Subtle white scan sweep across the modules near the end.
function scan(c, W, H, t) {
  const p = clamp((t - SCAN_T) / 1.2); if (!p || p >= 1) return;
  const x = -100 + 1280 * out(p);
  const g = c.createLinearGradient(x - 60, 0, x + 60, 0);
  g.addColorStop(0, 'rgba(243,242,241,0)'); g.addColorStop(0.5, 'rgba(243,242,241,0.30)'); g.addColorStop(1, 'rgba(243,242,241,0)');
  c.fillStyle = g; c.fillRect(x - 60, 500, 120, 800);
}

export function draw(c, t, { W, H }) {
  background(c, W, H, t); // fixed backdrop fills the frame
  // camera push + impact shake on the foreground (parallax over the fixed backdrop)
  const zoom = 1 + 0.04 * clamp(t / SCENE_END);
  let shx = 0, shy = 0; const ip = clamp((t - IMPACT_T) / 0.3);
  if (ip > 0 && ip < 1) { const amp = 9 * (1 - ip); shx = Math.sin(t * 90) * amp; shy = Math.cos(t * 77) * amp; }
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  // top technical label
  c.save(); c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
  c.font = `800 30px ${family('Inter', 'latin')}`; c.fillStyle = C.gray4;
  c.globalAlpha = clamp(t / 0.6); c.fillText('MEMORY CAPACITY', W / 2, 310); c.restore();
  redCircle(c, W, H, t);
  for (const m of MODS) module(c, m.x, 925, t, m.at, m.label);
  impact(c, W, H, t);
  scan(c, W, H, t);
  c.restore();
  // 2-frame flash at the impact
  if (t >= IMPACT_T && t < IMPACT_T + 2 / 30) { c.fillStyle = 'rgba(243,242,241,0.45)'; c.fillRect(0, 0, W, H); }
  drawWordCaption(c, t, CAPTIONS_S01, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.paper, shadow: 'rgba(0,0,0,.8)' });
}
