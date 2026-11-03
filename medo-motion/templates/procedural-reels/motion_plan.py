"""Original offline motion plans. Same JSON/timing semantics as K/R motion-plan.js."""
from __future__ import annotations

import copy
import math
import re

from motion import clamp, ease


def _finite(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def _number(n, name):
    if not _finite(n):
        raise ValueError(f'{name} must be finite')


def mix_value(a, b, p):
    _number(p, 'progress')
    if _finite(a) and _finite(b):
        value = (1-p)*a+p*b
        _number(value, 'mixed value')
        return value
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [mix_value(x, y, p) for x, y in zip(a, b)]
    if isinstance(a, dict) and isinstance(b, dict) and sorted(a) == sorted(b):
        return {k: mix_value(a[k], b[k], p) for k in sorted(a)}
    if isinstance(a, str) and isinstance(b, str):
        pattern = r'^([+-]?(?:\d+\.?\d*|\.\d+))(px|%|deg)$'
        x, y = re.fullmatch(pattern, a), re.fullmatch(pattern, b)
        if x and y and x[2] == y[2]:
            return f'{mix_value(float(x[1]), float(y[1]), p):.15g}{x[2]}'
        if a == b:
            return a
    raise ValueError('values must have matching numeric structure/units')


def stagger_time(index, count, options=None):
    options = options or {}
    each, origin, start = options.get('each', .06), options.get('from', 'first'), options.get('start', 0)
    if type(count) is not int or not 1 <= count <= 10000 or type(index) is not int or not 0 <= index < count:
        raise ValueError('invalid stagger index/count')
    if not _finite(each) or each < 0 or not _finite(start) or start < 0:
        raise ValueError('invalid stagger timing')
    if origin == 'edges':
        distance, maximum = min(index, count-1-index), (count-1)//2
    else:
        origin = {'first': 0, 'last': count-1, 'center': (count-1)/2}.get(origin, origin) if isinstance(origin, str) else origin
        if not _finite(origin) or not 0 <= origin <= count-1:
            raise ValueError('invalid stagger origin')
        nearest = abs(math.floor(origin+.5)-origin)
        distance = abs(index-origin)-nearest
        maximum = max(origin, count-1-origin)-nearest
    return start+each*maximum*clamp(ease(options.get('easing', 'linear'), distance/maximum if maximum else 0))


def cycle_value(a, b, time, spec):
    start, duration = spec.get('start'), spec.get('duration')
    repeat, delay = spec.get('repeat', 0), spec.get('repeatDelay', 0)
    kind, easing = spec.get('type', 'loop'), spec.get('easing', 'linear')
    for k, v in [('time', time), ('start', start), ('duration', duration), ('repeatDelay', delay)]:
        _number(v, k)
    if start < 0 or duration <= 0 or delay < 0 or type(repeat) is not int or not 0 <= repeat <= 10000 or kind not in ('loop', 'reverse', 'mirror'):
        raise ValueError('invalid finite cycle')
    total = duration*(repeat+1)+delay*repeat
    _number(total, 'cycle duration')
    elapsed = time-start
    iteration = 0 if elapsed < 0 else min(repeat, math.floor(elapsed/(duration+delay)))
    raw = 1 if elapsed >= total else clamp((elapsed-iteration*(duration+delay))/duration)
    raw = 1 if raw > 1-1e-12 else 0 if raw < 1e-12 else raw
    odd = iteration % 2 == 1
    p = ease(easing, 1-raw if kind == 'reverse' and odd else raw)
    return {'active': 0 <= elapsed < total, 'done': elapsed >= total, 'iteration': iteration,
            'value': mix_value(b, a, p) if kind == 'mirror' and odd else mix_value(a, b, p)}


class MotionSequence:
    def __init__(self, spec):
        if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec.get('version') != 1 or not isinstance(spec.get('clips'), list) or not spec['clips']:
            raise ValueError('sequence requires version=1 and nonempty clips')
        markers = spec.get('markers', {})
        if not isinstance(markers, dict) or any(not k or k in ('<', '>') or not _finite(v) or v < 0 for k, v in markers.items()):
            raise ValueError('invalid markers')
        self._tracks, ids, previous = {}, set(), None

        def resolve(at):
            if _finite(at):
                return at
            if at == '<':
                return previous['start'] if previous else None
            if at == '>':
                return previous['end'] if previous else None
            if isinstance(at, str):
                return markers.get(at)
            if isinstance(at, dict) and isinstance(at.get('label'), str) and _finite(at.get('offset')):
                base = resolve(at['label'])
                return base+at['offset'] if _finite(base) else None
            return None

        for c in spec['clips']:
            if not isinstance(c, dict) or not isinstance(c.get('id'), str) or not c['id'].strip() or c['id'] in ids or not isinstance(c.get('track'), str) or not c['track'].strip():
                raise ValueError('clips require unique ids and named tracks')
            if 'cut' in c and not isinstance(c['cut'], bool):
                raise ValueError('cut must be a boolean')
            start, duration = resolve(c.get('at')), c.get('duration')
            if not _finite(start) or start < 0 or not _finite(duration) or duration <= 0 or not _finite(start+duration):
                raise ValueError('invalid clip timing')
            mix_value(c.get('from'), c.get('to'), .5)
            ease(c.get('easing', 'linear'), .5)
            item = copy.deepcopy({**c, 'start': start, 'end': start+duration})
            self._tracks.setdefault(c['track'], []).append(item)
            ids.add(c['id']); previous = item
        for track in self._tracks.values():
            track.sort(key=lambda c: c['start'])
            for prev, curr in zip(track, track[1:]):
                if curr['start'] < prev['end']:
                    raise ValueError('overlapping clips on one track')
                if not curr.get('cut') and mix_value(curr['from'], prev['to'], 0) != mix_value(curr['from'], prev['to'], 1):
                    raise ValueError('discontinuous track requires cut:true')
        self.duration = max(c['end'] for track in self._tracks.values() for c in track)

    def at(self, time):
        _number(time, 'time')
        out = {}
        for name, track in self._tracks.items():
            value = copy.deepcopy(track[0]['from'])
            for c in track:
                if time < c['start']:
                    break
                value = copy.deepcopy(c['to']) if time >= c['end'] else mix_value(c['from'], c['to'], ease(c.get('easing', 'linear'), (time-c['start'])/(c['end']-c['start'])))
            out[name] = value
        return out


def compile_sequence(spec):
    return MotionSequence(spec)


def path_at(points, progress):
    _number(progress, 'progress')
    if not isinstance(points, list) or not 2 <= len(points) <= 4 or any(not isinstance(p, dict) or not _finite(p.get('x')) or not _finite(p.get('y')) for p in points):
        raise ValueError('path needs 2–4 finite points')
    p = clamp(progress)

    def sample(items):
        items = copy.deepcopy(items)
        while len(items) > 1:
            items = [{'x': mix_value(a['x'], b['x'], p), 'y': mix_value(a['y'], b['y'], p)} for a, b in zip(items, items[1:])]
        return items[0]

    point, n = sample(points), len(points)-1
    tangent = sample([{'x': n*(b['x']-a['x']), 'y': n*(b['y']-a['y'])} for a, b in zip(points, points[1:])])
    return {**point, 'angle': math.degrees(math.atan2(tangent['y'], tangent['x']))}


def arc_at(a, b, progress, height=0):
    _number(height, 'arc height')
    path_at([a, b], 0)
    dx, dy = b['x']-a['x'], b['y']-a['y']
    length = math.hypot(dx, dy)
    control = {'x': (a['x']+b['x'])/2-(dy/length if length else 0)*2*height,
               'y': (a['y']+b['y'])/2+(dx/length if length else 0)*2*height}
    return path_at([a, control, b], progress)


def presence_at(time, spec):
    start, enter, exit_start, end = [spec.get(k) for k in ('start', 'enterEnd', 'exitStart', 'end')]
    for value in (time, start, enter, exit_start, end):
        _number(value, 'presence timing')
    if not 0 <= start < enter <= exit_start < end:
        raise ValueError('invalid presence window')
    active = start <= time < end
    p = clamp((time-start)/(enter-start)) if time < enter else 1 if time < exit_start else clamp((end-time)/(end-exit_start))
    return {'active': active, 'opacity': clamp(ease(spec.get('easing', 'linear'), p)) if active else 0,
            'phase': 'absent' if not active else 'enter' if time < enter else 'hold' if time < exit_start else 'exit'}


def compile_nested_sequence(spec):
    """Nested local markers/clips compiled into namespaced finite tracks."""
    active = set(); count = [0]
    def walk(node, prefix, depth):
        if not isinstance(node, dict) or type(node.get('version')) is not int or node['version'] != 1 or not isinstance(node.get('items'), list) or not node['items'] or depth > 8 or id(node) in active:
            raise ValueError('invalid or recursive nested sequence')
        active.add(id(node))
        try:
            markers = node.get('markers', {})
            if not isinstance(markers, dict) or any(not isinstance(k, str) or not k or k in ('<', '>') or not _finite(v) or v < 0 for k, v in markers.items()): raise ValueError('invalid markers')
            ids, clips, previous, duration = set(), [], None, 0
            def resolve(at):
                if _finite(at): return at
                if at == '<': return previous['start'] if previous else None
                if at == '>': return previous['end'] if previous else None
                if isinstance(at, str): return markers.get(at)
                if isinstance(at, dict) and isinstance(at.get('label'), str) and _finite(at.get('offset')):
                    v = resolve(at['label']); return v+at['offset'] if _finite(v) else None
                return None
            for item in node['items']:
                count[0] += 1
                if count[0] > 512 or not isinstance(item, dict) or not isinstance(item.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', item['id']) or item['id'] in ids: raise ValueError('invalid or duplicate nested item id')
                ids.add(item['id']); start = resolve(item.get('at'))
                if not _finite(start) or start < 0: raise ValueError('invalid nested item start')
                name = prefix+item['id']
                if 'sequence' in item:
                    if set(item)-{'id','at','sequence','timeScale'}: raise ValueError('unsupported nested sequence property')
                    scale = item.get('timeScale', 1)
                    if not _finite(scale) or not .01 <= scale <= 100: raise ValueError('nested timeScale must be between 0.01 and 100')
                    child, child_duration = walk(item['sequence'], name+'/', depth+1); end = start+child_duration*scale
                    if not _finite(end) or end <= start: raise ValueError('invalid nested end')
                    for clip in child:
                        at, duration_scaled = start+clip['at']*scale, clip['duration']*scale
                        if not _finite(at) or not _finite(duration_scaled) or duration_scaled < 1e-9 or not _finite(at+duration_scaled) or at+duration_scaled <= at: raise ValueError('invalid scaled nested clip time')
                        clips.append({**clip, 'at': at, 'duration': duration_scaled})
                    previous = {'start': start, 'end': end}; duration = max(duration, end)
                else:
                    if 'timeScale' in item: raise ValueError('timeScale requires a nested sequence')
                    track, d = item.get('track'), item.get('duration')
                    if not isinstance(track, str) or not track.strip() or '/' in track or len(track) > 128 or not _finite(d) or d <= 0 or not _finite(start+d): raise ValueError('invalid nested clip')
                    clips.append({**item, 'id': name, 'track': prefix+track, 'at': start})
                    previous = {'start': start, 'end': start+d}; duration = max(duration, previous['end'])
            return clips, duration
        finally: active.remove(id(node))
    clips, _ = walk(spec, '', 0)
    # Clamp sub-picosecond floating point overlap at shared nested boundaries.
    by_track = {}
    for clip in clips: by_track.setdefault(clip['track'], []).append(clip)
    for track in by_track.values():
        track.sort(key=lambda c: c['at']); end = -math.inf
        for clip in track:
            if clip['at'] < end and clip['at'] >= end-1e-12: clip['at'] = end
            end = clip['at']+clip['duration']
    return compile_sequence({'version': 1, 'clips': clips})
