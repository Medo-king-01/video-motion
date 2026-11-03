// Original offline state/physics adapters. No browser clock, live subscription or runtime dependency.
import {mixValue,compileSequence} from './motion-plan.js';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const clone=x=>JSON.parse(JSON.stringify(x));
const option=(o,k,d)=>o[k]===undefined?d:o[k];
const number=(x,name)=>{if(!finite(x))throw Error(`${name} must be finite`);return x;};
const positive=(x,name)=>{number(x,name);if(x<=0)throw Error(`${name} must be positive`);return x;};
const state=(value,velocity)=>({value:number(value,'value'),velocity:number(velocity,'velocity')});
function physics(options={}){
  if(!object(options))throw Error('physics must be an object');
  const {stiffness=100,damping=18,mass=1}=options;
  positive(stiffness,'stiffness');positive(mass,'mass');number(damping,'damping');
  const w=Math.sqrt(stiffness/mass),z=(damping/mass)/(2*w);
  if(damping<0||!finite(w)||!finite(z)||w<1e-6||w>1e6||z>1e4)throw Error('unsupported spring conditioning');
  return {stiffness,damping,mass,w,z};
}
/** Closed-form scalar damped oscillator; velocity is units/second, not units/frame. */
export function springState(from,to,elapsed,options={}){
  [from,to,elapsed].forEach(v=>number(v,'spring input'));
  const {w,z}=physics(options),v=number(option(options,'velocity',0),'velocity');
  if(elapsed<0)return state(from,0);
  if(elapsed===0)return state(from,v);
  number(w*elapsed,'spring phase');
  const a=number(from-to,'displacement'),t=elapsed;let x,velocity;
  if(z<1-1e-7){
    const d=w*Math.sqrt(1-z*z),b=(v+z*w*a)/d,e=Math.exp(-z*w*t),c=Math.cos(d*t),s=Math.sin(d*t);
    x=e*(a*c+b*s);velocity=e*((-z*w*a+b*d)*c+(-z*w*b-a*d)*s);
  }else if(z>1+1e-7){
    const q=z+Math.sqrt(z*z-1),r1=-w/q,r2=-w*q,c=(v-r2*a)/(r1-r2),d=a-c;
    x=c*Math.exp(r1*t)+d*Math.exp(r2*t);velocity=r1*c*Math.exp(r1*t)+r2*d*Math.exp(r2*t);
  }else{
    const b=v+w*a,e=Math.exp(-w*t);x=(a+b*t)*e;velocity=(b-w*(a+b*t))*e;
  }
  return state(to+x,velocity);
}
/** Duration fit plus C1 terminal correction: intentional finite landing, not an exact free oscillator. */
export function durationSpring(from,to,elapsed,{duration,bounce=.2,velocity=0}={}){
  positive(duration,'duration');number(bounce,'bounce');
  if(bounce<0||bounce>.8)throw Error('bounce must be between 0 and .8');
  const z=1-bounce,w=8/(z*duration),options={stiffness:w*w,damping:2*z*w,velocity};
  number(elapsed,'time');springState(from,to,0,options);const last=springState(from,to,duration,options);
  if(elapsed<0)return state(from,0);
  if(elapsed>=duration)return state(to,0);
  const current=springState(from,to,elapsed,options),p=elapsed/duration,h=3*p*p-2*p*p*p,g=p*p*p-p*p;
  return state(current.value-(last.value-to)*h-last.velocity*duration*g,
    current.velocity-(last.value-to)*(6*p-6*p*p)/duration-last.velocity*(3*p*p-2*p));
}
/** Decay then finite snap/landing. Bounds are hard clamps, not an unreported bounce simulation. */
export function compileInertia(spec){
  if(!object(spec))throw Error('inertia requires an object');
  const {from,velocity,timeConstant=.35,decayDuration=.6,settleDuration=.3,min=null,max=null,snap=null}=spec;
  number(from,'from');number(velocity,'velocity');positive(timeConstant,'timeConstant');positive(decayDuration,'decayDuration');positive(settleDuration,'settleDuration');
  if(min!==null)number(min,'min');if(max!==null)number(max,'max');
  if((min!==null&&from<min)||(max!==null&&from>max)||(min!==null&&max!==null&&min>=max))throw Error('invalid inertia bounds/initial value');
  const bound=s=>{if(min!==null&&(s.value<min||(s.value===min&&s.velocity<0)))return state(min,0);if(max!==null&&(s.value>max||(s.value===max&&s.velocity>0)))return state(max,0);return s;};
  const project=number(from+velocity*timeConstant,'projected target');
  let target=bound(state(project,0)).value;
  if(snap!==null){
    if(!Array.isArray(snap)||!snap.length||snap.some(x=>!finite(x)||(min!==null&&x<min)||(max!==null&&x>max)))throw Error('snap points must be finite and within bounds');
    target=[...snap].sort((a,b)=>Math.abs(a-target)-Math.abs(b-target)||a-b)[0];
  }
  const decay=t=>bound(state(from+velocity*timeConstant*(-Math.expm1(-t/timeConstant)),velocity*Math.exp(-t/timeConstant)));
  const landing=decay(decayDuration),duration=number(decayDuration+settleDuration,'duration');
  // Preflight conditioning, even if only the final frame is requested later.
  durationSpring(landing.value,target,0,{duration:settleDuration,bounce:0,velocity:landing.velocity});
  return {duration,target,at(t){
    number(t,'time');
    const s=t>=duration?state(target,0):t<0?state(from,0):t<decayDuration?decay(t):bound(durationSpring(landing.value,target,t-decayDuration,{duration:settleDuration,bounce:0,velocity:landing.velocity}));
    return {...s,target,done:t>=duration};
  }};
}
/** Compile all retarget states in authored event order; arbitrary seeks never mutate them. */
export function compileRetarget(spec){
  if(!object(spec)||spec.version!==1||!Array.isArray(spec.events))throw Error('retarget requires version=1/events');
  const initial=number(spec.initial,'initial'),velocity=number(option(spec,'velocity',0),'velocity'),params=physics(option(spec,'physics',{}));
  let segments=[{at:0,from:initial,target:initial,velocity}],previous=-1;
  for(const event of spec.events){
    if(!object(event)||!finite(event.at)||event.at<0||event.at<=previous)throw Error('events must have strictly increasing nonnegative times');
    const target=number(event.target,'target'),last=segments.at(-1),s=springState(last.from,last.target,event.at-last.at,{...params,velocity:last.velocity});
    segments.push({at:event.at,from:s.value,target,velocity:s.velocity});previous=event.at;
  }
  // No reference to mutable user input survives compilation.
  segments=segments.map(s=>Object.freeze(s));
  return {at(t){
    number(t,'time');if(t<0)return {...state(initial,0),target:initial};
    let segment=segments[0];for(const s of segments){if(s.at>t)break;segment=s;}
    return {...springState(segment.from,segment.target,t-segment.at,{...params,velocity:segment.velocity}),target:segment.target};
  }};
}
/** A delayed follower of a piecewise-constant authored target, not a live pointer follower. */
export function compileFollow(spec){
  if(!object(spec)||!Array.isArray(spec.events))throw Error('follow requires an event log');
  const lag=number(option(spec,'lag',0),'lag');if(lag<0)throw Error('lag must be nonnegative');
  return compileRetarget({...spec,events:spec.events.map(e=>{if(!object(e)||!finite(e.at)||e.at<0)throw Error('invalid target event');return {...e,at:number(e.at+lag,'delayed time')};})});
}
/** Propagated variant labels with explicit parent/child ordering and global event barriers. */
export function compileVariants(spec){
  if(!object(spec)||spec.version!==1||!object(spec.root)||!Array.isArray(spec.events))throw Error('variants require version=1/root/events');
  const nodes=[],ids=new Set(),initial=Object.create(null),last=Object.create(null),clips=[];
  function visit(node,inherited,depth){
    if(depth>32||nodes.length>=256||!object(node)||typeof node.id!=='string'||!node.id.trim()||ids.has(node.id))throw Error('invalid/duplicate variant node');
    ids.add(node.id);nodes.push(node);
    const label=option(node,'initial',inherited);
    if(typeof label!=='string'||!object(node.variants)||!object(node.variants[label]))throw Error('node requires an initial variant');
    const base=node.variants[label];mixValue(base,base,0);
    for(const value of Object.values(node.variants)){if(!object(value))throw Error('variant state must be an object');mixValue(base,value,.5);}
    initial[node.id]=clone(base);last[node.id]=clone(base);
    if(node.children!==undefined&&!Array.isArray(node.children))throw Error('children must be an array');
    for(const child of node.children??[])visit(child,label,depth+1);
  }
  const root=clone(spec.root);visit(root,undefined,0);let end=0;
  for(const [index,event] of spec.events.entries()){
    if(!object(event)||!finite(event.at)||event.at<end-1e-12||typeof event.label!=='string')throw Error('variant events must follow the previous transition');
    positive(event.duration,'duration');const stagger=number(option(event,'stagger',0),'stagger'),order=option(event,'order','together');
    if(stagger<0||!['together','beforeChildren','afterChildren'].includes(order))throw Error('invalid variant orchestration');
    function schedule(node,start){
      const children=node.children??[];let own=start,finish=start+event.duration;
      const childStart=order==='beforeChildren'?finish:start;
      children.forEach((child,i)=>{finish=Math.max(finish,schedule(child,childStart+i*stagger));});
      if(order==='afterChildren'&&children.length){own=finish;finish=own+event.duration;}
      const to=node.variants[event.label];if(!object(to))throw Error(`missing variant ${event.label} on ${node.id}`);
      clips.push({id:`${index}:${node.id}`,track:node.id,at:own,duration:event.duration,from:last[node.id],to,easing:event.easing??'linear'});
      last[node.id]=to;return number(finish,'variant end');
    }
    end=schedule(root,Math.max(event.at,end));
  }
  const sequence=clips.length?compileSequence({version:1,clips}):null;
  return {duration:end,at(t){number(t,'time');return sequence?sequence.at(t):clone(initial);}};
}
/** JSON-only derived-value graph. No eval, callbacks or subscriptions. */
export function compileValues(spec){
  if(!object(spec)||spec.version!==1||!Array.isArray(spec.nodes)||spec.nodes.length>128)throw Error('values require version=1/nodes (max 128)');
  const constants=clone(option(spec,'constants',{}));if(!object(constants))throw Error('constants must be an object');
  for(const v of Object.values(constants))mixValue(v,v,0);
  const sequence=spec.sequence?compileSequence(spec.sequence):null,sources=new Set(Object.keys(constants));
  for(const k of Object.keys(sequence?.at(0)??{})){if(sources.has(k))throw Error('duplicate source');sources.add(k);}
  const nodes=new Map(),dependencies=new Map();
  for(const raw of spec.nodes){
    const n=clone(raw);if(!object(n)||typeof n.id!=='string'||!n.id.trim()||sources.has(n.id)||nodes.has(n.id))throw Error('invalid/duplicate value id');
    let refs;
    if(['map','mix','velocity'].includes(n.op)){
      refs=[n.input];
      if(n.op==='map'){
        if(!Array.isArray(n.range)||n.range.length!==2||!n.range.every(finite)||n.range[0]===n.range[1]||!Array.isArray(n.output)||n.output.length!==2||(n.clamp!==undefined&&typeof n.clamp!=='boolean'))throw Error('invalid map');
        number(n.range[1]-n.range[0],'map range span');mixValue(...n.output,.5);
      }
      if(n.op==='mix')mixValue(n.from,n.to,.5);
      if(n.op==='velocity'){positive(option(n,'step',1/600),'step');if((option(n,'step',1/600))>1)throw Error('velocity step must be <=1 second');}
    }else if(['add','multiply'].includes(n.op)){
      if(!Array.isArray(n.inputs)||!n.inputs.length)throw Error('arithmetic needs inputs');refs=n.inputs;
    }else if(n.op==='template'){
      if(!Number.isInteger(option(n,'digits',3))||(option(n,'digits',3))<0||(option(n,'digits',3))>6)throw Error('template digits must be 0..6');
      if(!Array.isArray(n.parts)||!n.parts.every(p=>typeof p==='string'||(object(p)&&typeof p.input==='string')))throw Error('invalid template');
      refs=n.parts.filter(object).map(p=>p.input);
    }else throw Error('unknown value operation');
    if(!refs.every(r=>typeof r==='string'))throw Error('references must be strings');nodes.set(n.id,n);dependencies.set(n.id,refs);
  }
  const visiting=new Set(),done=new Map();
  function check(id){
    if(sources.has(id))return false;
    if(!nodes.has(id)||visiting.has(id))throw Error('missing reference or cyclic value graph');
    if(done.has(id))return done.get(id);
    visiting.add(id);const upstream=dependencies.get(id).map(check).some(Boolean),own=nodes.get(id).op==='velocity';
    if(own&&upstream)throw Error('nested velocity derivatives are unsupported');
    visiting.delete(id);done.set(id,own||upstream);return own||upstream;
  }
  for(const id of nodes.keys())check(id);
  function at(t){
    number(t,'time');const memo=new Map(),samples=new Map();
    function value(id,time){
      const key=JSON.stringify([id,time]);if(memo.has(key))return memo.get(key);
      if(!samples.has(time))samples.set(time,{...constants,...sequence?.at(time)});
      if(sources.has(id))return samples.get(time)[id];
      const n=nodes.get(id),read=ref=>value(ref,time);let out;
      if(n.op==='velocity'){const h=option(n,'step',1/600);out=(number(value(n.input,time+h),'velocity input')-number(value(n.input,time-h),'velocity input'))/(2*h);}
      if(n.op==='map'){let p=(number(read(n.input),'map input')-n.range[0])/(n.range[1]-n.range[0]);if(n.clamp!==false)p=Math.max(0,Math.min(1,p));out=mixValue(...n.output,p);}
      if(n.op==='mix')out=mixValue(n.from,n.to,number(read(n.input),'mix input'));
      if(n.op==='add')out=n.inputs.reduce((s,r)=>s+number(read(r),'add input'),0);
      if(n.op==='multiply')out=n.inputs.reduce((s,r)=>s*number(read(r),'multiply input'),1);
      if(n.op==='template')out=n.parts.map(p=>{if(typeof p==='string')return p;const v=read(p.input);if(typeof v!=='string'&&!finite(v))throw Error('template reference must be scalar');if(typeof v==='string')return v;if(Math.abs(v)>=1e21)throw Error('template number too large');return String(Number(v.toFixed(option(n,'digits',3))));}).join('');
      if(typeof out==='number')number(out,'derived value');memo.set(key,out);return out;
    }
    return clone(Object.fromEntries([...sources,...nodes.keys()].map(id=>[id,value(id,t)])));
  }
  at(0);return {at};
}
