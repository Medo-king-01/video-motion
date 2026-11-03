"""Render policy and explicit resource lifecycle contracts."""
from __future__ import annotations

import json

import pytest
from conftest import SKILL
from render_policy import compile_motion_policy
from resource_scope import ResourceScope
from test_visual_tools import js

BASE = SKILL / 'templates/render/lib'


@pytest.mark.parametrize('reduced', [True, False])
def test_reduced_motion_only_explicit_tracks_unchanged_facts_and_time(reduced):
    spec = {'version': 1, 'reduced': reduced, 'decorative': [{'track': 'orb.rotation', 'value': 0}]}
    values = {'orb.rotation': 90, 'fact.opacity': 0, 'fact.copy': 'حقائق', 'localTime': 1.2}
    plan = compile_motion_policy(spec)
    actual = js(f'import {{compileMotionPolicy}} from {json.dumps((BASE / "render-policy.js").as_uri())};console.log(JSON.stringify(compileMotionPolicy({json.dumps(spec)}).at({json.dumps(values)})));')
    result = plan.at(values); assert actual == result
    assert result['orb.rotation'] == (0 if reduced else 90)
    assert all(result[k] == values[k] for k in ('fact.opacity', 'fact.copy', 'localTime'))
    spec['decorative'][0]['value'] = 999
    assert plan.at(values) == result
    assert values['orb.rotation'] == 90


@pytest.mark.parametrize('spec', [
    {'version': 1, 'reduced': 'true', 'decorative': []},
    {'version': 1, 'reduced': True, 'decorative': [{'track': '__proto__', 'value': 0}]},
    {'version': 1, 'reduced': True, 'decorative': [{'track': 'x', 'value': 0}, {'track': 'x', 'value': 1}]},
    {'version': 1, 'reduced': True, 'decorative': [{'track': 'x', 'value': '100'}]},
])
def test_invalid_policy_rejected_by_both(spec):
    with pytest.raises(ValueError): compile_motion_policy(spec)
    assert js(f'import {{compileMotionPolicy}} from {json.dumps((BASE / "render-policy.js").as_uri())};let bad=false;try{{compileMotionPolicy({json.dumps(spec)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def test_decorative_track_must_exist_even_when_reduced_false():
    plan = compile_motion_policy({'version': 1, 'reduced': False, 'decorative': [{'track': 'x', 'value': 0}]})
    with pytest.raises(ValueError): plan.at({})


def test_resource_scope_is_lifo_idempotent_and_continues_after_error():
    scope = ResourceScope(); log = []
    scope.defer(lambda: log.append('first'))
    def broken():
        log.append('broken'); raise ValueError('oops')
    scope.defer(broken); scope.defer(lambda: log.append('last'))
    with pytest.raises(RuntimeError): scope.close()
    scope.close(); assert scope.closed and log == ['last', 'broken', 'first']
    with pytest.raises(ValueError): scope.defer(lambda: None)
    code = f'''import {{createResourceScope}} from {json.dumps((BASE / "resource-scope.js").as_uri())};
      const s=createResourceScope(),log=[];s.defer(()=>log.push('first'));s.defer(()=>{{log.push('broken');throw Error('oops')}});s.defer(async()=>log.push('last'));
      const a=s.close(),b=s.close();let errors=0;try{{await a}}catch(e){{errors=e.errors.length}}try{{await b}}catch{{}}
      let reject=false;try{{s.defer(()=>{{}})}}catch{{reject=true}}console.log(JSON.stringify({{log,errors,reject,closed:s.closed}}));'''
    assert js(code) == {'log': ['last', 'broken', 'first'], 'errors': 1, 'reject': True, 'closed': True}


def test_js_shared_libraries_are_identical():
    for name in ['render-policy.js', 'resource-scope.js', 'frame-batch.js', 'svg-art.js']:
        assert (BASE / name).read_bytes() == (SKILL / 'templates/remotion/src/lib' / name).read_bytes()


def test_frame_batch_deduplicates_only_within_current_frame():
    from frame_batch import compile_frame_batch
    calls = []
    def sample(t): calls.append(t); return t*2
    batch = compile_frame_batch([{'id': 'a', 'sample': sample}, {'id': 'b', 'sample': sample}])
    assert batch.at(.3) == {'a': .6, 'b': .6}
    assert batch.at(.3) == {'a': .6, 'b': .6}
    assert calls == [.3, .3]
    code = f'''import {{compileFrameBatch}} from {json.dumps((BASE / "frame-batch.js").as_uri())};
      let calls=[];const sample=t=>{{calls.push(t);return t*2}};
      const batch=compileFrameBatch([{{id:'a',sample}},{{id:'b',sample}}]);const first=batch.at(.3),second=batch.at(.3);
      console.log(JSON.stringify({{first,second,calls}}));'''
    assert js(code) == {'first': {'a': .6, 'b': .6}, 'second': {'a': .6, 'b': .6}, 'calls': [.3, .3]}


def test_frame_batch_rejects_duplicate_ids_and_bad_times():
    from frame_batch import compile_frame_batch
    with pytest.raises(ValueError): compile_frame_batch([{'id': 'a', 'sample': lambda t: t}, {'id': 'a', 'sample': lambda t: t}])
    with pytest.raises(ValueError): compile_frame_batch([]).at(float('nan'))
