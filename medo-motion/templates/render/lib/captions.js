import { withLayout } from './layout.js';
// Word-by-word and phrase-chunk Arabic caption renderer (engine K). Timeline values
// are absolute scene-local seconds; the caller supplies MEASURED word onsets/offsets
// (tools/caption_align.py) — this module never estimates timing.
//
// `style` is REQUIRED and must be an explicit, agent-chosen value from
// plan/text-direction.json. There is no default look: omitting it fails loudly.
// All styles render unboxed text in brand colors; boxed/highlight catalog entries
// are intentionally NOT exposed as caption styles.
import { BRAND, PALETTE } from './brand.js';
import { clamp01, easeOutCubic, visualWordOrder } from './arabic.js';
import { captionTransform, resolveTextStyle, STYLE_ALIAS } from './caption-motion.js';
import { textStyleFor, fontFor } from './text-direction.js';
import { useFont } from './fonts.js';

export { STYLE_ALIAS, resolveTextStyle };

const ARABIC_GLUE_WORDS = new Set([
  'في', 'من', 'على', 'إلى', 'الى', 'عن', 'مع', 'كل', 'مش', 'ما', 'لا',
  'لن', 'لم', 'إن', 'أن', 'ان', 'لو', 'يا', 'ده', 'دي', 'اللي', 'بس',
  'ولا', 'أو', 'او', 'حتى', 'عشان', 'علشان', 'لأن', 'كان', 'غير', 'بين',
]);
const HARD_PUNCT_RE = /[،؛.؟!,:;…]$/;

function cleanGlueToken(word) {
  return String(word || '')
    .replace(/[\u064B-\u065F\u0670\u0640]/g, '')
    .replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '');
}

/** True when `time` falls inside any hero-text suppression window `[[start, end], ...]`. */
export function isHiddenAt(time, hideRanges) {
  if (!Array.isArray(hideRanges) || !Number.isFinite(time)) return false;
  for (const r of hideRanges) {
    const s = Array.isArray(r) ? r[0] : r?.start;
    const e = Array.isArray(r) ? r[1] : r?.end;
    if (Number.isFinite(s) && Number.isFinite(e) && time >= s && time < e) return true;
  }
  return false;
}

/**
 * Group measured word timings into natural 2–4 word single-line RTL phrase chunks.
 * Never orphans Arabic prepositions/particles (`في`, `من`, `على`, `مش`, `اللي`...) at
 * the end of a chunk unless forced by a pause > `maxGap` or terminal punctuation.
 */
export function groupCaptionChunks(words, {
  maxWords = 4,
  maxGap = 0.45,
  maxDuration = 2.2,
  holdAfter = 0.35,
  bridgeGap = 0.28,
} = {}) {
  validateWordTimeline(words);
  if (!words.length) return [];
  const cap = Math.max(1, Math.floor(maxWords));
  const rawChunks = [];
  let cur = [];

  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    if (!cur.length) {
      cur.push(w);
      continue;
    }
    const prev = cur[cur.length - 1];
    const gap = w.start - prev.end;
    const span = w.end - cur[0].start;
    const prevPunct = HARD_PUNCT_RE.test(prev.text.trim());
    const prevIsGlue = ARABIC_GLUE_WORDS.has(cleanGlueToken(prev.text));
    const overWords = cur.length >= cap;
    const hardLimit = cur.length >= cap + 1;

    let shouldSplit = false;
    if (gap > maxGap || prevPunct) {
      shouldSplit = true;
    } else if (hardLimit || (span > maxDuration && !prevIsGlue)) {
      shouldSplit = true;
    } else if (overWords && !prevIsGlue) {
      shouldSplit = true;
    }

    if (shouldSplit) {
      rawChunks.push(cur);
      cur = [w];
    } else {
      cur.push(w);
    }
  }
  if (cur.length) rawChunks.push(cur);

  return rawChunks.map((group, idx) => {
    const start = group[0].start;
    const lastEnd = group[group.length - 1].end;
    const nextStart = idx + 1 < rawChunks.length ? rawChunks[idx + 1][0].start : Infinity;
    const gapToNext = nextStart - lastEnd;
    const end = gapToNext <= bridgeGap
      ? nextStart
      : Math.min(nextStart, lastEnd + Math.max(0, holdAfter));
    return {
      index: idx,
      start,
      spokenEnd: lastEnd,
      end,
      text: group.map(x => x.text).join(' '),
      words: group,
    };
  });
}

export function activeChunkAt(chunks, time) {
  if (!Array.isArray(chunks) || !Number.isFinite(time)) return null;
  let lo = 0, hi = chunks.length - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const c = chunks[mid];
    if (time < c.start) hi = mid - 1;
    else if (time >= c.end) lo = mid + 1;
    else return c;
  }
  return null;
}

