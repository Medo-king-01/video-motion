// Synthetic scene factory for Remotion. All animation derives from its explicit local time.
import * as THREE from 'three';
import {createThreeLayer} from './lib/three-layer.js';
import {compileSequence} from './lib/motion-plan.js';
export function makeThreeScene(resources,reduced){
  const scene=new THREE.Scene(),camera=new THREE.OrthographicCamera(-2,2,2,-2,.1,20);
  camera.position.set(0,0,5);camera.lookAt(0,0,0);camera.updateProjectionMatrix();
  const plan=compileSequence({version:1,clips:[
    {id:'yaw',track:'yaw',at:0,duration:1,from:.2,to:1.25,easing:'linear'},
    {id:'pitch',track:'pitch',at:0,duration:1,from:.25,to:.55,easing:'linear'},
  ]});
  let cube;
  const layer=createThreeLayer({THREE,width:512,height:512,scene,camera,resources,update(time){
    const values=plan.at(reduced?0:time);cube.rotation.set(values.pitch,values.yaw,0);
  }});
  const geometry=new THREE.BoxGeometry(2,2,2);resources.defer(()=>geometry.dispose());
  const materials=[];
  for(const color of ['#CB271B','#D5AEA6','#F3F2F1','#CB271B','#D5AEA6','#F3F2F1']){
    const material=new THREE.MeshBasicMaterial({color});resources.defer(()=>material.dispose());materials.push(material);
  }
  cube=new THREE.Mesh(geometry,materials);scene.add(cube);return layer;
}
