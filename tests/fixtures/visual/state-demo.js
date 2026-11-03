// Synthetic offline verification. No measured production VO, pointer events or real factual claims.
import {durationSpring,compileInertia,compileRetarget,compileFollow,compileVariants,compileValues} from './lib/motion-state.js';
export const DIRECTION={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const eventLog={version:1,initial:180,physics:{stiffness:170,damping:18},events:[{at:.1,target:820},{at:.65,target:340},{at:1.3,target:760}]};
const retarget=compileRetarget(eventLog),follow=compileFollow({...eventLog,lag:.14});
const inertia=compileInertia({from:180,velocity:1700,timeConstant:.28,decayDuration:.75,settleDuration:.35,min:140,max:940,snap:[260,540,820]});
const variants=compileVariants({version:1,root:{id:'panel',initial:'off',variants:{off:{y:20},on:{y:0}},children:[0,1,2].map(i=>({id:`card${i}`,variants:{off:{y:800},on:{y:640}}}))},
  events:[{at:.1,label:'on',duration:.25,stagger:.1,order:'beforeChildren',easing:'cubicOut'},
    {at:1.7,label:'off',duration:.2,stagger:.08,order:'afterChildren',easing:'cubicInOut'}]});
const graph=compileValues({version:1,sequence:{version:1,clips:[{id:'p',track:'p',at:.1,duration:1.8,from:0,to:1}]},nodes:[
  {id:'radius',op:'map',input:'p',range:[0,1],output:[14,26]},
  {id:'speed',op:'velocity',input:'p'}]});
export function frameAt(t){
  const states=variants.at(t),derived=graph.at(t);
  return {spring:durationSpring(240,820,t-.1,{duration:.7,bounce:.35}),inertia:inertia.at(t-.1),retarget:retarget.at(t),follow:follow.at(t),
    cards:[0,1,2].map(i=>({x:140+i*280,y:states[`card${i}`].y+states.panel.y})),radius:derived.radius};
}
