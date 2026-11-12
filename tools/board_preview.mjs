#!/usr/bin/env node
// Deterministic SVG preview for a declarative board (B2).
//
//   node tools/board_preview.mjs medo-motion/motion/boards/explainer-sample.json out.html
//
// Samples the board with the same interpreter the renderer uses (`shared/js/board.js`) and draws
// the ops as SVG. No canvas, no browser, no timestamps: two runs are byte-identical. Colours and
// fonts are placeholders; Arabic shaping and real fonts belong to the browser/render stage.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';
import { boardFrame } from '../shared/js/board.js';

const PLACEHOLDER = {
  paper: '#F5F5F7', ink: '#1D1D1F', 'ink_soft': '#3A3A3C', salmon: '#E2674B',
  red: '#D5232F', 'red_bright': '#F03B3B', 'red_deep': '#9E1620',
  gray_1: '#8E8E93', gray_2: '#C7C7CC', gray_3: '#E5E5EA', gray_4: '#F2F2F7', blush: '#F6C7A8',
};

const esc = value => String(value).replace(/[&<>"]/g, ch => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[ch]));
const n = value => Number(value).toFixed(2);
const paint = role => PLACEHOLDER[role] ?? role;

function paintOps(ops) {
  return ops.map(op => {
    const transform = `translate(${n(op.x)} ${n(op.y)})`
      + (op.rotation ? ` rotate(${n(op.rotation)})` : '')
      + (op.scale !== 1 ? ` scale(${n(op.scale)})` : '');
    const alpha = op.alpha === 1 ? '' : ` opacity="${n(op.alpha)}"`;
    const group = body => `<g transform="${transform}"${alpha}>${body}</g>`;
    if (op.kind === 'text') {
      const anchor = op.align === 'center' ? 'middle' : op.align === 'left' ? 'start' : 'end';
      return group(`<text x="0" y="0" text-anchor="${anchor}" font-size="${n(op.size)}" `
        + `font-family="${esc(op.font ?? 'sans-serif')}" fill="${paint(op.color)}" direction="rtl">`
        + `${esc(op.text)}</text>`);
    }
    if (op.kind === 'shape') {
      const fill = op.fill ? paint(op.fill) : 'none';
      const stroke = op.stroke ? ` stroke="${paint(op.stroke)}" stroke-width="${n(op.strokeWidth)}"` : '';
      if (op.shape === 'rect') {
        return group(`<rect width="${n(op.w)}" height="${n(op.h)}" rx="${n(op.radius)}" fill="${fill}"${stroke}/>`);
      }
      if (op.shape === 'ellipse') {
        return group(`<ellipse cx="${n(op.w / 2)}" cy="${n(op.h / 2)}" rx="${n(op.w / 2)}" `
          + `ry="${n(op.h / 2)}" fill="${fill}"${stroke}/>`);
      }
      return group(`<line x1="0" y1="0" x2="${n(op.w)}" y2="0" stroke="${paint(op.stroke ?? 'ink')}" `
        + `stroke-width="${n(op.strokeWidth)}"/>`);
    }
    if (op.kind === 'draw') {
      const points = op.points.map(([x, y]) => `${n(x)},${n(y)}`).join(' ');
      return group(`<polyline points="${points}" fill="none" stroke="${paint(op.stroke)}" `
        + `stroke-width="${n(op.strokeWidth)}" stroke-linecap="round" stroke-linejoin="round"/>`
        + (op.arrow ? '<circle r="0" fill="none"/>' : ''));
    }
    if (op.kind === 'data') {
      const max = Math.max(...op.values.map(Math.abs), 1);
      const slot = op.w / op.values.length;
      const bar = slot * (1 - op.gap);
      const bars = op.values.map((value, index) => {
        const height = Math.max(0, (value / max) * op.h);
        return `<rect x="${n(index * slot + (slot - bar) / 2)}" y="${n(op.h - height)}" `
          + `width="${n(bar)}" height="${n(height)}" fill="${paint(op.fill)}"/>`;
      }).join('');
      return group(bars);
    }
    const label = op.kind === 'person' ? `person: ${op.pose}` : `image: ${op.src}`;
    const w = op.w ?? op.h * 0.62;
    return group(`<rect x="${n(-w / 2)}" y="${n(-op.h)}" width="${n(w)}" height="${n(op.h)}" `
      + `fill="none" stroke="#8E8E93" stroke-dasharray="10 8" stroke-width="3"/>`
      + `<text x="0" y="${n(-op.h / 2)}" text-anchor="middle" font-size="28" fill="#8E8E93">`
      + `${esc(label)}</text>`);
  }).join('');
}

function cameraGroup(frame, body) {
  const cx = frame.stage.width / 2;
  const cy = frame.stage.height / 2;
  const c = frame.camera;
  return `<g transform="translate(${n(cx + c.x)} ${n(cy + c.y)}) scale(${n(c.scale)}) translate(${n(-cx)} ${n(-cy)})">${body}</g>`;
}

function frameSvg(board, time) {
  const frame = boardFrame(board, time);
  const body = `<rect width="${frame.stage.width}" height="${frame.stage.height}" fill="${paint(frame.stage.background)}"/>`
    + cameraGroup(frame, paintOps(frame.ops));
  return `<figure><svg viewBox="0 0 ${frame.stage.width} ${frame.stage.height}" width="220" role="img" `
    + `aria-label="board t=${time}">${body}</svg><figcaption>t=${time.toFixed(2)}s · ${esc(frame.sceneId)}</figcaption></figure>`;
}

const [input, output] = process.argv.slice(2);
if (!input || !output) {
  console.error('usage: node tools/board_preview.mjs <board.json> <out.html>');
  process.exit(2);
}
const board = JSON.parse(readFileSync(input, 'utf8'));
if (board?.version !== 1) {
  console.error('board version must be 1');
  process.exit(1);
}
const count = 4;
const step = board.duration / count;
const times = Array.from({ length: count }, (_, i) => Math.min(board.duration - 1e-6, i * step + step / 3));
const html = `<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Board preview</title>
<style>
 body{font:14px/1.5 system-ui,sans-serif;background:#fff;color:#1D1D1F;margin:24px}
 h1{font-size:20px;margin:0 0 4px} p{color:#8E8E93;margin:0 0 24px}
 .row{display:flex;gap:18px;flex-wrap:wrap} figure{margin:0;text-align:center}
 figcaption{font-size:12px;color:#8E8E93;margin-top:6px}
</style>
<h1>Board — أوراق معاينة</h1>
<p>من نفس مُفسِّر K: <code>shared/js/board.js</code>. الألوان والخطوط بديلة؛ الشخص والصورة مربّعان بانتظار الأصل.</p>
<div class="row">${times.map(time => frameSvg(board, time)).join('')}</div>
</html>`;
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, html, 'utf8');
console.log(`wrote ${output} (${times.length} frames, deterministic)`);
