"""Milestone 1 & Phase 1 tests for the native Machine Explainer workflow (`X01`–`X04` + P/K/R parity)."""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
TOOLS = ROOT / "tools"

# Ensure Engine P's modules precede CLI wrappers in tools/
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ENGINE_P) in sys.path:
    sys.path.remove(str(ENGINE_P))
sys.path.insert(0, str(ENGINE_P))


def _sample_nvme_vo_spec() -> dict:
    return {
        "version": 1,
        "id": "nvme-ssd",
        "archetype": "nvme_ssd",
        "clock": "vo",
        "scene": 2,
        "start": 3.0,
        "end": 8.0,
        "wordTimings": "plan/word-timings.json",
        "revealWindow": {
            "unit": "vo_seconds",
            "start": 3.0,
            "end": 4.2,
        },
        "qa": {
            "maxOcclusion": 0.35,
            "zone": "content",
            "checkPlatformUi": True,
        },
        "sources": [
            {
                "id": "nvm-base-2.0d",
                "title": "NVM Express Base Specification Revision 2.0d",
                "kind": "spec",
                "ref": "https://nvmexpress.org/specifications/",
            }
        ],
        "steps": [
            {
                "id": "step-pcie",
                "evidence": "source",
                "sourceId": "nvm-base-2.0d",
                "locator": {"kind": "section", "value": "§3.1.2 PCIe Queue Transport, p. 44"},
                "quote": "Host submits commands directly across PCI Express lanes to controller queues.",
                "copyIds": ["nvme-step-1"],
                "timing": "sync",
                "anchor": {"word": 1, "text": "الكنترولر"},
                "start": 4.3,
                "end": 6.0,
                "activeTags": ["pcie_bus", "controller"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake", "rate": 1.4},
            },
            {
                "id": "step-nand",
                "evidence": "source",
                "sourceId": "nvm-base-2.0d",
                "locator": {"kind": "figure", "value": "Figure 14, Non-Volatile Memory Subsystem, p. 51"},
                "quote": "Controller stripes data across parallel non-volatile flash channels and dies.",
                "copyIds": ["nvme-step-2"],
                "timing": "reveal",
                "anchor": {"word": 3, "text": "طبقات"},
                "start": 6.1,
                "end": 7.8,
                "activeTags": ["nand_channel", "nand_stack"],
                "motion": {"kind": "packet_flow", "path": "controller_to_nand", "tint": "active", "rate": 1.2},
            },
        ],
    }


def _write_project_fixture(proj: Path, spec: dict) -> None:
    (proj / "plan" / "machines").mkdir(parents=True, exist_ok=True)
    beats = {
        "duration": 10.0,
        "scenes": [
            {"index": 1, "start": 0.0, "end": 3.0, "theme": "dark"},
            {"index": 2, "start": 3.0, "end": 8.0, "theme": "dark"},
            {"index": 3, "start": 8.0, "end": 10.0, "theme": "light"},
        ],
    }
    words = {
        "clock": "vo",
        "scenes": [
            {"scene": 1, "words": [{"text": "ليه", "start": 0.4, "end": 0.9}]},
            {
                "scene": 2,
                "words": [
                    {"text": "بيدخل", "start": 3.8, "end": 4.25},
                    {"text": "الكنترولر", "start": 4.3, "end": 4.95},
                    {"text": "ويوزع", "start": 5.3, "end": 5.9},
                    {"text": "طبقات", "start": 6.05, "end": 6.65},
                ],
            },
            {"scene": 3, "words": [{"text": "تفرق", "start": 8.2, "end": 8.8}]},
        ],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hook-1", "scene": 1, "role": "hook", "text": "إزاي الـSSD بيقرأ؟", "start": 0.0, "end": 2.6},
            {"id": "nvme-step-1", "scene": 2, "role": "label", "text": "المسارات بتسلّم الكنترولر مباشرة", "start": 4.3, "end": 6.0},
            {"id": "nvme-step-2", "scene": 2, "role": "label", "text": "يتوزع بالتوازي على طبقات الفلاش", "start": 6.1, "end": 7.8},
            {"id": "nvme-illus-tag", "scene": 2, "role": "label", "text": "رسم توضيحي", "start": 4.3, "end": 7.8},
        ],
    }
    (proj / "plan" / "beats.json").write_text(json.dumps(beats, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "word-timings.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "machines" / f"{spec['id']}.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


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


def test_x04_dynamic_safe_zone_and_platform_right_rail_audit():
    import layout_p  # noqa: PLC0415
    import machine_explainer as me  # noqa: PLC0415

    env = layout_p.safe_envelope("content", check_platform_ui=True)
    assert env["w"] == 1080 and env["h"] == 1920 and env["fps"] == 30

    # Push NVMe diagram into PLATFORM_RIGHT_RAIL (x=940..1080, y=1100..1500)
    bad_rail = _sample_nvme_vo_spec()
    bad_rail["layout"] = {"originX": 880, "originY": 1220, "scale": 1.1}
    res = me.audit_machine_spec(bad_rail)
    assert not res["ok"]
    assert any(f["code"] == "X04" and "PLATFORM_RIGHT_RAIL" in f["message"] for f in res["findings"])

    # Push NVMe diagram above content top safe-zone boundary (y < 200)
    bad_top = _sample_nvme_vo_spec()
    bad_top["layout"] = {"originX": 540, "originY": 180, "scale": 1.4}
    res_top = me.audit_machine_spec(bad_top)
    assert not res_top["ok"]
    assert any(f["code"] == "X04" and "safe zone" in f["message"] for f in res_top["findings"])

    # Intentional motion-path X04 tests:
    # Static solid/wire geometry stays completely safe near (500, 760), and the motion step is ONLY
    # active in [4.2, 5.8] (NOT active at spec midpoint 3.0s!).
    # Note: 3D point [527, 125, 0] projects to screen (sx=970, sy=1200), which is INSIDE the content
    # safe zone [40..1040, 200..1350] yet RIGHT INSIDE PLATFORM_RIGHT_RAIL [940..1080, 1100..1500]!
    def _motion_rail_spec(motion_kind: str, path_pts: list[list[float]]) -> dict:
        return {
            "version": 1,
            "id": f"rail-{motion_kind}",
            "archetype": "custom",
            "clock": "scene",
            "start": 0.0,
            "end": 6.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.6},
            "sources": [{"id": "s1", "title": "Motion Envelope Test Spec", "kind": "spec", "ref": "ENV-01"}],
            "parts": [
                {
                    "id": "safe_chip", "tag": "chip", "layer": "mid", "primitive": "slab", "role": "chip",
                    "x": -20, "y": -20, "z": 0, "dx": 40, "dy": 40, "dz": 12, "alpha": 1.0,
                }
            ],
            "paths": {"test_route": path_pts},
            "steps": [
                {
                    "id": "late-step",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§4.2"},
                    "quote": "Late step motion trajectory must be audited across its active window.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "حركة"},
                    "start": 4.2,
                    "end": 5.8,
                    "activeTags": ["chip"],
                    "motion": {"kind": motion_kind, "path": "test_route", "tint": "active"},
                }
            ],
        }

    # 1. packet_flow crossing PLATFORM_RIGHT_RAIL during late step [4.2, 5.8] must fail X04
    bad_pkt = _motion_rail_spec("packet_flow", [[0, 0, 14], [527, 125, 0]])
    res_pkt = me.audit_machine_spec(bad_pkt)
    assert not res_pkt["ok"]
    assert any(
        f["code"] == "X04" and "packet_flow" in f["message"] and "PLATFORM_RIGHT_RAIL" in f["message"]
        for f in res_pkt["findings"]
    ), res_pkt["findings"]

    # 2. airflow_stream crossing PLATFORM_RIGHT_RAIL during late step [4.2, 5.8] must fail X04
    bad_air = _motion_rail_spec("airflow_stream", [[0, 0, 14], [527, 125, 0]])
    res_air = me.audit_machine_spec(bad_air)
    assert not res_air["ok"]
    assert any(
        f["code"] == "X04" and "airflow_stream" in f["message"] and "PLATFORM_RIGHT_RAIL" in f["message"]
        for f in res_air["findings"]
    ), res_air["findings"]

    # 3. Safe packet_flow and airflow_stream paths stay completely clean
    ok_pkt = _motion_rail_spec("packet_flow", [[-30, -10, 14], [45, 25, 18]])
    ok_air = _motion_rail_spec("airflow_stream", [[-30, -10, 14], [45, 25, 18]])
    assert me.audit_machine_spec(ok_pkt)["ok"]
    assert me.audit_machine_spec(ok_air)["ok"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_nvme_ssd_p_k_r_geometry_parity_and_rendering():
    import layout_p  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    local_spec = mk.to_scene_local_machine(_sample_nvme_vo_spec(), scene_start=3.0)
    sample_t = 1.85  # inside step-pcie (1.3 .. 3.0), packet_flow active!

    py_graph = mk.build_machine_scene(local_spec, sample_t, theme="dark")

    # Render on a real Engine P frame with directed text + layout_p capture
    fr = np.full((1920, 1080, 3), 10.0, dtype=np.float32)
    direction = {
        "scenes": [
            {
                "scene": 2,
                "captionStyle": "softfade",
                "textStyles": {"label": "riseword"},
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
            }
        ]
    }
    copy_by_id = {
        "nvme-step-1": "المسارات بتسلّم الكنترولر مباشرة",
        "nvme-step-2": "يتوزع بالتوازي على طبقات الفلاش",
    }
    layout_p.begin_frame()
    try:
        mk.draw_machine_diagram(
            fr, local_spec, sample_t,
            direction=direction, scene=2, copy_by_id=copy_by_id, theme="dark",
        )
    finally:
        p_boxes = layout_p.end_frame()

    assert float(np.abs(fr - 10.0).max()) > 120.0, "Engine P must render visible cutaway pixels"
    assert any(b["id"] == "nvme-ssd.diagram" and b["kind"] == "keep" for b in p_boxes)
    assert any(b["id"] == "nvme-step-1" and b["kind"] == "text" for b in p_boxes)
    assert layout_p.audit_layout(p_boxes, check_platform_ui=True) == []

    # Compare exact state, bounds, world anchors, and ops against Engine K/R JS + Engine K Canvas2D adapter
    kit_js = (SKILL / "templates" / "render" / "lib" / "machine-kit.js").as_uri()
    vis_js = (SKILL / "templates" / "render" / "lib" / "machine-visual.js").as_uri()
    lay_js = (SKILL / "templates" / "render" / "lib" / "layout.js").as_uri()
    code = f"""
import {{ buildMachineScene, toSceneLocalMachine }} from {json.dumps(kit_js)};
import {{ drawMachineDiagram }} from {json.dumps(vis_js)};
import {{ captureLayout, auditLayout }} from {json.dumps(lay_js)};

const voSpec = {json.dumps(_sample_nvme_vo_spec())};
const localSpec = toSceneLocalMachine(voSpec, 3.0);
const graph = buildMachineScene(localSpec, {sample_t}, {{ theme: 'dark' }});

let drawOps = 0;
const tfStack = [];
let tf = {{ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 }};
const ctx = {{
  canvas: {{ width: 1080, height: 1920 }},
  globalAlpha: 1,
  fillStyle: '#000',
  strokeStyle: '#000',
  lineWidth: 1,
  lineJoin: 'round',
  lineCap: 'round',
  font: '800 46px Cairo',
  save() {{ tfStack.push({{ ...tf, alpha: this.globalAlpha }}); }},
  restore() {{ const p = tfStack.pop(); if (p) {{ this.globalAlpha = p.alpha; tf = {{ a: p.a, b: p.b, c: p.c, d: p.d, e: p.e, f: p.f }}; }} }},
  beginPath() {{}},
  closePath() {{}},
  moveTo() {{ drawOps += 1; }},
  lineTo() {{ drawOps += 1; }},
  fill() {{ drawOps += 1; }},
  stroke() {{ drawOps += 1; }},
  arc() {{ drawOps += 1; }},
  setLineDash() {{}},
  translate(dx, dy) {{ tf.e += tf.a * dx + tf.c * dy; tf.f += tf.b * dx + tf.d * dy; }},
  rotate() {{}},
  scale(sx, sy) {{ tf.a *= sx; tf.d *= sy; }},
  getTransform() {{ return {{ ...tf }}; }},
  measureText(txt) {{
    const w = [...String(txt)].length * 16;
    return {{ width: w, actualBoundingBoxLeft: w / 2, actualBoundingBoxRight: w / 2, actualBoundingBoxAscent: 32, actualBoundingBoxDescent: 10 }};
  }},
  fillText() {{ drawOps += 1; }},
  strokeText() {{ drawOps += 1; }},
}};
const cap = captureLayout(ctx);
cap.begin();
drawMachineDiagram(ctx, localSpec, {sample_t}, {{
  direction: {json.dumps(direction)},
  scene: 2,
  copyById: {json.dumps(copy_by_id)},
  theme: 'dark',
}});
const boxes = cap.snapshot();
const issues = auditLayout(boxes, {{ checkPlatformUi: true }});
console.log(JSON.stringify({{ graph, drawOps, boxes, issues }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    js_out = json.loads(res.stdout)
    js_graph = js_out["graph"]

    assert js_out["drawOps"] > 60
    assert js_out["issues"] == []
    assert any(b["id"] == "nvme-ssd.diagram" and b["kind"] == "keep" for b in js_out["boxes"])
    assert any(b["id"].startswith("nvme-step-1") and b["kind"] == "text" for b in js_out["boxes"])

    # Exact mathematical parity between Python (P) and JavaScript (K & R)
    assert py_graph["state"]["revealProgress"] == pytest.approx(js_graph["state"]["revealProgress"], abs=1e-4)
    assert py_graph["state"]["packetProgress"] == pytest.approx(js_graph["state"]["packetProgress"], abs=1e-4)
    assert py_graph["bounds"] == js_graph["bounds"]
    assert py_graph["world"] == js_graph["world"]
    assert len(py_graph["ops"]) == len(js_graph["ops"])
    for p_op, j_op in zip(py_graph["ops"], js_graph["ops"], strict=True):
        assert p_op["partId"] == j_op["partId"]
        assert p_op["kind"] == j_op["kind"]
        assert p_op["depth"] == pytest.approx(j_op["depth"], abs=1e-4)


@pytest.fixture(scope="module")
def _remotion_runtime(tmp_path_factory):
    """Prepare Remotion node_modules + shared Chromium once for real Engine R renders."""
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    chrom_proc = subprocess.run(
        ["node", str(TOOLS / "chromium.mjs"), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if chrom_proc.returncode != 0:
        pytest.skip(f"Chromium unavailable: {chrom_proc.stderr}")
    chrom = json.loads(chrom_proc.stdout)

    env_mods = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    if env_mods and Path(env_mods).is_dir():
        modules_dir = Path(env_mods).resolve()
    else:
        if shutil.which("npm") is None:
            pytest.skip("npm is not installed and MEDO_REMOTION_TEST_NODE_MODULES is unset")
        deps_dir = tmp_path_factory.mktemp("remotion_deps")
        rem_tpl = SKILL / "templates" / "remotion"
        shutil.copy2(rem_tpl / "package.json", deps_dir / "package.json")
        shutil.copy2(rem_tpl / "package-lock.json", deps_dir / "package-lock.json")
        ci_res = subprocess.run(
            ["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"],
            cwd=deps_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if ci_res.returncode != 0:
            pytest.skip(f"Remotion npm ci unavailable offline: {ci_res.stderr[:240]}")
        modules_dir = deps_dir / "node_modules"

    env = {
        **os.environ,
        "MEDO_TOOLKIT": str(ROOT / "tools" / "toolkit"),
        "MEDO_CHROMIUM": chrom["executablePath"],
        "REMOTION_BROWSER_EXECUTABLE": chrom["executablePath"],
    }
    if chrom.get("args"):
        env["REMOTION_CHROMIUM_ARGS"] = " ".join(chrom["args"])
    if chrom.get("libraryPath"):
        env["LD_LIBRARY_PATH"] = ":".join(
            [p for p in (chrom["libraryPath"], env.get("LD_LIBRARY_PATH")) if p]
        )
    return modules_dir, env


def _make_remotion_project(tmp_path: Path, modules_dir: Path, root_tsx: str) -> Path:
    proj = tmp_path / "r_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-machine-test", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (proj / "plan" / "beats.json").write_text(
        json.dumps({"duration": 4.0, "fps": 30, "frames": 120, "bounds": [0, 4.0], "scenes": [{"index": 1, "start": 0, "end": 4.0, "dur": 4.0, "frames": 120}]}),
        encoding="utf-8",
    )
    valid_td = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Remotion MachineDiagram real test direction",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"title": "softfade", "body": "softfade", "label": "riseword"},
                "textWhy": "crisp Arabic label motion",
                "fontStyles": {
                    "title": {"family": "Cairo", "weight": 800},
                    "body": {"family": "Cairo", "weight": 700},
                    "label": {"family": "Cairo", "weight": 800},
                },
                "fontWhy": "Cairo bold technical Arabic",
            }
        ],
    }
    (proj / "plan" / "text-direction.json").write_text(json.dumps(valid_td), encoding="utf-8")
    font_dst = proj / "public" / "fonts" / "Cairo"
    font_dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "assets" / "fonts" / "Cairo" / "Cairo_800ExtraBold.ttf", font_dst)
    (proj / "src" / "Root.tsx").write_text(root_tsx, encoding="utf-8")
    return proj


def test_remotion_machine_diagram_real_render_active_and_inactive_states(tmp_path: Path, _remotion_runtime):
    from PIL import Image, ImageChops  # noqa: PLC0415

    modules_dir, env = _remotion_runtime
    spec = {
        "version": 1,
        "id": "r-real-nvme",
        "archetype": "nvme_ssd",
        "clock": "scene",
        "start": 0.0,
        "end": 3.2,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.7},
        "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
        "steps": [
            {
                "id": "step-1",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "section", "value": "§3.1.2"},
                "quote": "Host submits queue entries over PCIe lanes to the controller.",
                "copyIds": ["c-1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الكنترولر"},
                "start": 1.0,
                "end": 2.8,
                "activeTags": ["pcie_bus", "controller", "dram_cache"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
            }
        ],
    }
    td_doc = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Real Remotion MachineDiagram verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"label": "riseword"},
                "textWhy": "crisp Arabic label motion",
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
                "fontWhy": "Cairo bold technical Arabic",
            }
        ],
    }
    copy_by_id = {"c-1": "بيانات PCIe بتدخل للكنترولر"}

    root_tsx = f"""import React, {{useEffect, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{MachineDiagram}} from './lib/MachineDiagram';

const SPEC = {json.dumps(spec)};
const TD = {json.dumps(td_doc)};
const COPY = {json.dumps(copy_by_id)};

const SceneComp: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  const [fontGate] = useState(() => delayRender('Load Cairo font'));
  useEffect(() => {{
    new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}})
      .load()
      .then((f) => {{ document.fonts.add(f); continueRender(fontGate); }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);
  return (
    <AbsoluteFill style={{{{background: PALETTE.ink}}}}>
      <MachineDiagram
        spec={{SPEC}}
        time={{frame / fps}}
        direction={{TD}}
        scene={{1}}
        copyById={{COPY}}
        theme="dark"
        strictLayout
      />
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition id="MachineRealTest" component={{SceneComp}} durationInFrames={{120}} fps={{BRAND.fps}} width={{BRAND.width}} height={{BRAND.height}} />
);
"""
    proj = _make_remotion_project(tmp_path, modules_dir, root_tsx)

    # 1. Strict TypeScript check across MachineDiagram.tsx, DirectedText.tsx, layout.tsx, and Root.tsx
    tsc = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc.returncode == 0, tsc.stdout + "\n" + tsc.stderr

    def render_still(frame_idx: int, name: str) -> Image.Image:
        out_file = proj / name
        r = subprocess.run(
            [
                "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
                "MachineRealTest", str(out_file), f"--frame={frame_idx}", "--log=error",
            ],
            cwd=proj,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert r.returncode == 0, r.stdout + "\n" + r.stderr
        return Image.open(out_file).convert("RGB")

    # Frame 9 (t=0.30s): inside opening reveal, BEFORE step-1 [1.0..2.8] -> geometry visible, callout absent
    im_pre = render_still(9, "pre.png")
    # Frame 48 (t=1.60s): step-1 ACTIVE -> geometry + packet_flow + DirectedText Arabic callout visible
    im_act1 = render_still(48, "active1.png")
    # Frame 57 (t=1.90s): step-1 ACTIVE later instant -> packet_flow dots moved deterministically
    im_act2 = render_still(57, "active2.png")
    # Frame 108 (t=3.60s): AFTER spec.end (3.2s) -> MachineDiagram inactive (returns null -> pure ink #0A0A0A)
    im_off = render_still(108, "inactive.png")

    # Verify inactive frame is pure #0A0A0A (RGB 10,10,10)
    assert im_off.getextrema() == ((10, 10), (10, 10), (10, 10))

    # Verify isometric geometry renders in both pre-step and active frames (diagram crop y=600..880)
    diag_pre = np.asarray(im_pre.crop((240, 600, 800, 880)))
    diag_act1 = np.asarray(im_act1.crop((240, 600, 800, 880)))
    assert int(diag_pre.max()) > 90
    assert int(diag_act1.max()) > 160
    # Active motion (packets + active part highlight) visibly changes diagram pixels between t=1.60s and t=1.90s
    assert ImageChops.difference(
        im_act1.crop((240, 600, 800, 880)),
        im_act2.crop((240, 600, 800, 880)),
    ).getbbox() is not None

    # Verify DirectedText Arabic callout is absent at t=0.30s and crisp at t=1.60s (callout crop y=900..1060)
    txt_pre = np.asarray(im_pre.crop((140, 900, 940, 1060)))
    txt_act = np.asarray(im_act1.crop((140, 900, 940, 1060)))
    assert int(txt_pre.max()) <= 12, "Callout region must be empty before step-1 starts"
    assert int(txt_act.max()) > 180, "DirectedText Arabic callout must render visible ink during active step"


def test_remotion_layout_audit_catches_multiline_arabic_overflow_and_right_rail(tmp_path: Path, _remotion_runtime):
    modules_dir, env = _remotion_runtime
    spec = {
        "version": 1,
        "id": "r-layout-gate",
        "archetype": "nvme_ssd",
        "clock": "scene",
        "start": 0.0,
        "end": 3.0,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.5},
        "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
        "steps": [
            {
                "id": "step-1",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "section", "value": "§3.1.2"},
                "quote": "Host submits queue entries over PCIe lanes to the controller.",
                "copyIds": ["c-1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الكنترولر"},
                "start": 0.8,
                "end": 2.8,
                "activeTags": ["pcie_bus", "controller"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
            }
        ],
    }
    td_doc = {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Engine R Arabic layout gate verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "captionWhy": "clean technical entry",
                "textStyles": {"label": "softfade"},
                "textWhy": "test wrapping and placement",
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
                "fontWhy": "Cairo bold Arabic",
            }
        ],
    }

    root_tsx = f"""import React, {{useEffect, useLayoutEffect, useRef, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{MachineDiagram}} from './lib/MachineDiagram';
import {{auditLayout, collectDomLayoutBoxes, ProtectBox}} from './lib/layout';

const SPEC = {json.dumps(spec)};
const TD = {json.dumps(td_doc)};

type VariantProps = {{ mode?: 'safe_short' | 'wrap_overflow' | 'right_rail' | 'diagram_collide' | 'motion_shift' | 'face_overlap' }};

const GateComp: React.FC<VariantProps> = ({{mode = 'safe_short'}}) => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [fontsReady, setFontsReady] = useState(false);
  const [fontGate] = useState(() => delayRender('Load Cairo font'));
  useEffect(() => {{
    new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}})
      .load()
      .then((f) => {{ document.fonts.add(f); setFontsReady(true); continueRender(fontGate); }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);

  useLayoutEffect(() => {{
    if (mode !== 'face_overlap' || !fontsReady || !stageRef.current) return;
    const issues = auditLayout(collectDomLayoutBoxes(stageRef.current), {{checkPlatformUi: true}});
    if (issues.length > 0) {{
      cancelRender(
        new Error(
          `Remotion layout audit failed: ${{issues.map((i) => `${{i.code}}: ${{i.message}}`).join('; ')}}`,
        ),
      );
    }}
  }}, [mode, fontsReady, frame]);

  const copyText =
    mode === 'wrap_overflow'
      ? 'البيانات بتتنقل عبر خطوط PCIe السريعة مباشرة للكنترولر وبتتوزع بالتوازي على قنوات الذاكرة المدمجة في أكثر من سطر متتالي'
      : 'بيانات PCIe بتدخل للكنترولر';
  const calloutY =
    mode === 'wrap_overflow' ? 1235
    : mode === 'right_rail' ? 1150
    : mode === 'diagram_collide' ? 740
    : 1235;
  const calloutStyle: React.CSSProperties =
    mode === 'right_rail'
      ? {{textAlign: 'right'}}
      : mode === 'motion_shift'
        ? {{textAlign: 'center', transform: 'translateY(130px) scale(1.15)'}}
        : {{textAlign: 'center'}};

  return (
    <AbsoluteFill ref={{stageRef}} style={{{{background: PALETTE.ink}}}}>
      {{mode === 'face_overlap' ? (
        <ProtectBox id="presenter.face" kind="face" box={{{{x: 340, y: 1215, w: 400, h: 100}}}} />
      ) : null}}
      <MachineDiagram
        spec={{SPEC}}
        time={{frame / fps}}
        direction={{TD}}
        scene={{1}}
        copyById={{{{'c-1': copyText}}}}
        calloutY={{calloutY}}
        calloutStyle={{calloutStyle}}
        theme="dark"
        strictLayout={{mode !== 'face_overlap'}}
      />
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LayoutGateTest"
    component={{GateComp}}
    durationInFrames={{90}}
    fps={{BRAND.fps}}
    width={{BRAND.width}}
    height={{BRAND.height}}
    defaultProps={{{{mode: 'safe_short'}}}}
  />
);
"""
    proj = _make_remotion_project(tmp_path, modules_dir, root_tsx)

    def run_mode(mode: str):
        return subprocess.run(
            [
                "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
                "LayoutGateTest", str(proj / f"{mode}.png"),
                "--frame=48", f'--props={json.dumps({"mode": mode})}',
            ],
            cwd=proj,
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
        )

    # 1. Short single-line centered Arabic text at calloutY=1235 fits inside [200..1350] and x=[300..780] -> PASS
    r_ok = run_mode("safe_short")
    assert r_ok.returncode == 0, r_ok.stdout + "\n" + r_ok.stderr

    # 2. Long Arabic copy at the EXACT SAME calloutY=1235 wraps onto 3 lines past y=1350 -> FAIL L01!
    r_wrap = run_mode("wrap_overflow")
    combined_wrap = r_wrap.stdout + "\n" + r_wrap.stderr
    assert r_wrap.returncode != 0
    assert "Remotion layout audit failed" in combined_wrap and "L01" in combined_wrap, combined_wrap

    # 3. Right-aligned Arabic text at y=1150 extends into x=940..1040 -> FAIL L04 (PLATFORM_RIGHT_RAIL)!
    r_rail = run_mode("right_rail")
    combined_rail = r_rail.stdout + "\n" + r_rail.stderr
    assert r_rail.returncode != 0
    assert "Remotion layout audit failed" in combined_rail and "L04" in combined_rail, combined_rail

    # 4. Callout placed over the cutaway diagram (calloutY=740) -> FAIL L02 (keep-box collision)!
    r_col = run_mode("diagram_collide")
    combined_col = r_col.stdout + "\n" + r_col.stderr
    assert r_col.returncode != 0
    assert "Remotion layout audit failed" in combined_col and "L02" in combined_col, combined_col

    # 5. Transform/motion displacement pushing an otherwise-safe calloutY=1235 line past y=1350 -> FAIL L01!
    r_shift = run_mode("motion_shift")
    combined_shift = r_shift.stdout + "\n" + r_shift.stderr
    assert r_shift.returncode != 0
    assert "Remotion layout audit failed" in combined_shift and "L01" in combined_shift, combined_shift

    # 6. Text overlapping a protected presenter `face` box -> FAIL L03 (face overlap, distinct from L02)!
    r_face = run_mode("face_overlap")
    combined_face = r_face.stdout + "\n" + r_face.stderr
    assert r_face.returncode != 0
    assert (
        "Remotion layout audit failed" in combined_face
        and "L03" in combined_face
        and "presenter face box" in combined_face
    ), combined_face


def _archetype_scene_specs() -> list[dict]:
    return [
        {
            "version": 1,
            "id": "nvme-arch",
            "archetype": "nvme_ssd",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
            "steps": [
                {
                    "id": "s-ctrl",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§3.1.2"},
                    "quote": "Host submits queue entries over PCIe lanes to the controller.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "الكنترولر"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["pcie_bus", "controller", "dram_cache"],
                    "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
                },
                {
                    "id": "s-nand",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "figure", "value": "Fig. 14"},
                    "quote": "Controller writes across parallel non-volatile flash channels.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "فلاش"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["nand_channel", "nand_stack"],
                    "motion": {"kind": "packet_flow", "path": "controller_to_nand", "tint": "active"},
                },
            ],
        },
        {
            "version": 1,
            "id": "cpu-arch",
            "archetype": "cpu_package",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "Processor Architecture Reference Manual", "kind": "manual", "ref": "CPU-PRM-2025"}],
            "steps": [
                {
                    "id": "s-cores",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§2.4 Core Complex & Shared L3"},
                    "quote": "Compute cores share a unified L3 cache slice connected over the die fabric.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "الأنوية"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["socket_pins", "cores", "l3_cache"],
                    "motion": {"kind": "packet_flow", "path": "ring_to_cores", "tint": "active"},
                },
                {
                    "id": "s-io",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "table", "value": "Table 4-1 Die Interconnect"},
                    "quote": "High-speed fabric links connect compute tiles with the I/O die.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "الذاكرة"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["fabric", "io_die"],
                    "motion": {"kind": "packet_flow", "path": "cache_to_io", "tint": "intake"},
                },
            ],
        },
        {
            "version": 1,
            "id": "ram-arch",
            "archetype": "ram_dimm",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "JEDEC DDR5 SDRAM Standard JESD79-5C", "kind": "standard", "ref": "JESD79-5C"}],
            "steps": [
                {
                    "id": "s-rcd",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "clause", "value": "Clause 4.1 Sub-channel Architecture"},
                    "quote": "Each DIMM routes two independent sub-channels from connector pins through the controller.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "القنوات"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["bus_pins", "rcd_controller", "channel_bus"],
                    "motion": {"kind": "packet_flow", "path": "channel_a", "tint": "intake"},
                },
                {
                    "id": "s-banks",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§4.5 Bank Groups"},
                    "quote": "Parallel DRAM bank groups service burst reads and writes concurrently.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "بنوك"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["dram_banks"],
                    "motion": {"kind": "packet_flow", "path": "channel_b", "tint": "active"},
                },
            ],
        },
        {
            "version": 1,
            "id": "cool-arch",
            "archetype": "cooling_system",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "Two-Phase Heat Pipe Thermal Transfer Handbook", "kind": "paper", "ref": "DOI:10.1016/heatpipe"}],
            "steps": [
                {
                    "id": "s-pipes",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§2.2 Evaporator to Fin Condenser"},
                    "quote": "Heat conducts into the coldplate and travels along sealed heatpipes into the fin stack.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "أنابيب"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["coldplate", "heatpipes", "fin_stack"],
                    "motion": {"kind": "packet_flow", "path": "heatpipe_transfer", "tint": "active"},
                },
                {
                    "id": "s-fan",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "page", "value": "p. 88 Forced Convection"},
                    "quote": "Axial fan rotation drives intake airflow across the fin array to exhaust.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "المروحة"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["fan", "fin_stack"],
                    "motion": {"kind": "airflow_stream", "path": "intake_to_exhaust", "tint": "intake", "rpm": 240},
                },
            ],
        },
    ]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_all_four_hardware_archetypes_pass_qa_and_match_across_p_k_r():
    import machine_explainer as me  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    specs = _archetype_scene_specs()
    kit_js = (SKILL / "templates" / "render" / "lib" / "machine-kit.js").as_uri()
    remotion_lib = SKILL / "templates" / "remotion" / "src" / "lib"

    for idx, spec in enumerate(specs):
        theme = "dark" if idx % 2 == 0 else "light"
        # X01–X04 standalone audit (including X03 <= 0.30 strict mask occlusion & X04 safe zone)
        audit = me.audit_machine_spec(spec, max_occlusion=0.30)
        assert audit["ok"], f"{spec['archetype']} failed audit: {audit['findings']}"

        for sample_t in (1.55, 3.05):
            py_g = mk.build_machine_scene(spec, sample_t, theme=theme)
            fr = np.full((1920, 1080, 3), 10.0 if theme == "dark" else 240.0, dtype=np.float32)
            mk.draw_machine_diagram(fr, spec, sample_t, theme=theme)
            assert float(np.std(fr)) > 3.0, f"{spec['archetype']} produced blank frame in Engine P"

            js_code = f"""
import {{ buildMachineScene }} from {json.dumps(kit_js)};
const g = buildMachineScene({json.dumps(spec)}, {sample_t}, {{ theme: {json.dumps(theme)} }});
console.log(JSON.stringify(g));
"""
            res = subprocess.run(["node", "--input-type=module", "-e", js_code], capture_output=True, text=True, check=True)
            js_g = json.loads(res.stdout)
            assert py_g["bounds"] == js_g["bounds"]
            assert py_g["world"] == js_g["world"]
            assert py_g["state"]["spinDeg"] == pytest.approx(js_g["state"]["spinDeg"], abs=1e-4)
            assert py_g["state"]["airflowPhase"] == pytest.approx(js_g["state"]["airflowPhase"], abs=1e-4)
            assert len(py_g["ops"]) == len(js_g["ops"])

    # Verify Engine R's remotion/src/lib/machine-kit.js + MachineDiagram.tsx cover cooling_system airflow & fan blades (Node 20+ compatible)
    r_exec = f"""
import fs from 'node:fs';
import path from 'node:path';
import {{ pathToFileURL }} from 'node:url';

const libDir = {json.dumps(str(remotion_lib))};
const kitUrl = pathToFileURL(path.join(libDir, 'machine-kit.js')).href;
const tsx = fs.readFileSync(path.join(libDir, 'MachineDiagram.tsx'), 'utf8');
for (const token of ['<svg', '<polygon', '<polyline', '<line', '<circle', '<DirectedText', "op.kind === 'airflow'", 'bladeLines']) {{
  if (!tsx.includes(token)) throw new Error('MachineDiagram.tsx missing expected token: ' + token);
}}
const kit = await import(kitUrl);
const coolSpec = {json.dumps(specs[3])};
const graph = kit.buildMachineScene(coolSpec, 3.05, {{ theme: 'dark', fps: 30 }});
const hasAirflow = graph.ops.some(o => o.kind === 'airflow' && o.streams.length === 3);
const hasBlades = graph.ops.some(o => o.kind === 'solid' && (o.bladeLines?.length || 0) === 7);
console.log(JSON.stringify({{ hasAirflow, hasBlades, spinDeg: graph.state.spinDeg }}));
"""
    r_res = subprocess.run(["node", "--input-type=module", "-e", r_exec], capture_output=True, text=True, check=True)
    r_data = json.loads(r_res.stdout)
    assert r_data["hasAirflow"] is True
    assert r_data["hasBlades"] is True
    assert r_data["spinDeg"] != 18.0


def test_cli_scaffold_and_reel_lint_integration(tmp_path: Path):
    # 1. Test `machine_explainer.py --init cpu_package`
    r_init = subprocess.run(
        [sys.executable, str(TOOLS / "machine_explainer.py"), str(tmp_path), "--init", "cpu_package", "--id", "cpu-1"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Wrote draft machine spec" in r_init.stdout
    draft_path = tmp_path / "plan" / "machines" / "cpu-1.json"
    assert draft_path.is_file()

    # Draft placeholder should fail X02 until anchored to real measured words & beats
    r_draft_chk = subprocess.run(
        [sys.executable, str(TOOLS / "machine_explainer.py"), str(tmp_path), "--check"],
        capture_output=True,
        text=True,
    )
    assert r_draft_chk.returncode == 1
    draft_path.unlink()

    # 2. Write a complete valid project with `plan/machines/nvme-ssd.json` and run `reel_lint.py`
    spec = _sample_nvme_vo_spec()
    _write_project_fixture(tmp_path, spec)
    # Add text-direction.json + techniques.json so full `reel_lint.py` passes with X00!
    td_doc = {
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "textStyles": {"hook": "zoompunch"},
                "fontStyles": {"hook": {"family": "Cairo", "weight": 800}},
            },
            {
                "scene": 2,
                "captionStyle": "softfade",
                "textStyles": {"label": "riseword"},
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
            },
            {
                "scene": 3,
                "captionStyle": "softfade",
                "textStyles": {},
                "fontStyles": {},
            },
        ]
    }
    (tmp_path / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    lint_json = tmp_path / "lint-out.json"
    r_lint = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(tmp_path), "--json", str(lint_json)],
        capture_output=True,
        text=True,
    )
    lint_report = json.loads(lint_json.read_text(encoding="utf-8"))
    codes = {item["code"]: item["level"] for item in lint_report["items"]}
    assert codes.get("X00") == "ok", r_lint.stdout + r_lint.stderr
    assert not any(c.startswith("X0") and lvl == "error" for c, lvl in codes.items())


