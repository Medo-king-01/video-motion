"""Machine Explainer X01-X03: source locators, word timings and polygon-mask occlusion.

The spec-validation half of the Machine Explainer suite. Everything here is decided in-process or by
shelling out to the CLI - no browser. P/K/R parity, the dynamic safe zone and the archetype renders
live in `test_machine_explainer_parity.py`; the Remotion renders in
`test_machine_explainer_remotion.py`; sample specs in `machine_explainer_support.py`.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from machine_explainer_support import (
    ENGINE_P,
    ROOT,
    SKILL,
    TOOLS,
    _sample_nvme_vo_spec,
    _write_project_fixture,
)

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


def test_k_and_r_machine_kit_byte_identical_and_locked_palette():
    k_path = SKILL / "templates" / "render" / "lib" / "machine-kit.js"
    r_path = SKILL / "templates" / "remotion" / "src" / "lib" / "machine-kit.js"
    assert k_path.read_bytes() == r_path.read_bytes(), "K and R machine-kit.js must stay byte-identical"

    brand = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed = {v["hex"].upper() for v in brand["palette"].values() if isinstance(v, dict) and "hex" in v}
    allowed |= {v["hex"].upper() for v in brand.get("derived", {}).values() if isinstance(v, dict) and "hex" in v}

    for path in (k_path, ENGINE_P / "machine_kit.py"):
        found = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8"))}
        assert found <= allowed, f"{path.name} introduces off-brand colours: {found - allowed}"


def test_x01_verifiable_source_locator_and_illustrative_guards(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415

    # Clean project passes X01–X04
    spec = _sample_nvme_vo_spec()
    _write_project_fixture(tmp_path, spec)
    report = me.check_project(tmp_path)
    assert report["ok"], report["errors"]

    # Bare quote WITHOUT locator must fail X01
    bad_no_locator = _sample_nvme_vo_spec()
    del bad_no_locator["steps"][0]["locator"]
    _write_project_fixture(tmp_path, bad_no_locator)
    res1 = me.check_project(tmp_path)
    assert not res1["ok"]
    assert any(code == "X01" and "locator" in msg for code, msg in res1["errors"])

    # Illustrative step asserting unverified hardware spec numbers ("7400 MB/s") must fail X01
    bad_illus = _sample_nvme_vo_spec()
    bad_illus["steps"][0] = {
        "id": "step-pcie",
        "evidence": "illustrative",
        "illustrativeLabelId": "nvme-illus-tag",
        "copyIds": ["nvme-step-1", "nvme-illus-tag"],
        "timing": "sync",
        "anchor": {"word": 1, "text": "الكنترولر"},
        "start": 4.3,
        "end": 6.0,
        "activeTags": ["controller"],
        "motion": {"kind": "pulse", "tint": "active"},
    }
    _write_project_fixture(tmp_path, bad_illus)
    copy_p = tmp_path / "plan" / "copy.json"
    copy_doc = json.loads(copy_p.read_text(encoding="utf-8"))
    copy_doc["copy"][1]["text"] = "سرعة قراءة 7400 MB/s"
    copy_p.write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    res2 = me.check_project(tmp_path)
    assert not res2["ok"]
    assert any(code == "X01" and "hardware spec numbers" in msg for code, msg in res2["errors"])


def test_x02_unified_word_timings_and_explicit_reveal_window_units(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    # Ambiguous array revealWindow [3.0, 4.2] must be rejected
    bad_rw = _sample_nvme_vo_spec()
    bad_rw["revealWindow"] = [3.0, 4.2]
    _write_project_fixture(tmp_path, bad_rw)
    r_rw = me.check_project(tmp_path)
    assert not r_rw["ok"]
    assert any(code == "X02" and "revealWindow" in msg for code, msg in r_rw["errors"])

    # Sync step drifting from measured word.start (4.30 -> 4.45) must fail X02
    bad_sync = _sample_nvme_vo_spec()
    bad_sync["steps"][0]["start"] = 4.45
    _write_project_fixture(tmp_path, bad_sync)
    r_sync = me.check_project(tmp_path)
    assert not r_sync["ok"]
    assert any(code == "X02" and "sync must start" in msg for code, msg in r_sync["errors"])

    # Converting VO spec -> scene-local updates clock="scene" and revealWindow.unit="scene_seconds"
    local = mk.to_scene_local_machine(_sample_nvme_vo_spec(), scene_start=3.0)
    assert local["clock"] == "scene"
    assert local["revealWindow"] == {"unit": "scene_seconds", "start": 0.0, "end": 1.2}
    assert local["steps"][0]["start"] == 1.3


def test_x02_mandatory_measured_words_rejects_missing_scene_empty_words_and_bad_anchor(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415

    # 1. Target scene (scene 2) completely missing from plan/word-timings.json -> must fail X02
    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    wt_path = tmp_path / "plan" / "word-timings.json"
    wt_missing_scene = {
        "clock": "vo",
        "scenes": [
            {"scene": 1, "words": [{"text": "إزاي", "start": 0.1, "end": 0.5}]},
            {"scene": 3, "words": [{"text": "خلاص", "start": 8.2, "end": 8.7}]},
        ],
    }
    wt_path.write_text(json.dumps(wt_missing_scene, ensure_ascii=False), encoding="utf-8")
    r_missing = me.check_project(tmp_path)
    assert not r_missing["ok"]
    assert any(code == "X02" and "scene 2 is missing" in msg for code, msg in r_missing["errors"])
    assert any(code == "X02" and "no measured words available" in msg for code, msg in r_missing["errors"])

    # 2. Target scene present in plan/word-timings.json but with an empty words list [] -> must fail X02
    wt_empty_words = {
        "clock": "vo",
        "scenes": [
            {"scene": 1, "words": [{"text": "إزاي", "start": 0.1, "end": 0.5}]},
            {"scene": 2, "words": []},
        ],
    }
    wt_path.write_text(json.dumps(wt_empty_words, ensure_ascii=False), encoding="utf-8")
    r_empty = me.check_project(tmp_path)
    assert not r_empty["ok"]
    assert any(code == "X02" and "empty measured word list" in msg for code, msg in r_empty["errors"])
    assert any(code == "X02" and "no measured words available" in msg for code, msg in r_empty["errors"])

    # 3. Anchor word index out of range -> must fail X02
    bad_idx_spec = _sample_nvme_vo_spec()
    bad_idx_spec["steps"][0]["anchor"] = {"word": 99, "text": "الكنترولر"}
    _write_project_fixture(tmp_path, bad_idx_spec)
    r_range = me.check_project(tmp_path)
    assert not r_range["ok"]
    assert any(code == "X02" and "out of range for scene 2" in msg for code, msg in r_range["errors"])

    # 4. Anchor text mismatch against measured word -> must fail X02
    bad_txt_spec = _sample_nvme_vo_spec()
    bad_txt_spec["steps"][1]["anchor"] = {"word": 2, "text": "كلمة_مختلفة"}
    _write_project_fixture(tmp_path, bad_txt_spec)
    r_txt = me.check_project(tmp_path)
    assert not r_txt["ok"]
    assert any(code == "X02" and "!= measured word" in msg for code, msg in r_txt["errors"])


def test_x02_rejects_nan_infinity_non_numeric_bool_and_inverted_bounds_across_start_and_end(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415

    def assert_x02_failure(report: dict, context: str) -> None:
        assert report["ok"] is False, f"Expected X02 failure for {context}, got ok=True"
        if "errors" in report:
            assert any(code == "X02" for code, _ in report["errors"]), (context, report["errors"])
            for m in report.get("machines", []):
                assert any(
                    f["level"] == "error" and f["code"] == "X02" for f in m.get("findings", [])
                ), (context, m)
        else:
            assert any(
                f["level"] == "error" and f["code"] == "X02" for f in report.get("findings", [])
            ), (context, report)

    invalid_scalars = [
        ("NaN", float("nan")),
        ("Infinity", float("inf")),
        ("-Infinity", float("-inf")),
        ("str", "4.3"),
        ("None", None),
        ("list", [4.3]),
        ("True", True),
        ("False", False),
    ]

    # 1. Measured word `start` and `end` in `plan/word-timings.json` (must work WITHOUT `plan/visual-direction.json`)
    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    assert not (tmp_path / "plan" / "visual-direction.json").exists()
    wt_path = tmp_path / "plan" / "word-timings.json"
    base_wt = json.loads(wt_path.read_text(encoding="utf-8"))

    for field in ("start", "end"):
        for label, bad_val in invalid_scalars:
            wt_doc = json.loads(json.dumps(base_wt))
            wt_doc["scenes"][1]["words"][1][field] = bad_val
            # `json.dumps(..., allow_nan=True)` writes literal NaN / Infinity / -Infinity on disk!
            wt_path.write_text(json.dumps(wt_doc, ensure_ascii=False, allow_nan=True), encoding="utf-8")
            assert not (tmp_path / "plan" / "visual-direction.json").exists()
            assert_x02_failure(me.check_project(tmp_path), f"word-timings.{field}={label}")

    # Empty (`end == start`) and inverted (`end < start`) measured word intervals in `word-timings.json`
    for bad_s, bad_e, desc in ((4.3, 4.3, "equal"), (4.95, 4.3, "inverted")):
        wt_doc = json.loads(json.dumps(base_wt))
        wt_doc["scenes"][1]["words"][1]["start"] = bad_s
        wt_doc["scenes"][1]["words"][1]["end"] = bad_e
        wt_path.write_text(json.dumps(wt_doc, ensure_ascii=False), encoding="utf-8")
        assert_x02_failure(me.check_project(tmp_path), f"word-timings interval {desc}")

    # Also verify `caption_align` list-format `word-timings.json` rejects bool/NaN/Infinity/end<=start
    for label, bad_scene_start, bad_w_start, bad_w_end in (
        ("scene_start_bool", True, 1.3, 1.95),
        ("scene_start_nan", float("nan"), 1.3, 1.95),
        ("word_start_bool", 3.0, True, 1.95),
        ("word_end_inf", 3.0, 1.3, float("inf")),
        ("word_inverted", 3.0, 1.95, 1.3),
    ):
        local_wt = [
            {"index": 1, "start": 0.0, "final": [{"text": "ليه", "start": 0.4, "end": 0.9}]},
            {
                "index": 2,
                "start": bad_scene_start,
                "final": [
                    {"text": "بيدخل", "start": 0.8, "end": 1.25},
                    {"text": "الكنترولر", "start": bad_w_start, "end": bad_w_end},
                    {"text": "ويوزع", "start": 2.3, "end": 2.9},
                    {"text": "طبقات", "start": 3.05, "end": 3.65},
                ],
            },
        ]
        wt_path.write_text(json.dumps(local_wt, ensure_ascii=False, allow_nan=True), encoding="utf-8")
        assert_x02_failure(me.check_project(tmp_path), f"caption_align list {label}")

    # Restore valid `word-timings.json` before testing `beats.json` and machine spec bounds
    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())

    # 2. Scene `start` and `end` in `plan/beats.json` (including literal NaN / ±Infinity on disk)
    beats_path = tmp_path / "plan" / "beats.json"
    base_beats = json.loads(beats_path.read_text(encoding="utf-8"))
    for field in ("start", "end"):
        for label, bad_val in invalid_scalars:
            b_doc = json.loads(json.dumps(base_beats))
            b_doc["scenes"][1][field] = bad_val
            beats_path.write_text(json.dumps(b_doc, ensure_ascii=False, allow_nan=True), encoding="utf-8")
            assert_x02_failure(me.check_project(tmp_path), f"beats.scene.{field}={label}")
    for bad_s, bad_e, desc in ((5.0, 5.0, "equal"), (8.0, 3.0, "inverted")):
        b_doc = json.loads(json.dumps(base_beats))
        b_doc["scenes"][1]["start"] = bad_s
        b_doc["scenes"][1]["end"] = bad_e
        beats_path.write_text(json.dumps(b_doc, ensure_ascii=False), encoding="utf-8")
        assert_x02_failure(me.check_project(tmp_path), f"beats.scene interval {desc}")

    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    machine_json_path = tmp_path / "plan" / "machines" / "nvme-ssd.json"

    # 3. Machine `spec.start`/`spec.end`, `revealWindow.start`/`end`, `step.start`/`end`,
    #    and standalone `anchor.wordStart`/`wordEnd` (both in-memory and from raw JSON files with NaN/±Infinity)
    for target_kind in ("spec", "revealWindow", "step", "anchor_word"):
        for field in ("start", "end"):
            for label, bad_val in invalid_scalars:
                sp = _sample_nvme_vo_spec()
                if target_kind == "spec":
                    sp[field] = bad_val
                elif target_kind == "revealWindow":
                    sp["revealWindow"][field] = bad_val
                elif target_kind == "step":
                    sp["steps"][0]["id"] = "source-step"  # ensure step id with 'source' stays X02, not X01
                    sp["steps"][0][field] = bad_val
                else:
                    sp["steps"][0]["anchor"] = {
                        "word": 1,
                        "text": "الكنترولر",
                        "wordStart": bad_val if field == "start" else 4.3,
                        "wordEnd": bad_val if field == "end" else 4.95,
                    }
                # Standalone audit (without project or visual-direction.json)
                assert_x02_failure(
                    me.audit_machine_spec(sp, project=None),
                    f"standalone {target_kind}.{field}={label}",
                )
                # Disk JSON audit via `check_project` (testing Python `json.loads()` on NaN / ±Infinity)
                machine_json_path.write_text(
                    json.dumps(sp, indent=2, ensure_ascii=False, allow_nan=True),
                    encoding="utf-8",
                )
                assert_x02_failure(
                    me.check_project(tmp_path),
                    f"disk-json {target_kind}.{field}={label}",
                )

        # Empty (`end == start`) and inverted (`end < start`) intervals on each target
        for bad_s, bad_e, desc in ((4.5, 4.5, "equal"), (6.0, 4.3, "inverted")):
            sp = _sample_nvme_vo_spec()
            if target_kind == "spec":
                sp["start"], sp["end"] = bad_s, bad_e
            elif target_kind == "revealWindow":
                sp["revealWindow"]["start"], sp["revealWindow"]["end"] = bad_s, bad_e
            elif target_kind == "step":
                sp["steps"][0]["start"], sp["steps"][0]["end"] = bad_s, bad_e
            else:
                sp["steps"][0]["anchor"] = {
                    "word": 1,
                    "text": "الكنترولر",
                    "wordStart": bad_s,
                    "wordEnd": bad_e,
                }
            assert_x02_failure(
                me.audit_machine_spec(sp, project=None),
                f"standalone {target_kind} interval {desc}",
            )
            machine_json_path.write_text(json.dumps(sp, indent=2, ensure_ascii=False), encoding="utf-8")
            assert_x02_failure(me.check_project(tmp_path), f"disk-json {target_kind} interval {desc}")


def test_x02_rejects_huge_integers_without_overflow_error_in_memory_json_and_cli(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    huge_pos = 10**1000
    huge_neg = -(10**1000)

    # 1. Direct helper checks: huge ints, NaN, ±Infinity, bool, and non-numbers return False without OverflowError
    for fn in (me._is_finite_number, mk._finite):
        for bad in (huge_pos, huge_neg, float("nan"), float("inf"), float("-inf"), True, False, "4.3", None, [1]):
            assert fn(bad) is False, f"{fn.__name__}({type(bad)}) must return False"
        for good in (0, 3, -5, 4.35, 1e308, -1e308):
            assert fn(good) is True, f"{fn.__name__}({good!r}) must return True"

    def assert_clean_x02(report: dict, ctx: str) -> None:
        assert report["ok"] is False, f"Expected X02 failure for {ctx}"
        if "errors" in report:
            assert any(code == "X02" for code, _ in report["errors"]), (ctx, report["errors"])
            for m in report.get("machines", []):
                assert any(f["level"] == "error" and f["code"] == "X02" for f in m.get("findings", [])), (ctx, m)
        else:
            assert any(f["level"] == "error" and f["code"] == "X02" for f in report.get("findings", [])), (ctx, report)

    def assert_cli_x02(target_path: Path, ctx: str) -> None:
        proc = subprocess.run(
            [sys.executable, str(TOOLS / "machine_explainer.py"), str(target_path), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc.returncode == 1, f"CLI expected exit 1 for {ctx}, got {proc.returncode}: {proc.stdout}\n{proc.stderr}"
        assert "!! X02" in proc.stdout, (ctx, proc.stdout, proc.stderr)
        assert "Traceback" not in proc.stderr and "OverflowError" not in proc.stderr, proc.stderr

    # 2. In-memory + JSON disk round-trip + CLI check across spec, revealWindow, step, and anchor.wordStart/wordEnd
    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    machine_json_path = tmp_path / "plan" / "machines" / "nvme-ssd.json"

    for target_kind in ("spec", "revealWindow", "step", "anchor_word"):
        for field in ("start", "end"):
            for label, huge_val in (("10**1000", huge_pos), ("-(10**1000)", huge_neg)):
                sp = _sample_nvme_vo_spec()
                if target_kind == "spec":
                    sp[field] = huge_val
                elif target_kind == "revealWindow":
                    sp["revealWindow"][field] = huge_val
                elif target_kind == "step":
                    sp["steps"][0][field] = huge_val
                else:
                    sp["steps"][0]["anchor"] = {
                        "word": 1,
                        "text": "الكنترولر",
                        "wordStart": huge_val if field == "start" else 4.3,
                        "wordEnd": huge_val if field == "end" else 4.95,
                    }
                # Direct in-memory audit (both standalone and project-bound)
                assert_clean_x02(
                    me.audit_machine_spec(sp, project=None),
                    f"in-memory standalone {target_kind}.{field}={label}",
                )
                assert_clean_x02(
                    me.audit_machine_spec(sp, project=tmp_path),
                    f"in-memory project {target_kind}.{field}={label}",
                )
                # Actual JSON file write + read via `json.loads()` on disk
                machine_json_path.write_text(json.dumps(sp, indent=2, ensure_ascii=False), encoding="utf-8")
                parsed_back = json.loads(machine_json_path.read_text(encoding="utf-8"))
                assert isinstance(
                    parsed_back[field]
                    if target_kind == "spec"
                    else parsed_back["revealWindow"][field]
                    if target_kind == "revealWindow"
                    else parsed_back["steps"][0][field]
                    if target_kind == "step"
                    else parsed_back["steps"][0]["anchor"]["wordStart" if field == "start" else "wordEnd"],
                    int,
                )
                assert_clean_x02(me.check_project(tmp_path), f"disk-json {target_kind}.{field}={label}")

    # Verify CLI (`machine_explainer.py --check` + `make machine-check`) on huge integer in spec JSON
    sp_cli = _sample_nvme_vo_spec()
    sp_cli["end"] = huge_pos
    machine_json_path.write_text(json.dumps(sp_cli, indent=2, ensure_ascii=False), encoding="utf-8")
    assert_cli_x02(tmp_path, "project machine spec.end=10**1000")
    assert_cli_x02(machine_json_path, "standalone machine spec.end=10**1000")
    if shutil.which("make") is not None:
        mk_proc = subprocess.run(
            ["make", "machine-check", f"PY={sys.executable}", f"P={tmp_path}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert mk_proc.returncode != 0
        combined_mk = mk_proc.stdout + "\n" + mk_proc.stderr
        assert "!! X02" in combined_mk
        assert "Traceback" not in combined_mk and "OverflowError" not in combined_mk

    # 3. Project scene bounds (`plan/beats.json`) and measured words (`plan/word-timings.json`)
    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    beats_path = tmp_path / "plan" / "beats.json"
    base_beats = json.loads(beats_path.read_text(encoding="utf-8"))
    for field in ("start", "end"):
        for label, huge_val in (("10**1000", huge_pos), ("-(10**1000)", huge_neg)):
            b_doc = json.loads(json.dumps(base_beats))
            b_doc["scenes"][1][field] = huge_val
            beats_path.write_text(json.dumps(b_doc, ensure_ascii=False), encoding="utf-8")
            assert_clean_x02(me.check_project(tmp_path), f"beats.scene.{field}={label}")
    assert_cli_x02(tmp_path, "CLI beats.scene.end=-(10**1000)")

    _write_project_fixture(tmp_path, _sample_nvme_vo_spec())
    wt_path = tmp_path / "plan" / "word-timings.json"
    base_wt = json.loads(wt_path.read_text(encoding="utf-8"))
    for field in ("start", "end"):
        for label, huge_val in (("10**1000", huge_pos), ("-(10**1000)", huge_neg)):
            wt_doc = json.loads(json.dumps(base_wt))
            wt_doc["scenes"][1]["words"][1][field] = huge_val
            # Direct in-memory `_extract_measured_words` check
            with pytest.raises(ValueError, match="finite non-boolean"):
                me._extract_measured_words(wt_doc)
            # Disk JSON check via `check_project`
            wt_path.write_text(json.dumps(wt_doc, ensure_ascii=False), encoding="utf-8")
            assert_clean_x02(me.check_project(tmp_path), f"word-timings.{field}={label}")
    assert_cli_x02(tmp_path, "CLI word-timings.end=-(10**1000)")

    # Also check `caption_align` list-format `scene.start` with `10**1000` and `-(10**1000)`
    for label, huge_val in (("10**1000", huge_pos), ("-(10**1000)", huge_neg)):
        local_wt = [
            {"index": 1, "start": 0.0, "final": [{"text": "ليه", "start": 0.4, "end": 0.9}]},
            {"index": 2, "start": huge_val, "final": [{"text": "الكنترولر", "start": 1.3, "end": 1.95}]},
        ]
        wt_path.write_text(json.dumps(local_wt, ensure_ascii=False), encoding="utf-8")
        assert_clean_x02(me.check_project(tmp_path), f"caption_align scene.start={label}")


def test_x03_polygon_mask_occlusion_distinguishes_true_shape_from_aabb_and_honors_threshold():
    import machine_kit as mk  # noqa: PLC0415

    # Build a custom machine where an L-shaped `front` bracket has an axis-aligned bounding box
    # that 100% encloses the target chip in `mid`, while its actual polygon leaves the chip 0% covered!
    l_bracket_faces = [
        [[-120, -100, 12], [120, -100, 12], [120, -82, 12], [-120, -82, 12]],
        [[-120, -100, 12], [-102, -100, 12], [-102, 140, 12], [-120, 140, 12]],
        [[-120, 122, 12], [120, 122, 12], [120, 140, 12], [-120, 140, 12]],
    ]
    spec = {
        "version": 1,
        "id": "poly-vs-aabb",
        "archetype": "custom",
        "clock": "scene",
        "start": 0.0,
        "end": 3.0,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.6},
        "sources": [
            {"id": "s1", "title": "Test Hardware Reference", "kind": "manual", "ref": "DOC-101"}
        ],
        "parts": [
            {
                "id": "target_chip", "tag": "die", "layer": "mid", "primitive": "slab", "role": "chip",
                "x": -15, "y": -15, "z": 4, "dx": 36, "dy": 36, "dz": 8, "alpha": 1.0,
            },
            {
                "id": "l_frame_front", "tag": "frame", "layer": "front", "primitive": "poly3d", "role": "housing",
                "faces3d": l_bracket_faces, "alpha": 1.0,
            },
        ],
        "steps": [
            {
                "id": "step-die",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "page", "value": "p. 12"},
                "quote": "Central processor die remains exposed inside the L-frame.",
                "copyIds": ["c1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الشريحة"},
                "start": 0.6,
                "end": 2.8,
                "activeTags": ["die"],
                "motion": {"kind": "pulse", "tint": "active"},
            }
        ],
    }

    # Verify the L-bracket's screen AABB really encloses the target chip's screen AABB,
    # yet polygon coverage-mask occlusion reports 0.0% occlusion!
    graph = mk.build_machine_scene(spec, 1.2, force_full_reveal=True)
    chip_op = next(op for op in graph["ops"] if op["partId"] == "target_chip")
    frame_op = next(op for op in graph["ops"] if op["partId"] == "l_frame_front")
    chip_pts = [pt for f in chip_op["faces"] for pt in f["points"]]
    frame_pts = [pt for f in frame_op["faces"] for pt in f["points"]]
    assert min(p[0] for p in frame_pts) < min(p[0] for p in chip_pts)
    assert max(p[0] for p in frame_pts) > max(p[0] for p in chip_pts)
    assert min(p[1] for p in frame_pts) < min(p[1] for p in chip_pts)
    assert max(p[1] for p in frame_pts) > max(p[1] for p in chip_pts)

    occ = mk.compute_occlusion_report(spec, max_occlusion=0.10)
    assert occ["errors"] == []
    assert occ["results"][0]["occludedRatio"] == 0.0

    # Now add a 60%-alpha hood directly over the chip: passes at max_occlusion=0.65, fails at 0.35!
    spec["parts"].append({
        "id": "heavy_hood", "tag": "hood", "layer": "front", "primitive": "slab", "role": "cutaway",
        "x": -30, "y": -30, "z": 20, "dx": 70, "dy": 70, "dz": 4, "alpha": 0.60, "cutaway": True,
    })
    occ_fail = mk.compute_occlusion_report(spec, max_occlusion=0.35)
    assert len(occ_fail["errors"]) == 1
    assert occ_fail["results"][0]["occludedRatio"] > 0.55
    occ_pass = mk.compute_occlusion_report(spec, max_occlusion=0.65)
    assert occ_pass["errors"] == []
