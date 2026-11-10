"""Nested offline timelines and conservatively validated SVG ring morphs."""
from __future__ import annotations

import copy
import json

import pytest
from conftest import SKILL
from motion_plan import compile_nested_sequence
from svg_compile import compile_svg
from svg_morph import compile_svg_morph
from test_motion_plan import assert_same
from test_visual_tools import js

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

NESTED = SKILL / 'templates/render/lib/motion-plan.js'
MORPH = SKILL / 'templates/render/lib/svg-morph.js'


def nested():
    return {'version': 1, 'markers': {'intro': .4}, 'items': [
        {'id': 'lead', 'track': 'opacity', 'at': 0, 'duration': .4, 'from': 0, 'to': 1},
        {'id': 'group', 'at': 'intro', 'sequence': {'version': 1, 'markers': {'start': .1}, 'items': [
            {'id': 'slide', 'track': 'x', 'at': 'start', 'duration': .5, 'from': 0, 'to': 100},
            {'id': 'sub', 'at': '>', 'sequence': {'version': 1, 'items': [
                {'id': 'rise', 'track': 'y', 'at': 0, 'duration': .2, 'from': 0, 'to': 50}]}},
            {'id': 'rest', 'track': 'x', 'at': '>', 'duration': .2, 'from': 100, 'to': 120}]}},
        {'id': 'out', 'track': 'opacity', 'at': '>', 'duration': .2, 'from': 1, 'to': 0}]}


def pair():
    one = '<svg viewBox="0 0 300 300"><path fill="#CB271B" stroke="#0A0A0A" fill-rule="evenodd" d="M50 50H250V250H50Z M110 110H190V190H110Z"/></svg>'
    two = '<svg viewBox="0 0 300 300"><path fill="#CB271B" stroke="#0A0A0A" fill-rule="evenodd" d="M40 70H260V230H40Z M100 120H200V180H100Z"/></svg>'
    return {'version': 1, 'from': compile_svg(one), 'to': compile_svg(two), 'count': 24}


def javascript_samples(module, func, spec, times):
    return js(f'import {{{func}}} from {json.dumps(module.as_uri())};const plan={func}({json.dumps(spec)});console.log(JSON.stringify({{duration:plan.duration??null,frames:{json.dumps(times)}.map(t=>plan.at(t))}}));')


def rejects_js(module, func, spec):
    return js(f'import {{{func}}} from {json.dumps(module.as_uri())};let rejected=false;try{{{func}({json.dumps(spec)})}}catch{{rejected=true}}console.log(JSON.stringify(rejected));')


def test_nested_sequence_timing_namespaces_parity_and_seek():
    spec = nested(); plan = compile_nested_sequence(spec); times = [-1,0,.4,.5,.75,1.0,1.3,1.5,3,.75]
    result = javascript_samples(NESTED, 'compileNestedSequence', spec, times)
    assert result['duration'] == pytest.approx(1.6)
    assert_same(result['frames'], [plan.at(t) for t in times])
    assert plan.at(.75)['group/x'] == pytest.approx(50)
    assert plan.at(1.1)['group/sub/y'] == pytest.approx(25)
    assert plan.at(1.5)['opacity'] == pytest.approx(.5)
    before = plan.at(.75); spec['items'][1]['sequence']['items'][0]['to'] = 999
    assert plan.at(.75) == before


@pytest.mark.parametrize('mutation', ['duplicate', 'slash', 'missing_marker', 'overlap', 'mixed_child', 'bad_version', 'empty', 'null_markers'])
def test_nested_rejects_ambiguous_or_invalid_inputs(mutation):
    spec = nested()
    if mutation == 'duplicate': spec['items'][1]['id'] = 'lead'
    if mutation == 'slash': spec['items'][1]['id'] = 'group/other'
    if mutation == 'missing_marker': spec['items'][1]['at'] = 'absent'
    if mutation == 'overlap': spec['items'][-1]['at'] = .1
    if mutation == 'mixed_child': spec['items'][1]['duration'] = 1
    if mutation == 'bad_version': spec['items'][1]['sequence']['version'] = 2
    if mutation == 'empty': spec['items'][1]['sequence']['items'] = []
    if mutation == 'null_markers': spec['items'][1]['sequence']['markers'] = None
    with pytest.raises(ValueError): compile_nested_sequence(spec)
    assert rejects_js(NESTED, 'compileNestedSequence', spec)


