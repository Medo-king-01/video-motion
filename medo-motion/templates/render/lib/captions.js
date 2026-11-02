// Word-by-word Arabic caption renderer (engine K). Timeline values are absolute
// scene-local seconds; the caller supplies MEASURED word onsets/offsets
// (tools/caption_align.py) — this module never estimates timing.
//
// `style` selects an optional entrance from the studio text-animation catalog
// (medo-motion/motion/text-animations.json -> lib/caption-styles.js). The default
// 'pop' reproduces the original brand-safe behaviour exactly. All styles render
// unboxed text in brand colors; boxed/highlight catalog entries are intentionally
// NOT exposed as caption styles.
import { keyframes } from './motion.js';
import { PALETTE } from './brand.js';
import { CAPTION_ENTRANCES } from './caption-styles.js';

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

// Friendly aliases -> catalog entrance ids. Any catalog id also works directly.
export const STYLE_ALIAS = {
  fadeTilt: 'fadetilt', fadeTiltAlt: 'fadetiltalt', fadeTiltBlur: 'fadetiltblur',
  softFade: 'softfade', fadeDrop: 'fadedrop', fadeTiltScale: 'fadetiltscale',
  zoomPunch: 'zoompunch', wordPop: 'wordpop', impact: 'impact', elastic: 'elastic',
  rise: 'slideup', drop: 'dropin', beat: 'beatpulse', comic: 'comic', hookZoom: 'hookzoom',
};

const clamp01 = v => Math.max(0, Math.min(1, v));
const popScale = elapsed => 0.94 + 0.06 * (1 - Math.pow(1 - Math.min(1, elapsed / 0.09), 3));

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
  const pos = clamp01(1 - p);
  const a = Math.max(0, pos - 0.12), b = Math.min(1, pos + 0.12);
  g.addColorStop(0, base);
  if (a > 0) g.addColorStop(a, base);
  if (b < 1) g.addColorStop(b, accent);
  g.addColorStop(1, accent);
  return g;
}

/**
 * Draw the single spoken word active at `time`, unboxed, with an optional style.
 * Returns the active word (or null). Default style 'pop' == the original renderer.
 */
export function drawWordCaption(ctx, time, words, {
  W, H, family = 'Cairo', size = 76, y = H * 0.82,
  color = PALETTE.paper, shadow = 'rgba(0,0,0,.72)', weight = 800,
  style = 'pop', accent = PALETTE.salmon, theme = 'dark',
} = {}) {
  const word = activeWordAt(words, time);
  if (!word) return null;
  const elapsed = Math.max(0, time - word.start);
  const dur = Math.max(0.05, word.end - word.start);

  let opacity = 1, tx = 0, ty = 0, rot = 0, scale = 1, blur = 0;
  let fill = color, underlineP = 0, karaokeP = -1;

  if (style === 'pop') {
    scale = popScale(elapsed);
  } else if (style === 'karaoke') {
    karaokeP = clamp01(elapsed / Math.max(0.15, dur * 0.7));
    scale = 1 + 0.08 * Math.sin(clamp01(elapsed / dur) * Math.PI);
  } else if (style === 'underline') {
    scale = popScale(elapsed);
    underlineP = clamp01(elapsed / Math.max(0.2, dur * 0.8));
  } else if (style === 'hormozi') {
    // Unboxed Hormozi-style pop (the catalog's boxed variant is not used here).
    const e = CAPTION_ENTRANCES.hormozipop;
    if (e) {
      const t = Math.min(elapsed, e.enter), v = {};
      for (const [n, tr] of Object.entries(e.tracks)) v[n] = keyframes(tr, t);
      opacity = v['word.opacity'] ?? 1; scale = v['word.scale'] ?? 1; rot = v['word.rotate'] ?? 0;
    } else { scale = popScale(elapsed); }
  } else {
    const preset = CAPTION_ENTRANCES[STYLE_ALIAS[style] || style];
    if (preset) {
      const t = Math.min(elapsed, preset.enter), v = {};
      for (const [n, tr] of Object.entries(preset.tracks)) v[n] = keyframes(tr, t);
      opacity = v['word.opacity'] ?? 1;
      ty = (v['word.y'] ?? 0) * size; tx = (v['word.x'] ?? 0) * size;
      rot = v['word.rotate'] ?? 0; scale = v['word.scale'] ?? 1; blur = (v['word.blur'] ?? 0) * size;
    } else {
      scale = popScale(elapsed);
    }
  }

  ctx.save();
  ctx.globalAlpha = opacity;
  ctx.direction = 'rtl';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;
  ctx.shadowColor = shadow;
  ctx.shadowBlur = 18;
  ctx.shadowOffsetY = 3;
  ctx.translate(W / 2 + tx, y + ty);
  ctx.rotate(rot * Math.PI / 180);
  ctx.scale(scale, scale);
  if (blur > 0.2) ctx.filter = `blur(${blur.toFixed(2)}px)`;

  if (karaokeP >= 0) {
    const base = withAlpha(theme === 'dark' ? PALETTE.paper : PALETTE.ink, 0.38);
    const acc = theme === 'dark' ? accent : PALETTE.red;
    ctx.fillStyle = karaokeFill(ctx, word.text, size, karaokeP, acc, base);
  } else {
    ctx.fillStyle = fill;
  }
  ctx.fillText(word.text, 0, 0, W * 0.88);
  ctx.filter = 'none';

  if (underlineP > 0) {
    const tw = Math.min(ctx.measureText(word.text).width, W * 0.88);
    const uw = tw * underlineP;
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
