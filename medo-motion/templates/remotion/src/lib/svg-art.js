/** Draw a precompiled bounded SVG plan. No XML/DOM, scripts, fetch or CSS. */
const TOKENS=new Set(['red','redBright','redDeep','ink','inkSoft','paper','gray1','gray2','gray3','gray4','salmon','blush']);
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<=1000000;
export function validateSvgArt(plan){
  if(!plan||plan.version!==1||!Array.isArray(plan.viewBox)||plan.viewBox.length!==4||!plan.viewBox.every(finite)||plan.viewBox[2]<=0||plan.viewBox[3]<=0||!Array.isArray(plan.shapes)||plan.shapes.length<1||plan.shapes.length>128)throw Error('invalid SVG plan');
  const ids=new Set();let total=0;
  for(const s of plan.shapes){
    if(!s||typeof s.id!=='string'||!s.id||ids.has(s.id)||![s.fill,s.stroke].every(t=>t===null||TOKENS.has(t))||!finite(s.strokeWidth)||s.strokeWidth<0||!finite(s.opacity)||s.opacity!==1||!Array.isArray(s.contours)||s.contours.length<1||s.contours.length>64)throw Error('invalid SVG shape');
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
    for(const contour of shape.contours)for(const p of contour.points)if(!Number.isFinite(px+p.x*s)||!Number.isFinite(py+p.y*s)||Math.abs(px+p.x*s)>10000000||Math.abs(py+p.y*s)>10000000)throw Error('SVG coordinates exceed output budget');
  }
  return {scale:s,x:px,y:py};
}
