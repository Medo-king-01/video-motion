"""Optional React/Remotion Three adapter: ownership and actual frame sampling."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import ROOT, SKILL
from PIL import Image, ImageChops
from test_visual_tools import js

R = SKILL/'templates/remotion'
K = SKILL/'templates/render'


def test_three_helper_is_identical_to_k():
    assert (R/'src/lib/three-layer.js').read_bytes() == (K/'lib/three-layer.js').read_bytes()


def test_sync_scope_lifo_idempotent_reentrant_and_errors():
    module=(R/'src/lib/sync-resource-scope.js').as_uri()
    result=js(f'''import {{createSyncResourceScope}} from {json.dumps(module)};
      const scope=createSyncResourceScope(),log=[];
      scope.defer(()=>log.push('first'));
      scope.defer(()=>{{log.push('broken');throw Error('bad')}});
      scope.defer(()=>{{log.push('last');scope.close()}});
      let errors=0;try{{scope.close()}}catch(e){{errors=e.errors.length}}scope.close();
      let closedReject=false;try{{scope.defer(()=>{{}})}}catch{{closedReject=true}}
      const asyncScope=createSyncResourceScope();asyncScope.defer(()=>Promise.resolve());let asyncReject=false;
      try{{asyncScope.close()}}catch(e){{asyncReject=e.errors.length===1}}
      console.log(JSON.stringify({{log,errors,closedReject,asyncReject,closed:scope.closed}}));''')
    assert result == {'log':['last','broken','first'],'errors':1,'closedReject':True,'asyncReject':True,'closed':True}


@pytest.fixture
def r_project(tmp_path):
    value=os.environ.get('MEDO_REMOTION_TEST_NODE_MODULES')
    if not value: pytest.skip('Set MEDO_REMOTION_TEST_NODE_MODULES to a prepared optional Remotion + Three node_modules')
    modules=Path(value).resolve()
    for name in ('three','@remotion/cli','@remotion/renderer','typescript','react','esbuild'):
        if not (modules/name).is_dir(): pytest.fail(f'Optional test modules incomplete: {name}')
    browser=subprocess.run(['node',str(ROOT/'tools/chromium.mjs'),'--json'],capture_output=True,text=True,timeout=90)
    if browser.returncode: pytest.fail('Chromium unavailable for explicitly requested R Three test')
    config=json.loads(browser.stdout);proj=tmp_path/'r';shutil.copytree(R,proj)
    (proj/'node_modules').symlink_to(modules,target_is_directory=True)
    for name,dest in [('ThreeReview.tsx','Root.tsx'),('three-r-scene.js','three-r-scene.js'),('three-r-harness.tsx','three-r-harness.tsx')]:
        shutil.copy2(ROOT/'tests/fixtures/visual'/name,proj/'src'/dest)
    tsc=json.loads((proj/'tsconfig.json').read_text());tsc['include']=['src/Root.tsx','src/index.ts','src/lib/useScopedEffect.ts'];(proj/'tsconfig.json').write_text(json.dumps(tsc))
    env={**os.environ,'MEDO_TOOLKIT':str(ROOT/'tools/toolkit'),'MEDO_CHROMIUM':config['executablePath'],
         'REMOTION_BROWSER_EXECUTABLE':config['executablePath'],
         'LD_LIBRARY_PATH':(config.get('libraryPath') or '')+':'+os.environ.get('LD_LIBRARY_PATH','')}
    return proj,env


@pytest.mark.slow
def test_three_component_actual_react_reverse_and_remotion_stills(r_project):
    project,env=r_project
    def run(command):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
        return result.stdout
    run(['node','node_modules/typescript/bin/tsc','--noEmit'])
    run(['node','node_modules/esbuild/bin/esbuild','src/three-r-harness.tsx','--bundle','--format=iife','--platform=browser','--outfile=harness.js'])
    report=json.loads(run(['node',str(ROOT/'tests/fixtures/visual/three-r-replay.mjs'),'harness.js']))
    assert {k:report[k] for k in ('frames','reverseMatches','distinct','cleanups','reducedMatchesStart','reducedDifferent')}=={'frames':30,'reverseMatches':30,'distinct':True,'cleanups':16,'reducedMatchesStart':True,'reducedDifferent':True}
    assert report['failure']['caught'] and report['failure']['attempts']>0
    assert report['failure']['disposed']==8*report['failure']['attempts']
    assert report['scopedEffect']==['init-a','last-a','first-a','init-b','last-b','first-b']
    assert {item['kind'] for item in report['scopedFailure']}=={'sync','async'}
    assert all(item['caught'] and item['attempts']>0 and item['disposed']==item['attempts'] for item in report['scopedFailure'])
    launcher=['node','scripts/launch-remotion.mjs','still','src/index.ts','ThreeReview']
    for filename,frame,props in [('f15.png',15,[]),('f00.png',0,[]),('f15again.png',15,[]),('reduced.png',15,['--props={"motionMode":"reduced"}'])]:
        run([*launcher,filename,f'--frame={frame}','--log=error',*props])
    def pixels(name): return Image.open(project/name).convert('RGB')
    assert ImageChops.difference(pixels('f15.png'),pixels('f15again.png')).getbbox() is None
    assert ImageChops.difference(pixels('f00.png'),pixels('reduced.png')).getbbox() is None
    assert ImageChops.difference(pixels('f15.png'),pixels('reduced.png')).getbbox() is not None
    assert max(pixels('f15.png').getpixel((190,570)))<12
    assert max(pixels('f15.png').getpixel((540,900)))>40


@pytest.mark.slow
def test_three_arabic_directed_fact_gate_preserved_in_both_modes(r_project):
    project,env=r_project
    shutil.copy2(ROOT/'tests/fixtures/visual/ThreeArabicReview.tsx',project/'src/Root.tsx')
    font_dir=project/'public/fonts/Cairo';font_dir.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'assets/fonts/Cairo/Cairo_800ExtraBold.ttf',font_dir)
    def run(command):
        result=subprocess.run(command,cwd=project,env=env,capture_output=True,text=True,timeout=180)
        assert result.returncode==0,result.stdout+'\n'+result.stderr
    run(['node','node_modules/typescript/bin/tsc','--noEmit'])
    launcher=['node','scripts/launch-remotion.mjs','still','src/index.ts','ThreeArabicGate']
    for frame in (14,25):
        for mode in ('normal','reduced'):
            run([*launcher,f'{frame}-{mode}.png',f'--frame={frame}',f'--props={{"motionMode":"{mode}"}}','--log=error'])
    def crop(frame,mode):
        with Image.open(project/f'{frame}-{mode}.png') as img:
            return img.convert('RGB').crop((90,1360,990,1600))
    for frame in (14,25):
        assert ImageChops.difference(crop(frame,'normal'),crop(frame,'reduced')).getbbox() is None
    # The gated area is the flat background before the anchor and contains text after it.
    before=crop(14,'normal');after=crop(25,'normal')
    assert before.getextrema()==((3,3),(3,3),(3,3))
    assert max(channel[1] for channel in after.getextrema())>100
