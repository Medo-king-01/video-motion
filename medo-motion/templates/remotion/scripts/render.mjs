#!/usr/bin/env node
import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {copyFile, mkdir, readFile, writeFile} from 'node:fs/promises';
import path from 'node:path';
import process from 'node:process';
import {validateTextDirection} from '../src/lib/text-direction.js';
import {isStageEnabled, normalizeStageSpec, validateStageSpec} from '../src/lib/stage.js';

const invocationStarted = process.hrtime.bigint();
const project = process.cwd();
const args = process.argv.slice(2);
const value = (name, fallback) => {
  const i = args.indexOf(name);
  return i === -1 ? fallback : args[i + 1];
};
const flag = (name) => args.includes(name);
const audioArg = value('--audio', null);
const silent = flag('--silent');
const motionMode = value('--motion-mode', process.env.MEDO_MOTION_MODE || 'normal');
if(!['normal','reduced'].includes(motionMode)){console.error('motion-mode must be normal or reduced');process.exit(2);}
const fromFrame = Number(value('--from-frame', 0));
const toFrameArg = value('--to-frame', null);
const toFrame = toFrameArg === null ? null : Number(toFrameArg);
const output = path.resolve(project, value('--out', 'out/remotion.mp4'));
const profilePath = `${output}.profile.json`;
const profile = flag('--profile');
const beatsPath = path.join(project, 'plan', 'beats.json');

function fail(message) {
  console.error(`Remotion render blocked: ${message}`);
  process.exit(2);
}

function wavDuration(buffer) {
  if (buffer.toString('ascii', 0, 4) !== 'RIFF' || buffer.toString('ascii', 8, 12) !== 'WAVE') return null;
  let byteRate = 0;
  let dataBytes = 0;
  for (let offset = 12; offset + 8 <= buffer.length;) {
    const id = buffer.toString('ascii', offset, offset + 4);
    const size = buffer.readUInt32LE(offset + 4);
    if (id === 'fmt ' && size >= 16) byteRate = buffer.readUInt32LE(offset + 16);
    if (id === 'data') dataBytes = size;
    offset += 8 + size + (size % 2);
  }
  return byteRate > 0 && dataBytes > 0 ? dataBytes / byteRate : null;
}

const beats = JSON.parse(await readFile(beatsPath, 'utf8'));
const duration = Number(beats.duration);
const fps = Number(beats.fps ?? 30);
if (!Number.isFinite(duration) || duration <= 0) fail('set the measured VO duration first: python3 tools/vo_length.py <vo.wav> --json plan/beats.json');
if (fps !== 30) fail(`the locked brand frame rate is 30 fps, but plan/beats.json says ${fps}`);
if (!Number.isInteger(fromFrame) || fromFrame < 0 || (toFrame !== null && (!Number.isInteger(toFrame) || toFrame <= fromFrame))) {
  fail('--from-frame/--to-frame must be a non-empty, half-open integer range');
}
if (toFrame !== null && toFrame > Math.round(duration * fps)) fail('requested frame range exceeds the approved timeline');
const endFrame = toFrame ?? Math.round(duration * fps);
if (fromFrame >= endFrame) fail('requested frame range starts at or beyond the timeline end');
if (!Array.isArray(beats.scenes) || beats.scenes.length === 0) fail('plan/beats.json has no scenes; regenerate it from the VO');
const last = beats.scenes.at(-1);
if (Math.abs(Number(last.end) - duration) > 0.02) fail('the final scene boundary must equal the measured VO duration');
let cursor = 0;
for (const [index, scene] of beats.scenes.entries()) {
  if (!Number.isFinite(Number(scene.start)) || !Number.isFinite(Number(scene.end)) || Number(scene.end) <= Number(scene.start)) {
    fail(`scene ${index + 1} has invalid start/end times`);
  }
  if (Math.abs(Number(scene.start) - cursor) > 0.02) fail(`scene ${index + 1} leaves a gap or overlaps the previous scene`);
  cursor = Number(scene.end);
}
// Text motion is an explicit agent decision per scene (no default style).
const dirPath = path.join(project, 'plan', 'text-direction.json');
const direction = existsSync(dirPath) ? JSON.parse(await readFile(dirPath, 'utf8')) : {};
const copyPath = path.join(project, 'plan', 'copy.json');
const copy = existsSync(copyPath) ? JSON.parse(await readFile(copyPath, 'utf8')) : null;
const fontsPath = path.join(project, 'assets', 'fonts', 'fonts.json');
const fonts = existsSync(fontsPath) ? (JSON.parse(await readFile(fontsPath, 'utf8')).families || {}) : null;
const dirReport = validateTextDirection(direction, beats, copy, fonts);
if (dirReport.errors.length) fail('Text direction incomplete — the agent must choose styles per scene:\n' + dirReport.errors.join('\n'));

