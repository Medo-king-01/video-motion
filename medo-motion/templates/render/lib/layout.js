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
  const restore=()=>{if(capture)capture.meta=previous;};
  try{
    const res=draw();
    if(res&&typeof res.then==='function')return res.finally(restore);
    restore();
    return res;
  }catch(err){restore();throw err;}
}

export function setStageWindow(ctx, win) {
  const capture=captures.get(ctx);
  if(capture)capture.stageWin=win&&typeof win==='object'?{...win}:null;
}

export function withStageLayer(ctx, layer, win, draw) {
  if(!['under','content','over'].includes(layer))throw Error(`Unknown Fixed Stage layer: ${layer}`);
  const capture=captures.get(ctx), prevLayer=capture?.layer;
  if(capture){
    capture.layer=layer;
    if(win&&typeof win==='object')capture.stageWin={...win};
  }
  const restore=()=>{if(capture)capture.layer=prevLayer;};
  try{
    const res=draw();
    if(res&&typeof res.then==='function')return res.finally(restore);
    restore();
    return res;
  }catch(err){restore();throw err;}
}

export function protectBox(ctx,id,box,kind='face',opts={}) {
  const c=captures.get(ctx);
  if(c && ctx.globalAlpha>0.01){
    const meta=c.meta||{};
    const layer=opts.layer||meta.layer||c.layer;
    const entry={id,kind,...screenBox(ctx,box)};
    if(layer&&['under','content','over'].includes(layer))entry.layer=layer;
    if(opts.chrome===true||meta.chrome===true)entry.chrome=true;
    c.boxes.push(entry);
  }
}

export function captureLayout(ctx) {
  if(captures.has(ctx))return captures.get(ctx);
  const state={
    boxes:[],meta:null,layer:null,stageWin:null,
    begin(){this.boxes=[];this.meta=null;this.layer=null;this.stageWin=null;},
    snapshot(){return this.boxes.map(b=>({...b}));},
    stageWindow(){return this.stageWin?{...this.stageWin}:null;},
  };
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
        const layer=meta.layer||state.layer;
        const item={id:meta.id||`text-${state.boxes.length}`,kind:'text',zone:meta.zone||'content',text:String(text),...box};
        if(layer&&['under','content','over'].includes(layer))item.layer=layer;
        // One stroke/fill pair for the same ink is one element, not a collision.
        if(!state.boxes.some(b=>b.kind==='text'&&b.text===item.text&&b.layer===item.layer&&['x','y','w','h'].every(k=>Math.abs(b[k]-item[k])<0.01)))state.boxes.push(item);
      }
      return maxWidth===undefined?original(text,x,y):original(text,x,y,maxWidth);
    };
  }
  return state;
}

export const PLATFORM_RIGHT_RAIL = Object.freeze({ x: 940, y: 1100, w: 140, h: 400 });

export function safeEnvelope(zone='content',{checkPlatformUi=true}={}) {
  if(!['content','caption','hud'].includes(zone))throw Error(`Unknown layout zone: ${zone}`);
  const y=zone==='caption'?[BRAND.safe.contentY[1],BRAND.safe.belowIsDead]:zone==='hud'?[0,BRAND.safe.contentY[0]]:BRAND.safe.contentY;
  return {
    w:BRAND.W,h:BRAND.H,fps:BRAND.FPS,margin:BRAND.safe.margin,zone,
    x:[BRAND.safe.margin,BRAND.W-BRAND.safe.margin],y:[y[0],y[1]],
    nothingImportantBelowY:BRAND.safe.belowIsDead,
    platformRightRail:checkPlatformUi?{...PLATFORM_RIGHT_RAIL}:null,
  };
}

