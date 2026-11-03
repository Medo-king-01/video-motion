"""Cross-engine deterministic planning without installing a real-time animation runtime."""
from __future__ import annotations

import copy
import importlib
import json
import subprocess
import sys

import pytest
from conftest import ROOT, SKILL
from test_visual_tools import js

P = SKILL / 'templates/procedural-reels'
sys.path.append(str(P))
mp = importlib.import_module('motion_plan')
MODEL = SKILL / 'templates/render/lib/motion-plan.js'


def evaluate(name, args):
    return js(f'import * as m from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(m.{name}(...{json.dumps(args)})));')


def assert_same(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a: assert_same(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True): assert_same(x, y)
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert a == pytest.approx(b, abs=1e-9)
    else:
        assert a == b


@pytest.mark.parametrize('origin', ['first', 'last', 'center', 'edges', 1.5])
def test_stagger_parity_and_order(origin):
    options = dict(each=.1, start=.2, easing='cubicInOut', **{'from': origin})
    result = js(f'import {{staggerTime}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify([0,1,2,3].map(i=>staggerTime(i,4,{json.dumps(options)}))));')
    assert_same(result, [mp.stagger_time(i, 4, options) for i in range(4)])
    if origin == 'center': assert result[1] == result[2] == .2 and result[0] > .2
    if origin == 'edges': assert result[0] == result[3] == .2


@pytest.mark.parametrize('kind', ['loop', 'reverse', 'mirror'])
def test_cycle_boundaries_delay_and_reverse_seek(kind):
    spec = dict(start=.2, duration=.5, repeat=2, repeatDelay=.1, type=kind, easing='cubicIn')
    times = [-1, .2, .45, .7, .75, .8, 1, 1.9, .45]
    result = js(f'import {{cycleValue}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify({json.dumps(times)}.map(t=>cycleValue(0,100,t,{json.dumps(spec)}))));')
    assert_same(result, [mp.cycle_value(0, 100, t, spec) for t in times])
    assert not result[0]['active'] and result[-2]['done']
    assert result[2] == result[-1]
    assert result[3]['value'] == result[4]['value'] == 100


@pytest.mark.parametrize(('a', 'b'), [(0, 10), ([0, 5], [10, 20]), ({'x': 0, 's': [1, 2]}, {'s': [2, 3], 'x': 10}), ('10px', '30px'), ('-5deg', '15deg'), ('2%', '10%')])
def test_mix_structures_and_units(a, b):
    assert_same(evaluate('mixValue', [a, b, .5]), mp.mix_value(a, b, .5))


def plan():
    return dict(version=1, markers={'word': .5}, clips=[
        dict(id='a', track='x', at='word', duration=.5, **{'from': 100, 'to': 300}, easing='cubicInOut'),
        dict(id='b', track='opacity', at='<', duration=.2, **{'from': 0, 'to': 1}),
        dict(id='c', track='x', at={'label': 'word', 'offset': .8}, duration=.3, **{'from': 300, 'to': 400}),
        dict(id='d', track='y', at='>', duration=.3, **{'from': 200, 'to': 500}),
    ])


def test_sequence_markers_tracks_gaps_snapshot_and_parity():
    spec = plan(); before = copy.deepcopy(spec)
    sequence = mp.compile_sequence(spec)
    times = [0, .5, .75, 1.1, 1.4, 1.9, .75]
    result = js(f'import {{compileSequence}} from {json.dumps(MODEL.as_uri())};const s={json.dumps(spec)},seq=compileSequence(s);s.clips[0].to=-200;console.log(JSON.stringify({{duration:seq.duration,frames:{json.dumps(times)}.map(t=>seq.at(t))}}));')
    spec['clips'][0]['to'] = -200
    assert_same(result, dict(duration=sequence.duration, frames=[sequence.at(t) for t in times]))
    assert result['frames'][2] == result['frames'][-1]
    output = sequence.at(.75); output['x'] = 999
    assert sequence.at(.75)['x'] == 200
    assert before['clips'][0]['to'] == 300


@pytest.mark.parametrize('mutation', ['overlap', 'discontinuity', 'missing-marker', 'negative-duration', 'duplicate-id'])
def test_invalid_sequences_fail_in_all_engines(mutation):
    data = plan()
    if mutation == 'overlap': data['clips'][2]['at'] = .7
    if mutation == 'discontinuity': data['clips'][2]['from'] = 99
    if mutation == 'missing-marker': data['clips'][0]['at'] = 'unknown'
    if mutation == 'negative-duration': data['clips'][0]['duration'] = -1
    if mutation == 'duplicate-id': data['clips'][2]['id'] = 'a'
    with pytest.raises(ValueError): mp.compile_sequence(data)
    assert js(f'import {{compileSequence}} from {json.dumps(MODEL.as_uri())};let failed=false;try{{compileSequence({json.dumps(data)})}}catch{{failed=true}}console.log(JSON.stringify(failed));')


@pytest.mark.parametrize('points', [[{'x': 0, 'y': 0}, {'x': 100, 'y': 0}], [{'x': 0, 'y': 0}, {'x': 50, 'y': 100}, {'x': 100, 'y': 0}], [{'x': 0, 'y': 0}, {'x': 30, 'y': 100}, {'x': 60, 'y': -50}, {'x': 100, 'y': 0}]])
def test_bezier_path_and_tangent_parity(points):
    result = js(f'import {{pathAt}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify([0,.25,.5,.75,1].map(t=>pathAt({json.dumps(points)},t))));')
    assert_same(result, [mp.path_at(points, t) for t in [0, .25, .5, .75, 1]])
    assert result[0]['x'] == 0 and result[-1]['x'] == 100


def test_arc_midpoint_and_zero_length_are_safe():
    for a, b in [({'x': 0, 'y': 0}, {'x': 100, 'y': 0}), ({'x': 50, 'y': 30}, {'x': 50, 'y': 30})]:
        assert_same(evaluate('arcAt', [a, b, .5, 40]), mp.arc_at(a, b, .5, 40))
    assert mp.arc_at({'x': 0, 'y': 0}, {'x': 100, 'y': 0}, .5, 40)['y'] == 40


def test_presence_never_extends_scene():
    spec = dict(start=.2, enterEnd=.4, exitStart=1.5, end=1.8, easing='easeOut')
    for t in [0, .2, .3, .7, 1.6, 1.8, .3]:
        assert_same(evaluate('presenceAt', [t, spec]), mp.presence_at(t, spec))
    assert not mp.presence_at(1.8, spec)['active']


def test_k_and_r_ship_identical_sources():
    assert MODEL.read_bytes() == (SKILL / 'templates/remotion/src/lib/motion-plan.js').read_bytes()


@pytest.mark.parametrize(('a', 'b'), [('#CB271B', '#F3F2F1'), ('10px', '10%'), ({'x': 1}, {'y': 2}), (True, 1), ([1], [1, 2])])
def test_invalid_mix_values_rejected(a, b):
    with pytest.raises(ValueError): mp.mix_value(a, b, .5)
    assert js(f'import {{mixValue}} from {json.dumps(MODEL.as_uri())};let failed=false;try{{mixValue({json.dumps(a)},{json.dumps(b)},.5)}}catch{{failed=true}}console.log(JSON.stringify(failed));')


def test_cut_is_explicit_and_preserves_declared_jump():
    data = plan(); data['clips'][2].update({'from': 99, 'cut': True})
    sequence = mp.compile_sequence(data)
    assert sequence.at(1.3)['x'] == 99
    assert_same(evaluate_sequence(data, 1.3), sequence.at(1.3))
    data['clips'][2]['cut'] = 'yes'
    with pytest.raises(ValueError): mp.compile_sequence(data)
    assert js(f'import {{compileSequence}} from {json.dumps(MODEL.as_uri())};let failed=false;try{{compileSequence({json.dumps(data)})}}catch{{failed=true}}console.log(JSON.stringify(failed));')


def evaluate_sequence(data, time):
    return js(f'import {{compileSequence}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(compileSequence({json.dumps(data)}).at({time})));')


def test_rollout_preserves_all_decisions_and_excludes_authoring():
    rollout = json.loads((SKILL / 'motion/rollout.json').read_text())
    states = {item['id']: item['status'] for item in rollout['features']}
    assert set(states) == set(range(1, 45))
    assert states[42] == states[44] == states[27] == 'excluded'
    assert states[39] == 'partial' and states[40] == 'planned'
    assert states[43] == 'requires-review'
    assert states[17] == 'partial' and states[5] == 'complete'


@pytest.mark.slow
def test_plan_fixture_real_frames_and_reverse_replay(tmp_path):
    import shutil
    project = tmp_path / 'project'
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    font_dir = project / 'assets/fonts/Cairo'; font_dir.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', font_dir)
    shutil.copy2(ROOT / 'tests/fixtures/visual/plan-demo.js', project / 'src/plan-demo.js')
    shutil.copy2(ROOT / 'tests/fixtures/visual/plan-scene.js', project / 'src/scenes/plan.js')
    (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=1.8,scenes=[{id:"plan",start:0,end:1.8}];')
    out = tmp_path / 'audit'
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(out), '--replay'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((out / 'report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 54
