// Synthetic local fixture: no live inputs, facts, VO or imported assets.
import * as THREE from '/node_modules/three/build/three.module.js';
import {createThreeLayer} from '../lib/three-layer.js';
import {compileSequence} from '../lib/motion-plan.js';
export const supportsReducedMotion=true;
let layer;
export function init({resources,motionMode}){
  const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-2,2,2,-2,.1,20);
  camera.position.set(0,0,5);camera.lookAt(0,0,0);camera.updateProjectionMatrix();
  let cube;
  const plan=compileSequence({version:1,clips:[
    {id:'yaw',track:'yaw',at:0,duration:1,from:.2,to:1.25,easing:'linear'},
    {id:'pitch',track:'pitch',at:0,duration:1,from:.25,to:.55,easing:'linear'},
  ]});
  // Register the renderer first: scene-owned assets registered later close before it.
  layer=createThreeLayer({THREE,width:512,height:512,scene,camera,resources,update(time){
    const values=plan.at(motionMode==='reduced'?0:time);
    cube.rotation.set(values.pitch,values.yaw,0);
  }});
  const geometry=new THREE.BoxGeometry(2,2,2);
  resources.defer(()=>geometry.dispose());
  const materials=[];
  for(const color of ['#CB271B','#D5AEA6','#F3F2F1','#CB271B','#D5AEA6','#F3F2F1']){
    const material=new THREE.MeshBasicMaterial({color});
    resources.defer(()=>material.dispose());materials.push(material);
  }
  cube=new THREE.Mesh(geometry,materials);scene.add(cube);
}
export function draw(ctx,t){
  ctx.fillStyle='#030303';ctx.fillRect(0,0,1080,1920);
  ctx.fillStyle='#F3F2F1';ctx.textAlign='center';ctx.font='64px sans-serif';ctx.fillText('3D render test',540,410);
  layer.draw(ctx,t,{x:180,y:560,w:720,h:720});
}
