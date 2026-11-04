// Arabic text helpers for the Canvas renderer. Rules: whole words only, RTL, no letter-spacing.
// See <skill>/reference/arabic-typography.md. Every function is pure for a given input (deterministic frames).
// Kashida & visual RTL/LTR run-order algorithms adapted cleanly under MIT (see assets/CREDITS.md).

const ARABIC_CHAR_RE = /[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]/;
const LATIN_OR_DIGIT_RE = /[A-Za-z0-9]/;
const HARAKAT_CHAR_RE = /[\u064B-\u065F\u0670\u06D6-\u06ED]/;

// Unicode ArabicShaping Joining_Type=D (dual-joining) vs Joining_Type=R (right-joining only).
const DUAL_JOIN = new Set([
  'ب', 'ت', 'ث', 'ج', 'ح', 'خ', 'س', 'ش', 'ص', 'ض', 'ط', 'ظ',
  'ع', 'غ', 'ف', 'ق', 'ك', 'ل', 'م', 'ن', 'ه', 'ي', 'ئ',
  'پ', 'چ', 'ڤ', 'گ', 'ک', 'ی',
]);
const RIGHT_JOIN = new Set([
  'ا', 'أ', 'إ', 'آ', 'ٱ', 'د', 'ذ', 'ر', 'ز', 'و', 'ؤ', 'ة', 'ء', 'ى', 'ژ',
]);
const STRETCH_TEETH = new Set(['س', 'ش', 'ص', 'ض']);
const ALEF_FORMS = new Set(['ا', 'أ', 'إ', 'آ', 'ٱ']);

export async function loadFont(family, url, descriptors = {}) {
  const face = new FontFace(family, `url("${url}")`, descriptors);
  await face.load();
  document.fonts.add(face);
  return face;
}

// Try several files; returns the family that loaded, or null (caller falls back to a system font).
export async function loadFirstFont(family, urls, descriptors = {}) {
  for (const url of urls) {
    try { await loadFont(family, url, descriptors); return family; } catch { /* try next */ }
  }
  return null;
}

export function setArabic(ctx, { family, size, weight = 700, align = 'center', fallback = 'sans-serif' }) {
  ctx.direction = 'rtl';
  ctx.textAlign = align;
  ctx.textBaseline = 'alphabetic';
  ctx.font = `${weight} ${size}px "${family}", ${fallback}`;
  if ('letterSpacing' in ctx) ctx.letterSpacing = '0px';   // tracking breaks joined letters
}

// Ink box of a string in the current font, padded so dots and descenders are never clipped.
export function inkBox(ctx, text, x, y, pad = 0.15) {
  const m = ctx.measureText(text);
  const asc = m.actualBoundingBoxAscent ?? parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font)?.[1] || '48') * 0.78;
  const desc = m.actualBoundingBoxDescent ?? parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font)?.[1] || '48') * 0.26;
  const left = x - (m.actualBoundingBoxLeft ?? m.width / 2);
  const right = x + (m.actualBoundingBoxRight ?? m.width / 2);
  const h = asc + desc, px = (right - left) * pad * 0.5, py = h * pad;
  return { x: left - px, y: y - asc - py, w: right - left + 2 * px, h: h + 2 * py };
}

function isLtrToken(word) {
  const s = String(word);
  return LATIN_OR_DIGIT_RE.test(s) && !ARABIC_CHAR_RE.test(s);
}

// Order tokens for right-to-left stepping on an RTL line while keeping contiguous multi-word
// Latin/numeric runs ("Claude Code 2.0") in natural left-to-right visual order on screen.
// Each returned item preserves `logicalIndex` so staggered animations still fire in spoken order.
export function visualWordOrder(words) {
  const items = words.map((entry, idx) => (
    typeof entry === 'string'
      ? { text: entry, logicalIndex: idx, ltr: isLtrToken(entry) }
      : { ...entry, logicalIndex: entry.logicalIndex ?? idx, ltr: isLtrToken(entry.text) }
  ));
  const out = [];
  let i = 0;
  while (i < items.length) {
    if (!items[i].ltr) {
      out.push(items[i]);
      i += 1;
      continue;
    }
    let j = i + 1;
    while (j < items.length && items[j].ltr) j += 1;
    // Because the RTL line cursor steps from right (large x) to left (small x),
    // reversing the LTR run places the first English word at smaller x (left) and the last at larger x (right).
    for (let k = j - 1; k >= i; k -= 1) out.push(items[k]);
    i = j;
  }
  return out;
}

