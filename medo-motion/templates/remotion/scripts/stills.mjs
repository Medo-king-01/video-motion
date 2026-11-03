#!/usr/bin/env node
import {spawnSync} from 'node:child_process';
import {mkdir, readFile} from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';

const project = process.cwd();
const beats = JSON.parse(await readFile(path.join(project, 'plan', 'beats.json'), 'utf8'));
const seconds = Number(beats.duration) > 0 ? Number(beats.duration) : 8;
const fps = 30;
const total = Math.max(1, Math.round(seconds * fps));
const rawArgs = process.argv.slice(2);
const index = rawArgs.indexOf('--motion-mode');
const motionMode = index < 0 ? (process.env.MEDO_MOTION_MODE || 'normal') : rawArgs[index+1];
if(!['normal','reduced'].includes(motionMode)){console.error('motion-mode must be normal or reduced');process.exit(2);}
const args = rawArgs.filter((_,i)=>i!==index && i!==index+1 || index<0);
let frames;
if (args.length) {
  const times = args.map(Number);
  if (times.some((time) => !Number.isFinite(time) || time < 0 || time >= seconds)) {
    console.error(`Still times must be finite seconds within 0..${seconds.toFixed(3)} (exclusive).`);
    process.exit(2);
  }
  frames = [...new Set(times.map((time) => Math.min(total - 1, Math.round(time * fps))))];
} else {
  frames = [...new Set([0, Math.floor(total * 0.28), Math.floor(total * 0.62), total - 1])];
}
const folder = path.resolve(project, 'out', 'remotion-stills');
await mkdir(folder, {recursive: true});
const launcher = path.join(project, 'scripts', 'launch-remotion.mjs');
for (const frame of frames) {
  const output = path.join(folder, `frame-${String(frame).padStart(5, '0')}.png`);
  const result = spawnSync(process.execPath, [
    launcher, 'still', 'src/index.ts', 'MedoReel', output,
    `--frame=${frame}`, '--scale=0.35', `--props=${JSON.stringify({motionMode})}`,
  ], {cwd: project, stdio: 'inherit'});
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log(`Rendered ${frames.length} review still(s) at ${frames.map((frame) => `${(frame / fps).toFixed(2)}s`).join(', ')} into ${folder}`);
