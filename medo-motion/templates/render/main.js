import { captureLayout } from './lib/layout.js';
import {createResourceScope} from './lib/resource-scope.js';
import { W, H, scenes } from './data.js';
const params = new URLSearchParams(location.search);
const scale = Number(params.get('scale')) || 1;
const motionMode = params.get('motionMode') || 'normal';
if(!['normal','reduced'].includes(motionMode)) throw Error('invalid motion mode');
const hasRange=params.has('rangeStart')&&params.has('rangeEnd');
const rangeStart=hasRange?Number(params.get('rangeStart')):null,rangeEnd=hasRange?Number(params.get('rangeEnd')):null;
if(params.has('rangeStart')!==params.has('rangeEnd')||(hasRange&&(!Number.isFinite(rangeStart)||!Number.isFinite(rangeEnd)||rangeStart<0||rangeEnd<=rangeStart)))throw Error('invalid render range');
const active=scenes.map(s=>!hasRange||s.start<rangeEnd&&s.end>rangeStart);
const canvas = document.getElementById('c');
canvas.width = Math.max(2, 2 * Math.round(W * scale / 2));
canvas.height = Math.max(2, 2 * Math.round(H * scale / 2));
const auditing = new URLSearchParams(location.search).has('audit');
// Readback QA must not trigger a mid-run GPU→CPU raster-mode change.
const ctx = canvas.getContext('2d', auditing ? {willReadFrequently:true} : {});
const layout = auditing ? captureLayout(ctx) : null;
window.layoutSnapshot = () => layout ? layout.snapshot() : null;
const mods = await Promise.all(scenes.map(s => import(`./scenes/${s.id}.js`)));
const scopes=mods.map(()=>createResourceScope());
window.closeScenes=async()=>{
  const errors=[];
  for(const scope of [...scopes].reverse())try{await scope.close();}catch(e){errors.push(e);}
  if(errors.length)throw new AggregateError(errors,'scene resource cleanup failed');
};
try{
  if(motionMode==='reduced'&&mods.some((m,i)=>active[i]&&m.supportsReducedMotion!==true))throw Error('Reduced motion requires every active K scene to explicitly declare supportsReducedMotion');
  const initialized=await Promise.allSettled(mods.map((m,i)=>Promise.resolve().then(()=>motionMode==='normal'||active[i]?m.init?.({W,H,scale,motionMode,resources:scopes[i]}):undefined)));
  const failures=initialized.filter(r=>r.status==='rejected').map(r=>r.reason);
  if(failures.length)throw new AggregateError(failures,'scene initialization failed');
  await document.fonts.ready;
}catch(error){
  try{await window.closeScenes();}catch(cleanup){console.error('scene cleanup failed',cleanup);}
  window.__error=String(error?.message||error);
}

// The agent-authored text direction (optional for the bare template examples;
// required by the render gate once a measured timeline exists).
let direction = null;
try {
  const r = await fetch('/plan/text-direction.json');
  if (r.ok) direction = await r.json();
} catch { /* template examples without a project plan */ }
window.renderFrame = async t => {
  if(motionMode==='reduced'&&hasRange&&(t<rangeStart||t>=rangeEnd))throw Error('frame outside reduced-motion render range');
  layout?.begin();
  ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#000';ctx.fillRect(0,0,canvas.width,canvas.height);
  for (let i=0;i<scenes.length;i++) {
    const s=scenes[i];if(t<s.start || t>=s.end)continue;
    ctx.save();try{ctx.setTransform(canvas.width/W,0,0,canvas.height/H,0,0);
      await mods[i].draw(ctx,t-s.start,{W,H,scale,dur:s.end-s.start,t,scene:s,direction,motionMode,resources:scopes[i]});
    }finally{ctx.restore();}
  }
};
window.grab=(type,quality=.95)=>canvas.toDataURL(type,quality);
if(!window.__error)window.__ready=true;
