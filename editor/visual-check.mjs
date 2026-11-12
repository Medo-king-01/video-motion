#!/usr/bin/env node
/**
 * Visual check for the editor page — the part jsdom cannot do.
 *
 * Usage (with the editor already running):
 *   node tools/editor_server.py projects/demo/project.json --port 8777 &
 *   CHROME=/usr/bin/chromium node editor/visual-check.mjs --url http://127.0.0.1:8777 --out /tmp/editor.png
 *
 * Needs `puppeteer-core` (and any Chromium). When `@sparticuz/chromium` is installed it is used to
 * locate the bundled binary; otherwise pass `--chrome <path>` or set `CHROME`.
 * Exit codes: 0 all checks pass, 1 a check failed, 2 cannot run (no browser / no server).
 *
 * What it proves: the document really is RTL, nothing overflows horizontally, the RTL column order is
 * the intended one (media bin on the right), the preview <img> decodes a real frame, the caption's
 * animation select and the `+ run` button round-trip through the API, and the console stays clean.
 * What it does not prove: pointer interaction (drag/select), other engines, other screen sizes.
 */
import process from 'node:process';
import { writeFile } from 'node:fs/promises';

const args = process.argv.slice(2);
const value = (name, fallback) => {
  const index = args.indexOf(name);
  return index === -1 ? fallback : args[index + 1];
};
const url = value('--url', 'http://127.0.0.1:8777');
const out = value('--out', null);
const frame = Number(value('--frame', '24'));

async function locateBrowser() {
  const explicit = value('--chrome', process.env.CHROME || null);
  if (explicit) return { executablePath: explicit, args: [] };
  try {
    const chromium = (await import('@sparticuz/chromium')).default;
    return { executablePath: await chromium.executablePath(), args: chromium.args };
  } catch {
    return null;
  }
}

const checks = [];
const check = (name, ok, detail) => checks.push({ name, ok: Boolean(ok), detail });

const browserInfo = await locateBrowser();
if (!browserInfo) {
  console.error('no browser: install puppeteer-core + @sparticuz/chromium, or pass --chrome <path>');
  process.exit(2);
}

let puppeteer;
try {
  puppeteer = (await import('puppeteer-core')).default;
} catch {
  console.error('puppeteer-core is not installed (npm i puppeteer-core)');
  process.exit(2);
}

const browser = await puppeteer.launch({
  executablePath: browserInfo.executablePath,
  args: [...browserInfo.args, '--font-render-hinting=none', '--lang=ar'],
  defaultViewport: { width: 1400, height: 900 },
  headless: true,
});
const page = await browser.newPage();
const errors = [];
page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()); });
page.on('pageerror', (error) => errors.push('pageerror: ' + error.message));

try {
  await page.goto(url + '/', { waitUntil: 'networkidle0', timeout: 30000 });
} catch (error) {
  await browser.close();
  console.error(`cannot load ${url}: ${error.message}`);
  process.exit(2);
}
await page.waitForSelector('.clip', { timeout: 30000 });

// park the playhead where the first caption is fully drawn, so the screenshot shows real type
await page.evaluate((target) => { window.eval(`frame = ${target}; render();`); }, frame);
await new Promise((resolve) => setTimeout(resolve, 2000));

