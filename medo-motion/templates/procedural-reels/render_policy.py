"""Explicit reduced motion overrides for authored decorative numeric tracks only."""
from __future__ import annotations

import math


def _finite(x):
    if type(x) not in (int, float): return False
    try: return math.isfinite(x)
    except OverflowError: return False


def compile_motion_policy(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('reduced'), bool) or not isinstance(spec.get('decorative'), list) or len(spec['decorative']) > 256: raise ValueError('invalid motion policy')
    forbidden = {'__proto__', 'constructor', 'prototype'}
    def snapshot(value):
        active, count = set(), [0]
        def walk(v, depth):
            count[0] += 1
            if count[0] > 1024 or depth > 8: raise ValueError('decorative value budget exceeded')
            if _finite(v): return v
            if not isinstance(v, (list, dict)) or id(v) in active: raise ValueError('decorative value must be a finite numeric tree')
            active.add(id(v))
            try:
                if isinstance(v, list):
                    if not 1 <= len(v) <= 256: raise ValueError('invalid decorative array')
                    return [walk(x, depth+1) for x in v]
                if not 1 <= len(v) <= 256 or any(not isinstance(k, str) or k in forbidden for k in v): raise ValueError('invalid decorative object')
                return {k:walk(x, depth+1) for k,x in v.items()}
            finally: active.remove(id(v))
        return walk(value, 0)
    def same_shape(a, b):
        if _finite(a): return _finite(b)
        if isinstance(a, list): return isinstance(b, list) and len(a)==len(b) and all(same_shape(x,y) for x,y in zip(a,b,strict=True))
        return isinstance(b, dict) and a.keys()==b.keys() and all(same_shape(a[k],b[k]) for k in a)
    tracks = {}
    for item in spec['decorative']:
        if not isinstance(item, dict) or not isinstance(item.get('track'), str) or not item['track'].strip() or item['track'] in forbidden or item['track'] in tracks: raise ValueError('invalid decorative track')
        tracks[item['track']] = snapshot(item.get('value'))
    reduced = spec['reduced']
    class Policy:
        def at(self, values):
            if not isinstance(values, dict): raise ValueError('expected track values')
            out = dict(values)
            for name, value in tracks.items():
                if name not in values or not same_shape(value, snapshot(values[name])): raise ValueError('missing or mismatched decorative track')
                if reduced: out[name] = snapshot(value)
            return out
    return Policy()


def motion_mode(value):
    """Validate an explicit environment/CLI mode; never inspect host preferences."""
    if value not in ('normal', 'reduced'): raise ValueError('motion mode must be normal or reduced')
    return value


def decorative_time(time, mode):
    """Freeze only an authored decorative clock; leave the scene/VO clock unchanged."""
    if not _finite(time): raise ValueError('decorative time must be finite')
    return 0 if motion_mode(mode) == 'reduced' else time