def test_nested_rejects_cycles_and_excessive_depth():
    cyc = {'version': 1, 'items': []}; cyc['items'].append({'id': 'x', 'at': 0, 'sequence': cyc})
    with pytest.raises(ValueError): compile_nested_sequence(cyc)
    code = f'''import {{compileNestedSequence}} from {json.dumps(NESTED.as_uri())};const x={{version:1,items:[]}};x.items.push({{id:'x',at:0,sequence:x}});let bad=false;try{{compileNestedSequence(x)}}catch{{bad=true}}console.log(JSON.stringify(bad));'''
    assert js(code)
    deep = nested()
    for _ in range(9): deep = {'version': 1, 'items': [{'id': 'a', 'at': 0, 'sequence': deep}]}
    with pytest.raises(ValueError): compile_nested_sequence(deep)
    assert rejects_js(NESTED, 'compileNestedSequence', deep)


def test_svg_morph_hole_parity_immutability_and_reverse_seek():
    spec = pair(); plan = compile_svg_morph(spec); times = [-1,0,.25,.5,.75,1,2,.5]
    result = javascript_samples(MORPH, 'compileSvgMorph', spec, times)
    assert_same(result['frames'], [plan.at(t) for t in times])
    for frame in result['frames']:
        assert len(frame['shapes'][0]['contours']) == 2
        assert all(c['closed'] and len(c['points']) == 24 for c in frame['shapes'][0]['contours'])
    before = plan.at(.5); spec['from']['shapes'][0]['contours'][0]['points'][0]['x'] = 999
    plan.at(.5)['shapes'][0]['contours'][0]['points'][0]['x'] = 999
    assert plan.at(.5) == before


@pytest.mark.parametrize('mutation', ['viewbox', 'paint', 'contours', 'open', 'budget', 'outside', 'bowtie', 'null_count'])
def test_svg_morph_rejects_incompatible_or_unprovable_geometry(mutation):
    spec = pair(); target = spec['to']
    if mutation == 'viewbox': target['viewBox'][2] = 400
    if mutation == 'paint': target['shapes'][0]['fill'] = 'gray1'
    if mutation == 'contours': target['shapes'][0]['contours'].pop()
    if mutation == 'open': target['shapes'][0]['contours'][0]['closed'] = False
    if mutation == 'budget': spec['count'] = 65
    if mutation == 'null_count': spec['count'] = None
    if mutation == 'outside':
        for p in target['shapes'][0]['contours'][1]['points']: p['x'] += 250
    if mutation == 'bowtie':
        target['shapes'][0]['contours'][0]['points'] = [{'x':40,'y':70},{'x':260,'y':230},{'x':40,'y':230},{'x':260,'y':70}]
    with pytest.raises(ValueError): compile_svg_morph(spec)
    assert rejects_js(MORPH, 'compileSvgMorph', spec)


def test_svg_morph_rejects_holes_swapping_between_valid_endpoints():
    source = '<svg viewBox="0 0 300 300"><path fill="#CB271B" fill-rule="evenodd" d="M10 10H290V290H10Z M40 100H90V150H40Z M210 100H260V150H210Z"/></svg>'
    a = compile_svg(source); b = copy.deepcopy(a)
    b['shapes'][0]['contours'][1], b['shapes'][0]['contours'][2] = b['shapes'][0]['contours'][2], b['shapes'][0]['contours'][1]
    spec = {'version': 1, 'from': a, 'to': b, 'count': 16}
    with pytest.raises(ValueError): compile_svg_morph(spec)
    assert rejects_js(MORPH, 'compileSvgMorph', spec)


