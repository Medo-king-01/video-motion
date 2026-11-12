"""B4 ingest: one file in, one deterministic report out — and nothing else touched.

The clip is synthesised here (three flat shots with a moving bar), so the test does not need a media
asset in the repository and still exercises a real encoder/decoder round trip.
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

import video_ingest  # noqa: E402

cv2 = pytest.importorskip("cv2")
np = pytest.importorskip("numpy")
pytest.importorskip("av")

W, H, FPS = 160, 120, 30


def make_clip(path: Path, shots: int = 3, frames_each: int = 30) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (W, H))
    assert writer.isOpened(), "the test encoder could not open an mp4 writer"
    colors = [(20, 90, 20), (180, 40, 40), (200, 160, 40)]
    try:
        for index in range(shots * frames_each):
            frame = np.zeros((H, W, 3), np.uint8)
            frame[:, :] = colors[index // frames_each]
            x = (index * 3) % (W - 30)
            frame[40:70, x:x + 30] = (30, 30, 30)
            writer.write(frame)
    finally:
        writer.release()
    return path


@pytest.fixture(scope="module")
def clip(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return make_clip(tmp_path_factory.mktemp("clip") / "shots.mp4")


@pytest.fixture(scope="module")
def report(clip: Path) -> dict:
    return video_ingest.ingest(clip)


# ---------------------------------------------------------------- report shape
def test_the_report_describes_the_file(report: dict, clip: Path) -> None:
    video = report["video"]
    assert report["version"] == 1
    assert report["source"]["name"] == "shots.mp4"
    assert report["source"]["bytes"] == clip.stat().st_size
    assert video["width"] == W and video["height"] == H
    assert video["fps"] == FPS
    assert video["frames"] == 90
    assert video["duration"] == pytest.approx(3.0, abs=0.02)
    assert video["vfr"] is False
    assert len(report["deltas"]) == video["frames"] - 1


def test_the_hash_matches_the_bytes(report: dict, clip: Path) -> None:
    assert report["source"]["sha256"] == hashlib.sha256(clip.read_bytes()).hexdigest()


def test_the_ingest_is_deterministic(clip: Path, report: dict) -> None:
    again = video_ingest.ingest(clip)
    assert again == report


def test_the_report_is_json_round_trippable(report: dict) -> None:
    assert json.loads(json.dumps(report)) == report


def test_cuts_show_up_as_delta_spikes(report: dict) -> None:
    deltas = report["deltas"]
    spikes = sorted(range(len(deltas)), key=lambda i: deltas[i], reverse=True)[:2]
    assert sorted(spikes) == [29, 59], "a cut between frames 29/30 and 59/60 must dominate the deltas"
    assert deltas[29] > 25 and deltas[30] < 25


def test_the_summary_names_the_measurements(report: dict) -> None:
    line = video_ingest.summary(report)
    assert "160×120" in line and "30 fps" in line and "90 frames" in line and "VFR no" in line


# ---------------------------------------------------------------- building blocks
def test_the_signature_is_a_stable_colour_grid() -> None:
    frame = np.zeros((H, W, 3), np.uint8)
    frame[:, :] = (10, 200, 30)
    sig = video_ingest.signature(frame)
    assert len(sig) == video_ingest.GRID_W * video_ingest.GRID_H * 3
    assert set(sig) == {10, 30, 200}
    assert video_ingest.signature(frame) == sig


def test_identical_frames_have_zero_delta() -> None:
    frame = np.zeros((H, W, 3), np.uint8)
    sig = video_ingest.signature(frame)
    assert video_ingest.delta(sig, sig) == 0.0


def test_vfr_is_detected_from_timestamps() -> None:
    steady = [round(i / 30, 4) for i in range(30)]
    jittered = list(steady)
    jittered[10] = steady[10] + 0.05
    jittered[11] = steady[11] + 0.05
    assert video_ingest._vfr(steady, 30) is False
    assert video_ingest._vfr(jittered, 30) is True


# ---------------------------------------------------------------- refusals
def test_missing_file_is_a_clean_error(tmp_path: Path) -> None:
    with pytest.raises(video_ingest.IngestError):
        video_ingest.ingest(tmp_path / "gone.mp4")


def test_a_non_video_file_is_refused(tmp_path: Path) -> None:
    fake = tmp_path / "audio.mp4"
    fake.write_bytes(b"not a video at all")
    with pytest.raises(Exception):
        video_ingest.ingest(fake)


def test_a_frame_cap_is_enforced(clip: Path) -> None:
    with pytest.raises(video_ingest.IngestError, match="more than 20 frames"):
        video_ingest.ingest(clip, max_frames=20)


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "video_ingest.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=180)


def test_cli_writes_the_report(clip: Path, tmp_path: Path) -> None:
    out = tmp_path / "media-report.json"
    result = run(str(clip), "-o", str(out))
    assert result.returncode == 0, result.stderr
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["video"]["frames"] == 90


def test_cli_json_summary(clip: Path) -> None:
    result = run(str(clip), "--json")
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["frames"] == 90 and payload["deltas"] == 89 and payload["vfr"] is False


def test_cli_reports_a_missing_file(tmp_path: Path) -> None:
    result = run(str(tmp_path / "gone.mp4"))
    assert result.returncode == 2
    assert "cannot read" in result.stderr
