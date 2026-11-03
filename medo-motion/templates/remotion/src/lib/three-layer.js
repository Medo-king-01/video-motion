/**
 * Optional Three r187 -> Canvas 2D bridge. Caller supplies the local Three module,
 * scene/camera, pure absolute-time updates, and explicitly owns scene assets.
 * This layer owns only its WebGLRenderer, registered in the scene resource scope.
 */
export function createThreeLayer({THREE,width,height,scene,camera,update,resources}) {
  if(!THREE||THREE.REVISION!=='187'||typeof THREE.WebGLRenderer!=='function')throw Error('Three r187 is required');
  if(!Number.isInteger(width)||!Number.isInteger(height)||width<2||height<2||width>4096||height>4096||width*height>4194304)throw Error('Invalid Three layer dimensions');
  if(scene?.isScene!==true||camera?.isCamera!==true||typeof update!=='function'||typeof resources?.defer!=='function')throw Error('Three scene, camera, update and resource scope are required');
  const canvas=document.createElement('canvas');let renderer,closed=false;
  try{
    renderer=new THREE.WebGLRenderer({canvas,alpha:true,antialias:false,preserveDrawingBuffer:true,premultipliedAlpha:true});
    renderer.setPixelRatio(1);renderer.setSize(width,height,false);renderer.setClearColor(0,0);
    resources.defer(()=>close());
  }catch(error){try{renderer?.dispose();}catch{}throw error;}
  function close(){if(closed)return;closed=true;renderer.dispose();}
  return {
    draw(ctx,time,{x,y,w,h}){
      if(closed)throw Error('Three layer is closed');
      if(!ctx||typeof ctx.drawImage!=='function'||![time,x,y,w,h].every(Number.isFinite)||w<=0||h<=0)throw Error('Invalid Three layer frame or placement');
      const result=update(time);
      if(result&&typeof result.then==='function')throw Error('Three frame update must be synchronous');
      const gl=renderer.getContext();
      if(gl.isContextLost())throw Error('Three WebGL context lost');
      renderer.render(scene,camera);
      if(gl.isContextLost())throw Error('Three WebGL context lost');
      ctx.drawImage(canvas,x,y,w,h);
    },
    close,
    get closed(){return closed;},
  };
}
