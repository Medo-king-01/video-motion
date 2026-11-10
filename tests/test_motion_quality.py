"""Native shared-shell continuity and observed reverse-seek pixel reproducibility."""
from __future__ import annotations

import json
import subprocess

import pytest
from conftest import ROOT, SKILL, requires_toolkit
from test_visual_tools import canvas_project as canvas_project
from test_visual_tools import js, set_scenes

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

MODEL = SKILL / 'templates/render/lib/shared-element.js'


def spec():
    return dict(id='detail', start=0, arrive=.8, contentAt=.9, end=2,
                **{'from': dict(x=620, y=300, w=360, h=140, r=28),
                   'to': dict(x=100, y=500, w=880, h=640, r=28)})


def test_shared_element_geometry_is_pure_holds_exactly_and_gates_contents():
    result = js(f'''import {{sharedElementAt}} from {json.dumps(MODEL.as_uri())};
const s={json.dumps(spec())};const before=JSON.stringify(s);
const frames=[-1,0,.4,.8,.89,.9,1.9,2,.4].map(t=>sharedElementAt(s,t));
console.log(JSON.stringify({{frames,unmutated:before===JSON.stringify(s)}}));''')
    frames = result['frames']
    assert result['unmutated']
    assert not frames[0]['active'] and not frames[7]['active']
    assert frames[1]['box'] == spec()['from']
    assert frames[3]['box'] == frames[6]['box'] == spec()['to']
    assert frames[2] == frames[-1] and frames[2]['progress'] == .5
    assert frames[2]['box'] == dict(x=360, y=400, w=620, h=390, r=28)
    assert not frames[4]['contentsReady'] and frames[5]['contentsReady']
    assert (SKILL / 'templates/remotion/src/lib/shared-element.js').read_bytes() == MODEL.read_bytes()


@pytest.mark.parametrize(('field', 'value'), [('id', ''), ('start', -1), ('arrive', 0),
    ('contentAt', .5), ('end', .8), ('from', {'x': 1}), ('to', None)])
def test_shared_element_rejects_invalid_specs(field, value):
    data = spec(); data[field] = value
    result = js(f'''import {{validateSharedElement}} from {json.dumps(MODEL.as_uri())};
console.log(JSON.stringify(validateSharedElement({json.dumps(data)})));''')
    assert result


def test_shared_element_adapter_calls_each_callback_once_and_restores_on_failure():
    adapter = (MODEL.parent / 'shared-panel.js').as_uri()
    result = js(f'''import {{drawSharedPanel}} from {json.dumps(adapter)};
const s={json.dumps(spec())},calls={{label:0,content:0,save:0,restore:0,shell:0}};
const ctx={{save:()=>calls.save++,restore:()=>calls.restore++,beginPath(){{}},
roundRect(){{}},fill:()=>calls.shell++,stroke(){{}}}};
const callbacks={{drawLabel:()=>calls.label++,drawContent:()=>calls.content++}};
drawSharedPanel(ctx,s,-1,callbacks);drawSharedPanel(ctx,s,.4,callbacks);drawSharedPanel(ctx,s,1,callbacks);
try{{drawSharedPanel(ctx,s,1,{{drawContent:()=>{{throw Error('fixture')}}}})}}catch{{}}
console.log(JSON.stringify(calls));''')
    assert result == dict(label=2, content=1, save=3, restore=3, shell=3)


def test_shared_interpolation_has_no_overshoot():
    result = js(f'''import {{sharedElementAt}} from {json.dumps(MODEL.as_uri())};
const s={json.dumps(spec())};console.log(JSON.stringify(Array.from({{length:61}},(_,i)=>sharedElementAt(s,i/30))));''')
    for state in result:
        for key, value in state['box'].items():
            assert min(spec()['from'][key], spec()['to'][key]) <= value <= max(spec()['from'][key], spec()['to'][key])


@pytest.mark.slow
@requires_toolkit
def test_k_replay_good_and_history_dependent_pixels_fail(canvas_project, tmp_path):
    set_scenes(canvas_project, ['counter'])
    command = ['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(canvas_project), '--replay', '--every', '6']
    good = tmp_path / 'good'
    result = subprocess.run([*command, '--out', str(good)], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads((good / 'report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 11  # includes the last frame
    assert report['sampling'].startswith('sampled')
    scene = canvas_project / 'src/scenes/counter.js'
    # A hidden per-render counter changes pixels, not text metrics or manual boxes.
    # It guarantees a failure instead of relying on a chance random collision.
    source = scene.read_text().replace('export function draw(ctx,t,', 'let count=0; export function draw(ctx,t,')
    source = source.replace('ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);', "ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);ctx.fillStyle=(++count%2)?C.red:C.ink;ctx.fillRect(80,250,80,80);")
    scene.write_text(source)
    bad = tmp_path / 'bad'
    result = subprocess.run([*command, '--out', str(bad)], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    report = json.loads((bad / 'report.json').read_text())
    assert report['replay']['status'] == 'fail'
    assert any(i['code'] == 'R01' for f in report['frames'] for i in f['issues'])
    assert list(bad.glob('replay-frame-*.png'))


@pytest.mark.slow
@requires_toolkit
def test_k_replay_checks_metadata_even_if_pixels_match(canvas_project, tmp_path):
    set_scenes(canvas_project, ['counter'])
    (canvas_project / 'src/scenes/counter.js').write_text('''import {withLayout} from '../lib/layout.js';
let count=0;
export function draw(ctx){ctx.font='60px sans-serif';ctx.fillStyle='#0A0A0A';
withLayout(ctx,{id:`unstable-${count++}`},()=>ctx.fillText('data',200,300));}''')
    target = tmp_path / 'metadata'
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(canvas_project),
        '--out', str(target), '--replay', '--every', '10'], capture_output=True, text=True, timeout=120)
    assert result.returncode != 0
    report = json.loads((target / 'report.json').read_text())
    assert {i['code'] for f in report['frames'] for i in f['issues']} == {'R02'}
