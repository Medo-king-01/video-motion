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

/** Finite per-frame dependency graph. Each node executes once; no cross-frame cache. */
export function compileFrameGraph(entries){
  if(!Array.isArray(entries)||entries.length>256)throw Error('invalid frame graph');
  const nodes=new Map(),forbidden=new Set(['__proto__','constructor','prototype']);
  for(const e of entries){
    if(!e||typeof e.id!=='string'||!e.id.trim()||forbidden.has(e.id)||nodes.has(e.id)||!Array.isArray(e.depends)||e.depends.length>256||typeof e.sample!=='function')throw Error('invalid graph entry');
    if(e.depends.some(d=>typeof d!=='string'||!d.trim()||forbidden.has(d))||new Set(e.depends).size!==e.depends.length)throw Error('invalid graph dependencies');
    nodes.set(e.id,{id:e.id,depends:[...e.depends],sample:e.sample});
  }
  const mark=new Map(),order=[];
  function visit(id){
    if(!nodes.has(id))throw Error('unknown graph dependency');
    if(mark.get(id)===1)throw Error('frame graph cycle');if(mark.get(id)===2)return;
    mark.set(id,1);const node=nodes.get(id);node.depends.forEach(visit);mark.set(id,2);order.push(node);
  }
  for(const id of nodes.keys())visit(id);
  return {at(t){
    if(typeof t!=='number'||!Number.isFinite(t))throw Error('invalid time');
    const out=Object.create(null);
    for(const node of order){
      const deps=Object.fromEntries(node.depends.map(id=>[id,out[id]]));const value=node.sample(t,deps);
      if(value&&typeof value.then==='function'){Promise.resolve(value).catch(()=>{});throw Error('frame graph samplers must be synchronous');}
      out[node.id]=value;
    }
    return out;
  }};
}
