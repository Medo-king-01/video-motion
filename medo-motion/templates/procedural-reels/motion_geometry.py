"""Original portable offline layout/shape/binding grammar, matching K/R motion-geometry.js."""
from __future__ import annotations

import copy
import math

from motion import clamp, ease
from motion_plan import mix_value
from motion_state import _finite, _number as _num, _positive as _pos, _Sampler


def _flag(x, name):
    if not isinstance(x, bool): raise ValueError(f'{name} must be boolean')
    return x


def _boxes(items):
    if not isinstance(items, list) or len(items) > 256: raise ValueError('layout needs <=256 items')
    ids, out = set(), []
    for item in items:
        if not isinstance(item, dict) or not isinstance(item.get('id'), str) or not item['id'].strip() or item['id'] in ids:
            raise ValueError('layout ids must be unique')
        ids.add(item['id'])
        x, y, w, h, r = item.get('x'), item.get('y'), item.get('w'), item.get('h'), item.get('r', 0)
        _num(x, 'x'); _num(y, 'y'); _pos(w, 'w'); _pos(h, 'h'); _num(r, 'r')
        if r < 0 or r > min(w, h)/2: raise ValueError('radius outside box')
        _num(x+w, 'right'); _num(y+h, 'bottom')
        out.append({'id': item['id'], 'x': x, 'y': y, 'w': w, 'h': h, 'r': r})
    return out


def stack_layout(items, options=None):
    options = options or {}
    x, y, gap, axis, columns, rtl = (options.get(k, d) for k, d in [('x', 0), ('y', 0), ('gap', 16), ('axis', 'y'), ('columns', 2), ('rtl', False)])
    _num(x, 'x'); _num(y, 'y'); _num(gap, 'gap'); _flag(rtl, 'rtl')
    if gap < 0 or axis not in ('x', 'y', 'grid') or type(columns) is not int or not 1 <= columns <= 256: raise ValueError('invalid stack options')
    source = _boxes([{**i, 'x': 0, 'y': 0} for i in items]); out = []
    cell_w = max([0]+[i['w'] for i in source]); cursor, row_y = 0, y
    for i, item in enumerate(source):
        left, top = x, y
        if axis == 'x':
            left = x-cursor-item['w'] if rtl else x+cursor; cursor += item['w']+gap
        if axis == 'y':
            top = y+cursor; cursor += item['h']+gap
            if rtl: left = x-item['w']
        if axis == 'grid':
            col = i % columns
            if col == 0 and i > 0: row_y += max(b['h'] for b in source[i-columns:i])+gap
            left = x-col*(cell_w+gap)-item['w'] if rtl else x+col*(cell_w+gap); top = row_y
        out.append({**item, 'x': left, 'y': top})
    return _boxes(out)


def reorder_layout(items, order, options=None):
    source = _boxes([{**i, 'x': 0, 'y': 0} for i in items]); by_id = {i['id']: i for i in source}
    if not isinstance(order, list) or not all(isinstance(i, str) for i in order) or len(order) != len(source) or len(set(order)) != len(order) or any(i not in by_id for i in order):
        raise ValueError('order must be an exact permutation')
    return stack_layout([by_id[i] for i in order], options)


