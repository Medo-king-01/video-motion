// Synthetic verification compositions only: no production VO or factual claim.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {DataRecipe} from './lib/DataRecipe';
import {PALETTE} from './brand';
const direction={scenes:[{scene:1,textStyles:{label:'softfade',number:'softfade'},
  fontStyles:{label:{family:'Cairo',weight:800},number:{family:'Cairo',weight:800}}}]};
const Demo:React.FC<{kind:string}>=({kind})=>{
  const frame=useCurrentFrame(),[handle]=useState(()=>delayRender('Cairo fixture'));
  useEffect(()=>{document.fonts.load('800 32px Cairo').then(()=>continueRender(handle)).catch(cancelRender);},[handle]);
  const rows=kind==='comparison'?[{id:'a',label:'الخيار الأول',value:16},{id:'b',label:'الخيار التاني',value:32}]
    :kind==='timeline'?[{id:'a',label:'البداية',value:10,at:0},{id:'b',label:'المنتصف',value:20,at:1},{id:'c',label:'النهاية',value:32,at:2}]
    :[{id:'a',label:'سعة الذاكرة',value:32}];
  const spec={start:0,end:2,anchor:{text:'اتنين وتلاتين',start:.3,end:.8},
    data:{version:1,kind,source:'بيانات توضيحية — مش اختبار منتج',unit:'جيجابايت',locale:'ar-EG',decimals:0,rows}};
  return <AbsoluteFill style={{background:PALETTE.paper}}>
    <style>{`@font-face{font-family:Cairo;font-weight:800;src:url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')}`}</style>
    <DataRecipe spec={spec} time={frame/30} direction={direction} scene={1} x={140} y={450} width={800} height={500}/>
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><>{['comparison','timeline','counter'].map(kind=><Composition
  key={kind} id={`Data-${kind}`} component={Demo} durationInFrames={60} fps={30} width={1080} height={1920} defaultProps={{kind}}/>)}</>;
