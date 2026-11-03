/** Bounded SVG morph with conservative continuous-time polygon topology checks. */
import {compileMorph} from './motion-geometry.js';
import {validateSvgArt} from './svg-art.js';
const cross=(a,b)=>a[0]*b[1]-a[1]*b[0],dot=(a,b)=>a[0]*b[0]+a[1]*b[1],sub=(a,b)=>[a[0]-b[0],a[1]-b[1]];
const position=(p,t)=>[p[0][0]+(p[1][0]-p[0][0])*t,p[0][1]+(p[1][1]-p[0][1])*t];
const vector=(a,b)=>[sub(b[0],a[0]),sub(b[1],a[1])];
function quadratic(u,v,prod){const u0=u[0],v0=v[0],du=sub(u[1],u0),dv=sub(v[1],v0);return [prod(u0,v0),prod(u0,dv)+prod(du,v0),prod(du,dv)];}
const orient=(a,b,c)=>quadratic(vector(a,b),vector(a,c),cross);
const dotAt=(a,b,c)=>quadratic(vector(b,a),vector(b,c),dot);
function range([c,b,a],lo,hi){
  const f=t=>(a*t+b)*t+c,vals=[f(lo),f(hi)];
  if(a!==0){const v=-b/(2*a);if(v>lo&&v<hi)vals.push(f(v));}
  return [Math.min(...vals),Math.max(...vals)];
}
const sameSide=(x,y,eps)=>(x[0]>eps&&y[0]>eps)||(x[1]<-eps&&y[1]<-eps);
function edgesSeparate(a,b,c,d,lo,hi,eps,linearEps,budget,depth=0){
  if(++budget.count>50000)throw Error('morph topology verification budget exceeded');
  const ab=[a,b].flatMap(p=>[position(p,lo),position(p,hi)]),cd=[c,d].flatMap(p=>[position(p,lo),position(p,hi)]);
  if([0,1].some(k=>Math.max(...ab.map(p=>p[k]))+linearEps<Math.min(...cd.map(p=>p[k]))||Math.max(...cd.map(p=>p[k]))+linearEps<Math.min(...ab.map(p=>p[k]))))return true;
  if(sameSide(range(orient(a,b,c),lo,hi),range(orient(a,b,d),lo,hi),eps)||sameSide(range(orient(c,d,a),lo,hi),range(orient(c,d,b),lo,hi),eps))return true;
  if(depth>=12)return false;const mid=(lo+hi)/2;
  return edgesSeparate(a,b,c,d,lo,mid,eps,linearEps,budget,depth+1)&&edgesSeparate(a,b,c,d,mid,hi,eps,linearEps,budget,depth+1);
}
function adjacentSafe(a,b,c,lo,hi,eps,budget,depth=0){
  if(++budget.count>50000)throw Error('morph topology verification budget exceeded');
  const o=range(orient(a,b,c),lo,hi);
  if(o[0]>eps||o[1]<-eps||range(dotAt(a,b,c),lo,hi)[1]<-eps)return true;
  if(depth>=12)return false;const mid=(lo+hi)/2;
  return adjacentSafe(a,b,c,lo,mid,eps,budget,depth+1)&&adjacentSafe(a,b,c,mid,hi,eps,budget,depth+1);
}
function inside(point,ring,t){
  const [x,y]=position(point,t);let result=false;
  for(let i=0;i<ring.length;i++){
    const [ax,ay]=position(ring[i],t),[bx,by]=position(ring[(i+1)%ring.length],t);
    if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)result=!result;
  }
  return result;
}
function validateRings(rings){
  const scale=Math.max(1,...rings.flatMap(r=>r.flatMap(p=>p.flatMap(pos=>pos.map(Math.abs))))),eps=1e-10*scale*scale,linearEps=1e-10*scale,budget={count:0};
  for(const ring of rings){
    const area=[0,0,0],n=ring.length;
    for(let i=0;i<n;i++){
      const point=ring[i],next=ring[(i+1)%n],after=ring[(i+2)%n],v=vector(point,next);
      if(range(quadratic(v,v,dot),0,1)[0]<=eps)throw Error('morph edge can collapse');
      const q=quadratic(point,next,cross);for(let k=0;k<3;k++)area[k]+=q[k];
      if(!adjacentSafe(point,next,after,0,1,eps,budget))throw Error('morph adjacent edges may overlap');
    }
    const bounds=range(area,0,1);if(bounds[0]<=eps&&bounds[1]>=-eps)throw Error('morph ring area may collapse');
    for(let i=0;i<n;i++)for(let j=i+1;j<n;j++){
      if(j===i+1||(i===0&&j===n-1))continue;
      if(!edgesSeparate(ring[i],ring[(i+1)%n],ring[j],ring[(j+1)%n],0,1,eps,linearEps,budget))throw Error('morph ring may self-intersect');
    }
  }
  for(let i=0;i<rings.length;i++)for(let j=i+1;j<rings.length;j++){
    const a=rings[i],b=rings[j];
    for(let k=0;k<a.length;k++)for(let q=0;q<b.length;q++)if(!edgesSeparate(a[k],a[(k+1)%a.length],b[q],b[(q+1)%b.length],0,1,eps,linearEps,budget))throw Error('morph contours may intersect');
    if(inside(a[0],b,0)!==inside(a[0],b,1)||inside(b[0],a,0)!==inside(b[0],a,1))throw Error('morph contour nesting differs');
  }
}
/** Pair shapes and closed contours by authored index; no topology changes or automatic matching. */
export function compileSvgMorph(spec){
  if(!spec||spec.version!==1)throw Error('SVG morph requires version 1');
  const source=spec.from,target=spec.to,count=Object.hasOwn(spec,'count')?spec.count:24;validateSvgArt(source);validateSvgArt(target);
  if(!Number.isInteger(count)||count<8||count>64||JSON.stringify(source.viewBox)!==JSON.stringify(target.viewBox)||source.shapes.length!==target.shapes.length||source.shapes.length>8)throw Error('incompatible SVG morph plans');
  const morphs=[];let total=0;
  source.shapes.forEach((a,i)=>{
    const b=target.shapes[i];
    if(['id','fill','stroke','strokeWidth','opacity'].some(k=>a[k]!==b[k])||a.contours.length!==b.contours.length)throw Error('SVG shape paint/contour mismatch');
    const group=[],rings=[];
    a.contours.forEach((x,j)=>{
      const y=b.contours[j];total+=count;
      if(!x.closed||!y.closed||total>192)throw Error('SVG morph needs closed contours within sample budget');
      const plan=compileMorph({from:x.points,to:y.points,count,closed:true,align:true}),start=plan.at(0),end=plan.at(1);
      rings.push(start.map((p,k)=>[[p.x,p.y],[end[k].x,end[k].y]]));group.push(plan);
    });
    validateRings(rings);morphs.push(group);
  });
  const base=JSON.parse(JSON.stringify(source));
  return {at(progress){
    if(typeof progress!=='number'||!Number.isFinite(progress))throw Error('progress must be finite');
    const result=JSON.parse(JSON.stringify(base));
    result.shapes.forEach((shape,i)=>shape.contours.forEach((contour,j)=>{contour.points=morphs[i][j].at(progress);}));
    return result;
  }};
}
