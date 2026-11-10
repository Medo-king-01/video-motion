"""Original QA/data/visual-direction contracts, including a real Chromium audit."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys

import pytest
import visual_direction as vd
from conftest import ROOT, SKILL, requires_toolkit

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

K = SKILL / 'templates/render'


def js(script):
    result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def dataset(kind='counter'):
    rows = [{'id': 'a', 'label': 'سعة', 'value': 32}]
    if kind == 'comparison':
        rows += [{'id': 'b', 'label': 'بديل', 'value': 16}]
    if kind == 'timeline':
        rows = [{'id': 'a', 'label': 'بداية', 'at': 0, 'value': -10}, {'id': 'b', 'label': 'نهاية', 'at': 2, 'value': 20}]
    return dict(version=1, kind=kind, rows=rows, source='Illustrative test data', unit='GB', locale='ar-EG', decimals=0)


@pytest.mark.parametrize('kind', ['counter', 'comparison', 'timeline'])
def test_shared_recipes_are_deterministic_and_word_gated(kind):
    module = (K / 'lib/data-recipes.js').as_uri()
    spec = dict(data=dataset(kind), start=0, end=4, anchor=dict(text='سعة', start=1, end=2))
    result = js(f'import {{recipeAt}} from {json.dumps(module)}; const s={json.dumps(spec)}; console.log(JSON.stringify([recipeAt(s,.9),recipeAt(s,2),recipeAt(s,1.5),recipeAt(s,2)]));')
    assert not result[0]['visible'] and not result[0]['rows']
    assert result[1] == result[3]
    assert result[1]['progress'] == 1
    if kind == 'timeline':
        assert result[1]['points'][-1]['value'] == 20
        assert 0 < result[2]['points'][-1]['x'] < 1
    else:
        assert result[1]['rows'][0]['shown'] == 32
        assert result[1]['rows'][0]['display'] == '32'
        assert 0 < result[2]['rows'][0]['shown'] < 32
    assert (K / 'lib/data-recipes.js').read_bytes() == (SKILL / 'templates/remotion/src/lib/data-recipes.js').read_bytes()


@pytest.mark.parametrize(('field', 'value'), [('source', ''), ('unit', ''), ('locale', 'nonsense'), ('rows', []), ('decimals', 1.5)])
def test_dataset_validation(field, value):
    data = dataset(); data[field] = value
    module = (K / 'lib/data-recipes.js').as_uri()
    assert js(f'import {{validateDataset}} from {json.dumps(module)}; console.log(JSON.stringify(validateDataset({json.dumps(data)})));')


def test_data_recipe_csv_and_no_overwrite(tmp_path):
    source, out = tmp_path / 'data.csv', tmp_path / 'data.json'
    source.write_text('id,label,value\na,"ذاكرة, كبيرة",32\n')
    command = [sys.executable, str(ROOT / 'tools/data_recipe.py'), str(source), '--out', str(out), '--kind', 'counter', '--source', 'Illustrative', '--unit', 'GB']
    result = subprocess.run(command, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text())['rows'][0]['label'] == 'ذاكرة, كبيرة'
    before = out.read_bytes()
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert before == out.read_bytes()
    out.unlink(); out.symlink_to(tmp_path / 'outside.json')
    assert subprocess.run(command, capture_output=True).returncode != 0
    assert not (tmp_path / 'outside.json').exists()


def test_layout_contains_face_also_fails_and_zone_rules():
    module = (K / 'lib/layout.js').as_uri()
    boxes = [dict(id='face', kind='face', x=300, y=400, w=400, h=300),
             dict(id='title', kind='text', x=350, y=450, w=200, h=100),
             dict(id='caption', kind='text', zone='caption', x=100, y=1410, w=500, h=70)]
    result = js(f'import {{auditLayout}} from {json.dumps(module)}; console.log(JSON.stringify(auditLayout({json.dumps(boxes)})));')
    assert [item['code'] for item in result] == ['L03']
    boxes[1]['y'] = 50
    result = js(f'import {{auditLayout}} from {json.dumps(module)}; console.log(JSON.stringify(auditLayout({json.dumps(boxes)})));')
    assert any(i['code'] == 'L01' for i in result)


def visual_plan(tmp_path):
    (tmp_path / 'plan').mkdir()
    (tmp_path / 'plan/data.json').write_text(json.dumps(dataset()))
    beats = dict(duration=3, scenes=[dict(index=1, start=0, end=3)])
    words = dict(clock='vo', scenes=[dict(scene=1, words=[dict(text='سعة', start=1, end=1.5)])])
    direction = vd.init_draft(beats)
    direction.update(status='ready', decidedBy='agent')
    direction['scenes'][0].update(treatment='cover', why='Show the measured capacity clearly', elements=[dict(
        id='capacity', kind='counter', dataset='plan/data.json', evidence='illustrative', copyIds=['number'],
        why='One number clarifies the spoken value', anchor=dict(word=0, text='سعة'), timing='sync', start=1, end=2)])
    copy_plan = {'copy': [dict(id='number', scene=1, text='32', role='number')]}
    return direction, beats, words, copy_plan


def test_visual_direction_valid_and_caption_measurement_conversion(tmp_path):
    direction, beats, words, copies = visual_plan(tmp_path)
    assert not vd.validate(direction, beats, words, copies, tmp_path)['errors']
    measured = [dict(index=1, start=0, final=words['scenes'][0]['words'])]
    assert not vd.validate(direction, beats, measured, copies, tmp_path)['errors']
    assert vd.validate(vd.init_draft(beats), beats)['errors']


@pytest.mark.parametrize('mutation', ['early', 'unknown-word', 'wrong-text', 'missing-source', 'escape', 'duplicate', 'copy', 'lead-fact', 'missing-scene'])
def test_visual_direction_rejects_invalid_plans(tmp_path, mutation):
    direction, beats, words, copies = visual_plan(tmp_path)
    e = direction['scenes'][0]['elements'][0]
    if mutation == 'early': e['start'] = .7
    if mutation == 'unknown-word': e['anchor']['word'] = 20
    if mutation == 'wrong-text': e['anchor']['text'] = 'اختلاق'
    if mutation == 'missing-source':
        data = dataset(); data['source'] = ''; (tmp_path / 'plan/data.json').write_text(json.dumps(data))
    if mutation == 'escape': e['dataset'] = '../../outside.json'
    if mutation == 'duplicate': direction['scenes'].append(copy.deepcopy(direction['scenes'][0]))
    if mutation == 'copy': e['copyIds'] = ['missing']
    if mutation == 'lead-fact': e.update(timing='lead', start=.9, fact=True)
    if mutation == 'missing-scene': direction['scenes'] = []
    assert vd.validate(direction, beats, words, copies, tmp_path)['errors']


@pytest.fixture()
def canvas_project(tmp_path):
    project = tmp_path / 'project'; project.mkdir()
    shutil.copytree(K, project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    shutil.copy2(ROOT / 'tests/fixtures/visual/scene.js', project / 'src/scenes/test.js')
    # Correct relative module imports from the scene folder.
    scene = project / 'src/scenes/test.js'
    scene.write_text(scene.read_text().replace("from './lib/", "from '../lib/"))
    font_dir = project / 'assets/fonts/Cairo'; font_dir.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', font_dir)
    return project


def set_scenes(project, kinds):
    scenes = [dict(id=kind, start=i*2, end=(i+1)*2) for i, kind in enumerate(kinds)]
    for kind in kinds:
        shutil.copy2(project / 'src/scenes/test.js', project / f'src/scenes/{kind}.js')
    (project / 'src/data.js').write_text(f'export const W=1080,H=1920,FPS=30,scenes={json.dumps(scenes)},DURATION={len(kinds)*2};')


@pytest.mark.slow
def test_real_canvas_layout_audit_good_bad_and_no_capture(canvas_project, tmp_path):
    if not (ROOT / 'tools/toolkit/node_modules/playwright-core').is_dir():
        pytest.skip('run setup --dev for Chromium')
    set_scenes(canvas_project, ['comparison', 'timeline', 'counter'])
    command = ['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(canvas_project)]
    good = tmp_path / 'good'
    result = subprocess.run([*command, '--out', str(good)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((good / 'report.json').read_text())
    assert report['status'] == 'pass' and report['capturedText'] > 0
    assert report['sampling'] == 'all frames'
    set_scenes(canvas_project, ['bad'])
    bad = tmp_path / 'bad'
    result = subprocess.run([*command, '--out', str(bad)], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    report = json.loads((bad / 'report.json').read_text())
    assert {'L01', 'L02', 'L03'} <= {i['code'] for f in report['frames'] for i in f['issues']}
    assert list(bad.glob('frame-*.png'))
    # Do not silently pass a page without the capture contract.
    main = canvas_project / 'src/main.js'
    main.write_text(main.read_text().replace('window.layoutSnapshot =', 'window.noSnapshot ='))
    result = subprocess.run([*command, '--out', str(tmp_path / 'missing')], capture_output=True, timeout=120)
    assert result.returncode != 0


def test_visual_direction_reel_lint_and_word_path(tmp_path):
    direction, beats, words, copies = visual_plan(tmp_path)
    for name, data in [('beats', beats), ('word-timings', words), ('visual-direction', direction), ('copy', copies)]:
        (tmp_path / f'plan/{name}.json').write_text(json.dumps(data))
    assert not vd.check_project(tmp_path)['errors']
    direction['wordTimings'] = '../outside.json'
    (tmp_path / 'plan/visual-direction.json').write_text(json.dumps(direction))
    assert vd.check_project(tmp_path)['errors']
    result = subprocess.run([sys.executable, str(ROOT / 'tools/reel_lint.py'), str(tmp_path)],
                            capture_output=True, text=True)
    assert result.returncode != 0 and 'V01' in result.stdout


def test_dataset_precision_duplicate_and_nonfinite_values():
    module = (K / 'lib/data-recipes.js').as_uri()
    script = f'''import {{validateDataset}} from {json.dumps(module)};
const base={json.dumps(dataset('comparison'))};
const bad=[];
for(const value of [NaN,Infinity,-1,9007199254740992,.123]){{const d=structuredClone(base);d.rows[0].value=value;bad.push(validateDataset(d));}}
const duplicate=structuredClone(base);duplicate.rows[1].id='a';bad.push(validateDataset(duplicate));
console.log(JSON.stringify(bad));'''
    assert all(js(script))


def test_canvas_box_transform_uses_design_coordinates():
    module = (K / 'lib/layout.js').as_uri()
    result = js(f'''import {{screenBox}} from {json.dumps(module)};
const ctx={{canvas:{{width:540,height:960}},getTransform:()=>({{a:0,b:1,c:-1,d:0,e:300,f:100}})}};
console.log(JSON.stringify(screenBox(ctx,{{x:10,y:20,w:40,h:60}})));''')
    assert result == dict(x=440, y=220, w=120, h=80)


@pytest.mark.parametrize('bad', [[], None, {'scenes': [None]}, {'duration': 1, 'scenes': [{'index': []}]}])
def test_visual_direction_malformed_input_fails_closed(tmp_path, bad):
    direction, beats, words, copies = visual_plan(tmp_path)
    assert vd.validate(direction, bad, words, copies, tmp_path)['errors']


def test_comparison_fraction_below_one_and_zero_domain():
    module = (K / 'lib/data-recipes.js').as_uri()
    spec = dict(data=dataset('comparison'), start=0, end=3, anchor=dict(text='سعة', start=1, end=2))
    spec['data'].update(decimals=2)
    spec['data']['rows'][0]['value'], spec['data']['rows'][1]['value'] = .5, .25
    result = js(f'import {{recipeAt}} from {json.dumps(module)};console.log(JSON.stringify(recipeAt({json.dumps(spec)},2)));')
    assert [r['fraction'] for r in result['rows']] == [1, .5]
    spec['data']['rows'][0]['value'] = spec['data']['rows'][1]['value'] = 0
    result = js(f'import {{recipeAt}} from {json.dumps(module)};console.log(JSON.stringify(recipeAt({json.dumps(spec)},2)));')
    assert [r['fraction'] for r in result['rows']] == [0, 0]


@pytest.mark.slow
@requires_toolkit
def test_audit_no_text_incomplete_and_failed_resource_not_pass(canvas_project, tmp_path):
    set_scenes(canvas_project, ['counter'])
    scene = canvas_project / 'src/scenes/counter.js'
    scene.write_text('export function draw(ctx){ctx.clearRect(0,0,1080,1920);}')
    command = ['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(canvas_project)]
    empty = tmp_path / 'empty'
    result = subprocess.run([*command, '--out', str(empty)], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    assert json.loads((empty / 'report.json').read_text())['status'] == 'incomplete'
    scene.write_text("export async function init(){await fetch('/assets/does-not-exist.json');} export function draw(ctx){ctx.font='60px sans-serif';ctx.fillText('data',200,300);}")
    missing = tmp_path / 'resource'
    result = subprocess.run([*command, '--out', str(missing)], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0 and 'Resource HTTP 404' in result.stderr
    assert not (missing / 'report.json').exists()


def test_invalid_registered_geometry_and_missing_face():
    module = (K / 'lib/layout.js').as_uri()
    result = js(f'''import {{auditLayout}} from {json.dumps(module)};
console.log(JSON.stringify(auditLayout([null,{{id:'missing-face',kind:'face',x:0,y:0,w:0,h:0}}])));''')
    assert [item['code'] for item in result] == ['L00', 'L00']
