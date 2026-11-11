"""Real hybrid drafts over odd and even frame ranges: P, K, a K alpha overlay, and the assembly.

A draft of a segment [start, end) shows source frames start, start+2, … stopping before
`end // 2 * 2`: `end // 2 - start // 2` frames, all inside the segment. Engine P, engine K as a base
and engine K as an alpha overlay sample that same list (`render_hybrid.draft_samples`).

Before 2026-11-11 the runner and P counted `end // 2 - start // 2` while K was asked for
`--from start/30 --to end/30 --fps 15` and rendered `ceil((end - start) / 2)`: every case in ODD_K
below stopped with "violates render contract … expected … 1 frames" or "overlay 1 produced 2
frame(s), expected 1". They were recorded here as `xfail(strict)` until the rule was chosen.
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
ODD_CONCAT = [  # two odd neighbours joined: [0,3) shows frame 0, [3,6) shows 3 and 5
    ("k-0-3-6", [("k", 0, 3), ("k", 3, 6)]),
    ("p-then-k-0-3-6", [("p", 0, 3), ("k", 3, 6)]),
    ("overlay-then-overlay-0-3-6", [(PK, 0, 3), (PK, 3, 6)]),
]
CASES = [pytest.param(plan, id=name)
         for name, plan in EVEN + ODD_P + ODD_K_THAT_HAPPENS_TO_MATCH + ODD_K + ODD_CONCAT]


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
    assert video["frames"] == total // 2 == sum(render_hybrid.draft_frames(start, end) for _, start, end in segments)
    assert abs(video["frames"] / 15 - total / 30) < 1 / 15, (
        f"{video['frames']} draft frames for a {total}-frame reel")


# --- a segment that starts on an odd frame opens on its own scene ------------------------------

RED, BLUE = (220, 30, 30), (30, 60, 220)
FLASH_DATA = """export const W = 1080, H = 1920, FPS = 30;
export const scenes = [
  { id: 'flash-a', start: 0, end: 0.1 },   // frames 0-2
  { id: 'flash-b', start: 0.1, end: 1 },   // from frame 3: the K scene cut sits on the segment cut
];
export const DURATION = scenes.at(-1).end;
"""


def _flat_scene(rgb: tuple[int, int, int]) -> str:
    return ("export const supportsReducedMotion=true;\n"
            f"export function draw(ctx,t,{{W,H}}){{ctx.fillStyle='rgb({rgb[0]},{rgb[1]},{rgb[2]})';ctx.fillRect(0,0,W,H);}}\n")


@pytest.fixture(scope="module")
def flash_project(project: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    target = tmp_path_factory.mktemp("hybrid-flash") / "reel"
    shutil.copytree(project, target, ignore=shutil.ignore_patterns("cache", "out"))
    (target / "out").mkdir()
    data = (target / "src" / "data.js").read_text(encoding="utf-8")
    tail = data[data.index("export const DURATION"):].split("\n", 1)[1]   # keep the template's other exports
    (target / "src" / "data.js").write_text(FLASH_DATA + tail, encoding="utf-8")
    (target / "src" / "scenes" / "flash-a.js").write_text(_flat_scene(RED), encoding="utf-8")
    (target / "src" / "scenes" / "flash-b.js").write_text(_flat_scene(BLUE), encoding="utf-8")
    return target


def _frames(video: Path) -> list:
    import numpy as np

    raw = subprocess.run([media_bin.ffmpeg(), "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return list(np.frombuffer(raw, dtype=np.uint8).reshape(-1, 960, 540, 3))


def _is(frame, rgb: tuple[int, int, int]) -> bool:
    mean = frame.reshape(-1, 3).mean(axis=0)
    return all(abs(float(mean[i]) - rgb[i]) < 25 for i in range(3))


def _run_dir(done: subprocess.CompletedProcess) -> Path:
    line = next(line for line in done.stdout.splitlines() if "segment diagnostics retained at" in line)
    return Path(line.split("retained at", 1)[1].strip())


def test_a_k_segment_starting_on_an_odd_frame_opens_on_its_own_scene(flash_project: Path) -> None:
    done, out = _draft(flash_project, [("k", 0, 3), ("k", 3, 6)], "flash-base")
    assert done.returncode == 0, (done.stdout + done.stderr)[-600:]
    frames = _frames(out)
    assert len(frames) == 3
    assert _is(frames[0], RED), "draft frame 0 is source frame 0: scene flash-a"
    assert _is(frames[1], BLUE), "the segment [3,6) opened on the scene before it (source frame 2) — a one-frame flash"
    assert _is(frames[2], BLUE)


def test_a_k_overlay_starting_on_an_odd_frame_is_there_from_its_first_frame(flash_project: Path) -> None:
    import numpy as np
    from PIL import Image

    plan = _plan([("p", 0, 3), (PK, 3, 6)])
    plan["segments"][1]["layers"][1]["scenes"] = ["flash-b"]     # --only: the scene that starts at frame 3
    (flash_project / "plan" / "hybrid.json").write_text(json.dumps(plan), encoding="utf-8")
    out = flash_project / "out" / "flash-overlay.mp4"
    env = dict(os.environ, PATH=f"{TOOLS / 'bin'}{os.pathsep}{os.environ.get('PATH', '')}")
    done = subprocess.run([sys.executable, str(TOOLS / "render_hybrid.py"), "--project", str(flash_project), "--draft",
                           "--out", str(out)], capture_output=True, text=True, env=env, timeout=900)
    assert done.returncode == 0, (done.stdout + done.stderr)[-600:]
    overlay = sorted((_run_dir(done) / "s1-overlay1").glob("*.png"))
    assert len(overlay) == 2
    for index, path in enumerate(overlay):
        pixels = np.asarray(Image.open(path).convert("RGBA"))
        assert int(pixels[..., 3].max()) > 0, f"overlay frame {index} is fully transparent — the layer vanished"
        assert _is(pixels[..., :3], BLUE), f"overlay frame {index} is not scene flash-b"
    frames = _frames(out)
    assert len(frames) == 3 and _is(frames[1], BLUE) and _is(frames[2], BLUE), "the overlay must cover the P base"