def compile_layout(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('events'), list):
        raise ValueError('layout requires version=1/events')
    initial = _boxes(spec.get('initial')); previous, events, end = initial, [], 0
    for raw in spec['events']:
        if not isinstance(raw, dict) or not _finite(raw.get('at')) or raw['at'] < 0 or raw['at'] < end-1e-12:
            raise ValueError('layout transitions must not overlap')
        duration = _pos(raw.get('duration'), 'duration'); mode, easing = raw.get('mode', 'sync'), raw.get('easing', 'cubicInOut')
        if mode not in ('sync', 'wait', 'popLayout'): raise ValueError('invalid presence mode')
        _num(ease(easing, .5), 'easing'); target = _boxes(raw.get('items')); start = max(raw['at'], end)
        end = _num(start+duration*(3 if mode == 'wait' else 1), 'end')
        events.append(dict(start=start, end=end, duration=duration, mode=mode, easing=easing, source=previous, target=target)); previous = target

    def held(items):
        return [{'id': item['id'], 'box': {k: v for k, v in item.items() if k != 'id'}, 'opacity': 1, 'phase': 'hold', 'layer': 'flow'} for item in items]

    def sample(t):
        items = initial
        for e in events:
            if t < e['start']: break
            if t >= e['end']: items = e['target']; continue
            source, target = {i['id']: i for i in e['source']}, {i['id']: i for i in e['target']}
            local = t-e['start']; move_start = e['duration'] if e['mode'] == 'wait' else 0; enter_start = 2*e['duration'] if e['mode'] == 'wait' else 0
            def progress(start): return clamp(ease(e['easing'], clamp((local-start)/e['duration'])))
            move, enter, leave = progress(move_start), progress(enter_start), progress(0); out = []
            for item in e['target']:
                key = item['id']; box = {k: v for k, v in item.items() if k != 'id'}
                if key in source:
                    old = {k: v for k, v in source[key].items() if k != 'id'}
                    out.append({'id': key, 'box': mix_value(old, box, move), 'opacity': 1, 'phase': 'hold' if move >= 1 else 'move', 'layer': 'flow'})
                elif enter > 0: out.append({'id': key, 'box': box, 'opacity': enter, 'phase': 'enter', 'layer': 'flow'})
            for item in e['source']:
                if item['id'] not in target and leave < 1:
                    out.append({'id': item['id'], 'box': {k: v for k, v in item.items() if k != 'id'}, 'opacity': 1-leave, 'phase': 'exit', 'layer': 'overlay' if e['mode'] == 'popLayout' else 'flow'})
            return out
        return held(items)
    return _Sampler(sample, duration=end)


def correct_scale(spec):
    sx, sy, radius, stroke = spec.get('scaleX'), spec.get('scaleY'), spec.get('radius', 0), spec.get('strokeWidth', 0)
    _pos(sx, 'scaleX'); _pos(sy, 'scaleY'); _num(radius, 'radius'); _num(stroke, 'strokeWidth')
    if radius < 0 or stroke < 0: raise ValueError('invalid scale correction')
    return {'radiusX': _num(radius/sx, 'radiusX'), 'radiusY': _num(radius/sy, 'radiusY'), 'strokeX': _num(stroke/sx, 'strokeX'), 'strokeY': _num(stroke/sy, 'strokeY')}


def _points(points, closed=False):
    _flag(closed, 'closed')
    if not isinstance(points, list) or not (3 if closed else 2) <= len(points) <= 4096 or any(not isinstance(p, dict) or not _finite(p.get('x')) or not _finite(p.get('y')) for p in points):
        raise ValueError('invalid polyline points')
    out = [{'x': p['x'], 'y': p['y']} for p in points]
    if closed and out[0] != out[-1]: out.append(out[0].copy())
    return out


def _path_info(points, closed):
    p = _points(points, closed); edges, distance, length = [], [0], 0
    for a, b in zip(p, p[1:]):
        size = _num(math.hypot(b['x']-a['x'], b['y']-a['y']), 'edge length')
        edges.append(size); length = _num(length+size, 'path length'); distance.append(length)

    def at(d):
        if d <= 0: return p[0].copy()
        if d >= length: return p[-1].copy()
        for i, size in enumerate(edges):
            if size > 0 and d <= distance[i+1]: return mix_value(p[i], p[i+1], (d-distance[i])/size)
        return p[-1].copy()
    return p, length, distance, at


def stroke_segments(points, options=None):
    options = options or {}; start, end, offset, closed = (options.get(k, d) for k, d in [('start', 0), ('end', 1), ('offset', 0), ('closed', False)])
    _num(start, 'start'); _num(end, 'end'); _num(offset, 'offset')
    if start < 0 or end > 1 or start > end: raise ValueError('invalid stroke interval')
    p, length, distance, at = _path_info(points, closed); size = end-start
    if not length or not size: return []
    if size == 1: return [p]
    first = (start+offset) % 1; last = first+size
    ranges = [(first, last)] if last <= 1 else [(first, 1), (0, last-1)]; out = []
    for a, b in ranges:
        if b <= a: continue
        lo, hi = a*length, b*length
        result = [at(lo)]+[point.copy() for point, d in zip(p, distance) if lo < d < hi]+[at(hi)]; out.append(result)
    return out


def normalize_shape(points, count=64, options=None):
    closed = (options or {}).get('closed', True)
    if type(count) is not int or not (3 if closed else 2) <= count <= 256: raise ValueError('invalid resample count')
    _, length, _, at = _path_info(points, closed)
    if length == 0: raise ValueError('shape must have positive length')
    return [at(length*i/(count if closed else count-1)) for i in range(count)]


