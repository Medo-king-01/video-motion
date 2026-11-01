// Presenter demo (lib/presenter.js ← assets/poses/poses.json).
// Shows the three things that make still poses act: idle motion, cross-faded pose changes and
// ground-line placement. Engine P draws the same poses from presenter.py.
import { PoseTrack, loadPoses } from '../lib/presenter.js';
import { BRAND } from '../lib/brand.js';
import { loadFirstFont } from '../lib/arabic.js';

const C = BRAND.colors;
const F = '/assets/fonts/';

// One cue per beat: greet → explain → point
const ACT = new PoseTrack([
  { t: 0.0, pose: 'neutral' },
  { t: 0.45, pose: 'welcome' },
  { t: 1.5, pose: 'explain' },
  { t: 2.45, pose: 'point' },
]);

export async function init() {
  for (const f of ['Cairo/Cairo_800ExtraBold.ttf', 'Cairo/Cairo[wght].ttf', 'Cairo/Cairo-Bold.ttf']) {
    try { await loadFirstFont('Cairo', [F + f], { weight: '800' }); break; } catch { /* next file */ }
  }
  await loadPoses('/assets/poses/');
}

export function draw(ctx, t, { W, H, dur }) {
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, C.bgDarkTop); g.addColorStop(1, C.bgDarkBottom);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

  // the brand circle behind him, so the cut-out reads against something
  ctx.fillStyle = C.red;
  ctx.beginPath(); ctx.arc(W / 2, 780, 330, 0, Math.PI * 2); ctx.fill();

  ACT.draw(ctx, t, { height: 0.62, x: 0.5 });

  // pose tag + caption plate
  const state = ACT.at(t);
  ctx.save();
  ctx.direction = 'ltr'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  const label = `pose · ${state.pose}`;
  ctx.font = '400 30px Cairo';
  const tw = ctx.measureText(label).width;
  ctx.fillStyle = 'rgba(71,57,56,0.92)';
  ctx.beginPath(); ctx.roundRect(W / 2 - tw / 2 - 24, 1452, tw + 48, 64, 14); ctx.fill();
  ctx.strokeStyle = C.red; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.roundRect(W / 2 - tw / 2 - 24, 1452, tw + 48, 64, 14); ctx.stroke();
  ctx.fillStyle = C.paper; ctx.fillText(label, W / 2, 1484);
  ctx.restore();

  ctx.save();
  ctx.fillStyle = C.gray2; ctx.fillRect(60, 64, W - 120, 6);
  ctx.fillStyle = C.red; ctx.fillRect(60, 64, (W - 120) * Math.min(1, t / dur), 6);
  ctx.restore();
}
