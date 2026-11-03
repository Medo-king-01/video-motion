"""Independent P render of the same compiled plans and nested timeline."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.append(str(ROOT / 'medo-motion/templates/procedural-reels'))
os.environ['REEL_DIR'] = str(ROOT)
os.environ['REEL_FONT'] = str(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf')
from captions import draw_directed_text  # noqa: E402
from motion_plan import compile_nested_sequence  # noqa: E402
from svg_art import draw_svg_art  # noqa: E402
from svg_morph import compile_svg_morph  # noqa: E402


def main():
    proof = json.loads(Path(sys.argv[1]).read_text()); out = Path(sys.argv[2]); sheet = Image.new('RGB', (1080,640))
    seq = compile_nested_sequence(proof['sequence']); morph = compile_svg_morph({'version': 1, 'from': proof['from'], 'to': proof['to'], 'count': 32})
    direction = {'scenes':[{'scene':1,'textStyles':{'label':'softfade'},'fontStyles':{'label':{'family':'Cairo','weight':800}}}]}
    for i, t in enumerate([.1,1.05,2.2]):
        values = seq.at(t); image = Image.new('RGB', (1080,1920), '#F3F2F1')
        draw_svg_art(image, morph.at(values['group/shape/value']), {'x':190,'y':550,'width':700,'height':700})
        draw = ImageDraw.Draw(image); draw.rectangle((340,1370,739,1377),fill='#0A0A0A')
        accent = round(400*values['group/accent'])
        if accent: draw.rectangle((340,1370,340+accent-1,1377),fill='#CB271B')
        frame = np.array(image)
        draw_directed_text(frame, 'تحول يحافظ على الفتحة', direction=direction, scene=1, role='label', element_id='title', t=t, start=0, end=2.4, cx=540, cy=280, size=58, color=(10,10,10), theme='light')
        image=Image.fromarray(frame); image.save(out / f'P-morph-{i}.png'); sheet.paste(image.resize((360,640)),(i*360,0))
    sheet.save(out / 'P-morph.png')


if __name__ == '__main__': main()
