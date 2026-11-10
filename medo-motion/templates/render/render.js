#!/usr/bin/env node
import { auditLayout } from './lib/layout.js';
import {performance} from 'node:perf_hooks';
// Copy this directory to <project>/src; package.json must contain "type":"module".
// node src/render.js --from 0 --to 3 --fps 30 --scale 1 --out cache/smoke --jpg
// Without --jpg: --out renders/previews --name "Smoke v1" [--audio mix.wav]. Silent if no --audio.
import http from 'node:http';
import {spawn} from 'node:child_process';
import {createRequire} from 'node:module';
import {once} from 'node:events';
import {readFile,stat,mkdir,writeFile,readdir} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath} from 'node:url';
const invocationStarted=performance.now();
const root=process.cwd(),src=path.dirname(fileURLToPath(import.meta.url)),a=process.argv.slice(2);
const opt=(k,d)=>{const i=a.indexOf('--'+k);return i<0?d:a[i+1];};
const {DURATION,scenes}=await import('./data.js');
import {validateTextDirection} from './lib/text-direction.js';
import {validateSlideWallSpec} from './lib/slide-wall.js';
import {validateOneTakeSpec} from './lib/one-take.js';
const from=Number(opt('from',0)),to=Number(opt('to',DURATION)),fps=Number(opt('fps',30)),scale=Number(opt('scale',1));
const crf=Number(opt('crf',18));
const motionMode=opt('motion-mode',process.env.MEDO_MOTION_MODE||'normal');
if(!['normal','reduced'].includes(motionMode))throw Error('motion-mode must be normal or reduced');
if(![from,to,fps,scale].every(Number.isFinite)||from<0||to<=from||fps<=0||scale<=0||scale>1)throw Error('Invalid range, fps or scale');
if(!Number.isFinite(crf)||crf<0||crf>51)throw Error('Invalid crf');
const count=Math.ceil((to-from)*fps-1e-8),out=path.resolve(opt('out','cache/smoke')),jpg=a.includes('--jpg');
// --alpha renders a transparent PNG sequence (no encoder) so a hybrid plan can composite the
// result over another engine's footage. JPEG cannot carry alpha, so the two modes are exclusive.
const alpha=a.includes('--alpha');
if(alpha&&jpg)throw Error('--alpha cannot be combined with --jpg');
// 30 fps is the master rate; the hybrid compositor asks for 15 when it builds a draft preview.
if(alpha&&fps!==30&&fps!==15)throw Error('--alpha renders at 30 fps, or 15 for a hybrid draft');
const seq=jpg||alpha;
const audit=a.includes('--audit'), replay=a.includes('--replay'), platformUi=a.includes('--platform-ui'), profile=a.includes('--profile'), every=Number(opt('every',1));
if(replay&&!audit)throw Error('--replay requires --audit');
if(audit&&(!Number.isInteger(every)||every<1))throw Error('--every must be a positive frame stride');
if(audit&&(fps!==30||to>DURATION+1e-8))throw Error('Audit requires native 30 fps and a range inside the timeline');
// --only draws a named subset of the timeline's scenes (comma-separated ids) and leaves every
// other moment transparent, so one K project can feed more than one hybrid overlay.
const only=String(opt('only','')).split(',').map(v=>v.trim()).filter(Boolean);
if(only.length&&!only.every(id=>/^[A-Za-z0-9_-]{1,64}$/.test(id)))throw Error('--only takes comma-separated scene ids (letters, digits, _ or -)');
if(new Set(only).size!==only.length)throw Error('--only lists the same scene twice');
// Fail here, not inside the browser: an unknown id there would stall the page until its timeout.
const unknownScenes=only.filter(id=>!scenes.some(scene=>scene.id===id));
if(unknownScenes.length)throw Error(`unknown scene id(s) in only: ${unknownScenes.join(', ')}`);
const name=String(opt('name','Smoke v1'));
if(!name||/[\\/:*?"<>|]/.test(name))throw Error('Use a plain output name without path separators');
const dest=path.join(out,name+'.mp4'),audio=opt('audio');
if(audio&&!existsSync(path.resolve(audio)))throw Error('Audio file not found');
// Text motion is an explicit agent decision per scene. When a measured timeline exists,
// refuse to render until plan/text-direction.json is complete (no default style).
const beatsPath=path.join(root,'plan','beats.json');
if(existsSync(beatsPath)){
  const beats=JSON.parse(await readFile(beatsPath,'utf8'));
  const dirPath=path.join(root,'plan','text-direction.json');
  const direction=existsSync(dirPath)?JSON.parse(await readFile(dirPath,'utf8')):{};
  const copyPath=path.join(root,'plan','copy.json');
  const copy=existsSync(copyPath)?JSON.parse(await readFile(copyPath,'utf8')):null;
  const fontsPath=path.join(root,'assets','fonts','fonts.json');
  const fonts=existsSync(fontsPath)?(JSON.parse(await readFile(fontsPath,'utf8')).families||{}):null;
  const {errors}=validateTextDirection(direction,beats,copy,fonts);
  if(errors.length)throw Error('Text direction incomplete — the agent must choose styles per scene:\n'+errors.join('\n'));
}
const slideWallPath=path.join(root,'plan','slide-wall.json');
if(existsSync(slideWallPath)){
  const spec=JSON.parse(await readFile(slideWallPath,'utf8'));
  const errors=validateSlideWallSpec(spec,Number.isFinite(DURATION)?DURATION:null);
  if(errors.length)throw Error('Invalid plan/slide-wall.json:\n'+errors.join('\n'));
}
const oneTakePath=path.join(root,'plan','one-take.json');
if(existsSync(oneTakePath)){
  const spec=JSON.parse(await readFile(oneTakePath,'utf8'));
  const beats=existsSync(beatsPath)?JSON.parse(await readFile(beatsPath,'utf8')):{};
  if(!Number.isFinite(beats.duration)||beats.duration<=0){
    throw Error('Invalid plan/one-take.json: plan/beats.json must contain a finite positive duration');
  }
  if(Math.abs(DURATION-beats.duration)>1e-9){
    throw Error(`Invalid plan/one-take.json: data.js DURATION ${DURATION} must equal plan/beats.json duration ${beats.duration}`);
  }
  const errors=validateOneTakeSpec(spec,beats.duration);
  if(errors.length)throw Error('Invalid plan/one-take.json:\n'+errors.join('\n'));
}
// The reel is exactly as long as the VO (no target length): say it out loud when they disagree,
// because `-af apad` + a fixed frame count would silently cut a longer voice-over.
async function probeDuration(file){
  // a missing/broken ffprobe emits 'error' on the child process — handle it, never crash
  return new Promise((resolve)=>{
    let out='';
    const p=spawn(process.env.MEDO_FFPROBE||process.env.KHAAM_FFPROBE||'ffprobe',
      ['-v','error','-show_entries','format=duration','-of','json',path.resolve(file)]);
    p.stdout.on('data',c=>out+=c);
    p.on('error',()=>resolve(null));
    p.on('close',()=>{
      try{
        const d=Number(JSON.parse(out).format.duration);resolve(Number.isFinite(d)?d:null);
      }catch{resolve(null);}
    });
  });
}
if(audit&&existsSync(out))throw Error('Audit output exists; choose a fresh directory');
if(profile&&existsSync(path.join(out,'render-profile.json')))throw Error('Profile already exists; choose a fresh directory');
if(!audit&&!seq&&existsSync(dest))throw Error('Output exists; use a new version name');
await mkdir(out,{recursive:true});
if(seq&&(await readdir(out)).some(f=>/^\d{5}\.(jpg|png)$/.test(f)))throw Error('Frame output already exists; choose a fresh cache directory');
const setting=name=>process.env['MEDO_'+name]||process.env['KHAAM_'+name];
const configCandidates=process.env.MEDO_CONFIG
  ? [process.env.MEDO_CONFIG]
  : [path.join(root,'.video-motion','config.json'),process.env.KHAAM_CONFIG,path.join(root,'.khaam','config.json')].filter(Boolean);
const cfgPath=configCandidates.find(existsSync)||process.env.MEDO_CONFIG||path.join(root,'.video-motion','config.json');
let cfg={};
if(existsSync(cfgPath))cfg=JSON.parse(await readFile(cfgPath,'utf8'));
const configBase=path.dirname(path.dirname(path.resolve(cfgPath)));
// Config values may use ~ and $VAR / %VAR%, like the Python helpers (video_motion_paths.py).
const expand=v=>String(v).replace(/^~(?=$|[\\/])/,os.homedir()).replace(/\$\{?(\w+)\}?|%(\w+)%/g,(m,a,b)=>process.env[a||b]??m);
const configPath=v=>{v=expand(v);return path.isAbsolute(v)?v:path.resolve(configBase,v);};
const toolkit=setting('TOOLKIT')||cfg.toolkit_dir;
const req=createRequire(path.join(toolkit?configPath(toolkit):root,'package.json'));
// playwright-core works with the bundled Chromium (tools/chromium.mjs); fall back to playwright if only that is installed.
const {chromium}=(()=>{try{return req('playwright');}catch{return req('playwright-core');}})();
const ffmpeg=setting('FFMPEG')||(cfg.ffmpeg?(/[\\/~]/.test(cfg.ffmpeg)?configPath(cfg.ffmpeg):cfg.ffmpeg):'ffmpeg');
const browserPath=setting('CHROMIUM');
// Serve only render resources on loopback; never expose project .env/config or arbitrary files.
const mime={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.svg':'image/svg+xml','.woff2':'font/woff2','.woff':'font/woff','.ttf':'font/ttf','.otf':'font/otf','.wav':'audio/wav','.mp3':'audio/mpeg','.mp4':'video/mp4'};
const srcUrl='/'+path.relative(root,src).split(path.sep).join('/');
const assetsRoot=path.resolve(setting('ASSETS_DIR')||path.join(root,'assets'));
if(srcUrl.includes('..'))throw Error('Renderer must live inside the selected project');
const ALLOWED_PLANS=['/plan/text-direction.json','/plan/beats.json','/plan/stage.json','/plan/slide-wall.json','/plan/one-take.json','/plan/copy.json','/plan/word-timings.json'];
const server=http.createServer(async (request,response)=>{
  try{
    const u=decodeURIComponent(new URL(request.url,'http://localhost').pathname);
    if(u.split('/').some(s=>s.startsWith('.'))||(![srcUrl+'/', '/assets/','/node_modules/'].some(s=>u.startsWith(s))&&!ALLOWED_PLANS.includes(u)))throw Error('Forbidden');
    const asset=u.startsWith('/assets/');
    const base=asset?assetsRoot:root;
    const relative=asset?u.slice('/assets'.length):u;
    const f=path.resolve(base,'.'+relative);
    if(!f.startsWith(base+path.sep)||(await stat(f)).isDirectory())throw Error('Forbidden');
    response.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream'});response.end(await readFile(f));
  }catch{response.writeHead(404);response.end('Not found');}
});
let browser,encoder,page;let encodeResult;let completed=false;
try{
  await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
  browser=await chromium.launch({headless:true,...(browserPath?{executablePath:browserPath}:{})});
  page=await browser.newPage();const errors=[];
  if(audit)await page.route('**/*',route=>{
    const u=new URL(route.request().url());
    if(u.origin!==`http://127.0.0.1:${server.address().port}`){errors.push('Blocked external resource: '+u.origin);return route.abort();}
    return route.continue();
  });
  if(audit){
    page.on('requestfailed',r=>errors.push('Resource failed: '+r.url()));
    page.on('response',r=>{
      const reqPath=new URL(r.url()).pathname;
      const optionalPlan=ALLOWED_PLANS.includes(reqPath)&&!existsSync(path.join(root,reqPath.slice(1)));
      if(r.status()>=400&&!optionalPlan)errors.push(`Resource HTTP ${r.status()}: ${r.url()}`);
    });
  }
  page.on('pageerror',e=>errors.push(e.message));
  const initStarted=performance.now();
  await page.goto(`http://127.0.0.1:${server.address().port}${srcUrl}/index.html?scale=${scale}&motionMode=${motionMode}&rangeStart=${from}&rangeEnd=${from+count/fps}${audit?'&audit=1':''}${alpha?'&alpha=1':''}${only.length?'&only='+encodeURIComponent(only.join(',')):''}`);
  await page.waitForFunction(()=>window.__ready===true||window.__error,{},{timeout:30000});
  const initError=await page.evaluate(()=>window.__error||null);if(initError)throw Error(initError);
  const initMs=performance.now()-initStarted,profileTimes=[],captureTimes=[];let encoderFinalizeMs=null;
  if(!audit&&!seq){
    const args=['-hide_banner','-n','-f','image2pipe','-framerate',String(fps),'-i','pipe:0'];
    if(audio)args.push('-ss',String(from),'-t',String(to-from),'-i',path.resolve(audio));
    args.push('-map','0:v:0');if(audio)args.push('-map','1:a:0','-af','apad','-c:a','aac','-b:a','192k','-ar','48000');
    args.push('-c:v','libx264','-preset','medium','-crf',String(crf),'-pix_fmt','yuv420p','-frames:v',String(count),'-t',String(count/fps),'-movflags','+faststart',dest);
    encoder=spawn(ffmpeg,args,{stdio:['pipe','inherit','inherit']});
    encodeResult=new Promise((resolve,reject)=>{encoder.once('error',reject);encoder.once('close',code=>code===0?resolve():reject(Error('FFmpeg exited '+code)));});
    // Attach a handler immediately to avoid an unhandled rejection during frame capture.
    encodeResult.catch(()=>{});encoder.stdin.on('error',()=>{});
  }
  const auditFrames=[], fingerprints=[];let captured=0,screenshots=0;
  // Hash decoded RGBA, not PNG bytes or a resized/grayscale approximation.
  const fingerprint=()=>page.evaluate(async()=>{
    const c=document.getElementById('c'),data=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
    const bytes=new Uint8Array(await crypto.subtle.digest('SHA-256',data));
    return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
  });
  for(let i=0;i<count;i++){
    if(audit&&i%every!==0&&i!==count-1)continue;
    const frameStarted=profile?performance.now():0;
    await page.evaluate(t=>window.renderFrame(t),from+i/fps);
    if(profile)profileTimes.push(performance.now()-frameStarted);
    if(errors.length)throw Error(errors.join('\n'));
    if(audit){
      const boxes=await page.evaluate(()=>window.layoutSnapshot?.());
      const stageWin=await page.evaluate(()=>window.stageWindowSnapshot?.()??null);
      const issues=auditLayout(boxes,{checkPlatformUi:platformUi,stageWin});captured+=boxes.filter(b=>b.kind==='text').length;
      if(replay)fingerprints.push({index:i,hash:await fingerprint(),layout:JSON.stringify({boxes,stageWin})});
      if(issues.length){
        const image=screenshots<12?`frame-${i}.png`:null;
        auditFrames.push({frame:Math.round(from*fps)+i,time:from+i/fps,issues,boxes,stageWin,image});
        if(image){
          await page.evaluate(({boxes,ids})=>{
            const c=document.getElementById('c'),ctx=c.getContext('2d');ctx.save();
            ctx.setTransform(c.width/1080,0,0,c.height/1920,0,0);ctx.strokeStyle='#CB271B';ctx.lineWidth=4;
            for(const b of boxes)if(ids.includes(b.id))ctx.strokeRect(b.x,b.y,b.w,b.h);ctx.restore();
          },{boxes,ids:issues.flatMap(i=>i.ids)});
          await page.locator('canvas').screenshot({path:path.join(out,image)});screenshots++;
        }
      }
      continue;
    }
    const captureStarted=profile?performance.now():0;
    const data=await page.evaluate(type=>window.grab(type),jpg?'image/jpeg':'image/png');
    const bytes=Buffer.from(data.slice(data.indexOf(',')+1),'base64');
    if(seq)await writeFile(path.join(out,String(i).padStart(5,'0')+(alpha?'.png':'.jpg')),bytes);
    else if(!encoder.stdin.write(bytes))await Promise.race([once(encoder.stdin,'drain'),encodeResult.then(()=>{throw Error('Encoder ended early');})]);
    if(profile)captureTimes.push(performance.now()-captureStarted);
  }
  let replayFailures=0;
  if(replay){
    let replayScreenshots=0;
    for(const original of [...fingerprints].reverse()){
      const time=from+original.index/fps;
      await page.evaluate(t=>window.renderFrame(t),time);
      if(errors.length)throw Error(errors.join('\n'));
      const hash=await fingerprint(),boxes=await page.evaluate(()=>window.layoutSnapshot?.());
      const stageWin=await page.evaluate(()=>window.stageWindowSnapshot?.()??null);
      const issues=[];
      if(hash!==original.hash)issues.push({code:'R01',ids:['canvas'],message:'Pixels changed when re-seeking the same time',expected:original.hash,actual:hash});
      if(JSON.stringify({boxes,stageWin})!==original.layout)issues.push({code:'R02',ids:['layout'],message:'Layout capture changed when re-seeking the same time'});
      if(issues.length){
        replayFailures++;
        const image=replayScreenshots<6?`replay-frame-${original.index}.png`:null;
        auditFrames.push({frame:Math.round(from*fps)+original.index,time,issues,boxes,image});
        if(image){await page.locator('canvas').screenshot({path:path.join(out,image)});replayScreenshots++;}
      }
    }
  }
  if(audit){
    auditFrames.sort((a,b)=>a.frame-b.frame);
    const status=!captured?'incomplete':auditFrames.length?'fail':'pass';
    await writeFile(path.join(out,'report.json'),JSON.stringify({version:1,status,fps,from,to,every,scale,browser:browser.version(),
      sampling:every===1?'all frames':'sampled; brief collisions can be missed',capturedText:captured,
      replay:{status:!replay?'not-requested':replayFailures?'fail':fingerprints.length?'pass':'incomplete',
        checkedFrames:fingerprints.length,failedFrames:replayFailures,order:'reverse of inspected frames',hash:'SHA-256 of canvas-size RGBA'},
      limitations:'Conservative ink AABBs; no clipping/occlusion or readability inference. Offscreen canvas/raster text is not captured.',frames:auditFrames},null,2));
    if(status!=='pass')throw Error(`Layout audit ${status}; see ${path.join(out,'report.json')}`);
    console.log('Layout audit PASS');
  }
  if(encoder){const finishStarted=profile?performance.now():0;encoder.stdin.end();await encodeResult;if(profile)encoderFinalizeMs=performance.now()-finishStarted;}
  if(audio&&!seq&&!audit){
    const dur=await probeDuration(audio);
    if(dur!==null&&Math.abs(dur-to)>0.15)console.warn(
      `!! audio is ${dur.toFixed(2)}s but the render window ends at ${to.toFixed(2)}s — `
      +'the reel must be exactly the VO length (python3 tools/vo_length.py <vo>)');
  }
  if(profile){
    const summary=values=>{if(!values.length)return null;const sorted=[...values].sort((a,b)=>a-b),quantile=q=>sorted[Math.min(sorted.length-1,Math.ceil(q*sorted.length)-1)];return {mean:values.reduce((a,b)=>a+b,0)/values.length,p50:quantile(.5),p95:quantile(.95),max:sorted.at(-1)};};
    await writeFile(path.join(out,'render-profile.json'),JSON.stringify({version:2,frames:profileTimes.length,motionMode,initMs,frameEvaluateMs:summary(profileTimes),captureAndWriteMs:summary(captureTimes),encoderFinalizeMs,wallMs:performance.now()-invocationStarted,audit,scope:'Frame evaluation includes IPC; capture/write includes browser data URL, decode and disk or encoder backpressure; FFmpeg overlaps capture. Finalize measures remaining flush only. Replay/audit work included only in wall; not GPU instrumentation.'},null,2),{flag:'wx'});
  }
  if(!audit)console.log(`Rendered ${count} frames at ${fps} fps${alpha?' as a transparent PNG sequence':jpg?' as JPEG frames':audio?' with audio':' (silent; supply --audio for sound)'}`);
  completed=true;
}finally{
  let cleanupError;
  if(page&&!page.isClosed())try{await page.evaluate(()=>window.closeScenes?.());}catch(e){cleanupError=e;console.error('Scene resource cleanup failed:',e.message);}
  if(encoder&&encoder.exitCode===null)encoder.kill();
  if(browser)await browser.close();
  await new Promise(resolve=>server.close(resolve));
  if(cleanupError&&completed)throw cleanupError;
}
