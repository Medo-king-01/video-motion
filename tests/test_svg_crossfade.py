"""Explicit group-opacity fallback for SVGs with incompatible geometry."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import SKILL
from PIL import Image
from svg_art import draw_svg_crossfade
from svg_compile import compile_svg
from test_gpu_preflight import browser_env

K=SKILL/'templates/render'
R=SKILL/'templates/remotion'
FROM=compile_svg('<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="#CB271B" fill-rule="evenodd"/></svg>')
TO=compile_svg('<svg viewBox="0 0 100 100"><rect x="0" y="0" width="100" height="100" fill="#0A0A0A" fill-rule="evenodd"/><circle cx="80" cy="80" r="8" fill="#D8D7D5" fill-rule="evenodd"/></svg>')
PLACEMENT={'x':0,'y':0,'width':100,'height':100}


def render_p(amount):
    im=Image.new('RGB',(100,100),'#F3F2F1');draw_svg_crossfade(im,FROM,TO,amount,PLACEMENT);return im


def test_python_crossfade_endpoints_middle_and_reverse():
    assert render_p(0).getpixel((50,50))==(203,39,27)
    assert render_p(1).getpixel((50,50))==(10,10,10)
    mid=render_p(.5);assert mid.getpixel((50,50))==pytest.approx((116,75,72),abs=1)
    assert mid.tobytes()==render_p(.5).tobytes()
    assert render_p(0).getpixel((80,80))==(203,39,27) and render_p(1).getpixel((80,80))==(216,215,213)


@pytest.mark.parametrize('amount', [-1,1.1,float('nan'),True,None])
def test_invalid_crossfade_rejected_before_drawing(amount):
    im=Image.new('RGB',(100,100),'#F3F2F1');before=im.tobytes()
    with pytest.raises(ValueError): draw_svg_crossfade(im,FROM,TO,amount,PLACEMENT)
    assert im.tobytes()==before


def test_invalid_hidden_plan_fails_before_drawing():
    broken=copy.deepcopy(TO);broken['shapes'][0]['fill']='url(https://invalid)'
    im=Image.new('RGB',(100,100),'#F3F2F1');before=im.tobytes()
    with pytest.raises(ValueError): draw_svg_crossfade(im,FROM,broken,0,PLACEMENT)
    assert im.tobytes()==before


@pytest.mark.slow
def test_k_real_canvas_crossfade_interior_pixels(tmp_path):
    env=browser_env();project=tmp_path/'k';project.mkdir();shutil.copytree(K,project/'src')
    (project/'package.json').write_text('{"type":"module"}')
    (project/'src/data.js').write_text("export const W=1080,H=1920,FPS=30,DURATION=1,scenes=[{id:'crossfade-test',start:0,end:1}];")
    (project/'src/scenes/crossfade-test.js').write_text("import {drawSvgCrossfade} from '../lib/svg-canvas.js';\n"+
        'const a='+json.dumps(FROM)+';const b='+json.dumps(TO)+';const p='+json.dumps(PLACEMENT)+';\n'+
        "export function draw(ctx,t,{W,H}){ctx.fillStyle='#F3F2F1';ctx.fillRect(0,0,W,H);drawSvgCrossfade(ctx,a,b,t,p);ctx.fillStyle='#0A0A0A';ctx.font='32px sans-serif';ctx.fillText('test',250,400);}\n")
    result=subprocess.run(['node','src/render.js','--jpg','--from','.5','--to',str(.5+1/30),'--out',str(tmp_path/'frames')],cwd=project,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(tmp_path/'frames/00000.jpg') as im:
        assert im.convert('RGB').getpixel((50,50))==pytest.approx(render_p(.5).getpixel((50,50)),abs=4)
    result=subprocess.run(['node','src/render.js','--jpg','--scale','.25','--from','.5','--to',str(.5+1/30),'--out',str(tmp_path/'small')],cwd=project,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(tmp_path/'small/00000.jpg') as im:
        assert im.convert('RGB').getpixel((12,12))==pytest.approx(render_p(.5).getpixel((50,50)),abs=4)
    result=subprocess.run(['node','src/render.js','--audit','--replay','--scale','.25','--from','0','--to','1','--out',str(tmp_path/'audit')],cwd=project,env=env,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    report=json.loads((tmp_path/'audit/report.json').read_text())
    assert report['status']=='pass' and report['replay']['checkedFrames']==30 and report['replay']['failedFrames']==0


@pytest.mark.slow
def test_r_real_svg_crossfade_interior_pixels(tmp_path):
    value=os.environ.get('MEDO_REMOTION_TEST_NODE_MODULES')
    if not value: pytest.skip('Set MEDO_REMOTION_TEST_NODE_MODULES to run the optional Remotion integration test')
    modules=Path(value).resolve()
    for name in ('@remotion/cli','@remotion/renderer','typescript','react'):
        if not (modules/name).is_dir(): pytest.fail(f'Optional Remotion modules incomplete: {name}')
    env=browser_env();env['REMOTION_BROWSER_EXECUTABLE']=env['MEDO_CHROMIUM']
    project=tmp_path/'r';shutil.copytree(R,project);(project/'node_modules').symlink_to(modules,target_is_directory=True)
    tsconfig=json.loads((project/'tsconfig.json').read_text());tsconfig['include']=['src/Root.tsx','src/index.ts']
    (project/'tsconfig.json').write_text(json.dumps(tsconfig))
    (project/'src/Root.tsx').write_text('''import React from 'react';
import {AbsoluteFill,Composition} from 'remotion';
import {SvgCrossfade,SvgPlan} from './lib/SvgArt';
const from='''+json.dumps(FROM)+''' as SvgPlan,to='''+json.dumps(TO)+''' as SvgPlan;
const Scene=()=> <AbsoluteFill style={{background:'#F3F2F1'}}><SvgCrossfade from={from} to={to} amount={.5} x={0} y={0} width={100} height={100}/></AbsoluteFill>;
export const RemotionRoot:React.FC=()=> <Composition id="Crossfade" component={Scene} fps={30} durationInFrames={1} width={100} height={100}/>;''')
    for command in (['node','node_modules/typescript/bin/tsc','--noEmit'],
                    ['node','scripts/launch-remotion.mjs','still','src/index.ts','Crossfade','frame.png','--frame=0','--log=error']):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(project/'frame.png') as im:
        assert im.convert('RGB').getpixel((50,50))==pytest.approx(render_p(.5).getpixel((50,50)),abs=2)


def test_canvas_rejects_invalid_hidden_plan_and_context_before_drawing():
    from test_visual_tools import js

    invalid=copy.deepcopy(TO);invalid['shapes'][0]['fill']='not-a-token'
    module=(K/'lib/svg-canvas.js').as_uri()
    result=js(f'''import {{drawSvgCrossfade}} from {json.dumps(module)};
      let draws=0;const ctx={{canvas:{{width:100,height:100}},getTransform:()=>({{is2D:true,a:1,b:0,c:0,d:1,e:0,f:0}}),globalCompositeOperation:'source-over',drawImage:()=>draws++}};
      let rejected=0;try{{drawSvgCrossfade(ctx,{json.dumps(FROM)},{json.dumps(invalid)},0,{json.dumps(PLACEMENT)})}}catch{{rejected++}}
      ctx.getTransform=()=>({{is2D:true,a:Infinity,b:0,c:0,d:1,e:0,f:0}});try{{drawSvgCrossfade(ctx,{json.dumps(FROM)},{json.dumps(TO)},.5,{json.dumps(PLACEMENT)})}}catch{{rejected++}}
      console.log(JSON.stringify({{rejected,draws}}));''')
    assert result=={'rejected':2,'draws':0}


def test_crossfade_preserves_transparency_and_group_opacity():
    im=Image.new('RGBA',(100,100),(0,0,0,0));draw_svg_crossfade(im,FROM,TO,.5,PLACEMENT)
    assert im.getpixel((5,5))[3] in (127,128)
    assert im.getpixel((50,50))[3] in (191,192)


def test_crossfade_rejects_stroke_options_before_painting():
    image=Image.new('RGB',(100,100),'#F3F2F1');before=image.tobytes()
    with pytest.raises(ValueError): draw_svg_crossfade(image,FROM,TO,.5,{**PLACEMENT,'progress':0})
    assert image.tobytes()==before
