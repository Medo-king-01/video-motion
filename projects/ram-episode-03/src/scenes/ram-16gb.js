// S06 — "ثانيًا: 16 جيجا... الاختيار المتوازن" (light, 11.814s) — balanced choice + multitask cards.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S06 } from '../captions-s06.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, card, ICONS, clamp, out } from '../lib/ramkit.js';

const DUST = dustField(83);
const GRID = { cell: 60, speed: -8, dir: 'h' };
const IMPACT_T = 0.88, DUR = 11.814;
// لتعدد المهام 5.94 · والبرمجة 6.82 · والتصميم 7.84 · والمونتاج 8.54
const CARDS = [
  { x: 300, y: 1090, at: 5.94, icon: ICONS.multitask, label: 'تعدد المهام' },
  { x: 780, y: 1090, at: 6.82, icon: ICONS.code, label: 'البرمجة' },
  { x: 300, y: 1268, at: 7.84, icon: ICONS.pen, label: 'التصميم' },
  { x: 780, y: 1268, at: 8.54, icon: ICONS.film, label: 'المونتاج' },
];

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'light', grid: GRID, dust: DUST });
  const zoom = 1 + 0.035 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 8);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'THE BALANCED CHOICE', { theme: 'light' });
  redCircle(c, W, H, t, { cx: 540, cy: 700, r: 260, at: 0.05, dur: 0.7 });
  module(c, 540, 700, t, 0.54, '16GB', { scale: 0.66 });
  arText(c, 'الاختيار المتوازن', 540, 390, 52, C.ink, clamp((t - 3.32) / 0.5));
  arText(c, 'لمعظم المستخدمين', 540, 985, 36, C.inkSoft, clamp((t - 4.24) / 0.5));
  for (const k of CARDS) card(c, k.x, k.y, 300, 156, t, k.at, { theme: 'light', icon: k.icon, label: k.label });
  impactRing(c, W, H, t, IMPACT_T, { cx: 540, cy: 700, r0: 270 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S06, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.ink, shadow: 'rgba(243,242,241,.6)' });
}
