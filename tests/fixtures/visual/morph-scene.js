import {DIRECTION,frameAt} from '../morph-demo.js';
import {loadFont} from '../lib/arabic.js';
import {drawSvgArt} from '../lib/svg-canvas.js';
import {drawDirectedText} from '../lib/captions.js';
import {PALETTE as C} from '../lib/brand.js';
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);
  const {art,values}=frameAt(t);drawSvgArt(ctx,art,{x:190,y:550,width:700,height:700});
  ctx.fillStyle=C.ink;ctx.fillRect(340,1370,400,8);ctx.fillStyle=C.red;ctx.fillRect(340,1370,400*values['group/accent'],8);
  drawDirectedText(ctx,'تحول يحافظ على الفتحة',{direction:DIRECTION,scene:1,role:'label',elementId:'title',time:t,start:0,end:2.4,x:540,y:280,size:58,color:C.ink,theme:'light',shadow:'transparent'});
}
