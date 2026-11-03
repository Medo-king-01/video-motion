// Synthetic frame gate: times stand in for anchors, not a real VO or production facts.
import React,{useEffect,useState} from 'react';
import {AbsoluteFill,Composition,continueRender,delayRender,cancelRender,staticFile,useCurrentFrame,useVideoConfig} from 'remotion';
import {DirectedText} from './lib/DirectedText';
import {ThreeCanvas,ThreeCanvasSetup} from './lib/ThreeCanvas';
import {makeThreeScene} from './three-r-scene.js';
type Props={motionMode:'normal'|'reduced'};
const normal:ThreeCanvasSetup=scope=>makeThreeScene(scope,false);
const reduced:ThreeCanvasSetup=scope=>makeThreeScene(scope,true);
const DIRECTION={scenes:[{scene:1,textStyles:{label:'softfade'},fontStyles:{label:{family:'Cairo',weight:800}}}]};
const Demo:React.FC<Props>=({motionMode})=>{
  const frame=useCurrentFrame(),{fps}=useVideoConfig(),time=frame/fps;
  const [handle]=useState(()=>delayRender('Load Cairo for synthetic Arabic gate'));
  useEffect(()=>{new FontFace('Cairo',`url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`,{weight:'800'}).load()
    .then(face=>{document.fonts.add(face);continueRender(handle);}).catch(cancelRender);},[handle]);
  return <AbsoluteFill style={{background:'#030303',color:'#F3F2F1'}}>
    <ThreeCanvas width={512} height={512} x={180} y={560} w={720} h={720} time={time} setup={motionMode==='reduced'?reduced:normal}/>
    {frame>=15&&<DirectedText direction={DIRECTION} scene={1} role="label" elementId="synthetic-fact"
      time={time} start={.5} end={1} size={72} color="#F3F2F1"
      style={{position:'absolute',left:90,top:1390,width:900,fontSize:72,textAlign:'center'}}>
      {'حقيقة تجريبية'}
    </DirectedText>}
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="ThreeArabicGate" component={Demo} fps={30} durationInFrames={30} width={1080} height={1920} defaultProps={{motionMode:'normal'}}/>;
