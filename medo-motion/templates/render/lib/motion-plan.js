// Original offline motion planning. Seconds, explicit inputs, no wall clock or subscriptions.
import {ease, clamp} from './motion.js';
const finite=n=>typeof n==='number'&&Number.isFinite(n);
const plain=o=>o!==null&&typeof o==='object'&&!Array.isArray(o)&&Object.getPrototypeOf(o)===Object.prototype;
function requireNumber(n,name){if(!finite(n))throw Error(`${name} must be finite`);}
function curve(name,p){const v=ease(name,p);requireNumber(v,'eased progress');return v;}

/** Matching numeric structures or same-unit px/%/deg strings; never interpolate brand colors. */
export function mixValue(a,b,p){
  requireNumber(p,'progress');
  if(finite(a)&&finite(b)){const v=(1-p)*a+p*b;requireNumber(v,'mixed value');return v;}
  if(Array.isArray(a)&&Array.isArray(b)&&a.length===b.length)return a.map((v,i)=>mixValue(v,b[i],p));
  if(plain(a)&&plain(b)){
    const keys=Object.keys(a).sort(),other=Object.keys(b).sort();
    if(JSON.stringify(keys)!==JSON.stringify(other))throw Error('object keys must match');
    return Object.fromEntries(keys.map(k=>[k,mixValue(a[k],b[k],p)]));
  }
  if(typeof a==='string'&&typeof b==='string'){
    const re=/^([+-]?(?:\d+\.?\d*|\.\d+))(px|%|deg)$/;
    const x=re.exec(a),y=re.exec(b);
    if(x&&y&&x[2]===y[2])return `${mixValue(Number(x[1]),Number(y[1]),p)}${x[2]}`;
    if(a===b)return a;
  }
  throw Error('values must have matching numeric structure/units; colors and unlike strings are not mixed');
}

/** Delay from a spatial origin, not per-frame mutable animation state. */
export function staggerTime(index,count,{each=.06,from='first',start=0,easing='linear'}={}){
  if(!Number.isInteger(count)||count<1||count>10000||!Number.isInteger(index)||index<0||index>=count)throw Error('invalid stagger index/count');
  if(!finite(each)||each<0||!finite(start)||start<0)throw Error('invalid stagger timing');
  let distance,max;
  if(from==='edges'){distance=Math.min(index,count-1-index);max=Math.floor((count-1)/2);}
  else{
    const origin=from==='first'?0:from==='last'?count-1:from==='center'?(count-1)/2:from;
    if(!finite(origin)||origin<0||origin>count-1)throw Error('invalid stagger origin');
    const nearest=Math.abs(Math.round(origin)-origin);
    distance=Math.abs(index-origin)-nearest;max=Math.max(origin,count-1-origin)-nearest;
  }
  return start+each*max*clamp(curve(easing,max?distance/max:0));
}

/** Finite decorative cycles only. Reverse rewinds the curve; mirror swaps its ends. */
export function cycleValue(a,b,time,{start,duration,repeat=0,repeatDelay=0,type='loop',easing='linear'}){
  for(const [k,v] of Object.entries({time,start,duration,repeatDelay}))requireNumber(v,k);
  if(start<0||duration<=0||repeatDelay<0||!Number.isInteger(repeat)||repeat<0||repeat>10000||!['loop','reverse','mirror'].includes(type))throw Error('invalid finite cycle');
  const total=duration*(repeat+1)+repeatDelay*repeat;
  requireNumber(total,'cycle duration');
  const elapsed=time-start,iteration=elapsed<0?0:Math.min(repeat,Math.floor(elapsed/(duration+repeatDelay)));
  let raw=elapsed>=total?1:clamp((elapsed-iteration*(duration+repeatDelay))/duration);
  if(raw>1-1e-12)raw=1;else if(raw<1e-12)raw=0;
  const odd=iteration%2===1,reverse=type==='reverse'&&odd;
  const progress=curve(easing,reverse?1-raw:raw);
  return {active:elapsed>=0&&elapsed<total,done:elapsed>=total,iteration,
    value:type==='mirror'&&odd?mixValue(b,a,progress):mixValue(a,b,progress)};
}

