// S03 — "ببساطة، الـ RAM هي الذاكرة المؤقتة..." (dark, 7.593s)
// One module center; programs feed data packets in, work flows out. Temporary-memory motif.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S03 } from '../captions-s03.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, clamp, out, rng } from '../lib/ramkit.js';

const DUST = dustField(59);
const GRID = { cell: 48, speed: -6, dir: 'v' };
const IMPACT_T = 1.44, DUR = 7.593;
const R = rng(77);
const PKT = Array.from({ length: 10 }, (_, i) => ({ ph: i / 10, sp: 0.55 + R() * 0.3, lane: (i % 3 - 1) * 46 }));

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'dark', grid: GRID, dust: DUST });
  const zoom = 1 + 0.035 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 8);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'TEMPORARY MEMORY', { theme: 'dark' });
  redCircle(c, W, H, t, { r: 400, at: 0.05, dur: 0.8 });
  // side nodes: programs (right, RTL reading) -> RAM -> active work (left)
  const nodeA = clamp((t - 4.36) / 0.5), nodeB = clamp((t - 6.06) / 0.5);
  c.save(); c.globalAlpha = nodeA; c.strokeStyle = C.salmon; c.lineWidth = 4;
  c.beginPath(); c.roundRect(880, 760, 120, 90, 12); c.stroke();
  c.lineWidth = 3; for (let i = 0; i < 3; i++) { c.beginPath(); c.moveTo(898, 786 + i * 20); c.lineTo(982, 786 + i * 20); c.stroke(); }
  c.restore();
  arText(c, 'البرامج', 940, 900, 34, C.gray3, nodeA);
  c.save(); c.globalAlpha = nodeB; c.strokeStyle = C.salmon; c.lineWidth = 4;
  c.beginPath(); c.roundRect(80, 760, 120, 90, 12); c.stroke();
  c.beginPath(); c.moveTo(100, 822); c.lineTo(128, 796); c.lineTo(150, 812); c.lineTo(180, 780); c.stroke();
  c.restore();
  arText(c, 'البيانات', 140, 900, 34, C.gray3, nodeB);
  // data packets streaming right->left through the module while "بيستخدمها" is spoken
  const flow = clamp((t - 3.44) / 0.6);
  if (flow > 0) {
    c.save(); c.globalAlpha = flow;
    for (const p of PKT) {
      const u = ((t * p.sp + p.ph) % 1);
      const x = 900 - u * 720, y = 805 + p.lane * Math.sin(u * Math.PI);
      const near = Math.abs(x - 540) < 90;
      c.fillStyle = near ? C.paper : C.salmon;
      c.globalAlpha = flow * (0.35 + 0.65 * Math.sin(u * Math.PI));
      c.beginPath(); c.roundRect(x - 9, y - 9, 18, 18, 4); c.fill();
    }
    c.restore();
  }
  module(c, 540, 900, t, 0.35, 'RAM', { scale: 0.95, labelColor: C.paper });
  arText(c, 'الذاكرة المؤقتة', 540, 1290, 44, C.salmon, clamp((t - 2.2) / 0.5));
  impactRing(c, W, H, t, IMPACT_T, { r0: 410 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S03, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.paper, shadow: 'rgba(0,0,0,.8)' });
}
