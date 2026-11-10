"""Engine K needs the toolkit's Chromium; the hybrid runner fills it in instead of failing.

`tools/pipeline.py` has always resolved Chromium for the caller; `render_hybrid.py` did not, so a
hybrid reel with a K overlay run from a clean shell died inside Node with
`Cannot find module 'playwright-core'`. These tests pin the resolution rules: fill what is missing,
never overwrite what the caller set, never download anything, and never turn a missing browser into
a crash for a reel that does not need one.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import render_hybrid  # noqa: E402


def plan_with(layers: list[dict]) -> dict:
    return {"segments": [{"id": "s", "layers": layers}]}


def test_a_reel_without_engine_k_asks_for_no_browser():
    assert not render_hybrid.needs_engine_k(plan_with([{"engine": "p", "alpha": False}]))
    assert not render_hybrid.needs_engine_k(plan_with([{"engine": "r", "alpha": False}]))
    assert render_hybrid.needs_engine_k(plan_with([{"engine": "k", "alpha": False}]))
    assert render_hybrid.needs_engine_k(
        plan_with([{"engine": "p", "alpha": False}, {"engine": "k", "alpha": True}]))


def test_the_toolkit_is_filled_only_when_it_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(render_hybrid, "TOOLKIT", tmp_path / "toolkit")
    monkeypatch.setattr(render_hybrid, "chromium_config", lambda node: None)
    env = render_hybrid.ensure_engine_k_environment({}, "node")
    assert "MEDO_TOOLKIT" not in env  # nothing installed → claim nothing

    (tmp_path / "toolkit" / "node_modules" / "playwright-core").mkdir(parents=True)
    env = render_hybrid.ensure_engine_k_environment({}, "node")
    assert env["MEDO_TOOLKIT"] == str(tmp_path / "toolkit")


def test_the_browser_and_its_libraries_are_taken_from_the_helper(monkeypatch):
    monkeypatch.setattr(render_hybrid, "chromium_config",
                        lambda node: {"executablePath": "/tmp/chromium", "libraryPath": "/libs/al2023"})
    env = render_hybrid.ensure_engine_k_environment({"LD_LIBRARY_PATH": "/already"}, "node")
    assert env["MEDO_CHROMIUM"] == "/tmp/chromium"
    assert env["LD_LIBRARY_PATH"] == "/libs/al2023:/already"


def test_a_caller_that_already_resolved_chromium_is_left_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(render_hybrid, "TOOLKIT", tmp_path / "absent")
    def explode(node):  # must not be consulted
        raise AssertionError("chromium_config must not run when MEDO_CHROMIUM is already set")

    monkeypatch.setattr(render_hybrid, "chromium_config", explode)
    env = render_hybrid.ensure_engine_k_environment({"MEDO_CHROMIUM": "/opt/chrome",
                                                     "LD_LIBRARY_PATH": "/x"}, "node")
    assert env == {"MEDO_CHROMIUM": "/opt/chrome", "LD_LIBRARY_PATH": "/x"}


def test_a_broken_helper_is_not_fatal(tmp_path, monkeypatch):
    monkeypatch.setattr(render_hybrid, "TOOLKIT", tmp_path / "absent")
    monkeypatch.setattr(render_hybrid, "chromium_config", lambda node: None)
    env = {"PATH": "/usr/bin"}
    assert render_hybrid.ensure_engine_k_environment(env, "node") == {"PATH": "/usr/bin"}


def test_the_helper_is_offline_and_never_installs(tmp_path, monkeypatch):
    """No helper file → no subprocess at all (so nothing can start a download)."""
    import subprocess

    monkeypatch.setattr(render_hybrid, "ROOT", tmp_path)
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: calls.append(a) or None)
    assert render_hybrid.chromium_config("node") is None
    assert calls == []
