"""Per-contour authored SVG stroke windows across offline engines."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT, SKILL
from PIL import Image
from svg_art import draw_svg_art, svg_stroke_windows
from svg_compile import compile_svg
from test_visual_tools import js

K = SKILL / 'templates/render'
R = SKILL / 'templates/remotion'
SOURCE = '<svg viewBox="0 0 100 100"><path fill="none" stroke="#0A0A0A" stroke-width="4" d="M10 25L90 25 M10 75L90 75"/></svg>'
PLAN = compile_svg(SOURCE)
OPTIONS = {'width': 100, 'height': 100, 'strokeStart': .25, 'progress': .75,
           'strokeWindows': {'svg-0': [None, {'start': .5, 'end': 1}]}}


def resolve_js(options):
    module=(K/'lib/svg-art.js').as_uri()
    return js(f'''import {{svgStrokeWindows}} from {json.dumps(module)};
      const r=svgStrokeWindows({json.dumps(PLAN)},{json.dumps(options)});
      console.log(JSON.stringify({{base:r.base,windows:Object.fromEntries(r.windows)}}));''')


def test_per_contour_windows_and_default_compatibility():
    assert (K/'lib/svg-art.js').read_bytes()==(R/'src/lib/svg-art.js').read_bytes()
    for options in ({}, {'progress': .7}, OPTIONS,
                    {'strokeStart': .2, 'progress': .7, 'strokeOffset': -.25,
                     'strokeWindows': {'svg-0': [{'start': .1, 'end': .9, 'offset': .3}, None]}}):
        assert resolve_js(options)==svg_stroke_windows(PLAN,options)
    assert resolve_js({})['base']=={'start':0,'end':1,'offset':0}


@pytest.mark.parametrize('options', [
    {'progress': -1}, {'progress': 1.1}, {'strokeStart': .8, 'progress': .2},
    {'strokeStart': True}, {'strokeOffset': 1000001}, {'progress': None},
    {'strokeStart': float('nan')}, {'strokeOffset': float('inf')}, {'strokeOffset': 10**400},
    {'strokeWindows': None}, {'strokeWindows': []}, {'strokeWindows': {'unknown': []}},
    {'strokeWindows': {'svg-0': [None]}}, {'strokeWindows': {'svg-0': [None, {}]}},
    {'strokeWindows': {'svg-0': [None, {'start': 0, 'end': 2}]}},
    {'strokeWindows': {'svg-0': [None, {'start': 0, 'end': 1, 'duration': 3}]}},
])
def test_bad_windows_rejected_in_python_and_js(options):
    with pytest.raises(ValueError): svg_stroke_windows(PLAN,options)
    module=(K/'lib/svg-art.js').as_uri()
    assert js(f'import {{svgStrokeWindows}} from {json.dumps(module)};let bad=false;try{{svgStrokeWindows({json.dumps(PLAN)},{json.dumps(options)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def test_p_pixels_and_k_native_segments_show_independent_windows():
    image=Image.new('RGB',(100,100),'#F3F2F1');draw_svg_art(image,PLAN,OPTIONS)
    for x,y,visible in [(20,25,False),(40,25,True),(80,25,False),(20,75,False),(40,75,False),(80,75,True)]:
        assert (image.getpixel((x,y))==(10,10,10))==visible
    module=(K/'lib/svg-canvas.js').as_uri()
    result=js(f'''import {{drawSvgArt}} from {json.dumps(module)};
      const paths=[];let points=[];const ctx={{save(){{}},restore(){{}},translate(){{}},scale(){{}},beginPath(){{points=[]}},
        moveTo(x,y){{points.push([x,y])}},lineTo(x,y){{points.push([x,y])}},stroke(){{paths.push(points)}},globalAlpha:1}};
      drawSvgArt(ctx,{json.dumps(PLAN)},{json.dumps(OPTIONS)});console.log(JSON.stringify(paths));''')
    assert result==[[[30,25],[70,25]],[[50,75],[90,75]]]


def test_offset_wrap_and_zero_window():
    options={'width':100,'height':100,'strokeStart':.25,'progress':.75,'strokeOffset':.5,
             'strokeWindows':{'svg-0':[None,{'start':.3,'end':.3}]}}
    img=Image.new('RGB',(100,100),'#F3F2F1');draw_svg_art(img,PLAN,options)
    for x,visible in [(20,True),(50,False),(80,True)]: assert (img.getpixel((x,25))==(10,10,10))==visible
    assert img.getpixel((50,75))==(243,242,241)


@pytest.mark.slow
def test_r_actual_still_matches_expected_stroke_interiors(tmp_path):
    value=os.environ.get('MEDO_REMOTION_TEST_NODE_MODULES')
    if not value: pytest.skip('Set MEDO_REMOTION_TEST_NODE_MODULES to run the optional Remotion SVG integration test')
    modules=Path(value).resolve()
    for name in ('@remotion/cli','@remotion/renderer','typescript','react'):
        if not (modules/name).is_dir(): pytest.fail(f'Optional Remotion modules incomplete: {name}')
    browser=subprocess.run(['node',str(ROOT/'tools/chromium.mjs'),'--json'],capture_output=True,text=True,timeout=90)
    assert browser.returncode==0,browser.stderr
    config=json.loads(browser.stdout)
    env={**os.environ,'MEDO_CHROMIUM':config['executablePath'],'REMOTION_BROWSER_EXECUTABLE':config['executablePath'],
         'LD_LIBRARY_PATH':(config.get('libraryPath') or '')+':'+os.environ.get('LD_LIBRARY_PATH','')}
    project=tmp_path/'r';shutil.copytree(R,project);(project/'node_modules').symlink_to(modules,target_is_directory=True)
    tsconfig=json.loads((project/'tsconfig.json').read_text());tsconfig['include']=['src/Root.tsx','src/index.ts']
    (project/'tsconfig.json').write_text(json.dumps(tsconfig))
    (project/'src/Root.tsx').write_text('''import React from 'react';
import {AbsoluteFill,Composition} from 'remotion';
import {SvgArt,SvgPlan} from './lib/SvgArt';
const plan='''+json.dumps(PLAN)+''' as SvgPlan;
const Scene=()=> <AbsoluteFill style={{background:'#F3F2F1'}}><SvgArt plan={plan} x={0} y={0} width={100} height={100}
  strokeStart={.25} progress={.75} strokeWindows={{'svg-0':[null,{start:.5,end:1}]}}/></AbsoluteFill>;
export const RemotionRoot:React.FC=()=> <Composition id="StrokeWindows" component={Scene} fps={30} durationInFrames={1} width={100} height={100}/>;''')
    for command in (['node','node_modules/typescript/bin/tsc','--noEmit'],
                    ['node','scripts/launch-remotion.mjs','still','src/index.ts','StrokeWindows','frame.png','--frame=0','--log=error']):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(project/'frame.png') as im:
        for x,y,visible in [(20,25,False),(40,25,True),(80,25,False),(20,75,False),(40,75,False),(80,75,True)]:
            assert (im.convert('RGB').getpixel((x,y))==(10,10,10))==visible


def test_fill_stays_constant_and_legacy_progress_is_unchanged():
    source='<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="#CB271B" fill-rule="evenodd" stroke="#0A0A0A" stroke-width="4"/></svg>'
    plan=compile_svg(source);images=[]
    for options in ({'progress':.5}, {'progress':.5,'strokeStart':0,'strokeOffset':0},
                    {'progress':0,'strokeWindows':{'svg-0':[{'start':.5,'end':.5}]}}):
        image=Image.new('RGB',(100,100),'#F3F2F1')
        draw_svg_art(image,plan,{'width':100,'height':100,**options});images.append(image)
    assert images[0].tobytes()==images[1].tobytes()
    assert all(image.getpixel((50,50))==(203,39,27) for image in images)
    assert images[2].getpixel((50,10))==(203,39,27)


def test_bad_windows_do_not_partially_paint_python_image():
    image=Image.new('RGB',(100,100),'#F3F2F1');before=image.tobytes()
    with pytest.raises(ValueError):
        draw_svg_art(image,PLAN,{'width':100,'height':100,'strokeWindows':{'svg-0':[None,{'start':.8,'end':.3}]}})
    assert image.tobytes()==before


@pytest.mark.slow
def test_k_actual_canvas_still_renders_expected_stroke_interiors(tmp_path):
    toolkit=ROOT/'tools/toolkit'
    if not (toolkit/'node_modules/playwright-core').is_dir(): pytest.skip('K toolkit not installed')
    browser=subprocess.run(['node',str(ROOT/'tools/chromium.mjs'),'--json'],capture_output=True,text=True,timeout=90)
    if browser.returncode: pytest.skip('Chromium unavailable for K')
    config=json.loads(browser.stdout)
    env={**os.environ,'MEDO_TOOLKIT':str(toolkit),'MEDO_CHROMIUM':config['executablePath'],
         'LD_LIBRARY_PATH':(config.get('libraryPath') or '')+':'+os.environ.get('LD_LIBRARY_PATH','')}
    project=tmp_path/'k';project.mkdir();shutil.copytree(K,project/'src')
    (project/'package.json').write_text('{"type":"module"}')
    (project/'src/data.js').write_text("export const W=1080,H=1920,FPS=30,DURATION=1,scenes=[{id:'window-test',start:0,end:1}];")
    (project/'src/scenes/window-test.js').write_text("import {drawSvgArt} from '../lib/svg-canvas.js';\n"+
        'const plan='+json.dumps(PLAN)+';const options='+json.dumps(OPTIONS)+';\n'+
        "export function draw(ctx,t,{W,H}){ctx.fillStyle='#F3F2F1';ctx.fillRect(0,0,W,H);drawSvgArt(ctx,plan,options);}\n")
    result=subprocess.run(['node','src/render.js','--jpg','--from','0','--to',str(1/30),'--out',str(tmp_path/'frames')],
                          cwd=project,env=env,capture_output=True,text=True,timeout=90)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
    with Image.open(tmp_path/'frames/00000.jpg') as image:
        for x,y,visible in [(20,25,False),(40,25,True),(80,25,False),(20,75,False),(40,75,False),(80,75,True)]:
            r,g,b=image.convert('RGB').getpixel((x,y))
            assert (max(r,g,b)<50) if visible else (min(r,g,b)>200)
