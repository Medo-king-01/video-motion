// Kinetic demo — the "continuous, beat-locked" vocabulary, in one 4 s loop.
//
// Three ideas, all pure functions of `t` (no cuts, no crossfades, no state between frames):
//   1. lib/beat.js    — the whole scene is locked to 120 BPM: rotation, type scale and the plate's
//                       swipe all read `grid()`/`ping()`, so nothing drifts off the beat.
//   2. lib/space3d.js — a real extruded plate (prism) orbits the camera; the word rides its front
//                       face, so the scene *turns* instead of cutting.
//   3. lib/motion.js  — the fast swipe is blurred with `drawBlurred` from the measured velocity
//                       (displacement = v · shutter), not a fake blur filter.
import { BRAND } from '../lib/brand.js';
import { loadFirstFont } from '../lib/arabic.js';
import { grid, ping, quantize } from '../lib/beat.js';
import { prism, camera, drawMesh, transform } from '../lib/space3d.js';
import { drawBlurred, velocity } from '../lib/motion.js';

const C = BRAND.colors;
const BPM = 120;
const F = '/assets/fonts/';

// a hexagon plate, extruded along z
const PLATE = prism(
  Array.from({ length: 6 }, (_, i) => {
    const a = Math.PI / 6 + (i * Math.PI) / 3;
    return [Math.cos(a) * 150, Math.sin(a) * 150];
  }),
  120,
);
const COLORS = { front: C.red, side: C.redDeep };
const GHOST = { front: C.ink, side: C.inkShadow, back: C.ink };

// the swipe: one quarter-note cycle around the centre. Continuous (no hold, no teleport), and fast
// enough at the crossings — ~880 px/s — for the velocity blur to have something real to smear.
const SLIDE = (t) => 540 + 280 * Math.cos((Math.PI / 2) * grid(t, BPM).pos);

export async function init() {
  for (const f of ['Cairo/Cairo_800ExtraBold.ttf', 'Cairo/Cairo[wght].ttf', 'Cairo/Cairo-Bold.ttf']) {
    try { await loadFirstFont('Cairo', [F + f], { weight: '800' }); break; } catch { /* next file */ }
  }
}

export function draw(ctx, t, { W, H, dur }) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, C.bgDarkTop); g.addColorStop(1, C.bgDarkBottom);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

  const beat = grid(t, BPM);
  // flat technical grid, redrawn every frame (no state): it breathes with the beat
  ctx.save();
  ctx.strokeStyle = 'rgba(139,103,101,0.22)'; ctx.lineWidth = 2;
  for (let x = 90; x < W; x += 90) {
    ctx.beginPath(); ctx.moveTo(x, 260); ctx.lineTo(x, 1340); ctx.stroke();
  }
  ctx.restore();

  // ---- the plate, orbiting: yaw advances per beat, pitch follows the bar phase
  const cam = camera({
    dist: 1500 - 110 * ping(t, BPM),
    yaw: 0.55 + 0.5 * Math.sin(beat.pos * Math.PI / 2),
    pitch: -0.12 + 0.05 * Math.sin(beat.pos * Math.PI / 4),
    fov: 38,
  });
  // a second plate behind, turning the other way: two depths read as space, one reads as a sticker
  drawMesh(ctx, transform(PLATE, { ry: 0.3 - (t / dur) * 1.15, rz: 0.1, scale: 1.22, move: [-70, 30, -260] }),
    cam, W, H, GHOST, { ambient: 0.5, light: [0.3, 0.5, 0.8] });
  const plate = transform(PLATE, {
    ry: 0.5 + (t / dur) * 0.85,               // continuous over the whole loop: it turns, it never cuts
    rz: 0.12 * Math.sin(beat.barPhase * Math.PI * 2),
    scale: 1 + 0.05 * ping(t, BPM, 0, 10),
    move: [0, 40, 0],
  });
  drawMesh(ctx, plate, cam, W, H, COLORS, { ambient: 0.55, light: [0.35, 0.45, 0.85] });

  // ---- kinetic type: on-grid stepped slide, blurred by its own velocity
  const x = SLIDE(t);
  const vx = velocity(SLIDE, t);
  const scale = 1 + 0.16 * ping(t, BPM, 0, 9);
  ctx.save();
  ctx.translate(x, 420);
  ctx.direction = 'rtl'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = C.paper;
  ctx.font = `800 ${Math.round(150 * scale)}px Cairo`;
  drawBlurred(ctx, (c) => c.fillText('حركة', 0, 0), vx, 0, { samples: 5, shutter: 0.06, maxPx: 34 });
  ctx.restore();

  // ---- readouts (real numbers from the same functions, so QA can see the grid)
  ctx.save();
  ctx.direction = 'ltr'; ctx.textAlign = 'left'; ctx.textBaseline = 'middle';
  ctx.font = '400 34px Cairo'; ctx.fillStyle = C.gray4;
  ctx.fillText(`beat ${beat.beat} · phase ${beat.phase.toFixed(2)}`, 90, 1180);
  ctx.fillText(`v ${Math.round(vx)} px/s · grid ${quantize(t, BPM, 4).toFixed(2)}s`, 90, 1232);
  ctx.restore();

  // HUD: progress bar only (brand rule)
  ctx.save();
  ctx.fillStyle = C.gray2; ctx.fillRect(60, 64, W - 120, 6);
  ctx.fillStyle = C.red; ctx.fillRect(60, 64, (W - 120) * Math.min(1, t / dur), 6);
  ctx.restore();
}
