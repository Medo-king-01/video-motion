"""Strict local SVG linear gradient compilation and P/K/R raster integration."""
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
from svg_art import draw_svg_art, svg_placement, validate_svg_art
from svg_compile import compile_svg
from svg_morph import compile_svg_morph
from test_gpu_preflight import browser_env
from test_visual_tools import js

K=SKILL/'templates/render'
R=SKILL/'templates/remotion'
GRADIENT='''<svg viewBox="0 0 100 100">
<defs><linearGradient id="shade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="100" y2="0">
<stop offset="0" stop-color="#CB271B"/><stop offset="1" stop-color="#0A0A0A"/>
</linearGradient></defs>
<rect x="0" y="0" width="100" height="100" style="fill:url(#shade);fill-rule:evenodd"/>
</svg>'''
RADIAL=GRADIENT.replace('linearGradient','radialGradient').replace('x1="0" y1="0" x2="100" y2="0"','cx="50" cy="50" r="50"')
PLAN=compile_svg(GRADIENT)


def test_local_gradient_plan_and_p_pixels():
    fill=PLAN['shapes'][0]['fill']
    assert fill=={'type':'linear','x1':0,'y1':0,'x2':100,'y2':0,'stops':[{'offset':0,'color':'red'},{'offset':1,'color':'ink'}]}
    validate_svg_art(PLAN)
    image=Image.new('RGB',(100,100),'#F3F2F1');draw_svg_art(image,PLAN,{'width':100,'height':100})
    assert image.getpixel((0,50))==pytest.approx((202,39,27),abs=1)
    assert image.getpixel((50,50))==pytest.approx((106,24,18),abs=1)
    assert image.getpixel((99,50))==pytest.approx((11,10,10),abs=1)


@pytest.mark.parametrize('source', [
    GRADIENT.replace('url(#shade)','url(https://example.com/a)'),
    GRADIENT.replace('url(#shade)','url(#missing)'),
    GRADIENT.replace('gradientUnits="userSpaceOnUse"','gradientUnits="objectBoundingBox"'),
    GRADIENT.replace('x1="0"','x1="0%"'),
    GRADIENT.replace('x2="100"','x2="0"'),
    GRADIENT.replace('offset="1"','offset="0"'),
    GRADIENT.replace('offset="1"','offset="0.9"'),
    GRADIENT.replace('stop-color="#0A0A0A"','stop-color="red"'),
    GRADIENT.replace('stop-color="#0A0A0A"','stop-color="#0A0A0A" stop-opacity="0.5"'),
    GRADIENT.replace('<linearGradient','<linearGradient href="#other"'),
    GRADIENT.replace('<rect x=', '<rect transform="scale(2 1)" x='),
    GRADIENT.replace('<linearGradient','<radialGradient').replace('</linearGradient>','</radialGradient>'),
    GRADIENT.replace('fill:url(#shade)','fill:#CB271B;stroke:url(#shade)'),
])
def test_unsupported_gradients_are_rejected(source):
    with pytest.raises(ValueError): compile_svg(source)


def test_validator_rejects_bad_gradient_in_p_and_js():
    bad=copy.deepcopy(PLAN);bad['shapes'][0]['fill']['stops'][1]['color']='url(https://invalid)'
    with pytest.raises(ValueError): validate_svg_art(bad)
    module=(K/'lib/svg-art.js').as_uri()
    assert js(f'import {{validateSvgArt}} from {json.dumps(module)};let bad=false;try{{validateSvgArt({json.dumps(bad)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')
    assert (K/'lib/svg-art.js').read_bytes()==(R/'src/lib/svg-art.js').read_bytes()


