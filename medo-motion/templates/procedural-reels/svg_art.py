"""Pillow renderer for bounded, precompiled SVG plans; no SVG/XML evaluation at runtime."""
from __future__ import annotations

import math

import numpy as np
from PIL import Image, ImageChops, ImageColor, ImageDraw
from geometry_draw import PALETTE
from motion_geometry import stroke_segments


def _number(x):
    return type(x) in (int, float) and abs(x) <= 1000000 and math.isfinite(x)


def _valid_fill(fill):
    if fill is None or isinstance(fill, str) and fill in PALETTE: return True
    if not isinstance(fill, dict): return False
    if fill.get('type') == 'linear':
        if set(fill) != {'type','x1','y1','x2','y2','stops'} or not all(_number(fill.get(k)) for k in ('x1','y1','x2','y2')) or math.hypot(fill['x2']-fill['x1'],fill['y2']-fill['y1']) < 1e-9: return False
    elif fill.get('type') == 'radial':
        if set(fill) != {'type','cx','cy','r','stops'} or not all(_number(fill.get(k)) for k in ('cx','cy','r')) or fill['r'] < 1e-9: return False
    else: return False
    stops = fill.get('stops')
    if not isinstance(stops, list) or not 2 <= len(stops) <= 16: return False
    for i, stop in enumerate(stops):
        if not isinstance(stop, dict) or set(stop) != {'offset','color'} or not _number(stop['offset']) or not 0 <= stop['offset'] <= 1 or not isinstance(stop['color'], str) or stop['color'] not in PALETTE: return False
        if (i == 0 and stop['offset'] != 0) or (i and stop['offset'] <= stops[i-1]['offset']) or (i == len(stops)-1 and stop['offset'] != 1): return False
    return True


def validate_svg_art(plan):
    if not isinstance(plan, dict) or type(plan.get('version')) is not int or plan.get('version') != 1: raise ValueError('invalid SVG plan')
    v, shapes = plan.get('viewBox'), plan.get('shapes')
    if not isinstance(v, list) or len(v) != 4 or not all(map(_number, v)) or min(v[2:]) <= 0 or not isinstance(shapes, list) or not 1 <= len(shapes) <= 128: raise ValueError('invalid SVG plan')
    ids = set(); total = 0
    for s in shapes:
        if not isinstance(s, dict) or not isinstance(s.get('id'), str) or not s['id'] or s['id'] in ids or 'fill' not in s or 'stroke' not in s or not _valid_fill(s.get('fill')) or (s.get('stroke') is not None and (not isinstance(s['stroke'], str) or s['stroke'] not in PALETTE)) or not _number(s.get('strokeWidth')) or s['strokeWidth'] < 0 or not _number(s.get('opacity')) or not 0 <= s['opacity'] <= 1: raise ValueError('invalid SVG shape')
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
        g = shape['fill']
        if isinstance(g, dict):
            if g['type'] == 'linear':
                endpoints = (px+g['x1']*scale, px+g['x2']*scale, py+g['y1']*scale, py+g['y2']*scale)
                extent = math.hypot((g['x2']-g['x1'])*scale, (g['y2']-g['y1'])*scale)
            else:
                endpoints = (px+g['cx']*scale,py+g['cy']*scale,g['r']*scale); extent = g['r']*scale
            if extent < 1e-9 or any(not math.isfinite(v) or abs(v) > 10000000 for v in endpoints): raise ValueError('SVG gradient exceeds output budget')
        for contour in shape['contours']:
            for point in contour['points']:
                sx, sy = px+point['x']*scale, py+point['y']*scale
                if not math.isfinite(sx) or not math.isfinite(sy) or abs(sx) > 10000000 or abs(sy) > 10000000: raise ValueError('SVG coordinates exceed output budget')
    return {'scale': scale, 'x': px, 'y': py}


def svg_stroke_windows(plan, options):
    """Resolve explicitly authored stroke windows against an already validated plan."""
    def interval(start, end, offset):
        if not all(map(_number, (start, end, offset))) or start < 0 or end > 1 or start > end:
            raise ValueError('invalid SVG stroke window')
        return {'start': start, 'end': end, 'offset': offset}
    base = interval(options.get('strokeStart', 0), options.get('progress', 1), options.get('strokeOffset', 0))
    supplied = options.get('strokeWindows', {})
    if not isinstance(supplied, dict): raise ValueError('invalid SVG stroke windows')
    by_id = {s['id']: s for s in plan['shapes']}; windows = {}
    for shape_id, entries in supplied.items():
        if shape_id not in by_id or not isinstance(entries, list) or len(entries) != len(by_id[shape_id]['contours']):
            raise ValueError('unknown shape or incorrect SVG contour window count')
        resolved = []
        for value in entries:
            if value is None: resolved.append(base); continue
            if not isinstance(value, dict) or set(value) - {'start', 'end', 'offset'} or 'start' not in value or 'end' not in value:
                raise ValueError('invalid SVG contour window')
            resolved.append(interval(value['start'], value['end'], value.get('offset', base['offset'])))
        windows[shape_id] = resolved
    return {'base': base, 'windows': windows}


