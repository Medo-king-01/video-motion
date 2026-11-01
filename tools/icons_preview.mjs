#!/usr/bin/env node
// QA preview for the icon layer: draws every icon through the engine-K canvas painter (lib/icons.js)
// and writes one contact sheet PNG. Needs the toolkit: bash tools/setup.sh
//
//   eval "$(node tools/chromium.mjs --env)" && node tools/icons_preview.mjs --out icons-k.png
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const opt = (k, d) => { const i = process.argv.indexOf('--' + k); return i < 0 ? d : process.argv[i + 1]; };
const out = path.resolve(opt('out', 'icons-k.png'));
const times = String(opt('times', '0.3,0.6,1.0,2.0')).split(',').map(Number);
const cell = Number(opt('cell', 168));
const group = String(opt('group', ''));
const limit = Number(opt('limit', 0));
const colsArg = Number(opt('cols', 0));

const req = createRequire(path.join(root, 'tools', 'toolkit', 'package.json'));
const { chromium } = req('playwright-core');
const src = await readFile(path.join(root, 'medo-motion', 'templates', 'render', 'lib', 'icons.js'), 'utf8');
const shim = src.replace(/^export default .*$/gm, '').replace(/^export\s+/gm, '') + '\nreturn { ICONS, drawIcon };';

const browser = await chromium.launch({ headless: true, ...(process.env.KHAAM_CHROMIUM ? { executablePath: process.env.KHAAM_CHROMIUM } : {}) });
const page = await browser.newPage();
await page.setContent(`<style>html,body{margin:0;background:#473938}</style><canvas id="c"></canvas>`);
const manifest = JSON.parse(await readFile(path.join(root, 'medo-motion', 'icons', 'manifest.json'), 'utf8'));
const meta = new Map(manifest.icons.map(i => [i.id, i]));
const dataUrl = await page.evaluate(({ code, times, cell, group, limit, colsArg, meta }) => {
  const { ICONS, drawIcon } = new Function(code)();
  let names = Object.keys(ICONS).filter(n => !group || meta[n]?.group === group);
  if (limit && names.length > limit) {
    const step = names.length / limit;
    names = Array.from({ length: limit }, (_, i) => names[Math.floor(i * step)]);
  }
  const cols = colsArg || names.length;
  const rows = Math.ceil(names.length / cols);
  const c = document.getElementById('c');
  c.width = cols * cell; c.height = times.length * rows * cell;
  const ctx = c.getContext('2d');
  ctx.fillStyle = '#473938'; ctx.fillRect(0, 0, c.width, c.height);
  times.forEach((t, r) => names.forEach((n, i) => {
    const col = i % cols, row = Math.floor(i / cols);
    const dark = r % 2 === 0;
    const x = col * cell, y = (r * rows + row) * cell, pad = 8;
    ctx.fillStyle = dark ? '#2E2423' : '#F3F2F1';
    ctx.fillRect(x + pad, y + pad, cell - pad * 2, cell - pad * 2);
    drawIcon(ctx, n, t, { x: x + cell / 2, y: y + cell / 2, size: cell * 0.62,
      color: dark ? '#F3F2F1' : '#473938', accent: dark ? '#D97F68' : '#CB271B', loop: false });
  }));
  return c.toDataURL('image/png');
}, { code: shim, times, cell, group, limit, colsArg, meta: Object.fromEntries(meta) });

await writeFile(out, Buffer.from(dataUrl.split(',')[1], 'base64'));
await browser.close();
console.log(`engine K icon sheet -> ${out} (${manifest.icons.length} icons registered)`);
