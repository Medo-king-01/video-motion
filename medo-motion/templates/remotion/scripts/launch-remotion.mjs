import {spawnSync} from 'node:child_process';
import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {validateTextDirection} from '../src/lib/text-direction.js';
import {validateStageSpec} from '../src/lib/stage.js';

const project = process.cwd();
const repoChromium = path.resolve(project, '../../tools/chromium.mjs');
const cli = path.join(project, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');

function fail(message) {
  console.error(`Remotion setup: ${message}`);
  process.exit(2);
}

// Every visible text element must have an explicit agent-chosen motion style.
const beatsPath = path.join(project, 'plan', 'beats.json');
if (existsSync(beatsPath)) {
  const beats = JSON.parse(readFileSync(beatsPath, 'utf8'));
  const dirPath = path.join(project, 'plan', 'text-direction.json');
  const direction = existsSync(dirPath) ? JSON.parse(readFileSync(dirPath, 'utf8')) : {};
  const copyPath = path.join(project, 'plan', 'copy.json');
  const copy = existsSync(copyPath) ? JSON.parse(readFileSync(copyPath, 'utf8')) : null;
  const fontsPath = path.join(project, 'assets', 'fonts', 'fonts.json');
  const fonts = existsSync(fontsPath) ? (JSON.parse(readFileSync(fontsPath, 'utf8')).families || {}) : null;
  const {errors} = validateTextDirection(direction, beats, copy, fonts);
  if (errors.length) fail('Text direction incomplete — the agent must choose styles for every text element:\n' + errors.join('\n'));
  const stagePath = path.join(project, 'plan', 'stage.json');
  if (existsSync(stagePath)) {
    const stageDoc = JSON.parse(readFileSync(stagePath, 'utf8'));
    const stageErrors = validateStageSpec(stageDoc);
    if (stageErrors.length) fail('Invalid plan/stage.json:\n' + stageErrors.join('\n'));
  }
}

let browser = null;
if (process.env.REMOTION_BROWSER_EXECUTABLE) {
  browser = {executablePath: process.env.REMOTION_BROWSER_EXECUTABLE, libraryPath: null, args: []};
} else if (existsSync(repoChromium)) {
  const resolved = spawnSync(process.execPath, [repoChromium, '--json'], {cwd: project, encoding: 'utf8'});
  if (resolved.status !== 0) {
    fail(`shared Chromium is not ready. Run [1mbash ../../tools/setup.sh[0m from the project, or set REMOTION_BROWSER_EXECUTABLE.\n${resolved.stderr || ''}`);
  }
  browser = JSON.parse(resolved.stdout);
}

const args = process.argv.slice(2);
if (browser) args.push(`--browser-executable=${browser.executablePath}`);
const env = {...process.env};
if (browser?.libraryPath) {
  env.LD_LIBRARY_PATH = [browser.libraryPath, env.LD_LIBRARY_PATH].filter(Boolean).join(':');
}
if (browser?.args?.length) env.REMOTION_CHROMIUM_ARGS = browser.args.join(' ');

const result = spawnSync(process.execPath, [cli, ...args], {cwd: project, env, stdio: 'inherit'});
if (result.error) fail(result.error.message);
process.exit(result.status ?? 1);
