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
