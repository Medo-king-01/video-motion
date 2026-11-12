"""Frame-sequence delivery: PNGs plus a manifest that can be re-verified without re-rendering."""
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

import sequence_export  # noqa: E402


def ppm(width: int, height: int, color: bytes) -> bytes:
    return f"P6\n{width} {height}\n255\n".encode("ascii") + color * (width * height)


def project(tmp_path: Path, *, width: int = 8, height: int = 8, duration: int = 32_000) -> dict:
    payload = ppm(width, height, b"\x20\x40\x60")
    image = tmp_path / "frame-a.ppm"
    image.write_bytes(payload)
    return {
        "schemaVersion": "1.0", "id": "seq", "name": "Sequence demo",
        "profile": {"width": width, "height": height, "fps": {"num": 30, "den": 1}, "sampleRate": 48000},
        "timebase": 240_000, "duration": duration, "seed": 1,
        "assets": [{"id": "a1", "kind": "image", "uri": image.name,
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "v1", "kind": "video", "enabled": True, "clips": [
            {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": duration,
             "sourceIn": 0, "effects": [], "keyframes": []}]}],
    }


# ---------------------------------------------------------------- build
def test_a_project_becomes_a_verified_sequence(tmp_path: Path) -> None:
    data = project(tmp_path)
    manifest = sequence_export.build(data, tmp_path, tmp_path / "frames")
    assert manifest["frames"] == 4
    assert manifest["totals"]["written"] == 4
    assert [item["index"] for item in manifest["files"]] == [0, 1, 2, 3]
    assert manifest["files"][2]["tick"] == 16_000
    assert (tmp_path / "frames" / "frame-0002.png").is_file()
    assert sequence_export.verify(manifest, tmp_path / "frames") == []


def test_a_selection_exports_only_those_frames(tmp_path: Path) -> None:
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out", frames=[0, 2])
    assert [item["index"] for item in manifest["files"]] == [0, 2]
    assert not (tmp_path / "out" / "frame-0001.png").exists()
    assert manifest["frames"] == 4  # the project's length is still reported


def test_the_pixels_hash_and_the_file_hash_are_independent(tmp_path: Path) -> None:
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out")
    first = manifest["files"][0]
    assert len(first["pixelSha256"]) == 64 and len(first["fileSha256"]) == 64
    assert first["pixelSha256"] != first["fileSha256"]


def test_the_sequence_follows_the_project_profile(tmp_path: Path) -> None:
    square = project(tmp_path, width=10, height=10)
    manifest = sequence_export.build(square, tmp_path, tmp_path / "square")
    assert manifest["profile"] == {"width": 10, "height": 10, "fps": {"num": 30, "den": 1}}
    from PIL import Image  # noqa: PLC0415

    assert Image.open(tmp_path / "square" / "frame-0000.png").size == (10, 10)


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    data = project(tmp_path)
    first = sequence_export.build(data, tmp_path, tmp_path / "a")
    second = sequence_export.build(data, tmp_path, tmp_path / "b")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert (tmp_path / "a" / "frame-0001.png").read_bytes() == (tmp_path / "b" / "frame-0001.png").read_bytes()


@pytest.mark.parametrize(("frames", "code"), [
    ([], "Q03"),
    ([0, 0], "Q03"),
    ([9], "Q03"),
    ([-1], "Q03"),
])
def test_bad_selections_are_refused(tmp_path: Path, frames: list[int], code: str) -> None:
    with pytest.raises(sequence_export.SequenceError) as excinfo:
        sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out", frames=frames)
    assert excinfo.value.code == code


def test_the_frame_cap_is_enforced(tmp_path: Path) -> None:
    with pytest.raises(sequence_export.SequenceError) as excinfo:
        sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out", max_frames=2)
    assert excinfo.value.code == "Q03" and "cap" in excinfo.value.message


def test_an_invalid_project_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["duration"] = 10
    with pytest.raises(sequence_export.SequenceError) as excinfo:
        sequence_export.build(data, tmp_path, tmp_path / "out")
    assert excinfo.value.code == "Q01"


def test_a_project_the_renderer_cannot_draw_is_refused(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": [
        {"id": "c2", "kind": "media", "assetId": "a1", "start": 0, "duration": 8000,
         "sourceIn": 0, "effects": [], "keyframes": []}]})
    with pytest.raises(sequence_export.SequenceError) as excinfo:
        sequence_export.build(data, tmp_path, tmp_path / "out")
    assert excinfo.value.code == "Q02" and "V02" in excinfo.value.message


# ---------------------------------------------------------------- verify
def test_an_edited_frame_is_caught(tmp_path: Path) -> None:
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out")
    target = tmp_path / "out" / "frame-0001.png"
    target.write_bytes(target.read_bytes() + b"x")
    errors = sequence_export.verify(manifest, tmp_path / "out")
    assert any("no longer match" in error for error in errors)


def test_a_missing_frame_is_caught(tmp_path: Path) -> None:
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out")
    (tmp_path / "out" / "frame-0000.png").unlink()
    assert any("missing" in error for error in sequence_export.verify(manifest, tmp_path / "out"))


@pytest.mark.parametrize("edit", [
    lambda m: m["totals"].update(written=9),
    lambda m: m["files"][0].update(index=1),
    lambda m: m["files"][1].update(tick=1),
    lambda m: m["files"][0].update(fileSha256="short"),
    lambda m: m.update(version=2),
])
def test_a_drifted_manifest_is_caught(tmp_path: Path, edit) -> None:
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "out")
    edit(manifest)
    assert sequence_export.validate_manifest(manifest) != []


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "sequence_export.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def test_cli_builds_and_checks(tmp_path: Path) -> None:
    data = project(tmp_path)
    path = tmp_path / "project.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    out = tmp_path / "frames"
    result = run("build", str(path), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert "4 frames" in result.stdout
    checked = run("check", str(out / "sequence.json"))
    assert checked.returncode == 0, checked.stderr
    assert "Valid sequence · 4 frames" in checked.stdout


def test_cli_reports_a_missing_project(tmp_path: Path) -> None:
    assert run("build", str(tmp_path / "gone.json"), "-o", str(tmp_path / "f")).returncode == 2


def test_cli_refuses_an_invalid_project(tmp_path: Path) -> None:
    data = project(tmp_path)
    data["duration"] = 10
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert run("build", str(path), "-o", str(tmp_path / "f")).returncode == 1