/** Resolve labels once. No callbacks, dynamic DOM snapshots or effects during seek. */
export function compileSequence(spec){
  if(!plain(spec)||spec.version!==1||!Array.isArray(spec.clips)||!spec.clips.length)throw Error('sequence requires version=1 and nonempty clips');
  const markers=spec.markers||{};
  if(!plain(markers))throw Error('markers must be an object');
  for(const [k,v] of Object.entries(markers))if(!k||['<','>'].includes(k)||!finite(v)||v<0)throw Error('invalid marker');
  const tracks=new Map(),ids=new Set();let previous=null;
  const resolve=at=>{
    if(finite(at))return at;
    if(at==='<')return previous?.start;
    if(at==='>')return previous?.end;
    if(typeof at==='string')return Object.hasOwn(markers,at)?markers[at]:undefined;
    if(plain(at)&&typeof at.label==='string'&&finite(at.offset)){
      const base=resolve(at.label);return finite(base)?base+at.offset:undefined;
    }
    return undefined;
  };
  for(const clip of spec.clips){
    if(!plain(clip)||typeof clip.id!=='string'||!clip.id.trim()||ids.has(clip.id)||typeof clip.track!=='string'||!clip.track.trim())throw Error('clips require unique ids and named tracks');
    if(clip.cut!==undefined&&typeof clip.cut!=='boolean')throw Error('cut must be a boolean');
    const start=resolve(clip.at),duration=clip.duration;
    if(!finite(start)||start<0||!finite(duration)||duration<=0||!finite(start+duration))throw Error(`invalid timing for ${clip.id}`);
    mixValue(clip.from,clip.to,.5);curve(clip.easing||'linear',.5);
    // Own snapshot: callers cannot mutate a compiled plan through their input object.
    const item=JSON.parse(JSON.stringify({...clip,start,end:start+duration}));
    const list=tracks.get(clip.track)||[];list.push(item);tracks.set(clip.track,list);ids.add(clip.id);previous=item;
  }
  for(const list of tracks.values()){
    list.sort((a,b)=>a.start-b.start);
    for(let i=1;i<list.length;i++){
      if(list[i].start<list[i-1].end)throw Error('overlapping clips on one track');
      if(!list[i].cut&&JSON.stringify(mixValue(list[i].from,list[i-1].to,0))!==JSON.stringify(mixValue(list[i].from,list[i-1].to,1)))throw Error('discontinuous track requires cut:true');
    }
  }
  const duration=Math.max(...[...tracks.values()].flat().map(c=>c.end));
  return {duration,at(time){
    requireNumber(time,'time');const out=[];
    for(const [name,list] of tracks){
      let value=mixValue(list[0].from,list[0].from,0);
      for(const c of list){
        if(time<c.start)break;
        value=time>=c.end?mixValue(c.to,c.to,1):mixValue(c.from,c.to,curve(c.easing||'linear',(time-c.start)/(c.end-c.start)));
      }
      out.push([name,value]);
    }
    return Object.fromEntries(out);
  }};
}

/** Quadratic/cubic Bezier or straight path, including tangent direction. */
export function pathAt(points,progress){
  requireNumber(progress,'progress');
  if(!Array.isArray(points)||points.length<2||points.length>4||points.some(p=>!plain(p)||!finite(p.x)||!finite(p.y)))throw Error('path needs 2–4 finite points');
  const p=clamp(progress),sample=list=>{
    let a=list.map(v=>({...v}));
    while(a.length>1)a=a.slice(0,-1).map((v,i)=>({x:mixValue(v.x,a[i+1].x,p),y:mixValue(v.y,a[i+1].y,p)}));
    return a[0];
  };
  const point=sample(points),n=points.length-1;
  const tangent=sample(points.slice(0,-1).map((v,i)=>({x:n*(points[i+1].x-v.x),y:n*(points[i+1].y-v.y)})));
  return {...point,angle:Math.atan2(tangent.y,tangent.x)*180/Math.PI};
}
export function arcAt(from,to,progress,height=0){
  requireNumber(height,'arc height');
  // Validate endpoints before computing the normal.
  pathAt([from,to],0);
  const dx=to.x-from.x,dy=to.y-from.y,length=Math.hypot(dx,dy);
  const control={x:(from.x+to.x)/2-(length?dy/length:0)*2*height,
    y:(from.y+to.y)/2+(length?dx/length:0)*2*height};
  return pathAt([from,control,to],progress);
}

