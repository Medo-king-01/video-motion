"""The P engine template must resolve ffmpeg/ffprobe without repo-layout assumptions.

Regression test for the 2026-11 nightly failure: run_all.py imported the repo's
tools/lib/media_bin.py via `parents[3]`, which crashes when the engine runs from the
flat standalone copy (tools/selftest.py copies the engine into a temp dir).
"""
from __future__ import annotations

import importlib.util
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "medo-motion" / "templates" / "procedural-reels"
SPEC = importlib.util.spec_from_file_location("media_tools", ENGINE / "media_tools.py")
media_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(media_tools)


def _fake_binary(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def test_env_override_wins(tmp_path, monkeypatch):
    fake = _fake_binary(tmp_path / "bin" / "ffmpeg")
    elsewhere = _fake_binary(tmp_path / "other" / "ffmpeg")
    monkeypatch.setenv("FFMPEG_BIN", str(fake))
    assert media_tools.find_media("ffmpeg", start=elsewhere) == str(fake)


def test_walks_up_to_nearest_shim(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    shim = _fake_binary(repo / "tools" / "bin" / "ffprobe")
    nested = repo / "medo-motion" / "templates" / "procedural-reels" / "run_all.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("# template\n", encoding="utf-8")
    monkeypatch.delenv("FFPROBE_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    assert media_tools.find_media("ffprobe", start=nested) == str(shim)


def test_standalone_copy_still_finds_path(tmp_path, monkeypatch):
    # engine copied to a flat temp dir: no tools/bin anywhere above -> PATH decides
    fake = _fake_binary(tmp_path / "path-bin" / "ffmpeg")
    nested = tmp_path / "throwaway" / "engine" / "run_all.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("# standalone\n", encoding="utf-8")
    monkeypatch.delenv("FFMPEG_BIN", raising=False)
    monkeypatch.setenv("PATH", str(fake.parent))
    assert media_tools.find_media("ffmpeg", start=nested) == str(fake)


def test_unresolvable_returns_none_never_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("NOSUCHBIN_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    nested = tmp_path / "a" / "b" / "media_tools.py"
    nested.parent.mkdir(parents=True)
    nested.write_text("# x\n", encoding="utf-8")
    assert media_tools.find_media("nosuchbin", start=nested) is None


def test_run_all_has_no_repo_relative_import():
    src = (ENGINE / "run_all.py").read_text(encoding="utf-8")
    assert "parents[3]" not in src
    assert "from media_bin import" not in src
    assert "media_tools" in src


def test_engine_template_is_self_contained():
    # every absolute repo-layout escape in run_all.py must go through media_tools or the engine dir
    src = (ENGINE / "run_all.py").read_text(encoding="utf-8")
    assert '"tools" / "lib")' not in src
