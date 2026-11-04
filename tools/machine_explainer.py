#!/usr/bin/env python3
"""Validate and scaffold Machine Explainer specs (`X01`–`X04`).

Enforces:
- `X01`: Verifiable technical sources with structured locators (`section|page|table|figure|clause|line`)
         + supporting quotes, or explicit `illustrative` labeling with no unverified hardware numbers.
- `X02`: Unified `clock="vo"` timing against `plan/beats.json`, `plan/word-timings.json`
         (`visual_direction.measured_words`), `plan/copy.json`, explicit `revealWindow.unit`,
         and active part-tag coverage.
- `X03`: Projected 2D polygon coverage-mask occlusion audit with configurable threshold
         (`--max-occlusion`, `step.maxOcclusion`, `spec.qa.maxOcclusion`, default `0.35`).
- `X04`: Dynamic safe-zone and `PLATFORM_RIGHT_RAIL` envelope check derived from `layout_p.safe_envelope()`.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "medo-motion" / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))

import layout_p  # noqa: E402
import machine_kit as mk  # noqa: E402
from _safe_paths import checked_path  # noqa: E402

UNVERIFIED_SPEC_NUM_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:GB/s|MB/s|TB|GB|MB|MHz|GHz|GT/s|MT/s|W|°C|nm|ns|RPM)\b",
    re.IGNORECASE,
)


def _is_finite_number(value: Any) -> bool:
    """Return True iff `value` is an int/float representable as a finite float (excluding `bool`)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(float(value))
    except (OverflowError, TypeError, ValueError):
        return False


def _short_repr(value: Any) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) >= 10**50:
        sign = "-" if value < 0 else ""
        return f"<{sign}int ({value.bit_length()} bits)>"
    return repr(value)


def _is_valid_interval(start: Any, end: Any, *, min_start: float | None = 0.0) -> bool:
    """Return True iff `start` and `end` are finite non-boolean numbers with `end > start`."""
    if not _is_finite_number(start) or not _is_finite_number(end):
        return False
    s_val = float(start)
    e_val = float(end)
    if min_start is not None and s_val < min_start:
        return False
    return e_val > s_val


def _extract_measured_words(document: Any) -> dict[int, list[dict[str, Any]]]:
    """Validate and normalize measured word timings independently of `visual-direction.json`.

    Supports both canonical VO word-timing documents (`{"clock": "vo", "scenes": [...]}`)
    and `caption_align` measurement lists (`[{"index": 1, "start": 0.0, "final": [...]}]`).
    Raw `start`/`end` values are validated before adding any scene offset so `bool` values
    (`True`/`False`), `NaN`, `±Infinity`, non-numbers, and `end <= start` never slip through.
    """
    if document is None:
        return {}
    is_local_list = isinstance(document, list)
    if not is_local_list:
        if not isinstance(document, dict):
            raise ValueError("word timings must be a JSON object or scene list")
        if document.get("clock") != "vo":
            raise ValueError('word timings must declare clock="vo"')
        scenes = document.get("scenes")
        if not isinstance(scenes, list):
            raise ValueError("word timings scenes must be a list")
    else:
        scenes = document

    out: dict[int, list[dict[str, Any]]] = {}
    for idx, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            raise ValueError("each word-timing scene entry must be an object")
        sc_num = sc.get("index", idx + 1) if is_local_list else sc.get("scene")
        if not isinstance(sc_num, int) or isinstance(sc_num, bool) or sc_num < 1:
            raise ValueError("each word-timing scene requires a positive integer scene index")
        if sc_num in out:
            raise ValueError(f"duplicate word-timing scene {sc_num}")

        if is_local_list:
            sc_start = sc.get("start")
            if not _is_finite_number(sc_start) or float(sc_start) < 0.0:
                raise ValueError(
                    f"scene {sc_num}: scene start must be a finite non-boolean number >= 0 "
                    f"(got {_short_repr(sc_start)})"
                )
            if "end" in sc and not _is_valid_interval(sc_start, sc.get("end"), min_start=0.0):
                raise ValueError(
                    f"scene {sc_num}: scene start/end must be finite non-boolean numbers with "
                    f"0 <= start < end (got start={_short_repr(sc_start)}, end={_short_repr(sc.get('end'))})"
                )
            offset = float(sc_start)
            raw_words = sc.get("final")
        else:
            offset = 0.0
            raw_words = sc.get("words")

        if not isinstance(raw_words, list):
            raise ValueError(f"scene {sc_num}: measured words must be a list")

        normalized: list[dict[str, Any]] = []
        for w_idx, word in enumerate(raw_words):
            if not isinstance(word, dict):
                raise ValueError(f"scene {sc_num} word {w_idx}: word entry must be an object")
            w_text = word.get("text")
            if not isinstance(w_text, str) or not w_text.strip():
                raise ValueError(f"scene {sc_num} word {w_idx}: word text must be a non-empty string")
            raw_s = word.get("start")
            raw_e = word.get("end")
            if not _is_valid_interval(raw_s, raw_e, min_start=0.0):
                raise ValueError(
                    f"scene {sc_num} word {w_idx} ({w_text!r}): start/end must be finite "
                    f"non-boolean numbers with 0 <= start < end "
                    f"(got start={_short_repr(raw_s)}, end={_short_repr(raw_e)})"
                )
            adj_s = float(raw_s) + offset
            adj_e = float(raw_e) + offset
            if not _is_valid_interval(adj_s, adj_e, min_start=0.0):
                raise ValueError(
                    f"scene {sc_num} word {w_idx} ({w_text!r}): shifted start/end overflowed finite float bounds"
                )
            normalized.append({
                **word,
                "text": w_text,
                "start": adj_s,
                "end": adj_e,
            })
        out[sc_num] = normalized
    return out