function isStageFullscreen(win) {
  if(!win||typeof win!=='object')return true;
  if(!['x','y','w','h'].every(k=>finite(win[k])))return true;
  const r=finite(win.r)?win.r:0;
  return Math.abs(win.x)<=1e-4&&Math.abs(win.y)<=1e-4&&Math.abs(win.w-BRAND.W)<=1e-4&&Math.abs(win.h-BRAND.H)<=1e-4&&Math.abs(r)<=1e-4;
}

function windowCornerClips(box,win,eps=0.5) {
  const r=finite(win.r)?win.r:0;
  if(r<=eps)return [];
  const bx0=box.x,by0=box.y,bx1=bx0+box.w,by1=by0+box.h;
  const wx0=win.x,wy0=win.y,wx1=wx0+win.w,wy1=wy0+win.h;
  const px0=Math.max(wx0,Math.min(wx1,bx0)),py0=Math.max(wy0,Math.min(wy1,by0));
  const px1=Math.max(wx0,Math.min(wx1,bx1)),py1=Math.max(wy0,Math.min(wy1,by1));
  if(px1<=px0||py1<=py0)return [];
  const out=[];
  if(px0<wx0+r&&py0<wy0+r&&Math.hypot((wx0+r)-px0,(wy0+r)-py0)>r+eps)out.push('top-left');
  if(px1>wx1-r&&py0<wy0+r&&Math.hypot(px1-(wx1-r),(wy0+r)-py0)>r+eps)out.push('top-right');
  if(px0<wx0+r&&py1>wy1-r&&Math.hypot((wx0+r)-px0,py1-(wy1-r))>r+eps)out.push('bottom-left');
  if(px1>wx1-r&&py1>wy1-r&&Math.hypot(px1-(wx1-r),py1-(wy1-r))>r+eps)out.push('bottom-right');
  return out;
}

function effectiveCollisionRect(box,other,stageWin,framedStage) {
  const x0=box.x,y0=box.y,x1=x0+box.w,y1=y0+box.h;
  if(!framedStage||!stageWin)return [x0,y0,x1,y1];
  const bLayer=box.layer||(['hud','caption'].includes(box.zone)?'over':'content');
  const oLayer=other.layer||(['hud','caption'].includes(other.zone)?'over':'content');
  if(bLayer==='content'&&oLayer!=='content'){
    const wx0=stageWin.x,wy0=stageWin.y,wx1=wx0+stageWin.w,wy1=wy0+stageWin.h;
    const cx0=Math.max(x0,wx0),cy0=Math.max(y0,wy0),cx1=Math.min(x1,wx1),cy1=Math.min(y1,wy1);
    if(cx1<=cx0||cy1<=cy0)return null;
    return [cx0,cy0,cx1,cy1];
  }
  return [x0,y0,x1,y1];
}

