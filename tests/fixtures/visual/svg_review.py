"""P rendering from the compiled portable SVG plan, independently from K/R."""
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
from render_policy import compile_motion_policy  # noqa: E402
from svg_art import draw_svg_art  # noqa: E402


def main():
    plan = json.loads(Path(sys.argv[1]).read_text()); out = Path(sys.argv[2]); sheet = Image.new('RGB', (1080, 640))
    direction = {'scenes': [{'scene': 1, 'textStyles': {'label': 'softfade'}, 'fontStyles': {'label': {'family': 'Cairo', 'weight': 800}}}]}
    policy = compile_motion_policy({'version': 1, 'reduced': True, 'decorative': [{'track': 'stroke', 'value': 1}]})
    for i, t in enumerate([.1, .8, 1.6]):
        image = Image.new('RGB', (1080, 1920), '#F3F2F1')
        progress = policy.at({'stroke': min(1, t/1.5)})['stroke']
        draw_svg_art(image, plan, {'x': 80, 'y': 650, 'width': 430, 'height': 430, 'progress': min(1, t/1.5)})
        draw_svg_art(image, plan, {'x': 570, 'y': 650, 'width': 430, 'height': 430, 'progress': progress})
        frame = np.array(image)
        draw_directed_text(frame, 'رسم ثابت ومسارات آمنة', direction=direction, scene=1, role='label', element_id='title', t=t, start=0, end=2, cx=540, cy=300, size=56, color=(10,10,10), theme='light')
        image = Image.fromarray(frame); image.save(out / f'P-svg-{i}.png'); sheet.paste(image.resize((360,640)), (i*360,0))
    sheet.save(out / 'P-svg.png')


if __name__ == '__main__': main()
