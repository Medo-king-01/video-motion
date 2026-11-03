import React,{useState,useEffect} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {DirectedText} from './lib/DirectedText';
import {PALETTE as C} from './brand';
import {DIRECTION,frameAt} from './state-demo.js';
const Demo:React.FC=()=>{
  const t=useCurrentFrame()/30,state=frameAt(t),[handle]=useState(()=>delayRender('Cairo state fixture'));
  useEffect(()=>{document.fonts.load('800 32px Cairo').then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
  const text=(copy:string,id:string,left:number,top:number,width:number,size:number)=><DirectedText key={id}
    direction={DIRECTION} scene={1} role="label" elementId={id} time={t} start={0} end={2.4}
    size={size} color={C.ink} theme="light" style={{position:'absolute',left,top,width,fontSize:size,textAlign:'center'}}>{copy}</DirectedText>;
  const rows=[{id:'inertia',label:'قصور',y:1000,value:state.inertia.value},
    {id:'retarget',label:'هدف جديد',y:1130,value:state.retarget.value},{id:'follow',label:'تتبّع',y:1260,value:state.follow.value}];
  return <AbsoluteFill style={{background:C.paper}}>
    <style>{`@font-face{font-family:Cairo;font-weight:800;src:url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')}`}</style>
    {text('فيزياء وحالات ثابتة','title',90,245,900,58)}
    <div style={{position:'absolute',left:state.spring.value-100,top:450,width:200,height:120,boxSizing:'border-box',borderRadius:24,border:`3px solid ${C.red}`,background:C.gray1}}>
      {text('نابض','spring',0,30,194,44)}</div>
    {state.cards.map((card,i)=><div key={i} style={{position:'absolute',left:card.x,top:card.y,width:240,height:140,boxSizing:'border-box',borderRadius:24,border:`3px solid ${C.ink}`,background:C.gray1}}>
      {text(`حالة ${i+1}`,`card-${i}`,0,40,234,44)}</div>)}
    <svg width={1080} height={1920} style={{position:'absolute'}}>{rows.map(row=><g key={row.id}>
      <line x1={140} y1={row.y} x2={940} y2={row.y} stroke={C.inkSoft} strokeWidth={3}/><circle cx={row.value} cy={row.y} r={state.radius} fill={C.red}/></g>)}</svg>
    {rows.map(row=>text(row.label,row.id,90,row.y+28,900,42))}
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="MotionState" component={Demo} fps={30} durationInFrames={72} width={1080} height={1920}/>;
