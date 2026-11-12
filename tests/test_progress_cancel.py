"""Long renders must be watchable and stoppable, and a stopped render must leave nothing behind.

`docs/development-plan-status.md` §3 item 6 asks for progress, cancel and cleanup; these tests are
the evidence for that row. They are cheap: a handful of 36×64 frames.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import sequence_export  # noqa: E402
import video_export  # noqa: E402

WIDTH, HEIGHT = 36, 64


def project(tmp_path: Path, ticks: int = 240_000) -> dict:
    payload = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii") + bytes([40, 60, 90]) * (WIDTH * HEIGHT)
    (tmp_path / "shot.ppm").write_bytes(payload)
    return {
        "schemaVersion": "1.3", "id": "progress-demo", "name": "Progress demo",
        "profile": {"width": WIDTH, "height": HEIGHT, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": ticks, "seed": 0,
        "assets": [{"id": "a1", "kind": "image", "uri": "shot.ppm",
                    "sha256": hashlib.sha256(payload).hexdigest()}],
        "tracks": [{"id": "v1", "kind": "video", "enabled": True, "clips": [
            {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": ticks,
             "sourceIn": 0, "effects": [], "keyframes": []}]}],
    }


def test_video_export_reports_progress_until_the_last_frame(tmp_path: Path) -> None:
    seen = []
    video_export.build(project(tmp_path), tmp_path, tmp_path / "out.mp4",
                       progress=lambda done, total: seen.append((done, total)))
    assert seen[0] == (1, 30) and seen[-1] == (30, 30)
    assert [done for done, _ in seen] == sorted(done for done, _ in seen)


def test_cancelling_a_video_export_removes_the_partial_file(tmp_path: Path) -> None:
    calls = {"count": 0}

    def cancel() -> bool:
        calls["count"] += 1
        return calls["count"] > 4

    out = tmp_path / "cut.mp4"
    with pytest.raises(video_export.VideoError) as excinfo:
        video_export.build(project(tmp_path), tmp_path, out, cancel=cancel)
    assert excinfo.value.code == "M07"
    assert not out.exists()


def test_sequence_export_reports_progress_per_frame(tmp_path: Path) -> None:
    seen = []
    manifest = sequence_export.build(project(tmp_path), tmp_path, tmp_path / "frames",
                                     frames=[0, 1, 2],
                                     progress=lambda done, total: seen.append((done, total)))
    assert seen == [(1, 3), (2, 3), (3, 3)]
    assert manifest["totals"]["written"] == 3


def test_cancelling_a_sequence_export_removes_the_frames_it_wrote(tmp_path: Path) -> None:
    calls = {"count": 0}

    def cancel() -> bool:
        calls["count"] += 1
        return calls["count"] > 2

    out = tmp_path / "frames"
    with pytest.raises(sequence_export.SequenceError) as excinfo:
        sequence_export.build(project(tmp_path), tmp_path, out, frames=[0, 1, 2, 3], cancel=cancel)
    assert excinfo.value.code == "Q06"
    assert not list(out.glob("*.png"))
    assert not (out / "sequence.json").exists()


def test_a_finished_run_writes_the_manifest_and_no_cancel_code(tmp_path: Path) -> None:
    out = tmp_path / "frames"
    sequence_export.build(project(tmp_path), tmp_path, out, frames=[0, 1], cancel=lambda: False)
    manifest = json.loads((out / "sequence.json").read_text(encoding="utf-8"))
    assert manifest["totals"]["written"] == 2
    assert sorted(path.name for path in out.glob("*.png")) == ["frame-0000.png", "frame-0001.png"]
