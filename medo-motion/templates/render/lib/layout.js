// Original studio QA instrumentation. Boxes are conservative screen-space ink AABBs,
// not pixel segmentation: clipping/occlusion and readability still need visual review.
import { BRAND } from './brand.js';
const captures = new WeakMap();
const finite = n => typeof n === 'number' && Number.isFinite(n);
export function screenBox(ctx, box) {
  const m = ctx.getTransform(), sx = BRAND.W / ctx.canvas.width, sy = BRAND.H / ctx.canvas.height;
  const points = [[box.x,box.y],[box.x+box.w,box.y],[box.x,box.y+box.h],[box.x+box.w,box.y+box.h]]
    .map(([x,y]) => [(m.a*x+m.c*y+m.e)*sx,(m.b*x+m.d*y+m.f)*sy]);
  const xs=points.map(p=>p[0]), ys=points.map(p=>p[1]);
  return {x:Math.min(...xs),y:Math.min(...ys),w:Math.max(...xs)-Math.min(...xs),h:Math.max(...ys)-Math.min(...ys)};
}
export function withLayout(ctx, meta, draw) {
  const capture=captures.get(ctx), previous=capture?.meta;
  if(capture)capture.meta=meta;
  try{return draw();}finally{if(capture)capture.meta=previous;}
}
export function protectBox(ctx,id,box,kind='face') {
  const c=captures.get(ctx);
  if(c && ctx.globalAlpha>0.01)c.boxes.push({id,kind,...screenBox(ctx,box)});
}
export function captureLayout(ctx) {
  if(captures.has(ctx))return captures.get(ctx);
  const state={boxes:[],meta:null,begin(){this.boxes=[];this.meta=null;},snapshot(){return this.boxes.map(b=>({...b}));}};
  captures.set(ctx,state);
  for(const method of ['fillText','strokeText']) {
    const original=ctx[method].bind(ctx);
    ctx[method]=(text,x,y,maxWidth)=>{
      if(ctx.globalAlpha>0.01 && String(text).trim()) {
        const m=ctx.measureText(String(text));
        const ratio=maxWidth===undefined?1:Math.min(1,maxWidth/Math.max(m.width,1e-9));
        const box=screenBox(ctx,{x:x-m.actualBoundingBoxLeft*ratio,y:y-m.actualBoundingBoxAscent,
          w:(m.actualBoundingBoxLeft+m.actualBoundingBoxRight)*ratio,h:m.actualBoundingBoxAscent+m.actualBoundingBoxDescent});
        const meta=state.meta||{};
        const item={id:meta.id||`text-${state.boxes.length}`,kind:'text',zone:meta.zone||'content',text:String(text),...box};
        // One stroke/fill pair for the same ink is one element, not a collision.
        if(!state.boxes.some(b=>b.kind==='text'&&b.text===item.text&&['x','y','w','h'].every(k=>Math.abs(b[k]-item[k])<0.01)))state.boxes.push(item);
      }
      return maxWidth===undefined?original(text,x,y):original(text,x,y,maxWidth);
    };
  }
  return state;
}
export function auditLayout(boxes,{minOverlap=2}={}) {
  if(!Array.isArray(boxes))throw Error('Layout capture is missing');
  const issues=[];
  for(const b of boxes) {
    if(!b||typeof b.id!=='string'||!b.id.trim()||!['text','face','keep'].includes(b.kind)||!['x','y','w','h'].every(k=>finite(b[k]))||b.w<=0||b.h<=0) {
      issues.push({code:'L00',ids:[b?.id||'?'],message:'Invalid registered box'});continue;
    }
    if(b.kind!=='text')continue;
    const zone=b.zone||'content';
    const range=zone==='caption'?[BRAND.safe.contentY[1],BRAND.safe.belowIsDead]:zone==='hud'?[0,BRAND.safe.contentY[0]]:BRAND.safe.contentY;
    if(!['content','caption','hud'].includes(zone))issues.push({code:'L00',ids:[b.id],message:'Unknown text zone'});
    if(b.x<BRAND.safe.margin||b.x+b.w>BRAND.W-BRAND.safe.margin||b.y<range[0]||b.y+b.h>range[1])
      issues.push({code:'L01',ids:[b.id],message:`Ink outside ${zone} safe zone`});
  }
  for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++) {
    const a=boxes[i],b=boxes[j];
    if(!a||!b||(a.kind!=='text'&&b.kind!=='text'))continue;
    const ox=Math.min(a.x+a.w,b.x+b.w)-Math.max(a.x,b.x),oy=Math.min(a.y+a.h,b.y+b.h)-Math.max(a.y,b.y);
    if(ox>=minOverlap&&oy>=minOverlap)issues.push({code:a.kind==='face'||b.kind==='face'?'L03':'L02',ids:[a.id,b.id],message:'Overlapping protected ink/box'});
  }
  return issues;
}
