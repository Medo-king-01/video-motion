// Real React mount/update/unmount harness; not a production scene.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {flushSync} from 'react-dom';
import {ThreeCanvas,ThreeCanvasSetup} from './lib/ThreeCanvas';
import {useScopedEffect} from './lib/useScopedEffect';
import {makeThreeScene} from './three-r-scene.js';
let cleanups=0;
const makeSetup=(reduced:boolean):ThreeCanvasSetup=>scope=>makeThreeScene({defer(fn:()=>void){scope.defer(()=>{fn();cleanups++;});}},reduced);
const normal=makeSetup(false),reduced=makeSetup(true);
const root=createRoot(document.getElementById('root')!);
(window as any).renderProbe=async(t:number,reduce=false)=>{
  flushSync(()=>root.render(<ThreeCanvas width={512} height={512} x={0} y={0} w={512} h={512} time={t} setup={reduce?reduced:normal}/>));
  const canvas=document.querySelector('canvas')!;
  const pixels=canvas.getContext('2d')!.getImageData(0,0,canvas.width,canvas.height).data;
  const hash=await crypto.subtle.digest('SHA-256',pixels);
  return Array.from(new Uint8Array(hash),v=>v.toString(16).padStart(2,'0')).join('');
};
(window as any).closeProbe=()=>{flushSync(()=>root.unmount());return cleanups;};
(window as any).failureProbe=()=>{
  let attempts=0,disposed=0;
  const holder=document.createElement('div');document.body.appendChild(holder);
  const failureRoot=createRoot(holder);
  class Boundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
    state={failed:false};static getDerivedStateFromError(){return {failed:true};}
    render(){return this.state.failed?<span id="caught">failed as expected</span>:this.props.children;}
  }
  const bad:ThreeCanvasSetup=scope=>{
    attempts++;
    makeThreeScene({defer(fn:()=>void){scope.defer(()=>{fn();disposed++;});}},false);
    throw Error('synthetic setup failure after creating a Three scene');
  };
  flushSync(()=>failureRoot.render(<Boundary><ThreeCanvas width={2} height={2} x={0} y={0} w={2} h={2} time={0} setup={bad}/></Boundary>));
  const caught=Boolean(holder.querySelector('#caught'));flushSync(()=>failureRoot.unmount());holder.remove();
  return {attempts,disposed,caught};
};

(window as any).scopedEffectProbe=()=>{
  const holder=document.createElement('div');document.body.appendChild(holder);
  const effectRoot=createRoot(holder),events:string[]=[];
  const Probe:React.FC<{id:string}>=({id})=>{
    useScopedEffect(scope=>{events.push(`init-${id}`);scope.defer(()=>{events.push(`first-${id}`);});scope.defer(()=>{events.push(`last-${id}`);});},[id]);
    return <span>{id}</span>;
  };
  flushSync(()=>effectRoot.render(<Probe id="a"/>));
  flushSync(()=>effectRoot.render(<Probe id="b"/>));
  flushSync(()=>effectRoot.unmount());holder.remove();return events;
};
(window as any).scopedFailureProbe=()=>{
  const result:{kind:string;attempts:number;disposed:number;caught:boolean}[]=[];
  for(const kind of ['sync','async']){
    let attempts=0,disposed=0;const holder=document.createElement('div');document.body.appendChild(holder);
    const failRoot=createRoot(holder);
    class Boundary extends React.Component<{children:React.ReactNode},{failed:boolean}>{
      state={failed:false};static getDerivedStateFromError(){return {failed:true};}
      render(){return this.state.failed?<span className="caught">caught</span>:this.props.children;}
    }
    const Probe:React.FC=()=>{
      useScopedEffect(scope=>{
        attempts++;scope.defer(()=>{disposed++;});
        if(kind==='sync')throw Error('synthetic setup error');
        return Promise.resolve() as unknown as void;
      },[]);
      return <span/>;
    };
    flushSync(()=>failRoot.render(<Boundary><Probe/></Boundary>));
    const caught=Boolean(holder.querySelector('.caught'));flushSync(()=>failRoot.unmount());holder.remove();
    result.push({kind,attempts,disposed,caught});
  }
  return result;
};
