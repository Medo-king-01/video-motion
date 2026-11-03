import React,{useLayoutEffect,useRef} from 'react';
import {createSyncResourceScope} from './sync-resource-scope.js';

type Scope=ReturnType<typeof createSyncResourceScope>;
type Placement={x:number;y:number;w:number;h:number};
type Layer={draw:(ctx:CanvasRenderingContext2D,time:number,placement:Placement)=>void};
export type ThreeCanvasSetup=(scope:Scope)=>Layer;
export type ThreeCanvasProps={width:number;height:number;time:number;setup:ThreeCanvasSetup;x:number;y:number;w:number;h:number};

/** Explicit scene-local frame time. setup must be stable and register all owned assets. */
export const ThreeCanvas:React.FC<ThreeCanvasProps>=({width,height,time,setup,x,y,w,h})=>{
  if(!Number.isInteger(width)||!Number.isInteger(height)||width<2||height<2||width>4096||height>4096||width*height>4194304||
    ![time,x,y,w,h].every(Number.isFinite)||w<=0||h<=0||typeof setup!=='function')throw Error('invalid Three canvas settings');
  const ref=useRef<HTMLCanvasElement>(null);
  const current=useRef<{ctx:CanvasRenderingContext2D;layer:Layer}|null>(null);
  useLayoutEffect(()=>{
    const ctx=ref.current?.getContext('2d');if(!ctx)throw Error('2D context unavailable');
    const scope=createSyncResourceScope();
    try{
      const layer=setup(scope);
      if(!layer||typeof layer.draw!=='function')throw Error('Three setup must return a layer');
      current.current={ctx,layer};
    }catch(error){
      try{scope.close();}catch(cleanup){console.error('Three setup cleanup failed',cleanup);}
      throw error;
    }
    return ()=>{current.current=null;scope.close();};
  },[width,height,setup]);
  useLayoutEffect(()=>{
    const state=current.current;if(!state)throw Error('Three layer is not initialized');
    const {ctx,layer}=state;ctx.save();
    try{
      ctx.setTransform(1,0,0,1,0,0);ctx.globalAlpha=1;ctx.globalCompositeOperation='source-over';
      ctx.clearRect(0,0,width,height);layer.draw(ctx,time,{x:0,y:0,w:width,h:height});
    }finally{ctx.restore();}
  },[time,width,height,setup]);
  return <canvas ref={ref} width={width} height={height} style={{position:'absolute',left:x,top:y,width:w,height:h,pointerEvents:'none'}}/>;
};
