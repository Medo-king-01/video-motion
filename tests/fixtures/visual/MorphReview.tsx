import React,{useEffect,useState} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {SvgArt,SvgPlan} from './lib/SvgArt';
import {DirectedText} from './lib/DirectedText';
import {DIRECTION,frameAt} from './morph-demo.js';
import {PALETTE} from './brand';
const Scene:React.FC=()=>{
  const t=useCurrentFrame()/30,[handle]=useState(()=>delayRender('Cairo'));
  useEffect(()=>{new FontFace('Cairo',`url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`,{weight:'800'}).load().then(face=>{document.fonts.add(face);continueRender(handle);}).catch(cancelRender);},[handle]);
  const state=frameAt(t);
  return <AbsoluteFill style={{background:PALETTE.paper}}>
    <SvgArt plan={state.art as SvgPlan} x={190} y={550} width={700} height={700}/>
    <div style={{position:'absolute',left:340,top:1370,width:400,height:8,background:PALETTE.ink}}/>
    <div style={{position:'absolute',left:340,top:1370,width:400*state.values['group/accent'],height:8,background:PALETTE.red}}/>
    <DirectedText direction={DIRECTION} scene={1} role="label" elementId="title" time={t} start={0} end={2.4} size={58} color={PALETTE.ink} theme="light" style={{position:'absolute',top:280-58*1.05,left:90,width:900,fontSize:58,textAlign:'center'}}>تحول يحافظ على الفتحة</DirectedText>
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="SvgMorphProof" component={Scene} fps={30} durationInFrames={72} width={1080} height={1920}/>;
