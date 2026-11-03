import {strokeSegments} from './motion-geometry.js';
import {PALETTE} from './brand.js';
/** Consume validated compileBindings output; native pixel geometry avoids scaling text/strokes. */
export function drawGeometry(ctx,items){
  for(const item of items){
    const p=item.props;if(p.opacity===0)continue;ctx.save();
    try{
      ctx.globalAlpha*=p.opacity;ctx.lineWidth=p.strokeWidth;ctx.lineCap='round';ctx.lineJoin='round';
      if(item.fill!==null)ctx.fillStyle=PALETTE[item.fill];if(item.stroke!==null)ctx.strokeStyle=PALETTE[item.stroke];
      if(item.kind==='rect'||item.kind==='circle'){
        ctx.beginPath();if(item.kind==='rect')ctx.roundRect(p.x,p.y,p.w,p.h,p.r);else ctx.arc(p.x,p.y,p.r,0,Math.PI*2);
        if(item.fill!==null)ctx.fill();if(item.stroke!==null&&p.strokeWidth>0)ctx.stroke();
      }else{
        if(item.fill!==null){ctx.beginPath();p.points.forEach((point,i)=>i?ctx.lineTo(point.x,point.y):ctx.moveTo(point.x,point.y));ctx.closePath();ctx.fill();}
        if(item.stroke!==null&&p.strokeWidth>0)for(const points of strokeSegments(p.points,p)){
          ctx.beginPath();points.forEach((point,i)=>i?ctx.lineTo(point.x,point.y):ctx.moveTo(point.x,point.y));ctx.stroke();
        }
      }
    }finally{ctx.restore();}
  }
}
