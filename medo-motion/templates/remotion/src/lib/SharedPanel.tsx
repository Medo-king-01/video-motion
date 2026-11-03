import React from 'react';
import {sharedElementAt} from './shared-element.js';
import {PALETTE} from '../brand';

type State=ReturnType<typeof sharedElementAt>;
/** Relative-positioned contents, no CSS timer, no duplicate source/destination shell. */
export const SharedPanel:React.FC<{
  spec:Parameters<typeof sharedElementAt>[0];time:number;
  label?:(state:State)=>React.ReactNode;
  children?:(state:State)=>React.ReactNode;
}>=({spec,time,label,children})=>{
  const state=sharedElementAt(spec,time);
  if(!state.active)return null;
  const {x,y,w,h,r}=state.box;
  return <div data-shared-id={state.id} style={{position:'absolute',left:x,top:y,
    width:w,height:h,borderRadius:r,boxSizing:'border-box',
    background:PALETTE.gray1,border:`3px solid ${PALETTE.ink}`}}>
    {label?.(state)}{state.contentsReady?children?.(state):null}
  </div>;
};