/** Load every face the agent chose for a scene (call from init()). */
export async function useDirectedFonts(direction, scene) {
  const sc = (direction.scenes || []).find(s => s.scene === scene) || {};
  const entries = [...Object.values(sc.fontStyles || {}), ...Object.values(sc.fontElements || {})];
  const seen = new Set();
  const jobs = [];
  for (const e of entries) {
    if (!e || typeof e.family !== 'string') continue;
    const key = `${e.family}@${e.weight}`;
    if (seen.has(key)) continue;
    seen.add(key);
    jobs.push(useFont(e.family, e.weight));
  }
  return Promise.all(jobs);
}

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
  still = false, hideRanges = null,
} = {}) {
  resolveTextStyle(style); // validate style upfront even on silent/hidden frames
  if (isHiddenAt(time, hideRanges)) return null;
  const word = activeWordAt(words, time);
  if (!word) return null;
  const elapsed = Math.max(0, time - word.start);
  const dur = Math.max(0.05, word.end - word.start);
  const rawM = captionTransform(style, elapsed, dur);
  const m = still
    ? { ...rawM, x: 0, y: 0, scale: 1, rotate: 0, blur: 0, opacity: clamp01(elapsed / 0.12) }
    : rawM;
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
  withLayout(ctx,{id:'caption',zone:'caption'},()=>ctx.fillText(word.text, 0, 0, W * 0.88));
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

/**
 * Draw a 2–4 word single-line RTL phrase caption, unboxed, highlighting the active
 * spoken word in brand accent while keeping mixed English/number runs in natural order.
 * Accepts either pre-grouped `chunks` (from `groupCaptionChunks`) or raw `words`.
 */
export function drawPhraseCaption(ctx, time, wordsOrChunks, {
  W = BRAND.W, H = BRAND.H, family = 'Cairo', size = 58, y = BRAND.safe.captionY,
  color = PALETTE.paper, shadow = 'rgba(0,0,0,.72)', weight = 800,
  style, accent = PALETTE.salmon, theme = 'dark',
  still = false, hideRanges = null, maxWords = 4, maxGap = 0.45,
} = {}) {
  resolveTextStyle(style);
  if (isHiddenAt(time, hideRanges)) return null;
  if (!Array.isArray(wordsOrChunks) || !wordsOrChunks.length) return null;
  const chunks = Array.isArray(wordsOrChunks[0]?.words)
    ? wordsOrChunks
    : groupCaptionChunks(wordsOrChunks, { maxWords, maxGap });
  const chunk = activeChunkAt(chunks, time);
  if (!chunk) return null;

  const chunkElapsed = Math.max(0, time - chunk.start);
  const chunkDur = Math.max(0.08, chunk.end - chunk.start);
  const baseM = still
    ? { x: 0, y: 0, scale: 1, rotate: 0, opacity: clamp01(chunkElapsed / 0.14) }
    : captionTransform(style, chunkElapsed, chunkDur);

  ctx.save();
  ctx.direction = 'rtl';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;

  const space = Math.max(size * 0.24, ctx.measureText(' ').width || size * 0.26);
  const ordered = visualWordOrder(chunk.words.map((w, idx) => ({
    ...w,
    logicalIndex: idx,
    width: ctx.measureText(w.text).width || size,
  })));
  const totalW = ordered.reduce((s, w) => s + w.width, 0) + space * Math.max(0, ordered.length - 1);
  const maxLineW = W - BRAND.safe.margin * 2;
  const fitScale = totalW > maxLineW ? maxLineW / totalW : 1;

  ctx.shadowColor = shadow;
  ctx.shadowBlur = 16;
  ctx.shadowOffsetY = 3;
  ctx.translate(W / 2 + (still ? 0 : baseM.x * size * 0.4), y + (still ? 0 : baseM.y * size * 0.4));
  if (!still && baseM.rotate) ctx.rotate(baseM.rotate * Math.PI / 180 * 0.35);
  const groupScale = (still ? 1 : (1 + (baseM.scale - 1) * 0.35)) * fitScale;
  ctx.scale(groupScale, groupScale);

  const accColor = theme === 'dark' ? accent : PALETTE.red;
  let right = totalW / 2;
  for (const item of ordered) {
    const cx = right - item.width / 2;
    const isActive = time >= item.start && time < item.end;
    const isSpoken = time >= item.end;
    const wordScale = (!still && isActive)
      ? 1 + 0.06 * easeOutCubic(clamp01((time - item.start) / 0.12))
      : 1;
    ctx.save();
    ctx.globalAlpha = baseM.opacity * (isActive || isSpoken ? 1 : 0.56);
    ctx.translate(cx, 0);
    if (wordScale !== 1) ctx.scale(wordScale, wordScale);
    ctx.fillStyle = isActive ? accColor : color;
    withLayout(
      ctx,
      { id: `caption-${chunk.index}-${item.logicalIndex}`, zone: 'caption' },
      () => ctx.fillText(item.text, 0, 0),
    );
    ctx.restore();
    right -= item.width + space;
  }
  ctx.restore();
  return chunk;
}

/**
 * Draw a fixed-window vertical word-slot ticker (`items = [{ start, text }, ...]`).
 * Outgoing text slides upward out of a dot-padded clip box while incoming text rises in.
 */
export function drawTextSlot(ctx, time, items, {
  x, y, maxWidth = 900, family = 'Cairo', size = 72, weight = 800,
  color = PALETTE.paper, transitionDur = 0.28, zone = 'content', id = 'slot',
} = {}) {
  if (!Array.isArray(items) || !items.length || !Number.isFinite(time)) return null;
  let activeIdx = -1;
  for (let i = 0; i < items.length; i++) {
    if (time >= items[i].start) activeIdx = i;
  }
  if (activeIdx < 0) return null;

  const cur = items[activeIdx];
  const prev = activeIdx > 0 ? items[activeIdx - 1] : null;
  const u = prev ? easeOutCubic(clamp01((time - cur.start) / Math.max(0.05, transitionDur))) : 1;
  const padTop = size * 0.72;
  const padBot = size * 0.62;
  const slotH = padTop + padBot;

  ctx.save();
  ctx.direction = 'rtl';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;
  ctx.beginPath();
  ctx.rect(x - maxWidth / 2, y - padTop, maxWidth, slotH);
  ctx.clip();

  if (prev && u < 1) {
    ctx.save();
    ctx.globalAlpha = 1 - u;
    ctx.fillStyle = color;
    ctx.fillText(prev.text, x, y - u * slotH * 0.82, maxWidth);
    ctx.restore();
  }
  ctx.save();
  ctx.globalAlpha = prev ? u : clamp01((time - cur.start) / 0.16);
  ctx.fillStyle = color;
  const curY = prev ? y + (1 - u) * slotH * 0.82 : y;
  withLayout(ctx, { id, zone }, () => ctx.fillText(cur.text, x, curY, maxWidth));
  ctx.restore();
  ctx.restore();
  return cur;
}

/**
 * Draw ANY on-screen text (title, keyword, number, CTA, label, UI) using the
 * agent's explicit motion choice from plan/text-direction.json. `text` may be a
 * string or an array of lines. There is no default style: a missing direction or
 * role throws before anything is drawn.
 */
export function drawDirectedText(ctx, text, {
  direction, scene, role, elementId = null,
  time, start, end, x, y, size = 64,
  color = PALETTE.paper, accent = PALETTE.salmon, shadow = 'rgba(0,0,0,.72)',
  theme = 'dark', rtl = true, maxWidth,
} = {}) {
  const style = textStyleFor(direction, scene, role, elementId);
  const font = fontFor(direction, scene, role, elementId);
  const family = font.family, weight = font.weight;
  const lines = Array.isArray(text) ? text : String(text).split('\n');
  const elapsed = Math.max(0, time - start);
  const dur = maxDur(end - start);
  const m = captionTransform(style, elapsed, dur);
  const blur = m.blur * size;
  const lineH = size * 1.35;

  ctx.save();
  ctx.globalAlpha = m.opacity;
  ctx.direction = rtl ? 'rtl' : 'ltr';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;
  ctx.shadowColor = shadow;
  ctx.shadowBlur = 18;
  ctx.shadowOffsetY = 3;
  ctx.translate(x + m.x * size, y + m.y * size);
  ctx.rotate(m.rotate * Math.PI / 180);
  ctx.scale(m.scale, m.scale);
  if (blur > 0.2) ctx.filter = `blur(${blur.toFixed(2)}px)`;

  lines.forEach((line, i) => {
    if (!line) return;
    const ly = (i - (lines.length - 1) / 2) * lineH;
    if (m.karaokeP >= 0) {
      const base = withAlpha(theme === 'dark' ? PALETTE.paper : PALETTE.ink, 0.38);
      const acc = theme === 'dark' ? accent : PALETTE.red;
      ctx.fillStyle = karaokeFill(ctx, line, size, m.karaokeP, acc, base);
    } else {
      ctx.fillStyle = color;
    }
    withLayout(ctx,{id:`${elementId||role}-${i}`,zone:role==='caption'?'caption':'content'},()=>ctx.fillText(line, 0, ly, maxWidth));
    if (m.underlineP > 0) {
      const tw = ctx.measureText(line).width;
      const uw = (maxWidth ? Math.min(tw, maxWidth) : tw) * m.underlineP;
      ctx.shadowBlur = 0; ctx.shadowOffsetY = 0;
      ctx.strokeStyle = theme === 'dark' ? accent : PALETTE.red;
      ctx.lineWidth = Math.max(4, size * 0.07);
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(uw / 2, ly + size * 0.62);
      ctx.lineTo(-uw / 2, ly + size * 0.62);
      ctx.stroke();
    }
  });
  ctx.restore();
  return style;
}

function maxDur(d) {
  return Math.max(0.05, d);
}