def _area(points):
    return sum(p['x']*points[(i+1) % len(points)]['y']-points[(i+1) % len(points)]['x']*p['y'] for i, p in enumerate(points))/2


def compile_morph(spec):
    closed, align, count = spec.get('closed', True), spec.get('align', True), spec.get('count', 64)
    _flag(closed, 'closed'); _flag(align, 'align')
    a, b = normalize_shape(spec.get('from'), count, {'closed': closed}), normalize_shape(spec.get('to'), count, {'closed': closed})
    if closed and align:
        if _area(a)*_area(b) < 0: b = [b[0]]+list(reversed(b[1:]))
        best, index = math.inf, 0
        for shift in range(count):
            score = _num(sum((p['x']-b[(i+shift) % count]['x'])**2+(p['y']-b[(i+shift) % count]['y'])**2 for i, p in enumerate(a)), 'alignment score')
            if score < best: best, index = score, shift
        b = [b[(i+index) % count] for i in range(count)]
    return _Sampler(lambda p: mix_value(a, b, clamp(p)))


def fit_measured_text(spec):
    if not isinstance(spec, dict) or not isinstance(spec.get('text'), str) or not spec['text'].strip() or not isinstance(spec.get('font'), dict): raise ValueError('explicit text/font required')
    font = spec['font']
    if not isinstance(font.get('family'), str) or not font['family'].strip() or type(font.get('weight')) is not int or not 100 <= font['weight'] <= 900: raise ValueError('explicit text/font required')
    max_w, max_h, candidates, pad, line_height = spec.get('maxWidth'), spec.get('maxHeight'), spec.get('candidates'), spec.get('padding', 0), spec.get('lineHeight', 1.3)
    _pos(max_w, 'maxWidth'); _pos(max_h, 'maxHeight'); _num(pad, 'padding'); _pos(line_height, 'lineHeight')
    if pad < 0 or not isinstance(candidates, list) or not candidates or len(candidates) > 512: raise ValueError('invalid measured candidates')
    norm = lambda s: ' '.join(s.split())
    sizes, valid = set(), []
    for c in candidates:
        if not isinstance(c, dict) or not _finite(c.get('size')) or c['size'] <= 0 or c['size'] in sizes or c.get('measuredBy') not in ('canvas', 'harfbuzz') or not isinstance(c.get('lines'), list) or not c['lines']:
            raise ValueError('invalid text candidate')
        sizes.add(c['size']); height, width, lines = 0, 0, []
        for line in c['lines']:
            if not isinstance(line, dict) or not isinstance(line.get('text'), str) or not line['text'].strip(): raise ValueError('invalid measured line')
            w, h = _num(line.get('w'), 'line width'), _pos(line.get('h'), 'line height')
            if w < 0: raise ValueError('negative width')
            cell = max(c['size']*line_height, h)
            lines.append({'text': line['text'], 'x': 0, 'y': pad+height+(cell-h)/2, 'w': w, 'h': h}); height += cell; width = max(width, w)
        if norm(' '.join(line['text'] for line in c['lines'])) != norm(spec['text']): raise ValueError('text fit may not omit/split words')
        for line in lines: line['x'] = pad+(width-line['w'])/2
        if width+2*pad <= max_w and height+2*pad <= max_h:
            valid.append({'fits': True, 'size': c['size'], 'font': font.copy(), 'measuredBy': c['measuredBy'], 'w': width+2*pad, 'h': height+2*pad, 'lines': lines})
    valid.sort(key=lambda c: -c['size'])
    return valid[0] if valid else {'fits': False, 'size': None, 'font': font.copy(), 'measuredBy': None, 'w': 0, 'h': 0, 'lines': []}


_TOKENS = ('red', 'redBright', 'redDeep', 'ink', 'inkSoft', 'paper', 'gray1', 'gray2', 'gray3', 'gray4', 'salmon', 'blush')


