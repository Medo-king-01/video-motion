import React,{useState,useEffect} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {SharedPanel} from './lib/SharedPanel';
import {DirectedText} from './lib/DirectedText';
import {PALETTE} from './brand';
import {SPEC,DIRECTION} from './shared-demo.js';
const Demo:React.FC=()=>{
  const t=useCurrentFrame()/30,[handle]=useState(()=>delayRender('Cairo shared-element fixture'));
  useEffect(()=>{document.fonts.load('800 32px Cairo').then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
  const text=(copy:string,id:string,role:string,top:number,size:number,start=0)=><DirectedText
    direction={DIRECTION} scene={1} role={role} elementId={`detail.${id}`} time={t}
    start={start} end={SPEC.end} size={size} color={PALETTE.ink} theme="light"
    style={{position:'absolute',top,left:0,width:'100%',textAlign:'center',fontSize:size}}>{copy}</DirectedText>;
  return <AbsoluteFill style={{background:PALETTE.paper}}>
    <style>{`@font-face{font-family:Cairo;font-weight:800;src:url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')}`}</style>
    <SharedPanel spec={SPEC} time={t} label={()=>text('تفاصيل','title','label',25,48)}>
      {()=> <><div style={{position:'absolute',top:115,left:40,right:40,borderTop:`3px solid ${PALETTE.inkSoft}`}}/>
        {text('مساحة للشرح','body','body',275,72,SPEC.contentAt)}</>}
    </SharedPanel>
    {text('مثال توضيحي','notice','label',1230,42)}
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="SharedDetail" component={Demo}
  fps={30} durationInFrames={54} width={1080} height={1920}/>;
