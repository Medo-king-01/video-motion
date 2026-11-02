// Word-by-word Arabic caption renderer. Timeline values are absolute scene-local seconds.
// The caller supplies measured word onsets/offsets; this module never estimates timing.
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

// One spoken word at a time; text is rendered directly over the scene with no box, border or panel.
export function drawWordCaption(ctx, time, words, {
  W, H, family = 'Cairo', size = 76, y = H * 0.82,
  color = '#F3F2F1', shadow = 'rgba(0,0,0,.72)', weight = 800,
} = {}) {
  const word = activeWordAt(words, time);
  if (!word) return null;
  const elapsed = Math.max(0, time - word.start);
  const pop = Math.min(1, elapsed / 0.09);
  const scale = 0.94 + 0.06 * (1 - Math.pow(1 - pop, 3));
  ctx.save();
  ctx.direction = 'rtl';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.font = `${weight} ${size}px "${family}", sans-serif`;
  ctx.fillStyle = color;
  ctx.shadowColor = shadow;
  ctx.shadowBlur = 18;
  ctx.shadowOffsetY = 3;
  ctx.translate(W / 2, y);
  ctx.scale(scale, scale);
  ctx.fillText(word.text, 0, 0, W * 0.88);
  ctx.restore();
  return word;
}
