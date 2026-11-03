"""Pillow adapter for validated geometry bindings. No text, scale transform or invented colors."""
from __future__ import annotations

from PIL import Image, ImageColor, ImageDraw

from motion_geometry import stroke_segments

# Palette v2: tests compare every token with the canonical brand JSON and K/R tokens.
PALETTE = {'red': '#CB271B', 'redBright': '#CB0801', 'redDeep': '#9F0803', 'ink': '#0A0A0A',
           'inkSoft': '#71717A', 'paper': '#F3F2F1', 'gray1': '#D8D7D5', 'gray2': '#C9C5C2',
           'gray3': '#BFBAB7', 'gray4': '#A3A2A0', 'salmon': '#D97F68', 'blush': '#D5AEA6'}


def draw_geometry(image, items):
    if image.mode not in ('RGB', 'RGBA'): raise ValueError('geometry target must be RGB/RGBA')
    for item in items:
        p = item['props']
        if p['opacity'] == 0: continue
        overlay = Image.new('RGBA', image.size); draw = ImageDraw.Draw(overlay)
        def color(token):
            return None if token is None else (*ImageColor.getrgb(PALETTE[token]), round(255*p['opacity']))
        fill, stroke = color(item['fill']), color(item['stroke']) if p['strokeWidth'] > 0 else None
        width = max(1, round(p['strokeWidth']))
        if item['kind'] == 'rect':
            draw.rounded_rectangle((p['x'], p['y'], p['x']+p['w'], p['y']+p['h']), radius=p['r'], fill=fill, outline=stroke, width=width)
        elif item['kind'] == 'circle':
            draw.ellipse((p['x']-p['r'], p['y']-p['r'], p['x']+p['r'], p['y']+p['r']), fill=fill, outline=stroke, width=width)
        else:
            if fill is not None: draw.polygon([(v['x'], v['y']) for v in p['points']], fill=fill)
            if stroke is not None:
                for line in stroke_segments(p['points'], p):
                    draw.line([(v['x'], v['y']) for v in line], fill=stroke, width=width, joint='curve')
                    for point in [line[0], line[-1]]:
                        r = width/2; draw.ellipse((point['x']-r, point['y']-r, point['x']+r, point['y']+r), fill=stroke)
        if image.mode == 'RGBA': image.alpha_composite(overlay)
        else: image.paste(Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB'))
    return image
