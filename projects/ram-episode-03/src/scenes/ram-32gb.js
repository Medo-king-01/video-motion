// S07 — "ثالثًا: 32 جيجا... شغلك تقيل" (dark, 12.215s) — heavy-workload cards.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S07 } from '../captions-s07.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, card, ICONS, clamp } from '../lib/ramkit.js';

const DUST = dustField(97);
const GRID = { cell: 52, speed: 7, dir: 'v' };
const IMPACT_T = 1.5, DUR = 12.215;
// ثلاثي الأبعاد 5.06 · والمشاريع البرمجية 5.96 · وبيئات عمل كتير 8.72
const CARDS = [
  { x: 330, y: 560, at: 5.06, icon: ICONS.cube, label: 'تصميم ثلاثي الأبعاد' },
  { x: 330, y: 830, at: 5.96, icon: ICONS.stack, label: 'مشاريع برمجية كبيرة' },
  { x: 330, y: 1100, at: 8.72, icon: ICONS.layers, label: 'بيئات عمل كتير' },
];

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'dark', grid: GRID, dust: DUST });
  const zoom = 1 + 0.035 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 9);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'HEAVY WORKLOADS', { theme: 'dark' });
  redCircle(c, W, H, t, { cx: 850, cy: 880, r: 300, at: 0.1, dur: 0.7 });
  module(c, 850, 880, t, 0.64, '32GB', { scale: 0.9 });
  arText(c, 'لو شغلك تقيل', 850, 480, 46, C.salmon, clamp((t - 3.52) / 0.5));
  for (const k of CARDS) card(c, k.x, k.y, 400, 220, t, k.at, { theme: 'dark', icon: k.icon, label: k.label });
  arText(c, 'اختيار أنسب', 850, 1300, 40, C.paper, clamp((t - 11.52) / 0.4));
  impactRing(c, W, H, t, IMPACT_T, { cx: 850, cy: 880, r0: 310 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S07, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.paper, shadow: 'rgba(0,0,0,.8)' });
}