def test_svg_placement_gradient_budget_parity():
    p=copy.deepcopy(PLAN);p['shapes'][0]['fill']['x2']=1e6
    with pytest.raises(ValueError): svg_placement(p,{'width':1000000,'height':1000000})
    module=(K/'lib/svg-art.js').as_uri()
    assert js(f'import {{svgPlacement}} from {json.dumps(module)};let bad=false;try{{svgPlacement({json.dumps(p)},{{width:1000000,height:1000000}})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def test_morph_uses_same_static_gradient_in_p_and_js():
    source=copy.deepcopy(PLAN);target=copy.deepcopy(PLAN)
    for point in target['shapes'][0]['contours'][0]['points']: point['x']*=.9
    spec={'version':1,'from':source,'to':target,'count':8}
    result=compile_svg_morph(spec).at(.5)
    module=(K/'lib/svg-morph.js').as_uri()
    actual=js(f'import {{compileSvgMorph}} from {json.dumps(module)};console.log(JSON.stringify(compileSvgMorph({json.dumps(spec)}).at(.5)));')
    assert actual['shapes'][0]['fill']==result['shapes'][0]['fill']==source['shapes'][0]['fill']
    target['shapes'][0]['fill']['x2']=80
    with pytest.raises(ValueError): compile_svg_morph(spec)
    assert js(f'import {{compileSvgMorph}} from {json.dumps(module)};let bad=false;try{{compileSvgMorph({json.dumps(spec)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


@pytest.mark.slow
@pytest.mark.parametrize('source', [GRADIENT,RADIAL],ids=['linear','radial'])
def test_k_actual_canvas_gradient_interior(tmp_path, source):
    plan=compile_svg(source);env=browser_env();project=tmp_path/'k';project.mkdir();shutil.copytree(K,project/'src')
    (project/'package.json').write_text('{"type":"module"}')
    (project/'src/data.js').write_text("export const W=1080,H=1920,FPS=30,DURATION=1,scenes=[{id:'gradient-test',start:0,end:1}];")
    (project/'src/scenes/gradient-test.js').write_text("import {drawSvgArt} from '../lib/svg-canvas.js';\n"+
        'const plan='+json.dumps(plan)+';\n'+
        "export function draw(ctx,t,{W,H}){ctx.fillStyle='#F3F2F1';ctx.fillRect(0,0,W,H);drawSvgArt(ctx,plan,{x:t*50,width:100,height:100});ctx.fillStyle='#0A0A0A';ctx.font='32px sans-serif';ctx.fillText('test',250,400);}\n")
    result=subprocess.run(['node','src/render.js','--jpg','--from','0','--to',str(1/30),'--out',str(tmp_path/'frames')],cwd=project,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    expected=Image.new('RGB',(100,100));draw_svg_art(expected,plan,{'width':100,'height':100})
    with Image.open(tmp_path/'frames/00000.jpg') as im:
        for x in (10,50,90):assert im.convert('RGB').getpixel((x,50))==pytest.approx(expected.getpixel((x,50)),abs=5)
    result=subprocess.run(['node','src/render.js','--audit','--replay','--scale','.25','--from','0','--to','1','--out',str(tmp_path/'audit')],cwd=project,env=env,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    report=json.loads((tmp_path/'audit/report.json').read_text())
    assert report['status']=='pass' and report['replay']['checkedFrames']==30 and report['replay']['failedFrames']==0


@pytest.mark.slow
@pytest.mark.parametrize('source', [GRADIENT,RADIAL],ids=['linear','radial'])
def test_r_actual_gradients_use_unique_instance_ids(tmp_path, source):
    value=os.environ.get('MEDO_REMOTION_TEST_NODE_MODULES')
    if not value: pytest.skip('Set MEDO_REMOTION_TEST_NODE_MODULES for the optional Remotion gradient integration test')
    modules=Path(value).resolve()
    for name in ('@remotion/cli','@remotion/renderer','typescript','react'):
        if not (modules/name).is_dir(): pytest.fail(f'Optional Remotion modules incomplete: {name}')
    env=browser_env();env['REMOTION_BROWSER_EXECUTABLE']=env['MEDO_CHROMIUM']
    project=tmp_path/'r';shutil.copytree(R,project);(project/'node_modules').symlink_to(modules,target_is_directory=True)
    tsconfig=json.loads((project/'tsconfig.json').read_text());tsconfig['include']=['src/Root.tsx','src/index.ts'];(project/'tsconfig.json').write_text(json.dumps(tsconfig))
    plan=compile_svg(source);other=copy.deepcopy(plan);other['shapes'][0]['fill']['stops']=[{'offset':0,'color':'paper'},{'offset':1,'color':'red'}]
    (project/'src/Root.tsx').write_text('''import React from 'react';
import {AbsoluteFill,Composition} from 'remotion';
import {SvgArt,SvgPlan} from './lib/SvgArt';
const a='''+json.dumps(plan)+''' as SvgPlan,b='''+json.dumps(other)+''' as SvgPlan;
const Scene=()=> <AbsoluteFill style={{background:'#F3F2F1'}}><SvgArt plan={a} x={0} y={0} width={100} height={100}/><SvgArt plan={b} x={100} y={0} width={100} height={100}/></AbsoluteFill>;
export const RemotionRoot:React.FC=()=> <Composition id="Gradient" component={Scene} fps={30} durationInFrames={1} width={200} height={100}/>;''')
    for command in (['node','node_modules/typescript/bin/tsc','--noEmit'],['node','scripts/launch-remotion.mjs','still','src/index.ts','Gradient','frame.png','--frame=0','--log=error']):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    a=Image.new('RGB',(100,100));draw_svg_art(a,plan,{'width':100,'height':100})
    b=Image.new('RGB',(100,100));draw_svg_art(b,other,{'width':100,'height':100})
    with Image.open(project/'frame.png') as image:
        im=image.convert('RGB')
        for x in (10,50,90):
            assert im.getpixel((x,50))==pytest.approx(a.getpixel((x,50)),abs=2)
            assert im.getpixel((x+100,50))==pytest.approx(b.getpixel((x,50)),abs=2)


def test_reused_gradient_plans_do_not_share_mutable_fill_objects():
    second=GRADIENT.replace('</svg>', '<rect x="10" y="10" width="20" height="20" fill="url(#shade)" fill-rule="evenodd"/></svg>')
    plan=compile_svg(second)
    plan['shapes'][0]['fill']['stops'][0]['color']='paper'
    assert plan['shapes'][1]['fill']['stops'][0]['color']=='red'


def test_radial_gradient_pixels_and_unsupported_focal_features():
    plan=compile_svg(RADIAL);validate_svg_art(plan)
    assert plan['shapes'][0]['fill']['type']=='radial'
    image=Image.new('RGB',(100,100));draw_svg_art(image,plan,{'width':100,'height':100})
    assert image.getpixel((50,50))==pytest.approx((200,39,27),abs=3)
    assert image.getpixel((0,50))==pytest.approx((12,10,10),abs=3)
    for invalid in (RADIAL.replace('r="50"','r="0"'),RADIAL.replace('r="50"','r="50" fx="10"'),RADIAL.replace('r="50"','r="50" gradientTransform="scale(2)"')):
        with pytest.raises(ValueError): compile_svg(invalid)


def test_gradient_filled_evenodd_hole_is_transparent():
    source=GRADIENT.replace('<rect x="0" y="0" width="100" height="100" style="fill:url(#shade);fill-rule:evenodd"/>',
        '<path d="M0 0H100V100H0Z M30 30H70V70H30Z" fill="url(#shade)" fill-rule="evenodd"/>')
    image=Image.new('RGBA',(100,100),(0,0,0,0));draw_svg_art(image,compile_svg(source),{'width':100,'height':100})
    assert image.getpixel((50,50))[3]==0 and image.getpixel((10,50))[3]==255


@pytest.mark.parametrize('source', [GRADIENT,RADIAL],ids=['linear','radial'])
def test_uniform_gradient_transform_is_baked_and_nonuniform_is_rejected(source):
    plain=compile_svg(source)['shapes'][0]['fill']
    translated=compile_svg(source.replace('<rect x=', '<rect transform="translate(10 20) scale(2)" x='))['shapes'][0]['fill']
    if plain['type']=='linear':
        assert (translated['x1'],translated['y1'],translated['x2'],translated['y2'])==pytest.approx((10,20,210,20))
    else:
        assert (translated['cx'],translated['cy'],translated['r'])==pytest.approx((110,120,100))
    validate_svg_art(compile_svg(source.replace('<rect x=', '<rect transform="rotate(90)" x=')))
    for transform in ('scale(2 1)','skewX(10)','scale(0)'):
        with pytest.raises(ValueError): compile_svg(source.replace('<rect x=', f'<rect transform="{transform}" x='))
