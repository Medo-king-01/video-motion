// Arabic smoke test: whole-word pops, a right→left typewriter wipe, safe dots. Absolute time only.
import { ARABIC_FONT } from '../data.js';
import { loadFirstFont, setArabic, layoutWords, inkBox, wipeReveal, clamp01, easeOutCubic, easeOutExpo } from '../lib/arabic.js';

let family = 'sans-serif';
export async function init() {
  family = (await loadFirstFont(ARABIC_FONT.family, ARABIC_FONT.urls)) || 'sans-serif';
}

// Brand palette (brand/brand.json): dark bg + red + warm white.
const BG = '#100F13', CREAM = '#F6F3ED', RED = '#E5262B';

export function draw(ctx, t, { W, H }) {
  ctx.fillStyle = BG; ctx.fillRect(0, 0, W, H);

  // Line 1: words pop in one by one, right to left, never split into letters.
  setArabic(ctx, { family, size: 150, weight: 900 });
  const words = layoutWords(ctx, 'عربي متصل صح', { x: W / 2, y: H * 0.40, maxWidth: W * 0.84, lineHeight: 1.5 });
  ctx.textAlign = 'center';
  words.forEach((w, i) => {
    const p = clamp01((t - 0.15 - i * 0.18) / 0.3);
    if (p <= 0) return;
    const s = 1.35 - 0.35 * easeOutExpo(p);
    ctx.save();
    ctx.globalAlpha = Math.min(1, p * 1.6);
    ctx.translate(w.x, w.y); ctx.scale(s, s);
    ctx.fillStyle = CREAM; ctx.fillText(w.text, 0, 0);
    ctx.restore();
  });

  // Line 2: typewriter feel by a clip that grows from the right edge; the shaped line stays whole.
  setArabic(ctx, { family, size: 96, weight: 700 });
  const line = 'والباقي علينا', lx = W / 2, ly = H * 0.53;
  const box = inkBox(ctx, line, lx, ly);
  const bar = inkBox(ctx, line, lx, ly, 0.3);                      // roomier box for the highlight bar
  const reveal = easeOutCubic((t - 1.1) / 1.4);
  if (reveal > 0) {
    ctx.fillStyle = RED;                                            // the bar sweeps right→left with the text
    ctx.fillRect(bar.x + bar.w * (1 - reveal), bar.y, bar.w * reveal, bar.h);
    ctx.fillStyle = CREAM;
    wipeReveal(ctx, () => ctx.fillText(line, lx, ly), box, reveal, { cursor: CREAM });
  }

  // Small Latin label far from the Arabic ink (decorative marks keep ≥ 0.4 em distance).
  ctx.direction = 'ltr'; ctx.textAlign = 'center';
  ctx.font = '500 28px "JetBrains Mono", monospace'; ctx.fillStyle = CREAM;
  ctx.globalAlpha = clamp01((t - 2.6) / 0.4);
  ctx.fillText('ARABIC SHAPING TEST', W / 2, H * 0.66);
  ctx.globalAlpha = 1;
}