// Lay out words right→left into lines. Returns [{text, x, y, line, index, logicalIndex}] with x = word centre.
// Words are never split; lines break only between words; multi-word Latin runs read left→right visually.
export function layoutWords(ctx, text, { x, y, maxWidth, lineHeight = 1.5 }) {
  const words = text.trim().split(/\s+/).filter(Boolean);
  const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font)?.[1] || '48');
  const space = ctx.measureText(' ').width;
  const lines = [[]];
  let width = 0;
  words.forEach((word, logicalIndex) => {
    const w = ctx.measureText(word).width;
    if (lines.at(-1).length && width + space + w > maxWidth) { lines.push([]); width = 0; }
    lines.at(-1).push({ text: word, w, logicalIndex });
    width += (lines.at(-1).length > 1 ? space : 0) + w;
  });
  const out = [];
  const step = size * lineHeight, top = y - (step * (lines.length - 1)) / 2;
  const prevAlign = ctx.textAlign;
  lines.forEach((line, li) => {
    const ordered = visualWordOrder(line);
    const total = ordered.reduce((s, w) => s + w.w, 0) + space * Math.max(0, ordered.length - 1);
    let right = prevAlign === 'right' ? x : prevAlign === 'left' ? x + total : x + total / 2;
    for (const w of ordered) {
      out.push({
        text: w.text,
        x: right - w.w / 2,
        y: top + li * step,
        line: li,
        index: out.length,
        logicalIndex: w.logicalIndex,
      });
      right -= w.w + space;
    }
  });
  return out;   // draw each with textAlign='center' at (x, y)
}

// Find Unicode-safe kashida (tatweel U+0640) insertion indices inside a single word.
// Rules:
//   1. Previous base letter MUST be dual-joining (never right-only like ا د ذ ر ز و ة ء ى).
//   2. Next base letter MUST join on its right (DUAL_JOIN or RIGHT_JOIN, excluding ء).
//   3. Never split Lam + Alef (لا / لأ / لإ / لآ / لٱ) — breaks mandatory ligature.
//   4. Insert AFTER any harakat/shadda attached to the left-joining letter, never between base & diacritic.
export function kashidaSlots(word) {
  const s = String(word);
  const bases = [];
  let idx = 0;
  while (idx < s.length) {
    const ch = s[idx];
    if (HARAKAT_CHAR_RE.test(ch) || ch === '\u0640' || ch === '\u200D') {
      idx += 1;
      continue;
    }
    let afterHarakat = idx + 1;
    while (afterHarakat < s.length && HARAKAT_CHAR_RE.test(s[afterHarakat])) afterHarakat += 1;
    bases.push({ ch, index: idx, insertAt: afterHarakat });
    idx = afterHarakat;
  }
  const slots = [];
  for (let b = 0; b + 1 < bases.length; b += 1) {
    const cur = bases[b];
    const nxt = bases[b + 1];
    if (!DUAL_JOIN.has(cur.ch)) continue;
    if (!(DUAL_JOIN.has(nxt.ch) || (RIGHT_JOIN.has(nxt.ch) && nxt.ch !== 'ء'))) continue;
    if (cur.ch === 'ل' && ALEF_FORMS.has(nxt.ch)) continue;
    let priority = 2;
    if (STRETCH_TEETH.has(cur.ch)) priority = 3;
    else if (b + 1 === bases.length - 1) priority = 3;
    else if ( b === 0 ) priority = 1;
    slots.push({ index: cur.insertAt, priority, order: b });
  }
  slots.sort((a, b) => (b.priority - a.priority) || (b.order - a.order));
  return slots;
}

// Deterministically insert `count` tatweel characters into valid Arabic connection slots.
export function insertKashida(text, count = 1) {
  const n = Math.max(0, Math.floor(count));
  if (n === 0 || !text) return String(text);
  const parts = String(text).split(/(\s+)/);
  const wordCandidates = [];
  parts.forEach((tok, pi) => {
    if (!tok || /^\s+$/.test(tok)) return;
    const slots = kashidaSlots(tok);
    if (slots.length) wordCandidates.push({ partIndex: pi, slots, counts: new Array(slots.length).fill(0) });
  });
  if (!wordCandidates.length) return String(text);
  for (let k = 0; k < n; k += 1) {
    const targetWord = wordCandidates[k % wordCandidates.length];
    const slotIdx = Math.floor(k / wordCandidates.length) % targetWord.slots.length;
    targetWord.counts[slotIdx] += 1;
  }
  for (const wc of wordCandidates) {
    const edits = wc.slots
      .map((slot, si) => ({ index: slot.index, add: wc.counts[si] }))
      .filter(e => e.add > 0)
      .sort((a, b) => b.index - a.index);
    let word = parts[wc.partIndex];
    for (const ed of edits) {
      word = word.slice(0, ed.index) + '\u0640'.repeat(ed.add) + word.slice(ed.index);
    }
    parts[wc.partIndex] = word;
  }
  return parts.join('');
}

