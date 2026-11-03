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


STILL_SIZE = (360, 640)          # one column of a three-frame contact sheet
SHEET_WIDTH = STILL_SIZE[0] * 3


def scenes(project, kinds):
    """Point the fixture scene file at one recipe per requested kind (2 s each)."""
    for kind in kinds:
        shutil.copy2(project / 'src/scenes/test.js', project / f'src/scenes/{kind}.js')
    values = [dict(id=kind, start=i * 2, end=(i + 1) * 2) for i, kind in enumerate(kinds)]
    (project / 'src/data.js').write_text(
        f'export const W=1080,H=1920,FPS=30,scenes={json.dumps(values)},DURATION={len(kinds) * 2};')


def install_fixture(project, fixture, name):
    """Copy a visual fixture into the project (kept in one place so the paths cannot drift)."""
    shutil.copy2(ROOT / f'tests/fixtures/visual/{fixture}', project / name)


def use_timeline(project, scene_id, duration):
    (project / 'src/data.js').write_text(
        f'export const W=1080,H=1920,FPS=30,DURATION={duration},'
        f'scenes=[{{id:"{scene_id}",start:0,end:{duration}}}];')


def render_stills(project, env, times, out_dir, prefix, sheet_path):
    """Render one still per timestamp and glue them into a single reviewable contact sheet."""
    sheet = Image.new('RGB', (SHEET_WIDTH, STILL_SIZE[1]))
    for i, moment in enumerate(times):
        target = out_dir / f'{prefix}-{i}'
        run(['node', 'src/render.js', '--jpg', '--from', moment, '--to', moment + 1 / 30, '--out', target],
            cwd=project, env=env)
        sheet.paste(Image.open(next(target.glob('*.jpg'))).resize(STILL_SIZE), (i * STILL_SIZE[0], 0))
    sheet.save(sheet_path)
    return sheet_path


def audit(project, out_dir, name, replay):
    """Run the K layout audit over a fixture and return its parsed report."""
    args = ['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project),
            '--out', str(out_dir / name), *( ['--replay'] if replay else [])]
    result = subprocess.run(args)
    report_path = out_dir / name / 'report.json'
    report = json.loads(report_path.read_text()) if report_path.is_file() else {}
    return result.returncode, report


def export_from_demo(project, demo_file, names):
    """Read named exports out of an ES module fixture as JSON (node is the parser)."""
    imports = ','.join(f'{name}:{name}' for name in names)
    script = (f'import {{{",".join(names)}}} from {json.dumps((project / demo_file).as_uri())};'
              f'console.log(JSON.stringify({{{imports}}}));')
    exported = subprocess.check_output(['node', '--input-type=module', '-e', script], text=True)
    return json.loads(exported)


def k_scenario(project, env, out, replay, *, scene_id, duration, demo, scene,
               times, audit_name, stem):
    """One K fixture end to end: install, audit, three stills, then a silent motion render."""
    install_fixture(project, demo, f'src/{demo}')
    install_fixture(project, scene, f'src/scenes/{scene_id}.js')
    use_timeline(project, scene_id, duration)
    audit(project, out, audit_name, replay)
    render_stills(project, env, times, out, f'K-{stem}', out / f'K-{stem}.png')
    run(['node', 'src/render.js', '--out', out / 'motion', '--name', f'{stem}-silent-test'],
        cwd=project, env=env)


def verify_k(project, env, out, args):
    """Engine K proofs: the three data recipes, their failing audit, and the opt-in scenarios."""
    kinds = ['comparison', 'timeline', 'counter']
    scenes(project, kinds)
    audit(project, out, 'audit-pass', args.replay)
    sheet = Image.new('RGB', (SHEET_WIDTH, STILL_SIZE[1]))
    for index, kind in enumerate(kinds):
        target = out / f'k-{kind}'
        run(['node', 'src/render.js', '--jpg', '--from', index * 2 + 1, '--to', index * 2 + 1 + 1 / 30,
             '--out', target], cwd=project, env=env)
        sheet.paste(Image.open(next(target.glob('*.jpg'))).resize(STILL_SIZE), (index * STILL_SIZE[0], 0))
    sheet.save(out / 'K-recipes.png')

    # A deliberately bad recipe must FAIL the audit — the gate has to be able to say no.
    scenes(project, ['bad'])
    code, report = audit(project, out, 'audit-fail', args.replay)
    assert code != 0 and report['status'] == 'fail'

    if args.replay:
        # History-dependent pixels must be caught by reverse seeking (R01).
        scenes(project, ['counter'])
        scene = project / 'src/scenes/counter.js'
        source = scene.read_text().replace('export function draw(ctx,t,', 'let count=0; export function draw(ctx,t,')
        source = source.replace(
            'ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);',
            'ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);'
            'ctx.fillStyle=(++count%2)?C.red:C.ink;ctx.fillRect(80,250,80,80);')
        scene.write_text(source)
        code, report = audit(project, out, 'replay-fail', True)
        assert code != 0 and report['replay']['status'] == 'fail'
        assert any(issue['code'] == 'R01' for frame in report['frames'] for issue in frame['issues'])
    scenes(project, kinds)

    scenarios = {
        'shared': dict(scene_id='shared', duration=1.8, demo='shared-demo.js', scene='shared-scene.js',
                       times=[.2, .5, 1.2], audit_name='audit-shared', stem='shared'),
        'plans': dict(scene_id='plan', duration=1.8, demo='plan-demo.js', scene='plan-scene.js',
                      times=[.25, .7, 1.4], audit_name='audit-plans', stem='plans'),
        'states': dict(scene_id='state', duration=2.4, demo='state-demo.js', scene='state-scene.js',
                       times=[.3, .8, 1.4], audit_name='audit-states', stem='states'),
        'geometry': dict(scene_id='geometry', duration=3, demo='geometry-demo.js', scene='geometry-scene.js',
                         times=[.1, .9, 2.8], audit_name='audit-geometry', stem='geometry'),
        'morph': dict(scene_id='morph', duration=2.4, demo='morph-demo.js', scene='morph-scene.js',
                      times=[.1, 1.05, 2.2], audit_name='audit-morph', stem='morph'),
    }
    for flag, scenario in scenarios.items():
        if getattr(args, flag):
            k_scenario(project, env, out, args.replay, **scenario)


