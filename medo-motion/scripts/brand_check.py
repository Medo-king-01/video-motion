#!/usr/bin/env python3
"""Brand guard for palette v2 (12 colours + one derived shade).

Usage:
  python brand_check.py                     -> validate brand.json, WCAG contrast of the approved text/background pairs
  python brand_check.py --project <dir>     -> also check palette drift in the project's engine files (lib.py, lib/brand.js)
  python brand_check.py --frame frame.png   -> report how much of a frame is on-palette (rough, for contact-sheet QA)

Read-only: installs nothing, uses no network.
"""
import json, sys, re, argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent


def lum(c):
    f = lambda v: (v / 255 / 12.92) if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    r, g, b = (f(v) for v in c)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted([lum(a), lum(b)], reverse=True)
    return (la + 0.05) / (lb + 0.05)


def hexof(rgb):
    return '#%02X%02X%02X' % tuple(rgb)


ap = argparse.ArgumentParser()
ap.add_argument('--project')
ap.add_argument('--frame')
a = ap.parse_args()

d = json.load(open(HERE / 'brand' / 'brand.json', encoding='utf-8'))
P = {k: v['rgb'] for k, v in d['palette'].items() if v.get('rgb')}
SHADOW = d['derived']['ink_shadow']['rgb']
bad = warn = 0

# ---- 1. the palette itself ---------------------------------------------------
print(f"Palette v2: {len(P)} colours")
if len(P) != 12:
    print(f"  FAIL palette must hold exactly 12 colours, found {len(P)}")
    bad += 1
for k, v in d['palette'].items():
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', v['hex']) or [int(v['hex'][i:i + 2], 16) for i in (1, 3, 5)] != v['rgb']:
        print(f"  FAIL {k}: hex {v['hex']} != rgb {v['rgb']}")
        bad += 1
if not all(P['x'] is not None for x in []):
    pass
# the 12 hex values must stay inside the light/dark ramps the brief uses
for side, k in (('dark', 'top'), ('dark', 'bottom'), ('light', 'top'), ('light', 'bottom')):
    if list(d['backgrounds'][side][k]) not in [list(v) for v in P.values()] + [SHADOW]:
        print(f'  FAIL background {side}.{k} is not a palette colour')
        bad += 1

# ---- 2. approved pairs -------------------------------------------------------
pairs = [
    ('paper', 'ink', 4.5, 'caption text on plate / text on dark'),
    ('paper', 'red_deep', 4.5, 'paper on deep red'),
    ('ink', 'paper', 4.5, 'ink on light background'),
    ('ink', 'gray_1', 4.5, 'ink on cards (bottom of light ramp)'),
    ('ink', 'gray_2', 4.5, 'ink on inactive fill'),
    ('red', 'paper', 3.0, 'red keyword on light (large)'),
    ('red_bright', 'paper', 3.0, 'bright red on light (large)'),
    ('blush', 'ink', 4.5, 'blush keyword on dark'),
    ('gray_4', 'ink', 3.0, 'secondary text on dark (large only)'),
    ('salmon', 'ink', 3.0, 'salmon keyword on dark (large)'),
]
print('Contrast of approved pairs:')
for t, b, mn, label in pairs:
    r = ratio(P[t], P[b])
    ok = r >= mn
    bad += (not ok)
    print(f"  {'OK ' if ok else 'LOW'} {r:5.2f}:1 (min {mn}) {label}")

print('Forbidden-pair sanity (these SHOULD stay low):')
for t, b, mn, label in (('red', 'ink', 4.5, 'red text on dark (below body bar; rule: use salmon anyway)'),
                        ('gray_4', 'paper', 4.6, 'gray_4 for body text on light'),
                        ('salmon', 'paper', 4.6, 'salmon for body text on light'),
                        ('gray_3', 'paper', 4.6, 'gray_3 text on light')):
    r = ratio(P[t], P[b])
    if r >= mn:
        print(f'  FAIL {r:5.2f}:1 {label}')
        bad += 1
    else:
        print(f'  OK  {r:5.2f}:1 {label} (blocked as intended)')

if list(SHADOW) != [3, 3, 3] or not all(s < i for s, i in zip(SHADOW, P['ink'])):
    print('  WARN ink_shadow is not the locked v2.6 derived value (#030303, darker than ink)')
    warn += 1

