// Synthetic render proof. All event times are illustrative, never presented as measured VO.
import {compileLayout,stackLayout,reorderLayout,compileMorph,compileBindings} from './lib/motion-geometry.js';
import {compileSequence} from './lib/motion-plan.js';
export const DIRECTION={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const ids=['a','b','c','d'],items=ids.map(id=>({id,w:240,h:140,r:24}));
const layout={version:1,initial:stackLayout(items.slice(0,3),{x:140,y:430,axis:'x',gap:40}),events:[
  {at:.2,duration:.6,items:reorderLayout(items.slice(0,3),['c','a','b'],{x:140,y:430,axis:'x',gap:40})},
  {at:1.2,duration:.5,mode:'wait',items:reorderLayout(items.map(i=>({...i,h:100})).filter(i=>i.id!=='b'),['a','d','c'],{x:140,y:400,axis:'y',gap:18})}]};
const motion={version:1,clips:[{id:'morph',track:'morph',at:.2,duration:2.4,from:0,to:1,easing:'cubicInOut'},
  {id:'stroke',track:'stroke',at:.2,duration:2.4,from:0,to:1}]};
const morph={from:Array.from({length:8},(_,i)=>({x:800+80*Math.cos(i*Math.PI/4),y:1020+80*Math.sin(i*Math.PI/4)})),
  to:[{x:710,y:940},{x:890,y:940},{x:890,y:1100},{x:710,y:1100}],count:64};
const bindings={version:1,bindings:[...ids.map((id,i)=>({id,kind:'rect',fill:['gray1','gray2','gray3','gray1'][i],constants:{strokeWidth:3},
  tracks:Object.fromEntries(['x','y','w','h','r','opacity'].map(k=>[k,`${id}.${k}`]))})),
  {id:'morph-shape',kind:'path',fill:'gray1',constants:{closed:true,strokeWidth:4},tracks:{points:'shape'}},
  {id:'stroke-line',kind:'path',stroke:'red',constants:{points:[{x:140,y:1040},{x:300,y:930},{x:460,y:1040},{x:620,y:950}],strokeWidth:8},tracks:{end:'stroke'}}]};
export const PROOF_SPEC={layout,motion,morph,bindings,direction:DIRECTION};
const group=compileLayout(layout),sequence=compileSequence(motion),shape=compileMorph(morph),paint=compileBindings(bindings);
export function frameAt(t){
  const cards=group.at(t),values={...sequence.at(t)};values.shape=shape.at(values.morph);
  ids.forEach(id=>['x','y','w','h','r','opacity'].forEach(k=>{values[`${id}.${k}`]=k==='w'||k==='h'?100:0;}));
  cards.forEach(card=>Object.entries({...card.box,opacity:card.opacity}).forEach(([k,v])=>{values[`${card.id}.${k}`]=v;}));
  return {cards,bindings:paint.at(values).filter(item=>item.props.opacity>0)};
}
