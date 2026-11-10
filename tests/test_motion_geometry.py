"""Portable geometry and strict offline layout/binding contracts; real fitting is tested separately."""
from __future__ import annotations

import copy
import importlib
import json
import math

import pytest
from conftest import ROOT, SKILL, requires_toolkit
from test_motion_plan import assert_same
from test_visual_tools import js

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

mg = importlib.import_module('motion_geometry')
MODEL = SKILL / 'templates/render/lib/motion-geometry.js'
TIMES = [-1, 0, .2, .3, .5, .6, .8, 1.1, 2, .3]
SQUARE = [{'x': 0, 'y': 0}, {'x': 100, 'y': 0}, {'x': 100, 'y': 100}, {'x': 0, 'y': 100}]


def evaluate(name, args):
    return js(f'import * as m from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(m.{name}(...{json.dumps(args)})));')


def samples(name, spec, times=TIMES):
    return js(f'import * as m from {json.dumps(MODEL.as_uri())};const p=m.{name}({json.dumps(spec)});console.log(JSON.stringify({json.dumps(times)}.map(t=>p.at(t))));')


def reject(name, spec):
    assert js(f'import * as m from {json.dumps(MODEL.as_uri())};let bad=false;try{{m.{name}({json.dumps(spec)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def items():
    return [{'id': 'a', 'w': 220, 'h': 120, 'r': 20}, {'id': 'b', 'w': 240, 'h': 100, 'r': 20}, {'id': 'c', 'w': 200, 'h': 150, 'r': 20}]


def layout(mode='sync'):
    initial = mg.stack_layout(items(), {'x': 140, 'y': 400})
    final = mg.stack_layout([items()[2], items()[0], {'id': 'd', 'w': 200, 'h': 80, 'r': 20}], {'x': 520, 'y': 400})
    return {'version': 1, 'initial': initial, 'events': [{'at': .2, 'duration': .3, 'mode': mode, 'items': final}]}


def text_spec():
    return {'text': 'حركة واضحة', 'font': {'family': 'Cairo', 'weight': 800}, 'maxWidth': 420, 'maxHeight': 160, 'padding': 8,
            'candidates': [{'size': 64, 'measuredBy': 'canvas', 'lines': [{'text': 'حركة واضحة', 'w': 600, 'h': 70}]},
                           {'size': 48, 'measuredBy': 'canvas', 'lines': [{'text': 'حركة', 'w': 190, 'h': 48}, {'text': 'واضحة', 'w': 210, 'h': 48}]},
                           {'size': 32, 'measuredBy': 'canvas', 'lines': [{'text': 'حركة واضحة', 'w': 300, 'h': 40}]}]}


def bindings():
    return {'version': 1, 'bindings': [
        {'id': 'rect', 'kind': 'rect', 'constants': {'x': 100, 'y': 400, 'w': 240, 'h': 100, 'r': 20}, 'tracks': {'opacity': 'alpha'}},
        {'id': 'dot', 'kind': 'circle', 'fill': 'red', 'stroke': None, 'constants': {'x': 200, 'y': 700}, 'tracks': {'r': 'radius'}},
        {'id': 'shape', 'kind': 'path', 'fill': 'gray1', 'constants': {'points': SQUARE, 'closed': True}, 'tracks': {'end': 'progress'}}]}


@pytest.mark.parametrize('axis', ['x', 'y', 'grid'])
@pytest.mark.parametrize('rtl', [False, True])
def test_stack_and_reorder_variable_sizes_parity(axis, rtl):
    options = {'x': 900 if rtl else 100, 'y': 200, 'gap': 24, 'axis': axis, 'columns': 2, 'rtl': rtl}
    assert_same(evaluate('stackLayout', [items(), options]), mg.stack_layout(items(), options))
    result = mg.reorder_layout(items(), ['c', 'a', 'b'], options)
    assert_same(evaluate('reorderLayout', [items(), ['c', 'a', 'b'], options]), result)
    assert [r['id'] for r in result] == ['c', 'a', 'b']
    assert result[0]['w'] == 200


@pytest.mark.parametrize('mode', ['sync', 'wait', 'popLayout'])
def test_group_layout_presence_exact_endpoints_and_unique_shells(mode):
    spec = layout(mode); plan = mg.compile_layout(spec)
    actual = samples('compileLayout', spec)
    assert_same(actual, [plan.at(t) for t in TIMES])
    for frame in actual: assert len({i['id'] for i in frame}) == len(frame)
    assert {i['id'] for i in plan.at(2)} == {'a', 'c', 'd'}
    assert {i['id'] for i in plan.at(-1)} == {'a', 'b', 'c'}
    if mode == 'wait':
        assert 'd' not in {i['id'] for i in plan.at(.6)}
        assert next(i for i in plan.at(.3) if i['id'] == 'a')['box']['x'] == 140
        assert plan.duration == pytest.approx(1.1)
    if mode == 'popLayout': assert next(i for i in plan.at(.3) if i['id'] == 'b')['layer'] == 'overlay'
    before = plan.at(.3); spec['initial'][0]['x'] = 999
    plan.at(.3)[0]['box']['x'] = 999
    assert plan.at(.3) == before


def test_multiple_layouts_and_empty_group_never_reset_on_reverse_seek():
    spec = layout(); spec['events'].append({'at': .5, 'duration': .2, 'items': []})
    plan = mg.compile_layout(spec)
    assert_same(samples('compileLayout', spec), [plan.at(t) for t in TIMES])
    assert plan.at(.7) == [] and plan.at(100) == []
    assert plan.at(.3) == plan.at(.3)
    assert mg.compile_layout({'version': 1, 'initial': [], 'events': []}).at(1) == []


@pytest.mark.parametrize('spec', [{'scaleX': 2, 'scaleY': .5, 'radius': 24, 'strokeWidth': 3}, {'scaleX': .25, 'scaleY': 4}])
def test_axis_scale_correction_restores_requested_device_sizes(spec):
    result = mg.correct_scale(spec)
    assert_same(evaluate('correctScale', [spec]), result)
    assert result['radiusX']*spec['scaleX'] == spec.get('radius', 0)
    assert result['strokeY']*spec['scaleY'] == spec.get('strokeWidth', 0)


@pytest.mark.parametrize('options', [{'start': 0, 'end': 0}, {'start': .2, 'end': .6}, {'start': .7, 'end': 1, 'offset': .2}, {'start': 0, 'end': 1, 'closed': True}])
def test_stroke_windows_trim_on_measured_length_and_wrap(options):
    points = SQUARE if options.get('closed') else [{'x': 0, 'y': 0}, {'x': 100, 'y': 0}, {'x': 100, 'y': 100}]
    result = mg.stroke_segments(points, options)
    assert_same(evaluate('strokeSegments', [points, options]), result)
    def length(line): return sum(math.hypot(a['x']-b['x'], a['y']-b['y']) for a, b in zip(line, line[1:], strict=False))
    total = 400 if options.get('closed') else 200
    assert sum(length(line) for line in result) == pytest.approx(total*(options['end']-options['start']))


def test_zero_length_path_and_duplicate_vertices_do_not_divide_by_zero():
    point = {'x': 10, 'y': 10}
    assert mg.stroke_segments([point, point]) == evaluate('strokeSegments', [[point, point]]) == []
    assert_same(evaluate('strokeSegments', [[point, point, {'x': 110, 'y': 10}], {'end': .5}]), mg.stroke_segments([point, point, {'x': 110, 'y': 10}], {'end': .5}))
    with pytest.raises(ValueError): mg.normalize_shape([point, point], 4, {'closed': False})


@pytest.mark.parametrize('closed', [False, True])
@pytest.mark.parametrize('align', [False, True])
def test_polygon_and_polyline_morph_normalization_parity(closed, align):
    target = [{'x': 50, 'y': -40}, {'x': 140, 'y': 100}, {'x': -40, 'y': 100}]
    spec = {'from': copy.deepcopy(SQUARE), 'to': target, 'count': 32, 'closed': closed, 'align': align}
    plan = mg.compile_morph(spec)
    times = [-1, 0, .25, .5, 1, 2, .25]
    assert_same(samples('compileMorph', spec, times), [plan.at(t) for t in times])
    assert len(plan.at(.5)) == 32 and plan.at(-1) == plan.at(0) and plan.at(2) == plan.at(1)
    before = plan.at(.5); spec['from'][0]['x'] = 999; plan.at(.5)[0]['x'] = 999
    assert plan.at(.5) == before


def test_morph_aligns_winding_and_rotated_start_of_same_square():
    target = [SQUARE[2], SQUARE[1], SQUARE[0], SQUARE[3]]
    spec = {'from': copy.deepcopy(SQUARE), 'to': target, 'count': 4}
    assert mg.compile_morph(spec).at(.5) == SQUARE
    assert_same(samples('compileMorph', spec, [0, .5, 1]), [SQUARE]*3)


def test_measured_fit_largest_size_whole_words_and_autosize():
    spec = text_spec(); result = mg.fit_measured_text(spec)
    assert_same(evaluate('fitMeasuredText', [spec]), result)
    assert result['fits'] and result['size'] == 48 and result['w'] == 226
    assert [line['text'] for line in result['lines']] == ['حركة', 'واضحة']
    assert all(0 <= line['x'] and line['x']+line['w'] <= result['w'] for line in result['lines'])
    spec['maxHeight'] = 1
    assert not mg.fit_measured_text(spec)['fits']
    assert_same(evaluate('fitMeasuredText', [spec]), mg.fit_measured_text(spec))


def test_real_harfbuzz_fit_retains_all_words_and_never_returns_fake_fit():
    measure = importlib.import_module('text_measure').measure_text_fit
    options = {'family': 'Cairo', 'weight': 800, 'minSize': 28, 'maxSize': 44, 'step': 2, 'maxWidth': 350, 'maxHeight': 180, 'padding': 8}
    text = 'نص عربي واضح على الخط الحقيقي'
    result = measure(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', text, options)
    assert result['fits'] and result['measuredBy'] == 'harfbuzz'
    assert result['w'] <= 350 and result['h'] <= 180
    assert ' '.join(l['text'] for l in result['lines']) == text
    assert not measure(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', text, {**options, 'maxWidth': 10})['fits']
    with pytest.raises((ValueError, FileNotFoundError)): measure(ROOT / 'missing.ttf', text, options)


def test_typed_bindings_palette_and_structured_style():
    spec = bindings(); values = {'alpha': .7, 'radius': 24, 'progress': .6}
    plan = mg.compile_bindings(spec); result = plan.at(values)
    actual = js(f'import {{compileBindings}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(compileBindings({json.dumps(spec)}).at({json.dumps(values)})));')
    assert_same(actual, result)
    palette = {'ink': '#0A0A0A', 'gray1': '#D8D7D5'}
    assert_same(evaluate('boxStyle', [result[0], palette]), mg.box_style(result[0], palette))
    before = plan.at(values); result[0]['props']['x'] = 999; spec['bindings'][0]['constants']['x'] = 999
    assert plan.at(values) == before
    with pytest.raises(ValueError): plan.at({})


@pytest.mark.parametrize('mutation', ['overlap', 'duplicate', 'radius', 'negative', 'mode'])
def test_invalid_layout_fails_closed(mutation):
    spec = layout()
    if mutation == 'overlap': spec['events'].append({'at': .3, 'duration': .2, 'items': []})
    if mutation == 'duplicate': spec['initial'].append(copy.deepcopy(spec['initial'][0]))
    if mutation == 'radius': spec['initial'][0]['r'] = 1000
    if mutation == 'negative': spec['events'][0]['duration'] = -1
    if mutation == 'mode': spec['events'][0]['mode'] = 'automatic'
    with pytest.raises(ValueError): mg.compile_layout(spec)
    reject('compileLayout', spec)


@pytest.mark.parametrize('mutation', ['unknown', 'color', 'conflict', 'duplicate', 'html'])
def test_invalid_bindings_are_not_arbitrary_styles_or_html(mutation):
    spec = bindings()
    if mutation == 'unknown': spec['bindings'][0]['constants']['filter'] = 'blur(2px)'
    if mutation == 'color': spec['bindings'][0]['fill'] = '#123456'
    if mutation == 'conflict': spec['bindings'][0]['tracks']['x'] = 'x'
    if mutation == 'duplicate': spec['bindings'][1]['id'] = 'rect'
    if mutation == 'html': spec['bindings'][0]['kind'] = 'innerHTML'
    with pytest.raises(ValueError): mg.compile_bindings(spec)
    reject('compileBindings', spec)


@pytest.mark.parametrize('mutation', ['omit', 'split', 'missing-font', 'fake-source', 'nonfinite'])
def test_text_fit_requires_explicit_font_and_complete_measured_copy(mutation):
    spec = text_spec()
    if mutation == 'omit': spec['candidates'][0]['lines'][0]['text'] = 'حركة'
    if mutation == 'split': spec['candidates'][0]['lines'][0]['text'] = 'حر كة واضحة'
    if mutation == 'missing-font': spec['font']['family'] = ''
    if mutation == 'fake-source': spec['candidates'][0]['measuredBy'] = 'guess'
    if mutation == 'nonfinite': spec['candidates'][0]['lines'][0]['w'] = -1
    with pytest.raises(ValueError): mg.fit_measured_text(spec)
    reject('fitMeasuredText', spec)


def test_k_r_ship_same_geometry_and_measurement():
    for file in ['motion-geometry.js', 'text-measure.js']:
        assert (SKILL / 'templates/render/lib' / file).read_bytes() == (SKILL / 'templates/remotion/src/lib' / file).read_bytes()


@pytest.mark.slow
@requires_toolkit
def test_real_geometry_frames_measurement_and_reverse_replay(tmp_path):
    import shutil
    import subprocess
    project = tmp_path / 'project'
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    fonts = project / 'assets/fonts/Cairo'; fonts.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', fonts)
    shutil.copy2(ROOT / 'tests/fixtures/visual/geometry-demo.js', project / 'src/geometry-demo.js')
    shutil.copy2(ROOT / 'tests/fixtures/visual/geometry-scene.js', project / 'src/scenes/geometry.js')
    (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=3,scenes=[{id:"geometry",start:0,end:3}];')
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(tmp_path / 'audit'), '--replay'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((tmp_path / 'audit/report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 90


def test_p_draw_adapter_palette_and_pixels():
    from geometry_draw import PALETTE, draw_geometry
    from PIL import Image
    brand = json.loads((SKILL / 'brand/brand.json').read_text())['palette']
    aliases = {'redBright': 'red_bright', 'redDeep': 'red_deep', 'inkSoft': 'ink_soft', **{f'gray{i}': f'gray_{i}' for i in range(1, 5)}}
    for token, color in PALETTE.items(): assert color == brand[aliases.get(token, token)]['hex']
    paint = mg.compile_bindings(bindings()).at({'alpha': 1, 'radius': 24, 'progress': 0})
    image = Image.new('RGB', (1080, 1920), PALETTE['paper']); draw_geometry(image, paint)
    assert image.getpixel((200, 700)) == (203, 39, 27)
    assert image.getpixel((200, 450)) == (216, 215, 213)


def test_pop_layout_adapter_orders_exiting_overlay_after_flow():
    sample = mg.compile_layout(layout('popLayout')).at(.3)
    sample = list(reversed(sample))
    options = {'colors': {'a': 'gray2'}, 'strokeWidth': 4}
    result = mg.layout_bindings(sample, options)
    assert_same(evaluate('layoutBindings', [sample, options]), result)
    assert result[-1]['id'] == 'b' and result[0]['props']['strokeWidth'] == 4


@pytest.mark.parametrize('order', [['a', 'a', 'c'], ['a', 'b'], ['a', 'b', 'unknown']])
def test_reorder_requires_exact_permutation(order):
    with pytest.raises(ValueError): mg.reorder_layout(items(), order)
    assert js(f'import {{reorderLayout}} from {json.dumps(MODEL.as_uri())};let bad=false;try{{reorderLayout({json.dumps(items())},{json.dumps(order)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


@pytest.mark.parametrize('spec', [{'scaleX': 0, 'scaleY': 1}, {'scaleX': 1, 'scaleY': -1}, {'scaleX': 1, 'scaleY': 1, 'strokeWidth': -1}])
def test_scale_correction_rejects_singular_or_negative_inputs(spec):
    with pytest.raises(ValueError): mg.correct_scale(spec)
    reject('correctScale', spec)


@pytest.mark.parametrize('options', [{'start': .8, 'end': .2}, {'end': 2}, {'start': -1}, {'closed': 'yes'}])
def test_invalid_stroke_window_fails_closed(options):
    with pytest.raises(ValueError): mg.stroke_segments(SQUARE, options)
    assert js(f'import {{strokeSegments}} from {json.dumps(MODEL.as_uri())};let bad=false;try{{strokeSegments({json.dumps(SQUARE)},{json.dumps(options)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def test_phase_three_rollout_keeps_limits_visible():
    rollout = json.loads((SKILL / 'motion/rollout.json').read_text())
    assert rollout['phase'] >= 3
    states = {entry['id']: entry['status'] for entry in rollout['features']}
    assert states[18] == 'complete'
    assert all(states[i] == 'partial' for i in [13, 14, 15, 16, 17, 19, 22, 23, 24, 25])
    assert states[27] == states[42] == 'excluded'
