"""Regression checks for local file boundaries and private environment files."""
from __future__ import annotations

import importlib
import os
import stat
import subprocess
import sys

import create_env
import get_fonts
import new_project
import pytest
from _safe_paths import checked_path
from conftest import ROOT, SKILL


@pytest.mark.skipif(os.name == 'nt', reason='POSIX permission bits')
def test_env_private_atomic_and_preserves_values(tmp_path):
    env = tmp_path / '.env'
    old_umask = os.umask(0)
    try:
        create_env.create_env(tmp_path)
    finally:
        os.umask(old_umask)
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    env.write_text('CUSTOM=local-test-value\nELEVENLABS_API_KEY=local-test-value\n')
    env.chmod(0o644)
    original = tmp_path / 'original'
    os.link(env, original)
    create_env.create_env(tmp_path)
    assert stat.S_IMODE(env.stat().st_mode) == 0o600
    assert 'ELEVENLABS_API_KEY=local-test-value' in env.read_text()
    assert original.read_text() == 'CUSTOM=local-test-value\nELEVENLABS_API_KEY=local-test-value\n'
    assert not list(tmp_path.glob('.env.*'))


@pytest.mark.parametrize('name', ['.env', '.gitignore'])
@pytest.mark.parametrize('dangling', [False, True])
def test_env_rejects_symlinks_without_touching_target(tmp_path, name, dangling):
    outside = tmp_path / 'outside'
    if not dangling:
        outside.write_text('keep')
    (tmp_path / name).symlink_to(outside)
    with pytest.raises(ValueError, match='symlink'):
        create_env.create_env(tmp_path)
    assert outside.read_text() == 'keep' if not dangling else not outside.exists()
    if name == '.gitignore':
        assert not (tmp_path / '.env').exists()


def test_env_atomic_failure_preserves_old_file(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('CUSTOM=keep\n')
    def fail(*_args):
        raise OSError('simulated replace failure')
    monkeypatch.setattr(create_env.os, 'replace', fail)
    with pytest.raises(OSError):
        create_env.create_env(tmp_path)
    assert env.read_text() == 'CUSTOM=keep\n'
    assert not list(tmp_path.glob('.env.*'))


def test_paths_reject_symlink_ancestor_and_nested_files(tmp_path):
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match='symlink'):
        checked_path(link / 'new' / 'file')
    tree = tmp_path / 'tree'
    tree.mkdir()
    (tree / 'file').symlink_to(outside / 'missing')
    with pytest.raises(ValueError, match='symlink'):
        checked_path(tree, tree=True)
    with pytest.raises(ValueError, match='escapes'):
        checked_path(tmp_path / 'escape', within=tree)


@pytest.mark.parametrize('nested', [False, True])
def test_scaffold_force_rejects_external_target(tmp_path, monkeypatch, nested):
    monkeypatch.setattr(new_project, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['new_project.py', 'probe', '--force'])
    outside = tmp_path / 'outside'
    outside.mkdir()
    project = tmp_path / 'projects' / 'probe'
    project.parent.mkdir()
    if nested:
        project.mkdir()
        (project / 'plan').symlink_to(outside, target_is_directory=True)
    else:
        project.symlink_to(outside, target_is_directory=True)
    with pytest.raises(SystemExit, match='symlink'):
        new_project.main()
    assert list(outside.iterdir()) == []


def test_scaffold_sources_trackable_outputs_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(new_project, 'ROOT', tmp_path)
    monkeypatch.setattr(sys, 'argv', ['new_project.py', 'ignore-probe'])
    (tmp_path / 'assets' / 'fonts').mkdir(parents=True)
    new_project.main()
    for relative in ['BRIEF.md', 'plan/beats.json', 'plan/text-direction.json']:
        assert (tmp_path / 'projects' / 'ignore-probe' / relative).is_file()
        result = subprocess.run(['git', 'check-ignore', '--no-index', 'projects/ignore-probe/' + relative],
                                cwd=ROOT, capture_output=True)
        assert result.returncode == 1, result.stdout
    for relative in ['out/frame.png', 'cache/a.json', 'renders/a.png', 'frames/a.png', 'video.mp4',
                     'node_modules/a.js', '.env', '.env.local', '.env.tmp-abcd']:
        result = subprocess.run(['git', 'check-ignore', '--no-index', 'projects/ignore-probe/' + relative],
                                cwd=ROOT, capture_output=True)
        assert result.returncode == 0, relative


