"""Whole-word measured fitting with the existing HarfBuzz/FreeType backend, not guessed metrics."""
from __future__ import annotations

from arabic_shape import measure
from motion_geometry import fit_measured_text


def measure_text_fit(font_path, text, options):
    family, weight, low, high, step = (options.get(k, d) for k, d in [('family', None), ('weight', None), ('minSize', None), ('maxSize', None), ('step', 1)])
    max_w, max_h, pad, line_height, rtl = (options.get(k, d) for k, d in [('maxWidth', None), ('maxHeight', None), ('padding', 0), ('lineHeight', 1.3), ('rtl', True)])
    if any(type(x) is not int for x in (low, high, step)) or low < 1 or high > 512 or high < low or step < 1 or not isinstance(rtl, bool): raise ValueError('invalid font size search')
    if not isinstance(family, str) or type(weight) is not int or not 100 <= weight <= 900 or not isinstance(text, str) or not text.strip(): raise ValueError('explicit text/font required')
    candidates = []
    for size in range(high, low-1, -step):
        def metrics(s):
            w, h = measure(str(font_path), s, size, rtl=rtl)
            return {'text': s, 'w': w, 'h': h}
        lines, line = [], ''
        for word in text.split():
            nxt = f'{line} {word}' if line else word
            if line and metrics(nxt)['w'] > max_w-2*pad: lines.append(metrics(line)); line = word
            else: line = nxt
        if line: lines.append(metrics(line))
        candidates.append({'size': size, 'measuredBy': 'harfbuzz', 'lines': lines})
    return fit_measured_text({'text': text, 'font': {'family': family, 'weight': weight}, 'maxWidth': max_w, 'maxHeight': max_h, 'padding': pad, 'lineHeight': line_height, 'candidates': candidates})