const view = await page.evaluate(() => {
  const hex = (value) => {
    const text = String(value || '').replace('#', '');
    return [0, 2, 4].map((offset) => parseInt(text.slice(offset, offset + 2), 16));
  };
  const block = (window.eval('state.project.texts[0]') || {});
  const wanted = [{ name: 'block colour', rgb: hex(block.color || '#ffffff'), min: 80 }];
  if ((block.runs || [])[0]?.color) wanted.push({ name: 'run colour', rgb: hex(block.runs[0].color), min: 20 });
  const stage = document.getElementById('frame');
  const probe = document.createElement('canvas');
  probe.width = stage.naturalWidth; probe.height = stage.naturalHeight;
  probe.getContext('2d').drawImage(stage, 0, 0);
  const data = probe.getContext('2d').getImageData(0, 0, probe.width, probe.height).data;
  const hits = wanted.map(() => 0);
  for (let index = 0; index < data.length; index += 4) {
    const [r, g, b] = [data[index], data[index + 1], data[index + 2]];
    for (let slot = 0; slot < wanted.length; slot += 1) {
      if (Math.abs(r - wanted[slot].rgb[0]) < 20 && Math.abs(g - wanted[slot].rgb[1]) < 20
        && Math.abs(b - wanted[slot].rgb[2]) < 20) hits[slot] += 1;
    }
  }
  const bin = document.querySelector('aside') || document.getElementById('bin');
  return {
    dir: document.documentElement.dir || document.body.dir,
    computedDirection: getComputedStyle(document.body).direction,
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
    timelineOverflow: document.getElementById('timeline').scrollWidth
      - document.getElementById('timeline').clientWidth,
    tracks: document.querySelectorAll('.track').length,
    clips: document.querySelectorAll('.clip').length,
    captions: document.querySelectorAll('#captions .fx').length,
    mediaBin: document.querySelectorAll('#bin .cell').length,
    animationKinds: [...new Set([...document.querySelectorAll('#captions select')]
      .flatMap((select) => [...select.options].map((option) => option.value)))],
    stageNatural: [stage.naturalWidth, stage.naturalHeight],
    inkHits: wanted.map((item, slot) => ({ name: item.name, count: hits[slot], min: item.min })),
    binX: Math.round(bin.getBoundingClientRect().x),
    stageX: Math.round(document.getElementById('stage').getBoundingClientRect().x),
    backend: document.getElementById('backendTag').textContent.trim(),
  };
});

check('document is rtl', view.dir === 'rtl' && view.computedDirection === 'rtl', view.computedDirection);
check('no horizontal page overflow', view.scrollWidth <= view.clientWidth + 1,
  `${view.scrollWidth}/${view.clientWidth}`);
check('timeline does not overflow', view.timelineOverflow <= 1, view.timelineOverflow);
check('media bin sits to the right of the stage', view.binX > view.stageX,
  `bin ${view.binX} > stage ${view.stageX}`);
check('tracks and clips are drawn', view.tracks >= 1 && view.clips >= 1, `${view.tracks}/${view.clips}`);
check('media bin is populated', view.mediaBin >= 1, view.mediaBin);
check('preview loaded a real frame', view.stageNatural[0] > 0 && view.stageNatural[1] > 0,
  view.stageNatural.join('x'));
for (const hit of view.inkHits) {
  check(`preview draws the ${hit.name}`, hit.count >= hit.min, `${hit.count} px (min ${hit.min})`);
}
check('animation kinds include the letter modes',
  view.animationKinds.includes('letters-up') && view.animationKinds.includes('letters-fade'),
  view.animationKinds.join(','));
check('a backend is reported', /^[PKR]\b/.test(view.backend), view.backend);

// the animation select must reach the server and come back in the state
const before = await page.evaluate(() => window.eval('state.project.texts[0].animation.kind'));
const target = before === 'letters-fade' ? 'letters-up' : 'letters-fade';
await page.select('#captions .fx select', target);
await new Promise((resolve) => setTimeout(resolve, 900));
const after = await page.evaluate(() => window.eval('state.project.texts[0].animation.kind'));
check('animation select round-trips through the API', after === target, `${before} -> ${after}`);

// + run must add a run the checker accepts (no 400)
const runsBefore = await page.evaluate(() => (window.eval('state.project.texts[0].runs') || []).length);
for (const button of await page.$$('#captions button')) {
  const label = await page.evaluate((element) => element.textContent.trim(), button);
  if (label === '+ run') { await button.click(); break; }
}
await new Promise((resolve) => setTimeout(resolve, 900));
const runsAfter = await page.evaluate(() => (window.eval('state.project.texts[0].runs') || []).length);
check('+ run adds a run the checker accepts', runsAfter === runsBefore + 1,
  `${runsBefore} -> ${runsAfter}`);

check('console stayed clean', errors.length === 0, errors.join(' | ') || 'no errors');

if (out) {
  await page.screenshot({ path: out });
  await writeFile(`${out}.json`, JSON.stringify({ url, view, checks }, null, 1));
}
await browser.close();

const failed = checks.filter((item) => !item.ok);
for (const item of checks) console.log(`${item.ok ? 'ok  ' : 'FAIL'} ${item.name} (${item.detail})`);
console.log(failed.length ? `\n${failed.length} failed` : `\nall ${checks.length} checks passed`);
process.exit(failed.length ? 1 : 0);
