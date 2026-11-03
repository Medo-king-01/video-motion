import {SPEC,DIRECTION} from '../shared-demo.js';
import {loadFont} from '../lib/arabic.js';
import {PALETTE as C} from '../lib/brand.js';
import {drawSharedPanel} from '../lib/shared-panel.js';
import {drawDirectedText} from '../lib/captions.js';
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);
  const text=(ctx,copy,key,role,x,y,size,start=0,maxWidth=880)=>drawDirectedText(ctx,copy,{
    direction:DIRECTION,scene:1,role,elementId:`detail.${key}`,time:t,start,end:SPEC.end,
    x,y,size,maxWidth,color:C.ink,theme:'light',shadow:'transparent'});
  drawSharedPanel(ctx,SPEC,t,{
    drawLabel:(ctx,{box})=>text(ctx,'تفاصيل','title','label',box.x+box.w/2,box.y+55,48,0,box.w-40),
    drawContent:(ctx,{box})=>{
      ctx.strokeStyle=C.inkSoft;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(box.x+40,box.y+115);ctx.lineTo(box.x+box.w-40,box.y+115);ctx.stroke();
      text(ctx,'مساحة للشرح','body','body',box.x+box.w/2,box.y+320,72,SPEC.contentAt);
    },
  });
  text(ctx,'مثال توضيحي','notice','label',540,1260,42);
}
