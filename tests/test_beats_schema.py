"""plan/beats.json is the single timing source of every reel — these tests pin its contract.

`medo-motion/schema/beats.schema.json` documents the shape (draft 2020-12, for editors and external
tooling); `tools/beats_check.py` is the stdlib-only checker for the same contract plus the
cross-field invariants a JSON Schema cannot express (bounds ↔ scenes ↔ duration, frames
arithmetic, index sequence, event containment). This file holds both in lockstep: every real
fixture in the repo passes, every tamper fails with the expected code, and the two artefacts
cannot drift apart silently. The reel length is the measured VO length — nothing here or there
prescribes one.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "beats_check.py"
SCHEMA = ROOT / "medo-motion" / "schema" / "beats.schema.json"
GOOD = ROOT / "tests" / "fixtures" / "reel" / "good" / "plan" / "beats.json"
BAD_CRAFT = ROOT / "tests" / "fixtures" / "reel" / "bad" / "plan" / "beats.json"
ONE_TAKE = ROOT / "medo-motion" / "examples" / "one-take" / "plan" / "beats.json"
SLIDE_WALL = ROOT / "medo-motion" / "examples" / "slide-wall" / "plan" / "beats.json"
SR = 24000


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True)


def good() -> dict:
    return json.loads(GOOD.read_text(encoding="utf-8"))


def codes(out: str) -> set[str]:
    return {line.split()[1] for line in out.splitlines() if line.startswith("!! B")}


def check(tmp_path: Path, beats: dict) -> subprocess.CompletedProcess:
    path = tmp_path / "beats.json"
    path.write_text(json.dumps(beats), encoding="utf-8")
    return run(str(path))


def mutate(**kw):
    beats = good()
    for key, value in kw.items():
        if value is ...:
            beats.pop(key, None)
        else:
            beats[key] = value
    return beats


# ---- the real files in the repo are valid -----------------------------------------------------

@pytest.mark.parametrize("path", [GOOD, BAD_CRAFT, ONE_TAKE, SLIDE_WALL], ids=lambda p: p.parts[-3])
def test_repo_fixtures_pass(path):
    r = run(str(path))
    assert r.returncode == 0, r.stdout
    assert "length = the VO" in r.stdout


def test_bad_fixture_is_craft_bad_not_schema_bad():
    """bad/ puts the craft tells back in (empty events, drifting cut) — structure stays legal."""
    beats = json.loads(BAD_CRAFT.read_text(encoding="utf-8"))
    assert beats["scenes"], "the bad fixture still has scenes"
    assert all(isinstance(s["events"], list) for s in beats["scenes"])


def test_checker_accepts_a_project_directory():
    r = run(str(GOOD.parents[1]))
    assert r.returncode == 0, r.stdout


def test_draft_scaffold_is_legal():
    r = run("/dev/stdin") if False else None  # placeholder, replaced below
    beats = {"duration": None, "scenes": [], "note": "fill it from the VO"}
    assert beats["duration"] is None
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(beats, fh)
        tmp = fh.name
    r = run(tmp)
    assert r.returncode == 0, r.stdout
    assert "draft" in r.stdout


def test_vo_measurement_round_trips_through_the_checker(tmp_path):
    """The writer's own output must satisfy the checker — otherwise the gates disagree."""
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffmpeg, ffprobe  # noqa: PLC0415

    if ffmpeg() is None or ffprobe() is None:
        pytest.skip("ffmpeg/ffprobe unavailable — the VO round-trip needs them (tools/setup.sh)")
    vo = tmp_path / "vo.wav"
    spans = [0.8, 0.4, 1.2, 0.3, 0.9]   # 3.6 s, two cuts
    parts = []
    for i, dur in enumerate(spans):
        n = int(dur * SR)
        if i % 2 == 0:
            t = np.arange(n) / SR
            parts.append((0.3 * np.sin(2 * np.pi * 180.0 * t) * 32767).astype(np.int16))
        else:
            parts.append(np.zeros(n, np.int16))
    import wave
    with wave.open(str(vo), "wb") as fh:
        fh.setnchannels(1)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        fh.writeframes(np.concatenate(parts).tobytes())
    beats = tmp_path / "beats.json"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "vo_length.py"), str(vo), "--json", str(beats)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    r = run(str(beats))
    assert r.returncode == 0, r.stdout


# ---- the negative matrix: one tampered field, one expected code --------------------------------

CASES = [
    ("missing_duration", mutate(duration=...), "B01"),
    ("duration_wrong_type", mutate(duration="soon"), "B01"),
    ("unknown_top_key", mutate(palette="red"), "B01"),
    ("fps_out_of_range", mutate(fps=400), "B01"),
    ("frames_float", mutate(frames=720.0), "B01"),
    ("bounds_not_array", mutate(bounds="0-24"), "B01"),
    ("scenes_not_array", mutate(scenes={}), "B01"),
    ("missing_bounds", mutate(bounds=...), "B02"),
    ("missing_scenes", mutate(scenes=...), "B01"),
    ("frames_arithmetic", mutate(frames=719), "B03"),
    ("bounds_start_not_zero", mutate(bounds=[1.0, *good()["bounds"][1:]]), "B04"),
    ("bounds_not_monotone", mutate(bounds=[0, 6.0, 3.0, *good()["bounds"][3:]]), "B04"),
    ("bounds_length", mutate(bounds=[0, 24.0]), "B04"),
    ("index_not_sequential", None, "B05"),
    ("scene_overlap", None, "B05"),
    ("gap_between_scenes", None, "B05"),
    ("last_end_mismatch", None, "B05"),
    ("dur_mismatch", None, "B06"),
    ("scene_frames_mismatch", None, "B06"),
    ("event_outside_scene", None, "B06"),
    ("duplicate_scene_id", None, "B07"),
    ("theme_invalid", None, "B01"),
    ("scene_unknown_key", None, "B01"),
]


