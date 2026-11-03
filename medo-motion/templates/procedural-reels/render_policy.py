"""Explicit reduced motion overrides for authored decorative numeric tracks only."""
from __future__ import annotations

import math


def _finite(x): return type(x) in (int, float) and math.isfinite(x)


def compile_motion_policy(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('reduced'), bool) or not isinstance(spec.get('decorative'), list) or len(spec['decorative']) > 256: raise ValueError('invalid motion policy')
    tracks = {}
    for item in spec['decorative']:
        if not isinstance(item, dict) or not isinstance(item.get('track'), str) or not item['track'].strip() or item['track'] in ('__proto__', 'constructor', 'prototype') or item['track'] in tracks or not _finite(item.get('value')): raise ValueError('invalid decorative track')
        tracks[item['track']] = item['value']
    reduced = spec['reduced']
    class Policy:
        def at(self, values):
            if not isinstance(values, dict): raise ValueError('expected track values')
            out = dict(values)
            for name, value in tracks.items():
                if name not in values or not _finite(values[name]): raise ValueError('missing or nonnumeric decorative track')
                if reduced: out[name] = value
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
