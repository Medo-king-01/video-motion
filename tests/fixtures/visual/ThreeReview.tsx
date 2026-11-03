import React from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,useVideoConfig} from 'remotion';
import {ThreeCanvas,ThreeCanvasSetup} from './lib/ThreeCanvas';
import {makeThreeScene} from './three-r-scene.js';
type Props={motionMode:'normal'|'reduced'};
const normal:ThreeCanvasSetup=scope=>makeThreeScene(scope,false);
const reduced:ThreeCanvasSetup=scope=>makeThreeScene(scope,true);
const Demo:React.FC<Props>=({motionMode})=>{
  const frame=useCurrentFrame(),{fps}=useVideoConfig();
  return <AbsoluteFill style={{background:'#030303',color:'#F3F2F1'}}>
    <div style={{position:'absolute',top:345,left:0,width:1080,textAlign:'center',fontSize:64}}>3D render test</div>
    <ThreeCanvas width={512} height={512} x={180} y={560} w={720} h={720} time={frame/fps} setup={motionMode==='reduced'?reduced:normal}/>
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="ThreeReview" component={Demo} fps={30} durationInFrames={30} width={1080} height={1920} defaultProps={{motionMode:'normal'}}/>;
