// Original studio geometry: one identity, one shell, frame-driven move then hold.
// Visual direction/VO timing is authored outside this primitive. No fixed-duration loop.
import {ease, progress} from './motion.js';
const finite = n => typeof n === 'number' && Number.isFinite(n);
/** @typedef {{x:number,y:number,w:number,h:number,r:number}} PanelBox */
/** @typedef {{id:string,start:number,arrive:number,contentAt:number,end:number,from:PanelBox,to:PanelBox}} SharedSpec */
/** @param {SharedSpec} spec */
export function validateSharedElement(spec) {
  const errors=[];
  if(!spec || typeof spec.id!=='string' || !spec.id.trim())errors.push('shared element needs a stable id');
  if(!['start','arrive','contentAt','end'].every(k=>finite(spec?.[k])) ||
    !(spec.start>=0 && spec.start<spec.arrive && spec.arrive<=spec.contentAt && spec.contentAt<spec.end))
    errors.push('require scene-local 0 <= start < arrive <= contentAt < end');
  for(const key of ['from','to']) {
    const b=spec?.[key];
    if(!b || !['x','y','w','h','r'].every(k=>finite(b[k])) || b.w<=0 || b.h<=0 || b.r<0 || b.r>Math.min(b.w,b.h)/2)
      errors.push(`${key} needs finite x/y/w/h/r, positive size and a radius fitting its box`);
  }
  return errors;
}
/** @param {SharedSpec} spec @param {number} time */
export function sharedElementAt(spec,time) {
  const errors=validateSharedElement(spec);
  if(errors.length)throw Error(errors.join('; '));
  if(!finite(time))throw Error('time must be finite');
  const p=ease('cubicInOut',progress(time,spec.start,spec.arrive-spec.start));
  // Return endpoints verbatim: exact holds, not residual float drift or a loop reset.
  const mix=(a,b)=>a*(1-p)+b*p; // convex form avoids overflow of b-a
  const box=p===0?{...spec.from}:p===1?{...spec.to}:{
    x:mix(spec.from.x,spec.to.x),y:mix(spec.from.y,spec.to.y),
    w:mix(spec.from.w,spec.to.w),h:mix(spec.from.h,spec.to.h),r:mix(spec.from.r,spec.to.r),
  };
  const active=time>=spec.start && time<spec.end;
  return {id:spec.id,active,progress:p,box,contentsReady:active && time>=spec.contentAt};
}
