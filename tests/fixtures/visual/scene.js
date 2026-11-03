// Synthetic verification fixture, not a claimed VO-derived reel or product benchmark.
import {loadFont} from './lib/arabic.js';
import {PALETTE as C} from './lib/brand.js';
import {drawDataRecipe} from './lib/data-visual.js';
import {protectBox} from './lib/layout.js';
const direction={scenes:[{scene:1,textStyles:{label:'softfade',number:'softfade'},
  fontStyles:{label:{family:'Cairo',weight:800},number:{family:'Cairo',weight:800}}}]};
export async function init(){await loadFont('Cairo','/assets/fonts/Cairo/Cairo_800ExtraBold.ttf',{weight:'800'});}
export function draw(ctx,t,{scene,W,H}){
  ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);
  const kind=scene.id;
  const rows=kind==='comparison'?[{id:'a',label:'الخيار الأول',value:16},{id:'b',label:'الخيار التاني',value:32}]
    :kind==='timeline'?[{id:'a',label:'البداية',value:10,at:0},{id:'b',label:'المنتصف',value:20,at:1},{id:'c',label:'النهاية',value:32,at:2}]
    :[{id:'a',label:'سعة الذاكرة',value:32}];
  const spec={start:0,end:2,anchor:{text:'اتنين وتلاتين',start:.3,end:.8},
    data:{version:1,kind:kind==='bad'?'counter':kind,source:'بيانات توضيحية — مش اختبار منتج',unit:'جيجابايت',locale:'ar-EG',decimals:0,rows}};
  drawDataRecipe(ctx,spec,t,{direction,scene:1,x:140,y:450,w:800,h:500});
  if(kind==='bad'){
    protectBox(ctx,'face',{x:400,y:380,w:280,h:160});
    ctx.font='800 60px Cairo';ctx.fillStyle=C.ink;ctx.fillText('خارج الحدود',5,100);
    ctx.fillText('نص أول',250,1200);ctx.fillText('نص تاني',250,1200);
  }
}
