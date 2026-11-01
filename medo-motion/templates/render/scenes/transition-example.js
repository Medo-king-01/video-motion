// Transition demo (lib/transition.js ← medo-motion/motion/transitions.json).
// Both "scenes" are pre-rendered once into offscreen layers, then the transition composites them —
// exactly how a real edit works: render scene → render scene → cut between them with a mask.
// The same masks exist in engine P (templates/procedural-reels/transition.py).
import { compositeTransition, makeLayer, transitionDuration } from '../lib/transition.js';
import { BRAND } from '../lib/brand.js';
import { loadFirstFont } from '../lib/arabic.js';

const C = BRAND.colors;
const F = '/assets/fonts/';
const ORDER = ['wipe', 'iris', 'checker', 'slide'];
const LAYERS = {};

async function useCairo() {
  for (const f of ['Cairo/Cairo_800ExtraBold.ttf', 'Cairo/Cairo[wght].ttf', 'Cairo/Cairo-Bold.ttf']) {
    try { await loadFirstFont('Cairo', [F + f], { weight: '800' }); break; } catch { /* next file */ }
  }
}

export async function init() {
  await useCairo();
}

// ---------- the two scenes being cut between ----------
function paintA(ctx, W, H) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, C.bgDarkTop); g.addColorStop(1, C.bgDarkBottom);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.red;
  ctx.beginPath(); ctx.arc(W / 2, 880, 320, 0, Math.PI * 2); ctx.fill();
  ctx.direction = 'rtl'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = C.paper; ctx.font = '800 132px Cairo';
  ctx.fillText('قبل', W / 2, 880);
  ctx.fillStyle = C.gray4; ctx.font = '400 34px Cairo';
  ctx.fillText('المشهد الأول', W / 2, 1290);
}

function paintB(ctx, W, H) {
  ctx.fillStyle = C.paper; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.ink;
  ctx.beginPath(); ctx.roundRect(120, 640, W - 240, 480, 40); ctx.fill();
  ctx.strokeStyle = C.red; ctx.lineWidth = 4;
  ctx.beginPath(); ctx.roundRect(120, 640, W - 240, 480, 40); ctx.stroke();
  ctx.direction = 'rtl'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = C.paper; ctx.font = '800 132px Cairo';
  ctx.fillText('بعد', W / 2, 880);
  ctx.fillStyle = C.inkSoft; ctx.font = '400 34px Cairo';
  ctx.fillText('المشهد اللي بعده', W / 2, 1290);
}

function layers(W, H) {
  if (LAYERS.a && LAYERS.w === W && LAYERS.h === H) return LAYERS;
  LAYERS.w = W; LAYERS.h = H;
  LAYERS.a = makeLayer(W, H, ctx => paintA(ctx, W, H));
  LAYERS.b = makeLayer(W, H, ctx => paintB(ctx, W, H));
  return LAYERS;
}

export function draw(ctx, t, { W, H, dur }) {
  const { a, b } = layers(W, H);
  const seg = dur / ORDER.length;
  const i = Math.min(ORDER.length - 1, Math.floor(t / seg));
  const name = ORDER[i];
  // hold the incoming frame for the last 25% of each slot so the cut reads as a cut
  const p = Math.min(1, (t - i * seg) / (seg * 0.75));

  compositeTransition(ctx, a, b, name, p, W, H);
  if (p >= 1) { ctx.drawImage(b, 0, 0); }

  // tag: which transition, on a plate so it reads over both scenes (caption-plate language)
  ctx.save();
  ctx.direction = 'ltr'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.font = '400 28px Cairo';
  const label = `${name} · ${transitionDuration(name)}s`;
  const tw = ctx.measureText(label).width;
  ctx.fillStyle = 'rgba(71,57,56,0.92)';
  ctx.beginPath(); ctx.roundRect(56, 1452, tw + 44, 62, 14); ctx.fill();
  ctx.strokeStyle = C.red; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.roundRect(56, 1452, tw + 44, 62, 14); ctx.stroke();
  ctx.fillStyle = C.paper;
  ctx.fillText(label, 78, 1484);
  ctx.restore();

  // HUD: the progress bar is the only chrome (brand rule)
  ctx.save();
  ctx.fillStyle = C.gray2; ctx.fillRect(60, 64, W - 120, 6);
  ctx.fillStyle = C.red; ctx.fillRect(60, 64, (W - 120) * Math.min(1, t / dur), 6);
  ctx.restore();
}
