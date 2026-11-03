"""Independent P rendering of the same JSON fixture, not screenshots of a browser."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT / 'medo-motion/templates/procedural-reels'))
os.environ['REEL_DIR'] = str(ROOT)
os.environ['REEL_FONT'] = str(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf')
from captions import draw_directed_text  # noqa: E402
from geometry_draw import PALETTE, draw_geometry  # noqa: E402
from motion_geometry import compile_bindings, compile_layout, compile_morph  # noqa: E402
from motion_plan import compile_sequence  # noqa: E402
from text_measure import measure_text_fit  # noqa: E402


def main():
    spec = json.loads(Path(sys.argv[1]).read_text()); out = Path(sys.argv[2])
    group, sequence, shape, paint = compile_layout(spec['layout']), compile_sequence(spec['motion']), compile_morph(spec['morph']), compile_bindings(spec['bindings'])
    fit = measure_text_fit(os.environ['REEL_FONT'], 'قياس على الخط الحقيقي', {'family': 'Cairo', 'weight': 800, 'minSize': 32, 'maxSize': 42, 'step': 2, 'maxWidth': 900, 'maxHeight': 100, 'padding': 12})
    if not fit['fits']: raise ValueError('P font fit failed')
    (out / 'P-font-fit.json').write_text(json.dumps(fit, ensure_ascii=False, indent=2)+'\n')
    sheet = Image.new('RGB', (1080, 640))
    for i, t in enumerate([.1, .9, 2.8]):
        cards, values = group.at(t), sequence.at(t); values['shape'] = shape.at(values['morph'])
        for key in ['a', 'b', 'c', 'd']:
            for k in ['x', 'y', 'w', 'h', 'r', 'opacity']: values[f'{key}.{k}'] = 100 if k in ('w', 'h') else 0
        for card in cards:
            for k, v in {**card['box'], 'opacity': card['opacity']}.items(): values[f'{card["id"]}.{k}'] = v
        image = Image.new('RGB', (1080, 1920), PALETTE['paper']); draw_geometry(image, paint.at(values))
        x, y = (1080-fit['w'])/2, 1210
        draw_geometry(image, [{'id': 'measured', 'kind': 'rect', 'fill': 'gray1', 'stroke': 'ink', 'props': {'x': x, 'y': y, 'w': fit['w'], 'h': fit['h'], 'r': 16, 'opacity': 1, 'strokeWidth': 3}}])
        frame = np.array(image)
        def text(copy, element, cx, cy, size, frame=frame, t=t):
            draw_directed_text(frame, copy, direction=spec['direction'], scene=1, role='label', element_id=element, t=t, start=0, end=3, cx=cx, cy=cy, size=size, color=(10, 10, 10), theme='light')
        text('عناصر بنفس الهوية', 'title', 540, 280, 58)
        for card in cards:
            if card['phase'] == 'hold' and card['opacity'] == 1: text(f'عنصر {card["id"].upper()}', f'card-{card["id"]}', card['box']['x']+card['box']['w']/2, card['box']['y']+card['box']['h']/2, 44)
        for j, line in enumerate(fit['lines']): text(line['text'], f'fit-{j}', x+line['x']+line['w']/2, y+line['y']+line['h']/2, fit['size'])
        image = Image.fromarray(frame); image.save(out / f'P-geometry-{i}.png'); sheet.paste(image.resize((360, 640)), (i*360, 0))
    sheet.save(out / 'P-geometry.png')


if __name__ == '__main__': main()
