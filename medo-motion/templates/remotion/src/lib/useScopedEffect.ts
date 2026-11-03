import {DependencyList,useLayoutEffect} from 'react';
import {createSyncResourceScope} from './sync-resource-scope.js';

export type SyncResourceScope=ReturnType<typeof createSyncResourceScope>;
/** Own synchronous resources for one committed React effect; deps must include every setup dependency. */
export function useScopedEffect(setup:(scope:SyncResourceScope)=>void,deps:DependencyList):void{
  useLayoutEffect(()=>{
    const scope=createSyncResourceScope();
    try{
      const result=setup(scope) as unknown;
      if(result && typeof (result as {then?:unknown}).then==='function'){
        Promise.resolve(result).catch(()=>{});
        throw Error('async setup is not supported in a synchronous scope');
      }
      if(result!==undefined)throw Error('register cleanup with scope.defer');
    }catch(error){
      try{scope.close();}catch(cleanup){console.error('resource setup cleanup failed',cleanup);}
      throw error;
    }
    return ()=>scope.close();
  },deps);
}
