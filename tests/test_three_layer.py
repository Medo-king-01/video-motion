"""Optional bounded K/Three layer and real-browser seek regressions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pytest
from conftest import ROOT, SKILL
from PIL import Image
from test_visual_tools import js

K = SKILL / 'templates/render'
THREE = ROOT / 'tools/optional-three/node_modules/three'


def test_layer_rejects_bad_inputs_closes_and_recovers_registration_failure():
    module = (K / 'lib/three-layer.js').as_uri()
    result = js(f'''import {{createThreeLayer}} from {json.dumps(module)};
      globalThis.document={{createElement:()=>({{}})}};
      let disposed=0, rendered=0, frames=[],draws=0,lost=false;
      class Renderer{{constructor(){{}}setPixelRatio(){{}}setSize(){{}}setClearColor(){{}}dispose(){{disposed++}}
        getContext(){{return {{isContextLost:()=>lost}}}}render(){{rendered++}}}}
      const THREE={{REVISION:'187',WebGLRenderer:Renderer}},scene={{isScene:true}},camera={{isCamera:true}};
      const cleanup=[],resources={{defer:f=>cleanup.push(f)}};
      const base={{THREE,width:20,height:20,scene,camera,resources,update:t=>{{frames.push(t)}}}};
      const ctx={{drawImage:()=>draws++}},at={{x:1,y:2,w:3,h:4}};
      const layer=createThreeLayer(base);layer.draw(ctx,.2,at);layer.draw(ctx,.1,at);layer.draw(ctx,.2,at);
      let invalid=0;for(const v of [NaN,Infinity])try{{layer.draw(ctx,v,at)}}catch{{invalid++}}
      lost=true;try{{layer.draw(ctx,.4,at)}}catch{{invalid++}}lost=false;
      for(const change of [{{width:0}},{{width:4097}},{{width:4096,height:4096}},{{THREE:{{...THREE,REVISION:'1'}}}}])try{{createThreeLayer({{...base,...change}})}}catch{{invalid++}}
      try{{createThreeLayer({{...base,resources:{{defer(){{throw Error('closed')}}}}}})}}catch{{invalid++}}
      cleanup[0]();layer.close();try{{layer.draw(ctx,0,at)}}catch{{invalid++}}
      console.log(JSON.stringify({{disposed,rendered,frames,draws,invalid,closed:layer.closed}}));''')
    assert result == {'disposed': 2, 'rendered': 3, 'frames': [.2, .1, .2, .4], 'draws': 3, 'invalid': 9, 'closed': True}


def test_async_update_is_not_accepted():
    module = (K / 'lib/three-layer.js').as_uri()
    result = js(f'''import {{createThreeLayer}} from {json.dumps(module)};
      globalThis.document={{createElement:()=>({{}})}};
      class Renderer{{setPixelRatio(){{}}setSize(){{}}setClearColor(){{}}dispose(){{}}}}
      const layer=createThreeLayer({{THREE:{{REVISION:'187',WebGLRenderer:Renderer}},width:2,height:2,scene:{{isScene:true}},camera:{{isCamera:true}},resources:{{defer(){{}}}},update:async()=>{{}}}});
      let rejected=false;try{{layer.draw({{drawImage(){{}}}},0,{{x:0,y:0,w:1,h:1}})}}catch{{rejected=true}}
      console.log(JSON.stringify(rejected));''')
    assert result is True


@pytest.fixture(scope='module')
def runtime():
    toolkit = ROOT/'tools/toolkit'
    if not shutil.which('node') or not THREE.is_dir() or not (toolkit/'node_modules/playwright-core').is_dir():
        pytest.skip('Optional Three test dependency or K toolkit not installed')
    data = subprocess.run(['node', str(ROOT/'tools/chromium.mjs'), '--json'], capture_output=True, text=True, timeout=90)
    if data.returncode: pytest.skip('Chromium unavailable')
    config = json.loads(data.stdout)
    return {**os.environ, 'MEDO_TOOLKIT': str(toolkit), 'MEDO_CHROMIUM': config['executablePath'],
            'LD_LIBRARY_PATH': (config.get('libraryPath') or '') + ':' + os.environ.get('LD_LIBRARY_PATH', '')}


@pytest.fixture
def project(tmp_path, runtime):
    proj = tmp_path/'project'; proj.mkdir()
    shutil.copytree(K,proj/'src')
    (proj/'package.json').write_text('{"type":"module","private":true}\n')
    (proj/'node_modules').symlink_to(THREE.parent, target_is_directory=True)
    (proj/'src/data.js').write_text("export const W=1080,H=1920,DURATION=1,scenes=[{id:'three-scene',start:0,end:1}];\n")
    shutil.copy2(ROOT/'tests/fixtures/visual/three-scene.js',proj/'src/scenes/three-scene.js')
    return proj,runtime


def run_scene(project, runtime, out, *extra):
    cmd=['node','src/render.js','--from','0','--to','1','--fps','30','--scale','.25','--out',str(out),*extra]
    return subprocess.run(cmd,cwd=project,env=runtime,capture_output=True,text=True,timeout=120)


def test_real_three_k_reverse_seek_and_reduced_mode(project):
    proj, env = project
    audit = run_scene(proj, env, 'audit', '--audit','--replay')
    assert audit.returncode == 0, audit.stderr
    report=json.loads((proj/'audit/report.json').read_text())
    assert report['status']=='pass' and report['replay']['checkedFrames']==30 and report['replay']['failedFrames']==0
    result=run_scene(proj, env, 'normal', '--jpg')
    assert result.returncode==0,result.stderr
    result=run_scene(proj, env, 'reduced', '--jpg','--motion-mode','reduced')
    assert result.returncode==0,result.stderr
    assert (proj/'normal/00000.jpg').read_bytes()==(proj/'reduced/00000.jpg').read_bytes()
    assert (proj/'normal/00020.jpg').read_bytes()!=(proj/'reduced/00020.jpg').read_bytes()
    # Transparent WebGL canvas must preserve the authored 2D background around the cube.
    with Image.open(proj/'normal/00000.jpg') as image:
        assert max(image.getpixel((50,145))) < 12
        assert max(image.getpixel((135,230))) > 40


def test_scope_continues_cleanup_when_renderer_disposal_fails():
    layer_module = (K / 'lib/three-layer.js').as_uri()
    scope_module = (K / 'lib/resource-scope.js').as_uri()
    result = js(f'''import {{createThreeLayer}} from {json.dumps(layer_module)};
      import {{createResourceScope}} from {json.dumps(scope_module)};
      globalThis.document={{createElement:()=>({{}})}};const log=[];
      class Renderer{{constructor(options){{log.push(options.alpha&&options.preserveDrawingBuffer&&!options.antialias?'options-ok':'bad-options')}}
        setPixelRatio(){{}}setSize(){{}}setClearColor(){{}}dispose(){{log.push('renderer');throw Error('cleanup failed')}}}}
      const resources=createResourceScope();resources.defer(()=>log.push('earlier'));
      const layer=createThreeLayer({{THREE:{{REVISION:'187',WebGLRenderer:Renderer}},width:2,height:2,scene:{{isScene:true}},camera:{{isCamera:true}},resources,update:()=>{{}}}});
      resources.defer(()=>log.push('assets'));let errors=0;try{{await resources.close()}}catch(e){{errors=e.errors.length}}
      layer.close();console.log(JSON.stringify({{log,errors,closed:layer.closed}}));''')
    assert result == {'log': ['options-ok', 'assets', 'renderer', 'earlier'], 'errors': 1, 'closed': True}
