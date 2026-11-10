"""Engine R renders a *range* — the claim "R has no range API" was wrong (N3).

`tools/render_scenes.py` and `pipeline.py` told anyone who asked that R/Remotion cannot render a
partial timeline, and `--scene-cache` rejected the engine on that basis. Meanwhile
`render_hybrid.py` had been rendering R segments with `scripts/render.mjs --from-frame --to-frame`
all along, and `render.mjs` validates that range against the locked 30 fps timeline before it opens
a browser.

These tests pin the capability itself: an empty range and an out-of-timeline range are refused with
sentences, and a *valid* range gets past range validation into the next gate (text direction) without
rendering anything — which is the proof that the flags are parsed and honoured. No Chromium, no
`npm ci`: every assertion here happens before a frame is drawn.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NEW_PROJECT = ROOT / "tools" / "new_project.py"


def make_r_project(tmp_path: Path) -> Path:
    if shutil.which("node") is None:
        pytest.skip("node is required for the Remotion scaffold")
    project = tmp_path / "r_range"
    subprocess.run([sys.executable, str(NEW_PROJECT), "r_range", "--engine", "r", "--out", str(project)],
                   check=True, capture_output=True)
    # A measured 2.0 s timeline at the locked 30 fps: ranges are validated against this.
    (project / "plan" / "beats.json").write_text(json.dumps({
        "duration": 2.0, "fps": 30, "frames": 60, "bounds": [0, 2.0],
        "scenes": [{"index": 1, "start": 0, "end": 2.0, "dur": 2.0, "frames": 60}],
    }), encoding="utf-8")
    return project


def render_r(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["node", "scripts/render.mjs", *args], cwd=str(project),
                          capture_output=True, text=True, timeout=180)


def test_an_empty_range_is_refused(tmp_path):
    project = make_r_project(tmp_path)
    result = render_r(project, "--from-frame", "60", "--to-frame", "60")
    assert result.returncode == 2
    assert "non-empty, half-open integer range" in result.stderr + result.stdout


def test_a_range_beyond_the_measured_timeline_is_refused(tmp_path):
    project = make_r_project(tmp_path)
    result = render_r(project, "--from-frame", "0", "--to-frame", "9999")
    assert result.returncode == 2
    assert "exceeds the approved timeline" in result.stderr + result.stdout


def test_a_valid_range_is_accepted_and_reaches_the_next_gate(tmp_path):
    """Proof the flags are honoured: the range passes, then text-direction stops the render."""
    project = make_r_project(tmp_path)
    result = render_r(project, "--from-frame", "0", "--to-frame", "1", "--silent")
    output = result.stderr + result.stdout
    assert result.returncode == 2
    assert "text-direction" in output, output
    assert "half-open integer range" not in output and "exceeds the approved timeline" not in output
    # Nothing was drawn: the refusal happens before Chromium is launched.
    assert not (project / "out" / "remotion.mp4").exists()


def test_the_hybrid_renderer_uses_that_range_api():
    source = (ROOT / "tools" / "render_hybrid.py").read_text(encoding="utf-8")
    assert "--from-frame" in source and "scripts/render.mjs" in source
