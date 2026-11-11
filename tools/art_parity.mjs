#!/usr/bin/env node
// Engine-K half of tools/art_parity.py: draws every case through `render/lib/art.js` in the studio
// Chromium and writes one transparent PNG per case. Not meant to be run by hand.
//
//   node tools/art_parity.mjs --cases cases.json --out dir
import { createRequire } from 'node:module';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const opt = k => { const i = process.argv.indexOf('--' + k); return i < 0 ? null : process.argv[i + 1]; };
const casesPath = opt('cases'), out = opt('out');
if (!casesPath || !out) { console.error('usage: art_parity.mjs --cases cases.json --out dir'); process.exit(2); }

const spec = JSON.parse(await readFile(casesPath, 'utf8'));
const lib = path.join(root, 'medo-motion', 'templates', 'render', 'lib');
const strip = src => src.replace(/^import .*$/gm, '').replace(/^export default .*$/gm, '').replace(/^export\s+/gm, '');
const code = strip(await readFile(path.join(lib, 'brand.js'), 'utf8')) + '\n' + strip(await readFile(path.join(lib, 'art.js'), 'utf8'))
  + '\nreturn { drawArt, artSize, PALETTE };';
const fonts = {};
for (const [family, file] of Object.entries(spec.fonts || {})) fonts[family] = (await readFile(file)).toString('base64');
const images = {};
for (const [name, file] of Object.entries(spec.images || {})) images[name] = (await readFile(file)).toString('base64');

const req = createRequire(path.join(root, 'tools', 'toolkit', 'package.json'));
const { chromium } = req('playwright-core');
const executablePath = process.env.MEDO_CHROMIUM || process.env.KHAAM_CHROMIUM;
const args = (process.env.MEDO_CHROMIUM_ARGS || '').split(/\s+/).filter(Boolean);
const browser = await chromium.launch({ headless: true, args, ...(executablePath ? { executablePath } : {}) });
try {
  const page = await browser.newPage();
  await page.setContent('<canvas id="c"></canvas>');
  const results = await page.evaluate(async ({ code, cases, scenes, fonts, images }) => {
    for (const [family, b64] of Object.entries(fonts)) {
      const face = new FontFace(family, `url(data:font/ttf;base64,${b64})`, { weight: '800' });
      await face.load(); document.fonts.add(face);
    }
    const loaded = {};
    for (const [name, b64] of Object.entries(images)) {
      const img = new Image(); img.src = `data:image/png;base64,${b64}`; await img.decode(); loaded[name] = img;
    }
    const { drawArt, artSize, PALETTE } = new Function(code)();
    const canvas = document.getElementById('c');
    const output = {};
    for (const item of cases) {
      const { w, h } = artSize(item.art, item.options);
      canvas.width = w; canvas.height = h;
      const ctx = canvas.getContext('2d');
      drawArt(ctx, item.art, w / 2, h / 2, item.options);
      output[item.id] = { w, h, png: canvas.toDataURL('image/png') };
    }
    for (const scene of scenes) {
      canvas.width = scene.w; canvas.height = scene.h;
      const ctx = canvas.getContext('2d');
      for (const op of scene.ops) {
        if (op.op === 'fill') { ctx.fillStyle = PALETTE[op.color]; ctx.fillRect(0, 0, scene.w, scene.h); }
        else if (op.op === 'art') drawArt(ctx, op.art, op.cx, op.cy, op.options || {}, op.place || {});
        else if (op.op === 'image') {
          const img = loaded[op.image], ih = op.height, iw = Math.trunc(img.width * ih / img.height);
          const [ax, ay] = op.anchor || [0.5, 0.5];
          ctx.imageSmoothingQuality = 'high';
          ctx.drawImage(img, op.cx - ax * iw, op.cy - ay * ih, iw, ih);
        } else if (op.op === 'text') {
          ctx.save();
          ctx.font = `800 ${op.size}px "Cairo", sans-serif`; ctx.direction = 'rtl'; ctx.textAlign = 'center';
          ctx.textBaseline = 'alphabetic'; ctx.fillStyle = PALETTE[op.color];
          const m = ctx.measureText(op.text);
          ctx.fillText(op.text, op.cx, op.cy + (m.actualBoundingBoxAscent - m.actualBoundingBoxDescent) / 2);
          ctx.restore();
          scene.textWidths = { ...(scene.textWidths || {}), [op.text]: m.actualBoundingBoxLeft + m.actualBoundingBoxRight };
        }
      }
      output[scene.id] = { w: scene.w, h: scene.h, png: canvas.toDataURL('image/png'), textWidths: scene.textWidths || {} };
    }
    return output;
  }, { code, cases: spec.cases || [], scenes: spec.scenes || [], fonts, images });
  await mkdir(out, { recursive: true });
  const meta = {};
  for (const [id, item] of Object.entries(results)) {
    await writeFile(path.join(out, `${id}.png`), Buffer.from(item.png.split(',')[1], 'base64'));
    meta[id] = { w: item.w, h: item.h, textWidths: item.textWidths || {} };
  }
  await writeFile(path.join(out, 'k.json'), JSON.stringify(meta, null, 2) + '\n');
  console.log(`engine K drew ${Object.keys(results).length} image(s) -> ${out}`);
} finally {
  await browser.close();
}
