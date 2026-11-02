// S05 — "أولًا: 8 جيجا..." (dark, 11.398s) — light-use workload cards on spoken words.
import { PALETTE as C } from '../lib/brand.js';
import { useFonts, family } from '../lib/fonts.js';
import { drawWordCaption } from '../lib/captions.js';
import { CAPTIONS_S05 } from '../captions-s05.js';
import { background, dustField, redCircle, module, impactRing, shake, flash, techLabel, arText, card, ICONS, clamp } from '../lib/ramkit.js';

const DUST = dustField(71);
const GRID = { cell: 44, speed: 6, dir: 'v' };
const IMPACT_T = 1.4, DUR = 11.398;
// Reveals measured to the spoken words (scene-local):
// التصفح 4.38 · والدراسة 5.24 · Office 6.34 · الخفيفة 7.84
const CARDS = [
  { x: 250, y: 640, at: 4.38, icon: ICONS.browser, label: 'التصفح' },
  { x: 530, y: 640, at: 5.24, icon: ICONS.book, label: 'الدراسة' },
  { x: 250, y: 900, at: 6.34, icon: ICONS.doc, label: 'Office' },
  { x: 530, y: 900, at: 7.84, icon: ICONS.feather, label: 'برامج خفيفة' },
];

export async function init() { await useFonts([['Inter', 800], ['Cairo', 800]]); }

export function draw(c, t, { W, H }) {
  background(c, W, H, t, { theme: 'dark', grid: GRID, dust: DUST });
  const zoom = 1 + 0.035 * clamp(t / DUR);
  const [shx, shy] = shake(t, IMPACT_T, 8);
  c.save();
  c.translate(W / 2 + shx, H / 2 + shy); c.scale(zoom, zoom); c.translate(-W / 2, -H / 2);
  techLabel(c, W, t, 'LIGHT USE', { theme: 'dark' });
  redCircle(c, W, H, t, { cx: 850, cy: 880, r: 300, at: 0.1, dur: 0.7 });
  module(c, 850, 880, t, 0.7, '8GB', { scale: 0.9 });
  arText(c, 'الاستخدام البسيط', 390, 430, 46, C.salmon, clamp((t - 3.54) / 0.5));
  for (const k of CARDS) card(c, k.x, k.y, 250, 220, t, k.at, { theme: 'dark', icon: k.icon, label: k.label });
  // limited open apps: three small windows + cap line at "محدود"
  const lp = clamp((t - 9.06) / 0.5);
  if (lp > 0) {
    c.save(); c.globalAlpha = lp;
    for (let i = 0; i < 3; i++) {
      c.strokeStyle = C.gray4; c.lineWidth = 3;
      c.beginPath(); c.roundRect(180 + i * 60, 1120 + i * 14, 150, 96, 8); c.stroke();
    }
    c.restore();
    arText(c, 'عدد محدود في نفس الوقت', 390, 1310, 32, C.gray3, lp);
  }
  impactRing(c, W, H, t, IMPACT_T, { cx: 850, cy: 880, r0: 310 });
  c.restore();
  flash(c, W, H, t, IMPACT_T);
  drawWordCaption(c, t, CAPTIONS_S05, { W, H, family: 'Cairo', size: 76, y: 1455, color: C.paper, shadow: 'rgba(0,0,0,.8)' });
}
