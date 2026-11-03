"""Exercise setup's shell contract without installing packages or touching HOME."""
from __future__ import annotations

import os
import shutil
import subprocess

import pytest
from conftest import ROOT


@pytest.fixture()
def sandbox(tmp_path):
    tools = tmp_path / 'tools'
    tools.mkdir()
    shutil.copy2(ROOT / 'tools' / 'setup.sh', tools / 'setup.sh')
    bin_dir = tmp_path / 'fake-bin'
    bin_dir.mkdir()
    scripts = {
        'python3': '''#!/bin/bash
case "$*" in
  *"pip install"*) exit "${PIP_CODE:-0}" ;;
  *"check_python_deps.py"*) exit "${DEPS_CODE:-0}" ;;
  *"doctor.py"*) exit "${DOCTOR_CODE:-0}" ;;
  *"fonts_install.py --check"*) exit "${FONTS_CHECK_CODE:-0}" ;;
  *"fonts_install.py"*) exit "${FONTS_CODE:-0}" ;;
esac
exit 0
''',
        'node': '#!/bin/bash\nexit "${NODE_CODE:-0}"\n',
        'npm': '#!/bin/bash\nexit "${NPM_CODE:-0}"\n',
        'ffmpeg': '#!/bin/bash\nexit 0\n',
        'ffprobe': '#!/bin/bash\nexit 0\n',
    }
    for name, text in scripts.items():
        path = bin_dir / name
        path.write_text(text)
        path.chmod(0o755)
    env = dict(os.environ, PATH=f'{bin_dir}:/usr/bin:/bin', PY=str(bin_dir / 'python3'))
    # Presence checks in --check mode are deliberate inventory, no browser launch.
    (tools / 'toolkit' / 'node_modules' / 'playwright-core').mkdir(parents=True)
    (tools / 'toolkit' / 'node_modules' / '@sparticuz' / 'chromium').mkdir(parents=True)
    return tmp_path, env


def snapshot(root):
    return {str(p.relative_to(root)): p.read_bytes() if p.is_file() else None for p in root.rglob('*')}


def run_setup(sandbox, *args, **env_vars):
    root, env = sandbox
    return subprocess.run(['bash', str(root / 'tools' / 'setup.sh'), *args],
                          env=dict(env, **env_vars), capture_output=True, text=True)


def test_check_is_read_only(sandbox):
    root, _ = sandbox
    before = snapshot(root)
    assert run_setup(sandbox, '--dev', '--check').returncode == 0
    assert snapshot(root) == before
    assert not (root / 'tools' / 'bin').exists()


@pytest.mark.parametrize('failure', ['PIP_CODE', 'NPM_CODE', 'DOCTOR_CODE', 'NODE_CODE'])
def test_setup_propagates_failures(sandbox, failure):
    assert run_setup(sandbox, **{failure: '7'}).returncode != 0


def test_check_missing_deps_fails_without_writes(sandbox):
    root, _ = sandbox
    before = snapshot(root)
    assert run_setup(sandbox, '--check', DEPS_CODE='1').returncode != 0
    assert snapshot(root) == before


def test_success_and_unknown_option(sandbox):
    assert run_setup(sandbox, '--dev').returncode == 0
    assert run_setup(sandbox, '--unexpected').returncode == 2


def test_font_install_failure_and_inventory_failure(sandbox):
    assert run_setup(sandbox, FONTS_CHECK_CODE='1', FONTS_CODE='7').returncode != 0
    assert run_setup(sandbox, '--check', FONTS_CHECK_CODE='1').returncode != 0


def test_missing_python_prerequisite(sandbox):
    assert run_setup(sandbox, PY='/nonexistent/python').returncode != 0
