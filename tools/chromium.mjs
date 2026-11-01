#!/usr/bin/env node
// Resolve a working Chromium for the Canvas/Playwright engine (engine K).
//
// Why: `npx playwright install chromium` downloads from cdn.playwright.dev,
// which some sandboxes block. @sparticuz/chromium ships a Chromium build inside
// the npm tarball (registry.npmjs.org), so it installs anywhere npm works.
// Its shared libs (AL2023) are shipped brotli-compressed and must be extracted
// once and put on LD_LIBRARY_PATH, otherwise Chromium dies with
// "libnspr4.so: cannot open shared object file".
//
// Usage:
//   node tools/chromium.mjs --env     # prints `export KHAAM_CHROMIUM=...` lines
//   node tools/chromium.mjs --path    # prints the executable path only
//   node tools/chromium.mjs --json    # machine-readable browser path, libraries and args
//   node tools/chromium.mjs --check   # launches a page and prints the version
import { createRequire } from 'node:module';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import zlib from 'node:zlib';

const here = path.dirname(new URL(import.meta.url).pathname);
const toolkit = process.env.MEDO_TOOLKIT || path.join(here, 'toolkit');
const require = createRequire(path.join(toolkit, 'package.json'));

const mode = process.argv[2] || '--path';
const cache = process.env.MEDO_CHROMIUM_CACHE || path.join(os.homedir(), '.cache', 'medo-motion', 'chromium');
mkdirSync(cache, { recursive: true });

function libsDir(pkg) {
  const dir = path.join(cache, 'al2023');
  const marker = path.join(dir, '.done');
  if (existsSync(marker)) return path.join(dir, 'lib');
  const br = path.join(pkg, 'bin', 'al2023.tar.br');
  if (!existsSync(br)) return null;                    // older packages: not needed
  mkdirSync(dir, { recursive: true });
  const raw = zlib.brotliDecompressSync(readFileSync(br));
  const r = spawnSync('tar', ['-x', '-C', dir], { input: raw });
  if (r.status !== 0) throw new Error('failed to extract AL2023 libs: ' + (r.stderr || '').toString());
  writeFileSync(marker, 'ok');
  return fsLibs(dir);
}
function fsLibs(dir) {
  const p = path.join(dir, 'lib');
  return existsSync(p) ? p : dir;
}

let chromium, pkgDir;
pkgDir = path.join(toolkit, 'node_modules', '@sparticuz', 'chromium');
try {
  chromium = (await import(path.join(pkgDir, 'build', 'index.js'))).default
    ?? (await import(path.join(pkgDir, 'index.js'))).default;
} catch (e) {
  try { chromium = require('@sparticuz/chromium'); }
  catch (e2) {
    console.error('toolkit missing or incomplete: run `npm install` in ' + toolkit);
    console.error(String(e2.message || e.message));
    process.exit(2);
  }
}

const exe = await chromium.executablePath();
const libs = libsDir(pkgDir);

if (mode === '--path') {
  process.stdout.write(exe);
} else if (mode === '--json') {
  process.stdout.write(JSON.stringify({executablePath: exe, libraryPath: libs, args: chromium.args}));
} else if (mode === '--env') {
  console.log(`export KHAAM_CHROMIUM="${exe}"`);
  if (libs) console.log(`export LD_LIBRARY_PATH="${libs}\${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"`);
  console.log(`export MEDO_CHROMIUM_ARGS="${chromium.args.join(' ')}"`);
} else if (mode === '--check') {
  process.env.LD_LIBRARY_PATH = libs ? `${libs}:${process.env.LD_LIBRARY_PATH || ''}` : process.env.LD_LIBRARY_PATH;
  const { chromium: pw } = await import(path.join(toolkit, 'node_modules', 'playwright-core', 'index.mjs'));
  const b = await pw.launch({ executablePath: exe, args: [...chromium.args, '--no-sandbox'], headless: true });
  const p = await b.newPage({ viewport: { width: 320, height: 200 } });
  await p.setContent('<h1>ok</h1>');
  console.log('CHROMIUM_OK', await b.version());
  await b.close();
} else {
  console.error('usage: node tools/chromium.mjs [--env|--path|--json|--check]');
  process.exit(1);
}
