#!/usr/bin/env node
// Local manual-seek functional probe; no claims about hardware acceleration or production fidelity.
import http from 'node:http';
import {createRequire} from 'node:module';
import {writeFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const args=process.argv.slice(2),usage='Usage: node tools/waapi_preflight.mjs [--out fresh-report.json]';
if(args.length===1&&args[0]==='--help'){console.log(usage);process.exit(0);}
if(args.length!==0&&(args.length!==2||args[0]!=='--out'))throw Error(usage);
const out=args[1];if(out&&existsSync(out))throw Error('Refusing to overwrite report: '+out);
const here=path.dirname(fileURLToPath(import.meta.url));
const toolkit=path.resolve(process.env.MEDO_TOOLKIT||process.env.KHAAM_TOOLKIT||path.join(here,'toolkit'));
const require=createRequire(path.join(toolkit,'package.json'));
const {chromium}=(()=>{try{return require('playwright');}catch{return require('playwright-core');}})();
const browserPath=process.env.MEDO_CHROMIUM||process.env.KHAAM_CHROMIUM;
const server=http.createServer((req,res)=>{
  if(req.method!=='GET'||req.url!=='/'){res.writeHead(404);res.end();return;}
  res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'",'Cache-Control':'no-store'});
  res.end('<!doctype html><title>Local manual seek test</title><div id="probe" style="width:20px;height:20px;background:#CB271B"></div>');
});
let browser;
try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  const origin=`http://127.0.0.1:${server.address().port}`;
  browser=await chromium.launch({headless:true,...(browserPath?{executablePath:browserPath}:{})});
  const page=await browser.newPage();
  await page.route('**/*',route=>new URL(route.request().url()).origin===origin?route.continue():route.abort());
  await page.goto(origin+'/');
  const result=await page.evaluate(async()=>{
    const element=document.getElementById('probe');
    if(typeof element.animate!=='function')return {status:'unavailable'};
    const animation=element.animate([{transform:'translateX(0px)',opacity:0},{transform:'translateX(100px)',opacity:1}],{duration:1000,fill:'both',easing:'linear'});
    try{
      animation.pause();await animation.ready;
      const sample=frame=>{animation.currentTime=frame*1000/30;const style=getComputedStyle(element),matrix=new DOMMatrixReadOnly(style.transform);
        return {x:matrix.m41,opacity:Number(style.opacity),paused:animation.playState==='paused'};};
      const started=performance.now(),forward=Array.from({length:30},(_,i)=>sample(i));let reverseMatches=0;
      for(let i=29;i>=0;i--){const value=sample(i);if(value.x===forward[i].x&&value.opacity===forward[i].opacity&&value.paused)reverseMatches++;}
      const expected=forward.every((v,i)=>Math.abs(v.x-i*100/30)<.001&&Math.abs(v.opacity-i/30)<.00001&&v.paused);
      return {status:expected&&reverseMatches===30?'pass':'fail',frames:30,reverseMatches,expectedValues:expected,elapsedMs:performance.now()-started};
    }finally{animation.cancel();}
  });
  const report={version:1,browserVersion:browser.version(),...result,
    limitations:'One local paused WAAPI transform/opacity seek smoke test. Timing is not a benchmark. No proof of hardware acceleration, performance benefit, Remotion integration, text, cross-browser pixel identity, VO timing or production suitability.'};
  const json=JSON.stringify(report,null,2)+'\n';
  if(out)await writeFile(out,json,{flag:'wx'});else process.stdout.write(json);
  if(result.status!=='pass')process.exitCode=1;
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
