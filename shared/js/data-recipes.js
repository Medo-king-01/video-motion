// Original, frame-deterministic data recipes. No timers, data fetching or chart dependencies.
import { ease, clamp } from './motion.js';
const number=n=>typeof n==='number'&&Number.isFinite(n);
const text=s=>typeof s==='string'&&s.trim().length>0;
export function validateDataset(data) {
  const errors=[];
  if(!data||data.version!==1)return ['dataset version must be 1'];
  if(!text(data.source)||!text(data.unit))errors.push('source and unit are required (use an explicit dimensionless unit where applicable)');
  if(!['ar-EG','en-US'].includes(data.locale))errors.push('locale must be ar-EG or en-US');
  if(!['comparison','timeline','counter'].includes(data.kind))errors.push('unknown data kind');
  if(!Number.isInteger(data.decimals)||data.decimals<0||data.decimals>6)errors.push('decimals must be an integer from 0 to 6');
  const rows=data.rows;
  if(!Array.isArray(rows)||!rows.length)return [...errors,'rows must be non-empty'];
  if(rows.length>1000)errors.push('at most 1000 rows');
  if(data.kind==='counter'&&rows.length!==1)errors.push('counter needs exactly one row');
  if(data.kind==='comparison'&&(rows.length<2||rows.length>8))errors.push('comparison needs 2–8 rows');
  if(data.kind==='timeline'&&rows.length<2)errors.push('timeline needs at least two points');
  const ids=new Set();let previous=-Infinity;
  for(const row of rows){
    if(!row||!text(row.id)||!text(row.label)||ids.has(row.id))errors.push('rows need unique ids and non-empty labels');
    ids.add(row?.id);
    if(!number(row?.value)||(data.kind!=='timeline'&&row.value<0))errors.push('values must be finite (non-negative for comparisons/counters)');
    if(number(row?.value)&&Number.isInteger(data.decimals)){const scaled=row.value*10**data.decimals;
      if(!Number.isSafeInteger(Math.round(scaled))||Math.abs(scaled-Math.round(scaled))>1e-6)errors.push('value exceeds declared decimal precision or safe numeric range');}
    if(data.kind==='timeline'){
      if(!number(row?.at)||row.at<0||row.at<=previous)errors.push('timeline at values must increase strictly from zero or later');
      previous=row?.at;
    }
  }
  return errors;
}
export function validateRecipe(spec) {
  const errors=validateDataset(spec?.data);
  if(!number(spec?.start)||!number(spec?.end)||spec.start<0||spec.end<=spec.start)errors.push('recipe needs measured scene-local start/end');
  const a=spec?.anchor;
  if(!text(a?.text)||!number(a?.start)||!number(a?.end)||!(spec.start<=a.start&&a.start<a.end&&a.end<=spec.end))
    errors.push('recipe needs a measured scene-local word anchor within its bounds');
  return errors;
}
export function recipeAt(spec,time) {
  const errors=validateRecipe(spec);if(errors.length)throw Error(errors.join('; '));
  if(!number(time))throw Error('time must be finite');
  const {data,anchor}=spec;
  const active=time>=spec.start&&time<spec.end, visible=active&&time>=anchor.start;
  const p=ease('cubicOut',clamp((time-anchor.start)/(anchor.end-anchor.start)));
  const format=value=>new Intl.NumberFormat(data.locale,{numberingSystem:'latn',maximumFractionDigits:data.decimals}).format(value);
  /** @type {{active:boolean,visible:boolean,progress:number,unit:string,source:string,kind:string,
   * rows:Array<{id:string,label:string,value:number,shown:number,fraction:number,display:string}>,
   * points:Array<{id:string,x:number,y:number,value:number,label:string}>,domain?:number[]}} */
  const state={active,visible,progress:p,unit:data.unit,source:data.source,kind:data.kind,rows:[],points:[]};
  if(!visible)return state; // Axes/context may prepare; never reveal a fact before its spoken word.
  if(data.kind==='timeline'){
    const first=data.rows[0].at,last=data.rows.at(-1).at,lo=Math.min(0,...data.rows.map(r=>r.value)),hi=Math.max(0,...data.rows.map(r=>r.value));
    const span=hi-lo||1,cut=first+(last-first)*p;
    state.domain=[lo,hi];
    for(let i=0;i<data.rows.length;i++){
      const r=data.rows[i];
      if(r.at<=cut)state.points.push({id:r.id,x:(r.at-first)/(last-first),y:1-(r.value-lo)/span,value:r.value,label:r.label});
      else {const prev=data.rows[i-1];if(prev){const q=(cut-prev.at)/(r.at-prev.at),v=prev.value+(r.value-prev.value)*q;
        state.points.push({id:'cursor',x:(cut-first)/(last-first),y:1-(v-lo)/span,value:v,label:''});}break;}
    }
    state.rows=data.rows.map(r=>({...r,shown:r.value,fraction:0,display:format(r.value)}));
  }else{
    const max=Math.max(...data.rows.map(r=>r.value))||1;
    state.rows=data.rows.map(r=>({...r,shown:r.value*p,fraction:r.value/max*p,display:format(r.value*p)}));
  }
  return state;
}
