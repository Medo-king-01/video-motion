// Word-by-word Arabic caption renderer (engine K). Timeline values are absolute
// scene-local seconds; the caller supplies MEASURED word onsets/offsets
// (tools/caption_align.py) — this module never estimates timing.
//
// `style` is REQUIRED and must be an explicit, agent-chosen value from
// plan/text-direction.json. There is no default look: omitting it fails loudly.
// All styles render unboxed text in brand colors; boxed/highlight catalog entries
// are intentionally NOT exposed as caption styles.
import { PALETTE } from './brand.js';
import { captionTransform, resolveTextStyle, STYLE_ALIAS } from './caption-motion.js';

export { STYLE_ALIAS, resolveTextStyle };

export function activeWordAt(words, time) {
  if (!Array.isArray(words) || !Number.isFinite(time)) return null;
  let lo = 0, hi = words.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const word = words[mid];
    if (time < word.start) hi = mid - 1;
    else if (time >= word.end) lo = mid + 1;
    else return word;
  }
  return null;
}

export function validateWordTimeline(words) {
  if (!Array.isArray(words)) throw new TypeError('Caption words must be an array');
  let previousEnd = 0;
  for (let i = 0; i < words.length; i++) {
    const word = words[i];
    if (!word || typeof word.text !== 'string' || !word.text.trim()) throw new Error(`Word ${i} has no text`);
    if (!Number.isFinite(word.start) || !Number.isFinite(word.end) || word.start < 0 || word.end <= word.start) {
      throw new Error(`Word ${i} has invalid timing`);
    }
    if (i && word.start < previousEnd) throw new Error(`Word ${i} overlaps or is out of order`);
    previousEnd = word.end;
  }
  return true;
}

function hexToRgb(hex) {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function withAlpha(hex, a) {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r},${g},${b},${a})`;
}

// Karaoke: a right-to-left color sweep across the word over its MEASURED spoken
// duration (no box, no background plate). The lit part uses the brand accent.
function karaokeFill(ctx, text, size, p, accent, base) {
  const tw = ctx.measureText(text).width || size;
  const g = ctx.createLinearGradient(-tw / 2, 0, tw / 2, 0);
  const pos = Math.max(0, Math.min(1, 1 - p));
  const a = Math.max(0, pos - 0.12), b = Math.min(1, pos + 0.12);
  g.addColorStop(0, base);
  if (a > 0) g.addColorStop(a, base);
  if (b < 1) g.addColorStop(b, accent);
  g.addColorStop(1, accent);
  return g;
}

/**
 * Draw the single spoken word active at `time`, unboxed, with a REQUIRED style.
 * Returns the active word (or null). `style` must be chosen by the agent per scene.
 */
export function drawWordCaption(ctx, time, words, {
  W, H, family = 'Cairo', size = 76, y = H * 0.82,
  color = PALETTE.paper, shadow = 'rgba(0,0,0,.72)', weight = 800,
  style, accent = PALETTE.salmon, theme = 'dark',
} = {}) {
  const word = activeWordAt(words, time);
  if (!word) return null;
  const elapsed = Math.max(0, time - word.start);
  const dur = Math.max(0.05, word.end - word.start);
  const m = captionTransform(style, elapsed, dur);
  const tx = m.x * size, ty = m.y * size, blur = m.blur * size;

  ctx.save();
  ctx.globalAlpha = m.opacity;
  ctx.direction = 'rtl';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;
  ctx.shadowColor = shadow;
  ctx.shadowBlur = 18;
  ctx.shadowOffsetY = 3;
  ctx.translate(W / 2 + tx, y + ty);
  ctx.rotate(m.rotate * Math.PI / 180);
  ctx.scale(m.scale, m.scale);
  if (blur > 0.2) ctx.filter = `blur(${blur.toFixed(2)}px)`;

  if (m.karaokeP >= 0) {
    const base = withAlpha(theme === 'dark' ? PALETTE.paper : PALETTE.ink, 0.38);
    const acc = theme === 'dark' ? accent : PALETTE.red;
    ctx.fillStyle = karaokeFill(ctx, word.text, size, m.karaokeP, acc, base);
  } else {
    ctx.fillStyle = color;
  }
  ctx.fillText(word.text, 0, 0, W * 0.88);
  ctx.filter = 'none';

  if (m.underlineP > 0) {
    const tw = Math.min(ctx.measureText(word.text).width, W * 0.88);
    const uw = tw * m.underlineP;
    ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
    ctx.strokeStyle = theme === 'dark' ? accent : PALETTE.red;
    ctx.lineWidth = Math.max(4, size * 0.07);
    ctx.lineCap = 'round';
    ctx.beginPath();
    ctx.moveTo(uw / 2, size * 0.62);
    ctx.lineTo(-uw / 2, size * 0.62);
    ctx.stroke();
  }
  ctx.restore();
  return word;
}