/** Finite presence window; never extends the measured scene to await an exit callback. */
export function presenceAt(time,{start,enterEnd,exitStart,end,easing='linear'}){
  for(const [k,v] of Object.entries({time,start,enterEnd,exitStart,end}))requireNumber(v,k);
  if(!(0<=start&&start<enterEnd&&enterEnd<=exitStart&&exitStart<end))throw Error('invalid presence window');
  const active=time>=start&&time<end;
  const p=time<enterEnd?clamp((time-start)/(enterEnd-start)):time<exitStart?1:clamp((end-time)/(end-exitStart));
  return {active,opacity:active?clamp(curve(easing,p)):0,
    phase:!active?'absent':time<enterEnd?'enter':time<exitStart?'hold':'exit'};
}

/** Nested JSON sequences. Child markers/timings are local; tracks are prefixed by child IDs. */
export function compileNestedSequence(spec){
  const active=new Set();let itemCount=0;
  function walk(node,prefix,depth){
    if(!plain(node)||node.version!==1||!Array.isArray(node.items)||!node.items.length||depth>8||active.has(node))throw Error('invalid or recursive nested sequence');
    active.add(node);
    try{
      const markers=Object.hasOwn(node,'markers')?node.markers:{};if(!plain(markers))throw Error('markers must be an object');
      for(const [k,v] of Object.entries(markers))if(!k||['<','>'].includes(k)||!finite(v)||v<0)throw Error('invalid marker');
      const ids=new Set(),clips=[];let previous=null,duration=0;
      const resolve=at=>{
        if(finite(at))return at;
        if(at==='<')return previous?.start;
        if(at==='>')return previous?.end;
        if(typeof at==='string')return Object.hasOwn(markers,at)?markers[at]:undefined;
        if(plain(at)&&typeof at.label==='string'&&finite(at.offset)){const v=resolve(at.label);return finite(v)?v+at.offset:undefined;}
        return undefined;
      };
      for(const item of node.items){
        if(++itemCount>512||!plain(item)||typeof item.id!=='string'||!/^[A-Za-z0-9_-]{1,64}$/.test(item.id)||ids.has(item.id))throw Error('invalid or duplicate nested item id');
        ids.add(item.id);const start=resolve(item.at);if(!finite(start)||start<0)throw Error('invalid nested item start');
        const id=prefix+item.id;
        if(Object.hasOwn(item,'sequence')){
          if(Object.keys(item).some(k=>!['id','at','sequence'].includes(k)))throw Error('unsupported nested sequence property');
          const child=walk(item.sequence,id+'/',depth+1),end=start+child.duration;
          if(!finite(end))throw Error('invalid nested end');
          for(const clip of child.clips){const at=start+clip.at;if(!finite(at))throw Error('invalid nested clip time');clips.push({...clip,at});}
          previous={start,end};duration=Math.max(duration,end);
        }else{
          if(typeof item.track!=='string'||!item.track.trim()||item.track.includes('/')||item.track.length>128||!finite(item.duration)||item.duration<=0||!finite(start+item.duration))throw Error('invalid nested clip');
          const clip={...item,id,track:prefix+item.track,at:start};clips.push(clip);previous={start,end:start+item.duration};duration=Math.max(duration,previous.end);
        }
      }
      return {clips,duration};
    }finally{active.delete(node);}
  }
  const {clips}=walk(spec,'',0);
  // Adding parent/child decimal offsets may differ by a few ulps at a shared boundary.
  const byTrack=new Map();for(const c of clips){const list=byTrack.get(c.track)||[];list.push(c);byTrack.set(c.track,list);}
  for(const list of byTrack.values()){
    list.sort((a,b)=>a.at-b.at);let end=-Infinity;
    for(const c of list){if(c.at<end&&c.at>=end-1e-12)c.at=end;end=c.at+c.duration;}
  }
  return compileSequence({version:1,clips});
}