def test_new_js_models_match_between_k_and_r():
    for name in ['svg-morph.js', 'motion-plan.js']:
        assert (SKILL / 'templates/render/lib' / name).read_bytes() == (SKILL / 'templates/remotion/src/lib' / name).read_bytes()


def test_morph_draw_preserves_hole_in_intermediate_p_frame():
    from PIL import Image
    from svg_art import draw_svg_art
    plan = compile_svg_morph(pair())
    for progress in [0, .25, .5, .75, 1]:
        image = Image.new('RGB', (300, 300), '#F3F2F1')
        draw_svg_art(image, plan.at(progress), {'x': 0, 'y': 0, 'width': 300, 'height': 300})
        assert image.getpixel((150, 150)) == (243,242,241)
        assert image.getpixel((75, 150)) == (203,39,27)


def test_svg_morph_rejects_degenerate_shapes_at_input():
    spec = pair()
    ring = spec['from']['shapes'][0]['contours'][0]
    ring['points'] = [{'x':10,'y':10},{'x':10,'y':10},{'x':10,'y':10}]
    with pytest.raises(ValueError): compile_svg_morph(spec)
    assert rejects_js(MORPH, 'compileSvgMorph', spec)


def test_morph_and_nested_reject_nonfinite_sample_times():
    with pytest.raises(ValueError): compile_svg_morph(pair()).at(float('nan'))
    with pytest.raises(ValueError): compile_nested_sequence(nested()).at(float('inf'))


