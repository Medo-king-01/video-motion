// Original offline layout/shape/binding grammar. No DOM snapshots, UI or mutable frame history.
import {ease,clamp} from './motion.js';
import {mixValue} from './motion-plan.js';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&Object.getPrototypeOf(x)===Object.prototype;
const num=(x,name)=>{if(!finite(x))throw Error(`${name} must be finite`);return x;};
const pos=(x,name)=>{num(x,name);if(x<=0)throw Error(`${name} must be positive`);return x;};
const copy=x=>JSON.parse(JSON.stringify(x));
const opt=(o,k,d)=>o[k]===undefined?d:o[k];
const flag=(x,name)=>{if(typeof x!=='boolean')throw Error(`${name} must be boolean`);return x;};
function boxes(items){
  if(!Array.isArray(items)||items.length>256)throw Error('layout needs <=256 items');
  const ids=new Set();return items.map(item=>{
    if(!obj(item)||typeof item.id!=='string'||!item.id.trim()||ids.has(item.id))throw Error('layout ids must be unique');
    ids.add(item.id);const {x,y,w,h}=item,r=opt(item,'r',0);
    num(x,'x');num(y,'y');pos(w,'w');pos(h,'h');num(r,'r');
    if(r<0||r>Math.min(w,h)/2)throw Error('radius outside box');
    num(x+w,'right');num(y+h,'bottom');return {id:item.id,x,y,w,h,r};
  });
}
/** Stable-id row/column/grid snapshots, not browser-dependent reflow. */
export function stackLayout(items,{x=0,y=0,gap=16,axis='y',columns=2,rtl=false}={}){
  num(x,'x');num(y,'y');num(gap,'gap');flag(rtl,'rtl');
  if(gap<0||!['x','y','grid'].includes(axis)||!Number.isInteger(columns)||columns<1||columns>256)throw Error('invalid stack options');
  const source=boxes(items.map(i=>({...i,x:0,y:0}))),out=[];
  const cellW=Math.max(0,...source.map(i=>i.w));let cursor=0,rowY=y;
  source.forEach((item,i)=>{
    let left=x,top=y;
    if(axis==='x'){left=rtl?x-cursor-item.w:x+cursor;cursor+=item.w+gap;}
    if(axis==='y'){top=y+cursor;cursor+=item.h+gap;if(rtl)left=x-item.w;}
    if(axis==='grid'){
      const col=i%columns;if(col===0&&i>0)rowY+=Math.max(...source.slice(i-columns,i).map(b=>b.h))+gap;
      left=rtl?x-col*(cellW+gap)-item.w:x+col*(cellW+gap);top=rowY;
    }
    out.push({...item,x:left,y:top});
  });return boxes(out);
}
export function reorderLayout(items,order,options={}){
  const source=boxes(items.map(i=>({...i,x:0,y:0}))),byId=new Map(source.map(i=>[i.id,i]));
  if(!Array.isArray(order)||order.length!==source.length||new Set(order).size!==order.length||order.some(id=>!byId.has(id)))throw Error('order must be an exact permutation');
  return stackLayout(order.map(id=>byId.get(id)),options);
}
/** One shell per stable id; wait/sync/popLayout are authored finite windows. */
export function compileLayout(spec){
  if(!obj(spec)||spec.version!==1||!Array.isArray(spec.events))throw Error('layout requires version=1/events');
  const initial=boxes(spec.initial),events=[];let previous=initial,end=0;
  for(const raw of spec.events){
    if(!obj(raw)||!finite(raw.at)||raw.at<0||raw.at<end-1e-12)throw Error('layout transitions must not overlap');
    const duration=pos(raw.duration,'duration'),mode=opt(raw,'mode','sync'),easing=opt(raw,'easing','cubicInOut');
    if(!['sync','wait','popLayout'].includes(mode))throw Error('invalid presence mode');
    num(ease(easing,.5),'easing');const next=boxes(raw.items),start=Math.max(raw.at,end);
    end=num(start+duration*(mode==='wait'?3:1),'end');
    events.push({start,end,duration,mode,easing,from:previous,to:next});previous=next;
  }
  const held=items=>items.map(({id,...box})=>({id,box:{...box},opacity:1,phase:'hold',layer:'flow'}));
  return {duration:end,at(t){
    num(t,'time');let items=initial;
    for(const e of events){
      if(t<e.start)break;if(t>=e.end){items=e.to;continue;}
      const from=new Map(e.from.map(i=>[i.id,i])),to=new Map(e.to.map(i=>[i.id,i]));
      const local=t-e.start,moveStart=e.mode==='wait'?e.duration:0,enterStart=e.mode==='wait'?2*e.duration:0;
      const progress=start=>clamp(ease(e.easing,clamp((local-start)/e.duration)));
      const move=progress(moveStart),enter=progress(enterStart),exit=progress(0),out=[];
      for(const item of e.to){
        const {id,...target}=item,old=from.get(id);
        if(old){const {id:ignored,...source}=old;out.push({id,box:mixValue(source,target,move),opacity:1,phase:move>=1?'hold':'move',layer:'flow'});}
        else if(enter>0)out.push({id,box:target,opacity:enter,phase:'enter',layer:'flow'});
      }
      for(const item of e.from)if(!to.has(item.id)&&exit<1){const {id,...box}=item;out.push({id,box,opacity:1-exit,phase:'exit',layer:e.mode==='popLayout'?'overlay':'flow'});}
      return out;
    }
    return held(items);
  }};
}
/** Axis-aligned scale compensation only. Native box rendering is preferred for text/strokes. */
export function correctScale({scaleX,scaleY,radius=0,strokeWidth=0}){
  pos(scaleX,'scaleX');pos(scaleY,'scaleY');num(radius,'radius');num(strokeWidth,'strokeWidth');
  if(radius<0||strokeWidth<0)throw Error('invalid scale correction');
  return {radiusX:num(radius/scaleX,'radiusX'),radiusY:num(radius/scaleY,'radiusY'),strokeX:num(strokeWidth/scaleX,'strokeX'),strokeY:num(strokeWidth/scaleY,'strokeY')};
}
function pathPoints(points,closed=false){
  flag(closed,'closed');
  if(!Array.isArray(points)||points.length<(closed?3:2)||points.length>4096||points.some(p=>!obj(p)||!finite(p.x)||!finite(p.y)))throw Error('invalid polyline points');
  const out=points.map(p=>({x:p.x,y:p.y}));
  if(closed&&(out[0].x!==out.at(-1).x||out[0].y!==out.at(-1).y))out.push({...out[0]});return out;
}
function pathInfo(points,closed){
  const p=pathPoints(points,closed),edges=[],distance=[0];let length=0;
  for(let i=1;i<p.length;i++){
    const size=num(Math.hypot(p[i].x-p[i-1].x,p[i].y-p[i-1].y),'edge length');
    edges.push(size);length=num(length+size,'path length');distance.push(length);
  }
  const at=d=>{
    if(d<=0)return {...p[0]};if(d>=length)return {...p.at(-1)};
    for(let i=0;i<edges.length;i++)if(edges[i]>0&&d<=distance[i+1])return mixValue(p[i],p[i+1],(d-distance[i])/edges[i]);
    return {...p.at(-1)};
  };return {points:p,length,distance,at};
}
/** Visible path window; offset wraps, start/end never get confused with scene timing. */
export function strokeSegments(points,{start=0,end=1,offset=0,closed=false}={}){
  num(start,'start');num(end,'end');num(offset,'offset');if(start<0||end>1||start>end)throw Error('invalid stroke interval');
  const path=pathInfo(points,closed),size=end-start;if(!path.length||!size)return [];
  if(size===1)return [path.points];
  const first=((start+offset)%1+1)%1,last=first+size,ranges=last<=1?[[first,last]]:[[first,1],[0,last-1]];
  return ranges.filter(([a,b])=>b>a).map(([a,b])=>{
    const lo=a*path.length,hi=b*path.length,result=[path.at(lo)];
    path.points.forEach((p,i)=>{if(path.distance[i]>lo&&path.distance[i]<hi)result.push({...p});});result.push(path.at(hi));return result;
  });
}
export function normalizeShape(points,count=64,{closed=true}={}){
  if(!Number.isInteger(count)||count<(closed?3:2)||count>256)throw Error('invalid resample count');
  const path=pathInfo(points,closed);if(path.length===0)throw Error('shape must have positive length');
  return Array.from({length:count},(_,i)=>path.at(path.length*i/(closed?count:count-1)));
}
const area=points=>points.reduce((sum,p,i)=>{const q=points[(i+1)%points.length];return sum+p.x*q.y-q.x*p.y;},0)/2;
/** Single-ring polygon/open-polyline morph, not arbitrary SVG parsing/topology conversion. */
export function compileMorph({from,to,count=64,closed=true,align=true}){
  flag(closed,'closed');flag(align,'align');
  let a=normalizeShape(from,count,{closed}),b=normalizeShape(to,count,{closed});
  if(closed&&align){
    if(area(a)*area(b)<0)b=[b[0],...b.slice(1).reverse()];
    let best=Infinity,index=0;
    for(let shift=0;shift<count;shift++){
      const score=num(a.reduce((sum,p,i)=>{const q=b[(i+shift)%count];return sum+(p.x-q.x)**2+(p.y-q.y)**2;},0),'alignment score');
      if(score<best){best=score;index=shift;}
    }
    b=b.map((_,i)=>b[(i+index)%count]);
  }
  return {at(p){num(p,'progress');return mixValue(a,b,clamp(p));}};
}
/** Pick from real, premeasured full-word lines; no estimated glyph widths or forced tiny text. */
export function fitMeasuredText(spec){
  if(!obj(spec)||typeof spec.text!=='string'||!spec.text.trim()||!obj(spec.font)||typeof spec.font.family!=='string'||!spec.font.family.trim()||!Number.isInteger(spec.font.weight)||spec.font.weight<100||spec.font.weight>900)throw Error('explicit text/font required');
  const {maxWidth,maxHeight,candidates}=spec,padding=opt(spec,'padding',0),lineHeight=opt(spec,'lineHeight',1.3);
  pos(maxWidth,'maxWidth');pos(maxHeight,'maxHeight');num(padding,'padding');pos(lineHeight,'lineHeight');
  if(padding<0||!Array.isArray(candidates)||!candidates.length||candidates.length>512)throw Error('invalid measured candidates');
  const norm=s=>s.trim().split(/\s+/).join(' '),sizes=new Set(),valid=[];
  for(const c of candidates){
    if(!obj(c)||!finite(c.size)||c.size<=0||sizes.has(c.size)||!['canvas','harfbuzz'].includes(c.measuredBy)||!Array.isArray(c.lines)||!c.lines.length)throw Error('invalid text candidate');
    sizes.add(c.size);let height=0,width=0;const lines=[];
    for(const line of c.lines){
      if(!obj(line)||typeof line.text!=='string'||!line.text.trim())throw Error('invalid measured line');
      num(line.w,'line width');pos(line.h,'line height');if(line.w<0)throw Error('negative width');
      const cell=Math.max(c.size*lineHeight,line.h);lines.push({text:line.text,x:padding+(maxWidth-2*padding-line.w)/2,y:padding+height+(cell-line.h)/2,w:line.w,h:line.h});
      height+=cell;width=Math.max(width,line.w);
    }
    if(norm(c.lines.map(l=>l.text).join(' '))!==norm(spec.text))throw Error('text fit may not omit/split words');
    lines.forEach(line=>{line.x=padding+(width-line.w)/2;});
    if(width+2*padding<=maxWidth&&height+2*padding<=maxHeight)valid.push({fits:true,size:c.size,font:{...spec.font},measuredBy:c.measuredBy,w:width+2*padding,h:height+2*padding,lines});
  }
  valid.sort((a,b)=>b.size-a.size);return valid[0]??{fits:false,size:null,font:{...spec.font},measuredBy:null,w:0,h:0,lines:[]};
}
const TOKENS=['red','redBright','redDeep','ink','inkSoft','paper','gray1','gray2','gray3','gray4','salmon','blush'];
/** Typed numeric/point bindings and palette tokens only; never eval arbitrary CSS/HTML. */
export function compileBindings(spec){
  if(!obj(spec)||spec.version!==1||!Array.isArray(spec.bindings)||spec.bindings.length>256)throw Error('bindings require version=1/bindings');
  const bindings=copy(spec.bindings),ids=new Set();
  for(const b of bindings){
    if(!obj(b)||typeof b.id!=='string'||!b.id.trim()||ids.has(b.id)||!['rect','circle','path'].includes(b.kind)||!obj(opt(b,'constants',{}))||!obj(opt(b,'tracks',{})))throw Error('invalid binding');
    ids.add(b.id);b.constants=opt(b,'constants',{});b.tracks=opt(b,'tracks',{});
    const allowed=new Set(['opacity','strokeWidth',...(b.kind==='rect'?['x','y','w','h','r']:b.kind==='circle'?['x','y','r']:['points','start','end','offset','closed'])]);
    if([...Object.keys(b.constants),...Object.keys(b.tracks)].some(k=>!allowed.has(k))||Object.values(b.tracks).some(v=>typeof v!=='string'||!v)||Object.keys(b.tracks).some(k=>Object.hasOwn(b.constants,k)))throw Error('unknown/conflicting property binding');
    b.fill=opt(b,'fill',b.kind==='path'?null:'gray1');b.stroke=opt(b,'stroke','ink');
    for(const token of [b.fill,b.stroke])if(token!==null&&!TOKENS.includes(token))throw Error('color must be a palette token or null');
  }
  return {at(values){
    if(!obj(values))throw Error('binding values must be an object');
    return bindings.map(b=>{
      const p={opacity:1,strokeWidth:3,...b.constants};
      for(const [k,ref] of Object.entries(b.tracks)){if(!Object.hasOwn(values,ref))throw Error(`missing binding value ${ref}`);p[k]=copy(values[ref]);}
      num(p.opacity,'opacity');num(p.strokeWidth,'strokeWidth');if(p.opacity<0||p.opacity>1||p.strokeWidth<0)throw Error('invalid paint');
      if(b.kind==='rect'){const [box]=boxes([{id:b.id,...p}]);Object.assign(p,box);delete p.id;}
      if(b.kind==='circle'){num(p.x,'x');num(p.y,'y');pos(p.r,'r');}
      if(b.kind==='path'){
        p.closed=opt(p,'closed',false);pathPoints(p.points,p.closed);p.start=opt(p,'start',0);p.end=opt(p,'end',1);p.offset=opt(p,'offset',0);
        strokeSegments(p.points,p);if(!p.closed&&b.fill!==null)throw Error('open path cannot be filled');
      }
      return {id:b.id,kind:b.kind,fill:b.fill,stroke:b.stroke,props:p};
    });
  }};
}
/** Structured CSS properties for native-size boxes; no string interpolation or font scaling. */
export function boxStyle(item,palette){
  if(item.kind!=='rect')throw Error('boxStyle requires a rect binding');
  const p=item.props;
  const color=token=>{if(token===null)return 'transparent';if(!Object.hasOwn(palette,token))throw Error('missing palette token');return palette[token];};
  return {position:'absolute',boxSizing:'border-box',left:p.x,top:p.y,width:p.w,height:p.h,borderRadius:p.r,
    borderWidth:item.stroke===null?0:p.strokeWidth,borderStyle:'solid',borderColor:color(item.stroke),background:color(item.fill),opacity:p.opacity};
}

/** Native geometry adapter for a layout sample, with explicit overlay ordering. */
export function layoutBindings(states,{fill='gray1',stroke='ink',strokeWidth=3,colors={}}={}){
  if(!Array.isArray(states)||!obj(colors))throw Error('invalid layout sample/colors');
  const ordered=states.map((s,i)=>{
    if(!obj(s)||!obj(s.box)||!['flow','overlay'].includes(s.layer))throw Error('invalid layout sample');
    return {state:s,index:i};
  }).sort((a,b)=>(a.state.layer==='overlay'?1:0)-(b.state.layer==='overlay'?1:0)||a.index-b.index);
  return compileBindings({version:1,bindings:ordered.map(({state:s})=>({id:s.id,kind:'rect',fill:Object.hasOwn(colors,s.id)?colors[s.id]:fill,stroke,
    constants:{...s.box,opacity:s.opacity,strokeWidth}}))}).at({});
}
