#!/usr/bin/env python3
"""Stage checkpoint and Delivery Promise gate for a reel project.

    python3 tools/stage_gate.py projects/my-reel --stage intake
    python3 tools/stage_gate.py projects/my-reel --stage plan --write-checkpoint
    python3 tools/stage_gate.py projects/my-reel --stage render --media out/master.mp4
    python3 tools/stage_gate.py projects/my-reel --stage deliver --media out/master.mp4 --layout-report cache/layout-v1/report.json
    python3 tools/stage_gate.py projects/my-reel --verify-checkpoint plan

Enforces the cumulative studio contract (`AGENTS.md` §5 & §7, `DESIGN_SYSTEM.md` §7–8) without
creating a background orchestrator or keeping finished videos in Git:
- `G01` (`intake`): `BRIEF.md`, `plan/script.md`, and VO recording present (no scaffold placeholders)
- `G02` (`plan`): `out/vo24.wav` is mono 24 kHz PCM16 and `vo_length.py --check` agrees with `plan/beats.json` + scene code
- `G03` (`plan`): `copy.json`, `text-direction.json`, `visual-direction.json` (when present), and `techniques.json` are complete
- `G04` (`plan`): `reel_lint.py --scan-code` and `brand_check.py --project` pass cleanly
- `G05` (`render`): rendered MP4 exists and any supplied/required layout audit report (`K` or `P`) passed
- `G06` (`deliver`): `media_qa.py --mode master` passes on the final MP4, external assets in `assets/` are credited in `CREDITS.md`, and no unapproved series chip was added
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
# Put toolkit libraries ahead of `tools/` so `text_direction` resolves to the library module, not `tools/text_direction.py`.
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(SKILL / "scripts"))
sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))

import asr_check  # noqa: E402
import media_qa  # noqa: E402
import text_direction as td  # noqa: E402
import visual_direction as vd  # noqa: E402
from _safe_paths import checked_path  # noqa: E402

STAGES = ("intake", "plan", "render", "deliver")
STAGE_RANK = {name: idx for idx, name in enumerate(STAGES)}
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".aac", ".opus"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_artifact_digest(project: Path, media_path: Path | None = None) -> tuple[str, dict[str, str]]:
    """Hash canonical project inputs/plans (and optional rendered MP4) to detect stale checkpoints."""
    tracked_rel = [
        "BRIEF.md",
        "STYLE.md",
        "TASTE.md",
        "CREDITS.md",
        "assets/CREDITS.md",
        "plan/script.md",
        "plan/beats.json",
        "plan/copy.json",
        "plan/text-direction.json",
        "plan/visual-direction.json",
        "plan/techniques.json",
        "plan/hybrid.json",
        "out/vo24.wav",
    ]
    digests: dict[str, str] = {}
    for rel in tracked_rel:
        candidate = project / rel
        if candidate.is_file() and not candidate.is_symlink():
            digests[rel] = _sha256_file(candidate)
    if media_path is not None and media_path.is_file() and not media_path.is_symlink():
        try:
            key = media_path.relative_to(project).as_posix()
        except ValueError:
            key = str(media_path)
        digests[f"media:{key}"] = _sha256_file(media_path)

    overall = hashlib.sha256()
    for key in sorted(digests):
        overall.update(f"{key}={digests[key]}\n".encode())
    return overall.hexdigest(), digests


def _studio_bundled_assets() -> tuple[set[str], set[str]]:
    pose_files: set[str] = {"poses.json"}
    poses_dir = ROOT / "assets" / "poses"
    if poses_dir.is_dir():
        pose_files.update(p.name for p in poses_dir.glob("*.png"))
    font_files: set[str] = {"fonts.json"}
    fonts_dir = ROOT / "assets" / "fonts"
    if fonts_dir.is_dir():
        for p in fonts_dir.rglob("*"):
            if p.is_file():
                font_files.add(p.relative_to(fonts_dir).as_posix())
    return pose_files, font_files


def _external_project_assets(project: Path) -> list[Path]:
    """Return files in `project/assets/` that did not come from studio poses/fonts or user VO/refs."""
    assets_dir = project / "assets"
    if not assets_dir.is_dir():
        return []
    bundled_poses, bundled_fonts = _studio_bundled_assets()
    externals: list[Path] = []
    for path in sorted(assets_dir.rglob("*")):
        if not path.is_file() or path.name.startswith("."):
            continue
        rel = path.relative_to(assets_dir)
        parts = rel.parts
        if not parts:
            continue
        if parts[0] in ("vo", "refs"):
            continue
        if rel.as_posix() == "CREDITS.md":
            continue
        if parts[0] == "poses" and len(parts) == 2 and parts[1] in bundled_poses:
            continue
        if parts[0] == "fonts":
            sub = Path(*parts[1:]).as_posix()
            if sub in bundled_fonts:
                continue
        externals.append(rel)
    return externals


def _safe_abs(path: Path, *, tree: bool = False) -> Path:
    checked_path(Path(os.path.abspath(path)), tree=tree)
    return checked_path(path.resolve(), tree=tree)


def _resolve_media(project: Path, explicit: Path | None) -> tuple[Path | None, str | None]:
    if explicit is not None:
        raw = explicit if explicit.is_absolute() else (project / explicit)
        resolved = _safe_abs(raw)
        if not resolved.is_file():
            return None, f"Rendered media file not found: {explicit}"
        return resolved, None
    out_dir = project / "out"
    if not out_dir.is_dir():
        return None, "No out/ directory found; pass --media <path-to-mp4>"
    candidates = [
        p for p in sorted(out_dir.glob("*.mp4"))
        if not p.name.startswith("c_")
        and not p.name.endswith((".tmp.mp4", ".part.mp4", "_preview.mp4"))
        and p.name != "video_only.mp4"
    ]
    if len(candidates) == 1:
        return checked_path(candidates[0].resolve()), None
    if len(candidates) > 1:
        names = ", ".join(p.name for p in candidates)
        return None, f"Multiple candidate MP4 files in out/ ({names}); pass --media explicitly"
    if (out_dir / "video_only.mp4").is_file():
        return None, "Only out/video_only.mp4 exists (unmuxed picture); mux final audio or pass --media explicitly"
    return None, "No rendered master MP4 found in out/; pass --media <path-to-mp4>"


def _check_unapproved_chip(project: Path) -> str | None:
    scenes_py = project / "scenes.py"
    if not scenes_py.is_file():
        return None
    text = scenes_py.read_text(encoding="utf-8")
    matches = re.findall(r"^\s*CHIP\s*=\s*(.+?)\s*(?:#.*)?$", text, re.M)
    if not matches:
        return None
    rhs = matches[-1].strip()
    if rhs in ("None", "''", '""'):
        return None
    copy_path = project / "plan" / "copy.json"
    if copy_path.is_file():
        try:
            copy_doc = json.loads(copy_path.read_text(encoding="utf-8"))
            fragments = copy_doc.get("copy") or []
            if any(isinstance(f, dict) and f.get("approvedByUser") is True for f in fragments):
                return None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass
    return f"scenes.py sets CHIP={rhs}, but no copy.json entry carries approvedByUser=true (AGENTS.md Rule 1)"


def evaluate_stage(
    project_path: Path,
    *,
    stage: str = "plan",
    media: Path | None = None,
    layout_report: Path | None = None,
    require_layout: bool = False,
    min_mbps: float | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    if stage not in STAGE_RANK:
        raise ValueError(f"Unknown stage {stage!r}; choose from {', '.join(STAGES)}")
    project = _safe_abs(project_path, tree=True)
    rank = STAGE_RANK[stage]
    items: list[dict[str, str]] = []
    incomplete_reasons: list[str] = []

    def add(level: str, code: str, msg: str) -> None:
        items.append({"level": level, "code": code, "msg": msg})

    if not project.is_dir():
        add("error", "G01", f"Project directory does not exist: {project}")
        return {
            "version": 1, "stage": stage, "status": "fail", "project": str(project),
            "items": items, "errors": items, "warnings": [], "incomplete_reasons": [],
        }

    # ---------------- G01: Intake ----------------
    brief_path = project / "BRIEF.md"
    if not brief_path.is_file():
        add("error", "G01", "BRIEF.md is missing")
    else:
        brief_text = brief_path.read_text(encoding="utf-8")
        if "(1) ..." in brief_text and "(2) ..." in brief_text:
            add("error", "G01", "BRIEF.md still contains untouched script placeholders `(1) ...`")
        else:
            add("ok", "G01", "BRIEF.md present and filled")

    script_path = project / "plan" / "script.md"
    if not script_path.is_file():
        add("error", "G01", "plan/script.md is missing")
    else:
        script_text = script_path.read_text(encoding="utf-8")
        if "(paste the numbered beats here)" in script_text or not script_text.strip():
            add("error", "G01", "plan/script.md still contains template placeholder text")
        else:
            add("ok", "G01", "plan/script.md present and filled")

    vo_dir = project / "assets" / "vo"
    vo_sources = [
        p for p in (sorted(vo_dir.iterdir()) if vo_dir.is_dir() else [])
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in AUDIO_EXTS
    ]
    vo24 = project / "out" / "vo24.wav"
    if vo_sources or vo24.is_file():
        add("ok", "G01", f"VO input present ({vo24.name if vo24.is_file() else vo_sources[0].name})")
    else:
        add("error", "G01", "No VO audio found in assets/vo/ or out/vo24.wav")

    # ---------------- G02..G04: Plan ----------------
    vo_duration: float | None = None
    if rank >= STAGE_RANK["plan"]:
        if not vo24.is_file():
            add("error", "G02", "out/vo24.wav is missing (prepare mono 24 kHz PCM16 WAV from the VO)")
        else:
            try:
                with wave.open(str(vo24), "rb") as wf:
                    ch, sw, sr, nf = wf.getnchannels(), wf.getsampwidth(), wf.getframerate(), wf.getnframes()
                if (ch, sw, sr) != (1, 2, 24000) or nf <= 0:
                    add("error", "G02", f"out/vo24.wav must be mono 16-bit 24000 Hz PCM WAV, got ch={ch}, width={sw*8}b, rate={sr}, frames={nf}")
                else:
                    vo_duration = nf / float(sr)
                    add("ok", "G02", f"out/vo24.wav verified ({vo_duration:.3f}s mono 24 kHz PCM16)")
            except wave.Error as error:
                add("error", "G02", f"out/vo24.wav is not a readable PCM WAV: {error}")

        beats_path = project / "plan" / "beats.json"
        beats_doc: dict[str, Any] = {}
        if not beats_path.is_file():
            add("error", "G02", "plan/beats.json is missing")
        else:
            try:
                beats_doc = json.loads(beats_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as error:
                add("error", "G02", f"plan/beats.json invalid JSON: {error}")
            b_dur = beats_doc.get("duration") if isinstance(beats_doc, dict) else None
            if not isinstance(b_dur, (int, float)) or isinstance(b_dur, bool) or float(b_dur) <= 0:
                add("error", "G02", "plan/beats.json has no measured VO duration (run tools/vo_length.py)")
            elif vo_duration is not None and abs(float(b_dur) - vo_duration) > 0.055:
                add("error", "G02", f"plan/beats.json duration ({float(b_dur):.3f}s) disagrees with out/vo24.wav ({vo_duration:.3f}s)")
            else:
                add("ok", "G02", f"plan/beats.json locked ({float(b_dur):.3f}s, {len(beats_doc.get('scenes') or [])} scene(s))")

        if vo24.is_file() and vo_duration is not None:
            vo_chk = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "vo_length.py"), str(vo24), "--check", str(project)],
                cwd=str(ROOT), capture_output=True, text=True, check=False,
            )
            if vo_chk.returncode != 0:
                detail = (vo_chk.stdout + vo_chk.stderr).strip().splitlines()[-1:] or ["timeline mismatch"]
                add("error", "G02", f"vo_length --check failed: {detail[0]}")
            else:
                add("ok", "G02", "Scene timeline matches VO duration (vo_length --check)")

        has_word_timings = (
            (project / "plan" / "word-timings.json").is_file()
            or (project / "cache" / "scene-measurements.json").is_file()
        )
        if has_word_timings:
            try:
                asr_rep = asr_check.audit_asr(project)
                for err_item in asr_rep["errors"]:
                    add("error", "G02", f"asr_check [{err_item['code']}]: {err_item['msg']}")
                for warn_item in asr_rep["warnings"]:
                    add("warning", "G02", f"asr_check [{warn_item['code']}]: {warn_item['msg']}")
                if not asr_rep["errors"] and not asr_rep["warnings"]:
                    add("ok", "G02", f"ASR word timings verified ({asr_rep['word_count']} word(s))")
            except (OSError, ValueError, json.JSONDecodeError, wave.Error) as error:
                add("error", "G02", f"asr_check failed: {error}")

        # G03: Copy, text direction, visual direction, techniques
        copy_path = project / "plan" / "copy.json"
        copy_doc: dict[str, Any] | None = None
        if not copy_path.is_file():
            add("error", "G03", "plan/copy.json is missing")
        else:
            try:
                copy_doc = json.loads(copy_path.read_text(encoding="utf-8"))
                frags = copy_doc.get("copy") if isinstance(copy_doc, dict) else None
                if not isinstance(frags, list) or not frags:
                    add("error", "G03", "plan/copy.json has no on-screen copy fragments")
                else:
                    add("ok", "G03", f"plan/copy.json declares {len(frags)} fragment(s)")
            except json.JSONDecodeError as error:
                add("error", "G03", f"plan/copy.json invalid JSON: {error}")

        dir_doc = td.load(project)
        fonts_map = td.load_fonts(project) or None
        if isinstance(beats_doc, dict) and beats_doc.get("duration"):
            td_report = td.validate(dir_doc, beats_doc, copy_doc, fonts_map)
            if td_report["errors"]:
                add("error", "G03", f"plan/text-direction.json incomplete: {td_report['errors'][0]}")
            else:
                add("ok", "G03", "plan/text-direction.json validated for all scenes and roles")
        elif not (project / "plan" / "text-direction.json").is_file():
            add("error", "G03", "plan/text-direction.json is missing")

        vis_path = project / "plan" / "visual-direction.json"
        if vis_path.is_file():
            vd_report = vd.check_project(project)
            if vd_report["errors"]:
                add("error", "G03", f"plan/visual-direction.json invalid: {vd_report['errors'][0]}")
            else:
                add("ok", "G03", "plan/visual-direction.json validated against measured word anchors")

        tech_path = project / "plan" / "techniques.json"
        if not tech_path.is_file():
            add("error", "G03", "plan/techniques.json missing (draw moves with tools/techniques.py --draw)")
        else:
            try:
                tech_doc = json.loads(tech_path.read_text(encoding="utf-8"))
                drawn = (
                    (tech_doc.get("picks") or tech_doc.get("moves") or tech_doc.get("selected") or tech_doc.get("scenes"))
                    if isinstance(tech_doc, dict) else tech_doc
                )
                if not drawn:
                    add("error", "G03", "plan/techniques.json contains no drawn moves")
                else:
                    add("ok", "G03", "plan/techniques.json present")
            except json.JSONDecodeError as error:
                add("error", "G03", f"plan/techniques.json invalid JSON: {error}")

        # G04: Craft lint & brand guard
        lint_cmd = [sys.executable, str(ROOT / "tools" / "reel_lint.py"), str(project), "--scan-code"]
        if strict:
            lint_cmd.append("--strict")
        lint_res = subprocess.run(lint_cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
        if lint_res.returncode != 0:
            last_ln = (lint_res.stdout + lint_res.stderr).strip().splitlines()[-1:] or ["reel_lint failed"]
            add("error", "G04", f"reel_lint failed: {last_ln[0]}")
        else:
            add("ok", "G04", "reel_lint --scan-code passed")

        brand_res = subprocess.run(
            [sys.executable, str(SKILL / "scripts" / "brand_check.py"), "--project", str(project)],
            cwd=str(ROOT), capture_output=True, text=True, check=False,
        )
        if brand_res.returncode != 0 or "RESULT: PASS" not in brand_res.stdout:
            add("error", "G04", "brand_check.py reported palette/contrast drift")
        else:
            add("ok", "G04", "brand_check.py passed")

    # ---------------- G05: Render & Layout Audit ----------------
    resolved_media: Path | None = None
    if rank >= STAGE_RANK["render"]:
        resolved_media, media_err = _resolve_media(project, media)
        if media_err or resolved_media is None:
            add("error", "G05", media_err or "Rendered media missing")
        else:
            add("ok", "G05", f"Rendered media located: {resolved_media.name}")

        has_k_or_p = (project / "src" / "render.js").is_file() or (project / "scenes.py").is_file()
        if layout_report is not None:
            lr_raw = layout_report if layout_report.is_absolute() else (project / layout_report)
            lr_path = _safe_abs(lr_raw)
            if not lr_path.is_file():
                add("error", "G05", f"Layout audit report not found: {layout_report}")
            else:
                lr_doc = json.loads(lr_path.read_text(encoding="utf-8"))
                lr_status = lr_doc.get("status")
                rp_status = (lr_doc.get("replay") or {}).get("status", "not-requested")
                if lr_status != "pass" or rp_status == "fail":
                    add("error", "G05", f"Layout audit report status={lr_status!r}, replay={rp_status!r}")
                else:
                    add("ok", "G05", f"Layout audit report passed (replay: {rp_status})")
        elif require_layout:
            add("error", "G05", "Layout audit report required (--layout-report <report.json>)")
        elif has_k_or_p and rank >= STAGE_RANK["deliver"]:
            add("warn", "G05", "No --layout-report supplied for K/P project; run layout_audit.mjs or layout_audit_p.py")

    # ---------------- G06: Delivery Promise ----------------
    media_qa_summary: dict[str, Any] | None = None
    if rank >= STAGE_RANK["deliver"]:
        chip_problem = _check_unapproved_chip(project)
        if chip_problem:
            add("error", "G06", chip_problem)
        else:
            add("ok", "G06", "No unapproved series chip detected")

        externals = _external_project_assets(project)
        if externals:
            credits_texts: list[str] = []
            for credits_candidate in (project / "CREDITS.md", project / "assets" / "CREDITS.md", ROOT / "assets" / "CREDITS.md"):
                if credits_candidate.is_file():
                    credits_texts.append(credits_candidate.read_text(encoding="utf-8"))
            combined_credits = "\n".join(credits_texts)
            uncredited = [rel.as_posix() for rel in externals if rel.name not in combined_credits]
            if uncredited:
                add("error", "G06", f"External asset(s) missing licence entry in CREDITS.md: {', '.join(uncredited[:5])}")
            else:
                add("ok", "G06", f"All {len(externals)} external asset(s) attributed in CREDITS.md")
        else:
            add("ok", "G06", "Only studio-bundled assets and user VO/refs present")

        if resolved_media is not None:
            beats_file = project / "plan" / "beats.json"
            qa = media_qa.inspect_media(
                resolved_media,
                mode="master",
                vo_path=vo24 if vo24.is_file() else None,
                beats_path=beats_file if beats_file.is_file() else None,
                min_mbps=min_mbps,
                strict=strict,
            )
            media_qa_summary = {
                "status": qa["status"],
                "errors": qa["errors"],
                "warnings": qa["warnings"],
                "incomplete_reasons": qa.get("incomplete_reasons", []),
                "video": qa.get("video"),
                "audio": qa.get("audio"),
            }
            if qa["status"] == "pass":
                add("ok", "G06", "Final Media QA (master) passed")
            elif qa["status"] == "incomplete":
                for reason in qa.get("incomplete_reasons", []):
                    incomplete_reasons.append(f"media_qa: {reason}")
                add("warn", "G06", "Final Media QA could not complete all master measurements")
            else:
                for err in qa.get("errors", []):
                    add("error", "G06", f"media_qa {err['code']}: {err['msg']}")

    errors = [i for i in items if i["level"] == "error"]
    warnings = [i for i in items if i["level"] == "warn"]
    if errors or (strict and warnings):
        status = "fail"
    elif incomplete_reasons:
        status = "incomplete"
    else:
        status = "pass"

    digest, artifact_hashes = compute_artifact_digest(project, resolved_media)
    return {
        "version": 1,
        "stage": stage,
        "status": status,
        "strict": strict,
        "project": str(project),
        "media": str(resolved_media) if resolved_media else None,
        "artifact_digest": digest,
        "artifacts": artifact_hashes,
        "media_qa": media_qa_summary,
        "incomplete_reasons": incomplete_reasons,
        "items": items,
        "errors": errors,
        "warnings": warnings,
    }


def write_checkpoint(project: Path, report: dict[str, Any]) -> Path:
    cache_dir = checked_path(project / "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    ckpt_path = checked_path(cache_dir / "stage-gate.json")
    tmp_path = checked_path(cache_dir / f"stage-gate.{int(time.time() * 1000)}.tmp.json")
    payload = {
        "version": 1,
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "stage": report["stage"],
        "status": report["status"],
        "artifact_digest": report["artifact_digest"],
        "artifacts": report["artifacts"],
        "media": report["media"],
        "errors": report["errors"],
        "warnings": report["warnings"],
    }
    tmp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp_path.replace(ckpt_path)
    return ckpt_path


def verify_checkpoint(project_path: Path, required_stage: str) -> tuple[bool, str]:
    if required_stage not in STAGE_RANK:
        return False, f"Unknown stage: {required_stage}"
    project = _safe_abs(project_path, tree=True)
    ckpt_path = checked_path(project / "cache" / "stage-gate.json")
    if not ckpt_path.is_file():
        return False, f"No stage checkpoint found at {ckpt_path}"
    ckpt = json.loads(ckpt_path.read_text(encoding="utf-8"))
    if ckpt.get("status") != "pass":
        return False, f"Checkpoint status is {ckpt.get('status')!r}, not 'pass'"
    recorded_stage = ckpt.get("stage")
    if recorded_stage not in STAGE_RANK or STAGE_RANK[recorded_stage] < STAGE_RANK[required_stage]:
        return False, f"Checkpoint recorded stage {recorded_stage!r} is earlier than required {required_stage!r}"
    media_str = ckpt.get("media")
    media_path = Path(media_str) if isinstance(media_str, str) and media_str else None
    current_digest, _ = compute_artifact_digest(project, media_path)
    if current_digest != ckpt.get("artifact_digest"):
        return False, "STALE_CHECKPOINT: project plans, VO, or rendered media changed after checkpoint was written"
    return True, f"Checkpoint verified ({recorded_stage}, digest {current_digest[:12]})"


def render_human(report: dict[str, Any]) -> str:
    lines = [f"stage_gate · {report['stage'].upper()} · {report['status'].upper()} · {report['project']}"]
    for item in report.get("items", []):
        prefix = {"ok": "  OK  ", "warn": " WARN ", "error": " FAIL "}.get(item["level"], "      ")
        lines.append(f"{prefix}{item['code']}  {item['msg']}")
    for reason in report.get("incomplete_reasons", []):
        lines.append(f" INCOMPLETE  {reason}")
    lines.append(
        f"RESULT: {report['status'].upper()} — "
        f"{len(report.get('errors', []))} error(s), {len(report.get('warnings', []))} warning(s)"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="project root directory")
    parser.add_argument("--stage", choices=STAGES, default="plan")
    parser.add_argument("--media", type=Path, default=None, help="rendered MP4 path (for render/deliver stages)")
    parser.add_argument("--layout-report", type=Path, default=None, help="report.json from layout_audit.mjs or layout_audit_p.py")
    parser.add_argument("--require-layout", action="store_true", help="require a passing --layout-report at render/deliver")
    parser.add_argument("--min-mbps", type=float, default=None, help="override master bitrate floor in deliver stage")
    parser.add_argument("--write-checkpoint", action="store_true", help="record stage checkpoint in <project>/cache/stage-gate.json")
    parser.add_argument("--verify-checkpoint", choices=STAGES, default=None, help="verify existing checkpoint is fresh and >= stage")
    parser.add_argument("--json", dest="json_out", type=Path, default=None, help="write full gate report to a fresh path")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.verify_checkpoint is not None:
            ok, msg = verify_checkpoint(args.project, args.verify_checkpoint)
            print(msg, file=sys.stdout if ok else sys.stderr)
            return 0 if ok else 1

        json_out = _safe_abs(args.json_out) if args.json_out else None
        if json_out is not None and json_out.exists():
            print(f"stage_gate blocked: refusing to overwrite existing report: {json_out}", file=sys.stderr)
            return 2

        report = evaluate_stage(
            args.project,
            stage=args.stage,
            media=args.media,
            layout_report=args.layout_report,
            require_layout=args.require_layout,
            min_mbps=args.min_mbps,
            strict=args.strict,
        )
        if args.write_checkpoint:
            ckpt = write_checkpoint(_safe_abs(args.project, tree=True), report)
            report["checkpoint"] = str(ckpt)
        if json_out is not None:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            with json_out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        print(render_human(report))
        return 0 if report["status"] == "pass" else 1
    except ValueError as error:
        print(f"stage_gate blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