# ---- 3. drift in a real project ---------------------------------------------
PY_NAMES = {'RED': 'red', 'DRED': 'red_deep', 'WHITE': 'paper', 'EMER': 'blush', 'TEAL': 'ink_soft',
            'YEL': 'salmon', 'BLACK': 'ink_shadow', 'INK': 'ink', 'GRAY': 'gray_4', 'LGRAY': 'gray_2'}
JS_NAMES = {'red': 'red', 'redBright': 'red_bright', 'redDeep': 'red_deep', 'ink': 'ink', 'inkSoft': 'ink_soft',
            'paper': 'paper', 'gray1': 'gray_1', 'gray2': 'gray_2', 'gray3': 'gray_3', 'gray4': 'gray_4',
            'salmon': 'salmon', 'blush': 'blush', 'inkShadow': 'ink_shadow'}
BG = dict(P, ink_shadow=SHADOW)
allowed = {v['hex'].upper() for v in d['palette'].values()} | {d['derived']['ink_shadow']['hex'].upper()}

if a.project:
    root = Path(a.project)
    libpy = next((c for c in [root / 'lib.py', root / 'procedural-reels' / 'lib.py'] if c.is_file()), None)
    if libpy is not None:
        s = libpy.read_text(encoding='utf-8')
        for n, k in PY_NAMES.items():
            m = re.search(r'\b' + n + r'=\((\d+),(\d+),(\d+)\)', s)
            if m and list(map(int, m.groups())) != BG[k]:
                print('  DRIFT lib.py', n, m.groups(), '!= brand', BG[k])
                bad += 1
        print('  engine P palette checked (lib.py)')
    else:
        print('  engine P: no lib.py at project root (skipped)')

    js = next((c for c in [root / 'src' / 'lib' / 'brand.js', root / 'lib' / 'brand.js', root / 'brand.js',
                           root / 'render' / 'lib' / 'brand.js'] if c.is_file()), None)
    if js:
        j = js.read_text(encoding='utf-8')
        dj = 0
        for key, bk in JS_NAMES.items():
            m = re.search(key + r"\s*:\s*'(#[0-9A-Fa-f]{6})'", j)
            exp = hexof(BG[bk])
            if m is None:
                print(f'  DRIFT brand.js: {key} not found'); bad += 1; dj += 1
            elif m.group(1).upper() != exp:
                print(f'  DRIFT brand.js {key} {m.group(1)} != brand {exp}'); bad += 1; dj += 1
        for key, side, end in (('bgDarkTop', 'dark', 'top'), ('bgDarkBottom', 'dark', 'bottom'),
                               ('bgLightTop', 'light', 'top'), ('bgLightBottom', 'light', 'bottom')):
            m = re.search(key + r"\s*:\s*'(#[0-9A-Fa-f]{6})'", j)
            exp = hexof(d['backgrounds'][side][end])
            if m is None:
                print(f'  DRIFT brand.js: {key} missing (background gradient)'); bad += 1; dj += 1
            elif m.group(1).upper() != exp:
                print(f'  DRIFT brand.js {key} {m.group(1)} != brand {exp}'); bad += 1; dj += 1
        mf = re.search(r"font\s*:\s*\{\s*ar\s*:\s*'([^']+)'", j)
        fallback_ar = d['typography']['type_system']['fallback']['arabic']
        if mf and mf.group(1) != fallback_ar:
            print(f"  DRIFT brand.js font.ar '{mf.group(1)}' != brand fallback '{fallback_ar}'"); bad += 1; dj += 1
        for key, bk in (('captionY', 'caption_center_y'), ('progressY', 'progress_bar_y'), ('margin', 'margin_px'),
                        ('belowIsDead', 'nothing_important_below_y')):
            mv = re.search(key + r'\s*:\s*(\d+)', j)
            if mv and int(mv.group(1)) != d['safe_zone'][bk]:
                print(f'  DRIFT brand.js {key} {mv.group(1)} != brand {d["safe_zone"][bk]}'); bad += 1; dj += 1
        # any colour literal in the engine must be one of the 12 + derived shade
        off = set()
        for f in sorted(root.rglob('*.js')):
            if 'node_modules' in f.parts or f.name.endswith('.min.js'):
                continue
            for h in re.findall(r"#[0-9A-Fa-f]{6}", f.read_text(encoding='utf-8')):
                if h.upper() not in allowed:
                    off.add((f.name, h))
        if off:
            for name, h in sorted(off):
                print(f'  OFF-PALETTE {name}: {h}')
            bad += len(off)
            dj += len(off)
        print('  engine K tokens checked (' + str(js.relative_to(root)) + ')' if not dj else f'  engine K: {dj} drift(s)')
    else:
        print('  engine K: no lib/brand.js found (skipped)')

    # Engine R uses a TypeScript brand mirror so it can bundle locally with Remotion.
    ts = next((c for c in [root / 'src' / 'brand.ts', root / 'remotion' / 'src' / 'brand.ts'] if c.is_file()), None)
    if ts is not None:
        source = ts.read_text(encoding='utf-8')
        dr = 0
        for key, bk in JS_NAMES.items():
            m = re.search(r'\b' + re.escape(key) + r"\s*:\s*'(#[0-9A-Fa-f]{6})'", source)
            expected = hexof(BG[bk])
            if m is None:
                print(f'  DRIFT brand.ts: {key} not found'); bad += 1; dr += 1
            elif m.group(1).upper() != expected:
                print(f'  DRIFT brand.ts {key} {m.group(1)} != brand {expected}'); bad += 1; dr += 1
        for key, side, end in (('bgDarkTop', 'dark', 'top'), ('bgDarkBottom', 'dark', 'bottom'),
                               ('bgLightTop', 'light', 'top'), ('bgLightBottom', 'light', 'bottom')):
            m = re.search(r'\b' + key + r"\s*:\s*'(#[0-9A-Fa-f]{6})'", source)
            expected = hexof(d['backgrounds'][side][end])
            if m is None:
                print(f'  DRIFT brand.ts: {key} missing'); bad += 1; dr += 1
            elif m.group(1).upper() != expected:
                print(f'  DRIFT brand.ts {key} {m.group(1)} != brand {expected}'); bad += 1; dr += 1
        mf = re.search(r"font\s*:\s*'([^']+)'", source)
        fallback_ar = d['typography']['type_system']['fallback']['arabic']
        if not mf or mf.group(1) != fallback_ar:
            print('  DRIFT brand.ts font != brand fallback Arabic font'); bad += 1; dr += 1
        for f in sorted([*root.rglob('*.ts'), *root.rglob('*.tsx')]):
            if 'node_modules' in f.parts:
                continue
            for h in re.findall(r"#[0-9A-Fa-f]{6}", f.read_text(encoding='utf-8')):
                if h.upper() not in allowed:
                    print(f'  OFF-PALETTE {f.name}: {h}'); bad += 1; dr += 1
        print('  engine R tokens checked (' + str(ts.relative_to(root)) + ')' if not dr else f'  engine R: {dr} drift(s)')
    else:
        print('  engine R: no src/brand.ts found (skipped)')

    # any colour literal in engine P's python must be palette or derived too
    allowed = {tuple(v['rgb']) for v in d['palette'].values()} | {tuple(SHADOW)}
    off = set()
    TUP = re.compile(r'(?<![\d.])(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})(?!\s*,\s*\d)')
    for f in sorted(root.glob('*.py')):
        if f.name in ('sfx.py', 'mix.py'):      # audio params, not colours
            continue
        for m in TUP.finditer(f.read_text(encoding='utf-8')):
            tup = tuple(map(int, m.groups()))
            if tup not in allowed:
                off.add((f.name, tup))
    if off:
        for name, t in sorted(off):
            print(f'  OFF-PALETTE {name}: rgb{t}')
        bad += len(off)

# ---- 4. optional frame audit -------------------------------------------------
if a.frame:
    from PIL import Image
    import numpy as np
    im = np.asarray(Image.open(a.frame).convert('RGB').resize((270, 480))).reshape(-1, 3).astype(int)
    pal = np.array(list(P.values()) + [SHADOW,
                                      d['backgrounds']['dark']['top'], d['backgrounds']['dark']['bottom'],
                                      d['backgrounds']['light']['top'], d['backgrounds']['light']['bottom']])
    dist = np.sqrt(((im[:, None, :] - pal[None, :, :]) ** 2).sum(2)).min(1)
    on = (dist < 60).mean()
    print(f'On-palette pixels (within 60 RGB units): {on*100:.0f}%  '
          '(illustrated characters/skin tones lower this; <55% on a non-character scene = check colours)')

print('RESULT:', ('PASS' if not bad else f'{bad} issue(s)') + (f' + {warn} known warning(s)' if warn else ''))
sys.exit(1 if bad else 0)
