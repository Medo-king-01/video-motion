// Synthetic fixture. Marker names are illustrative, not measured production VO.
import {compileSequence,staggerTime,arcAt,cycleValue,presenceAt} from './lib/motion-plan.js';
export const DIRECTION={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const clips=[{id:'path',track:'path',at:'word',duration:1.3,from:0,to:1,easing:'cubicInOut'}];
for(let i=0;i<3;i++)clips.push({id:`card-${i}`,track:`card-${i}`,at:staggerTime(i,3,{from:'center',each:.12,start:.2}),duration:.4,from:640,to:480,easing:'cubicOut'});
const plan=compileSequence({version:1,markers:{word:.2},clips});
export function frameAt(t){
  const values=plan.at(t);
  return {cards:[0,1,2].map(i=>({x:140+i*280,y:values[`card-${i}`],start:staggerTime(i,3,{from:'center',each:.12,start:.2})})),
    point:arcAt({x:180,y:1000},{x:900,y:1000},values.path,-180),
    scale:cycleValue(.8,1.2,t,{start:.2,duration:.6,repeat:1,type:'reverse',easing:'cubicInOut'}).value,
    presence:presenceAt(t,{start:0,enterEnd:.2,exitStart:1.6,end:1.8})};
}
