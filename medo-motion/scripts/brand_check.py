#!/usr/bin/env python3
"""Brand guard. Usage:
  python brand_check.py                      -> validate brand.json, WCAG contrast of the approved text/background pairs,
                                                and (if a procedural-reels project is given with --project) palette drift vs lib.py
  python brand_check.py --frame frame.png    -> report how much of a frame is on-palette (rough, for contact-sheet QA)
Read-only: installs nothing, uses no network."""
import json, sys, re, argparse
from pathlib import Path
HERE=Path(__file__).resolve().parent.parent
def lum(c):
    f=lambda v:(v/255/12.92) if v/255<=0.03928 else ((v/255+0.055)/1.055)**2.4
    r,g,b=[f(v) for v in c]; return 0.2126*r+0.7152*g+0.0722*b
def ratio(a,b):
    la,lb=sorted([lum(a),lum(b)],reverse=True); return (la+0.05)/(lb+0.05)
ap=argparse.ArgumentParser(); ap.add_argument('--project'); ap.add_argument('--frame'); a=ap.parse_args()
d=json.load(open(HERE/'brand'/'brand.json',encoding='utf-8')); P={k:v['rgb'] for k,v in d['palette'].items() if v['rgb']}
bad=0; warn=0
P['light']=[231,228,226]
# (text, background, min ratio, label) - the pairs the brief actually uses
pairs=[('white','ink2',4.5,'caption text on plate'),('white','red',3.0,'white on red chip (large)'),('white','black',4.5,'text on dark'),
       ('yellow','black',4.5,'yellow keyword on dark'),('emerald','black',4.5,'emerald keyword on dark'),('red','black',3.0,'red keyword on dark (large)'),
       ('ink','white',4.5,'ink on warm white'),('red','light',3.0,'red on light (large)'),('ink','light',4.5,'ink on light'),
       ('white','red_dark',4.5,'white on dark red')]
light=[231,228,226]   # worst case: bottom of the light-background gradient
extra=[('yellow',light,'yellow on LIGHT (must be avoided)'),('white',light,'white on LIGHT (must be avoided)')]
print('Contrast of approved pairs:')
for t,b,mn,l in pairs:
    r=ratio(P[t],P[b]); ok=r>=mn; bad+=(not ok); print(f"  {'OK ' if ok else 'LOW'} {r:5.2f}:1 (min {mn}) {l}")
r=ratio(P['gold'],P['light']); warn+=r<3.0
print(f"  {'OK ' if r>=3 else 'WARN'} {r:5.2f}:1 gold on light bg -> decorative only; for readable text use ink/red or the proposed #AD7608")
print('Forbidden-pair sanity (these SHOULD be low):')
for t,b,l in extra: print(f"  {ratio(P[t],b):5.2f}:1 {l}")
if a.project:
    root=Path(a.project)
    # ---- engine P: python palette constants
    libpy=root/'lib.py'
    if libpy.is_file():
        s=libpy.read_text(encoding='utf-8')
        names={'RED':'red','DRED':'red_dark','WHITE':'white','EMER':'emerald','TEAL':'teal','YEL':'yellow'}
        for n,k in names.items():
            m=re.search(r'\b'+n+r'=\((\d+),(\d+),(\d+)\)',s)
            if m and list(map(int,m.groups()))!=P[k]: print('  DRIFT lib.py',n,m.groups(),'!= brand',P[k]); bad+=1
        print('  engine P palette checked (lib.py)')
    else:
        print('  engine P: no lib.py at project root (skipped)')
    # ---- engine K: js brand tokens (src/lib/brand.js, lib/brand.js or root)
    js=next((c for c in [root/'src'/'lib'/'brand.js',root/'lib'/'brand.js',root/'brand.js'] if c.is_file()),None)
    if js:
        j=js.read_text(encoding='utf-8'); dj=0
        def hexof(name):
            m=re.search(name+r"\s*:\s*'#([0-9A-Fa-f]{6})'",j)
            return m.group(1).upper() if m else None
        want={'red':'red','redDark':'red_dark','black':'black','ink':'ink','ink2':'ink2','white':'white',
              'yellow':'yellow','gold':'gold','emerald':'emerald','teal':'teal'}
        for key,bk in want.items():
            got=hexof(key); exp='%02X%02X%02X'%tuple(P[bk])
            if got is None: print(f'  DRIFT brand.js: {key} not found'); bad+=1; dj+=1
            elif got!=exp: print(f'  DRIFT brand.js {key} #{got} != brand #{exp}'); bad+=1; dj+=1
        for key,bk,side in [('bgDarkTop','dark','top'),('bgDarkBottom','dark','bottom'),
                            ('bgLightTop','light','top'),('bgLightBottom','light','bottom')]:
            got=hexof(key); exp='%02X%02X%02X'%tuple(d['backgrounds'][bk][side])
            if got is None: print(f'  DRIFT brand.js: {key} missing (background gradient)'); bad+=1; dj+=1
            elif got!=exp: print(f'  DRIFT brand.js {key} #{got} != brand #{exp}'); bad+=1; dj+=1
        mf=re.search(r"font\s*:\s*\{\s*ar\s*:\s*'([^']+)'",j)
        if mf and mf.group(1)!=d['typography']['arabic']:
            print(f"  DRIFT brand.js font.ar '{mf.group(1)}' != brand '{d['typography']['arabic']}'"); bad+=1; dj+=1
        for key,bk in [('captionY','caption_center_y'),('progressY','progress_bar_y'),('margin','margin_px'),
                       ('belowIsDead','nothing_important_below_y'),('groundY',None)]:
            if bk is None: continue
            mv=re.search(key+r"\s*:\s*(\d+)",j)
            if mv and int(mv.group(1))!=d['safe_zone'][bk]:
                print(f'  DRIFT brand.js {key} {mv.group(1)} != brand {d["safe_zone"][bk]}'); bad+=1; dj+=1
        print('  engine K tokens checked ('+str(js.relative_to(root))+')' if not dj else f'  engine K: {dj} drift(s)')
    else:
        print('  engine K: no lib/brand.js found (skipped)')
if a.frame:
    from PIL import Image; import numpy as np
    im=np.asarray(Image.open(a.frame).convert('RGB').resize((270,480))).reshape(-1,3).astype(int)
    pal=np.array(list(P.values())+[d['backgrounds']['dark']['top'],d['backgrounds']['light']['top'],[255,255,255],[0,0,0]])
    dist=np.sqrt(((im[:,None,:]-pal[None,:,:])**2).sum(2)).min(1); on=(dist<60).mean()
    print(f'On-palette pixels (within 60 RGB units): {on*100:.0f}%  (illustrated characters/skin tones lower this; <55% on a non-character scene = check colours)')
print('RESULT:', ('PASS' if not bad else f'{bad} issue(s)')+(f' + {warn} known warning(s)' if warn else '')); sys.exit(1 if bad else 0)
