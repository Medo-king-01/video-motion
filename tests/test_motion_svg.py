"""Bounded SVG compiler, safety contract and P/K/R plan parity."""
from __future__ import annotations

import json

import pytest
from conftest import SKILL
from PIL import Image
from svg_art import draw_svg_art, svg_placement, validate_svg_art
from svg_compile import compile_svg, parse_d
from test_motion_plan import assert_same
from test_visual_tools import js

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop

MODEL = SKILL / 'templates/render/lib/svg-art.js'
SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
<g fill="#CB271B" fill-rule="evenodd" stroke="#0A0A0A" stroke-width="2"><path d="M10 10 H90 V90 H10 Z M30 30 h40 v40 h-40 Z"/></g>
</svg>'''


def test_hole_and_stroke_render_in_p():
    plan = compile_svg(SVG); assert len(plan['shapes'][0]['contours']) == 2
    image = Image.new('RGB', (200, 200), '#F3F2F1')
    draw_svg_art(image, plan, {'x': 0, 'y': 0, 'width': 200, 'height': 200})
    assert image.getpixel((40,40)) == (203,39,27)
    assert image.getpixel((100,100)) == (243,242,241)
    assert image.getpixel((20,100)) == (10,10,10)
    assert image.getpixel((5,5)) == (243,242,241)


@pytest.mark.parametrize('d,expected', [
    ('M0 0 l10 0 0 10 z', (0, 0)),
    ('M0 0 H10 V10 h-10 v-10', (0, 0)),
    ('M0 0 C0 10 10 10 10 0 S20 -10 20 0', (20, 0)),
    ('M0 0 Q5 10 10 0 T20 0', (20, 0)),
    ('M0 0 A10 10 0 0110 10', (10, 10)),
    ('M0 0 a10 5 45 1 0 20 0', (20, 0)),
])
def test_path_commands_and_compact_arc_flags(d, expected):
    paths = parse_d(d); c = paths[-1]; end = c['points'][0 if c['closed'] else -1]
    assert (end['x'], end['y']) == pytest.approx(expected)


def test_subpaths_with_coincident_endpoints_remain_distinct():
    result = parse_d('M0 0L10 10 M10 10l10 0 0 10z')
    assert len(result) == 2 and not result[0]['closed'] and result[1]['closed']
    assert result[1]['points'][0] == {'x': 10, 'y': 10}


@pytest.mark.parametrize('d', ['L0 0', 'M0', 'M0 0L2', 'M0 0Z', 'M0 0 R10 10', 'M0 0A1 1 0 2 0 2 2', 'M0 0A-1 1 0 0 1 2 2', 'M0 0L1e999 0', 'M0 0L1 1 garbage'])
def test_invalid_paths_fail_closed(d):
    with pytest.raises(ValueError): parse_d(d)


@pytest.mark.parametrize('svg', [
    '<!DOCTYPE svg [<!ENTITY x "hello">]><svg viewBox="0 0 1 1"/>',
    '<svg viewBox="0 0 1 1"><script/></svg>',
    '<svg viewBox="0 0 1 1"><image href="https://example.com/a"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="url(#x)"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="none" stroke="#0A0A0A" transform="scale(2 1)"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="#CB271B"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="#000000"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="red"/></svg>',
    '<svg viewBox="0 0 1 1"><path d="M0 0L1 1" fill="none" onclick="x()"/></svg>',
])
def test_unsupported_svg_is_rejected_instead_of_silent_degradation(svg):
    with pytest.raises(ValueError): compile_svg(svg)


def test_native_placement_parity_and_invalid_plan():
    plan = compile_svg(SVG); options = {'x': 5, 'y': 15, 'width': 400, 'height': 200}
    actual = js(f'import {{svgPlacement}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(svgPlacement({json.dumps(plan)},{json.dumps(options)})));')
    assert_same(actual, svg_placement(plan, options))
    plan['shapes'][0]['fill'] = 'url(https://example.com)'
    with pytest.raises(ValueError): validate_svg_art(plan)
    assert js(f'import {{validateSvgArt}} from {json.dumps(MODEL.as_uri())};let bad=false;try{{validateSvgArt({json.dumps(plan)})}}catch{{bad=true}}console.log(JSON.stringify(bad));')


@pytest.mark.parametrize('geometry', [
    '<rect x="10" y="10" width="40" height="30" rx="5"/>',
    '<circle cx="20" cy="20" r="10"/>',
    '<ellipse cx="20" cy="20" rx="10" ry="5"/>',
    '<polygon points="0,0 30,0 30,30"/>',
    '<polyline points="0,0 30,0 30,30"/>',
    '<line x1="0" y1="0" x2="30" y2="30"/>',
])
def test_svg_basic_shapes_compile_to_portable_contours(geometry):
    source = f'<svg viewBox="0 0 100 100"><g fill="none" stroke="#0A0A0A">{geometry}</g></svg>'
    plan = compile_svg(source)
    assert plan['shapes'][0]['contours']
    validate_svg_art(plan)


def test_nested_uniform_transforms_and_inherited_stroke():
    source = '<svg viewBox="0 0 100 100"><g fill="none" stroke="#0A0A0A" stroke-width="2" transform="translate(10 20)"><path d="M1 2L3 4" transform="scale(2)"/></g></svg>'
    shape = compile_svg(source)['shapes'][0]
    assert shape['contours'][0]['points'] == [{'x': 12, 'y': 24}, {'x': 16, 'y': 28}]
    assert shape['strokeWidth'] == 4


def test_nonuniform_transform_is_supported_only_without_stroke():
    source = '<svg viewBox="0 0 100 100"><rect fill="#CB271B" fill-rule="evenodd" transform="scale(2 3)" x="1" y="2" width="4" height="5"/></svg>'
    shape = compile_svg(source)['shapes'][0]
    assert shape['contours'][0]['points'][0] == {'x': 2, 'y': 6}
    with pytest.raises(ValueError): compile_svg(source.replace('fill="#CB271B"', 'fill="#CB271B" stroke="#0A0A0A"'))


@pytest.mark.slow
def test_real_k_svg_replay_and_profile_does_not_change_frames(tmp_path):
    import os
    import shutil
    import subprocess

    from conftest import ROOT

    project = tmp_path / 'project'
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}')
    fonts = project / 'assets/fonts/Cairo'; fonts.mkdir(parents=True)
    shutil.copy2(ROOT / 'assets/fonts/Cairo/Cairo_800ExtraBold.ttf', fonts)
    plan = compile_svg((ROOT / 'tests/fixtures/visual/svg-proof.svg').read_text())
    (project / 'src/svg-proof.js').write_text('export const PLAN='+json.dumps(plan)+';')
    shutil.copy2(ROOT / 'tests/fixtures/visual/svg-scene.js', project / 'src/scenes/svg.js')
    (project / 'src/data.js').write_text('export const W=1080,H=1920,FPS=30,DURATION=2,scenes=[{id:"svg",start:0,end:2}];')
    result = subprocess.run(['node', str(ROOT / 'tools/layout_audit.mjs'), '--project', str(project), '--out', str(tmp_path / 'audit'), '--replay'], capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout+result.stderr
    report = json.loads((tmp_path / 'audit/report.json').read_text())
    assert report['status'] == report['replay']['status'] == 'pass'
    assert report['replay']['checkedFrames'] == 60
    cfg = json.loads(subprocess.check_output(['node', str(ROOT / 'tools/chromium.mjs'), '--json'], text=True))
    env = dict(os.environ, MEDO_TOOLKIT=str(ROOT / 'tools/toolkit'), MEDO_CHROMIUM=cfg['executablePath'])
    env['LD_LIBRARY_PATH'] = ':'.join(filter(None, [cfg.get('libraryPath'), env.get('LD_LIBRARY_PATH')]))
    for name in ('normal', 'profile'):
        args = ['node', 'src/render.js', '--jpg', '--from', '.8', '--to', str(.8+1/30), '--out', str(tmp_path / name)]
        if name == 'profile': args.append('--profile')
        result = subprocess.run(args, cwd=project, env=env, capture_output=True, text=True, timeout=60)
        assert result.returncode == 0, result.stdout+result.stderr
    assert (tmp_path / 'normal/00000.jpg').read_bytes() == (tmp_path / 'profile/00000.jpg').read_bytes()
    profile = json.loads((tmp_path / 'profile/render-profile.json').read_text())
    assert profile['frames'] == 1 and profile['frameEvaluateMs']['max'] >= 0


def test_svg_rollout_is_truthful_about_incomplete_morph():
    rollout = json.loads((SKILL / 'motion/rollout.json').read_text())
    statuses = {f['id']: f['status'] for f in rollout['features']}
    assert rollout['phase'] >= 4
    assert all(statuses[i] == 'partial' for i in [21, 22, 23, 32, 36, 37, 38, 41])
    assert statuses[27] == statuses[42] == 'excluded'


def test_placement_defaults_match_across_backends():
    plan = compile_svg(SVG); options = {'width': 100, 'height': 100}
    actual = js(f'import {{svgPlacement}} from {json.dumps(MODEL.as_uri())};console.log(JSON.stringify(svgPlacement({json.dumps(plan)},{json.dumps(options)})));')
    assert_same(actual, svg_placement(plan, options))


def test_xml_declaration_and_comments_are_supported_without_accepting_entities():
    source = '<?xml version="1.0" encoding="UTF-8"?>\n<!-- safe note -->' + SVG
    assert compile_svg(source) == compile_svg(SVG)
    with pytest.raises(ValueError): compile_svg('<!--safe--><!DOCTYPE svg [<!ENTITY x "oops">]><svg viewBox="0 0 1 1"/>')
    with pytest.raises(ValueError): compile_svg('<?xml version="1.0"?><?evil go?><svg viewBox="0 0 1 1"/>')


def test_safe_inline_presentation_declarations_inherit_and_override():
    source = '''<svg viewBox="0 0 100 100" fill="#0A0A0A" style="fill: #CB271B; fill-rule: evenodd">
      <g stroke="#0A0A0A" style="stroke-width: 2"><rect x="10" y="10" width="80" height="80" fill="none" style="fill: #D8D7D5; opacity: 1"/></g></svg>'''
    equivalent = '''<svg viewBox="0 0 100 100"><g fill="#CB271B" fill-rule="evenodd" stroke="#0A0A0A" stroke-width="2"><rect x="10" y="10" width="80" height="80" fill="#D8D7D5" opacity="1"/></g></svg>'''
    assert compile_svg(source) == compile_svg(equivalent)


@pytest.mark.parametrize('style', [
    'fill:url(https://example.com/a)', 'fill:var(--x)', 'fill:#CB271B!important',
    'fill:#CB271B;fill:#0A0A0A', 'filter:none', 'fill:#CB271B;opacity:1.5',
    'stroke-width:1px', 'stroke-width:-1', 'fill-rule:bogus', 'transform:rotate(30deg)',
    'fill:#CB271B/*comment*/', 'fill:red', 'fill:#CB271B:extra',
])
def test_unsupported_inline_style_fails_closed(style):
    with pytest.raises(ValueError):
        compile_svg(f'<svg viewBox="0 0 10 10"><rect width="5" height="5" fill="none" style="{style}"/></svg>')


def test_inline_style_rejects_group_opacity_even_if_child_overrides():
    with pytest.raises(ValueError):
        compile_svg('<svg viewBox="0 0 10 10"><g style="opacity:1"><rect width="5" height="5" fill="none"/></g></svg>')


def test_svg_explicit_stable_ids_are_optional_and_independent_of_order(tmp_path):
    import subprocess
    import sys

    from conftest import ROOT

    source='''<svg viewBox="0 0 100 100"><rect id="first" x="0" y="0" width="10" height="10" fill="none"/><circle id="second" cx="30" cy="30" r="10" fill="none"/></svg>'''
    assert [s['id'] for s in compile_svg(source)['shapes']]==['svg-0','svg-1']
    plan=compile_svg(source,preserve_ids=True)
    assert [s['id'] for s in plan['shapes']]==['first','second']
    file=tmp_path/'input.svg';file.write_text(source);out=tmp_path/'plan.json'
    result=subprocess.run([sys.executable,str(ROOT/'tools/svg_compile.py'),str(file),str(out),'--preserve-ids'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert json.loads(out.read_text())==plan


@pytest.mark.parametrize('ids', [('', 'b'), ('same', 'same'), ('a b', 'b'), ('<script>', 'b'), ('a'*65, 'b'), ('a', 'shade')])
def test_svg_preserve_ids_rejects_missing_duplicate_unsafe_or_gradient_collision(ids):
    first,second=ids
    source=f'''<svg viewBox="0 0 100 100"><defs><linearGradient id="shade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#CB271B"/><stop offset="1" stop-color="#0A0A0A"/></linearGradient></defs>
      <rect id="{first}" width="10" height="10" fill="none"/><rect id="{second}" width="10" height="10" fill="none"/></svg>'''
    with pytest.raises(ValueError): compile_svg(source,preserve_ids=True)