class _Bindings:
    def __init__(self, bindings): self._bindings = bindings

    def at(self, values):
        if not isinstance(values, dict): raise ValueError('binding values must be an object')
        out = []
        for b in self._bindings:
            p = {'opacity': 1, 'strokeWidth': 3, **copy.deepcopy(b['constants'])}
            for key, ref in b['tracks'].items():
                if ref not in values: raise ValueError('missing binding value')
                p[key] = copy.deepcopy(values[ref])
            _num(p['opacity'], 'opacity'); _num(p['strokeWidth'], 'strokeWidth')
            if not 0 <= p['opacity'] <= 1 or p['strokeWidth'] < 0: raise ValueError('invalid paint')
            if b['kind'] == 'rect':
                box = _boxes([{'id': b['id'], **p}])[0]; del box['id']; p.update(box)
            if b['kind'] == 'circle':
                _num(p.get('x'), 'x'); _num(p.get('y'), 'y'); _pos(p.get('r'), 'r')
            if b['kind'] == 'path':
                p['closed'] = p.get('closed', False); _points(p.get('points'), p['closed'])
                p['start'], p['end'], p['offset'] = p.get('start', 0), p.get('end', 1), p.get('offset', 0)
                stroke_segments(p['points'], p)
                if not p['closed'] and b['fill'] is not None: raise ValueError('open path cannot be filled')
            out.append({'id': b['id'], 'kind': b['kind'], 'fill': b['fill'], 'stroke': b['stroke'], 'props': p})
        return out


def compile_bindings(spec):
    if not isinstance(spec, dict) or type(spec.get('version')) is not int or spec['version'] != 1 or not isinstance(spec.get('bindings'), list) or len(spec['bindings']) > 256: raise ValueError('bindings require version=1/bindings')
    bindings = copy.deepcopy(spec['bindings']); ids = set()
    for b in bindings:
        if not isinstance(b, dict) or not isinstance(b.get('id'), str) or not b['id'].strip() or b['id'] in ids or b.get('kind') not in ('rect', 'circle', 'path') or not isinstance(b.get('constants', {}), dict) or not isinstance(b.get('tracks', {}), dict): raise ValueError('invalid binding')
        ids.add(b['id']); b['constants'], b['tracks'] = b.get('constants', {}), b.get('tracks', {})
        allowed = {'opacity', 'strokeWidth'} | (set(('x', 'y', 'w', 'h', 'r')) if b['kind'] == 'rect' else set(('x', 'y', 'r')) if b['kind'] == 'circle' else set(('points', 'start', 'end', 'offset', 'closed')))
        if any(k not in allowed for k in [*b['constants'], *b['tracks']]) or any(not isinstance(v, str) or not v for v in b['tracks'].values()) or any(k in b['constants'] for k in b['tracks']): raise ValueError('unknown/conflicting property binding')
        b['fill'], b['stroke'] = b.get('fill', None if b['kind'] == 'path' else 'gray1'), b.get('stroke', 'ink')
        if any(t is not None and t not in _TOKENS for t in (b['fill'], b['stroke'])): raise ValueError('color must be a palette token or null')
    return _Bindings(bindings)


def box_style(item, palette):
    if item['kind'] != 'rect': raise ValueError('boxStyle requires a rect binding')
    p = item['props']
    def color(token):
        if token is None: return 'transparent'
        if token not in palette: raise ValueError('missing palette token')
        return palette[token]
    return {'position': 'absolute', 'boxSizing': 'border-box', 'left': p['x'], 'top': p['y'], 'width': p['w'], 'height': p['h'], 'borderRadius': p['r'],
            'borderWidth': 0 if item['stroke'] is None else p['strokeWidth'], 'borderStyle': 'solid', 'borderColor': color(item['stroke']), 'background': color(item['fill']), 'opacity': p['opacity']}


def layout_bindings(states, options=None):
    options = options or {}; colors = options.get('colors', {})
    if not isinstance(states, list) or not isinstance(colors, dict): raise ValueError('invalid layout sample/colors')
    for s in states:
        if not isinstance(s, dict) or not isinstance(s.get('box'), dict) or s.get('layer') not in ('flow', 'overlay'): raise ValueError('invalid layout sample')
    ordered = sorted(states, key=lambda s: s['layer'] == 'overlay')
    return compile_bindings({'version': 1, 'bindings': [{'id': s['id'], 'kind': 'rect', 'fill': colors.get(s['id'], options.get('fill', 'gray1')), 'stroke': options.get('stroke', 'ink'),
        'constants': {**s['box'], 'opacity': s['opacity'], 'strokeWidth': options.get('strokeWidth', 3)}} for s in ordered]}).at({})
