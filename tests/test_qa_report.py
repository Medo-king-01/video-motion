"""The HTML QA report: one self-contained page with lint, media findings, and a contact sheet."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FFMPEG = shutil.which("ffmpeg", path=str(ROOT / "tools" / "bin")) or "ffmpeg"
FFPROBE = shutil.which("ffprobe", path=str(ROOT / "tools" / "bin")) or "ffprobe"


def make_project(tmp_path: Path, seconds: float = 2.0) -> tuple[Path, Path]:
    project = tmp_path / "reel"
    (project / "plan").mkdir(parents=True)
    (project / "out").mkdir(parents=True)
    media = project / "out" / "master.mp4"
    subprocess.run(
        [FFMPEG, "-y", "-f", "lavfi", "-i", f"color=c=0x101820:s=270x480:r=30:d={seconds}",
         "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}", "-shortest",
         "-c:v", "libx264", "-preset", "ultrafast", "-crf", "30", "-c:a", "aac",
         "-b:a", "96k", "-movflags", "+faststart", str(media)],
        check=True, capture_output=True,
    )
    (project / "plan" / "beats.json").write_text(json.dumps({
        "duration": seconds, "bpm": 120,
        "scenes": [{"id": "s1", "start": 0.0, "end": seconds}],
    }), encoding="utf-8")
    return project, media


def run_report(project: Path, media: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "tools" / "qa_report.py"), str(project), "--media", str(media), *extra],
        capture_output=True, text=True, check=False, cwd=str(ROOT),
    )


def test_report_is_self_contained_and_shows_the_sheet(tmp_path: Path) -> None:
    project, media = make_project(tmp_path)
    out = tmp_path / "qa" / "report.html"
    result = run_report(project, media, "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert "QA REPORT" in result.stdout
    page = out.read_text(encoding="utf-8")
    assert 'dir="rtl"' in page and 'lang="ar"' in page
    # the contact sheet is embedded, not linked: the page must work from a bare file:// path
    assert "data:image/png;base64," in page
    assert "http://" not in page and "https://" not in page
    assert (out.parent / "contact-sheet.png").is_file()
    assert "Final Media QA" in page and "reel_lint" in page


def test_report_refuses_to_overwrite_unless_forced(tmp_path: Path) -> None:
    project, media = make_project(tmp_path, seconds=1.0)
    out = tmp_path / "qa" / "report.html"
    out.parent.mkdir(parents=True)
    out.write_text("stale", encoding="utf-8")
    first = run_report(project, media, "--out", str(out))
    assert first.returncode == 2
    assert "refusing to overwrite" in first.stderr
    assert out.read_text(encoding="utf-8") == "stale"
    second = run_report(project, media, "--out", str(out), "--force")
    assert second.returncode == 0 and "stale" not in out.read_text(encoding="utf-8")


def test_missing_media_is_an_error_not_a_crash(tmp_path: Path) -> None:
    project, _ = make_project(tmp_path, seconds=1.0)
    result = run_report(project, project / "out" / "nope.mp4")
    assert result.returncode == 2
    assert "media not found" in result.stderr


@pytest.mark.parametrize("seconds", [1.0])
def test_json_out_mirrors_the_page(tmp_path: Path, seconds: float) -> None:
    project, media = make_project(tmp_path, seconds=seconds)
    raw = tmp_path / "raw.json"
    assert run_report(project, media, "--json-out", str(raw)).returncode == 0
    payload = json.loads(raw.read_text(encoding="utf-8"))
    assert set(payload) == {"media_qa", "reel_lint"}
    assert payload["media_qa"]["status"] in {"pass", "fail", "incomplete"}
    assert FFPROBE  # the report leans on ffprobe; keep the dependency explicit
