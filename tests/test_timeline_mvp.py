"""B5 Timeline MVP: open → edit → save → reopen → render the same bytes.

The session layer is exercised on a 6-frame, 4×2 project with two canonical PPM stills, so the
identity claim ("re-rendering gives the same pixels") is checkable without a codec or a browser.
"""
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

import timeline_session as ts  # noqa: E402
from unified_project_check import validate  # noqa: E402
from unified_render_graph import compile_project, graph_digest  # noqa: E402

RED = b"P6\n4 2\n255\n" + bytes([255, 0, 0] * 8)
BLUE = b"P6\n4 2\n255\n" + bytes([0, 0, 255] * 8)


def clip(clip_id: str, asset: str, start: int, duration: int) -> dict:
    return {"id": clip_id, "kind": "media", "assetId": asset, "start": start,
            "duration": duration, "sourceIn": 0, "effects": [], "keyframes": []}


def make_project(tmp_path: Path, name: str = "project.json") -> Path:
    (tmp_path / "red.ppm").write_bytes(RED)
    (tmp_path / "blue.ppm").write_bytes(BLUE)
    project = json.loads((ROOT / "tests" / "fixtures" / "unified_project" / "basic.json").read_text(encoding="utf-8"))
    project["profile"].update(width=4, height=2)
    project["duration"] = 48000
    project["assets"] = [
        {"id": "a1", "kind": "image", "uri": "red.ppm", "sha256": hashlib.sha256(RED).hexdigest()},
        {"id": "a2", "kind": "image", "uri": "blue.ppm", "sha256": hashlib.sha256(BLUE).hexdigest()},
    ]
    project["tracks"] = [
        {"id": "v1", "kind": "video", "enabled": True,
         "clips": [clip("c1", "a1", 0, 24000), clip("c2", "a2", 24000, 24000)]},
        {"id": "v2", "kind": "video", "enabled": False, "clips": []},
    ]
    assert validate(project) == []
    path = tmp_path / name
    path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def project_path(tmp_path: Path) -> Path:
    return make_project(tmp_path)


@pytest.fixture
def session(project_path: Path) -> ts.Session:
    return ts.Session.open(project_path)


# ---------------------------------------------------------------- open
def test_open_reports_the_timeline(session: ts.Session) -> None:
    status = session.status()
    assert status["frames"] == 6
    assert status["frameTicks"] == 8000
    assert status["tracks"] == [{"id": "v1", "kind": "video", "enabled": True, "clips": 2},
                                {"id": "v2", "kind": "video", "enabled": False, "clips": 0}]
    assert status["canUndo"] is False and status["canRedo"] is False
    assert status["graphDigest"] == graph_digest(compile_project(session.project))


def test_open_refuses_an_invalid_project(tmp_path: Path) -> None:
    broken = make_project(tmp_path, "broken.json")
    data = json.loads(broken.read_text(encoding="utf-8"))
    data["schemaVersion"] = "0.9"
    broken.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        ts.Session.open(broken)


# ---------------------------------------------------------------- edit
def test_trim_shortens_a_clip(session: ts.Session) -> None:
    before = session.project
    session.apply({"op": "trim", "clip": "c2", "start": 24000, "end": 40000})
    c2 = session.project["tracks"][0]["clips"][1]
    assert (c2["start"], c2["duration"]) == (24000, 16000)
    assert session.project["duration"] == before["duration"], "the project duration is explicit, not implied"
    assert session.can_undo and not session.can_redo


def test_split_creates_a_second_clip(session: ts.Session) -> None:
    session.apply({"op": "split", "clip": "c2", "at": 32000, "id": "c2b"})
    clips = session.project["tracks"][0]["clips"]
    assert [(c["id"], c["start"], c["duration"]) for c in clips] == [
        ("c1", 0, 24000), ("c2", 24000, 8000), ("c2b", 32000, 16000)]


def test_move_crosses_tracks(session: ts.Session) -> None:
    session.apply({"op": "move", "clip": "c1", "track": "v2", "start": 0})
    tracks = {t["id"]: t for t in session.project["tracks"]}
    assert [c["id"] for c in tracks["v1"]["clips"]] == ["c2"]
    assert [c["id"] for c in tracks["v2"]["clips"]] == ["c1"]


