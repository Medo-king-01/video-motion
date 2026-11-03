import React,{useState,useEffect} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {DirectedText} from './lib/DirectedText';
import {PALETTE as C} from './brand';
import {DIRECTION,frameAt} from './plan-demo.js';
const Demo:React.FC=()=>{
  const t=useCurrentFrame()/30,state=frameAt(t),[handle]=useState(()=>delayRender('Cairo motion-plan fixture'));
  useEffect(()=>{document.fonts.load('800 32px Cairo').then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
  const text=(copy:string,id:string,left:number,top:number,width:number,size:number,start=0)=><DirectedText
    key={id} direction={DIRECTION} scene={1} role="label" elementId={id} time={t} start={start} end={1.8}
    size={size} color={C.ink} theme="light" style={{position:'absolute',left,top,width,fontSize:size,textAlign:'center'}}>{copy}</DirectedText>;
  return <AbsoluteFill style={{background:C.paper}}>
    <style>{`@font-face{font-family:Cairo;font-weight:800;src:url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')}`}</style>
    {state.presence.active&&text('حركة بتوقيت واضح','title',90,245,900,58)}
    {state.cards.map((card,i)=>t<card.start?null:<div key={i} style={{position:'absolute',left:card.x,top:card.y,width:240,height:160,
      boxSizing:'border-box',borderRadius:24,background:C.gray1,border:`3px solid ${C.ink}`}}>{text(`عنصر ${i+1}`,`card-${i}`,0,50,234,44,card.start)}</div>)}
    <svg width={1080} height={1920} style={{position:'absolute'}}><path d="M180 1000 Q540 640 900 1000" fill="none" stroke={C.inkSoft} strokeWidth={3}/>
      <circle cx={state.point.x} cy={state.point.y} r={18*state.scale} fill={C.red}/></svg>
    {text('معاينة اختبارية','notice',90,1230,900,42)}
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="MotionPlan" component={Demo} fps={30} durationInFrames={54} width={1080} height={1920}/>;
