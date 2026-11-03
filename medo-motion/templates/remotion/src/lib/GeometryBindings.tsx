import React from 'react';
import {PALETTE} from '../brand';
import {strokeSegments} from './motion-geometry.js';

type Point={x:number;y:number};
type Paint={opacity:number;strokeWidth:number};
type Token='red'|'redBright'|'redDeep'|'ink'|'inkSoft'|'paper'|'gray1'|'gray2'|'gray3'|'gray4'|'salmon'|'blush';
type Identity={id:string;fill:Token|null;stroke:Token|null};
export type BindingItem=Identity&(
  {kind:'rect';props:Paint&{x:number;y:number;w:number;h:number;r:number}}|
  {kind:'circle';props:Paint&{x:number;y:number;r:number}}|
  {kind:'path';props:Paint&{points:Point[];closed:boolean;start:number;end:number;offset:number}}
);
/** No CSS timers/layout reads. Parent supplies already-validated compileBindings output. */
export const GeometryBindings:React.FC<{items:readonly BindingItem[];width?:number;height?:number}>=({items,width=1080,height=1920})=>
  <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{position:'absolute',inset:0}}>
    {items.map(item=>{
      const color=(token:Token|null)=>token===null?'none':PALETTE[token];
      const paint={fill:color(item.fill),stroke:color(item.stroke),strokeWidth:item.props.strokeWidth,vectorEffect:'non-scaling-stroke' as const};
      if(item.kind==='rect'){const p=item.props;return <rect key={item.id} data-layout-id={item.id} opacity={p.opacity} x={p.x} y={p.y} width={p.w} height={p.h} rx={p.r} {...paint}/>;}
      if(item.kind==='circle'){const p=item.props;return <circle key={item.id} data-layout-id={item.id} opacity={p.opacity} cx={p.x} cy={p.y} r={p.r} {...paint}/>;}
      const p=item.props,points=(list:Point[])=>list.map(v=>`${v.x},${v.y}`).join(' ');
      return <g key={item.id} data-layout-id={item.id} opacity={p.opacity}>
        {item.fill!==null&&<polygon points={points(p.points)} fill={color(item.fill)}/>}
        {item.stroke!==null&&p.strokeWidth>0&&strokeSegments(p.points,p).map((segment:Point[],i:number)=><polyline key={i} points={points(segment)} fill="none" stroke={color(item.stroke)} strokeWidth={p.strokeWidth} strokeLinecap="round" strokeLinejoin="round" vectorEffect="non-scaling-stroke"/>)}
      </g>;
    })}
  </svg>;
