import React from 'react';
import {PALETTE} from '../brand';
import {svgPlacement,svgStrokeWindows} from './svg-art.js';
import {strokeSegments} from './motion-geometry.js';

type Token=keyof typeof PALETTE;
type Point={x:number;y:number};
type Contour={points:Point[];closed:boolean};
export type LinearFill={type:'linear';x1:number;y1:number;x2:number;y2:number;stops:{offset:number;color:Token}[]};
export type RadialFill={type:'radial';cx:number;cy:number;r:number;stops:{offset:number;color:Token}[]};
export type SvgPlan={version:1;viewBox:[number,number,number,number];shapes:{id:string;fill:Token|LinearFill|RadialFill|null;stroke:Token|null;strokeWidth:number;opacity:number;contours:Contour[]}[]};
export type StrokeWindow={start:number;end:number;offset?:number};
/** A bounded precompiled SVG plan. Use an explicit frame-derived progress; never insert SVG markup. */
export const SvgArt:React.FC<{plan:SvgPlan;x:number;y:number;width:number;height:number;progress?:number;strokeStart?:number;strokeOffset?:number;strokeWindows?:Record<string,(StrokeWindow|null)[]>}>=({plan,x,y,width,height,...strokeOptions})=>{
  const instanceId=React.useId().replace(/[^A-Za-z0-9_-]/g,'');
  const place=svgPlacement(plan,{x,y,width,height});
  const {base,windows}=svgStrokeWindows(plan,strokeOptions);
  const path=(contours:Contour[])=>contours.map(c=>c.points.map((p,i)=>`${i?'L':'M'}${p.x} ${p.y}`).join(' ')+' Z').join(' ');
  return <svg width="100%" height="100%" style={{position:'absolute',inset:0,overflow:'visible',pointerEvents:'none'}}>
    <defs>{plan.shapes.map((shape,i)=>{
      const fill=shape.fill;if(!fill||typeof fill==='string')return null;
      const id=`svg-gradient-${instanceId}-${i}`,stops=fill.stops.map((stop,j)=><stop key={j} offset={stop.offset} stopColor={PALETTE[stop.color]}/>);
      return fill.type==='linear'?<linearGradient key={i} id={id} gradientUnits="userSpaceOnUse" x1={fill.x1} y1={fill.y1} x2={fill.x2} y2={fill.y2}>{stops}</linearGradient>:
        <radialGradient key={i} id={id} gradientUnits="userSpaceOnUse" cx={fill.cx} cy={fill.cy} r={fill.r}>{stops}</radialGradient>;
    })}</defs>
    <g transform={`translate(${place.x} ${place.y}) scale(${place.scale})`}>
      {plan.shapes.map((s,si)=><g key={s.id} opacity={s.opacity}>
        {s.fill!==null&&<path d={path(s.contours)} fill={typeof s.fill==='string'?PALETTE[s.fill]:`url(#svg-gradient-${instanceId}-${si})`} fillRule="evenodd"/>}
        {s.stroke!==null&&s.strokeWidth>0&&s.contours.flatMap((c,ci)=>strokeSegments(c.points,{closed:c.closed,...(windows.get(s.id)?.[ci]??base)}).map((pts:Point[],i:number)=><polyline key={`${ci}-${i}`} points={pts.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke={PALETTE[s.stroke!]} strokeWidth={s.strokeWidth} strokeLinecap="round" strokeLinejoin="round"/>))}
      </g>)}
    </g>
  </svg>;
};

/** Group opacity crossfade between two unrelated plans; not geometry morphing. */
export const SvgCrossfade:React.FC<{from:SvgPlan;to:SvgPlan;amount:number;x:number;y:number;width:number;height:number}>=({from,to,amount,x,y,width,height})=>{
  if(!Number.isFinite(amount)||amount<0||amount>1)throw Error('invalid SVG crossfade amount');
  // Validate both plans even at the endpoints; malformed hidden content is never ignored.
  svgPlacement(from,{x,y,width,height});svgPlacement(to,{x,y,width,height});
  return <>
    <div style={{position:'absolute',inset:0,opacity:1-amount,pointerEvents:'none'}}><SvgArt plan={from} x={x} y={y} width={width} height={height}/></div>
    <div style={{position:'absolute',inset:0,opacity:amount,pointerEvents:'none'}}><SvgArt plan={to} x={x} y={y} width={width} height={height}/></div>
  </>;
};
