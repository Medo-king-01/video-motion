"""Production opt-in, cache separation and resource lifecycle regressions."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

import pytest
from chunk_utils import build_signature
from conftest import ENGINE_P, ROOT, SKILL
from render_policy import decorative_time, motion_mode
from resource_scope import ResourceScope
from test_visual_tools import js


def test_decorative_clock_never_changes_scene_time_and_validates():
    assert decorative_time(1.2, 'normal') == 1.2
    assert decorative_time(1.2, 'reduced') == 0
    with pytest.raises(ValueError): motion_mode('automatic')
    with pytest.raises(ValueError): decorative_time(float('nan'), 'normal')


def test_cache_signature_distinguishes_modes(tmp_path):
    args = (tmp_path, tmp_path / 'assets', 2, 1, [0, 1], 30, 8, 8)
    assert build_signature(*args) == build_signature(*args, motion_mode='normal')
    assert build_signature(*args) != build_signature(*args, motion_mode='reduced')
    with pytest.raises(ValueError): build_signature(*args, motion_mode='invalid')


def test_python_cleanup_does_not_mask_primary_error():
    def bad(): raise ValueError('cleanup')
    with pytest.warns(RuntimeWarning, match='cleanup'):
        with pytest.raises(KeyError, match='primary'):
            with ResourceScope() as scope:
                scope.defer(bad)
                raise KeyError('primary')


def test_js_reentrant_close_during_disposal_reuses_pending_promise():
    module = (SKILL / 'templates/render/lib/resource-scope.js').as_uri()
    assert js(f'''import {{createResourceScope}} from {json.dumps(module)};
      const s=createResourceScope(), seen=[];let nested;
      s.defer(()=>{{seen.push('one');nested=s.close();}});
      const outer=s.close();await outer;await nested;
      console.log(JSON.stringify({{same:outer===nested,seen}}));''') == {'same': True, 'seen': ['one']}


@pytest.fixture
def p_project(tmp_path):
    pytest.importorskip('av')
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg: pytest.skip('ffmpeg missing')
    for name in ('chunk.py', 'chunk_utils.py', 'render_policy.py', 'resource_scope.py'):
        shutil.copy2(ENGINE_P / name, tmp_path / name)
    (tmp_path / 'text_direction.py').write_text('', encoding='utf8')
    (tmp_path / 'art.py').write_text('W=H=8\n', encoding='utf8')
    (tmp_path / 'scenes.py').write_text('''import os
import numpy as np
W=H=8
SUPPORTS_REDUCED_MOTION=True
def log(s):
    with open('resources.log','a') as f: f.write(s+'\\n')
def init_resources(scope):
    log('init'); scope.defer(lambda: log('close'))
    if os.environ.get('FAIL_INIT'): raise RuntimeError('init failed')
def render_frame(t):
    if os.environ.get('FAIL_FRAME'): raise RuntimeError('frame failed')
    return np.full((8,8,3), 200 if os.environ.get('MEDO_MOTION_MODE')=='reduced' else 20, dtype=np.uint8)
''', encoding='utf8')
    return tmp_path, ffmpeg


def run_chunk(project, ffmpeg, mode='normal', **extra):
    env = {**os.environ, 'REEL_DIR': str(project), 'FFMPEG_BIN': ffmpeg, 'MEDO_MOTION_MODE': mode, **extra}
    return subprocess.run([sys.executable, str(project / 'chunk.py'), '0', '2'], cwd=project, env=env, capture_output=True, text=True, timeout=30)


def test_direct_chunk_cache_is_separated_and_scopes_close(p_project):
    project, ffmpeg = p_project
    for mode, expected in [('normal', 'verified'), ('normal', 'cached'), ('reduced', 'verified'), ('normal', 'verified')]:
        result = run_chunk(project, ffmpeg, mode)
        assert result.returncode == 0, result.stderr
        assert expected in result.stdout
        assert (project / 'out/c_00000_00002.mode').read_text().strip() == mode
    assert (project / 'resources.log').read_text().splitlines() == ['init', 'close'] * 3


@pytest.mark.parametrize('fault', ['FAIL_INIT', 'FAIL_FRAME'])
def test_p_scene_errors_cleanup_without_cache_marker(p_project, fault):
    project, ffmpeg = p_project
    result = run_chunk(project, ffmpeg, 'reduced', **{fault: '1'})
    assert result.returncode != 0
    assert (project / 'resources.log').read_text().splitlines() == ['init', 'close']
    assert not (project / 'out/c_00000_00002.mode').exists()


def test_p_reduced_requires_scene_opt_in(p_project):
    project, ffmpeg = p_project
    p = project / 'scenes.py'
    p.write_text(p.read_text().replace('SUPPORTS_REDUCED_MOTION=True', 'SUPPORTS_REDUCED_MOTION=False'))
    result = run_chunk(project, ffmpeg, 'reduced')
    assert result.returncode != 0 and 'SUPPORTS_REDUCED_MOTION' in result.stderr
    assert not (project / 'resources.log').exists()


def test_p_segment_profile_and_mode(p_project):
    project, ffmpeg = p_project
    output = project / 'segment.mp4'; profile = project / 'profile.json'
    cmd = [sys.executable, str(ROOT / 'tools/render_p_segment.py'), '--project', str(project), '--from-frame', '0', '--to-frame', '2', '--out', str(output), '--ffmpeg', ffmpeg, '--motion-mode', 'reduced', '--profile-out', str(profile)]
    result = subprocess.run(cmd, cwd=project, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    data = json.loads(profile.read_text()); assert data['motionMode'] == 'reduced' and data['frames'] == 2
    assert data['frameRenderMs']['p95'] >= 0 and data['encoderFinalizeMs'] >= 0
    assert (project / 'resources.log').read_text().splitlines() == ['init', 'close']
    assert subprocess.run(cmd, cwd=project, capture_output=True).returncode != 0


@pytest.fixture(scope='module')
def browser_env():
    toolkit = ROOT / 'tools/toolkit'
    if not (toolkit / 'node_modules/playwright-core').exists() or not shutil.which('node'):
        pytest.skip('K toolkit unavailable')
    result = subprocess.run(['node', str(ROOT / 'tools/chromium.mjs'), '--json'], capture_output=True, text=True, timeout=90)
    if result.returncode: pytest.skip('Chromium unavailable')
    config = json.loads(result.stdout)
    env = {**os.environ, 'MEDO_TOOLKIT': str(toolkit), 'MEDO_CHROMIUM': config['executablePath'],
           'LD_LIBRARY_PATH': (config.get('libraryPath') or '') + ':' + os.environ.get('LD_LIBRARY_PATH', '')}
    env.pop('MEDO_MOTION_MODE', None)
    return env


@pytest.fixture
def k_project(tmp_path, browser_env):
    project = tmp_path / 'k'; project.mkdir()
    shutil.copytree(SKILL / 'templates/render', project / 'src')
    (project / 'package.json').write_text('{"type":"module"}\n')
    (project / 'src/data.js').write_text("export const W=100,H=100,DURATION=1,scenes=[{id:'one',start:0,end:1}];\n")
    (project / 'src/scenes/one.js').write_text('''export const supportsReducedMotion=true;
export function init({resources}){resources.defer(()=>{});}
export function draw(ctx,t,{motionMode}){ctx.fillStyle=motionMode==='reduced'?'#ff0000':'#0000ff';ctx.fillRect(0,0,100,100);}
''')
    return project, browser_env


def run_k(project, env, out, *extra):
    return subprocess.run(['node', 'src/render.js', '--from', '0', '--to', '0.1', '--fps', '30', '--scale', '.5', '--jpg', '--out', out, *extra], cwd=project, env=env, capture_output=True, text=True, timeout=90)


def test_k_mode_reaches_scene_and_normal_default_is_identical(k_project):
    project, env = k_project
    for out, extra in [('default', []), ('normal', ['--motion-mode', 'normal']), ('reduced', ['--motion-mode', 'reduced', '--profile'])]:
        result = run_k(project, env, out, *extra)
        assert result.returncode == 0, result.stderr
    assert (project/'default/00000.jpg').read_bytes() == (project/'normal/00000.jpg').read_bytes()
    assert (project/'default/00000.jpg').read_bytes() != (project/'reduced/00000.jpg').read_bytes()
    profile = json.loads((project/'reduced/render-profile.json').read_text())
    assert profile['motionMode'] == 'reduced' and profile['captureAndWriteMs']['p95'] >= 0


def test_k_unsupported_and_cleanup_errors_fail(k_project):
    project, env = k_project; scene = project / 'src/scenes/one.js'
    original = scene.read_text(); scene.write_text(original.replace('supportsReducedMotion=true', 'supportsReducedMotion=false'))
    result = run_k(project, env, 'unsupported', '--motion-mode', 'reduced')
    assert result.returncode != 0 and 'supportsReducedMotion' in result.stderr
    scene.write_text(original.replace('resources.defer(()=>{});', "resources.defer(()=>{throw Error('cleanup failed')});"))
    result = run_k(project, env, 'cleanup')
    assert result.returncode != 0 and 'cleanup' in result.stderr.lower()


def test_k_reduced_requires_only_active_scenes_and_init_failures_are_reported(k_project):
    project, env = k_project
    data = project / 'src/data.js'; scene = project / 'src/scenes/one.js'
    data.write_text("export const W=100,H=100,DURATION=1,scenes=[{id:'one',start:0,end:.5},{id:'two',start:.5,end:1}];\n")
    (project / 'src/scenes/two.js').write_text('export function draw(){}\n')
    result = run_k(project, env, 'active-only', '--motion-mode', 'reduced')
    assert result.returncode == 0, result.stderr
    result = subprocess.run(['node', 'src/render.js', '--from', '.5', '--to', '.6', '--fps', '30', '--scale', '.5', '--jpg', '--out', 'bad-active', '--motion-mode', 'reduced'], cwd=project, env=env, capture_output=True, text=True, timeout=90)
    assert result.returncode != 0 and 'supportsReducedMotion' in result.stderr
    original = scene.read_text()
    scene.write_text(original.replace('resources.defer(()=>{});', "resources.defer(()=>{});throw Error('init failed');"))
    result = run_k(project, env, 'init-failure', '--motion-mode', 'reduced')
    assert result.returncode != 0 and 'initialization failed' in result.stderr


def test_invalid_mode_is_rejected_by_clis(p_project, k_project):
    project, ffmpeg = p_project
    assert run_chunk(project, ffmpeg, 'invalid').returncode != 0
    k, env = k_project
    assert run_k(k, env, 'invalid', '--motion-mode', 'invalid').returncode != 0
    result = subprocess.run(['node', str(SKILL / 'templates/remotion/scripts/render.mjs'), '--motion-mode', 'invalid'], cwd=k, capture_output=True, text=True)
    assert result.returncode != 0 and 'motion-mode' in result.stderr
    result = subprocess.run([sys.executable, str(ROOT / 'tools/render_hybrid.py'), '--motion-mode', 'invalid'], cwd=k, capture_output=True, text=True)
    assert result.returncode != 0 and 'invalid choice' in result.stderr
