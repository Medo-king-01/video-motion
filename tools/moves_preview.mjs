#!/usr/bin/env node
// Deterministic preview sheet for the element moves (B1b).
//
//   node tools/moves_preview.mjs out/moves.html
//
// Draws sampled frames with plain SVG — no canvas, no browser, no timestamps — so the same
// command produces byte-identical output. It is a review aid, not a render: colours and fonts
// are placeholders, and Arabic shaping is the browser's.
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import {
  pixelListItem, parallaxLayer, orbitItem, wordPathItem, explodePart,
  maskWipe, dataCount, cardStackItem, cameraPush, particleBurst,
} from '../shared/js/moves.js';

const FS = 40;
const TIMES = [0, 0.28, 0.62, 1.4];
const PROGRESS = [0, 0.33, 0.66, 1];
const ROWS = ['مدخل أول', 'المدخل الثاني', 'الثالث'];
const WORDS = ['أول', 'ثاني', 'ثالث'];

const esc = value => String(value).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
const n = value => Number(value).toFixed(3);
const frame = (body, label) => `<figure><svg viewBox="0 0 360 260" width="240" role="img" aria-label="${esc(label)}">`
  + `<rect width="360" height="260" fill="#f5f5f7"/>${body}</svg><figcaption>${esc(label)}</figcaption></figure>`;
const row = items => `<div class="row">${items.join('')}</div>`;
const section = (title, frames) => `<section><h2>${esc(title)}</h2>${row(frames)}</section>`;

const listFrames = TIMES.map(t => frame(ROWS.map((label, i) => {
  const s = pixelListItem(i, t, { fontSize: FS });
  return `<g opacity="${s.opacity.toFixed(4)}" transform="translate(${n(120 + s.x * FS)} ${n(40 + i * 62 + s.y * FS)})">`
    + `<rect width="200" height="34" rx="8" fill="#1d1d1f"/>`
    + `<text x="188" y="24" text-anchor="end" font-size="18" fill="#f5f5f7">${esc(label)}</text></g>`;
}).join(''), `pixel-list · t=${t.toFixed(2)}s`));

const parallaxFrames = PROGRESS.map(p => frame([[0.15, '#d9d4cc', 70], [0.5, '#9b968d', 120], [1, '#1d1d1f', 190]]
  .map(([depth, fill, y], i) => {
    const s = parallaxLayer(depth, p, { panX: 0.8 });
    return `<rect x="${n(60 + s.x * FS + i * 6)}" y="${y}" width="180" height="46" rx="10" fill="${fill}"/>`;
  }).join(''), `parallax · progress=${p.toFixed(2)}`));

const orbitFrames = TIMES.map(t => frame([0, 1, 2, 3, 4, 5].map(i => {
  const s = orbitItem(i, t, { count: 6, radius: 1.6 });
  const size = 22 + 10 * (s.scale - 1) / 0.08;
  return `<circle cx="${n(180 + s.x * FS)}" cy="${n(130 + s.y * FS)}" r="${n(size / 2)}" `
    + `fill="#1d1d1f" opacity="${(0.35 + 0.65 * (s.depth + 1) / 2).toFixed(3)}"/>`;
}).join(''), `orbit · t=${t.toFixed(2)}s`));

const wordFrames = TIMES.map(t => frame(WORDS.map((word, i) => {
  const s = wordPathItem(i, t, { fromX: -1.6, toX: 1.2 });
  return `<g opacity="${s.opacity.toFixed(4)}" transform="translate(${n(180 + s.x * FS)} ${n(70 + i * 54 + s.y * FS)}) rotate(${n(s.rotation)})">`
    + `<text x="0" y="0" text-anchor="middle" font-size="26" fill="#1d1d1f">${esc(word)}</text></g>`;
}).join(''), `word-path · t=${t.toFixed(2)}s`));

const explodeFrames = [0, 0.3, 0.9, 1.6].map(t => frame([0, 1, 2, 3, 4, 5].map(i => {
  const s = explodePart(i, t, { count: 6, spread: 1.6, duration: 0.5, hold: 0.4, back: 0.5 });
  return `<rect x="${n(180 + s.x * FS - 16)}" y="${n(130 + s.y * FS - 16)}" width="32" height="32" rx="6" `
    + `fill="#1d1d1f" transform="rotate(${n(s.rotation)} ${n(180 + s.x * FS)} ${n(130 + s.y * FS)})"/>`;
}).join(''), `explode · t=${t.toFixed(2)}s`));

