from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "medo-motion" / "scripts"))
from reference_report import build_report  # noqa: E402


def test_reference_report_marks_sampled_palette_as_observational(tmp_path: Path):
    frames_dir = tmp_path / "frames"
    frames_dir.mkdir()
    samples = []
    for index, color in enumerate(((30, 20, 20), (190, 25, 15))):
        image = np.zeros((64, 36, 3), dtype=np.uint8)
        image[:] = color
        image[20:45, 8 + index:28 + index] = (245, 230, 220)
        path = frames_dir / f"{index:04d}.jpg"
        Image.fromarray(image).save(path)
        samples.append(path)

    out = tmp_path / "analysis"
    summary = build_report(
        source=tmp_path / "reference.mp4", out=out, sample_paths=samples,
        sample_fps=1, start=10, duration=4,
        info={"width": 1080, "height": 1920, "fps": 30},
        cuts=[10.8, 12.2, 16.0], audio=None, ffmpeg="ffmpeg",
    )

    assert summary["cut_count"] == 2
    assert summary["cut_times"] == [10.8, 12.2]
    assert summary["width"] == 1080
    assert summary["palette"]
    assert (out / "palette.png").is_file()
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "translate through the locked brand" in report
    assert "not a style prescription" in report
    assert (out / "analysis.json").is_file()
