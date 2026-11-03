import React from 'react';
import {PALETTE} from '../brand';
import {svgPlacement} from './svg-art.js';
import {strokeSegments} from './motion-geometry.js';

type Token=keyof typeof PALETTE;
type Point={x:number;y:number};
type Contour={points:Point[];closed:boolean};
export type SvgPlan={version:1;viewBox:[number,number,number,number];shapes:{id:string;fill:Token|null;stroke:Token|null;strokeWidth:number;opacity:number;contours:Contour[]}[]};
/** A bounded precompiled SVG plan. Use an explicit frame-derived progress; never insert SVG markup. */
export const SvgArt:React.FC<{plan:SvgPlan;x:number;y:number;width:number;height:number;progress?:number}>=({plan,x,y,width,height,progress=1})=>{
  const place=svgPlacement(plan,{x,y,width,height});
  if(!Number.isFinite(progress)||progress<0||progress>1)throw Error('SVG stroke progress must be 0..1');
  const path=(contours:Contour[])=>contours.map(c=>c.points.map((p,i)=>`${i?'L':'M'}${p.x} ${p.y}`).join(' ')+' Z').join(' ');
  return <svg width="100%" height="100%" style={{position:'absolute',inset:0,overflow:'visible',pointerEvents:'none'}}>
    <g transform={`translate(${place.x} ${place.y}) scale(${place.scale})`}>
      {plan.shapes.map(s=><g key={s.id} opacity={s.opacity}>
        {s.fill!==null&&<path d={path(s.contours)} fill={PALETTE[s.fill]} fillRule="evenodd"/>}
        {s.stroke!==null&&s.strokeWidth>0&&s.contours.flatMap((c,ci)=>strokeSegments(c.points,{closed:c.closed,end:progress}).map((pts:Point[],i:number)=><polyline key={`${ci}-${i}`} points={pts.map(p=>`${p.x},${p.y}`).join(' ')} fill="none" stroke={PALETTE[s.stroke!]} strokeWidth={s.strokeWidth} strokeLinecap="round" strokeLinejoin="round"/>))}
      </g>)}
    </g>
  </svg>;
};
