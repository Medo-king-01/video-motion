"""Contract subset: structural validation, timeline invariants and safe failure."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_check import validate  # noqa: E402

FIXTURE = ROOT / "tests/fixtures/unified_project/basic.json"
TOOL = ROOT / "tools/unified_project_check.py"


def project():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_example_is_valid_and_unmodified():
    p = project()
    before = copy.deepcopy(p)
    assert validate(p) == []
    assert p == before


def test_empty_project_is_valid():
    p = project()
    p.update(duration=0, assets=[], tracks=[])
    assert validate(p) == []


@pytest.mark.parametrize("mutation,code", [
    (lambda p: p.update(schemaVersion="2.0"), "U01"),
    (lambda p: p.update(schemaVersion="1.2"), "U01"),
    (lambda p: p.update(unrecognized=True), "U01"),
    (lambda p: p.update(duration=True), "U01"),
    (lambda p: p["tracks"][0]["clips"][0]["effects"].append({}), "U01"),
    (lambda p: p["tracks"][0]["clips"][0]["keyframes"].append({}), "U01"),
    (lambda p: p["profile"]["fps"].update(num=60, den=2), "U02"),
    (lambda p: p.update(timebase=12345), "U02"),
    (lambda p: p["tracks"][0].update(id="a1"), "U03"),
    (lambda p: p["tracks"][0]["clips"][0].update(assetId="missing"), "U03"),
    (lambda p: p["assets"][0].update(uri="../secret"), "U04"),
    (lambda p: p["assets"][0].update(uri="C:/video.mp4"), "U04"),
    (lambda p: p["assets"][0].update(uri="/root/video.mp4"), "U04"),
    (lambda p: p["assets"][0].update(uri="media\\video.mp4"), "U04"),
    (lambda p: p["tracks"][0]["clips"][0].update(duration=480001), "U05"),
    (lambda p: p["tracks"][0]["clips"][0].update(sourceIn=240001), "U05"),
    (lambda p: p["tracks"][0].update(kind="text"), "U05"),
])
def test_invalid_cases(mutation, code):
    p = project()
    mutation(p)
    assert any(error.startswith(code) for error in validate(p))


def test_half_open_ranges_and_overlap():
    p = project()
    clip = p["tracks"][0]["clips"][0]
    clip["duration"] = 240000
    second = {**clip, "id": "c2", "start": 240000, "sourceIn": 240000}
    p["tracks"][0]["clips"].append(second)
    assert not validate(p)
    second["start"] -= 1
    assert any("overlaps" in e for e in validate(p))


def test_image_and_source_rules():
    p = project()
    a = p["assets"][0]
    a["kind"] = "image"
    del a["duration"]
    assert not validate(p)
    p["tracks"][0]["clips"][0]["sourceIn"] = 1
    assert any("image source" in e for e in validate(p))
    a["duration"] = 1
    assert any(e.startswith("U01") for e in validate(p))


def test_cli_errors_and_no_changes(tmp_path):
    path = tmp_path / "project.json"
    path.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    before = path.read_bytes()
    result = subprocess.run([sys.executable, str(TOOL), str(path)], capture_output=True, text=True)
    assert result.returncode == 0
    assert path.read_bytes() == before
    path.write_text('{"id": 1, "id": 2}', encoding="utf-8")
    assert subprocess.run([sys.executable, str(TOOL), str(path)], capture_output=True).returncode == 2
    path.write_text('{}', encoding="utf-8")
    assert subprocess.run([sys.executable, str(TOOL), str(path)], capture_output=True).returncode == 1
    assert subprocess.run([sys.executable, str(TOOL), str(tmp_path / "missing")], capture_output=True).returncode == 2
