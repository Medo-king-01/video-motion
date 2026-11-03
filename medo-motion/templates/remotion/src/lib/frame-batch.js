/** Evaluate each pure sampler once per call; no global or cross-frame cache. */
export function compileFrameBatch(entries){
  if(!Array.isArray(entries)||entries.length>256)throw Error('invalid frame batch');
  const names=new Set();const compiled=entries.map(e=>{
    if(!e||typeof e.id!=='string'||!e.id.trim()||['__proto__','constructor','prototype'].includes(e.id)||names.has(e.id)||typeof e.sample!=='function')throw Error('invalid batch entry');
    names.add(e.id);return {id:e.id,sample:e.sample};
  });
  return {at(t){
    if(typeof t!=='number'||!Number.isFinite(t))throw Error('invalid time');
    const cache=new Map(),out=Object.create(null);
    for(const e of compiled){if(!cache.has(e.sample))cache.set(e.sample,e.sample(t));out[e.id]=cache.get(e.sample);}
    return out;
  }};
}
