// Arabic text helpers for the Canvas renderer. Rules: whole words only, RTL, no letter-spacing.
// See <skill>/reference/arabic-typography.md. Every function is pure for a given input (deterministic frames).

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
  const asc = m.actualBoundingBoxAscent, desc = m.actualBoundingBoxDescent;
  const left = x - m.actualBoundingBoxLeft, right = x + m.actualBoundingBoxRight;
  const h = asc + desc, px = (right - left) * pad * 0.5, py = h * pad;
  return { x: left - px, y: y - asc - py, w: right - left + 2 * px, h: h + 2 * py };
}

// Lay out words right→left into lines. Returns [{text, x, y, line, index}] with x = word centre.
// Words are never split; lines break only between words.
export function layoutWords(ctx, text, { x, y, maxWidth, lineHeight = 1.5 }) {
  const words = text.trim().split(/\s+/);
  const size = parseFloat(/(\d+(?:\.\d+)?)px/.exec(ctx.font)?.[1] || '48');
  const space = ctx.measureText(' ').width;
  const lines = [[]];
  let width = 0;
  for (const word of words) {
    const w = ctx.measureText(word).width;
    if (lines.at(-1).length && width + space + w > maxWidth) { lines.push([]); width = 0; }
    lines.at(-1).push({ text: word, w });
    width += (lines.at(-1).length > 1 ? space : 0) + w;
  }
  const out = [];
  const step = size * lineHeight, top = y - (step * (lines.length - 1)) / 2;
  const prevAlign = ctx.textAlign;
  lines.forEach((line, li) => {
    const total = line.reduce((s, w) => s + w.w, 0) + space * (line.length - 1);
    let right = prevAlign === 'right' ? x : prevAlign === 'left' ? x + total : x + total / 2;
    for (const w of line) {
      out.push({ text: w.text, x: right - w.w / 2, y: top + li * step, line: li, index: out.length });
      right -= w.w + space;
    }
  });
  return out;   // draw each with textAlign='center' at (x, y)
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