const maskFrames = PROGRESS.map(p => {
  const s = maskWipe(p, { duration: 1 });
  return frame(`<rect x="${n(s.x * 360)}" y="${n(s.y * 260)}" width="${n(s.w * 360)}" height="${n(s.h * 260)}" fill="#1d1d1f"/>`,
    `mask-wipe · p=${p.toFixed(2)}`);
});

const countFrames = PROGRESS.map(p => {
  const s = dataCount(p, { duration: 1, from: 0, to: 2400, decimals: 0 });
  return frame(`<text x="180" y="150" text-anchor="middle" font-size="44" fill="#1d1d1f">${esc(String(s.value))}</text>`,
    `data-count · p=${p.toFixed(2)}`);
});

const cardFrames = TIMES.map(t => frame([0, 1, 2].map(i => {
  const s = cardStackItem(i, t, { spread: 0.35, tilt: 4 });
  return `<g opacity="${s.opacity.toFixed(4)}" transform="translate(${n(180 + s.x * FS)} ${n(130 + s.y * FS)}) rotate(${n(s.rotation)}) scale(${n(s.scale)})">`
    + `<rect x="-70" y="-45" width="140" height="90" rx="10" fill="#1d1d1f" opacity="${(0.45 + i * 0.2).toFixed(2)}"/></g>`;
}).join(''), `card-stack · t=${t.toFixed(2)}s`));

const cameraFrames = PROGRESS.map(p => {
  const s = cameraPush(p, { duration: 1, toScale: 1.25 });
  return frame(`<g transform="translate(${n(180 + s.x)} ${n(130 + s.y)}) scale(${n(s.scale)}) translate(-180 -130)">`
    + `<rect x="90" y="80" width="180" height="100" rx="8" fill="none" stroke="#1d1d1f" stroke-width="3"/>`
    + `<circle cx="180" cy="130" r="26" fill="#1d1d1f"/></g>`, `camera-push · p=${p.toFixed(2)}`);
});

const burstFrames = [0.05, 0.18, 0.34, 0.62].map(t => frame(Array.from({ length: 18 }, (_, i) => {
  const s = particleBurst(i, t, { count: 18, duration: 0.7 });
  return `<circle cx="${n(180 + s.x * FS)}" cy="${n(130 + s.y * FS)}" r="${n(s.size * FS)}" `
    + `fill="#1d1d1f" opacity="${s.opacity.toFixed(3)}"/>`;
}).join(''), `particle-burst · t=${t.toFixed(2)}s`));

const sections = [
  section('pixel-list — كل سطر يدخل بعد stagger، والإزاحة منقّطة على بكسل', listFrames),
  section('parallax — الطبقات تتحرك بسرعات مختلفة مع تقدّم الكاميرا', parallaxFrames),
  section('orbit — عناصر تدور على قطع ناقص، والعمق يغيّر الحجم', orbitFrames),
  section('word-path — كل كلمة تسير على مسار مستقيم وتستقر', wordFrames),
  section('explode — تفكيك ثم إعادة تجميع (0.5s فتح · 0.4s ثبات · 0.5s رجوع)', explodeFrames),
  section('mask-wipe — مستطيل قصّ متحرك', maskFrames),
  section('data-count — عدّاد رقمي حتمي', countFrames),
  section('card-stack — كروت متراكبة تدخل بالتتابع', cardFrames),
  section('camera-push — دفع كاميرا حول مركز الإطار', cameraFrames),
  section('particle-burst — شظايا حتمية بجاذبية', burstFrames),
];

const total = TIMES.length * 5 + PROGRESS.length * 4 + 4;
const html = `<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Element moves — preview</title>
<style>
 body{font:14px/1.5 system-ui,sans-serif;background:#fff;color:#1d1d1f;margin:24px}
 h1{font-size:20px;margin:0 0 4px} p{color:#6e6e73;margin:0 0 24px}
 section{margin-bottom:28px} h2{font-size:15px;margin:0 0 12px;font-weight:600}
 .row{display:flex;gap:16px;flex-wrap:wrap} figure{margin:0;text-align:center}
 figcaption{font-size:12px;color:#6e6e73;margin-top:6px}
</style>
<h1>حركات العنصر — أوراق معاينة</h1>
<p>إطارات مُعاينة مولّدة من نفس دوال K/P/R: <code>shared/js/moves.js</code>. ألوان ونصوص بديلة عن البراند.</p>
${sections.join('\n')}
</html>`;

const out = process.argv[2];
if (!out) {
  console.error('usage: node tools/moves_preview.mjs <out.html>');
  process.exit(2);
}
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, html, 'utf8');
console.log(`wrote ${out} (${total} frames, deterministic)`);
