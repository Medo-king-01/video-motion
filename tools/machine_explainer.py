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
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "medo-motion" / "scripts"))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))

import layout_p  # noqa: E402
import machine_kit as mk  # noqa: E402
import visual_direction as vd  # noqa: E402
from _safe_paths import checked_path  # noqa: E402

UNVERIFIED_SPEC_NUM_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:GB/s|MB/s|TB|GB|MB|MHz|GHz|GT/s|MT/s|W|°C|nm|ns|RPM)\b",
    re.IGNORECASE,
)


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
    if any(k in low for k in ("source", "locator", "quote", "illustrative")):
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
        beats = _load_json(proj / "plan" / "beats.json") or {}
        copy_doc = _load_json(proj / "plan" / "copy.json") or {}
        scenes_by_idx = {
            s.get("index", idx + 1): s
            for idx, s in enumerate(beats.get("scenes") or [])
            if isinstance(s, dict)
        }
        sc_idx = spec.get("scene")
        beat = scenes_by_idx.get(sc_idx)
        if beat is None:
            fail("X02", f"{spec['id']}: scene {sc_idx} does not exist in plan/beats.json")
        else:
            b_start, b_end = float(beat["start"]), float(beat["end"])
            if float(spec["start"]) < b_start - 1e-6 or float(spec["end"]) > b_end + 1e-6:
                fail(
                    "X02",
                    f"{spec['id']}: machine bounds [{spec['start']}, {spec['end']}] must stay inside "
                    f"scene {sc_idx} [{b_start}, {b_end}]",
                )

        wt_rel = spec.get("wordTimings") or "plan/word-timings.json"
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
                    words_by_scene = vd.measured_words(wt_doc)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                fail("X02", f"{spec['id']}: invalid wordTimings ({exc})")
                words_by_scene = {}

        copies_by_id = {
            c["id"]: c
            for c in (copy_doc.get("copy") or [])
            if isinstance(c, dict) and isinstance(c.get("id"), str)
        }

        bound_spec = json.loads(json.dumps(spec))
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

            if scene_words:
                anc = st["anchor"]
                w_idx = anc["word"]
                if not (0 <= w_idx < len(scene_words)):
                    fail("X02", f"{spec['id']}.{stid}: anchor word index {w_idx} out of range for scene {sc_idx}")
                else:
                    measured_w = scene_words[w_idx]
                    if anc["text"] != measured_w.get("text"):
                        fail(
                            "X02",
                            f"{spec['id']}.{stid}: anchor text {anc['text']!r} != measured word {measured_w.get('text')!r}",
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

        # X04: Dynamic safe-zone & platform right-rail envelope audit
        sample_t = (float(spec["start"]) + float(spec["end"])) * 0.5
        graph = mk.build_machine_scene(spec, sample_t, fps=fps, force_full_reveal=True)
        verts = graph["vertices"]
        if verts:
            xs = [v[0] for v in verts]
            ys = [v[1] for v in verts]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            if (
                min_x < env["x"][0] - 1e-3
                or max_x > env["x"][1] + 1e-3
                or min_y < env["y"][0] - 1e-3
                or max_y > env["y"][1] + 1e-3
            ):
                fail(
                    "X04",
                    f"{spec['id']}: projected geometry [{min_x:.1f}..{max_x:.1f}, {min_y:.1f}..{max_y:.1f}] "
                    f"exceeds dynamic {zone} safe zone [{env['x'][0]:.0f}..{env['x'][1]:.0f}, "
                    f"{env['y'][0]:.0f}..{env['y'][1]:.0f}]",
                )
            if max_y > env["nothing_important_below_y"] + 1e-3:
                fail(
                    "X04",
                    f"{spec['id']}: projected geometry crosses nothing_important_below_y "
                    f"({max_y:.1f} > {env['nothing_important_below_y']:.0f})",
                )

            rail = env.get("platform_right_rail")
            if rail is not None:
                w, h = int(env["w"]), int(env["h"])
                diagram_mask = np.zeros((h, w), dtype=np.uint8)
                for op in graph["ops"]:
                    if op["kind"] in ("solid", "wire"):
                        diagram_mask |= mk._rasterize_op_mask(op, w, h)
                rx0, ry0 = int(round(rail["x"])), int(round(rail["y"]))
                rx1, ry1 = int(round(rail["x"] + rail["w"])), int(round(rail["y"] + rail["h"]))
                rail_overlap_px = int(np.count_nonzero(diagram_mask[ry0:ry1, rx0:rx1]))
                if rail_overlap_px >= 4:
                    fail(
                        "X04",
                        f"{spec['id']}: projected polygon mask overlaps PLATFORM_RIGHT_RAIL "
                        f"by {rail_overlap_px} px² (x={rx0}..{rx1}, y={ry0}..{ry1})",
                    )

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
            if isinstance(sc, dict) and sc.get("index", idx + 1) == args.scene:
                start, end = float(sc["start"]), float(sc["end"])
                break
        draft = init_machine_draft(mid, args.archetype, scene=args.scene, start=start, end=end)
        raw_out.parent.mkdir(parents=True, exist_ok=True)
        raw_out.write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote draft machine spec -> {raw_out}")
        return 0

    target = _safe_file(args.target)
    if target.is_file():
        doc = json.loads(target.read_text(encoding="utf-8"))
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