def verify_k_geometry_review(project, out, env):
    """Export the geometry proof spec and check it with the shared reviewer."""
    spec = export_from_demo(project, 'src/geometry-demo.js', ['PROOF_SPEC'])
    (out / 'geometry-spec.json').write_text(json.dumps(spec))
    run([sys.executable, ROOT / 'tests/fixtures/visual/geometry_review.py', out / 'geometry-spec.json', out], env=env)


def verify_k_svg(project, out, env, args):
    """Compile one bounded SVG, render it, profile the run, then review the result."""
    run([sys.executable, ROOT / 'tools/svg_compile.py',
         ROOT / 'tests/fixtures/visual/svg-proof.svg', out / 'svg-plan.json'])
    plan = json.loads((out / 'svg-plan.json').read_text())
    (project / 'src/svg-proof.js').write_text('export const PLAN=' + json.dumps(plan) + ';')
    install_fixture(project, 'svg-scene.js', 'src/scenes/svg.js')
    use_timeline(project, 'svg', 2)
    audit(project, out, 'audit-svg', args.replay)
    render_stills(project, env, [.1, .8, 1.6], out, 'K-svg', out / 'K-svg.png')
    run(['node', 'src/render.js', '--profile', '--out', out / 'motion', '--name', 'svg-reduced-silent-test'],
        cwd=project, env=env)
    profile = json.loads((out / 'motion/render-profile.json').read_text())
    assert profile['frames'] == 60 and profile['frameEvaluateMs']['p95'] >= 0
    run([sys.executable, ROOT / 'tests/fixtures/visual/svg_review.py', out / 'svg-plan.json', out], env=env)
    return plan


def verify_k_morph(project, out, env, args):
    """Compile the two morph contours, render the nested sequence, and review the proof."""
    for name in ('from', 'to'):
        run([sys.executable, ROOT / 'tools/svg_compile.py',
             ROOT / f'tests/fixtures/visual/morph-{name}.svg', out / f'morph-{name}.json'])
    source = json.loads((out / 'morph-from.json').read_text())
    target = json.loads((out / 'morph-to.json').read_text())
    (project / 'src/morph-plans.js').write_text(
        'export const FROM=' + json.dumps(source) + ';export const TO=' + json.dumps(target) + ';')
    k_scenario(project, env, out, args.replay, scene_id='morph', duration=2.4,
               demo='morph-demo.js', scene='morph-scene.js',
               times=[.1, 1.05, 2.2], audit_name='audit-morph', stem='morph')
    sequence = export_from_demo(project, 'src/morph-demo.js', ['SPEC'])
    (out / 'morph-proof.json').write_text(json.dumps({'sequence': sequence, 'from': source, 'to': target}))
    run([sys.executable, ROOT / 'tests/fixtures/visual/morph_review.py', out / 'morph-proof.json', out], env=env)
    return source, target


def use_root(project_dir, fixture):
    """Swap the Remotion root composition for the fixture under review."""
    shutil.copyfile(ROOT / f'tests/fixtures/visual/{fixture}', project_dir / 'src/Root.tsx')


def r_stills(project_dir, out, env, composition, frames, stem, sheet_name=None):
    """Remotion stills for one composition, glued into a three-frame contact sheet."""
    shot = Image.new('RGB', (SHEET_WIDTH, STILL_SIZE[1]))
    for index, frame in enumerate(frames):
        target = out / f'{stem}-{index}.png'
        run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', composition, target,
             f'--frame={frame}', '--log=error'], cwd=project_dir, env=env)
        shot.paste(Image.open(target).resize(STILL_SIZE), (index * STILL_SIZE[0], 0))
    shot.save(out / (sheet_name or f'{stem}.png'))


