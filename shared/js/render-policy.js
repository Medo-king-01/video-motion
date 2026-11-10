/** Explicit offline decorative-only reduced-motion overrides. Never derives timings or gates. */
export function compileMotionPolicy(spec){
  if(!spec||spec.version!==1||typeof spec.reduced!=='boolean'||!Array.isArray(spec.decorative)||spec.decorative.length>256)throw Error('invalid motion policy');
  const forbidden=new Set(['__proto__','constructor','prototype']);
  function snapshot(value){
    const active=new Set();let count=0;
    function walk(v,depth){
      if(++count>1024||depth>8)throw Error('decorative value budget exceeded');
      if(typeof v==='number'&&Number.isFinite(v))return v;
      if(!v||typeof v!=='object'||active.has(v))throw Error('decorative value must be a finite numeric tree');
      active.add(v);
      try{
        if(Array.isArray(v)){if(!v.length||v.length>256||Object.keys(v).length!==v.length||Array.from({length:v.length},(_,i)=>i).some(i=>!Object.hasOwn(v,i)))throw Error('invalid decorative array');return v.map(x=>walk(x,depth+1));}
        if(Object.getPrototypeOf(v)!==Object.prototype)throw Error('invalid decorative object');
        const entries=Object.entries(v);if(!entries.length||entries.length>256||entries.some(([k])=>forbidden.has(k)))throw Error('invalid decorative object');
        return Object.fromEntries(entries.map(([k,x])=>[k,walk(x,depth+1)]));
      }finally{active.delete(v);}
    }
    return walk(value,0);
  }
  function sameShape(a,b){
    if(typeof a==='number')return typeof b==='number';
    if(Array.isArray(a))return Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>sameShape(v,b[i]));
    if(!b||typeof b!=='object'||Array.isArray(b))return false;
    const keys=Object.keys(a).sort(),other=Object.keys(b).sort();
    return JSON.stringify(keys)===JSON.stringify(other)&&keys.every(k=>sameShape(a[k],b[k]));
  }
  const tracks=new Map();
  for(const entry of spec.decorative){
    if(!entry||typeof entry.track!=='string'||!entry.track.trim()||forbidden.has(entry.track)||tracks.has(entry.track))throw Error('invalid decorative track');
    tracks.set(entry.track,snapshot(entry.value));
  }
  const reduced=spec.reduced;
  return {at(values){
    if(!values||typeof values!=='object'||Array.isArray(values))throw Error('expected track values');
    const out=Object.fromEntries(Object.entries(values));
    for(const [name,value] of tracks){
      if(!Object.hasOwn(values,name)||!sameShape(value,snapshot(values[name])))throw Error('missing or mismatched decorative track');
      if(reduced)out[name]=snapshot(value);
    }
    return out;
  }};
}