def _safe_file(path: Path, *, within: Path | None = None) -> Path:
    raw = Path(os.path.abspath(path))
    checked_path(raw, within=within)
    return checked_path(path.resolve(), within=within)


def _load_json(path: Path, default: Any = None) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def init_machine_draft(machine_id: str, archetype: str, *, scene: int = 1, start: float = 0.0, end: float = 4.0) -> dict[str, Any]:
    if archetype not in mk.SUPPORTED_ARCHETYPES:
        raise ValueError(f"Unsupported archetype {archetype!r}; choose from {', '.join(mk.SUPPORTED_ARCHETYPES)}")
    rw_end = round(start + min(1.2, max(0.3, (end - start) * 0.35)), 3)
    default_tag_by_arch = {
        "nvme_ssd": ("controller", "packet_flow", "pcie_to_controller"),
        "cpu_package": ("cores", "packet_flow", "ring_to_cores"),
        "ram_dimm": ("dram_banks", "packet_flow", "channel_a"),
        "cooling_system": ("fan", "airflow_stream", "intake_to_exhaust"),
        "custom": ("core", "pulse", None),
    }
    tag, motion_kind, path_name = default_tag_by_arch.get(archetype, ("controller", "pulse", None))
    motion: dict[str, Any] = {"kind": motion_kind, "tint": "active"}
    if path_name:
        motion["path"] = path_name
    return {
        "version": 1,
        "id": machine_id,
        "archetype": archetype,
        "clock": "vo",
        "scene": scene,
        "start": round(start, 3),
        "end": round(end, 3),
        "wordTimings": "plan/word-timings.json",
        "revealWindow": {
            "unit": "vo_seconds",
            "start": round(start, 3),
            "end": rw_end,
        },
        "qa": {
            "maxOcclusion": mk.DEFAULT_MAX_OCCLUSION,
            "zone": "content",
            "checkPlatformUi": True,
        },
        "sources": [
            {
                "id": "primary-spec",
                "title": "REPLACE WITH OFFICIAL SPECIFICATION TITLE",
                "kind": "spec",
                "ref": "https://example.org/replace-with-spec",
            }
        ],
        "steps": [
            {
                "id": "step-1",
                "evidence": "source",
                "sourceId": "primary-spec",
                "locator": {"kind": "section", "value": "§1.1"},
                "quote": "Replace with exact supporting technical excerpt from the cited section.",
                "copyIds": [f"{machine_id}-step-1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "REPLACE_WITH_MEASURED_WORD"},
                "start": round(rw_end, 3),
                "end": round(end, 3),
                "activeTags": [tag],
                "motion": motion,
            }
        ],
    }


def _classify_spec_error(msg: str) -> str:
    low = msg.lower()
    if low.startswith('source "') or low.startswith("sources ") or low.startswith("each source "):
        return "X01"
    body = low.split(": ", 1)[1] if ": " in low else low
    if any(k in body for k in ("sourceid", "evidence", "locator", "quote", "illustrative")):
        return "X01"
    return "X02"


def audit_machine_spec(
    spec: dict[str, Any],
    *,
    project: Path | None = None,
    max_occlusion: float | None = None,
) -> dict[str, Any]:
    """Run `X01`–`X04` checks on a single machine spec (standalone or bound to `project`)."""
    findings: list[dict[str, str]] = []

    def fail(code: str, msg: str) -> None:
        findings.append({"level": "error", "code": code, "message": msg})

    qa_cfg = spec.get("qa") if isinstance(spec, dict) and isinstance(spec.get("qa"), dict) else {}
    zone = qa_cfg.get("zone") or "content"
    check_platform = qa_cfg.get("checkPlatformUi") is not False

    try:
        env = layout_p.safe_envelope(zone, check_platform_ui=check_platform)
    except ValueError as exc:
        fail("X04", str(exc))
        env = layout_p.safe_envelope("content", check_platform_ui=check_platform)

    fps = int(env["fps"])
    base_errors = mk.validate_machine_spec(spec, fps=fps)
    for err in base_errors:
        fail(_classify_spec_error(err), f"{spec.get('id', 'machine')}: {err}")

    if not isinstance(spec, dict):
        return {"id": "unknown", "ok": False, "findings": findings, "occlusion": None, "bounds": None}

    if project is not None and spec.get("clock") != "vo":
        fail("X02", f"{spec.get('id', 'machine')}: project plan machine specs must use clock=\"vo\"")

    # Project-level cross-checks (`beats.json`, `word-timings.json`, `copy.json`)
    if project is not None and not base_errors:
        proj = _safe_file(project)
        try:
            beats = _load_json(proj / "plan" / "beats.json") or {}
        except (OSError, json.JSONDecodeError) as exc:
            fail("X02", f"{spec['id']}: invalid plan/beats.json ({exc})")
            beats = {}
        try:
            copy_doc = _load_json(proj / "plan" / "copy.json") or {}
        except (OSError, json.JSONDecodeError) as exc:
            fail("X02", f"{spec['id']}: invalid plan/copy.json ({exc})")
            copy_doc = {}

        scenes_by_idx = {
            s.get("index", idx + 1): s
            for idx, s in enumerate(beats.get("scenes") or [])
            if isinstance(s, dict)
        }
        sc_idx = spec.get("scene")
        beat = scenes_by_idx.get(sc_idx)
        beat_bounds: tuple[float, float] | None = None
        if beat is None:
            fail("X02", f"{spec['id']}: scene {sc_idx} does not exist in plan/beats.json")
        elif not _is_valid_interval(beat.get("start"), beat.get("end"), min_start=0.0):
            fail(
                "X02",
                f"{spec['id']}: scene {sc_idx} in plan/beats.json requires finite non-boolean "
                f"start/end bounds with 0 <= start < end "
                f"(got start={_short_repr(beat.get('start'))}, end={_short_repr(beat.get('end'))})",
            )
        else:
            b_start, b_end = float(beat["start"]), float(beat["end"])
            beat_bounds = (b_start, b_end)
            if float(spec["start"]) < b_start - 1e-6 or float(spec["end"]) > b_end + 1e-6:
                fail(
                    "X02",
                    f"{spec['id']}: machine bounds [{spec['start']}, {spec['end']}] must stay inside "
                    f"scene {sc_idx} [{b_start}, {b_end}]",
                )

        wt_rel = spec.get("wordTimings") or "plan/word-timings.json"
        words_loaded = False
        if not isinstance(wt_rel, str) or Path(wt_rel).is_absolute():
            fail("X02", f"{spec['id']}: wordTimings must be a project-relative path")
            words_by_scene: dict[int, list[dict[str, Any]]] = {}
        else:
            try:
                wt_path = _safe_file(proj / wt_rel, within=proj)
                wt_doc = _load_json(wt_path)
                if wt_doc is None:
                    fail("X02", f"{spec['id']}: missing measured word timings at {wt_rel}")
                    words_by_scene = {}
                else:
                    words_by_scene = _extract_measured_words(wt_doc)
                    words_loaded = True
            except (ValueError, OSError, KeyError, TypeError) as exc:
                fail("X02", f"{spec['id']}: invalid wordTimings ({exc})")
                words_by_scene = {}

        if words_loaded:
            if sc_idx not in words_by_scene:
                fail("X02", f"{spec['id']}: scene {sc_idx} is missing from measured wordTimings ({wt_rel})")
            elif len(words_by_scene[sc_idx]) == 0:
                fail("X02", f"{spec['id']}: scene {sc_idx} has an empty measured word list in {wt_rel}")
            elif beat_bounds is not None:
                b_start, b_end = beat_bounds
                for mw_i, mw in enumerate(words_by_scene[sc_idx]):
                    if mw["start"] < b_start - 1e-6 or mw["end"] > b_end + 1e-6:
                        fail(
                            "X02",
                            f"{spec['id']}: measured word {mw_i} ({mw['text']!r}) [{mw['start']}, {mw['end']}] "
                            f"falls outside scene {sc_idx} [{b_start}, {b_end}]",
                        )

        copies_by_id = {
            c["id"]: c
            for c in (copy_doc.get("copy") or [])
            if isinstance(c, dict) and isinstance(c.get("id"), str)
        }

        bound_spec = copy.deepcopy(spec)
        scene_words = words_by_scene.get(sc_idx, [])
        for st in bound_spec.get("steps", []):
            stid = st["id"]
            for cid in st.get("copyIds", []):
                frag = copies_by_id.get(cid)
                if frag is None or frag.get("scene") != sc_idx:
                    fail("X02", f"{spec['id']}.{stid}: copyId {cid!r} missing from plan/copy.json scene {sc_idx}")
                elif st.get("evidence") == "illustrative" and cid != st.get("illustrativeLabelId"):
                    txt = str(frag.get("text") or "")
                    if UNVERIFIED_SPEC_NUM_RE.search(txt):
                        fail(
                            "X01",
                            f"{spec['id']}.{stid}: illustrative step copy {cid!r} asserts hardware spec numbers "
                            f"({txt!r}) without a verifiable source+locator",
                        )

            anc = st["anchor"]
            w_idx = anc["word"]
            if not scene_words:
                fail(
                    "X02",
                    f"{spec['id']}.{stid}: cannot verify anchor word {w_idx} ({anc['text']!r}) — "
                    f"no measured words available for scene {sc_idx}",
                )
            elif not (0 <= w_idx < len(scene_words)):
                fail(
                    "X02",
                    f"{spec['id']}.{stid}: anchor word index {w_idx} out of range for scene {sc_idx} "
                    f"(0..{len(scene_words) - 1})",
                )
            else:
                measured_w = scene_words[w_idx]
                if anc["text"] != measured_w.get("text"):
                    fail(
                        "X02",
                        f"{spec['id']}.{stid}: anchor text {anc['text']!r} != measured word {measured_w.get('text')!r}",
                    )
                elif not _is_valid_interval(measured_w.get("start"), measured_w.get("end"), min_start=0.0):
                    fail(
                        "X02",
                        f"{spec['id']}.{stid}: measured word {w_idx} in scene {sc_idx} requires finite "
                        f"non-boolean start/end bounds with 0 <= start < end "
                        f"(got start={_short_repr(measured_w.get('start'))}, end={_short_repr(measured_w.get('end'))})",
                    )
                else:
                    anc["wordStart"] = float(measured_w["start"])
                    anc["wordEnd"] = float(measured_w["end"])

        # Re-validate bound anchor timing laws (`lead` <= 6 frames @ 30fps, `sync`, `reveal`, survival)
        for err in mk.validate_machine_spec(bound_spec, fps=fps):
            fail(_classify_spec_error(err), f"{spec['id']}: {err}")

    occ_report = None
    bounds = None
    if not any(f["code"] in ("X01", "X02") for f in findings):
        # X03: Projected-polygon coverage-mask occlusion audit
        occ_report = mk.compute_occlusion_report(spec, max_occlusion=max_occlusion)
        bounds = occ_report["bounds"]
        for err in occ_report["errors"]:
            fail("X03", f"{spec['id']}: {err}")

        # X04: Dynamic safe-zone & platform right-rail envelope audit across all steps & motion trajectories
        env_report = mk.compute_envelope_report(
            spec,
            zone=zone if zone in ("content", "caption", "hud") else "content",
            check_platform_ui=check_platform,
        )
        bounds = env_report["bounds"]
        for err in env_report["errors"]:
            fail("X04", f"{spec['id']}: {err}")

    return {
        "id": spec.get("id", "machine"),
        "ok": len(findings) == 0,
        "findings": findings,
        "occlusion": occ_report["results"] if occ_report else [],
        "bounds": bounds,
    }


def check_project(project: Path, *, max_occlusion: float | None = None) -> dict[str, Any]:
    """Audit all `plan/machines/*.json` specs in `project`."""
    proj = _safe_file(project)
    machines_dir = proj / "plan" / "machines"
    if not machines_dir.is_dir():
        return {"ok": True, "machines": [], "errors": []}

    specs = sorted(machines_dir.glob("*.json"))
    reports = []
    flat_errors: list[tuple[str, str]] = []
    for sp_path in specs:
        safe_sp = _safe_file(sp_path, within=proj)
        try:
            doc = json.loads(safe_sp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"{sp_path.name}: invalid JSON ({exc})"
            flat_errors.append(("X02", msg))
            reports.append({"id": sp_path.stem, "ok": False, "findings": [{"level": "error", "code": "X02", "message": msg}]})
            continue
        res = audit_machine_spec(doc, project=proj, max_occlusion=max_occlusion)
        reports.append(res)
        for item in res["findings"]:
            flat_errors.append((item["code"], item["message"]))

    return {
        "ok": len(flat_errors) == 0,
        "machines": reports,
        "errors": flat_errors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate or scaffold native Machine Explainer specs (X01–X04).")
    ap.add_argument("target", type=Path, help="Project directory or standalone machine JSON file")
    ap.add_argument("--init", dest="archetype", choices=list(mk.SUPPORTED_ARCHETYPES), help="Scaffold a draft machine JSON")
    ap.add_argument("--id", dest="machine_id", default=None, help="Machine id when using --init")
    ap.add_argument("--scene", type=int, default=1, help="Scene index for --init")
    ap.add_argument("--out", type=Path, default=None, help="Output JSON path for --init or --json")
    ap.add_argument("--force", action="store_true", help="Overwrite existing file during --init")
    ap.add_argument("--check", action="store_true", help="Run X01–X04 validation (default when --init is omitted)")
    ap.add_argument("--max-occlusion", type=float, default=None, help="Override maximum foreground occlusion ratio (0..1)")
    ap.add_argument("--json", dest="json_out", type=Path, default=None, help="Write structured audit report JSON")
    args = ap.parse_args(argv)

    if args.archetype:
        proj = _safe_file(args.target)
        mid = args.machine_id or args.archetype.replace("_", "-")
        out_path = args.out or (proj / "plan" / "machines" / f"{mid}.json")
        raw_out = Path(os.path.abspath(out_path))
        checked_path(raw_out, within=proj)
        if raw_out.exists() and not args.force:
            print(f"Refusing to overwrite existing {raw_out} without --force", file=sys.stderr)
            return 1
        beats = _load_json(proj / "plan" / "beats.json") or {}
        start, end = 0.0, 4.0
        for idx, sc in enumerate(beats.get("scenes") or []):
            if (
                isinstance(sc, dict)
                and sc.get("index", idx + 1) == args.scene
                and _is_valid_interval(sc.get("start"), sc.get("end"), min_start=0.0)
            ):
                start, end = float(sc["start"]), float(sc["end"])
                break
        draft = init_machine_draft(mid, args.archetype, scene=args.scene, start=start, end=end)
        raw_out.parent.mkdir(parents=True, exist_ok=True)
        raw_out.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote draft machine spec -> {raw_out}")
        return 0

    target = _safe_file(args.target)
    if target.is_file():
        try:
            doc = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            msg = f"{target.name}: invalid JSON ({exc})"
            res = {"id": target.stem, "ok": False, "findings": [{"level": "error", "code": "X02", "message": msg}]}
        else:
            res = audit_machine_spec(doc, project=None, max_occlusion=args.max_occlusion)
        payload = {"ok": res["ok"], "machines": [res], "errors": [(f["code"], f["message"]) for f in res["findings"]]}
    elif target.is_dir():
        payload = check_project(target, max_occlusion=args.max_occlusion)
    else:
        print(f"Target not found: {args.target}", file=sys.stderr)
        return 2

    if args.json_out:
        out_p = _safe_file(args.json_out) if args.json_out.exists() else checked_path(Path(os.path.abspath(args.json_out)))
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for m in payload["machines"]:
        if m["ok"]:
            max_occ = max((r["occludedRatio"] for r in m.get("occlusion") or []), default=0.0)
            print(f"PASS  {m['id']} · peak occlusion {max_occ * 100:.1f}%")
        else:
            for f in m["findings"]:
                print(f"!! {f['code']}  {f['message']}")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