def test_ripple_delete_shifts_later_clips(session: ts.Session) -> None:
    session.apply({"op": "ripple", "start": 0, "end": 24000, "tracks": ["v1"]})
    clips = session.project["tracks"][0]["clips"]
    assert [(c["id"], c["start"]) for c in clips] == [("c2", 0)]


def test_snap_finds_a_clip_boundary(session: ts.Session) -> None:
    entry = session.apply({"op": "snap", "tick": 24100, "tolerance": 300})
    assert (entry["tick"], entry["kind"]) == (24000, "clip")
    assert session.project["tracks"][0]["clips"][1]["start"] == 24000, "a query must not move anything"


def test_undo_and_redo_restore_the_exact_project(session: ts.Session) -> None:
    original = session.project
    session.apply({"op": "split", "clip": "c2", "at": 32000, "id": "c2b"})
    edited = session.project
    session.apply({"op": "undo"})
    assert session.project == original
    assert session.can_redo
    session.apply({"op": "redo"})
    assert session.project == edited


def test_undo_without_history_is_refused(session: ts.Session) -> None:
    with pytest.raises(ts.SessionError) as excinfo:
        session.apply({"op": "undo"})
    assert excinfo.value.code == "T04"


@pytest.mark.parametrize(("command", "code"), [
    ({"op": "explode"}, "T01"),
    ({"op": "trim", "clip": "c2", "start": 24000}, "T02"),
    ({"op": "trim", "clip": "c2", "start": 24000, "end": 40000, "speed": 2}, "T02"),
    ({"op": "trim", "clip": "c2", "start": 0, "end": 40000}, "T03"),
    ({"op": "split", "clip": "c2", "at": 24000, "id": "x"}, "T03"),
    ({"op": "move", "clip": "c2", "track": "nope", "start": 0}, "T03"),
    ({"op": "snap", "tick": 999999, "tolerance": 10}, "T03"),
    ("not a command", "T01"),
])
def test_bad_commands_are_refused_and_change_nothing(session: ts.Session, command, code: str) -> None:
    before = session.project
    with pytest.raises(ts.SessionError) as excinfo:
        session.apply(command)
    assert excinfo.value.code == code
    assert session.project == before
    assert session.can_undo is False


# ---------------------------------------------------------------- save + reopen
def test_save_then_reopen_is_identical(session: ts.Session, tmp_path: Path) -> None:
    session.apply({"op": "split", "clip": "c2", "at": 32000, "id": "c2b"})
    target = tmp_path / "saved.json"
    revision = session.save(target)
    assert len(revision) == 64
    reopened = ts.Session.open(target)
    assert reopened.project == session.project
    assert reopened.revision == revision
    assert reopened.can_undo is False, "history is a session, not a file"


def test_saving_twice_needs_the_current_revision(session: ts.Session, project_path: Path) -> None:
    session.apply({"op": "trim", "clip": "c2", "start": 24000, "end": 40000})
    session.save()
    stale = ts.Session.open(project_path)
    session.apply({"op": "trim", "clip": "c2", "start": 24000, "end": 36000})
    session.save()
    stale.apply({"op": "trim", "clip": "c2", "start": 24000, "end": 32000})
    with pytest.raises(ts.SessionError) as excinfo:
        stale.save(project_path)
    assert excinfo.value.code == "T05"


# ---------------------------------------------------------------- render identity
def test_rendering_the_same_frame_twice_gives_the_same_pixels(session: ts.Session, tmp_path: Path) -> None:
    first = session.render(3, tmp_path / "a.png")
    second = session.render(3, tmp_path / "b.png")
    assert first["pixelSha256"] == second["pixelSha256"]
    assert first["fileSha256"] == second["fileSha256"]
    assert (tmp_path / "a.png").read_bytes() == (tmp_path / "b.png").read_bytes()


def test_reopening_then_rendering_gives_the_same_bytes(session: ts.Session, tmp_path: Path) -> None:
    session.apply({"op": "split", "clip": "c2", "at": 32000, "id": "c2b"})
    session.apply({"op": "move", "clip": "c2b", "track": "v2", "start": 0})
    before = [session.render(i)["pixelSha256"] for i in (0, 3, 5)]
    target = tmp_path / "saved.json"
    session.save(target)
    reopened = ts.Session.open(target)
    assert [reopened.render(i)["pixelSha256"] for i in (0, 3, 5)] == before
    assert reopened.status()["graphDigest"] == session.status()["graphDigest"]


