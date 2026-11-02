// S08 — "مش معنى إن 32 جيجا أكبر إنها الاختيار الأفضل للجميع" (light, 4.941s)
// 32GB module grows, then a clear "bigger ≠ better for everyone" statement.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts, family } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S08 } from '../captions-s08.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, clamp, out } from '../lib/ramkit.js';

const DUST = dustField(103);
const GRID = { cell: 40, speed: -5, dir: 'h' };
const IMPACT_T = 3.16, DUR = 4.941;

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'light', grid: GRID, dust: DUST });
  const zoom = 1 + 0.03 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 7);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'BIGGER IS NOT ALWAYS BETTER', { theme: 'light' });
  redCircle(c, W, H, t, { cx: 540, cy: 760, r: 330, at: 0.05, dur: 0.7 });
  // "أكبر" emphasis comes from the impact ring + shake; module stays put so its label never leaves the circle
  module(c, 540, 760, t, 0.6, '32GB', { scale: 0.85 });
  // the statement: أكبر ≠ الأفضل للجميع
  const sp = clamp((t - 3.7) / 0.5);
  if (sp > 0) {
    arText(c, 'أكبر ≠ الأفضل للجميع', 540, 1230, 54, C.ink, sp);
    c.save(); c.globalAlpha = sp; c.strokeStyle = C.red; c.lineWidth = 6; c.lineCap = 'round';
    const uw = 460 * out(sp);
    c.beginPath(); c.moveTo(540 - uw / 2, 1282); c.lineTo(540 + uw / 2, 1282); c.stroke();
    c.restore();
  }
  impactRing(c, W, H, t, IMPACT_T, { cx: 540, cy: 760, r0: 340 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S08, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.ink, shadow: 'rgba(243,242,241,.6)' });
}