def verify_r(out, env, args, kinds, font, svg_plan, morph_plans):
    """Engine R proofs: the same fixtures compiled through Remotion, plus a typecheck per fixture."""
    project = out / 'r'
    shutil.copytree(ROOT / 'medo-motion/templates/remotion', project)
    (project / 'public/fonts/Cairo').mkdir(parents=True)
    shutil.copy2(font, project / 'public/fonts/Cairo')

    def typecheck():
        run(['node', 'node_modules/typescript/bin/tsc', '--noEmit'], cwd=project)

    use_root(project, 'DataReview.tsx')
    # Compile just this isolated composition and its imported adapters.
    tsconfig = json.loads((project / 'tsconfig.json').read_text())
    tsconfig['include'] = ['src/Root.tsx', 'src/index.ts']
    (project / 'tsconfig.json').write_text(json.dumps(tsconfig))
    run(['npm', 'ci', '--no-audit', '--no-fund'], cwd=project)
    typecheck()
    sheet = Image.new('RGB', (SHEET_WIDTH, STILL_SIZE[1]))
    for index, kind in enumerate(kinds):
        target = out / f'R-{kind}.png'
        run(['node', 'scripts/launch-remotion.mjs', 'still', 'src/index.ts', f'Data-{kind}', target,
             '--frame=30', '--log=error'], cwd=project, env=env)
        sheet.paste(Image.open(target).resize(STILL_SIZE), (index * STILL_SIZE[0], 0))
    sheet.save(out / 'R-recipes.png')

    optional = {
        'shared': ('SharedReview.tsx', 'shared-demo.js', 'SharedDetail', [6, 15, 36], 'R-shared'),
        'plans': ('PlanReview.tsx', 'plan-demo.js', 'MotionPlan', [8, 21, 42], 'R-plans'),
        'states': ('StateReview.tsx', 'state-demo.js', 'MotionState', [9, 24, 42], 'R-states'),
        'geometry': ('GeometryReview.tsx', 'geometry-demo.js', 'MotionGeometry', [3, 27, 84], 'R-geometry'),
    }
    for flag, (root, demo, composition, frames, stem) in optional.items():
        if not getattr(args, flag):
            continue
        use_root(project, root)
        install_fixture(project, demo, f'src/{demo}')
        typecheck()
        r_stills(project, out, env, composition, frames, stem)

    if getattr(args, 'svg', False):
        use_root(project, 'SvgReview.tsx')
        (project / 'src/svg-proof.js').write_text('export const PLAN=' + json.dumps(svg_plan) + ';')
        typecheck()
        r_stills(project, out, env, 'SvgProof', [3, 24, 48], 'R-svg')

    if getattr(args, 'morph', False) and morph_plans:
        source, target = morph_plans
        use_root(project, 'MorphReview.tsx')
        install_fixture(project, 'morph-demo.js', 'src/morph-demo.js')
        (project / 'src/morph-plans.js').write_text(
            'export const FROM=' + json.dumps(source) + ';export const TO=' + json.dumps(target) + ';')
        typecheck()
        r_stills(project, out, env, 'SvgMorphProof', [3, 32, 66], 'R-morph')


def main(argv=None):
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
    args = ap.parse_args(argv)
    out = checked_path(args.out, tree=True)
    out.mkdir(parents=True, exist_ok=False)

    config = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/chromium.mjs'), '--json'], text=True))
    env = dict(os.environ, MEDO_TOOLKIT=str(ROOT / 'tools/toolkit'),
               MEDO_CHROMIUM=config['executablePath'], REMOTION_BROWSER_EXECUTABLE=config['executablePath'])
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [config.get('libraryPath'), env.get('LD_LIBRARY_PATH')]))

    font = ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf'
    project = out / 'k'
    shutil.copytree(ROOT / 'medo-motion/templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module","private":true}')
    (project / 'assets/fonts/Cairo').mkdir(parents=True)
    shutil.copy2(font, project / 'assets/fonts/Cairo')
    fixture = (ROOT / 'tests/fixtures/visual/scene.js').read_text().replace("from './lib/", "from '../lib/")
    (project / 'src/scenes/test.js').write_text(fixture)

    verify_k(project, env, out, args)
    if args.geometry:
        verify_k_geometry_review(project, out, env)
    svg_plan = verify_k_svg(project, out, env, args) if args.svg else None
    morph_plans = verify_k_morph(project, out, env, args) if args.morph else None
    if args.remotion:
        verify_r(out, env, args, ['comparison', 'timeline', 'counter'], font, svg_plan, morph_plans)
    print(f'Verified artifacts: {out} (synthetic data/timing, not a production reel)')


if __name__ == '__main__':
    main()