def _apply(beats: dict, case: str) -> dict:
    if case == "index_not_sequential":
        beats["scenes"][1]["index"] = 3
        return beats
    if case == "scene_overlap":
        beats["scenes"][1]["start"] = beats["scenes"][0]["end"] - 0.5
        return beats
    if case == "gap_between_scenes":
        beats["scenes"][1]["start"] = beats["scenes"][0]["end"] + 0.5
        beats["scenes"][1]["dur"] = round(beats["scenes"][1]["end"] - beats["scenes"][1]["start"], 3)
        return beats
    if case == "last_end_mismatch":
        beats["scenes"][-1]["end"] = beats["duration"] - 2.0
        beats["scenes"][-1]["dur"] = round(beats["scenes"][-1]["end"] - beats["scenes"][-1]["start"], 3)
        return beats
    if case == "dur_mismatch":
        beats["scenes"][0]["dur"] = round(beats["scenes"][0]["dur"] + 0.5, 3)
        return beats
    if case == "scene_frames_mismatch":
        beats["scenes"][0]["frames"] += 7
        return beats
    if case == "event_outside_scene":
        beats["scenes"][0]["events"] = [{"t": beats["scenes"][0]["end"] + 1.0, "what": "too late"}]
        return beats
    if case == "duplicate_scene_id":
        beats["scenes"][0]["id"] = "same"
        beats["scenes"][1]["id"] = "same"
        return beats
    if case == "theme_invalid":
        beats["scenes"][0]["theme"] = "purple"
        return beats
    if case == "scene_unknown_key":
        beats["scenes"][0]["shadow"] = "soft"
        return beats
    raise AssertionError(f"unhandled case {case}")


@pytest.mark.parametrize("case,beats,expected", [(c, b, e) for c, b, e in CASES],
                         ids=[c for c, _, _ in CASES])
def test_tampered_plan_fails_with_the_expected_code(tmp_path, case, beats, expected):
    if beats is None:
        beats = _apply(good(), case)
    r = check(tmp_path, beats)
    assert r.returncode == 1, f"{case}: expected failure\n{r.stdout}"
    assert expected in codes(r.stdout), f"{case}: want {expected} in:\n{r.stdout}"


def test_gap_failure_reports_the_scene_number(tmp_path):
    beats = _apply(good(), "gap_between_scenes")
    r = check(tmp_path, beats)
    assert "scene 2" in r.stdout


def test_draft_with_scenes_fails(tmp_path):
    r = check(tmp_path, {"duration": None, "scenes": [{"index": 1, "start": 0, "end": 1, "theme": "dark"}]})
    assert r.returncode == 1
    assert "B02" in codes(r.stdout)


def test_unreadable_file_and_bad_json(tmp_path):
    assert run(str(tmp_path / "missing.json")).returncode == 2
    path = tmp_path / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    assert run(str(path)).returncode == 2


def test_measured_file_without_duration_fails(tmp_path):
    beats = good()
    del beats["duration"]
    r = check(tmp_path, beats)
    assert r.returncode == 1
    assert "B01" in codes(r.stdout)


# ---- schema ↔ checker lockstep -----------------------------------------------------------------

def test_schema_documents_the_same_contract():
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert "2020-12" in schema["$schema"]
    assert schema["type"] == "object"
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"duration", "scenes"}
    assert schema["properties"]["fps"]["exclusiveMinimum"] == 0
    assert schema["properties"]["fps"]["maximum"] == 240
    titles = {branch.get("title") for branch in schema["anyOf"]}
    assert titles == {"draft", "measured"}
    scene = schema["$defs"]["scene"]
    assert scene["additionalProperties"] is False
    assert schema["$defs"]["event"]["additionalProperties"] is False
    assert scene["properties"]["theme"]["enum"] == ["dark", "light"]
    assert scene["properties"]["index"]["minimum"] == 1
    # the checker's top-level key set is exactly the schema's property set
    assert set(schema["properties"]) == {"duration", "fps", "frames", "bounds", "audio", "note", "scenes"}
    assert set(scene["properties"]) == {"index", "id", "start", "end", "dur", "frames", "theme", "ui", "events"}


def test_schema_has_no_palette_or_color_anywhere():
    """beats.json carries timing, never art direction — no color keys, no hex strings."""
    raw = SCHEMA.read_text(encoding="utf-8")
    for banned in ("palette", "#CB", "#0A0A0A", "colors", "colour"):
        assert banned not in raw, banned


def test_checker_source_enforces_the_same_theme_enum():
    source = TOOL.read_text(encoding="utf-8")
    assert 'THEMES = {"dark", "light"}' in source
    assert "START_TOL = 0.05" in source and "DURATION_TOL = 0.15" in source
