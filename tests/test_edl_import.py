"""The other direction: an EDL comes back as a project, with real media and real hashes.

Nothing is invented — a reel that has no file is listed, not faked, and the rate must be known (our own
sidecar or an explicit `--fps`).
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import edl_export  # noqa: E402
import edl_import  # noqa: E402
import timeline_session  # noqa: E402


def make_media(folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, color in (("shot-a.png", (203, 39, 27)), ("shot-b.png", (20, 20, 20))):
        Image.new("RGB", (16, 16), color).save(folder / name)
    with wave.open(str(folder / "vo.wav"), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 16000)


def asset(folder: Path, name: str, kind: str, duration: int | None = None) -> dict:
    payload = {"id": name.split(".")[0].replace("-", ""), "kind": kind, "uri": name,
               "sha256": hashlib.sha256((folder / name).read_bytes()).hexdigest()}
    if duration is not None:
        payload["duration"] = duration
    return payload


def project_with_media(folder: Path) -> dict:
    return {
        "schemaVersion": "1.0", "id": "rt", "name": "Round trip",
        "profile": {"width": 1080, "height": 1920, "fps": {"num": 30, "den": 1}, "sampleRate": 48000},
        "timebase": 240_000, "duration": 480_000, "seed": 7,
        "assets": [asset(folder, "shot-a.png", "image"), asset(folder, "shot-b.png", "image"),
                   asset(folder, "vo.wav", "audio", 480_000)],
        "tracks": [
            {"id": "v1", "kind": "video", "enabled": True, "clips": [
                {"id": "c1", "kind": "media", "assetId": "shota", "start": 0, "duration": 160_000,
                 "sourceIn": 0, "effects": [], "keyframes": []},
                {"id": "c2", "kind": "media", "assetId": "shotb", "start": 240_000, "duration": 160_000,
                 "sourceIn": 0, "effects": [], "keyframes": []},
            ]},
            {"id": "a1", "kind": "audio", "enabled": True, "clips": [
                {"id": "m1", "kind": "media", "assetId": "vo", "start": 0, "duration": 400_000,
                 "sourceIn": 0, "effects": [], "keyframes": []},
            ]},
        ],
    }


def export(tmp_path: Path, project: dict) -> Path:
    text, manifest = edl_export.build_edl(project)
    edl = tmp_path / "reel.edl"
    edl.write_text(text, encoding="utf-8")
    Path(str(edl) + ".json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    return edl


# ---------------------------------------------------------------- round trip
def test_an_export_comes_back_as_the_same_edit(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    project = project_with_media(media)
    edl = export(tmp_path, project)
    back = edl_import.build_project(edl, media=media, name="Round trip")
    video = back["tracks"][0]["clips"]
    assert [(c["start"], c["duration"], c["sourceIn"]) for c in video] == \
           [(c["start"], c["duration"], c["sourceIn"]) for c in project["tracks"][0]["clips"]]
    assert edl_export.validate_manifest(edl_export.build_edl(back)[1]) == []
    def events(text: str) -> list[str]:
        return [line for line in text.splitlines() if line[:1].isdigit()]

    assert events(edl_export.build_edl(back)[0]) == events(edl.read_text(encoding="utf-8"))


def test_audio_and_stills_survive_the_trip(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    back = edl_import.build_project(export(tmp_path, project_with_media(media)), media=media)
    kinds = {a["kind"] for a in back["assets"]}
    assert kinds == {"image", "audio"}
    assert [t["kind"] for t in back["tracks"]] == ["video", "audio"]
    assert back["tracks"][1]["clips"][0]["duration"] == 400_000
    assert all(len(a["sha256"]) == 64 for a in back["assets"])


def test_gaps_are_kept_not_closed(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    back = edl_import.build_project(edl, media=media)
    assert back["tracks"][0]["clips"][1]["start"] == 240_000


def test_the_imported_project_opens_in_the_session(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    back = edl_import.build_project(edl, media=media)
    path = tmp_path / "back.json"
    path.write_text(json.dumps(back), encoding="utf-8")
    opened = timeline_session.Session.open(path)
    assert opened.status()["frames"] == 60  # the sidecar's duration restores the 2s canvas
    assert opened.status()["tracks"][0]["clips"] == 2


# ---------------------------------------------------------------- refusals
def test_a_reel_without_a_file_is_listed(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    (media / "shot-b.png").unlink()
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media)
    assert excinfo.value.code == "I03" and "SHOT_B" in excinfo.value.message


def test_no_sidecar_and_no_rate_is_refused(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    bare = tmp_path / "bare.edl"
    bare.write_text(edl.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(bare, media=media)
    assert excinfo.value.code == "I02"
    assert edl_import.build_project(bare, media=media, fps=30)["profile"]["fps"]["num"] == 30


def test_the_sidecar_wins_over_a_conflicting_flag(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, fps=25)
    assert excinfo.value.code == "I05"


def test_the_profile_rate_must_match_the_edl(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, profile_id="stop-motion-12")
    assert excinfo.value.code == "I05"


def test_an_overlapping_edl_is_refused(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    text = ("TITLE: overlap\nFCM: NON-DROP FRAME\n"
            "001  SHOT_A    V    C        00:00:00:00 00:00:02:00 00:00:00:00 00:00:02:00\n"
            "002  SHOT_A    V    C        00:00:00:00 00:00:02:00 00:00:01:00 00:00:03:00\n")
    edl = tmp_path / "overlap.edl"
    edl.write_text(text, encoding="utf-8")
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, fps=30)
    assert excinfo.value.code == "I04"


def test_a_frame_beyond_the_rate_is_named(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    text = ("TITLE: bad frame\nFCM: NON-DROP FRAME\n"
            "001  SHOT_A    V    C        00:00:00:00 00:00:00:29 00:00:00:00 00:00:00:29\n")
    edl = tmp_path / "bad.edl"
    edl.write_text(text, encoding="utf-8")
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, fps=12, profile_id="stop-motion-12")
    assert excinfo.value.code == "I05" and "29" in excinfo.value.message


def test_a_broken_edl_is_refused_before_media(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = tmp_path / "broken.edl"
    edl.write_text("not an edl\n", encoding="utf-8")
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, fps=30)
    assert excinfo.value.code == "I01"


def test_a_missing_media_directory_is_refused(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=tmp_path / "gone")
    assert excinfo.value.code == "I03"


def test_a_still_must_start_at_zero(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    text = ("TITLE: still\nFCM: NON-DROP FRAME\n"
            "001  SHOT_A    V    C        00:00:01:00 00:00:02:00 00:00:00:00 00:00:01:00\n")
    edl = tmp_path / "still.edl"
    edl.write_text(text, encoding="utf-8")
    with pytest.raises(edl_import.ImportError_) as excinfo:
        edl_import.build_project(edl, media=media, fps=30)
    assert excinfo.value.code == "I05"


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "edl_import.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def test_cli_writes_a_project(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    out = tmp_path / "out" / "back.json"
    result = run("build", str(edl), "--media", str(media), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert "clips" in result.stdout and out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["timebase"] == 240_000 and data["tracks"][0]["id"] == "v1"


def test_cli_refuses_a_missing_reel(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    (media / "shot-a.png").unlink()
    out = tmp_path / "back.json"
    result = run("build", str(edl), "--media", str(media), "-o", str(out))
    assert result.returncode == 1 and "I03" in result.stderr
    assert not out.exists()


def test_cli_needs_a_rate_without_a_sidecar(tmp_path: Path) -> None:
    media = tmp_path / "media"
    make_media(media)
    edl = export(tmp_path, project_with_media(media))
    bare = tmp_path / "bare.edl"
    bare.write_text(edl.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "back.json"
    assert run("build", str(bare), "--media", str(media), "-o", str(out)).returncode == 1
    assert run("build", str(bare), "--media", str(media), "--fps", "30", "-o", str(out)).returncode == 0
