// Pure, frame-deterministic caption/text motion shared by engines K and R.
// Engine P mirrors this in caption_motion.py (tests keep the numbers in parity).
// No style is a default: the caller must pass an explicit, agent-chosen style.
import { keyframes } from './motion.js';
import { CAPTION_ENTRANCES } from './caption-styles.js';

// Friendly aliases -> catalog entrance ids. Any catalog id also works directly.
export const STYLE_ALIAS = {
  fadeTilt: 'fadetilt', fadeTiltAlt: 'fadetiltalt', fadeTiltBlur: 'fadetiltblur',
  softFade: 'softfade', fadeDrop: 'fadedrop', fadeTiltScale: 'fadetiltscale',
  zoomPunch: 'zoompunch', wordPop: 'wordpop', impact: 'impact', elastic: 'elastic',
  rise: 'slideup', drop: 'dropin', beat: 'beatpulse', comic: 'comic', hookZoom: 'hookzoom',
};

export const SPECIAL_STYLES = ['pop', 'karaoke', 'underline', 'hormozi'];

const clamp01 = v => Math.max(0, Math.min(1, v));
const popScale = elapsed => 0.94 + 0.06 * (1 - Math.pow(1 - Math.min(1, elapsed / 0.09), 3));

/** Resolve an explicit style id. Missing/unknown styles fail loudly — never fall back. */
export function resolveTextStyle(style) {
  if (typeof style !== 'string' || !style.trim()) {
    throw new Error('Text style is required: the agent must choose a style per scene (plan/text-direction.json).');
  }
  const id = STYLE_ALIAS[style] || style;
  if (SPECIAL_STYLES.includes(id) || CAPTION_ENTRANCES[id]) return id;
  throw new Error(`Unknown text style "${style}". Choose from the caption-safe catalog (docs/text-animations.md).`);
}

/**
 * Sample the chosen style at `elapsed` seconds into a word/fragment of `duration`.
 * Returns { opacity, x, y, rotate, scale, blur, underlineP, karaokeP } where x/y/blur
 * are font-relative em (multiply by the font size); rotate is degrees.
 */
export function captionTransform(style, elapsed, duration) {
  const id = resolveTextStyle(style);
  const dur = Math.max(0.05, duration);
  let opacity = 1, x = 0, y = 0, rotate = 0, scale = 1, blur = 0;
  let underlineP = 0, karaokeP = -1;

  if (id === 'pop') {
    scale = popScale(elapsed);
  } else if (id === 'karaoke') {
    karaokeP = clamp01(elapsed / Math.max(0.15, dur * 0.7));
    scale = 1 + 0.08 * Math.sin(clamp01(elapsed / dur) * Math.PI);
  } else if (id === 'underline') {
    scale = popScale(elapsed);
    underlineP = clamp01(elapsed / Math.max(0.2, dur * 0.8));
  } else {
    const preset = id === 'hormozi' ? CAPTION_ENTRANCES.hormozipop : CAPTION_ENTRANCES[id];
    if (!preset) throw new Error(`Text style "${style}" has no entrance preset.`);
    const t = Math.min(elapsed, preset.enter), v = {};
    for (const [n, tr] of Object.entries(preset.tracks)) v[n] = keyframes(tr, t);
    opacity = v['word.opacity'] ?? 1;
    y = v['word.y'] ?? 0; x = v['word.x'] ?? 0;
    rotate = v['word.rotate'] ?? 0; scale = v['word.scale'] ?? 1; blur = v['word.blur'] ?? 0;
  }
  return { id, opacity, x, y, rotate, scale, blur, underlineP, karaokeP };
}