// Compute stretched Arabic text + subtle residual horizontal scale (<= maxScaleX) to hit targetWidth smoothly.
export function stretchKashida(ctx, text, targetWidth, { maxTatweels = 16, maxScaleX = 1.06 } = {}) {
  const raw = String(text);
  const naturalWidth = ctx.measureText(raw).width;
  if (!(targetWidth > naturalWidth) || naturalWidth <= 0) {
    return { text: raw, naturalWidth, width: naturalWidth, scaleX: 1, tatweels: 0 };
  }
  let bestText = raw;
  let bestWidth = naturalWidth;
  let bestCount = 0;
  for (let c = 1; c <= maxTatweels; c += 1) {
    const candidate = insertKashida(raw, c);
    if (candidate === bestText) break;
    const w = ctx.measureText(candidate).width;
    if (w <= targetWidth) {
      bestText = candidate;
      bestWidth = w;
      bestCount = c;
    } else {
      break;
    }
  }
  const scaleX = bestWidth > 0 ? Math.min(maxScaleX, Math.max(1, targetWidth / bestWidth)) : 1;
  return {
    text: bestText,
    naturalWidth,
    width: bestWidth * scaleX,
    scaleX,
    tatweels: bestCount,
  };
}

// Draw stretched Arabic text at (x, y) with smooth animated progress 0..1 from naturalWidth to targetWidth.
export function drawKashida(ctx, text, x, y, targetWidth, { progress = 1, maxTatweels = 16, maxScaleX = 1.06, stroke = false } = {}) {
  const raw = String(text);
  const natural = ctx.measureText(raw).width;
  const desired = natural + Math.max(0, targetWidth - natural) * clamp01(progress);
  const res = stretchKashida(ctx, raw, desired, { maxTatweels, maxScaleX });
  ctx.save();
  ctx.translate(x, y);
  if (Math.abs(res.scaleX - 1) > 1e-4) ctx.scale(res.scaleX, 1);
  if (stroke) ctx.strokeText(res.text, 0, 0);
  ctx.fillText(res.text, 0, 0);
  ctx.restore();
  return res;
}

// Workaround for calligraphic fonts (e.g. Aref Ruqaa) where isolated ة after a right-only letter renders detached/broken.
export function fixRuqaaTaaMarbuta(text) {
  const s = String(text);
  let out = '';
  for (let i = 0; i < s.length; i += 1) {
    const ch = s[i];
    if (ch === 'ة' && i > 0) {
      let p = i - 1;
      while (p >= 0 && HARAKAT_CHAR_RE.test(s[p])) p -= 1;
      if (p >= 0 && RIGHT_JOIN.has(s[p]) && s[i - 1] !== '\u200D') {
        out += '\u200D';
      }
    }
    out += ch;
  }
  return out;
}

// Right→left reveal of an already shaped word/line: the clip grows from the right edge.
// draw() must render the full text; box comes from inkBox(). progress 0..1.
export function wipeReveal(ctx, draw, box, progress, { cursor = null } = {}) {
  const p = Math.min(1, Math.max(0, progress));
  const w = box.w * p;
  ctx.save();
  ctx.beginPath();
  ctx.rect(box.x + box.w - w, box.y, w, box.h);
  ctx.clip();
  draw();
  ctx.restore();
  if (cursor && p > 0 && p < 1) {
    ctx.save();
    ctx.fillStyle = cursor;
    ctx.fillRect(box.x + box.w - w - box.h * 0.04, box.y + box.h * 0.1, box.h * 0.06, box.h * 0.8);
    ctx.restore();
  }
}

export const clamp01 = v => Math.min(1, Math.max(0, v));
export const easeOutCubic = u => 1 - Math.pow(1 - clamp01(u), 3);
export const easeOutExpo = u => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp01(u)));