def test_reference_analysis_rejects_motion_symlink_before_probe(tmp_path):
    ref = tmp_path / 'input.mp4'
    ref.write_bytes(b'not a real video: path checks must run first')
    outside = tmp_path / 'outside'
    outside.mkdir()
    protected = outside / 'strip_001.jpg'
    protected.write_bytes(b'keep')
    out = tmp_path / 'out'
    out.mkdir()
    (out / 'motion').symlink_to(outside, target_is_directory=True)
    result = subprocess.run([sys.executable, str(SKILL / 'scripts' / 'analyze_ref.py'), str(ref), '--out', str(out)],
                            capture_output=True, text=True)
    assert result.returncode != 0
    assert 'symlink' in result.stderr
    assert protected.read_bytes() == b'keep'


@pytest.mark.parametrize('family', ['../../Inter', '/Inter', '..\\Inter', '...'])
def test_font_paths_rejected_before_network(tmp_path, monkeypatch, family):
    monkeypatch.setattr(sys, 'argv', ['get_fonts.py', family, '--dest', str(tmp_path / 'fonts')])
    def fail(*args):
        pytest.fail('unsafe names must not reach network')
    monkeypatch.setattr(get_fonts, 'lookup', fail)
    with pytest.raises(SystemExit):
        get_fonts.main()
    assert not (tmp_path / 'fonts').exists()


def test_font_download_rejects_listing_paths_and_symlinks(tmp_path):
    with pytest.raises(ValueError, match='filename'):
        get_fonts.download({'name': '../outside.ttf'}, tmp_path)
    (tmp_path / 'font.ttf').symlink_to(tmp_path / 'missing')
    with pytest.raises(ValueError, match='symlink'):
        get_fonts.download({'name': 'font.ttf'}, tmp_path)


def test_p_segment_does_not_delete_existing_part(tmp_path):
    # Fail after temporary-file allocation, before rendering; an old .part file
    # belongs to the user, not to this invocation.
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'scenes.py').write_text('raise RuntimeError("not rendered")')
    ffmpeg = tmp_path / 'ffmpeg'
    ffmpeg.write_text('unused')
    old_part = tmp_path / 'segment.part.mp4'
    old_part.write_bytes(b'keep old render')
    result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'render_p_segment.py'), '--project', str(project),
                             '--from-frame', '0', '--to-frame', '1', '--out', str(tmp_path / 'segment.mp4'),
                             '--ffmpeg', str(ffmpeg)], capture_output=True)
    assert result.returncode != 0
    assert old_part.read_bytes() == b'keep old render'
    assert sorted(p.name for p in tmp_path.glob('*.mp4')) == ['segment.part.mp4']


def test_type_system_detects_missing_font_and_missing_family(tmp_path):
    import json
    fonts = importlib.import_module('fonts_install')
    (tmp_path / 'fonts.json').write_text(json.dumps({'families': {}}))
    problems = fonts.check_type_system(tmp_path)
    assert sum('manifest weights' in problem for problem in problems) == len(fonts.FAMILIES)
    assert any('missing/unsafe/empty' in problem for problem in problems)


def test_p_segment_rejects_dangling_output_link(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'scenes.py').write_text('')
    executable = tmp_path / 'ffmpeg'
    executable.write_text('')
    output = tmp_path / 'segment.mp4'
    outside = tmp_path / 'outside' / 'escaped.mp4'
    output.symlink_to(outside)
    result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'render_p_segment.py'), '--project', str(project),
        '--from-frame', '0', '--to-frame', '1', '--out', str(output), '--ffmpeg', str(executable)],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert 'symlink' in result.stderr
    assert not outside.parent.exists()


def test_segment_publish_does_not_overwrite_racing_output(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    (project / 'text_direction.py').write_text('')
    (project / 'art.py').write_text('W=H=2\n')
    (project / 'scenes.py').write_text('import numpy as np\ndef render_frame(t): return np.zeros((2,2,3), dtype=np.uint8)\n')
    executable = tmp_path / 'fake-ffmpeg'
    executable.write_text(f'''#!{sys.executable}
import sys
from pathlib import Path
sys.stdin.buffer.read()
path=Path(sys.argv[-1])
path.write_bytes(b'encoded')
(path.parent/'segment.mp4').write_bytes(b'other invocation')
''')
    executable.chmod(0o755)
    output = tmp_path / 'segment.mp4'
    result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'render_p_segment.py'), '--project', str(project),
        '--from-frame', '0', '--to-frame', '1', '--out', str(output), '--ffmpeg', str(executable)],
        capture_output=True, text=True)
    assert result.returncode != 0
    assert output.read_bytes() == b'other invocation'
    assert not list(tmp_path.glob('*.part.mp4'))
