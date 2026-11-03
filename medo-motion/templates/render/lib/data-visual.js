// Canvas adapter; every visible label uses the existing explicit text-direction contract.
import { recipeAt } from './data-recipes.js';
import { drawDirectedText } from './captions.js';
import { PALETTE as C } from './brand.js';
export function drawDataRecipe(ctx,spec,time,{direction,scene,id='data',x=140,y=400,w=800,h=600}={}) {
  const state=recipeAt(spec,time);if(!state.active)return state;
  const label=(text,key,role,tx,ty,size=38)=>drawDirectedText(ctx,text,{direction,scene,role,elementId:`${id}.${key}`,time,
    start:spec.start,end:spec.end,x:tx,y:ty,size,maxWidth:w,color:C.ink,theme:'light',shadow:'transparent'});
  ctx.save();ctx.strokeStyle=C.inkSoft;ctx.lineWidth=3;
  if(state.kind!=='counter'){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x,y+h);ctx.lineTo(x+w,y+h);ctx.stroke();}
  label(state.unit,'unit','label',x+w/2,y-55);
  label(state.source,'source','label',x+w/2,y+h+70,28);
  if(state.visible){
    if(state.kind==='comparison'){
      const step=h/state.rows.length;
      state.rows.forEach((r,i)=>{
        ctx.fillStyle=C.red;ctx.fillRect(x,y+i*step+18,w*r.fraction,step*0.3);
        label(r.label,`${r.id}.label`,'label',x+w*0.28,y+(i+0.75)*step,32);
        label(r.display,`${r.id}.value`,'number',x+w*0.8,y+(i+0.75)*step,38);
      });
    }else if(state.kind==='counter'){
      label(state.rows[0].display,'value','number',x+w/2,y+h*0.45,110);
      label(state.rows[0].label,'label','label',x+w/2,y+h*0.75,42);
    }else{
      ctx.strokeStyle=C.red;ctx.lineWidth=6;ctx.beginPath();
      state.points.forEach((p,i)=>{const px=x+p.x*w,py=y+p.y*h;i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.stroke();
      const first=state.rows[0],last=state.rows.at(-1);
      label(first.label,'first','label',x+w*0.2,y+h+28,28);
      label(last.label,'last','label',x+w*0.8,y+h+28,28);
      if(state.progress===1)label(last.display,'value','number',x+w/2,y+55,50);
    }
  }
  ctx.restore();return state;
}
