// S09 — "اختار على قد استخدامك وميزانيتك" (dark, 4.59s)
// Usage gauge fills to "just enough"; wallet stays closed — don't pay for unused space.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S09 } from '../captions-s09.js';
import { background, dustField, redCircle, impactRing, shake, flash, techLabel, arText, card, ICONS, clamp, out } from '../lib/ramkit.js';

const DUST = dustField(113);
const GRID = { cell: 64, speed: 8, dir: 'v' };
const IMPACT_T = 1.14, DUR = 4.59;

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'dark', grid: GRID, dust: DUST });
  const zoom = 1 + 0.03 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 7);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'MATCH YOUR NEEDS', { theme: 'dark' });
  redCircle(c, W, H, t, { cx: 540, cy: 820, r: 360, at: 0.05, dur: 0.6 });
  // usage bar fills to exactly "enough" (60%) — no more
  const bp = out(clamp((t - 0.74) / 1.0));
  c.save(); c.globalAlpha = clamp(t / 0.4);
  c.beginPath(); c.roundRect(240, 700, 600, 54, 27); c.fillStyle = C.inkShadow; c.fill();
  c.lineWidth = 3; c.strokeStyle = C.inkSoft; c.stroke();
  if (bp > 0) {
    c.beginPath(); c.roundRect(246, 706, Math.max(42, 588 * 0.6 * bp), 42, 21);
    c.fillStyle = C.red; c.fill();
  }
  // "enough" tick
  c.strokeStyle = C.paper; c.lineWidth = 4;
  c.beginPath(); c.moveTo(240 + 600 * 0.6, 688); c.lineTo(240 + 600 * 0.6, 766); c.stroke();
  c.restore();
  arText(c, 'على قد استخدامك', 540, 640, 44, C.paper, clamp((t - 0.9) / 0.4));
  card(c, 380, 1060, 280, 220, t, 1.74, { theme: 'dark', icon: ICONS.wallet, label: 'ميزانيتك' });
  card(c, 700, 1060, 280, 220, t, 1.14, { theme: 'dark', icon: ICONS.gauge, label: 'استخدامك' });
  // unused space stays dim
  arText(c, 'مساحة مش هتحتاجها = فلوس زيادة', 540, 1290, 34, C.gray3, clamp((t - 3.58) / 0.5));
  impactRing(c, W, H, t, IMPACT_T, { cx: 540, cy: 820, r0: 370 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S09, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.paper, shadow: 'rgba(0,0,0,.8)' });
}

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }
