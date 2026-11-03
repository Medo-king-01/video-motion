import React,{useState,useEffect} from 'react';
import {AbsoluteFill,Composition,useCurrentFrame,delayRender,continueRender,cancelRender,staticFile} from 'remotion';
import {DirectedText} from './lib/DirectedText';
import {GeometryBindings,BindingItem} from './lib/GeometryBindings';
import {measureTextFit} from './lib/text-measure.js';
import {PALETTE as C} from './brand';
import {DIRECTION,frameAt} from './geometry-demo.js';
type LayoutCard={id:string;opacity:number;phase:string;box:{x:number;y:number;w:number;h:number;r:number}};
const Demo:React.FC=()=>{
  const t=useCurrentFrame()/30,state=frameAt(t),[handle]=useState(()=>delayRender('Geometry measured Cairo'));
  const cards=state.cards as LayoutCard[];
  const [fit,setFit]=useState<ReturnType<typeof measureTextFit>|null>(null);
  useEffect(()=>{const face=new FontFace('Cairo',`url('${staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}')`,{weight:'800'});face.load().then(loaded=>{document.fonts.add(loaded);
    const ctx=document.createElement('canvas').getContext('2d');if(!ctx)throw Error('canvas measurement missing');
    const measured=measureTextFit(ctx,'قياس على الخط الحقيقي',{family:'Cairo',weight:800,minSize:32,maxSize:42,step:2,maxWidth:900,maxHeight:100,padding:12});
    if(!measured.fits)throw Error('font does not fit');setFit(measured);continueRender(handle);
  }).catch(cancelRender);},[handle]);
  const text=(copy:string,id:string,x:number,y:number,width:number,size:number)=><DirectedText key={id}
    direction={DIRECTION} scene={1} role="label" elementId={id} time={t} start={0} end={3} size={size} color={C.ink} theme="light"
    style={{position:'absolute',left:x-width/2,top:y-size*1.05,width,fontSize:size,textAlign:'center'}}>{copy}</DirectedText>;
  const measured:BindingItem[]=fit?[{id:'measured',kind:'rect',fill:'gray1',stroke:'ink',props:{x:(1080-fit.w)/2,y:1210,w:fit.w,h:fit.h,r:16,opacity:1,strokeWidth:3}}]:[];
  return <AbsoluteFill style={{background:C.paper}}>
    <GeometryBindings items={[...state.bindings as BindingItem[],...measured]}/>
    {text('عناصر بنفس الهوية','title',540,280,900,58)}
    {cards.filter(card=>card.phase==='hold'&&card.opacity===1).map(card=>text(`عنصر ${card.id.toUpperCase()}`,`card-${card.id}`,card.box.x+card.box.w/2,card.box.y+card.box.h/2,card.box.w,44))}
    {fit&&fit.lines.map((line,i)=>text(line.text,`fit-${i}`,(1080-fit.w)/2+line.x+line.w/2,1210+line.y+line.h/2,Math.max(1,line.w+6),fit.size!))}
  </AbsoluteFill>;
};
export const RemotionRoot:React.FC=()=><Composition id="MotionGeometry" component={Demo} fps={30} durationInFrames={90} width={1080} height={1920}/>;