def test_edits_change_the_picture_and_undo_restores_it(session: ts.Session) -> None:
    before = session.render(4)["pixelSha256"]
    session.apply({"op": "move", "clip": "c2", "track": "v2", "start": 24000})
    assert session.render(4)["pixelSha256"] != before, "the moved clip leaves a gap"
    session.apply({"op": "undo"})
    assert session.render(4)["pixelSha256"] == before


def test_render_outside_the_project_is_refused(session: ts.Session) -> None:
    with pytest.raises(ts.SessionError) as excinfo:
        session.render(6)
    assert excinfo.value.code == "V01"


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "timeline_session.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def write_script(path: Path, commands: list[dict], frames: list[int] | None = None) -> Path:
    path.write_text(json.dumps({"commands": commands, "frames": frames or []}), encoding="utf-8")
    return path


def test_cli_check_and_status(project_path: Path) -> None:
    checked = run("check", str(project_path))
    assert checked.returncode == 0, checked.stderr
    assert "Valid project" in checked.stdout
    status = run("status", str(project_path))
    assert status.returncode == 0
    assert json.loads(status.stdout)["frames"] == 6


def test_cli_renders_one_frame(project_path: Path, tmp_path: Path) -> None:
    out = tmp_path / "frame.png"
    result = run("frame", str(project_path), "1", "-o", str(out))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["frame"] == 1 and out.exists()


def test_cli_script_round_trip(project_path: Path, tmp_path: Path) -> None:
    script = write_script(tmp_path / "edit.json", [
        {"op": "trim", "clip": "c2", "start": 24000, "end": 40000},
        {"op": "split", "clip": "c2", "at": 32000, "id": "c2b"},
        {"op": "snap", "tick": 24050, "tolerance": 200},
    ], frames=[0, 4])
    out = tmp_path / "edited.json"
    result = run("script", str(project_path), str(script), "-o", str(out), "--out-dir", str(tmp_path / "frames"))
    assert result.returncode == 0, result.stderr
    assert out.exists()
    manifest = json.loads((tmp_path / "edited.frames.json").read_text(encoding="utf-8"))
    assert [f["frame"] for f in manifest["frames"]] == [0, 4]
    assert all(len(f["pixelSha256"]) == 64 for f in manifest["frames"])
    assert (tmp_path / "frames" / "frame-0004.png").exists()
    # a second run from the same input is byte-identical
    first_project = out.read_bytes()
    run("script", str(project_path), str(script), "-o", str(tmp_path / "again.json"),
        "--out-dir", str(tmp_path / "frames2"))
    assert (tmp_path / "again.json").read_bytes() == first_project
    again = json.loads((tmp_path / "again.frames.json").read_text(encoding="utf-8"))
    assert [f["pixelSha256"] for f in again["frames"]] == [f["pixelSha256"] for f in manifest["frames"]]


def test_cli_script_stops_on_a_bad_command(project_path: Path, tmp_path: Path) -> None:
    script = write_script(tmp_path / "bad.json", [
        {"op": "split", "clip": "c2", "at": 32000, "id": "c2b"},
        {"op": "trim", "clip": "c2", "start": 0, "end": 40000},
    ])
    out = tmp_path / "never.json"
    result = run("script", str(project_path), str(script), "-o", str(out))
    assert result.returncode == 1
    assert "T03" in result.stderr
    assert not out.exists(), "a failed session must not leave a half-edited project"


def test_cli_autosave_writes_after_each_command(project_path: Path, tmp_path: Path) -> None:
    script = write_script(tmp_path / "auto.json", [
        {"op": "trim", "clip": "c2", "start": 24000, "end": 40000}])
    out = tmp_path / "autosaved.json"
    result = run("script", str(project_path), str(script), "-o", str(out), "--autosave")
    assert result.returncode == 0, result.stderr
    assert json.loads(out.read_text(encoding="utf-8"))["tracks"][0]["clips"][1]["duration"] == 16000
