"""Real hybrid drafts over odd and even frame ranges: P, K, a K alpha overlay, and the assembly.

`render_hybrid.py --draft` expects `end // 2 - start // 2` frames from a segment (draft frame k is
source frame 2k). Engine P counts the same way. Engine K — as a base and as an alpha overlay — is
asked for `--from start/30 --to end/30 --fps 15` and renders `ceil((end - start) / 2)` frames. The
two agree only when a segment has an even length; otherwise the draft stops with a contract error.

Measured on 2026-11-11 (real renders, this file): every case in ODD_K below fails with
"violates render contract … expected … 1 frames" (K base) or "overlay 1 produced 2 frame(s),
expected 1" (K overlay). They are marked `xfail(strict=True)`: the fix is a design choice that has
not been made yet, and a strict xfail turns red the moment the behaviour changes, so the marks
cannot outlive the fix.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
FIXTURE_PLAN = ROOT / "tests" / "fixtures" / "reel" / "good" / "plan"
for _path in (TOOLS, TOOLS / "lib"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

import media_bin  # noqa: E402
import render_hybrid  # noqa: E402

pytestmark = pytest.mark.slow  # real P and Chromium renders

PK = "p+k"  # an engine-P base with an engine-K alpha overlay

# (case id, [(engine, start_frame, end_frame), ...])
EVEN = [
    ("p-k-overlay-even", [("p", 0, 4), ("k", 4, 8), (PK, 8, 12)]),
    ("k-even", [("k", 0, 4), ("k", 4, 8)]),
]
ODD_P = [  # engine P counts like the runner, so odd ranges already work
    ("p-odd", [("p", 0, 3), ("p", 3, 6)]),
    ("p-odd-total", [("p", 0, 3), ("p", 3, 7)]),
]
ODD_K_THAT_HAPPENS_TO_MATCH = [  # odd start and odd end: both formulas give the same count
    ("overlay-3-6", [("p", 0, 3), (PK, 3, 6)]),
]
ODD_K = [
    ("k-0-3", [("k", 0, 3), ("k", 3, 8)]),
    ("k-2-5", [("k", 0, 2), ("k", 2, 5), ("k", 5, 8)]),
    ("k-between-p", [("p", 0, 4), ("k", 4, 7), ("p", 7, 10)]),
    ("k-30-61", [("k", 0, 30), ("k", 30, 61)]),
    ("overlay-0-3", [(PK, 0, 3), ("p", 3, 6)]),
    ("overlay-4-7", [("p", 0, 4), (PK, 4, 7), ("p", 7, 10)]),
]
KNOWN = pytest.mark.xfail(strict=True, reason="K renders ceil(len/2) draft frames; the runner expects "
                                              "end//2 - start//2 — fix pending a design decision")
CASES = ([pytest.param(plan, id=name) for name, plan in EVEN + ODD_P + ODD_K_THAT_HAPPENS_TO_MATCH]
         + [pytest.param(plan, id=name, marks=KNOWN) for name, plan in ODD_K])


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not media_bin.ffmpeg() or not shutil.which("node"):
        pytest.skip("ffmpeg and node are required for a real hybrid draft")
    target = tmp_path_factory.mktemp("hybrid-draft") / "reel"
    made = subprocess.run([sys.executable, str(TOOLS / "new_project.py"), "reel", "--engine", "hybrid",
                           "--out", str(target)], capture_output=True, text=True, timeout=300)
    assert made.returncode == 0, made.stdout + made.stderr
    for name in ("beats.json", "text-direction.json", "copy.json"):  # a directed text plan: both engines require it
        shutil.copy2(FIXTURE_PLAN / name, target / "plan" / name)
    return target


def _plan(segments: list[tuple[str, int, int]]) -> dict:
    out = []
    for index, (engine, start, end) in enumerate(segments):
        segment: dict = {"id": f"s{index}", "start_frame": start, "end_frame": end}
        if engine == PK:
            segment["layers"] = [{"engine": "p"}, {"engine": "k", "alpha": True}]
        else:
            segment["engine"] = engine
        out.append(segment)
    return {"version": 2, "fps": 30, "width": 1080, "height": 1920, "duration_frames": segments[-1][2],
            "segments": out, "audio": None}


def _draft(project: Path, segments: list[tuple[str, int, int]], name: str) -> tuple[subprocess.CompletedProcess, Path]:
    (project / "plan" / "hybrid.json").write_text(json.dumps(_plan(segments)), encoding="utf-8")
    out = project / "out" / f"{name}.mp4"
    out.unlink(missing_ok=True)
    env = dict(os.environ, PATH=f"{TOOLS / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    done = subprocess.run([sys.executable, str(TOOLS / "render_hybrid.py"), "--project", str(project), "--draft",
                           "--out", str(out)], capture_output=True, text=True, env=env, timeout=900)
    return done, out


@pytest.mark.parametrize("segments", CASES)
def test_a_draft_renders_over_this_range(project: Path, segments: list[tuple[str, int, int]],
                                         request: pytest.FixtureRequest) -> None:
    done, out = _draft(project, segments, request.node.callspec.id)
    tail = "\n".join((done.stdout + done.stderr).splitlines()[-3:])
    assert done.returncode == 0, f"the draft stopped: {tail}"
    video = render_hybrid.probe(media_bin.ffprobe(), out)
    total = segments[-1][2]
    assert (video["width"], video["height"], video["fps"]) == (540, 960, 15.0)
    # Whatever rule the engines share, the draft must last as long as the reel to within one draft frame.
    assert abs(video["frames"] / 15 - total / 30) < 1 / 15, (
        f"{video['frames']} draft frames for a {total}-frame reel")
