#!/usr/bin/env node
// Offline capability probe, not a renderer and not evidence of hardware acceleration.
import http from 'node:http';
import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {probeGraphics} from './lib/gpu_probe.mjs';

const args=process.argv.slice(2);
let out=null,requirement='none';
const usage='Usage: node tools/gpu_preflight.mjs [--out fresh-report.json] [--require webgl2|webgpu|both]';
for(let i=0;i<args.length;i++){
  if(args[i]==='--help'){console.log(usage);process.exit(0);}
  if(args[i]==='--out'&&i+1<args.length&&out===null){out=args[++i];continue;}
  if(args[i]==='--require'&&i+1<args.length&&requirement==='none'){requirement=args[++i];continue;}
  throw Error(usage);
}
if(!['none','webgl2','webgpu','both'].includes(requirement))throw Error(usage);
if(out&&existsSync(out))throw Error('Refusing to overwrite report: '+out);
const here=path.dirname(fileURLToPath(import.meta.url));
const toolkit=path.resolve(process.env.MEDO_TOOLKIT||process.env.KHAAM_TOOLKIT||path.join(here,'toolkit'));
const require=createRequire(path.join(toolkit,'package.json'));
const {chromium}=(()=>{try{return require('playwright');}catch{return require('playwright-core');}})();
const browserPath=process.env.MEDO_CHROMIUM||process.env.KHAAM_CHROMIUM;
const server=http.createServer((req,res)=>{
  if(req.method!=='GET'||req.url!=='/'){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'});
  res.end('<!doctype html><title>Local graphics capability probe</title>');
});
let browser;
try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin=`http://127.0.0.1:${server.address().port}`;
  browser=await chromium.launch({headless:true,...(browserPath?{executablePath:browserPath}:{})});
  const page=await browser.newPage();
  await page.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  await page.goto(origin+'/');
  const result=await page.evaluate(probeGraphics);
  const report={version:1,browserVersion:browser.version(),...result,
    limitations:'Local functional smoke only. No raw adapter identifiers retained; software indicators are incomplete. A pass does not prove hardware acceleration, vgpu/Three compatibility, GPU encoding, reproducibility across devices, visual quality or safety.'};
  const json=JSON.stringify(report,null,2)+'\n';
  if(out)await writeFile(out,json,{flag:'wx'});else process.stdout.write(json);
  const failed=(requirement==='webgl2'||requirement==='both')&&report.webgl2.status!=='pass'||
    (requirement==='webgpu'||requirement==='both')&&report.webgpu.status!=='pass';
  if(failed)process.exitCode=1;
}finally{
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
}
