/** Explicitly owned asynchronous resources; release LIFO even when one fails. */
export function createResourceScope(){
  let state='open',pending=null;const stack=[];
  return {
    defer(dispose){if(state!=='open'||typeof dispose!=='function')throw Error('scope closed or disposer invalid');stack.push(dispose);},
    close(){
      if(pending)return pending;state='closed';
      pending=Promise.resolve().then(async()=>{const errors=[];while(stack.length){try{await stack.pop()();}catch(e){errors.push(e);}}if(errors.length)throw new AggregateError(errors,'resource cleanup failed');});
      return pending;
    },
    get closed(){return state==='closed';}
  };
}
