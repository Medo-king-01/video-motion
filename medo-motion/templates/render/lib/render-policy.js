/** Explicit offline decorative-only reduced-motion overrides. Never derives timings or gates. */
export function compileMotionPolicy(spec){
  if(!spec||spec.version!==1||typeof spec.reduced!=='boolean'||!Array.isArray(spec.decorative)||spec.decorative.length>256)throw Error('invalid motion policy');
  const tracks=new Map();
  for(const entry of spec.decorative){
    if(!entry||typeof entry.track!=='string'||!entry.track.trim()||['__proto__','constructor','prototype'].includes(entry.track)||tracks.has(entry.track)||typeof entry.value!=='number'||!Number.isFinite(entry.value))throw Error('invalid decorative track');
    tracks.set(entry.track,entry.value);
  }
  const reduced=spec.reduced;
  return {at(values){
    if(!values||typeof values!=='object'||Array.isArray(values))throw Error('expected track values');
    const out=Object.fromEntries(Object.entries(values));
    for(const [name,value] of tracks){
      if(!Object.hasOwn(values,name)||typeof values[name]!=='number'||!Number.isFinite(values[name]))throw Error('missing or nonnumeric decorative track');
      if(reduced)out[name]=value;
    }
    return out;
  }};
}
