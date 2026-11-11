"""Media inspection is explicit, non-destructive, and fails closed on changed assets."""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_media import inspect_assets  # noqa: E402


def setup_project(tmp_path):
    p = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))
    media = tmp_path / "media"
    media.mkdir()
    path = media / "shot.mp4"
    path.write_bytes(b"original media bytes")
    p["assets"][0]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return p, path


def test_integrity_missing_changed_and_read_only(tmp_path):
    p, path = setup_project(tmp_path)
    before = copy.deepcopy(p)
    assert inspect_assets(p, tmp_path)[0]["status"] == "ok"
    assert p == before and path.read_bytes() == b"original media bytes"
    path.write_bytes(b"different")
    assert inspect_assets(p, tmp_path)[0]["status"] == "changed"
    path.unlink()
    assert inspect_assets(p, tmp_path)[0]["status"] == "missing"


def test_symlinks_and_non_regular_files_are_rejected(tmp_path):
    p, path = setup_project(tmp_path)
    path.unlink()
    path.mkdir()
    assert inspect_assets(p, tmp_path)[0]["status"] == "error"
    path.rmdir()
    target = tmp_path / "target"
    target.write_bytes(b"original media bytes")
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert "symlinks" in inspect_assets(p, tmp_path)[0]["error"]


def test_symlink_parent_rejected(tmp_path):
    p, path = setup_project(tmp_path)
    path.unlink()
    path.parent.rmdir()
    target = tmp_path / "other"
    target.mkdir()
    (target / "shot.mp4").write_bytes(b"original media bytes")
    try:
        path.parent.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    assert "symlinks" in inspect_assets(p, tmp_path)[0]["error"]


def test_probe_is_explicit_and_only_runs_on_matching_hash(tmp_path):
    p, path = setup_project(tmp_path)
    response = subprocess.CompletedProcess([], 0, '{"streams": [{"index": 0, "codec_type": "video"}]}', '')
    with patch("unified_project_media.subprocess.run", return_value=response) as run:
        assert "probe" not in inspect_assets(p, tmp_path)[0]
        run.assert_not_called()
        report = inspect_assets(p, tmp_path, probe=True)[0]
        assert report["probe"]["streams"][0]["index"] == 0
        assert run.call_args.args[0][-1] == str(path)
        path.write_bytes(b"changed")
        assert inspect_assets(p, tmp_path, probe=True)[0]["status"] == "changed"
        assert run.call_count == 1


@pytest.mark.parametrize("result", [
    subprocess.CompletedProcess([], 1, '', 'broken file'),
    subprocess.CompletedProcess([], 0, 'not json', ''),
    subprocess.CompletedProcess([], 0, '{}', ''),
])
def test_probe_failures_are_reported(tmp_path, result):
    p, _ = setup_project(tmp_path)
    with patch("unified_project_media.subprocess.run", return_value=result):
        assert inspect_assets(p, tmp_path, probe=True)[0]["status"] == "probe_error"


def test_probe_unavailable_and_timeout(tmp_path):
    p, _ = setup_project(tmp_path)
    for error in (FileNotFoundError("missing executable"), subprocess.TimeoutExpired("ffprobe", 1)):
        with patch("unified_project_media.subprocess.run", side_effect=error):
            assert inspect_assets(p, tmp_path, probe=True)[0]["status"] == "probe_error"


def test_cli_reports_status_and_returns_nonzero(tmp_path):
    p, path = setup_project(tmp_path)
    project_file = tmp_path / "project.json"
    project_file.write_text(json.dumps(p), encoding="utf-8")
    tool = ROOT / "tools/unified_project_media.py"
    cmd = [sys.executable, str(tool), str(project_file)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0
    assert json.loads(result.stdout)["assets"][0]["status"] == "ok"
    path.unlink()
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)["assets"][0]["status"] == "missing"
    project_file.write_text('{}', encoding="utf-8")
    assert subprocess.run(cmd, capture_output=True).returncode == 2


def test_import_new_asset_creates_verified_copy_without_mutating_project(tmp_path):
    from unified_project_media import import_asset

    p, _ = setup_project(tmp_path)
    source = tmp_path / "source.wav"
    source.write_bytes(b"audio source")
    before = copy.deepcopy(p)
    result = import_asset(p, tmp_path, source, asset_id="a2", kind="audio", uri="media/audio.wav", duration=240000)
    assert p == before
    assert (tmp_path / "media/audio.wav").read_bytes() == source.read_bytes()
    assert result["assets"][1]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert [r["status"] for r in inspect_assets(result, tmp_path)] == ["ok", "ok"]


def test_import_refuses_clobber_and_cleans_temporary_file(tmp_path):
    from unified_project_media import import_asset

    p, original = setup_project(tmp_path)
    source = tmp_path / "source"
    source.write_bytes(b"other")
    # Existing unrelated destination, not registered in the project.
    dest = tmp_path / "media/existing.wav"
    dest.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        import_asset(p, tmp_path, source, asset_id="a2", kind="audio", uri="media/existing.wav", duration=5)
    assert dest.read_bytes() == b"keep" and original.exists()
    assert sorted(f.name for f in dest.parent.iterdir()) == ["existing.wav", "shot.mp4"]


def test_import_invalid_inputs_do_not_write(tmp_path):
    from unified_project_media import import_asset

    p, _ = setup_project(tmp_path)
    source = tmp_path / "source"
    source.write_bytes(b"other")
    for options in [
        {"asset_id": "a1", "kind": "audio", "uri": "media/new.wav", "duration": 5},
        {"asset_id": "a2", "kind": "audio", "uri": "../new.wav", "duration": 5},
        {"asset_id": "a2", "kind": "audio", "uri": "media/new.wav"},
        {"asset_id": "a2", "kind": "image", "uri": "media/new.wav", "duration": 5},
        {"asset_id": "a2", "kind": "audio", "uri": "media/shot.mp4", "duration": 5},
    ]:
        with pytest.raises(ValueError):
            import_asset(p, tmp_path, source, **options)
    assert sorted(f.name for f in (tmp_path / "media").iterdir()) == ["shot.mp4"]


def test_import_refuses_symlink_parent(tmp_path):
    from unified_project_media import import_asset

    p, _ = setup_project(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlinks unavailable")
    source = tmp_path / "source"
    source.write_bytes(b"test")
    with pytest.raises(ValueError, match="symlinks"):
        import_asset(p, tmp_path, source, asset_id="img", kind="image", uri="link/image.png")
    assert not list(outside.iterdir())
