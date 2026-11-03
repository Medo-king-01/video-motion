/** Draw a precompiled bounded SVG plan. No XML/DOM, scripts, fetch or CSS. */
const TOKENS=new Set(['red','redBright','redDeep','ink','inkSoft','paper','gray1','gray2','gray3','gray4','salmon','blush']);
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<=1000000;
function validFill(fill){
  if(fill===null||TOKENS.has(fill))return true;
  if(!fill||typeof fill!=='object'||Array.isArray(fill)||Object.getPrototypeOf(fill)!==Object.prototype||
     !Array.isArray(fill.stops)||fill.stops.length<2||fill.stops.length>16)return false;
  if(fill.type==='linear'){
    if(Object.keys(fill).sort().join(',')!=='stops,type,x1,x2,y1,y2'||![fill.x1,fill.y1,fill.x2,fill.y2].every(finite)||Math.hypot(fill.x2-fill.x1,fill.y2-fill.y1)<1e-9)return false;
  }else if(fill.type==='radial'){
    if(Object.keys(fill).sort().join(',')!=='cx,cy,r,stops,type'||![fill.cx,fill.cy,fill.r].every(finite)||fill.r<1e-9)return false;
  }else return false;
  return fill.stops.every((s,i)=>s&&typeof s==='object'&&!Array.isArray(s)&&Object.getPrototypeOf(s)===Object.prototype&&
    Object.keys(s).sort().join(',')==='color,offset'&&finite(s.offset)&&s.offset>=0&&s.offset<=1&&
    TOKENS.has(s.color)&&(i===0?s.offset===0:s.offset>fill.stops[i-1].offset)&&
    (i!==fill.stops.length-1||s.offset===1));
}
export function validateSvgArt(plan){
  if(!plan||plan.version!==1||!Array.isArray(plan.viewBox)||plan.viewBox.length!==4||!plan.viewBox.every(finite)||plan.viewBox[2]<=0||plan.viewBox[3]<=0||!Array.isArray(plan.shapes)||plan.shapes.length<1||plan.shapes.length>128)throw Error('invalid SVG plan');
  const ids=new Set();let total=0;
  for(const s of plan.shapes){
    if(!s||typeof s.id!=='string'||!s.id||ids.has(s.id)||!validFill(s.fill)||!(s.stroke===null||TOKENS.has(s.stroke))||!finite(s.strokeWidth)||s.strokeWidth<0||!finite(s.opacity)||s.opacity<0||s.opacity>1||!Array.isArray(s.contours)||s.contours.length<1||s.contours.length>64)throw Error('invalid SVG shape');
    ids.add(s.id);
    for(const c of s.contours){if(!c||typeof c.closed!=='boolean'||!Array.isArray(c.points)||c.points.length<(c.closed?3:2)||c.points.length>4096||c.points.some(p=>!p||!finite(p.x)||!finite(p.y)))throw Error('invalid SVG contour');total+=c.points.length;if(total>65536)throw Error('SVG point budget exceeded');}
  }
  return plan;
}
/** @param {any} plan @param {{x?:number,y?:number,width:number,height:number}} options */
export function svgPlacement(plan,options){
  const {x=0,y=0,width,height}=options||{};
  validateSvgArt(plan);if(![x,y,width,height].every(finite)||width<=0||height<=0)throw Error('invalid SVG placement');
  const [vx,vy,vw,vh]=plan.viewBox,s=Math.min(width/vw,height/vh);
  if(!Number.isFinite(s)||s<=0||s>1000000)throw Error('invalid SVG scale');
  const px=x+(width-vw*s)/2-vx*s,py=y+(height-vh*s)/2-vy*s;
  if(!Number.isFinite(px)||!Number.isFinite(py))throw Error('invalid SVG placement');
  for(const shape of plan.shapes){
    if(shape.strokeWidth*s>100000)throw Error('SVG stroke exceeds output budget');
    if(shape.fill&&typeof shape.fill==='object'){
      const g=shape.fill;
      const endpoints=g.type==='linear'?[px+g.x1*s,px+g.x2*s,py+g.y1*s,py+g.y2*s]:[px+g.cx*s,py+g.cy*s,g.r*s];
      const extent=g.type==='linear'?Math.hypot((g.x2-g.x1)*s,(g.y2-g.y1)*s):g.r*s;
      if(extent<1e-9||endpoints.some(v=>!Number.isFinite(v)||Math.abs(v)>10000000))throw Error('SVG gradient exceeds output budget');
    }
    for(const contour of shape.contours)for(const p of contour.points)if(!Number.isFinite(px+p.x*s)||!Number.isFinite(py+p.y*s)||Math.abs(px+p.x*s)>10000000||Math.abs(py+p.y*s)>10000000)throw Error('SVG coordinates exceed output budget');
  }
  return {scale:s,x:px,y:py};
}

/** Resolve stroke windows against an already validated SVG plan. Inputs are explicit frame values. */
export function svgStrokeWindows(plan,options={}){
  const read=(obj,key,fallback)=>Object.hasOwn(obj,key)&&obj[key]!==undefined?obj[key]:fallback;
  const interval=(start,end,offset)=>{
    if(![start,end,offset].every(finite)||start<0||end>1||start>end)throw Error('invalid SVG stroke window');
    return {start,end,offset};
  };
  const base=interval(read(options,'strokeStart',0),read(options,'progress',1),read(options,'strokeOffset',0));
  const supplied=read(options,'strokeWindows',{});
  if(!supplied||typeof supplied!=='object'||Array.isArray(supplied)||![Object.prototype,null].includes(Object.getPrototypeOf(supplied)))throw Error('invalid SVG stroke windows');
  const byId=new Map(plan.shapes.map(s=>[s.id,s]));const windows=new Map();
  for(const [id,list] of Object.entries(supplied)){
    const shape=byId.get(id);
    if(!shape||!Array.isArray(list)||list.length!==shape.contours.length)throw Error('unknown shape or incorrect SVG contour window count');
    const resolved=[];
    for(let i=0;i<list.length;i++){
      if(!Object.hasOwn(list,i))throw Error('missing SVG contour window');
      const value=list[i];
      if(value===null){resolved.push(base);continue;}
      if(!value||typeof value!=='object'||Array.isArray(value)||![Object.prototype,null].includes(Object.getPrototypeOf(value))||
         !Object.hasOwn(value,'start')||!Object.hasOwn(value,'end')||Object.keys(value).some(k=>!['start','end','offset'].includes(k)))throw Error('invalid SVG contour window');
      resolved.push(interval(value.start,value.end,read(value,'offset',base.offset)));
    }
    windows.set(id,resolved);
  }
  return {base,windows};
}
