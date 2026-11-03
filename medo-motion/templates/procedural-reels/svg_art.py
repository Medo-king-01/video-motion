"""Pillow renderer for bounded, precompiled SVG plans; no SVG/XML evaluation at runtime."""
from __future__ import annotations

import math
from PIL import Image, ImageChops, ImageColor, ImageDraw
from geometry_draw import PALETTE
from motion_geometry import stroke_segments


def _number(x):
    return type(x) in (int, float) and math.isfinite(x) and abs(x) <= 1000000


def validate_svg_art(plan):
    if not isinstance(plan, dict) or type(plan.get('version')) is not int or plan.get('version') != 1: raise ValueError('invalid SVG plan')
    v, shapes = plan.get('viewBox'), plan.get('shapes')
    if not isinstance(v, list) or len(v) != 4 or not all(map(_number, v)) or min(v[2:]) <= 0 or not isinstance(shapes, list) or not 1 <= len(shapes) <= 128: raise ValueError('invalid SVG plan')
    ids = set(); total = 0
    for s in shapes:
        if not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'] or s['id'] in ids or 'fill' not in s or 'stroke' not in s or any(t is not None and (not isinstance(t, str) or t not in PALETTE) for t in (s.get('fill'), s.get('stroke'))) or not _number(s.get('strokeWidth')) or s['strokeWidth'] < 0 or not _number(s.get('opacity')) or s['opacity'] != 1: raise ValueError('invalid SVG shape')
        ids.add(s['id']); contours = s.get('contours')
        if not isinstance(contours, list) or not 1 <= len(contours) <= 64: raise ValueError('invalid SVG contours')
        for c in contours:
            if not isinstance(c, dict) or not isinstance(c.get('closed'), bool) or not isinstance(c.get('points'), list) or not (3 if c['closed'] else 2) <= len(c['points']) <= 4096 or any(not isinstance(p, dict) or not _number(p.get('x')) or not _number(p.get('y')) for p in c['points']): raise ValueError('invalid SVG contour')
            total += len(c['points'])
            if total > 65536: raise ValueError('SVG point budget exceeded')
    return plan


def svg_placement(plan, options):
    validate_svg_art(plan); x, y, width, height = (options.get(k, d) for k, d in [('x', 0), ('y', 0), ('width', None), ('height', None)])
    if not all(map(_number, (x,y,width,height))) or width <= 0 or height <= 0: raise ValueError('invalid SVG placement')
    vx, vy, vw, vh = plan['viewBox']; scale = min(width/vw, height/vh)
    if not math.isfinite(scale) or scale <= 0 or scale > 1000000: raise ValueError('invalid SVG scale')
    px, py = x+(width-vw*scale)/2-vx*scale, y+(height-vh*scale)/2-vy*scale
    if not math.isfinite(px) or not math.isfinite(py): raise ValueError('invalid SVG placement')
    for shape in plan['shapes']:
        if shape['strokeWidth']*scale > 100000: raise ValueError('SVG stroke exceeds output budget')
        for contour in shape['contours']:
            for point in contour['points']:
                sx, sy = px+point['x']*scale, py+point['y']*scale
                if not math.isfinite(sx) or not math.isfinite(sy) or abs(sx) > 10000000 or abs(sy) > 10000000: raise ValueError('SVG coordinates exceed output budget')
    return {'scale': scale, 'x': px, 'y': py}


def draw_svg_art(image, plan, options):
    if image.mode not in ('RGB', 'RGBA'): raise ValueError('expected RGB/RGBA image')
    place = svg_placement(plan, options); progress = options.get('progress', 1)
    if not _number(progress) or not 0 <= progress <= 1: raise ValueError('invalid SVG stroke progress')
    def points(path): return [(place['x']+p['x']*place['scale'], place['y']+p['y']*place['scale']) for p in path]
    for s in plan['shapes']:
        overlay = Image.new('RGBA', image.size); draw = ImageDraw.Draw(overlay); alpha = round(255*s['opacity'])
        if s['fill'] is not None:
            mask = Image.new('1', image.size, 0)
            for c in s['contours']:
                part = Image.new('1', image.size, 0); ImageDraw.Draw(part).polygon(points(c['points']), fill=1)
                mask = ImageChops.logical_xor(mask, part)
            color = (*ImageColor.getrgb(PALETTE[s['fill']]), alpha)
            overlay.paste(Image.new('RGBA', image.size, color), (0,0), mask)
        if s['stroke'] is not None and s['strokeWidth'] > 0:
            stroke = (*ImageColor.getrgb(PALETTE[s['stroke']]), alpha); width = max(1, round(s['strokeWidth']*place['scale']))
            for c in s['contours']:
                for part in stroke_segments(c['points'], {'closed': c['closed'], 'end': progress}):
                    p = points(part); draw.line(p, fill=stroke, width=width, joint='curve')
                    for x, y in (p[0], p[-1]):
                        r = width/2; draw.ellipse((x-r,y-r,x+r,y+r), fill=stroke)
        if image.mode == 'RGBA': image.alpha_composite(overlay)
        else: image.paste(Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB'))
    return image
