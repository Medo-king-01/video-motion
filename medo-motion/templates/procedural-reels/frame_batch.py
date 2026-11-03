"""Batch pure samplers within one frame. No cross-frame cache or timing side effects."""
from __future__ import annotations

import math


def compile_frame_batch(entries):
    if not isinstance(entries, list) or len(entries) > 256: raise ValueError('invalid frame batch')
    names = set(); compiled = []
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get('id'), str) or not e['id'].strip() or e['id'] in ('__proto__', 'constructor', 'prototype') or e['id'] in names or not callable(e.get('sample')): raise ValueError('invalid batch entry')
        names.add(e['id']); compiled.append((e['id'], e['sample']))
    class Batch:
        def at(self, t):
            if type(t) not in (int, float) or not math.isfinite(t): raise ValueError('invalid time')
            cache, out = {}, {}
            for name, sample in compiled:
                key = id(sample)
                if key not in cache: cache[key] = sample(t)
                out[name] = cache[key]
            return out
    return Batch()


def compile_frame_graph(entries):
    """Topologically evaluate authored dependencies once per call; never cache across frames."""
    import inspect

    if not isinstance(entries, list) or len(entries) > 256: raise ValueError('invalid frame graph')
    forbidden = {'__proto__', 'constructor', 'prototype'}; nodes = {}
    for e in entries:
        if not isinstance(e, dict) or not isinstance(e.get('id'), str) or not e['id'].strip() or e['id'] in forbidden or e['id'] in nodes or not isinstance(e.get('depends'), list) or len(e['depends']) > 256 or not callable(e.get('sample')): raise ValueError('invalid graph entry')
        deps = e['depends']
        if any(not isinstance(d, str) or not d.strip() or d in forbidden for d in deps) or len(set(deps)) != len(deps): raise ValueError('invalid graph dependencies')
        nodes[e['id']] = (list(deps), e['sample'])
    marks, order = {}, []
    def visit(name):
        if name not in nodes: raise ValueError('unknown graph dependency')
        if marks.get(name) == 1: raise ValueError('frame graph cycle')
        if marks.get(name) == 2: return
        marks[name] = 1
        for dep in nodes[name][0]: visit(dep)
        marks[name] = 2; order.append(name)
    for name in nodes: visit(name)
    class Graph:
        def at(self, t):
            if type(t) not in (int, float) or not math.isfinite(t): raise ValueError('invalid time')
            out = {}
            for name in order:
                deps, sample = nodes[name]; result = sample(t, {dep:out[dep] for dep in deps})
                if inspect.isawaitable(result):
                    if inspect.iscoroutine(result): result.close()
                    raise ValueError('frame graph samplers must be synchronous')
                out[name] = result
            return out
    return Graph()
