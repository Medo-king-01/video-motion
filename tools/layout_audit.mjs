#!/usr/bin/env node
// Use the existing K renderer and bundled browser; never install another runtime.
import {spawnSync} from 'node:child_process';
import {resolve,dirname,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {lstatSync} from 'node:fs';
const root=dirname(dirname(fileURLToPath(import.meta.url))),a=process.argv.slice(2);
const opt=k=>{const i=a.indexOf('--'+k);return i<0?null:a[i+1];};
try {
  if(!opt('project')||!opt('out'))throw Error('Usage: node tools/layout_audit.mjs --project projects/x --out cache/audit-v1 [--from 0 --to 1 --every 1 --replay]');
  const project=resolve(opt('project')),out=resolve(opt('out'));
  for(const target of [project,out])for(let p=target;;p=dirname(p)){
    try{if(lstatSync(p).isSymbolicLink())throw Error('Symlink path refused: '+p);}catch(e){if(e.code!=='ENOENT')throw e;}
    if(dirname(p)===p)break;
  }
  const config=spawnSync(process.execPath,[join(root,'tools/chromium.mjs'),'--json'],{encoding:'utf8'});
  if(config.status!==0)throw Error(config.stderr||'Chromium resolver failed');
  const browser=JSON.parse(config.stdout);
  const args=[join(project,'src/render.js'),'--audit','--out',out];
  if(a.includes('--replay'))args.push('--replay');
  for(const k of ['from','to','every','motion-mode'])if(opt(k)!==null)args.push('--'+k,opt(k));
  const r=spawnSync(process.execPath,args,{cwd:project,stdio:'inherit',env:{...process.env,
    MEDO_TOOLKIT:join(root,'tools/toolkit'),MEDO_CHROMIUM:browser.executablePath,
    LD_LIBRARY_PATH:[browser.libraryPath,process.env.LD_LIBRARY_PATH].filter(Boolean).join(':')}});
  if(r.error)throw r.error;
  process.exitCode=r.status??1;
}catch(e){console.error('Layout audit blocked:',e.message);process.exitCode=1;}
