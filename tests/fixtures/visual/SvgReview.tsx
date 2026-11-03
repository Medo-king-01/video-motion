import React,{useEffect,useState} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {SvgArt,SvgPlan} from './lib/SvgArt';
import {DirectedText} from './lib/DirectedText';
import {compileMotionPolicy} from './lib/render-policy.js';
import {PLAN} from './svg-proof.js';
import {PALETTE} from './brand';
const direction={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const policy=compileMotionPolicy({version:1,reduced:true,decorative:[{track:'stroke',value:1}]});
const Scene:React.FC=()=>{
  const t=useCurrentFrame()/30,[handle]=useState(()=>delayRender('Cairo'));
  useEffect(()=>{new FontFace('Cairo',`url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`,{weight:'800'}).load().then(face=>{document.fonts.add(face);continueRender(handle);}).catch(cancelRender);},[handle]);
  return <AbsoluteFill style={{background:PALETTE.paper}}>
    <SvgArt plan={PLAN as SvgPlan} x={80} y={650} width={430} height={430} progress={Math.min(1,t/1.5)}/>
    <SvgArt plan={PLAN as SvgPlan} x={570} y={650} width={430} height={430} progress={policy.at({stroke:Math.min(1,t/1.5)}).stroke}/>
    <DirectedText direction={direction} scene={1} role="label" elementId="title" time={t} start={0} end={2} size={56} color={PALETTE.ink} theme="light" style={{position:'absolute',top:300-56*1.05,left:90,width:900,fontSize:56,textAlign:'center'}}>رسم ثابت ومسارات آمنة</DirectedText>
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="SvgProof" component={Scene} fps={30} durationInFrames={60} width={1080} height={1920}/>;
