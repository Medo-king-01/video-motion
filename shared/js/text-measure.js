// Measure once after explicit font load; save the returned plan, never measure during frame sampling.
import {fitMeasuredText} from './motion-geometry.js';
export function measureTextFit(ctx,text,options){
  const {family,weight,minSize,maxSize,step=1,maxWidth,maxHeight,padding=0,lineHeight=1.3,rtl=true}=options;
  if(![minSize,maxSize,step].every(Number.isInteger)||minSize<1||maxSize>512||maxSize<minSize||step<1||typeof rtl!=='boolean')throw Error('invalid font size search');
  if(typeof family!=='string'||!Number.isInteger(weight)||weight<100||weight>900||typeof text!=='string'||!text.trim())throw Error('explicit text/font required');
  const loaded=typeof document!=='undefined'&&[...document.fonts].some(f=>{
    const weights=f.weight.split(/\s+/).map(Number),matches=weights.length===1?weights[0]===weight:weights[0]<=weight&&weight<=weights[1];
    return f.family.replace(/["']/g,'')===family&&f.status==='loaded'&&matches;
  });
  if(!loaded)throw Error('requested font face/weight is not loaded; no fallback measurement');
  const candidates=[];ctx.save();
  try{
    ctx.direction=rtl?'rtl':'ltr';ctx.textAlign='left';ctx.textBaseline='alphabetic';
    for(let size=maxSize;size>=minSize;size-=step){
      ctx.font=`${weight} ${size}px "${family}"`;const lines=[];let line='';
      const metrics=s=>{const m=ctx.measureText(s);return {text:s,w:Math.max(m.width,m.actualBoundingBoxLeft+m.actualBoundingBoxRight),h:Math.max(1,m.actualBoundingBoxAscent+m.actualBoundingBoxDescent)};};
      for(const word of text.trim().split(/\s+/)){
        const next=line?`${line} ${word}`:word;
        if(line&&metrics(next).w>maxWidth-2*padding){lines.push(metrics(line));line=word;}else line=next;
      }
      if(line)lines.push(metrics(line));candidates.push({size,measuredBy:'canvas',lines});
    }
  }finally{ctx.restore();}
  return fitMeasuredText({text,font:{family,weight},maxWidth,maxHeight,padding,lineHeight,candidates});
}
