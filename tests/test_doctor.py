"""`make doctor` must not stop at DEGRADED: every non-OK capability carries the command that fixes it."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import doctor  # noqa: E402

ANSI = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    """The report uses colour; assertions care about the words."""
    return ANSI.sub("", text)


def mixed() -> list[doctor.Finding]:
    return [
        doctor.Finding("ffmpeg", doctor.OK, "7.1 · libx264 yes"),
        doctor.Finding("node", doctor.DEGRADED, "18.0 — too old", "nvm install 20"),
        doctor.Finding("Chromium (engines K/R)", doctor.BLOCKED, "not installed",
                       "npm ci --prefix tools/toolkit"),
        doctor.Finding("drawtext filter", "WARN", "optional", "sudo apt-get install -y ffmpeg   # freetype"),
        doctor.Finding("ffprobe", doctor.BLOCKED, "missing", "npm ci --prefix tools/toolkit"),
        doctor.Finding("brand lock", doctor.OK, "brand.json"),
    ]


def test_render_prints_fix_lines_only_for_problems() -> None:
    text = plain(doctor.render(mixed(), "harfbuzz"))
    assert "fix: nvm install 20" in text
    assert "fix: npm ci --prefix tools/toolkit" in text
    assert "git restore" not in text
    assert "Suggested fixes" in text
    # deduplicated: two missing capabilities share one command, numbered once
    block = text.split("Suggested fixes", 1)[1]
    assert block.count("npm ci --prefix tools/toolkit") == 1
    assert "  1. nvm install 20" in block


def test_ok_rows_do_not_leak_into_suggested_fixes() -> None:
    fixes = doctor.suggested_fixes(mixed())
    assert fixes == [
        "nvm install 20",
        "npm ci --prefix tools/toolkit",
        "sudo apt-get install -y ffmpeg   # freetype",
    ]


def test_envelope_carries_the_fix_per_finding_and_in_bulk() -> None:
    payload = doctor.envelope(mixed(), "harfbuzz")
    assert payload["fixes"][0] == "nvm install 20"
    by_name = {row["capability"]: row for row in payload["findings"]}
    assert by_name["node"]["fix"] == "nvm install 20"
    assert by_name["brand lock"]["fix"] == ""
    json.dumps(payload)  # an agent consumes this; it must stay serialisable


def test_fix_mode_prints_commands_only(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(doctor, "collect", lambda fast=False: (mixed(), "harfbuzz"))
    code = doctor.main(["--fast", "--fix"])
    lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert lines == doctor.suggested_fixes(mixed())
    assert code == 1  # BLOCKED capabilities still exit non-zero, as the report does


def test_fix_mode_on_a_healthy_machine_is_silent(monkeypatch: pytest.MonkeyPatch,
                                                 capsys: pytest.CaptureFixture[str]) -> None:
    healthy = [doctor.Finding("ffmpeg", doctor.OK, "7.1"), doctor.Finding("node", doctor.OK, "22.1")]
    monkeypatch.setattr(doctor, "collect", lambda fast=False: (healthy, "harfbuzz"))
    assert doctor.main(["--fast", "--fix"]) == 0
    assert capsys.readouterr().out.strip() == ""


def test_every_blocking_check_knows_its_repair() -> None:
    """A capability that can be BLOCKED must offer a command; otherwise the report is a dead end."""
    findings, _ = doctor.collect(fast=True)
    for finding in findings:
        if finding.state in doctor.BLOCKING_STATES:
            assert finding.fix, f"{finding.capability} has no suggested fix"
