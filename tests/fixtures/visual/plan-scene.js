import {DIRECTION,frameAt} from '../plan-demo.js';
import {loadFont} from '../lib/arabic.js';
import {PALETTE as C} from '../lib/brand.js';
import {drawDirectedText} from '../lib/captions.js';
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);
  const state=frameAt(t);
  const text=(copy,id,x,y,size,start=0)=>drawDirectedText(ctx,copy,{direction:DIRECTION,scene:1,role:'label',elementId:id,
    time:t,start,end:1.8,x,y,size,maxWidth:900,color:C.ink,theme:'light',shadow:'transparent'});
  if(state.presence.active)text('حركة بتوقيت واضح','title',540,280,58);
  state.cards.forEach((card,i)=>{
    if(t<card.start)return;
    ctx.fillStyle=C.gray1;ctx.strokeStyle=C.ink;ctx.lineWidth=3;ctx.beginPath();ctx.roundRect(card.x,card.y,240,160,24);ctx.fill();ctx.stroke();
    text(`عنصر ${i+1}`,`card-${i}`,card.x+120,card.y+80,44,card.start);
  });
  ctx.strokeStyle=C.inkSoft;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(180,1000);ctx.quadraticCurveTo(540,640,900,1000);ctx.stroke();
  ctx.fillStyle=C.red;ctx.beginPath();ctx.arc(state.point.x,state.point.y,18*state.scale,0,Math.PI*2);ctx.fill();
  text('معاينة اختبارية','notice',540,1260,42);
}
