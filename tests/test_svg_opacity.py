"""Shape opacity composites fill and stroke together, preserving even-odd holes."""
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
from svg_art import draw_svg_art, validate_svg_art
from svg_compile import compile_svg
from test_gpu_preflight import browser_env
from test_visual_tools import js

K=SKILL/'templates/render';R=SKILL/'templates/remotion'
SOURCE='''<svg viewBox="0 0 100 100"><rect x="20" y="20" width="60" height="60" fill="#CB271B" fill-rule="evenodd" stroke="#0A0A0A" stroke-width="10" opacity="0.5"/></svg>'''
PLAN=compile_svg(SOURCE)


def sample():
    img=Image.new('RGB',(100,100),'#F3F2F1');draw_svg_art(img,PLAN,{'width':100,'height':100});return img


def test_p_shape_opacity_is_applied_after_fill_and_stroke_group():
    img=sample()
    assert img.getpixel((50,50))==pytest.approx((223,140,134),abs=1)
    assert img.getpixel((22,50))==pytest.approx((126,126,125),abs=1)
    assert img.getpixel((5,50))==(243,242,241)
    transparent=Image.new('RGBA',(100,100),(0,0,0,0));draw_svg_art(transparent,PLAN,{'width':100,'height':100})
    assert transparent.getpixel((50,50))[3]==transparent.getpixel((22,50))[3]==128


def test_inline_opacity_overrides_attribute_and_morph_is_static():
    plan=compile_svg(SOURCE.replace('opacity="0.5"','opacity="0.2" style="opacity:0.75"'))
    assert plan['shapes'][0]['opacity']==.75
    svg_art=(K/'lib/svg-art.js').as_uri()
    assert js(f'import {{validateSvgArt}} from {json.dumps(svg_art)};console.log(JSON.stringify(validateSvgArt({json.dumps(plan)}).shapes[0].opacity));')==.75


@pytest.mark.parametrize('opacity', ['-0.1','1.01','nan','1%'])
def test_invalid_shape_opacity_rejected(opacity):
    with pytest.raises(ValueError): compile_svg(SOURCE.replace('opacity="0.5"',f'opacity="{opacity}"'))


def test_invalid_plan_opacity_rejected_in_both_backends():
    plan=copy.deepcopy(PLAN);plan['shapes'][0]['opacity']=1.1
    with pytest.raises(ValueError): validate_svg_art(plan)
    svg_art=(K/'lib/svg-art.js').as_uri()
    assert js(f'import {{validateSvgArt}} from {json.dumps(svg_art)};let rejected=false;try{{validateSvgArt({json.dumps(plan)})}}catch{{rejected=true}}console.log(JSON.stringify(rejected));')


