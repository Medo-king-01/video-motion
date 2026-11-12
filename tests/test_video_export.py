"""MP4 delivery: H.264 through PyAV, frames from the reference renderer, sidecar that re-checks the file."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

av = pytest.importorskip("av", reason="MP4 export needs PyAV")

import audio_export  # noqa: E402
import video_export  # noqa: E402


def ppm(width: int, height: int, color: bytes) -> bytes:
    return f"P6\n{width} {height}\n255\n".encode("ascii") + color * (width * height)


def project(tmp_path: Path, *, width: int = 16, height: int = 16, duration: int = 64_000,
            fps: int = 30) -> dict:
    payload = ppm(width, height, b"\x40\x80\xc0")
    (tmp_path / "still.ppm").write_bytes(payload)
    return {
        "schemaVersion": "1.0", "id": "mp4", "name": "MP4 demo",
        "profile": {"width": width, "height": height, "fps": {"num": fps, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": duration, "seed": 2,
        "assets": [{"id": "a1", "kind": "image", "uri": "still.ppm",
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "v1", "kind": "video", "enabled": True, "clips": [
            {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": duration,
             "sourceIn": 0, "effects": [], "keyframes": []}]}],
    }


def tone(tmp_path: Path, *, seconds: float = 1.0) -> Path:
    import math  # noqa: PLC0415
    import struct  # noqa: PLC0415
    import wave  # noqa: PLC0415

    path = tmp_path / "vo.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"".join(struct.pack("<h", int(9000 * math.sin(2 * math.pi * 220 * i / 48_000)))
                                    for i in range(int(seconds * 48_000))))
    return path


# ---------------------------------------------------------------- build
def test_a_project_becomes_an_h264_file_with_the_expected_frames(tmp_path: Path) -> None:
    manifest = video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4")
    assert manifest["video"] == {"width": 16, "height": 16, "fps": 30, "frames": 8, "codec": "libx264",
                                "crf": 20, "preset": "medium",
                                "frameRoot": manifest["video"]["frameRoot"]}
    probe = video_export.inspect(tmp_path / "reel.mp4")
    assert probe["videoFrames"] == 8 and probe["streams"]["video"] == 1
    assert manifest["decode"]["frames"] == 8 and len(manifest["decode"]["sha256"]) == 64
    assert manifest["audio"] is None
    with av.open(str(tmp_path / "reel.mp4")) as container:
        stream = container.streams.video[0]
        assert stream.codec_context.name == "h264" and stream.average_rate == 30
        assert (stream.width, stream.height) == (16, 16)


def test_the_file_is_laid_out_for_streaming(tmp_path: Path) -> None:
    # faststart: the index comes before the media, so a browser can start without the whole file.
    video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4")
    payload = (tmp_path / "reel.mp4").read_bytes()
    assert 0 <= payload.find(b"moov") < payload.find(b"mdat")


def test_the_frame_root_pins_the_rendered_pictures_not_the_encoder(tmp_path: Path) -> None:
    # x264's bytes are not guaranteed identical between runs, and two different bitstreams may decode to
    # slightly different samples. What is stable is the picture sequence that went in.
    first = video_export.build(project(tmp_path), tmp_path, tmp_path / "a.mp4")
    second = video_export.build(project(tmp_path), tmp_path, tmp_path / "b.mp4")
    assert first["video"]["frameRoot"] == second["video"]["frameRoot"]
    # …and each file's own decoded fingerprint stays true to that file.
    assert video_export.verify(first, tmp_path / "a.mp4", decode=True) == []
    assert video_export.verify(second, tmp_path / "b.mp4", decode=True) == []


def test_silent_audio_is_muxed_as_a_second_stream(tmp_path: Path) -> None:
    manifest = video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4",
                                 audio=tone(tmp_path))
    probe = video_export.inspect(tmp_path / "reel.mp4")
    assert probe["streams"] == {"video": 1, "audio": 1}
    assert manifest["audio"]["file"] == "vo.wav"
    assert manifest["video"]["frames"] == 8


def test_the_audio_must_exist(tmp_path: Path) -> None:
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4",
                           audio=tmp_path / "gone.wav")
    assert excinfo.value.code == "M06"


def test_a_half_frame_rate_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["profile"]["fps"] = {"num": 30_000, "den": 1_001}
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(data, tmp_path, tmp_path / "reel.mp4")
    assert excinfo.value.code == "M01" and "integer rate" in excinfo.value.message


def test_an_odd_canvas_is_refused_before_encoding(tmp_path: Path) -> None:
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(project(tmp_path, width=17, height=17), tmp_path, tmp_path / "reel.mp4")
    assert excinfo.value.code == "M01" and "even" in excinfo.value.message


def test_the_frame_cap_is_enforced(tmp_path: Path) -> None:
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4", max_frames=2)
    assert excinfo.value.code == "M04" and "cap" in excinfo.value.message


def test_an_invalid_project_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["duration"] = 10
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(data, tmp_path, tmp_path / "reel.mp4")
    assert excinfo.value.code == "M01"


def test_a_project_the_renderer_cannot_draw_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": [
        {"id": "c2", "kind": "media", "assetId": "a1", "start": 0, "duration": 32_000,
         "sourceIn": 0, "effects": [], "keyframes": []}]})
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(data, tmp_path, tmp_path / "reel.mp4")
    assert excinfo.value.code == "M02" and "V02" in excinfo.value.message


# ---------------------------------------------------------------- manifest
def test_an_edited_file_is_caught(tmp_path: Path) -> None:
    manifest = video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4")
    out = tmp_path / "reel.mp4"
    assert video_export.verify(manifest, out) == []
    out.write_bytes(out.read_bytes() + b"\x00")
    assert any("no longer match" in error for error in video_export.verify(manifest, out))


def test_a_spliced_decode_is_caught(tmp_path: Path) -> None:
    manifest = video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4")
    other = video_export.build(project(tmp_path, duration=32_000), tmp_path, tmp_path / "short.mp4")
    (tmp_path / "reel.mp4").write_bytes((tmp_path / "short.mp4").read_bytes())
    errors = video_export.verify(manifest, tmp_path / "reel.mp4", decode=True)
    assert errors


@pytest.mark.parametrize("edit", [
    lambda m: m["video"].update(fps=24),
    lambda m: m["video"].update(frameRoot="short"),
    lambda m: m["decode"].update(frames=1),
    lambda m: m["totals"].update(durationSeconds=9.0),
    lambda m: m.update(version=3),
])
def test_a_drifted_manifest_is_caught(tmp_path: Path, edit) -> None:
    manifest = video_export.build(project(tmp_path), tmp_path, tmp_path / "reel.mp4")
    edit(manifest)
    assert video_export.validate_manifest(manifest) != []


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "video_export.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=600)


def test_cli_builds_and_checks(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(project(tmp_path)), encoding="utf-8")
    result = run("build", str(path), "-o", str(tmp_path / "reel.mp4"))
    assert result.returncode == 0, result.stderr
    assert "8 frames" in result.stdout and "16×16" in result.stdout
    checked = run("check", str(tmp_path / "reel.mp4.json"), "--decode")
    assert checked.returncode == 0, checked.stderr
    assert "Valid video · 8 frames" in checked.stdout


def test_cli_refuses_an_invalid_project(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["duration"] = 10
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert run("build", str(path), "-o", str(tmp_path / "reel.mp4")).returncode == 1


def test_cli_reports_a_missing_project(tmp_path: Path) -> None:
    assert run("build", str(tmp_path / "gone.json"), "-o", str(tmp_path / "reel.mp4")).returncode == 2
