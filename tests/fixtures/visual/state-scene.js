import {DIRECTION,frameAt} from '../state-demo.js';
import {loadFont} from '../lib/arabic.js';
import {PALETTE as C} from '../lib/brand.js';
import {drawDirectedText} from '../lib/captions.js';
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);const state=frameAt(t);
  const text=(copy,id,x,y,size)=>drawDirectedText(ctx,copy,{direction:DIRECTION,scene:1,role:'label',elementId:id,
    time:t,start:0,end:2.4,x,y,size,maxWidth:900,color:C.ink,theme:'light',shadow:'transparent'});
  text('فيزياء وحالات ثابتة','title',540,280,58);
  ctx.strokeStyle=C.red;ctx.fillStyle=C.gray1;ctx.lineWidth=3;ctx.beginPath();ctx.roundRect(state.spring.value-100,450,200,120,24);ctx.fill();ctx.stroke();
  text('نابض','spring',state.spring.value,510,44);
  state.cards.forEach((card,i)=>{ctx.fillStyle=C.gray1;ctx.strokeStyle=C.ink;ctx.beginPath();ctx.roundRect(card.x,card.y,240,140,24);ctx.fill();ctx.stroke();text(`حالة ${i+1}`,`card-${i}`,card.x+120,card.y+70,44);});
  [['inertia','قصور',1000],['retarget','هدف جديد',1130],['follow','تتبّع',1260]].forEach(([id,label,y])=>{
    ctx.strokeStyle=C.inkSoft;ctx.beginPath();ctx.moveTo(140,y);ctx.lineTo(940,y);ctx.stroke();
    ctx.fillStyle=C.red;ctx.beginPath();ctx.arc(state[id].value,y,state.radius,0,Math.PI*2);ctx.fill();text(label,id,540,y+58,42);
  });
}