def draw_svg_art(image, plan, options):
    if image.mode not in ('RGB', 'RGBA'): raise ValueError('expected RGB/RGBA image')
    place = svg_placement(plan, options); stroke_options = svg_stroke_windows(plan, options)
    if image.width*image.height > 4194304 and any(0 < shape['opacity'] < 1 for shape in plan['shapes']): raise ValueError('SVG opacity requires bounded image')
    def points(path): return [(place['x']+p['x']*place['scale'], place['y']+p['y']*place['scale']) for p in path]
    for s in plan['shapes']:
        if s['opacity'] == 0: continue
        overlay = Image.new('RGBA', image.size); draw = ImageDraw.Draw(overlay); alpha = 255
        if s['fill'] is not None:
            mask = Image.new('1', image.size, 0)
            for c in s['contours']:
                part = Image.new('1', image.size, 0); ImageDraw.Draw(part).polygon(points(c['points']), fill=1)
                mask = ImageChops.logical_xor(mask, part)
            if isinstance(s['fill'], str):
                color = (*ImageColor.getrgb(PALETTE[s['fill']]), alpha)
                overlay.paste(Image.new('RGBA', image.size, color), (0,0), mask)
            else:
                bounds = mask.getbbox()
                if bounds:
                    left,top,right,bottom = bounds
                    if (right-left)*(bottom-top) > 4194304: raise ValueError('SVG gradient exceeds raster budget')
                    g = s['fill']; scale = place['scale']
                    yy,xx = np.ogrid[top:bottom,left:right]
                    if g['type'] == 'linear':
                        x1,y1 = place['x']+g['x1']*scale,place['y']+g['y1']*scale
                        dx,dy = (g['x2']-g['x1'])*scale,(g['y2']-g['y1'])*scale
                        progress = ((xx+.5-x1)*dx+(yy+.5-y1)*dy)/(dx*dx+dy*dy)
                    else:
                        cx,cy = place['x']+g['cx']*scale,place['y']+g['cy']*scale
                        progress = np.hypot(xx+.5-cx,yy+.5-cy)/(g['r']*scale)
                    offsets = [stop['offset'] for stop in g['stops']]
                    colors = [ImageColor.getrgb(PALETTE[stop['color']]) for stop in g['stops']]
                    pixels = np.empty((bottom-top,right-left,4),dtype=np.uint8)
                    for channel in range(3): pixels[:,:,channel] = np.rint(np.interp(progress,offsets,[color[channel] for color in colors])).astype(np.uint8)
                    pixels[:,:,3] = alpha
                    overlay.paste(Image.fromarray(pixels), (left,top), mask.crop(bounds))
        if s['stroke'] is not None and s['strokeWidth'] > 0:
            stroke = (*ImageColor.getrgb(PALETTE[s['stroke']]), alpha); width = max(1, round(s['strokeWidth']*place['scale']))
            for ci, c in enumerate(s['contours']):
                window = stroke_options['windows'].get(s['id'])
                for part in stroke_segments(c['points'], {'closed': c['closed'], **(window[ci] if window is not None else stroke_options['base'])}):
                    p = points(part); draw.line(p, fill=stroke, width=width, joint='curve')
                    for x, y in (p[0], p[-1]):
                        r = width/2; draw.ellipse((x-r,y-r,x+r,y+r), fill=stroke)
        if s['opacity'] != 1: overlay.putalpha(overlay.getchannel('A').point(lambda a: round(a*s['opacity'])))
        if image.mode == 'RGBA': image.alpha_composite(overlay)
        else: image.paste(Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB'))
    return image


def draw_svg_crossfade(image, source, target, amount, placement):
    """Fade independently rendered SVG groups; no geometry/topology interpolation."""
    if image.mode not in ('RGB', 'RGBA') or image.width*image.height > 4194304: raise ValueError('SVG crossfade requires bounded RGB/RGBA image')
    if not _number(amount) or not 0 <= amount <= 1: raise ValueError('invalid SVG crossfade amount')
    if not isinstance(placement, dict) or set(placement)-{'x', 'y', 'width', 'height'}: raise ValueError('invalid SVG crossfade placement')
    svg_placement(source, placement); svg_placement(target, placement)
    for plan, weight in ((source, 1-amount), (target, amount)):
        if weight == 0: continue
        layer = Image.new('RGBA', image.size, (0,0,0,0)); draw_svg_art(layer, plan, placement)
        layer.putalpha(layer.getchannel('A').point(lambda alpha: round(alpha*weight)))
        if image.mode == 'RGBA': image.alpha_composite(layer)
        else: image.paste(layer.convert('RGB'), (0,0), layer.getchannel('A'))
    return image