@pytest.mark.slow
def test_actual_k_shape_opacity_pixel_and_reverse(tmp_path):
    env=browser_env();project=tmp_path/'k';project.mkdir();shutil.copytree(K,project/'src')
    (project/'package.json').write_text('{"type":"module"}')
    (project/'src/data.js').write_text("export const W=1080,H=1920,FPS=30,DURATION=1,scenes=[{id:'opacity-test',start:0,end:1}];")
    (project/'src/scenes/opacity-test.js').write_text("import {drawSvgArt} from '../lib/svg-canvas.js';\n"+
        'const plan='+json.dumps(PLAN)+';\n'+
        "export function draw(ctx,t,{W,H}){ctx.fillStyle='#F3F2F1';ctx.fillRect(0,0,W,H);drawSvgArt(ctx,plan,{x:t*40,width:100,height:100});ctx.fillStyle='#0A0A0A';ctx.font='32px sans-serif';ctx.fillText('test',250,400);}\n")
    result=subprocess.run(['node','src/render.js','--jpg','--from','0','--to',str(1/30),'--out',str(tmp_path/'frames')],cwd=project,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(tmp_path/'frames/00000.jpg') as im:
        for x in (5,22,50): assert im.convert('RGB').getpixel((x,50))==pytest.approx(sample().getpixel((x,50)),abs=5)
    result=subprocess.run(['node','src/render.js','--audit','--replay','--scale','.25','--from','0','--to','1','--out',str(tmp_path/'audit')],cwd=project,env=env,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    report=json.loads((tmp_path/'audit/report.json').read_text());assert report['status']=='pass' and report['replay']['checkedFrames']==30 and report['replay']['failedFrames']==0


@pytest.mark.slow
def test_actual_r_shape_opacity_pixel(tmp_path):
    value=os.environ.get('MEDO_REMOTION_TEST_NODE_MODULES')
    if not value: pytest.skip('Set MEDO_REMOTION_TEST_NODE_MODULES for optional Remotion opacity integration')
    modules=Path(value).resolve()
    for name in ('@remotion/cli','@remotion/renderer','typescript','react'):
        if not (modules/name).is_dir(): pytest.fail(f'Optional Remotion modules incomplete: {name}')
    env=browser_env();env['REMOTION_BROWSER_EXECUTABLE']=env['MEDO_CHROMIUM']
    project=tmp_path/'r';shutil.copytree(R,project);(project/'node_modules').symlink_to(modules,target_is_directory=True)
    tsconfig=json.loads((project/'tsconfig.json').read_text());tsconfig['include']=['src/Root.tsx','src/index.ts'];(project/'tsconfig.json').write_text(json.dumps(tsconfig))
    (project/'src/Root.tsx').write_text('''import React from 'react';
import {AbsoluteFill,Composition} from 'remotion';
import {SvgArt,SvgPlan} from './lib/SvgArt';
const plan='''+json.dumps(PLAN)+''' as SvgPlan;
const Scene=()=> <AbsoluteFill style={{background:'#F3F2F1'}}><SvgArt plan={plan} x={0} y={0} width={100} height={100}/></AbsoluteFill>;
export const RemotionRoot:React.FC=()=> <Composition id="Opacity" component={Scene} fps={30} durationInFrames={1} width={100} height={100}/>;''')
    for command in (['node','node_modules/typescript/bin/tsc','--noEmit'],['node','scripts/launch-remotion.mjs','still','src/index.ts','Opacity','frame.png','--frame=0','--log=error']):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(project/'frame.png') as im:
        for x in (5,22,50): assert im.convert('RGB').getpixel((x,50))==pytest.approx(sample().getpixel((x,50)),abs=2)


def test_partial_opacity_with_gradient_and_zero_opacity():
    from test_svg_gradient import RADIAL

    partial=compile_svg(RADIAL.replace('width="100" height="100" style=', 'width="100" height="100" opacity="0.5" style='))
    image=Image.new('RGBA',(100,100),(0,0,0,0));draw_svg_art(image,partial,{'width':100,'height':100})
    assert image.getpixel((50,50))[3]==128
    invisible=compile_svg(SOURCE.replace('opacity="0.5"','opacity="0"'))
    blank=Image.new('RGBA',(100,100),(0,0,0,0));draw_svg_art(blank,invisible,{'width':100,'height':100})
    assert blank.getbbox() is None


def test_partial_opacity_budget_and_unsafe_canvas_context_fail_before_paint():
    oversized=Image.new('RGB',(2049,2048),'white')
    with pytest.raises(ValueError,match='bounded image'): draw_svg_art(oversized,PLAN,{'width':100,'height':100})
    assert oversized.getpixel((50,50))==(255,255,255)
    module=(K/'lib/svg-canvas.js').as_uri()
    result=js(f'''import {{drawSvgArt}} from {json.dumps(module)};
let painted=false, restored=false;
const ctx={{canvas:{{width:2049,height:2048}},globalCompositeOperation:'source-over',filter:'none',shadowColor:'rgba(0, 0, 0, 0)',
 save(){{}},restore(){{restored=true}},translate(){{}},scale(){{}},getTransform(){{return {{is2D:true,a:1,b:0,c:0,d:1,e:0,f:0}}}},
 beginPath(){{painted=true}}}};
let rejected=false;try{{drawSvgArt(ctx,{json.dumps(PLAN)},{{width:100,height:100}})}}catch(e){{rejected=true}}
console.log(JSON.stringify({{painted,restored,rejected}}));''')
    assert result=={'painted':False,'restored':True,'rejected':True}
