import {svgPlacement,svgStrokeWindows} from './svg-art.js';
import {strokeSegments} from './motion-geometry.js';
import {PALETTE} from './brand.js';
export function drawSvgArt(ctx,plan,options){
  const {scale,x,y}=svgPlacement(plan,options);const {base,windows}=svgStrokeWindows(plan,options);
  const paint=(target,s)=>{
    target.lineWidth=s.strokeWidth;
    if(s.fill!==null){
      if(typeof s.fill==='string')target.fillStyle=PALETTE[s.fill];
      else{const g=s.fill,gradient=g.type==='linear'?target.createLinearGradient(g.x1,g.y1,g.x2,g.y2):target.createRadialGradient(g.cx,g.cy,0,g.cx,g.cy,g.r);for(const stop of g.stops)gradient.addColorStop(stop.offset,PALETTE[stop.color]);target.fillStyle=gradient;}
      target.beginPath();for(const c of s.contours){c.points.forEach((p,i)=>i?target.lineTo(p.x,p.y):target.moveTo(p.x,p.y));target.closePath();}target.fill('evenodd');
    }
    if(s.stroke!==null&&s.strokeWidth>0){target.strokeStyle=PALETTE[s.stroke];for(const [ci,c] of s.contours.entries())for(const part of strokeSegments(c.points,{closed:c.closed,...(windows.get(s.id)?.[ci]??base)})){target.beginPath();part.forEach((p,i)=>i?target.lineTo(p.x,p.y):target.moveTo(p.x,p.y));target.stroke();}}
  };
  ctx.save();try{
    ctx.translate(x,y);ctx.scale(scale,scale);ctx.lineCap='round';ctx.lineJoin='round';
    let buffer,layer,transform;
    if(plan.shapes.some(s=>s.opacity>0&&s.opacity<1)){
      const c=ctx.canvas;transform=ctx.getTransform?.();
      if(ctx.globalCompositeOperation!=='source-over'||ctx.filter!=='none'||ctx.shadowColor!=='rgba(0, 0, 0, 0)')throw Error('SVG opacity requires source-over without canvas filter or shadow');
      if(!c||!Number.isInteger(c.width)||!Number.isInteger(c.height)||c.width<1||c.height<1||c.width*c.height>4194304||!transform?.is2D||![transform.a,transform.b,transform.c,transform.d,transform.e,transform.f].every(Number.isFinite))throw Error('SVG opacity requires bounded canvas and finite 2D transform');
      buffer=document.createElement('canvas');buffer.width=c.width;buffer.height=c.height;
      layer=buffer.getContext('2d');if(!layer)throw Error('SVG opacity canvas unavailable');
      layer.lineCap='round';layer.lineJoin='round';
    }
    for(const s of plan.shapes){
      if(s.opacity===0)continue;
      if(s.opacity===1){ctx.save();try{paint(ctx,s);}finally{ctx.restore();}continue;}
      layer.setTransform(1,0,0,1,0,0);layer.clearRect(0,0,buffer.width,buffer.height);
      layer.setTransform(transform);paint(layer,s);
      ctx.save();try{ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha*=s.opacity;ctx.drawImage(buffer,0,0);}finally{ctx.restore();}
    }
  }finally{ctx.restore();}
}

/** Group-opacity crossfade between two unrelated SVG plans. This is not geometry morphing. */
export function drawSvgCrossfade(ctx,from,to,amount,placement){
  if(typeof amount!=='number'||!Number.isFinite(amount)||amount<0||amount>1)throw Error('invalid SVG crossfade amount');
  if(!placement||typeof placement!=='object'||Array.isArray(placement)||Object.keys(placement).some(k=>!['x','y','width','height'].includes(k)))throw Error('invalid SVG crossfade placement');
  svgPlacement(from,placement);svgPlacement(to,placement);
  const canvas=ctx?.canvas,transform=ctx?.getTransform?.();
  if(!canvas||!Number.isInteger(canvas.width)||!Number.isInteger(canvas.height)||canvas.width<1||canvas.height<1||canvas.width*canvas.height>4194304||!transform?.is2D||![transform.a,transform.b,transform.c,transform.d,transform.e,transform.f].every(v=>Number.isFinite(v)&&Math.abs(v)<=1000000)||ctx.globalCompositeOperation!=='source-over')throw Error('SVG crossfade requires bounded canvas, finite 2D transform and source-over');
  const buffer=document.createElement('canvas');buffer.width=canvas.width;buffer.height=canvas.height;
  const layer=buffer.getContext('2d');if(!layer)throw Error('SVG crossfade canvas unavailable');
  ctx.save();try{
    ctx.setTransform(1,0,0,1,0,0);
    for(const [plan,alpha] of [[from,1-amount],[to,amount]]){
      if(alpha===0)continue;
      layer.setTransform(1,0,0,1,0,0);layer.clearRect(0,0,buffer.width,buffer.height);layer.setTransform(transform);drawSvgArt(layer,plan,placement);
      ctx.save();try{ctx.globalAlpha*=alpha;ctx.drawImage(buffer,0,0);}finally{ctx.restore();}
    }
  }finally{ctx.restore();}
}
