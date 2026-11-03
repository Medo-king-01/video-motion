import React from 'react';
import {recipeAt} from './data-recipes.js';
import {DirectedText} from './DirectedText';
import {PALETTE} from '../brand';

/** Same pure data/time model as K; deliberately not an independent chart timer. */
export const DataRecipe: React.FC<{
  spec: Parameters<typeof recipeAt>[0]; time: number; direction: any; scene: number;
  id?: string; x?: number; y?: number; width?: number; height?: number;
}> = ({spec,time,direction,scene,id='data',x=140,y=400,width=800,height=600}) => {
  const state=recipeAt(spec,time);if(!state.active)return null;
  const label=(text:string,key:string,role:string,left:number,top:number,size=38,boxWidth=width/2)=>(
    <DirectedText key={key} direction={direction} scene={scene} role={role} elementId={`${id}.${key}`}
      time={time} start={spec.start} end={spec.end} size={size} color={PALETTE.ink} theme="light"
      style={{position:'absolute',left,top,width:boxWidth,textAlign:'center',fontSize:size}}>{text}</DirectedText>
  );
  const labels=[label(state.unit,'unit','label',width/4,-80),label(state.source,'source','label',0,height+50,28,width)];
  const shapes: React.ReactNode[]=[];
  if(state.visible){
    if(state.kind==='comparison')state.rows.forEach((r,i)=>{
      const step=height/state.rows.length;
      shapes.push(<rect key={r.id} x={0} y={i*step+18} width={width*r.fraction} height={step*.3} fill={PALETTE.red}/>);
      labels.push(label(r.label,`${r.id}.label`,'label',0,(i+.6)*step,32),label(r.display,`${r.id}.value`,'number',width/2,(i+.6)*step));
    });
    else if(state.kind==='counter')labels.push(label(state.rows[0].display,'value','number',width/4,height*.25,110),label(state.rows[0].label,'label','label',width/4,height*.7,42));
    else{
      shapes.push(<polyline key="line" points={state.points.map(p=>`${p.x*width},${p.y*height}`).join(' ')} fill="none" stroke={PALETTE.red} strokeWidth={6}/>);
      labels.push(label(state.rows[0].label,'first','label',0,height+10,28),label(state.rows.at(-1)!.label,'last','label',width/2,height+10,28));
      if(state.progress===1)labels.push(label(state.rows.at(-1)!.display,'value','number',width/4,25,50));
    }
  }
  return <div style={{position:'absolute',left:x,top:y,width,height}}>
    <svg width={width} height={height} style={{position:'absolute',overflow:'visible'}}>
      {state.kind!=='counter'&&<path d={`M0 0 V${height} H${width}`} fill="none" stroke={PALETTE.inkSoft} strokeWidth={3}/>}{shapes}
    </svg>{labels}
  </div>;
};
