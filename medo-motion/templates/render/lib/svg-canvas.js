import {svgPlacement} from './svg-art.js';
import {strokeSegments} from './motion-geometry.js';
import {PALETTE} from './brand.js';
const finite=x=>typeof x==='number'&&Number.isFinite(x)&&Math.abs(x)<=1000000;
export function drawSvgArt(ctx,plan,options){
  const {scale,x,y}=svgPlacement(plan,options);const progress=options?.progress??1;
  if(!finite(progress)||progress<0||progress>1)throw Error('SVG stroke progress must be 0..1');
  ctx.save();try{
    ctx.translate(x,y);ctx.scale(scale,scale);ctx.lineCap='round';ctx.lineJoin='round';
    for(const s of plan.shapes){
      ctx.save();try{ctx.globalAlpha*=s.opacity;ctx.lineWidth=s.strokeWidth;
        if(s.fill!==null){ctx.fillStyle=PALETTE[s.fill];ctx.beginPath();for(const c of s.contours){c.points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();}ctx.fill('evenodd');}
        if(s.stroke!==null&&s.strokeWidth>0){ctx.strokeStyle=PALETTE[s.stroke];for(const c of s.contours)for(const part of strokeSegments(c.points,{closed:c.closed,end:progress})){ctx.beginPath();part.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.stroke();}}
      }finally{ctx.restore();}
    }
  }finally{ctx.restore();}
}
