"""A bounded, explicit per-frame dependency graph with no wall clock or retained frames."""
from __future__ import annotations

import json

import pytest
from conftest import SKILL
from frame_batch import compile_frame_graph
from test_visual_tools import js

MODULE=SKILL/'templates/render/lib/frame-batch.js'


def test_graph_topology_sampling_once_reverse_and_python_javascript_parity():
    calls=[]
    def base(t,_): calls.append(t); return t*2
    graph=compile_frame_graph([{'id':'sum','depends':['left','right'],'sample':lambda t,d:d['left']+d['right']},
        {'id':'right','depends':['base'],'sample':lambda t,d:d['base']*3},
        {'id':'base','depends':[],'sample':base}, {'id':'left','depends':['base'],'sample':lambda t,d:d['base']+1}])
    times=[0,1,.5,2,.5,1,0];output=[graph.at(t) for t in times]
    assert calls==times and output[2]==output[4] and output[1]==output[5]
    assert output[1]['sum']==9
    result=js(f'''import {{compileFrameGraph}} from {json.dumps(MODULE.as_uri())};let calls=[];
      const g=compileFrameGraph([{{id:'sum',depends:['left','right'],sample:(t,d)=>d.left+d.right}},
      {{id:'right',depends:['base'],sample:(t,d)=>d.base*3}},{{id:'base',depends:[],sample:(t)=>{{calls.push(t);return t*2}}}},
      {{id:'left',depends:['base'],sample:(t,d)=>d.base+1}}]);
      console.log(JSON.stringify({{output:{json.dumps(times)}.map(t=>g.at(t)),calls}}));''')
    assert result['output']==output and result['calls']==times
    assert MODULE.read_bytes()==(SKILL/'templates/remotion/src/lib/frame-batch.js').read_bytes()


@pytest.mark.parametrize('nodes', [
    [{'id':'a','depends':['b']}],
    [{'id':'a','depends':['b']},{'id':'b','depends':['a']}],
    [{'id':'a','depends':['a']}],
    [{'id':'a','depends':[]},{'id':'a','depends':[]}],
    [{'id':'a','depends':['b','b']},{'id':'b','depends':[]}],
    [{'id':'constructor','depends':[]}],
])
def test_graph_rejects_invalid_dependencies_in_both_languages(nodes):
    entries=[{**v,'sample':lambda t,d:0} for v in nodes]
    with pytest.raises(ValueError): compile_frame_graph(entries)
    result=js(f'''import {{compileFrameGraph}} from {json.dumps(MODULE.as_uri())};let bad=false;
      try{{compileFrameGraph({json.dumps(nodes)}.map(x=>({{...x,sample:()=>0}})))}}catch{{bad=true}}console.log(JSON.stringify(bad));''')
    assert result


def test_graph_rejects_async_and_does_not_keep_failed_frame():
    async def bad(t,d): return 1
    with pytest.raises(ValueError): compile_frame_graph([{'id':'a','depends':[],'sample':bad}]).at(1)
    calls=[]
    def sample(t,d):
        calls.append(t)
        if t==1: raise RuntimeError('error')
        return t
    graph=compile_frame_graph([{'id':'a','depends':[],'sample':sample}])
    with pytest.raises(RuntimeError): graph.at(1)
    assert graph.at(2)=={'a':2} and calls==[1,2]
    result=js(f'''import {{compileFrameGraph}} from {json.dumps(MODULE.as_uri())};
      let bad=false;try{{compileFrameGraph([{{id:'a',depends:[],sample:async()=>1}}]).at(1)}}catch{{bad=true}}
      console.log(JSON.stringify(bad));''')
    assert result