const stagePath = path.join(project, 'plan', 'stage.json');
if (existsSync(stagePath)) {
  const stageDoc = JSON.parse(await readFile(stagePath, 'utf8'));
  const stageErrors = validateStageSpec(stageDoc);
  if (stageErrors.length) fail('Invalid plan/stage.json:\n' + stageErrors.join('\n'));
  if (isStageEnabled(stageDoc)) {
    const normStage = normalizeStageSpec(stageDoc);
    const copyIds = new Set(((copy?.copy) || []).filter((c) => c && typeof c.id === 'string' && String(c.text || '').trim()).map((c) => c.id));
    for (const slot of normStage.over.header.slots) {
      if (!copyIds.has(slot.copyId)) {
        fail(`plan/stage.json header slot "${slot.id}" references missing copyId "${slot.copyId}" in plan/copy.json`);
      }
    }
  }
}

// Guard against shipping the template's placeholder copy: STORY must be replaced with the
// approved per-scene text, one card per scene, before a final render.
const dataSource = await readFile(path.join(project, 'src', 'data.ts'), 'utf8').catch(() => null);
if (dataSource !== null) {
  const placeholders = ['اكتب عنوان المشهد', 'حط هنا الجملة الأساسية', 'الحركة والإيقاع بيساعدوا'];
  const hit = placeholders.find((ph) => dataSource.includes(ph));
  if (hit) fail(`src/data.ts still contains placeholder copy (“${hit}”) — replace STORY with the approved per-scene text (one card per scene) before rendering`);
  const cards = (dataSource.match(/eyebrow\s*:/g) || []).length;
  if (cards < beats.scenes.length) fail(`STORY has ${cards} card(s) but the timeline has ${beats.scenes.length} scenes — bind one card to each scene in src/data.ts`);
}
if (!audioArg && !silent) fail('pass --audio out/vo24.wav, or explicitly use --silent for a visual-only render');
if (existsSync(output)) fail(`output already exists: ${output}; choose a new --out path/version`);
if (profile && existsSync(profilePath)) fail(`profile already exists: ${profilePath}`);

let props = {audioFile: null, previewOnly: false, motionMode};
if (audioArg) {
  const audioPath = path.resolve(project, audioArg);
  const audio = await readFile(audioPath).catch(() => null);
  if (!audio) fail(`audio file not found: ${audioArg}`);
  const measured = wavDuration(audio);
  if (measured === null) fail('audio must be a PCM WAV (prepare out/vo24.wav as described in AGENTS.md)');
  // One frame (1/fps) is the largest difference the frame grid can even represent; 150 ms would
  // silently clip the VO or leave a silent tail, so anything larger must be fixed at the source.
  const frameTol = 1 / fps;
  if (Math.abs(measured - duration) > frameTol) {
    fail(`audio is ${measured.toFixed(3)}s but the approved timeline is ${duration.toFixed(3)}s `
      + `(tolerance one frame = ${frameTol.toFixed(4)}s) — trim/pad the VO to the measured beats: `
      + `ffmpeg -i <vo> -t ${duration.toFixed(4)} out/vo24.wav`);
  }
  const publicAudio = path.join(project, 'public', 'vo.wav');
  await mkdir(path.dirname(publicAudio), {recursive: true});
  await copyFile(audioPath, publicAudio);
  props = {audioFile: 'vo.wav', previewOnly: false, motionMode};
}

await mkdir(path.dirname(output), {recursive: true});
const propsFile = path.join(project, 'cache', 'remotion-props.json');
await mkdir(path.dirname(propsFile), {recursive: true});
await writeFile(propsFile, `${JSON.stringify(props)}\n`);
const launcher = path.join(project, 'scripts', 'launch-remotion.mjs');
const renderArgs = [
  launcher, 'render', 'src/index.ts', 'MedoReel', output,
  `--props=${propsFile}`, '--codec=h264', '--crf=13', '--pixel-format=yuv420p',
];
if (fromFrame !== 0 || endFrame !== Math.round(duration * fps)) renderArgs.push(`--frames=${fromFrame}-${endFrame - 1}`);
const renderStarted = process.hrtime.bigint();
const result = spawnSync(process.execPath, renderArgs, {cwd: project, stdio: 'inherit'});
const renderMs = Number(process.hrtime.bigint()-renderStarted)/1e6;
if (result.error) fail(result.error.message);
if (result.status !== 0) process.exit(result.status ?? 1);
if(profile)await writeFile(profilePath,JSON.stringify({version:1,engine:'R',motionMode,frames:endFrame-fromFrame,renderMs,wallMs:Number(process.hrtime.bigint()-invocationStarted)/1e6,scope:'Render subprocess includes Remotion bundle, browser, capture and encode; no independent frame or GPU timing.'},null,2)+'\n',{flag:'wx'});
console.log(`Rendered ${output} · ${duration.toFixed(3)}s · ${Math.round(duration * fps)} frames @ ${fps}fps`);
