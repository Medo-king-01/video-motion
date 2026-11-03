import {PLAN} from '../svg-proof.js';
import {drawSvgArt} from '../lib/svg-canvas.js';
import {drawDirectedText} from '../lib/captions.js';
import {loadFont} from '../lib/arabic.js';
import {PALETTE as C} from '../lib/brand.js';
import {compileMotionPolicy} from '../lib/render-policy.js';
const direction={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const reduced=compileMotionPolicy({version:1,reduced:true,decorative:[{track:'stroke',value:1}]});
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);
  const progress=reduced.at({stroke:Math.min(1,t/1.5)}).stroke;
  const p=Math.min(1,t/1.5),start=Math.max(0,p-.5);
  drawSvgArt(ctx,PLAN,{x:80,y:650,width:430,height:430,progress:p,strokeStart:start,strokeWindows:{'svg-0':[{start,end:p},{start:0,end:p/2}]}});
  drawSvgArt(ctx,PLAN,{x:570,y:650,width:430,height:430,progress});
  drawDirectedText(ctx,'رسم ثابت ومسارات آمنة',{direction,scene:1,role:'label',elementId:'title',time:t,start:0,end:2,x:540,y:300,size:56,color:C.ink,theme:'light',shadow:'transparent'});
}
