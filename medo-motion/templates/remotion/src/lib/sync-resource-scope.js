/** Synchronous React-lifetime ownership. Never register async disposers. */
export function createSyncResourceScope(){
  const stack=[];let closed=false;
  return {
    /** @param {() => void} dispose */
    defer(dispose){if(closed||typeof dispose!=='function')throw Error('scope closed or disposer invalid');stack.push(dispose);},
    close(){
      if(closed)return;closed=true;const errors=[];
      while(stack.length){
        try{
          const value=stack.pop()();
          if(value&&typeof value.then==='function'){
            Promise.resolve(value).catch(()=>{});
            throw Error('async cleanup is not supported in a synchronous scope');
          }
        }catch(error){errors.push(error);}
      }
      if(errors.length)throw new AggregateError(errors,'resource cleanup failed');
    },
    get closed(){return closed;},
  };
}
