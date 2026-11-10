"""Offline physics/event/state graphs: mathematical invariants, P/K/R parity and replay."""
from __future__ import annotations

import importlib
import json
import math
import shutil
import subprocess
from decimal import Inexact, localcontext

import pytest
from conftest import ROOT, SKILL
from test_motion_plan import assert_same
from test_visual_tools import js

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

ms = importlib.import_module('motion_state')
MODEL = SKILL / 'templates/render/lib/motion-state.js'
TIMES = [-.2, 0, .05, .2, .4, .6, .85, 1.2, 2, 10, .2]


def samples(name, spec, times=TIMES):
    return js(f'import * as m from {json.dumps(MODEL.as_uri())};const p=m.{name}({json.dumps(spec)});console.log(JSON.stringify({json.dumps(times)}.map(t=>p.at(t))));')


def rejects(name, spec):
    assert js(f'import * as m from {json.dumps(MODEL.as_uri())};let bad=false;try{{m.{name}({json.dumps(spec)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def retarget():
    return {'version': 1, 'initial': 10, 'velocity': 4, 'physics': {'stiffness': 170, 'damping': 16},
            'events': [{'at': .1, 'target': 200}, {'at': .6, 'target': -40}, {'at': 1.2, 'target': 80}]}


def variants(order='beforeChildren'):
    return {'version': 1, 'root': {'id': 'panel', 'initial': 'off', 'variants': {'off': {'y': 20}, 'on': {'y': 0}},
            'children': [{'id': f'card{i}', 'variants': {'off': {'x': 0, 'y': 100}, 'on': {'x': 40, 'y': 0}}} for i in range(3)]},
            'events': [{'at': .1, 'label': 'on', 'duration': .2, 'stagger': .05, 'order': order},
                       {'at': 1.4, 'label': 'off', 'duration': .15, 'order': 'afterChildren', 'easing': 'cubicInOut'}]}


def values():
    return {'version': 1, 'sequence': {'version': 1, 'clips': [{'id': 'x', 'track': 'x', 'at': .1, 'duration': 1, 'from': 0, 'to': 100}]},
            'constants': {'factor': 2}, 'nodes': [
                {'id': 'caption', 'op': 'template', 'parts': ['x=', {'input': 'x'}, '; p=', {'input': 'progress'}]},
                {'id': 'progress', 'op': 'map', 'input': 'x', 'range': [0, 100], 'output': [0, 1]},
                {'id': 'size', 'op': 'mix', 'input': 'progress', 'from': {'width': 140}, 'to': {'width': 420}},
                {'id': 'doubled', 'op': 'multiply', 'inputs': ['x', 'factor']},
                {'id': 'sum', 'op': 'add', 'inputs': ['x', 'doubled']},
                {'id': 'speed', 'op': 'velocity', 'input': 'sum', 'step': .001}]}


@pytest.mark.parametrize('damping', [0, 8, 20, 40, 200])
def test_closed_form_spring_parity_and_derivative(damping):
    options = {'stiffness': 100, 'damping': damping, 'mass': 1, 'velocity': 17}
    actual = js(f'import {{springState}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify({json.dumps(TIMES)}.map(t=>springState(-20,80,t,{json.dumps(options)}))));')
    assert_same(actual, [ms.spring_state(-20, 80, t, options) for t in TIMES])
    assert ms.spring_state(-20, 80, 0, options) == {'value': -20, 'velocity': 17}
    t, h = .27, 1e-6
    central = (ms.spring_state(-20, 80, t+h, options)['value']-ms.spring_state(-20, 80, t-h, options)['value'])/(2*h)
    assert central == pytest.approx(ms.spring_state(-20, 80, t, options)['velocity'], rel=1e-7)
    if damping > 0: assert ms.spring_state(-20, 80, 100, options)['value'] == pytest.approx(80, abs=1e-6)


@pytest.mark.parametrize('bounce', [0, .2, .5, .8])
def test_duration_spring_lands_c1_with_preserved_initial_velocity(bounce):
    options = {'duration': .65, 'bounce': bounce, 'velocity': -35}
    times = [-1, 0, .1, .4, .65-1e-7, .65, 10]
    actual = js(f'import {{durationSpring}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify({json.dumps(times)}.map(t=>durationSpring(100,400,t,{json.dumps(options)}))));')
    assert_same(actual, [ms.duration_spring(100, 400, t, options) for t in times])
    assert actual[1]['velocity'] == -35 and actual[-1] == {'value': 400, 'velocity': 0}
    assert abs(actual[-3]['velocity']) < .01
    h, t = 1e-6, .3
    derivative = (ms.duration_spring(100, 400, t+h, options)['value']-ms.duration_spring(100, 400, t-h, options)['value'])/(2*h)
    assert derivative == pytest.approx(ms.duration_spring(100, 400, t, options)['velocity'], rel=1e-7)


@pytest.mark.parametrize('spec', [
    {'from': 10, 'velocity': 400}, {'from': 90, 'velocity': -900, 'min': 0, 'max': 100},
    {'from': 10, 'velocity': 900, 'min': 0, 'max': 100, 'snap': [0, 50, 100]},
    {'from': 10, 'velocity': 0, 'snap': [0, 20]},
])
def test_inertia_decay_bounds_snap_terminal_and_snapshot(spec):
    sampler = ms.compile_inertia(spec)
    times = sorted(set([*TIMES, sampler.duration, .6-1e-8, .6]))
    assert_same(samples('compileInertia', spec, times), [sampler.at(t) for t in times])
    natural = spec['from']+spec['velocity']*.35*(1-math.exp(-.1/.35))
    expected = min(spec.get('max', math.inf), max(spec.get('min', -math.inf), natural))
    assert sampler.at(.1)['value'] == pytest.approx(expected)
    assert sampler.at(sampler.duration+1)['value'] == sampler.target
    assert sampler.at(sampler.duration+1)['velocity'] == 0
    if 'min' in spec:
        assert all(spec['min'] <= sampler.at(i/300)['value'] <= spec['max'] for i in range(500))
    before = sampler.at(.3); spec['velocity'] = 999
    assert sampler.at(.3) == before


def test_snap_tie_prefers_lower_independent_of_input_order():
    a = ms.compile_inertia({'from': 10, 'velocity': 0, 'snap': [20, 0]})
    b = ms.compile_inertia({'from': 10, 'velocity': 0, 'snap': [0, 20]})
    assert a.target == b.target == 0


def test_retarget_and_follow_are_causal_c1_and_seek_independent():
    spec = retarget(); sampler = ms.compile_retarget(spec)
    assert_same(samples('compileRetarget', spec), [sampler.at(t) for t in TIMES])
    for event in spec['events']:
        left, right = sampler.at(event['at']-1e-8), sampler.at(event['at'])
        assert left['value'] == pytest.approx(right['value'], abs=1e-4)
        assert left['velocity'] == pytest.approx(right['velocity'], abs=1e-3)
    follower = ms.compile_follow({**spec, 'lag': .15})
    assert_same(samples('compileFollow', {**spec, 'lag': .15}), [follower.at(t) for t in TIMES])
    assert follower.at(.2)['target'] == spec['initial']
    before = sampler.at(.4); spec['events'][1]['target'] = 10000
    assert sampler.at(.4) == ms.compile_retarget(spec).at(.4) == before
    spec['events'][0]['target'] = -10000
    assert sampler.at(.4) == before
    assert js(f'import {{compileRetarget}} from {json.dumps(MODEL.as_uri())};const s={json.dumps(retarget())};const p=compileRetarget(s),a=p.at(.4);s.events[0].target=999;console.log(JSON.stringify(a===p.at(.4)?false:JSON.stringify(a)===JSON.stringify(p.at(.4))));')


@pytest.mark.parametrize('order', ['together', 'beforeChildren', 'afterChildren'])
def test_variant_label_propagation_ordering_and_return(order):
    spec = variants(order); sampler = ms.compile_variants(spec)
    assert_same(samples('compileVariants', spec), [sampler.at(t) for t in TIMES])
    assert sampler.at(10) == sampler.at(-1)
    early = sampler.at(.2)
    if order == 'beforeChildren': assert early['panel']['y'] < 20 and early['card0']['y'] == 100
    if order == 'afterChildren': assert early['panel']['y'] == 20 and early['card0']['y'] < 100
    before = sampler.at(.3); sampler.at(.3)['card0']['x'] = 999; spec['root']['children'][0]['variants']['on']['x'] = 999
    assert sampler.at(.3) == before


def test_static_variant_and_safe_special_ids():
    spec = variants(); spec['events'] = []; spec['root']['id'] = '__proto__'
    assert_same(samples('compileVariants', spec), [ms.compile_variants(spec).at(t) for t in TIMES])


def test_derived_graph_is_out_of_order_safe_with_numeric_velocity():
    spec = values(); sampler = ms.compile_values(spec)
    assert_same(samples('compileValues', spec), [sampler.at(t) for t in TIMES])
    assert sampler.at(.5)['speed'] == pytest.approx(300, abs=.01)
    assert sampler.at(2)['speed'] == 0
    assert sampler.at(.6)['caption'] == 'x=50; p=0.5'
    before = sampler.at(.5); sampler.at(.5)['size']['width'] = 999
    spec['sequence']['clips'][0]['to'] = 999
    assert sampler.at(.5) == before


@pytest.mark.parametrize('value', [2.5, -2.5, 2.675, -.0001, 1e20, 1/3])
def test_numeric_templates_have_explicit_cross_language_rounding(value):
    spec = {'version': 1, 'constants': {'n': value}, 'nodes': [{'id': 's', 'op': 'template', 'digits': 2, 'parts': ['(', {'input': 'n'}, ')']}]}
    assert_same(samples('compileValues', spec), [ms.compile_values(spec).at(t) for t in TIMES])


@pytest.mark.parametrize(('js_name', 'py_name', 'spec'), [
    ('compileInertia', 'compile_inertia', {'from': 0, 'velocity': 4, 'timeConstant': 0}),
    ('compileInertia', 'compile_inertia', {'from': 0, 'velocity': 4, 'min': 10}),
    ('compileInertia', 'compile_inertia', {'from': 0, 'velocity': 4, 'snap': []}),
    ('compileInertia', 'compile_inertia', {'from': 0, 'velocity': 4, 'max': 10, 'snap': [20]}),
    ('compileRetarget', 'compile_retarget', {'version': 1, 'initial': 0, 'events': [{'at': .1, 'target': 1}, {'at': .1, 'target': 2}]}),
    ('compileFollow', 'compile_follow', {'version': 1, 'initial': 0, 'events': [{'at': -.1, 'target': 1}], 'lag': 1}),
    ('compileRetarget', 'compile_retarget', {'version': 1, 'initial': 0, 'events': [], 'physics': {'mass': 0}}),
    ('compileValues', 'compile_values', {'version': 1, 'nodes': [{'id': 'a', 'op': 'add', 'inputs': ['b']}, {'id': 'b', 'op': 'add', 'inputs': ['a']}]}),
    ('compileValues', 'compile_values', {'version': 1, 'nodes': [{'id': 'a', 'op': 'velocity', 'input': 'missing'}]}),
    ('compileValues', 'compile_values', {'version': 1, 'constants': {'x': 1}, 'nodes': [{'id': 'v', 'op': 'velocity', 'input': 'x'}, {'id': 'a', 'op': 'velocity', 'input': 'v'}]}),
    ('compileValues', 'compile_values', {'version': 1, 'constants': {'x': 1}, 'nodes': [{'id': 'a', 'op': 'map', 'input': 'x', 'range': [0, 0], 'output': [0, 1]}]}),
    ('compileValues', 'compile_values', {'version': 1, 'constants': {'x': 1}, 'nodes': [{'id': 'a', 'op': 'eval', 'input': 'x'}]}),
])
def test_invalid_specs_fail_closed(js_name, py_name, spec):
    with pytest.raises(ValueError): getattr(ms, py_name)(spec)
    rejects(js_name, spec)


@pytest.mark.parametrize('mutation', ['overlap', 'missing', 'duplicate', 'structure'])
def test_invalid_variants_rejected(mutation):
    spec = variants()
    if mutation == 'overlap': spec['events'][1]['at'] = .2
    if mutation == 'missing': del spec['root']['children'][0]['variants']['on']
    if mutation == 'duplicate': spec['root']['children'][0]['id'] = 'panel'
    if mutation == 'structure': spec['root']['variants']['on'] = {'x': 10}
    with pytest.raises(ValueError): ms.compile_variants(spec)
    rejects('compileVariants', spec)


def test_sources_identical_and_physics_rejects_nonfinite():
    assert MODEL.read_bytes() == (SKILL / 'templates/remotion/src/lib/motion-state.js').read_bytes()
    for options in [{'mass': 0}, {'damping': -1}, {'stiffness': 1e50}, {'velocity': math.inf}, {'velocity': True}]:
        with pytest.raises(ValueError): ms.spring_state(0, 1, .1, options)
    for options in [{'duration': 0}, {'duration': 1, 'bounce': 1}]:
        with pytest.raises(ValueError): ms.duration_spring(0, 1, .1, options)


@pytest.mark.slow
def test_real_state_frames_and_reverse_replay(tmp_path):
    project = tmp_path / 'project'
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    font_dir = project / 'assets/fonts/Cairo'; font_dir.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', font_dir)
    shutil.copy2(ROOT / 'tests/fixtures/visual/state-demo.js', project / 'src/state-demo.js')
    shutil.copy2(ROOT / 'tests/fixtures/visual/state-scene.js', project / 'src/scenes/state.js')
    (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2.4,scenes=[{id:"state",start:0,end:2.4}];')
    out = tmp_path / 'audit'
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(out), '--replay'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((out / 'report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 72


def test_exact_terminal_inertia_frame_and_hard_boundary_velocity():
    spec = {'from': 0, 'velocity': -500, 'min': 0, 'max': 100, 'snap': [0, 50]}
    sampler = ms.compile_inertia(spec)
    assert sampler.at(0)['velocity'] == 0
    assert sampler.at(sampler.duration) == {'value': 0, 'velocity': 0, 'target': 0, 'done': True}
    assert_same(samples('compileInertia', spec, [0, sampler.duration, 1e100]), [sampler.at(t) for t in [0, sampler.duration, 1e100]])


@pytest.mark.parametrize('field', ['velocity', 'physics'])
def test_retarget_null_optional_fields_rejected_consistently(field):
    spec = {**retarget(), field: None}
    with pytest.raises(ValueError): ms.compile_retarget(spec)
    rejects('compileRetarget', spec)


@pytest.mark.parametrize('field', ['step', 'digits'])
def test_graph_null_numeric_options_rejected(field):
    spec = {'version': 1, 'constants': {'x': 1}, 'nodes': [
        {'id': 'v', 'op': 'velocity', 'input': 'x', 'step': None} if field == 'step' else
        {'id': 's', 'op': 'template', 'parts': [{'input': 'x'}], 'digits': None}]}
    with pytest.raises(ValueError): ms.compile_values(spec)
    rejects('compileValues', spec)


def test_spring_extreme_mass_uses_stable_damping_ratio():
    options = {'stiffness': 1e-300, 'mass': 1e-300, 'damping': 2e-300}
    actual = js(f'import {{springState}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(springState(0,1,.5,{json.dumps(options)})));')
    assert_same(actual, ms.spring_state(0, 1, .5, options))


def test_graph_map_clamp_extrapolation_and_static_constants_snapshot():
    spec = {'version': 1, 'constants': {'x': 2}, 'nodes': [
        {'id': 'limited', 'op': 'map', 'input': 'x', 'range': [0, 1], 'output': [20, 40]},
        {'id': 'extra', 'op': 'map', 'input': 'x', 'range': [0, 1], 'output': [20, 40], 'clamp': False}]}
    sampler = ms.compile_values(spec)
    assert sampler.at(0)['limited'] == 40 and sampler.at(0)['extra'] == 60
    assert_same(samples('compileValues', spec), [sampler.at(t) for t in TIMES])
    spec['constants']['x'] = 999
    assert sampler.at(0)['x'] == 2


@pytest.mark.parametrize('damping', [0, 8, 20, 40])
def test_spring_satisfies_oscillator_equation(damping):
    options = {'stiffness': 130, 'mass': 1.3, 'damping': damping, 'velocity': 25}
    t, h = .37, 1e-6
    s = ms.spring_state(20, 160, t, options)
    acceleration = (ms.spring_state(20, 160, t+h, options)['velocity']-ms.spring_state(20, 160, t-h, options)['velocity'])/(2*h)
    assert acceleration == pytest.approx(-(damping*s['velocity']+130*(s['value']-160))/1.3, rel=1e-7)


def test_variant_adjacent_decimal_event_boundary_not_a_false_overlap():
    spec = {'version': 1, 'root': {'id': 'card', 'initial': 'off', 'variants': {'off': {'x': 0}, 'on': {'x': 10}}},
            'events': [{'at': .1, 'label': 'on', 'duration': .2}, {'at': .3, 'label': 'off', 'duration': .2}]}
    sampler = ms.compile_variants(spec)
    assert_same(samples('compileVariants', spec), [sampler.at(t) for t in TIMES])
    assert sampler.at(.3)['card']['x'] == pytest.approx(10)


@pytest.mark.parametrize('value', [2.5, -2.5])
def test_template_half_ties_do_not_use_bankers_rounding(value):
    spec = {'version': 1, 'constants': {'n': value}, 'nodes': [{'id': 's', 'op': 'template', 'digits': 0, 'parts': [{'input': 'n'}]}]}
    sampler = ms.compile_values(spec)
    assert sampler.at(0)['s'] == ('3' if value > 0 else '-3')
    assert_same(samples('compileValues', spec), [sampler.at(t) for t in TIMES])


def test_phase_two_rollout_and_scaffold_contract():
    rollout = json.loads((SKILL / 'motion/rollout.json').read_text())
    assert rollout['phase'] >= 2
    assert len(rollout['features']) == 44
    states = {f['id']: f['status'] for f in rollout['features']}
    assert all(states[i] == 'complete' for i in [1, 2, 3, 4, 8, 11])
    assert states[13] == ('partial' if rollout['phase'] >= 3 else 'planned')
    assert states[27] == 'excluded'
    assert (ROOT / 'docs/motion-state.md').is_file()


def test_template_rounding_does_not_depend_on_process_decimal_context():
    spec = {'version': 1, 'constants': {'x': 12.3456}, 'nodes': [{'id': 's', 'op': 'template', 'digits': 3, 'parts': [{'input': 'x'}]}]}
    with localcontext() as context:
        context.prec = 2; context.traps[Inexact] = True
        assert ms.compile_values(spec).at(0)['s'] == '12.346'
