import {spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const project = process.cwd();
const repoChromium = path.resolve(project, '../../tools/chromium.mjs');
const cli = path.join(project, 'node_modules', '@remotion', 'cli', 'remotion-cli.js');

function fail(message) {
  console.error(`Remotion setup: ${message}`);
  process.exit(2);
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
