#!/usr/bin/env python3
"""Compile a deliberately bounded, static SVG path subset into portable brand-safe JSON.

No browser, XML entities, external resources, CSS or executable SVG. Unsupported content fails
closed; this is NOT a general SVG renderer. See docs/motion-svg.md before using assets.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from svgpathtools import Line, parse_path

ROOT = Path(__file__).resolve().parents[1]
TOKENS = {'red': '#CB271B', 'redBright': '#CB0801', 'redDeep': '#9F0803', 'ink': '#0A0A0A', 'inkSoft': '#71717A',
          'paper': '#F3F2F1', 'gray1': '#D8D7D5', 'gray2': '#C9C5C2', 'gray3': '#BFBAB7', 'gray4': '#A3A2A0', 'salmon': '#D97F68', 'blush': '#D5AEA6'}
NUMBER = re.compile(r'[+-]?(?:(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)')
ARITY = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'A': 7}
MAX_COORD = 1_000_000


def _num(value):
    try: number = float(value)
    except (TypeError, ValueError): raise ValueError('invalid SVG number') from None
    if not math.isfinite(number) or abs(number) > MAX_COORD: raise ValueError('SVG number out of range')
    return number


def _transform_point(matrix, x, y):
    a,b,c,d,e,f = matrix
    return _num(a*x+c*y+e), _num(b*x+d*y+f)


def _paint(value, *, allow_reference=False):
    if value == 'none': return None
    if allow_reference and re.fullmatch(r'url\(#[A-Za-z_][A-Za-z0-9_.-]{0,63}\)', value): return value
    for token, hex_value in TOKENS.items():
        if value.lower() == hex_value.lower(): return token
    raise ValueError('SVG paint must be none or an exact brand palette hex; named colors are not accepted')


def _inline_style(value, *, allow_opacity=False):
    """A strict list of static presentation declarations, not a general CSS parser."""
    if not isinstance(value, str) or len(value) > 4096: raise ValueError('invalid inline SVG style')
    allowed = {'fill', 'stroke', 'stroke-width', 'fill-rule'} | ({'opacity'} if allow_opacity else set())
    result = {}
    for declaration in value.split(';'):
        if not declaration.strip(): continue
        if declaration.count(':') != 1: raise ValueError('invalid inline SVG declaration')
        key, val = (part.strip() for part in declaration.split(':', 1))
        if key not in allowed or key in result or not val: raise ValueError('unsupported or duplicate inline SVG declaration')
        if key in ('fill', 'stroke'): _paint(val, allow_reference=key == 'fill')
        elif key == 'stroke-width':
            if _num(val) < 0: raise ValueError('negative SVG stroke width')
        elif key == 'fill-rule':
            if val not in ('evenodd', 'nonzero'): raise ValueError('unsupported fill rule')
        elif not 0 <= _num(val) <= 1: raise ValueError('opacity must be between 0 and 1')
        result[key] = val
    return result


def parse_d(data, steps=32):
    """Validate every character, expand repetitions/compact flags, preserve explicit subpaths."""
    if not isinstance(data, str) or not data.strip() or len(data) > 65536: raise ValueError('invalid path data')
    if type(steps) is not int or not 4 <= steps <= 64: raise ValueError('steps must be 4..64')
    i = 0; command = None; commands = []; chunks = []; current = 0j; start = 0j; closed = False; ops = 0
    def skip():
        nonlocal i
        while i < len(data) and data[i] in ' \t\r\n,': i += 1
    def number(flag=False):
        nonlocal i
        skip()
        if flag:
            if i >= len(data) or data[i] not in '01': raise ValueError('arc flag must be 0 or 1')
            result = data[i]; i += 1; return result
        match = NUMBER.match(data, i)
        if not match: raise ValueError('missing or invalid path number')
        i = match.end(); _num(match.group()); return match.group()
    def flush():
        nonlocal commands, current
        if not commands: return
        try: path = parse_path(' '.join(commands), current_pos=current)
        except Exception as error: raise ValueError('invalid SVG path') from error
        if not path: raise ValueError('empty or degenerate SVG subpath')
        points = [{'x': float(path[0].start.real), 'y': float(path[0].start.imag)}]
        for segment in path:
            n = 1 if isinstance(segment, Line) else steps
            for j in range(1, n+1):
                z = segment.point(j/n); x, y = _num(z.real), _num(z.imag)
                points.append({'x': x, 'y': y})
                if len(points) > 4096: raise ValueError('SVG subpath exceeds point budget')
        if closed and points[-1] == points[0]: points.pop()
        if len(points) < (3 if closed else 2): raise ValueError('degenerate SVG subpath')
        current = path[-1].end
        chunks.append({'points': points, 'closed': closed}); commands = []
        if len(chunks) > 64: raise ValueError('too many SVG subpaths')
    while True:
        skip()
        if i == len(data): break
        ch = data[i]
        if ch.isalpha():
            if ch not in 'MmLlHhVvCcSsQqTtAaZz': raise ValueError('unsupported SVG path command')
            i += 1; command = ch
            if ch in 'Zz':
                if not commands: raise ValueError('close without open subpath')
                commands.append('Z'); closed = True; flush(); current = start; command = None
                continue
        if command is None: raise ValueError('SVG command required')
        up = command.upper()
        if not commands and up != 'M': raise ValueError('subpath must start with moveto')
        values = [number(up == 'A' and j in (3, 4)) for j in range(ARITY[up])]
        if up == 'A' and (_num(values[0]) < 0 or _num(values[1]) < 0): raise ValueError('negative arc radius')
        if up == 'M':
            if commands: flush()
            x, y = _num(values[0]), _num(values[1]); start = complex(x,y)+(current if command.islower() else 0j)
            closed = False
        commands.append(command+' '+' '.join(values)); ops += 1
        if ops > 1024: raise ValueError('SVG path exceeds command budget')
        if up == 'M': command = 'l' if command.islower() else 'L'
    flush()
    if not chunks: raise ValueError('SVG path has no geometry')
    return chunks



def _mul(a, b):
    aa, ab, ac, ad, ae, af = a; ba, bb, bc, bd, be, bf = b
    result = [aa*ba+ac*bb, ab*ba+ad*bb, aa*bc+ac*bd, ab*bc+ad*bd, aa*be+ac*bf+ae, ab*be+ad*bf+af]
    return [_num(v) for v in result]


def _numbers(text):
    result = []; pos = 0
    for match in NUMBER.finditer(text):
        if not re.fullmatch(r'[\s,]*', text[pos:match.start()]): raise ValueError('invalid numeric list')
        result.append(_num(match.group())); pos = match.end()
    if not re.fullmatch(r'[\s,]*', text[pos:]): raise ValueError('invalid numeric list')
    return result


def _transform(text):
    matrix = [1,0,0,1,0,0]; pos = 0
    for match in re.finditer(r'([A-Za-z]+)\s*\(([^()]*)\)', text):
        if not re.fullmatch(r'[\s,]*', text[pos:match.start()]): raise ValueError('invalid transform')
        name, nums = match.group(1), _numbers(match.group(2)); pos = match.end()
        if name == 'matrix' and len(nums) == 6: step = nums
        elif name == 'translate' and len(nums) in (1, 2): step = [1,0,0,1,nums[0],nums[1] if len(nums) == 2 else 0]
        elif name == 'scale' and len(nums) in (1, 2): step = [nums[0],0,0,nums[-1],0,0]
        elif name == 'rotate' and len(nums) in (1, 3):
            angle = math.radians(nums[0]); co, si = math.cos(angle), math.sin(angle)
            step = [co,si,-si,co,0,0]
            if len(nums) == 3: step = _mul(_mul([1,0,0,1,nums[1],nums[2]],step),[1,0,0,1,-nums[1],-nums[2]])
        elif name in ('skewX','skewY') and len(nums) == 1:
            tangent = math.tan(math.radians(nums[0])); step = [1,0,tangent,1,0,0] if name == 'skewX' else [1,tangent,0,1,0,0]
        else: raise ValueError('unsupported SVG transform')
        matrix = _mul(matrix, step)
    if not re.fullmatch(r'[\s,]*', text[pos:]) or (text.strip() and pos == 0): raise ValueError('invalid transform')
    return matrix


def _shape_data(tag, attrs):
    def n(name, default=None):
        value = attrs.get(name, default)
        if value is None: raise ValueError(f'missing {tag} {name}')
        return _num(value)
    if tag == 'path': return attrs.get('d')
    if tag in ('polygon', 'polyline'):
        nums = _numbers(attrs.get('points', ''))
        if len(nums) % 2 or len(nums) < (6 if tag == 'polygon' else 4): raise ValueError('invalid points')
        return 'M '+' '.join(str(v) for v in nums[:2])+' L '+' '.join(str(v) for v in nums[2:])+(' Z' if tag == 'polygon' else '')
    if tag == 'line': return f"M {n('x1', 0)} {n('y1', 0)} L {n('x2', 0)} {n('y2', 0)}"
    if tag in ('circle', 'ellipse'):
        x, y = n('cx', 0), n('cy', 0)
        rx, ry = (n('r'), n('r')) if tag == 'circle' else (n('rx'), n('ry'))
        if rx <= 0 or ry <= 0: raise ValueError('circle/ellipse radii must be positive')
        return f'M {x-rx} {y} A {rx} {ry} 0 1 0 {x+rx} {y} A {rx} {ry} 0 1 0 {x-rx} {y} Z'
    if tag == 'rect':
        x, y, w, h = n('x', 0), n('y', 0), n('width'), n('height')
        if w <= 0 or h <= 0: raise ValueError('rect dimensions must be positive')
        rx = n('rx', attrs.get('ry', 0)); ry = n('ry', attrs.get('rx', 0))
        if rx < 0 or ry < 0: raise ValueError('rect radii must be nonnegative')
        rx, ry = min(rx,w/2), min(ry,h/2)
        if rx == 0 or ry == 0: return f'M {x} {y} H {x+w} V {y+h} H {x} Z'
        return f'M {x+rx} {y} H {x+w-rx} A {rx} {ry} 0 0 1 {x+w} {y+ry} V {y+h-ry} A {rx} {ry} 0 0 1 {x+w-rx} {y+h} H {x+rx} A {rx} {ry} 0 0 1 {x} {y+h-ry} V {y+ry} A {rx} {ry} 0 0 1 {x+rx} {y} Z'
    raise ValueError('unsupported SVG element')

def compile_svg(source, steps=32, *, preserve_ids=False):
    if not isinstance(preserve_ids, bool): raise ValueError('preserve_ids must be boolean')
    if not isinstance(source, str) or len(source.encode('utf-8')) > 262144: raise ValueError('SVG too large')
    # Preflight before XML parsing: ignore valid comments for this scan only, then allow
    # a leading XML declaration. All remaining declarations/PIs fail closed.
    scan = re.sub(r'<!--(?:(?!--).)*-->', '', source, flags=re.S)
    scan = re.sub(r'^\s*<\?xml\s+[^?]*\?>', '', scan, count=1, flags=re.I)
    if re.search(r'<!|<\?', scan, re.I): raise ValueError('DTD, entities and processing instructions are not supported')
    try: root = ET.fromstring(source)
    except ET.ParseError as error: raise ValueError('invalid SVG XML') from error
    def local(tag):
        if tag.startswith('{http://www.w3.org/2000/svg}'): return tag.split('}', 1)[1]
        if '{' in tag or ':' in tag: raise ValueError('unsupported SVG namespace')
        return tag
    if local(root.tag) != 'svg': raise ValueError('root must be svg')
    if set(root.attrib) - {'viewBox', 'width', 'height', 'style', 'fill', 'stroke', 'stroke-width', 'fill-rule'}: raise ValueError('unsupported svg attributes')
    view = re.split(r'[\s,]+', root.get('viewBox', '').strip())
    if len(view) != 4: raise ValueError('explicit viewBox required')
    view = [_num(v) for v in view]
    if view[2] <= 0 or view[3] <= 0: raise ValueError('invalid viewBox')
    for key in ('width', 'height'):
        if key in root.attrib and _num(root.get(key)) <= 0: raise ValueError('invalid dimensions')
    # Static, local, explicit-coordinate linear/radial gradients only. No resources are fetched.
    gradients = {}; defs_count = 0
    for node in root:
        if local(node.tag) != 'defs': continue
        defs_count += 1
        if defs_count > 1 or node.attrib or (node.text and node.text.strip()) or (node.tail and node.tail.strip()): raise ValueError('invalid SVG defs')
        for gradient in node:
            tag = local(gradient.tag)
            keys = {'linearGradient': ('x1','y1','x2','y2'), 'radialGradient': ('cx','cy','r')}.get(tag)
            if not keys or set(gradient.attrib) != {'id','gradientUnits',*keys} or gradient.get('gradientUnits') != 'userSpaceOnUse' or (gradient.text and gradient.text.strip()) or (gradient.tail and gradient.tail.strip()): raise ValueError('unsupported SVG gradient')
            name = gradient.get('id')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}', name) or name in gradients or len(gradients) >= 16: raise ValueError('invalid SVG gradient id')
            coords = {k:_num(gradient.get(k)) for k in keys}
            if tag == 'linearGradient' and math.hypot(coords['x2']-coords['x1'], coords['y2']-coords['y1']) < 1e-9: raise ValueError('SVG gradient endpoints must differ')
            if tag == 'radialGradient' and coords['r'] < 1e-9: raise ValueError('SVG gradient radius must be positive')
            stops = []
            for stop in gradient:
                if local(stop.tag) != 'stop' or set(stop.attrib) != {'offset','stop-color'} or len(stop) or (stop.text and stop.text.strip()) or (stop.tail and stop.tail.strip()): raise ValueError('unsupported SVG gradient stop')
                offset = _num(stop.get('offset')); color = _paint(stop.get('stop-color'))
                if color is None or not 0 <= offset <= 1 or (stops and offset <= stops[-1]['offset']): raise ValueError('invalid SVG gradient stop')
                stops.append({'offset':offset,'color':color})
            if not 2 <= len(stops) <= 16 or stops[0]['offset'] != 0 or stops[-1]['offset'] != 1: raise ValueError('SVG gradient needs 2..16 ordered stops from 0 to 1')
            gradients[name] = {'type':'linear' if tag == 'linearGradient' else 'radial',**coords,'stops':stops}
    shapes = []; shape_ids = set()
    def walk(node, inherited, parent_matrix, depth=0):
        if depth > 16: raise ValueError('SVG groups too deep')
        if node.text and node.text.strip(): raise ValueError('text not supported')
        for child in node:
            tag = local(child.tag)
            if tag == 'defs' and node is root: continue
            if child.tail and child.tail.strip(): raise ValueError('text not supported')
            geometry = {'path': {'d'}, 'rect': {'x','y','width','height','rx','ry'}, 'circle': {'cx','cy','r'}, 'ellipse': {'cx','cy','rx','ry'}, 'line': {'x1','y1','x2','y2'}, 'polygon': {'points'}, 'polyline': {'points'}}
            if tag != 'g' and tag not in geometry: raise ValueError(f'unsupported SVG element: {tag}')
            allowed = {'fill', 'stroke', 'stroke-width', 'fill-rule', 'transform', 'style'} | ((geometry[tag] | {'opacity', 'id'}) if tag != 'g' else set())
            if set(child.attrib)-allowed: raise ValueError('unsupported SVG attribute')
            style = dict(inherited)
            for key in ('fill', 'stroke', 'stroke-width', 'fill-rule'):
                if key in child.attrib: style[key] = child.get(key)
            inline = _inline_style(child.get('style', ''), allow_opacity=tag != 'g')
            style.update({key:value for key,value in inline.items() if key != 'opacity'})
            matrix = _mul(parent_matrix, _transform(child.get('transform', '')))
            if tag == 'g': walk(child, style, matrix, depth+1); continue
            if len(child): raise ValueError('path cannot contain elements')
            if style['fill'] is None: raise ValueError('explicit fill required; use none for stroke-only paths')
            fill, stroke = _paint(style['fill'], allow_reference=True), _paint(style['stroke'])
            if isinstance(fill, str) and fill.startswith('url('):
                name = fill[5:-1]
                if name not in gradients: raise ValueError('unknown local SVG gradient')
                # Similarity transforms preserve the gradient projection; nonuniform scale/shear do not.
                a,b,c,d,e,f = matrix; sx, sy = math.hypot(a,b), math.hypot(c,d)
                if sx == 0 or sy == 0 or abs(sx-sy) > 1e-9*max(sx,sy) or abs(a*c+b*d) > 1e-9*sx*sy: raise ValueError('gradient-filled SVG shapes require uniform orthogonal transform')
                fill = copy.deepcopy(gradients[name])
                if fill['type'] == 'linear':
                    fill['x1'],fill['y1'] = _transform_point(matrix,fill['x1'],fill['y1'])
                    fill['x2'],fill['y2'] = _transform_point(matrix,fill['x2'],fill['y2'])
                    if math.hypot(fill['x2']-fill['x1'],fill['y2']-fill['y1']) < 1e-9: raise ValueError('transformed gradient is too small')
                else:
                    fill['cx'],fill['cy'] = _transform_point(matrix,fill['cx'],fill['cy']); fill['r'] = _num(fill['r']*sx)
                    if fill['r'] < 1e-9: raise ValueError('transformed gradient is too small')
            width = _num(style['stroke-width']); opacity = _num(inline.get('opacity', child.get('opacity', '1')))
            if width < 0 or not 0 <= opacity <= 1: raise ValueError('stroke width must be nonnegative and opacity must be 0..1')
            if fill is not None and style['fill-rule'] != 'evenodd': raise ValueError('filled paths require explicit evenodd fill-rule')
            if style['fill-rule'] not in ('evenodd', 'nonzero'): raise ValueError('unsupported fill rule')
            a,b,c,d,e,f = matrix; sx, sy = math.hypot(a,b), math.hypot(c,d)
            if stroke is not None and width > 0 and (sx == 0 or sy == 0 or abs(sx-sy) > 1e-9*max(sx,sy) or abs(a*c+b*d) > 1e-9*sx*sy): raise ValueError('stroked SVG requires uniform orthogonal transform')
            contours = parse_d(_shape_data(tag, child.attrib), steps)
            for contour in contours:
                for point in contour['points']:
                    x, y = point['x'], point['y']; point['x'], point['y'] = _num(a*x+c*y+e), _num(b*x+d*y+f)
            shape_id = child.get('id') if preserve_ids else f'svg-{len(shapes)}'
            if preserve_ids and (not shape_id or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]{0,63}', shape_id) or shape_id in shape_ids or shape_id in gradients): raise ValueError('preserve-ids requires unique safe IDs for every shape, distinct from gradient IDs')
            shape_ids.add(shape_id)
            shapes.append({'id': shape_id, 'fill': fill, 'stroke': stroke, 'strokeWidth': _num(width*sx) if stroke is not None else 0, 'opacity': opacity, 'contours': contours})
            if len(shapes) > 128: raise ValueError('too many SVG paths')
            if sum(len(c['points']) for s in shapes for c in s['contours']) > 65536: raise ValueError('SVG exceeds point budget')
    root_style = {'fill': None, 'stroke': 'none', 'stroke-width': '1', 'fill-rule': 'nonzero'}
    root_style.update({key: root.get(key) for key in root_style if key in root.attrib})
    root_style.update(_inline_style(root.get('style', '')))
    walk(root, root_style, [1,0,0,1,0,0])
    if not shapes: raise ValueError('SVG contains no paths')
    return {'version': 1, 'viewBox': view, 'shapes': shapes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path); parser.add_argument('output', type=Path); parser.add_argument('--steps', type=int, default=32)
    parser.add_argument('--preserve-ids', action='store_true', help='require and retain a safe unique id on every shape')
    args = parser.parse_args()
    if args.output.exists(): raise SystemExit('Output exists; choose a fresh path')
    plan = compile_svg(args.input.read_text(encoding='utf-8'), args.steps, preserve_ids=args.preserve_ids)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as f: json.dump(plan, f, ensure_ascii=False, indent=2); f.write('\n')


if __name__ == '__main__': main()
