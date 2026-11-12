"""B6 subtitles: one cue list, two formats, and the same bytes on every run.

The source is the reel's own `plan/copy.json`, so what is on screen and what is in the SRT cannot drift.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import subtitles  # noqa: E402

COPY = ROOT / "tests" / "fixtures" / "reel" / "good" / "plan" / "copy.json"


def payload() -> dict:
    return json.loads(COPY.read_text(encoding="utf-8"))


def two_cues(start: float = 0.0, gap: float = 0.4) -> dict:
    return {"copy": [
        {"id": "a", "text": "النهاردة", "start": start, "end": start + 1.0},
        {"id": "b", "text": "سؤال واحد", "start": start + 1.0 + gap, "end": start + 2.0 + gap},
    ]}


# ---------------------------------------------------------------- build
def test_the_fixture_becomes_ordered_cues() -> None:
    cues = subtitles.build_cues(payload())
    assert len(cues) == 11
    assert cues == sorted(cues, key=lambda c: c["start"])
    assert all(c["end"] > c["start"] for c in cues)
    assert cues[0]["lines"] == ["النهاردة"]


def test_every_cue_respects_the_reading_rules() -> None:
    cues = subtitles.build_cues(payload(), min_duration=0.6, max_chars=42, max_lines=2)
    for cue in cues:
        assert cue["end"] - cue["start"] >= 0.6 - 1e-9, cue
        assert len(cue["lines"]) <= 2
        assert all(len(line) <= 42 for line in cue["lines"])


def test_a_short_cue_is_extended_when_there_is_room() -> None:
    cues = subtitles.build_cues({"copy": [{"id": "a", "text": "قصير", "start": 0, "end": 0.2}]}, min_duration=0.8)
    assert cues[0]["end"] == pytest.approx(0.8)


def test_a_short_cue_with_no_room_is_refused() -> None:
    data = {"copy": [{"id": "a", "text": "قصير", "start": 0, "end": 0.2},
                     {"id": "b", "text": "بعده", "start": 0.25, "end": 2.0}]}
    with pytest.raises(subtitles.SubtitleError) as excinfo:
        subtitles.build_cues(data, min_duration=0.6)
    assert excinfo.value.code == "S03"


def test_overlaps_are_rejected_by_default() -> None:
    data = {"copy": [{"id": "a", "text": "أول", "start": 0, "end": 2.0},
                     {"id": "b", "text": "تاني", "start": 1.0, "end": 3.0}]}
    with pytest.raises(subtitles.SubtitleError) as excinfo:
        subtitles.build_cues(data)
    assert excinfo.value.code == "S02"


def test_overlaps_can_be_merged_explicitly() -> None:
    data = {"copy": [{"id": "a", "text": "أول", "start": 0, "end": 2.0},
                     {"id": "b", "text": "تاني", "start": 1.0, "end": 3.0}]}
    cues = subtitles.build_cues(data, on_overlap="merge")
    assert len(cues) == 1
    assert cues[0]["lines"] == ["أول تاني"]
    assert cues[0]["end"] == pytest.approx(3.0)


@pytest.mark.parametrize(("data", "code"), [
    ({"copy": []}, "S01"),
    ({"copy": [{"id": "a", "text": "  ", "start": 0, "end": 1}]}, "S04"),
    ({"copy": [{"id": "a", "text": "نص", "start": -1, "end": 1}]}, "S03"),
    ({"copy": [{"id": "a", "text": "نص", "start": 2, "end": 2}]}, "S03"),
    ({"copy": [{"id": "a", "text": "كلمةطويلةجداًبزيادةكبيرةجدا", "start": 0, "end": 3}]}, "S04"),
])
def test_broken_copy_is_refused(data, code: str) -> None:
    with pytest.raises(subtitles.SubtitleError) as excinfo:
        subtitles.build_cues(data, max_chars=20)
    assert excinfo.value.code == code


def test_text_needing_three_lines_is_refused() -> None:
    data = {"copy": [{"id": "a", "text": " ".join(["كلمة"] * 12), "start": 0, "end": 4}]}
    with pytest.raises(subtitles.SubtitleError, match="S04"):
        subtitles.build_cues(data, max_chars=20, max_lines=2)


def test_settings_are_validated() -> None:
    with pytest.raises(subtitles.SubtitleError, match="S06"):
        subtitles.build_cues(two_cues(), on_overlap="ignore")
    with pytest.raises(subtitles.SubtitleError, match="S06"):
        subtitles.build_cues(two_cues(), min_duration=0)
    with pytest.raises(subtitles.SubtitleError, match="S06"):
        subtitles.build_cues(two_cues(), max_lines=9)


def test_whitespace_and_control_characters_are_cleaned() -> None:
    cues = subtitles.build_cues({"copy": [{"id": "a", "text": "  نص\nواحد\x07  ", "start": 0, "end": 1}]})
    assert cues[0]["lines"] == ["نص واحد"]


# ---------------------------------------------------------------- formats
def test_srt_shape() -> None:
    text = subtitles.to_srt(subtitles.build_cues(payload()))
    blocks = text.strip().split("\n\n")
    assert blocks[0].startswith("1\n00:00:00,000 --> 00:00:01,500")
    assert "," in blocks[0].splitlines()[1]
    assert "[WEBVTT]" not in text
    assert blocks[-1].splitlines()[0] == str(len(blocks))


def test_vtt_shape() -> None:
    text = subtitles.to_vtt(subtitles.build_cues(payload()))
    assert text.startswith("WEBVTT\n")
    assert "00:00:00.000 --> 00:00:01.500" in text
    assert "\n1\n" not in text


def test_vtt_escapes_markup() -> None:
    cues = [{"id": "a", "start": 0.0, "end": 1.0, "lines": ["5 < 6 & 7 > 3"]}]
    text = subtitles.to_vtt(cues)
    assert "5 &lt; 6 &amp; 7 &gt; 3" in text
    assert "5 < 6" not in text


def test_timestamps_round_trip() -> None:
    assert subtitles._timestamp(0, ",") == "00:00:00,000"
    assert subtitles._timestamp(3661.239, ",") == "01:01:01,239"
    assert subtitles._timestamp(1.2346, ".") == "00:00:01.235"


# ---------------------------------------------------------------- manifest contract
def manifest() -> dict:
    settings = dict(subtitles.DEFAULTS)
    return subtitles.manifest(subtitles.build_cues(payload()), COPY, settings)


def test_a_fresh_manifest_is_valid() -> None:
    data = manifest()
    assert subtitles.validate_manifest(data) == []
    assert data["totals"]["cues"] == 11
    assert data["source"]["sha256"] == subtitles.hashlib.sha256(COPY.read_bytes()).hexdigest()


@pytest.mark.parametrize(("edit", "code"), [
    (lambda d: d.update(version=2), "S01"),
    (lambda d: d["totals"].update(cues=99), "S05"),
    (lambda d: d["cues"][1].update(id=d["cues"][0]["id"]), "S02"),
    (lambda d: d["cues"][1].update(start=0.0), "S02"),
    (lambda d: d["cues"][0].update(end=d["cues"][0]["start"] + 0.1), "S03"),
    (lambda d: d["cues"][0].update(lines=["x" * 60]), "S04"),
    (lambda d: d["settings"].update(minDuration=0), "S06"),
])
def test_broken_manifests_are_refused(edit, code: str) -> None:
    data = manifest()
    edit(data)
    errors = subtitles.validate_manifest(data)
    assert any(error.startswith(code) for error in errors), errors


# ---------------------------------------------------------------- CLI
def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / "subtitles.py"), *args],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=60)


def test_cli_builds_both_formats_and_the_manifest(tmp_path: Path) -> None:
    srt, vtt, man = tmp_path / "ar.srt", tmp_path / "ar.vtt", tmp_path / "ar.json"
    result = run("build", str(COPY), "--srt", str(srt), "--vtt", str(vtt), "--manifest", str(man))
    assert result.returncode == 0, result.stderr
    assert srt.read_text(encoding="utf-8").startswith("1\n")
    assert vtt.read_text(encoding="utf-8").startswith("WEBVTT")
    checked = run("check", str(man))
    assert checked.returncode == 0, checked.stderr
    assert "11 cues" in checked.stdout


def test_cli_output_is_byte_identical(tmp_path: Path) -> None:
    first = tmp_path / "a"
    second = tmp_path / "b"
    for folder in (first, second):
        folder.mkdir()
        run("build", str(COPY), "--srt", str(folder / "x.srt"), "--vtt", str(folder / "x.vtt"),
            "--manifest", str(folder / "x.json"))
    assert (first / "x.srt").read_bytes() == (second / "x.srt").read_bytes()
    assert (first / "x.vtt").read_bytes() == (second / "x.vtt").read_bytes()
    assert (first / "x.json").read_bytes() == (second / "x.json").read_bytes()


def test_cli_refuses_an_overlap(tmp_path: Path) -> None:
    bad = tmp_path / "copy.json"
    bad.write_text(json.dumps({"copy": [
        {"id": "a", "text": "أول", "start": 0, "end": 2},
        {"id": "b", "text": "تاني", "start": 1, "end": 3}]}), encoding="utf-8")
    result = run("build", str(bad), "--srt", str(tmp_path / "x.srt"), "--vtt", str(tmp_path / "x.vtt"))
    assert result.returncode == 1
    assert "S02" in result.stderr


def test_cli_reports_a_missing_file(tmp_path: Path) -> None:
    result = run("check", str(tmp_path / "gone.json"))
    assert result.returncode == 2
