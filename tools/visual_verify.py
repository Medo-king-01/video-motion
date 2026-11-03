#!/usr/bin/env python3
"""Reproduce synthetic data stills + passing/failing K QA; optional R compile/stills.

This is an offline render verification fixture, NOT a measured-VO production reel.
Writes only to a fresh destination; npm ci (--remotion only) uses the pinned lock.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'medo-motion/scripts'))
from _safe_paths import checked_path  # noqa: E402


def run(args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def scenes(project, kinds):
    for kind in kinds:
        shutil.copy2(project / 'src/scenes/test.js', project / f'src/scenes/{kind}.js')
    values = [dict(id=kind, start=i*2, end=(i+1)*2) for i, kind in enumerate(kinds)]
    (project / 'src/data.js').write_text(f'export const W=1080,H=1920,FPS=30,scenes={json.dumps(values)},DURATION={len(kinds)*2};')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, default=ROOT / '.cache/visual-review')
    ap.add_argument('--remotion', action='store_true')
    ap.add_argument('--morph', action='store_true', help='verify nested sequences and topology-checked SVG morph in P/K/R')
    ap.add_argument('--svg', action='store_true', help='verify bounded SVG, reduced motion and profiling in P/K/R')
    ap.add_argument('--geometry', action='store_true', help='verify group layout, measured fonts and shape/property adapters in P/K/R')
    ap.add_argument('--states', action='store_true', help='also verify offline physics, event targets and variants')
    ap.add_argument('--plans', action='store_true', help='also verify native sequence/stagger/path planning')
    ap.add_argument('--shared', action='store_true', help='also verify shared-shell continuity with a silent K test clip')
    ap.add_argument('--replay', action='store_true', help='reverse-seek pixel/layout checks on inspected K frames')
    args = ap.parse_args()
    out = checked_path(args.out, tree=True)
    out.mkdir(parents=True, exist_ok=False)
    config = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/chromium.mjs'), '--json'], text=True))
    env = dict(os.environ, MEDO_TOOLKIT=str(ROOT / 'tools/toolkit'), MEDO_CHROMIUM=config['executablePath'], REMOTION_BROWSER_EXECUTABLE=config['executablePath'])
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [config.get('libraryPath'), env.get('LD_LIBRARY_PATH')]))
    font = ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf'
    project = out / 'k'
    shutil.copytree(ROOT / 'medo-motion/templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module","private":true}')
    (project / 'assets/fonts/Cairo').mkdir(parents=True)
    shutil.copy2(font, project / 'assets/fonts/Cairo')
    fixture = (ROOT / 'tests/fixtures/visual/scene.js').read_text().replace("from './lib/", "from '../lib/")
    (project / 'src/scenes/test.js').write_text(fixture)
    audit_args = ['--replay'] if args.replay else []
    kinds = ['comparison', 'timeline', 'counter']
    scenes(project, kinds)
    run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-pass', *audit_args])
    sheet = Image.new('RGB', (360*3, 640))
    for i, kind in enumerate(kinds):
        target = out / f'k-{kind}'
        run(['node', 'src/render.js', '--jpg', '--from', i*2+1, '--to', i*2+1+1/30, '--out', target], cwd=project, env=env)
        image = Image.open(next(target.glob('*.jpg')))
        sheet.paste(image.resize((360, 640)), (i*360, 0))
    sheet.save(out / 'K-recipes.png')
    scenes(project, ['bad'])
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(out / 'audit-fail'), *audit_args])
    assert result.returncode != 0 and json.loads((out / 'audit-fail/report.json').read_text())['status'] == 'fail'
    if args.replay:
        scenes(project, ['counter'])
        scene = project / 'src/scenes/counter.js'
        source = scene.read_text().replace('export function draw(ctx,t,', 'let count=0; export function draw(ctx,t,')
        source = source.replace('ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);',
            'ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);ctx.fillStyle=(++count%2)?C.red:C.ink;ctx.fillRect(80,250,80,80);')
        scene.write_text(source)
        result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project),
            '--out', str(out / 'replay-fail'), '--replay'])
        report = json.loads((out / 'replay-fail/report.json').read_text())
        assert result.returncode != 0 and report['replay']['status'] == 'fail'
        assert any(i['code'] == 'R01' for f in report['frames'] for i in f['issues'])
    scenes(project, kinds)
    if args.shared:
        shutil.copy2(ROOT / 'tests/fixtures/visual/shared-demo.js', project / 'src/shared-demo.js')
        shutil.copy2(ROOT / 'tests/fixtures/visual/shared-scene.js', project / 'src/scenes/shared.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=1.8,scenes=[{id:"shared",start:0,end:1.8}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-shared', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.2, .5, 1.2]):
            target = out / f'K-shared-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target], cwd=project, env=env)
            sheet.paste(Image.open(next(target.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-shared.png')
        run(['node', 'src/render.js', '--out', out / 'motion', '--name', 'shared-shell-silent-test'], cwd=project, env=env)
    if args.plans:
        shutil.copy2(ROOT / 'tests/fixtures/visual/plan-demo.js', project / 'src/plan-demo.js')
        shutil.copy2(ROOT / 'tests/fixtures/visual/plan-scene.js', project / 'src/scenes/plan.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=1.8,scenes=[{id:"plan",start:0,end:1.8}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-plans', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.25, .7, 1.4]):
            target = out / f'K-plan-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target], cwd=project, env=env)
            sheet.paste(Image.open(next(target.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-plans.png')
        run(['node', 'src/render.js', '--out', out / 'motion', '--name', 'motion-plan-silent-test'], cwd=project, env=env)
    if args.states:
        shutil.copy2(ROOT / 'tests/fixtures/visual/state-demo.js', project / 'src/state-demo.js')
        shutil.copy2(ROOT / 'tests/fixtures/visual/state-scene.js', project / 'src/scenes/state.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2.4,scenes=[{id:"state",start:0,end:2.4}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-states', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.3, .8, 1.4]):
            target = out / f'K-state-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target], cwd=project, env=env)
            sheet.paste(Image.open(next(target.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-states.png')
        run(['node', 'src/render.js', '--out', out / 'motion', '--name', 'motion-state-silent-test'], cwd=project, env=env)
    if args.geometry:
        shutil.copy2(ROOT / 'tests/fixtures/visual/geometry-demo.js', project / 'src/geometry-demo.js')
        shutil.copy2(ROOT / 'tests/fixtures/visual/geometry-scene.js', project / 'src/scenes/geometry.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=3,scenes=[{id:"geometry",start:0,end:3}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-geometry', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.1, .9, 2.8]):
            target = out / f'K-geometry-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target], cwd=project, env=env)
            sheet.paste(Image.open(next(target.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-geometry.png')
        run(['node', 'src/render.js', '--out', out / 'motion', '--name', 'motion-geometry-silent-test'], cwd=project, env=env)
        exported = subprocess.check_output(['node', '--input-type=module', '-e',
            f'import {{PROOF_SPEC}} from {json.dumps((project / "src/geometry-demo.js").as_uri())};console.log(JSON.stringify(PROOF_SPEC));'], text=True)
        (out / 'geometry-spec.json').write_text(exported)
        run([sys.executable, ROOT / 'tests/fixtures/visual/geometry_review.py', out / 'geometry-spec.json', out], env=env)
    if args.svg:
        run([sys.executable, ROOT / 'tools/svg_compile.py', ROOT / 'tests/fixtures/visual/svg-proof.svg', out / 'svg-plan.json'])
        plan = json.loads((out / 'svg-plan.json').read_text())
        (project / 'src/svg-proof.js').write_text('export const PLAN='+json.dumps(plan)+';')
        shutil.copy2(ROOT / 'tests/fixtures/visual/svg-scene.js', project / 'src/scenes/svg.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2,scenes=[{id:"svg",start:0,end:2}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-svg', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.1, .8, 1.6]):
            target = out / f'K-svg-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target], cwd=project, env=env)
            sheet.paste(Image.open(next(target.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-svg.png')
        run(['node', 'src/render.js', '--profile', '--out', out / 'motion', '--name', 'svg-reduced-silent-test'], cwd=project, env=env)
        profile = json.loads((out / 'motion/render-profile.json').read_text())
        assert profile['frames'] == 60 and profile['frameEvaluateMs']['p95'] >= 0
        run([sys.executable, ROOT / 'tests/fixtures/visual/svg_review.py', out / 'svg-plan.json', out], env=env)
    if args.morph:
        for name in ('from', 'to'):
            run([sys.executable, ROOT / 'tools/svg_compile.py', ROOT / f'tests/fixtures/visual/morph-{name}.svg', out / f'morph-{name}.json'])
        morph_source = json.loads((out / 'morph-from.json').read_text()); morph_target = json.loads((out / 'morph-to.json').read_text())
        (project / 'src/morph-plans.js').write_text('export const FROM='+json.dumps(morph_source)+';export const TO='+json.dumps(morph_target)+';')
        shutil.copy2(ROOT / 'tests/fixtures/visual/morph-demo.js', project / 'src/morph-demo.js')
        shutil.copy2(ROOT / 'tests/fixtures/visual/morph-scene.js', project / 'src/scenes/morph.js')
        (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2.4,scenes=[{id:"morph",start:0,end:2.4}];')
        run(['node', ROOT / 'tools/layout_audit.mjs', '--project', project, '--out', out / 'audit-morph', *audit_args])
        sheet = Image.new('RGB', (1080, 640))
        for i, time in enumerate([.1, 1.05, 2.2]):
            target_dir = out / f'K-morph-{i}'
            run(['node', 'src/render.js', '--jpg', '--from', time, '--to', time+1/30, '--out', target_dir], cwd=project, env=env)
            sheet.paste(Image.open(next(target_dir.glob('*.jpg'))).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'K-morph.png')
        run(['node', 'src/render.js', '--out', out / 'motion', '--name', 'svg-morph-nested-silent-test'], cwd=project, env=env)
        exported = subprocess.check_output(['node', '--input-type=module', '-e',
            f'import {{SPEC}} from {json.dumps((project / "src/morph-demo.js").as_uri())};console.log(JSON.stringify(SPEC));'], text=True)
        (out / 'morph-proof.json').write_text(json.dumps({'sequence': json.loads(exported), 'from': morph_source, 'to': morph_target}))
        run([sys.executable, ROOT / 'tests/fixtures/visual/morph_review.py', out / 'morph-proof.json', out], env=env)
    if args.remotion:
        r = out / 'r'
        shutil.copytree(ROOT / 'medo-motion/templates/remotion', r)
        (r / 'public/fonts/Cairo').mkdir(parents=True)
        shutil.copy2(font, r / 'public/fonts/Cairo')
        shutil.copy2(ROOT / 'tests/fixtures/visual/DataReview.tsx', r / 'src/Root.tsx')
        # Compile just this isolated composition and its imported adapters.
        tsconfig = json.loads((r / 'tsconfig.json').read_text())
        tsconfig['include'] = ['src/Root.tsx', 'src/index.ts']
        (r / 'tsconfig.json').write_text(json.dumps(tsconfig))
        run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=r)
        run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
        sheet = Image.new('RGB', (360*3, 640))
        for i, kind in enumerate(kinds):
            target = out / f'R-{kind}.png'
            run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', f'Data-{kind}', target, '--frame=30', '--log=error'], cwd=r, env=env)
            sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
        sheet.save(out / 'R-recipes.png')
        if args.shared:
            shutil.copy2(ROOT / 'tests/fixtures/visual/shared-demo.js', r / 'src/shared-demo.js')
            shutil.copy2(ROOT / 'tests/fixtures/visual/SharedReview.tsx', r / 'src/Root.tsx')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([6,15,36]):
                target = out / f'R-shared-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'SharedDetail', target, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-shared.png')
        if args.plans:
            shutil.copy2(ROOT / 'tests/fixtures/visual/plan-demo.js', r / 'src/plan-demo.js')
            shutil.copy2(ROOT / 'tests/fixtures/visual/PlanReview.tsx', r / 'src/Root.tsx')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([8,21,42]):
                target = out / f'R-plan-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'MotionPlan', target, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-plans.png')
        if args.states:
            shutil.copy2(ROOT / 'tests/fixtures/visual/state-demo.js', r / 'src/state-demo.js')
            shutil.copy2(ROOT / 'tests/fixtures/visual/StateReview.tsx', r / 'src/Root.tsx')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([9,24,42]):
                target = out / f'R-state-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'MotionState', target, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-states.png')
        if args.geometry:
            shutil.copy2(ROOT / 'tests/fixtures/visual/geometry-demo.js', r / 'src/geometry-demo.js')
            shutil.copy2(ROOT / 'tests/fixtures/visual/GeometryReview.tsx', r / 'src/Root.tsx')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([3,27,84]):
                target = out / f'R-geometry-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'MotionGeometry', target, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-geometry.png')
        if args.svg:
            shutil.copy2(ROOT / 'tests/fixtures/visual/SvgReview.tsx', r / 'src/Root.tsx')
            (r / 'src/svg-proof.js').write_text('export const PLAN='+json.dumps(plan)+';')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([3,24,48]):
                target = out / f'R-svg-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'SvgProof', target, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-svg.png')
        if args.morph:
            shutil.copy2(ROOT / 'tests/fixtures/visual/MorphReview.tsx', r / 'src/Root.tsx')
            shutil.copy2(ROOT / 'tests/fixtures/visual/morph-demo.js', r / 'src/morph-demo.js')
            (r / 'src/morph-plans.js').write_text('export const FROM='+json.dumps(morph_source)+';export const TO='+json.dumps(morph_target)+';')
            run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=r)
            sheet = Image.new('RGB', (1080, 640))
            for i, frame in enumerate([3,32,66]):
                target_file = out / f'R-morph-{i}.png'
                run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', 'SvgMorphProof', target_file, f'--frame={frame}', '--log=error'], cwd=r, env=env)
                sheet.paste(Image.open(target_file).resize((360, 640)), (i*360, 0))
            sheet.save(out / 'R-morph.png')
    print(f'Verified artifacts: {out} (synthetic data/timing, not a production reel)')


if __name__ == '__main__':
    main()
