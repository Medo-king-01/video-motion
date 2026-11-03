import {DIRECTION,frameAt} from '../geometry-demo.js';
import {loadFont} from '../lib/arabic.js';
import {drawGeometry} from '../lib/geometry-canvas.js';
import {measureTextFit} from '../lib/text-measure.js';
import {drawDirectedText} from '../lib/captions.js';
import {PALETTE as C} from '../lib/brand.js';
let fit;
export async function init(){
  await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});
  const ctx=document.createElement('canvas').getContext('2d');
  let rejected=false;try{measureTextFit(ctx,'نص',{family:'Missing-Proof-Font',weight:800,minSize:32,maxSize:42,maxWidth:900,maxHeight:100});}catch{rejected=true;}
  if(!rejected)throw Error('missing font incorrectly accepted');
  fit=measureTextFit(ctx,'قياس على الخط الحقيقي',{family:'Cairo',weight:800,minSize:32,maxSize:42,step:2,maxWidth:900,maxHeight:100,padding:12});
  if(!fit.fits)throw Error('real font measurement did not fit');
}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);const state=frameAt(t);drawGeometry(ctx,state.bindings);
  const text=(copy,id,x,y,size)=>drawDirectedText(ctx,copy,{direction:DIRECTION,scene:1,role:'label',elementId:id,time:t,start:0,end:3,x,y,size,maxWidth:900,color:C.ink,theme:'light',shadow:'transparent'});
  text('عناصر بنفس الهوية','title',540,280,58);
  for(const card of state.cards)if(card.phase==='hold'&&card.opacity===1)text(`عنصر ${card.id.toUpperCase()}`,`card-${card.id}`,card.box.x+card.box.w/2,card.box.y+card.box.h/2,44);
  const x=(W-fit.w)/2,y=1210;
  drawGeometry(ctx,[{id:'measured',kind:'rect',fill:'gray1',stroke:'ink',props:{x,y,w:fit.w,h:fit.h,r:16,opacity:1,strokeWidth:3}}]);
  fit.lines.forEach((line,i)=>text(line.text,`fit-${i}`,x+line.x+line.w/2,y+line.y+line.h/2,fit.size));
}
