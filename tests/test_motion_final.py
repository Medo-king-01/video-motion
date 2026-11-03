"""Final offline additions: explicit shared identities, parity and lifecycle."""
from __future__ import annotations

import copy
import json

import pytest
from conftest import SKILL
from motion_geometry import compile_shared_layout
from test_motion_plan import assert_same
from test_visual_tools import js

GEOMETRY=SKILL/'templates/render/lib/motion-geometry.js'


def spec():
    return {'version':1,'at':.5,'duration':1,'easing':'linear',
        'from':[{'id':'left-a','x':0,'y':0,'w':100,'h':80,'r':10},{'id':'left-b','x':0,'y':100,'w':100,'h':80,'r':10}],
        'to':[{'id':'right-a','x':200,'y':0,'w':200,'h':80,'r':20},{'id':'right-b','x':200,'y':100,'w':100,'h':80,'r':10}],
        'pairs':[{'id':'card-a','from':'left-a','to':'right-a'},{'id':'card-b','from':'left-b','to':'right-b'}]}


def js_sample(value,times):
    return js(f'import {{compileSharedLayout}} from {json.dumps(GEOMETRY.as_uri())};let p=compileSharedLayout({json.dumps(value)});console.log(JSON.stringify({json.dumps(times)}.map(t=>p.at(t))));')


def test_shared_layout_explicit_identity_parity_and_reverse():
    value=spec();plan=compile_shared_layout(value);times=[-.1,.5,1,1.5,2,1,.5]
    assert_same(js_sample(value,times),[plan.at(t) for t in times])
    midpoint=plan.at(1)[0];assert midpoint['id']=='card-a' and midpoint['box']['x']==pytest.approx(100)
    assert midpoint['box']['w']==pytest.approx(150) and midpoint['box']['r']==pytest.approx(15)
    before=plan.at(1);value['to'][0]['x']=999;assert plan.at(1)==before
    assert GEOMETRY.read_bytes()==(SKILL/'templates/remotion/src/lib/motion-geometry.js').read_bytes()


@pytest.mark.parametrize('mutation', ['unknown','duplicate_source','duplicate_target','duplicate_identity','missing','extra_key','bad_timing'])
def test_shared_layout_invalid_mappings_are_rejected(mutation):
    value=copy.deepcopy(spec());pairs=value['pairs']
    if mutation=='unknown': pairs[0]['from']='not-here'
    if mutation=='duplicate_source': pairs[1]['from']=pairs[0]['from']
    if mutation=='duplicate_target': pairs[1]['to']=pairs[0]['to']
    if mutation=='duplicate_identity': pairs[1]['id']=pairs[0]['id']
    if mutation=='missing': pairs.pop()
    if mutation=='extra_key': pairs[0]['other']=1
    if mutation=='bad_timing': value['duration']=0
    with pytest.raises(ValueError): compile_shared_layout(value)
    assert js(f'import {{compileSharedLayout}} from {json.dumps(GEOMETRY.as_uri())};let bad=false;try{{compileSharedLayout({json.dumps(value)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


def test_reduced_numeric_tree_preserves_other_tracks_and_defensive_copy():
    from render_policy import compile_motion_policy

    spec={'version':1,'reduced':True,'decorative':[{'track':'decoration','value':{'xy':[0,5],'rotation':0}}]}
    values={'decoration':{'xy':[10,20],'rotation':30},'factOpacity':1,'voTime':3.1}
    policy=compile_motion_policy(spec);output=policy.at(values)
    assert output=={'decoration':{'xy':[0,5],'rotation':0},'factOpacity':1,'voTime':3.1}
    output['decoration']['xy'][0]=999;spec['decorative'][0]['value']['xy'][0]=888
    assert policy.at(values)['decoration']['xy']==[0,5]
    module=(SKILL/'templates/render/lib/render-policy.js').as_uri()
    result=js(f'''import {{compileMotionPolicy}} from {json.dumps(module)};
      const spec={{version:1,reduced:true,decorative:[{{track:'decoration',value:{{xy:[0,5],rotation:0}}}}]}};
      const input={json.dumps(values)},policy=compileMotionPolicy(spec),out=policy.at(input);
      out.decoration.xy[0]=999;spec.decorative[0].value.xy[0]=888;
      let rejected=0;for(const value of [{{xy:[0],rotation:0}},{{xy:[0,5],rotation:'3'}},{{xy:[0,5],rotation:0,extra:1}}])try{{policy.at({{decoration:value}})}}catch{{rejected++}}
      console.log(JSON.stringify({{result:policy.at(input),rejected}}));''')
    assert result['result']==policy.at(values) and result['rejected']==3
    for bad in ({'xy':[0],'rotation':0},{'xy':[0,5],'rotation':'3'},{'xy':[0,5],'rotation':0,'extra':1}):
        with pytest.raises(ValueError): policy.at({'decoration':bad})


def test_reduced_numeric_tree_rejects_cycles_and_non_numbers():
    from render_policy import compile_motion_policy

    value=[];value.append(value)
    with pytest.raises(ValueError): compile_motion_policy({'version':1,'reduced':True,'decorative':[{'track':'a','value':value}]})
    with pytest.raises(ValueError): compile_motion_policy({'version':1,'reduced':True,'decorative':[{'track':'a','value':[True]}]})
    module=(SKILL/'templates/render/lib/render-policy.js').as_uri()
    assert js(f'''import {{compileMotionPolicy}} from {json.dumps(module)};
      let bad=0;const a=[];a.push(a);const sparse=new Array(2);sparse[0]=0;sparse.extra=1;
      for(const value of [a,sparse,[true]])try{{compileMotionPolicy({{version:1,reduced:true,decorative:[{{track:'a',value}}]}})}}catch{{bad++}}
      console.log(JSON.stringify(bad===3));''')
