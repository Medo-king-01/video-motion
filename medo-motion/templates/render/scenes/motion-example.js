// Motion grammar demo (lib/motion.js ← medo-motion/motion/easings.json).
// Everything on screen is driven by a keyframe timeline — the same JSON runs in engine P via motion.py.
// In a real project, keep the timeline next to the brief: assets/timelines/<scene>.json and fetch it in init().
import { timeline, ease, progress } from '../lib/motion.js';
import { BRAND } from '../lib/brand.js';
import { loadFirstFont } from '../lib/arabic.js';

const C = BRAND.colors;
const F = '/assets/fonts/';

const SPEC = {
  duration: 2.6,
  tracks: {
    'card.y': [{ t: 0, v: 300 }, { t: 0.8, v: 0, ease: 'spring' }],
    'card.scale': [{ t: 0, v: 0.84 }, { t: 0.7, v: 1, ease: 'backOut' }],
    'card.opacity': [{ t: 0, v: 0 }, { t: 0.3, v: 1, ease: 'easeOut' }],
    'card.rotate': [{ t: 0, v: -5 }, { t: 0.9, v: 0, ease: 'easeInOut' }],
    'bar.width': [{ t: 0.4, v: 0 }, { t: 1.4, v: 520, ease: 'circOut' }],
    'title.opacity': [{ t: 0.55, v: 0 }, { t: 1.0, v: 1, ease: 'easeOut' }],
  },
};

const tl = timeline(SPEC);

export async function init() {
  for (const f of ['Cairo/Cairo_800ExtraBold.ttf', 'Cairo/Cairo[wght].ttf', 'Cairo/Cairo-Bold.ttf']) {
    try { await loadFirstFont('Cairo', [F + f], { weight: '800' }); break; } catch { /* next file */ }
  }
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export function draw(ctx, t, { W, H, dur }) {
  const v = tl.at(Math.min(t, tl.duration));

  // background: palette v2, no new colours
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, C.bgDarkTop);
  g.addColorStop(1, C.bgDarkBottom);
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);

  // hero circle (the brand signature) breathes with the same ease as the card
  const circleIn = ease('backOut', progress(t, 0.05, 0.6));
  ctx.fillStyle = C.red;
  ctx.beginPath(); ctx.arc(W / 2, 840, 300 * circleIn, 0, Math.PI * 2); ctx.fill();

  // card driven entirely by the timeline
  ctx.save();
  ctx.globalAlpha = v['card.opacity'];
  ctx.translate(W / 2, 840 + v['card.y']);
  ctx.rotate((v['card.rotate'] * Math.PI) / 180);
  ctx.scale(v['card.scale'], v['card.scale']);
  const cw = 720, ch = 300;
  ctx.fillStyle = C.ink;
  ctx.shadowColor = 'rgba(46,36,35,0.45)'; ctx.shadowBlur = 48; ctx.shadowOffsetY = 20;
  roundRect(ctx, -cw / 2, -ch / 2, cw, ch, 28); ctx.fill();
  ctx.shadowColor = 'transparent';
  ctx.strokeStyle = C.red; ctx.lineWidth = 3;   // same language as the caption plate
  roundRect(ctx, -cw / 2, -ch / 2, cw, ch, 28); ctx.stroke();

  ctx.direction = 'rtl'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillStyle = C.paper; ctx.font = '800 52px Cairo';
  ctx.globalAlpha = v['card.opacity'] * v['title.opacity'];
  ctx.fillText('الحركة بقت أرقام', 0, -46);
  ctx.fillStyle = C.gray4; ctx.font = '400 30px Cairo';
  ctx.fillText('keyframes + springs · JSON واحد للمحركين', 0, 14);

  // accent bar (drawn width from the timeline)
  ctx.globalAlpha = v['card.opacity'];
  ctx.fillStyle = C.gray2; roundRect(ctx, -210, 78, 420, 10, 5); ctx.fill();
  ctx.fillStyle = C.red; roundRect(ctx, -210, 78, Math.max(10, v['bar.width'] * 0.808), 10, 5); ctx.fill();
  ctx.restore();

  // footer note + HUD progress (brand rule: progress bar is the only HUD)
  ctx.globalAlpha = 1; ctx.textAlign = 'center';
  ctx.fillStyle = C.gray4; ctx.font = '400 28px Cairo';
  ctx.fillText('medo-motion/motion · ease · spring · timeline', W / 2, 1290);
  ctx.fillStyle = C.gray2; ctx.fillRect(60, 64, W - 120, 6);
  ctx.fillStyle = C.red; ctx.fillRect(60, 64, (W - 120) * Math.min(1, t / dur), 6);
}
