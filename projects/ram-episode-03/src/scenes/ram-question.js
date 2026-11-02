// S02 — "بس يا ترى إيه الفرق؟ وأنهي حجم مناسب لاستخدامك؟" (light, 3.925s)
// Three identical modules + big question; spotlight sweep asks "which one fits you".
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S02 } from '../captions-s02.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, clamp, out } from '../lib/ramkit.js';

const DUST = dustField(47);
const GRID = { cell: 56, speed: 7, dir: 'h' };
const IMPACT_T = 1.1, DUR = 3.925;

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'light', grid: GRID, dust: DUST });
  const zoom = 1 + 0.03 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 7);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'WHICH SIZE FITS YOU?', { theme: 'light' });
  redCircle(c, W, H, t, { r: 430, at: 0.05, dur: 0.7 });
  // big question mark behind modules
  c.save(); c.globalAlpha = 0.9 * clamp((t - 0.3) / 0.5);
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.direction = 'ltr';
  c.font = '800 140px "Inter", sans-serif'; c.fillStyle = C.paper;
  c.fillText('?', W / 2, 550); c.restore();
  // identical modules, only labels differ
  module(c, 780, 950, t, 0.55, '8GB', { scale: 0.82 });
  module(c, 540, 950, t, 0.75, '16GB', { scale: 0.82 });
  module(c, 300, 950, t, 0.95, '32GB', { scale: 0.82 });
  // spotlight sweep across the three at "لاستخدامك"
  const sp = clamp((t - 2.98) / 0.85);
  if (sp > 0 && sp < 1) {
    const x = 920 - 740 * out(sp);
    const g = c.createLinearGradient(x - 90, 0, x + 90, 0);
    g.addColorStop(0, 'rgba(243,242,241,0)'); g.addColorStop(0.5, 'rgba(243,242,241,0.35)'); g.addColorStop(1, 'rgba(243,242,241,0)');
    c.fillStyle = g; c.fillRect(x - 90, 620, 180, 660);
  }
  impactRing(c, W, H, t, IMPACT_T, { r0: 440 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S02, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.ink, shadow: 'rgba(243,242,241,.6)' });
}
