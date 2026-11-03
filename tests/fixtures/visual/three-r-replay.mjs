import {createServer} from 'node:http';
import {readFile} from 'node:fs/promises';
import {createRequire} from 'node:module';
import path from 'node:path';
const req=createRequire(path.join(process.env.MEDO_TOOLKIT,'package.json'));
const {chromium}=req('playwright-core');
const script=await readFile(process.argv[2]);
const server=createServer((request,response)=>{
  if(request.url==='/'){response.writeHead(200,{'Content-Type':'text/html'});response.end('<div id="root"></div><script src="/bundle.js"></script>');}
  else if(request.url==='/bundle.js'){response.writeHead(200,{'Content-Type':'text/javascript'});response.end(script);}
  else{response.writeHead(404);response.end();}
});
let browser;
try{
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  browser=await chromium.launch({headless:true,executablePath:process.env.MEDO_CHROMIUM});
  const page=await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  await page.waitForFunction(()=>typeof window.renderProbe==='function');
  const sample=async(frame,reduced=false)=>page.evaluate(({time,reduced})=>window.renderProbe(time,reduced),{time:frame/30,reduced});
  const forward=[];for(let i=0;i<30;i++)forward.push(await sample(i));
  let reverseMatches=0;for(let i=29;i>=0;i--)if(await sample(i)===forward[i])reverseMatches++;
  const reduced=await sample(15,true);
  const cleanups=await page.evaluate(()=>window.closeProbe());
  const failure=await page.evaluate(()=>window.failureProbe());
  const scopedEffect=await page.evaluate(()=>window.scopedEffectProbe());
  const scopedFailure=await page.evaluate(()=>window.scopedFailureProbe());
  console.log(JSON.stringify({frames:forward.length,reverseMatches,distinct:forward[0]!==forward[29],reducedMatchesStart:reduced===forward[0],reducedDifferent:reduced!==forward[15],cleanups,failure,scopedEffect,scopedFailure}));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
