"""Parallel test workers must not share Remotion's webpack bundle directory (N2).

The symptom was intermittent and only in parallel runs: `pytest -n 2` over the real-render modules
failed roughly one run in two, either with

    The requested path (/tmp/remotion-webpack-bundle-.../index.html) could not be found

or with

    Error: The bundler completed without emitting bundle.js

Both are the same collision. Remotion derives its bundle work directory from the entry point
(`src/index.ts`) under the OS temp root, and every scaffolded project has the same relative entry, so
two workers building at the same moment resolve to the same directory: one finishes and cleans up
while the other is still serving or writing it.

The fix is the temp root, not the entry point: each test process gets its own TMPDIR, which Remotion
and webpack both honour. Evidence: 2 failures in 3 parallel runs before, 0 in 5 after (see
docs/studio-review-2026-11-10.md, row N2).

What these tests protect is the property, not the incident: the directory is per process, stable
within a process, and actually exported to the child environment Remotion receives.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from conftest import remotion_env, remotion_tmpdir


def test_the_temp_dir_is_stable_within_a_process():
    first = remotion_tmpdir()
    assert first == remotion_tmpdir(), "the temp dir is rebuilt per call, so cleanup would leak"
    assert first.is_dir(), "the temp dir does not exist"
    assert os.access(first, os.W_OK), "the temp dir is not writable"


def test_two_processes_get_different_temp_dirs():
    """The whole point: a parallel worker must not resolve to our directory."""
    code = "from conftest import remotion_tmpdir; print(remotion_tmpdir())"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(Path(__file__).resolve().parent),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    other = result.stdout.strip().splitlines()[-1]
    assert other != str(remotion_tmpdir()), "a second process reused our temp dir - bundles will collide"


def test_the_env_hands_the_temp_dir_to_remotion():
    env = remotion_env({"PATH": "/usr/bin", "EXISTING": "kept"})
    for name in ("TMPDIR", "TMP", "TEMP"):
        assert env[name] == str(remotion_tmpdir()), f"{name} is not the per-process temp dir"
    # Everything else must pass through untouched, or the browser/font setup breaks.
    assert env["EXISTING"] == "kept" and env["PATH"] == "/usr/bin"


def test_the_default_env_still_contains_the_real_environment():
    """`remotion_env()` with no argument wraps os.environ instead of replacing it (Chromium lives there)."""
    env = remotion_env()
    for name in ("PATH",):
        assert env.get(name) == os.environ.get(name)
