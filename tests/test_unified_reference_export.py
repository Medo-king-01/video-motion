"""Reference export failure safety and optional actual FFmpeg round trip."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_reference_export import export_reference  # noqa: E402
from unified_reference_preview import PreviewError  # noqa: E402


def project(tmp_path):
    p = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))
    p["profile"].update(width=2, height=1)
    p["duration"] = 24000
    data = b"P6\n2 1\n255\n" + bytes([255, 0, 0, 0, 128, 255])
    (tmp_path / "image.ppm").write_bytes(data)
    p["assets"][0] = {"id": "a1", "kind": "image", "uri": "image.ppm",
                      "sha256": hashlib.sha256(data).hexdigest()}
    p["tracks"][0]["clips"][0].update(start=8000, duration=8000)
    return p


def test_encoder_failure_does_not_publish_or_leave_temp(tmp_path):
    p = project(tmp_path)
    out = tmp_path / "result.mkv"
    with pytest.raises(PreviewError, match="cannot start ffmpeg"):
        export_reference(p, tmp_path, out, ffmpeg=str(tmp_path / "missing"))
    assert not out.exists()
    assert not list(tmp_path.glob(".reference-export-*"))


def test_encoder_failures_and_empty_success_clean_up(tmp_path, monkeypatch):
    p = project(tmp_path)
    out = tmp_path / "result.mkv"
    for result in (subprocess.CompletedProcess([], 1, stderr=b"encoder error"),
                   subprocess.CompletedProcess([], 0, stderr=b"")):
        monkeypatch.setattr(subprocess, "run", lambda *args, _result=result, **kwargs: _result)
        with pytest.raises(PreviewError, match="E02"):
            export_reference(p, tmp_path, out)
        assert not out.exists()
        assert not list(tmp_path.glob(".reference-export-*"))


def test_invalid_input_and_existing_output_are_safe(tmp_path):
    p = project(tmp_path)
    out = tmp_path / "result.mkv"
    out.write_bytes(b"keep")
    with pytest.raises(FileExistsError):
        export_reference(p, tmp_path, out)
    assert out.read_bytes() == b"keep"
    with pytest.raises(PreviewError, match="mkv"):
        export_reference(p, tmp_path, tmp_path / "out.mp4")
    p["duration"] = 1000000000
    with pytest.raises(PreviewError, match="limit"):
        export_reference(p, tmp_path, tmp_path / "new.mkv")
    assert not list(tmp_path.glob(".reference-export-*"))


def test_missing_asset_fails_before_encoding(tmp_path):
    p = project(tmp_path)
    (tmp_path / "image.ppm").unlink()
    with pytest.raises(PreviewError, match="V03"):
        export_reference(p, tmp_path, tmp_path / "result.mkv")
    assert not (tmp_path / "result.mkv").exists()


def test_real_ffmpeg_lossless_frame_roundtrip(tmp_path):
    ffmpeg = os.environ.get("TEST_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("ffmpeg not installed; set TEST_FFMPEG to run integration test")
    p = project(tmp_path)
    out = tmp_path / "result.mkv"
    info = export_reference(p, tmp_path, out, ffmpeg=ffmpeg)
    assert info["frameCount"] == 3 and not info["audio"]
    decoded = subprocess.run([ffmpeg, "-v", "error", "-i", str(out), "-map", "0:v:0", "-f", "rawvideo",
                              "-pix_fmt", "rgba", "-fps_mode", "passthrough", "pipe:1"],
                             capture_output=True, check=True).stdout
    assert decoded == b"\0" * 8 + bytes([255, 0, 0, 255, 0, 128, 255, 255]) + b"\0" * 8
