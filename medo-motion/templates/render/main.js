import { W, H, scenes } from './data.js';
const scale = Number(new URLSearchParams(location.search).get('scale')) || 1;
const canvas = document.getElementById('c');
canvas.width = Math.max(2, 2 * Math.round(W * scale / 2));
canvas.height = Math.max(2, 2 * Math.round(H * scale / 2));
const ctx = canvas.getContext('2d');
const mods = await Promise.all(scenes.map(s => import(`./scenes/${s.id}.js`)));
await Promise.all(mods.map(m => m.init?.({ W, H, scale })));
await document.fonts.ready;
// The agent-authored text direction (optional for the bare template examples;
// required by the render gate once a measured timeline exists).
let direction = null;
try {
  const r = await fetch('/plan/text-direction.json');
  if (r.ok) direction = await r.json();
} catch { /* template examples without a project plan */ }
window.renderFrame = async t => {
  ctx.setTransform(1,0,0,1,0,0);ctx.fillStyle='#000';ctx.fillRect(0,0,canvas.width,canvas.height);
  for (let i=0;i<scenes.length;i++) {
    const s=scenes[i];if(t<s.start || t>=s.end)continue;
    ctx.save();ctx.setTransform(canvas.width/W,0,0,canvas.height/H,0,0);
    await mods[i].draw(ctx,t-s.start,{W,H,scale,dur:s.end-s.start,t,scene:s,direction});ctx.restore();
  }
};
window.grab=(type,quality=.95)=>canvas.toDataURL(type,quality);
window.__ready=true;