@pytest.mark.slow
def test_real_nested_svg_morph_reverse_replay(tmp_path):
    import shutil
    import subprocess

    from conftest import ROOT

    project = tmp_path / 'project'
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    fonts = project / 'assets/fonts/Cairo'; fonts.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', fonts)
    source = compile_svg((ROOT / 'tests/fixtures/visual/morph-from.svg').read_text())
    target = compile_svg((ROOT / 'tests/fixtures/visual/morph-to.svg').read_text())
    (project / 'src/morph-plans.js').write_text('export const FROM='+json.dumps(source)+';export const TO='+json.dumps(target)+';')
    shutil.copy2(ROOT / 'tests/fixtures/visual/morph-demo.js', project / 'src/morph-demo.js')
    shutil.copy2(ROOT / 'tests/fixtures/visual/morph-scene.js', project / 'src/scenes/morph.js')
    (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2.4,scenes=[{id:"morph",start:0,end:2.4}];')
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(tmp_path / 'audit'), '--replay'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout+result.stderr
    report = json.loads((tmp_path / 'audit/report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 72


def test_nested_floating_point_shared_boundary_and_true_overlap():
    spec = {'version': 1, 'items': [{'id': 'g', 'at': .1, 'sequence': {'version': 1, 'items': [
        {'id': 'a', 'track': 'x', 'at': .1, 'duration': .6, 'from': 0, 'to': 1},
        {'id': 'b', 'track': 'x', 'at': '>', 'duration': .2, 'from': 1, 'to': 2}]}}]}
    plan = compile_nested_sequence(spec); times = [.2, .8, .9, 1]
    assert_same(javascript_samples(NESTED, 'compileNestedSequence', spec, times)['frames'], [plan.at(t) for t in times])
    spec['items'][0]['sequence']['items'][1]['at'] = .699999
    with pytest.raises(ValueError): compile_nested_sequence(spec)
    assert rejects_js(NESTED, 'compileNestedSequence', spec)


def test_phase_five_rollout_preserves_scope_and_exclusions():
    data = json.loads((SKILL / 'motion/rollout.json').read_text())
    by_id = {item['id']: item for item in data['features']}
    assert data['phase'] >= 5
    assert by_id[7]['status'] == by_id[23]['status'] == 'partial'
    assert 'nested' in by_id[7]['scope'] and 'multi-contour' in by_id[23]['scope']
    assert by_id[27]['status'] == by_id[42]['status'] == 'excluded'


def test_nested_authored_time_scaling_parity_and_relative_end():
    original = nested(); scaled = copy.deepcopy(original); scaled['items'][1]['timeScale'] = 2
    a, b = compile_nested_sequence(original), compile_nested_sequence(scaled)
    assert b.duration == pytest.approx(2.6)
    for t in [0, .1, .35, .6, .75, 1, .35]:
        for key in ('group/x', 'group/sub/y'):
            assert b.at(.4+2*t)[key] == pytest.approx(a.at(.4+t)[key])
    times = [0, .6, 1.1, 1.6, 2.4, 2.5, 2.6, 1.1]
    assert_same(javascript_samples(NESTED, 'compileNestedSequence', scaled, times)['frames'], [b.at(t) for t in times])
    scaled['items'][1]['sequence']['items'][1]['timeScale'] = .5
    plan = compile_nested_sequence(scaled)
    assert plan.at(1.7)['group/sub/y'] == pytest.approx(25)
    assert plan.duration == pytest.approx(2.4)
    assert_same(javascript_samples(NESTED, 'compileNestedSequence', scaled, times)['frames'], [plan.at(t) for t in times])


@pytest.mark.parametrize('bad', [0, -1, .009, 101, None, True, float('inf')])
def test_nested_invalid_time_scale_rejected(bad):
    spec=nested();spec['items'][1]['timeScale']=bad
    with pytest.raises(ValueError): compile_nested_sequence(spec)
    assert rejects_js(NESTED, 'compileNestedSequence', spec)


def test_nested_scale_is_only_for_sequences_and_rejects_underflow():
    spec=nested();spec['items'][0]['timeScale']=2
    with pytest.raises(ValueError): compile_nested_sequence(spec)
    assert rejects_js(NESTED, 'compileNestedSequence', spec)
    spec={'version':1,'items':[{'id':'a','at':0,'timeScale':.01,'sequence':{'version':1,'items':[
        {'id':'b','track':'x','at':0,'duration':1e-8,'from':0,'to':1}]}}]}
    with pytest.raises(ValueError): compile_nested_sequence(spec)
    assert rejects_js(NESTED, 'compileNestedSequence', spec)


def test_morph_explicit_ids_allow_safe_reordering_with_swept_bounds():
    one='''<svg viewBox="0 0 100 100"><rect id="left" x="5" y="10" width="20" height="20" fill="#CB271B" fill-rule="evenodd"/><rect id="right" x="75" y="10" width="20" height="20" fill="#D8D7D5" fill-rule="evenodd"/></svg>'''
    two='''<svg viewBox="0 0 100 100"><rect id="right" x="70" y="12" width="20" height="20" fill="#D8D7D5" fill-rule="evenodd"/><rect id="left" x="10" y="12" width="20" height="20" fill="#CB271B" fill-rule="evenodd"/></svg>'''
    spec={'version':1,'from':compile_svg(one,preserve_ids=True),'to':compile_svg(two,preserve_ids=True),'count':8}
    with pytest.raises(ValueError): compile_svg_morph(spec)
    assert rejects_js(MORPH,'compileSvgMorph',spec)
    spec['matchById']=True
    py=compile_svg_morph(spec);times=[0,.25,.5,.75,1]
    j=javascript_samples(MORPH,'compileSvgMorph',spec,times)
    assert_same([py.at(t) for t in times],j['frames'])
    assert [s['id'] for s in py.at(1)['shapes']]==['left','right']
    overlapping=copy.deepcopy(spec)
    for p in overlapping['to']['shapes'][0]['contours'][0]['points']: p['x']-=55
    with pytest.raises(ValueError,match='bounds overlap'): compile_svg_morph(overlapping)
    assert rejects_js(MORPH,'compileSvgMorph',overlapping)
    missing=copy.deepcopy(spec);missing['to']['shapes'][0]['id']='missing'
    with pytest.raises(ValueError): compile_svg_morph(missing)
    assert rejects_js(MORPH,'compileSvgMorph',missing)
    for invalid in (None,1,'true'):
        wrong=copy.deepcopy(spec);wrong['matchById']=invalid
        with pytest.raises(ValueError): compile_svg_morph(wrong)
        assert rejects_js(MORPH,'compileSvgMorph',wrong)