export function auditLayout(boxes,{minOverlap=2,checkPlatformUi=false,stageWin=null}={}) {
  if(!Array.isArray(boxes))throw Error('Layout capture is missing');
  const issues=[];
  const validFlags=[];
  const hasStageWin=stageWin&&typeof stageWin==='object'&&['x','y','w','h'].every(k=>finite(stageWin[k]))&&stageWin.w>0&&stageWin.h>0;
  const framedStage=Boolean(hasStageWin&&!isStageFullscreen(stageWin));

  for(const b of boxes) {
    const ok=Boolean(b&&typeof b.id==='string'&&b.id.trim()&&['text','face','keep'].includes(b.kind)&&['x','y','w','h'].every(k=>finite(b[k]))&&b.w>0&&b.h>0);
    validFlags.push(ok);
    if(!ok) {
      issues.push({code:'L00',ids:[b?.id||'?'],message:'Invalid registered box'});continue;
    }
    if(b.kind!=='text') {
      if(b.layer==='over'&&b.chrome!==true){
        if(b.x<BRAND.safe.margin||b.x+b.w>BRAND.W-BRAND.safe.margin||b.y<0||b.y+b.h>BRAND.safe.belowIsDead)
          issues.push({code:'L01',ids:[b.id],message:'Foreground overlay escapes safe region'});
        if(checkPlatformUi){
          const rx=Math.min(b.x+b.w,PLATFORM_RIGHT_RAIL.x+PLATFORM_RIGHT_RAIL.w)-Math.max(b.x,PLATFORM_RIGHT_RAIL.x);
          const ry=Math.min(b.y+b.h,PLATFORM_RIGHT_RAIL.y+PLATFORM_RIGHT_RAIL.h)-Math.max(b.y,PLATFORM_RIGHT_RAIL.y);
          if(rx>=minOverlap&&ry>=minOverlap)
            issues.push({code:'L04',ids:[b.id],message:'Foreground overlay overlaps social right-rail UI zone (x940..1080 y1100..1500)'});
        }
      }
      continue;
    }
    const zone=b.zone||'content';
    const range=zone==='caption'?[BRAND.safe.contentY[1],BRAND.safe.belowIsDead]:zone==='hud'?[0,BRAND.safe.contentY[0]]:BRAND.safe.contentY;
    if(!['content','caption','hud'].includes(zone))issues.push({code:'L00',ids:[b.id],message:'Unknown text zone'});
    if(b.x<BRAND.safe.margin||b.x+b.w>BRAND.W-BRAND.safe.margin||b.y<range[0]||b.y+b.h>range[1])
      issues.push({code:'L01',ids:[b.id],message:`Ink outside ${zone} safe zone`});
    if(checkPlatformUi&&zone!=='hud') {
      const rx=Math.min(b.x+b.w,PLATFORM_RIGHT_RAIL.x+PLATFORM_RIGHT_RAIL.w)-Math.max(b.x,PLATFORM_RIGHT_RAIL.x);
      const ry=Math.min(b.y+b.h,PLATFORM_RIGHT_RAIL.y+PLATFORM_RIGHT_RAIL.h)-Math.max(b.y,PLATFORM_RIGHT_RAIL.y);
      if(rx>=minOverlap&&ry>=minOverlap)
        issues.push({code:'L04',ids:[b.id],message:'Ink overlaps social right-rail UI zone (x940..1080 y1100..1500)'});
    }
    const effLayer=b.layer||(['hud','caption'].includes(zone)?'over':'content');
    if(framedStage&&effLayer==='content') {
      const eps=0.5;
      if(b.x<stageWin.x-eps||b.y<stageWin.y-eps||b.x+b.w>stageWin.x+stageWin.w+eps||b.y+b.h>stageWin.y+stageWin.h+eps)
        issues.push({code:'L05',ids:[b.id],message:'Content ink extends outside Fixed Stage window win(t)'});
      const corners=windowCornerClips(b,stageWin,eps);
      if(corners.length)
        issues.push({code:'L06',ids:[b.id],message:`Ink clipped by Fixed Stage rounded corner (${corners.join(', ')})`});
    }
  }
  for(let i=0;i<boxes.length;i++) {
    if(!validFlags[i])continue;
    const a=boxes[i];
    if(a.chrome===true||a.layer==='under')continue;
    for(let j=i+1;j<boxes.length;j++) {
      if(!validFlags[j])continue;
      const b=boxes[j];
      if(b.chrome===true||b.layer==='under')continue;
      if(a.kind!=='text'&&b.kind!=='text')continue;
      const ra=effectiveCollisionRect(a,b,stageWin,framedStage);
      const rb=effectiveCollisionRect(b,a,stageWin,framedStage);
      if(!ra||!rb)continue;
      const ox=Math.min(ra[2],rb[2])-Math.max(ra[0],rb[0]),oy=Math.min(ra[3],rb[3])-Math.max(ra[1],rb[1]);
      if(ox>=minOverlap&&oy>=minOverlap)issues.push({code:a.kind==='face'||b.kind==='face'?'L03':'L02',ids:[a.id,b.id],message:'Overlapping protected ink/box'});
    }
  }
  return issues;
}
