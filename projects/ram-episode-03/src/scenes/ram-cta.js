// S10 — "دلوقتي قولي: أنت شايف جهازك محتاج كام جيجا RAM؟" (light, 3.52s)
// Closing question: three identical modules + comment prompt. No logo/series text.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S10 } from '../captions-s10.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, arText, card, ICONS, clamp } from '../lib/ramkit.js';

const DUST = dustField(127);
const GRID = { cell: 48, speed: -7, dir: 'h' };
const IMPACT_T = 2.74, DUR = 3.52;

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'light', grid: GRID, dust: DUST });
  const zoom = 1 + 0.04 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 8);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  redCircle(c, W, H, t, { cx: 540, cy: 860, r: 420, at: 0.02, dur: 0.6 });
  module(c, 800, 900, t, 0.3, '8GB', { scale: 0.72 });
  module(c, 540, 900, t, 0.42, '16GB', { scale: 0.72 });
  module(c, 280, 900, t, 0.54, '32GB', { scale: 0.72 });
  arText(c, 'جهازك محتاج كام جيجا؟', 540, 400, 60, C.ink, clamp((t - 0.5) / 0.5));
  card(c, 540, 1270, 340, 150, t, 0.86, { theme: 'light', icon: ICONS.chat, label: 'قولي في التعليقات', accent: true });
  impactRing(c, W, H, t, IMPACT_T, { cx: 540, cy: 860, r0: 430 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S10, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.ink, shadow: 'rgba(243,242,241,.6)' });
}
