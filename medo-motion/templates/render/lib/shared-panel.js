// Canvas adapter. Callbacks draw directed, whole-word text; the shell is drawn once.
import {sharedElementAt} from './shared-element.js';
import {PALETTE} from './brand.js';
export function drawSharedPanel(ctx,spec,time,{drawLabel,drawContent}={}) {
  const state=sharedElementAt(spec,time);
  if(!state.active)return state;
  const {x,y,w,h,r}=state.box;
  ctx.save();
  try {
    ctx.fillStyle=PALETTE.gray1;ctx.strokeStyle=PALETTE.ink;ctx.lineWidth=3;
    ctx.beginPath();ctx.roundRect(x,y,w,h,r);ctx.fill();ctx.stroke();
    // Each callback runs at most once. No scaling/letter splitting of the text.
    drawLabel?.(ctx,state);
    if(state.contentsReady)drawContent?.(ctx,state);
  }finally{ctx.restore();}
  return state;
}
