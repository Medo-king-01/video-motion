// S04 — "تعالى نعرف تختار كام جيجا!" (light, 2.091s)
// Kinetic question + three capacity chips springing in on "جيجا".
import { PALETTE as C } from '../lib/brand.js';
import { useFonts, family } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S04 } from '../captions-s04.js';
import { background, dustField, redCircle, impactRing, shake, flash, arText, clamp, back } from '../lib/ramkit.js';

const DUST = dustField(63);
const GRID = { cell: 36, speed: 9, dir: 'h' };
const IMPACT_T = 1.36, DUR = 2.091;
const CHIPS = [{ x: 800, at: 1.36, label: '8' }, { x: 540, at: 1.46, label: '16' }, { x: 280, at: 1.56, label: '32' }];

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'light', grid: GRID, dust: DUST });
  const zoom = 1 + 0.04 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 8);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  redCircle(c, W, H, t, { r: 380, cy: 820, at: 0.02, dur: 0.5 });
  const hp = clamp((t - 0.4) / 0.45);
  arText(c, 'كام جيجا؟', 540, 800, 110 * (0.85 + 0.15 * back(hp)), C.paper, hp);
  for (const ch of CHIPS) {
    const p = clamp((t - ch.at) / 0.45); if (!p) continue;
    const e = back(p), s = 0.7 + 0.3 * e;
    c.save(); c.globalAlpha = clamp(p * 2.5);
    c.translate(ch.x, 1150); c.scale(s, s);
    c.beginPath(); c.roundRect(-95, -60, 190, 120, 20);
    c.fillStyle = C.ink; c.fill(); c.lineWidth = 4; c.strokeStyle = C.red; c.stroke();
    c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
    c.font = `800 64px ${family('Inter', 'latin')}`; c.fillStyle = C.paper;
    c.fillText(ch.label, 0, -6);
    c.font = `800 24px ${family('Inter', 'latin')}`; c.fillStyle = C.gray4;
    c.fillText('GB', 0, 36);
    c.restore();
  }
  impactRing(c, W, H, t, IMPACT_T, { cy: 820, r0: 390 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S04, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.ink, shadow: 'rgba(243,242,241,.6)' });
}
