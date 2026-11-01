// Animated icon layer demo (lib/icons.js ← medo-motion/icons/registry.json).
// Shows the six laptop-part icons the explainer uses, brand-locked to palette v2.
import { drawIcon } from '../lib/icons.js';
import { BRAND } from '../lib/brand.js';

const C = BRAND.colors;
const NAMES = ['cpu', 'ram', 'ssd', 'display', 'gpu', 'battery'];
const LABELS = ['المعالج', 'الرامات', 'التخزين', 'الشاشة', 'كارت الشاشة', 'البطارية'];
const ACCENTS = [C.salmon, C.blush, C.gray4, C.salmon, C.blush, C.gray4];

export function draw(ctx, t, { W, H, dur }) {
  const u = Math.min(1, Math.max(0, t / dur));
  ctx.fillStyle = C.bgDarkTop; ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = C.inkShadow; ctx.fillRect(0, H * 0.79, W, H * 0.21);   // dead zone only

  ctx.direction = 'rtl'; ctx.textAlign = 'center';
  ctx.fillStyle = C.paper; ctx.font = '800 64px Cairo';
  ctx.fillText('أيقونات متحركة', W / 2, 320 - (1 - u) * 24);
  ctx.fillStyle = C.gray4; ctx.font = '400 34px Cairo';
  ctx.fillText('من icons/registry.json — نفس الأيقونة في المحركين', W / 2, 386);

  const cols = 3, cw = W / cols, ch = 300, top = 620;
  NAMES.forEach((name, i) => {
    const cx = (i % cols + 0.5) * cw;
    const cy = top + Math.floor(i / cols) * ch;
    const local = t - (0.25 + i * 0.18);            // staggered entrance
    ctx.fillStyle = i % 2 ? C.ink : C.inkShadow;
    ctx.beginPath(); ctx.arc(cx, cy, 116, 0, Math.PI * 2); ctx.fill();
    drawIcon(ctx, name, Math.max(0, local), {
      x: cx, y: cy, size: 128, color: C.paper, accent: ACCENTS[i], loop: false,
    });
    ctx.fillStyle = C.paper; ctx.font = '700 40px Cairo';
    ctx.fillText(LABELS[i], cx, cy + 176);
  });

  // progress line: the reel's only HUD element
  ctx.fillStyle = C.gray2; ctx.fillRect(60, 64, W - 120, 6);
  ctx.fillStyle = C.red; ctx.fillRect(60, 64, (W - 120) * u, 6);
}
