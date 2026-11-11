#!/usr/bin/env python3
"""Deterministic render pipeline for a reel project — no creative decisions, ever.

    python3 tools/pipeline.py projects/my-reel                 # full run: vo -> gate
    python3 tools/pipeline.py .                                # cwd is the project
    python3 tools/pipeline.py P --engine p                     # skip auto-detection
    python3 tools/pipeline.py P --from mix                     # resume after a failure
    python3 tools/pipeline.py P --dry-run                      # print plan, run nothing
    python3 tools/pipeline.py K --draft                        # preview: 540x960 @15fps -> out/draft.mp4
    python3 tools/pipeline.py K --scene-cache                  # re-render only the scenes that changed

Steps (fail-fast; each timed; nothing is overwritten silently):

    vo     tools/vo_length.py <project> --check
    lint   tools/reel_lint.py <project> --scan-code
    brand  medo-motion/scripts/brand_check.py --project <project>
    mix    tools/audio_mix.py --sheet <cues> --vo out/vo24.wav --out out/final_audio.wav
           (an existing out/final_audio.wav is kept only while out/final_audio.mix.json still
           matches the VO + cue sheet; STALE fails until --remix or --keep-mix; SKIP when no cue sheet)
    render engine dispatch (p: run_all.py · k: render.js --crf 13 · r: Remotion · hybrid)
    mux    engine P only: ffmpeg mux video_only + final_audio -> out/master.mp4
    qa     tools/media_qa.py <master> --mode master|video-only --vo out/vo24.wav --beats plan/beats.json
    gate   tools/stage_gate.py <project> --stage deliver --media <master> [--layout-report PATH]

Every run writes <project>/cache/pipeline-timings.json (per-step ms + total), so the
numbers decide whether a real runner (with human stops) is worth building.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
TOOLKIT = ROOT / "tools" / "toolkit"
sys.path.insert(0, str(ROOT / "tools" / "lib"))

from media_bin import ffmpeg as _ffmpeg  # noqa: E402 - path set above
from media_bin import ffprobe as _ffprobe  # noqa: E402 - path set above

STEPS = ("vo", "lint", "brand", "mix", "render", "mux", "qa", "gate")


def detect_engine(project: Path) -> str | None:
    """Replicate the scaffold layout: hybrid carries all three engines + plan/hybrid.json."""
    if (project / "plan" / "hybrid.json").is_file():
        return "hybrid"
    pkg = project / "package.json"
    if (project / "scripts" / "render.mjs").is_file() and pkg.is_file() \
            and '"remotion"' in pkg.read_text(encoding="utf-8"):
        return "r"
    if (project / "run_all.py").is_file() and (project / "scenes.py").is_file():
        return "p"
    if (project / "src" / "render.js").is_file() and pkg.is_file():
        return "k"
    return None


class PipelineError(Exception):
    pass


def run_cmd(cmd, cwd: Path, env=None, timeout: int = 1800, log: Path | None = None) -> int:
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    with (log.open("a", encoding="utf-8") if log else open(os.devnull, "w")) as sink:
        proc = subprocess.run(cmd, cwd=cwd, env=env, stdout=sink, stderr=subprocess.STDOUT,
                              text=True, timeout=timeout)
    return proc.returncode


def tail(path: Path, lines: int = 25) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8").splitlines()[-lines:])
    except OSError:
        return ""


def step_vo(project: Path, ctx) -> tuple[int, str]:
    return run_cmd([sys.executable, str(ROOT / "tools" / "vo_length.py"), str(project), "--check"], project, log=ctx.log), "vo vs beats in sync"


def step_lint(project: Path, ctx) -> tuple[int, str]:
    return run_cmd([sys.executable, str(ROOT / "tools" / "reel_lint.py"), str(project), "--scan-code"], project, log=ctx.log), "lint clean"


def step_brand(project: Path, ctx) -> tuple[int, str]:
    return run_cmd([sys.executable, str(SKILL / "scripts" / "brand_check.py"), "--project", str(project)], project, log=ctx.log), "brand clean"


def _cue_sheet(project: Path, override: Path | None) -> Path | None:
    if override is not None:
        return override if override.is_file() else None
    candidate = project / "plan" / "cues.json"
    return candidate if candidate.is_file() else None


# --- mix freshness -------------------------------------------------------------------------
#
# `out/final_audio.wav` used to be kept whenever it existed, so a re-recorded VO or an edited cue
# sheet shipped with the previous mix. The mix step now writes `out/final_audio.mix.json` next to
# the WAV — a hash of everything the mix was made from, and of the WAV itself — and an existing
# mix is kept only while that record still matches.
MIX_RECORD_VERSION = 1
MIX_CODE = (  # music and SFX are generated, not sampled: these files *are* the music/SFX used
    ROOT / "tools" / "audio_mix.py",
    ROOT / "shared" / "py" / "audio_mix.py",
    ROOT / "shared" / "py" / "audio_engine.py",
    ROOT / "shared" / "py" / "music.py",
    ROOT / "shared" / "py" / "sfx.py",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def _sheet_hash(sheet: Path) -> str:
    """Hash the cue sheet's *values*: reformatting the JSON is not a different mix."""
    try:
        document = json.loads(sheet.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _sha256(sheet)
    canonical = json.dumps(document, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def mix_inputs(project: Path, sheet: Path, ctx) -> dict[str, str]:
    """Label -> hash for every input of the mix: voice, cue sheet (music, SFX cues, ducking, master
    LUFS/true peak live in it), the generators, and whether ffmpeg's loudnorm masters it."""
    vo = project / "out" / "vo24.wav"
    try:
        sheet_label = sheet.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        sheet_label = str(sheet)
    inputs = {
        "out/vo24.wav": _sha256(vo) if vo.is_file() else "missing",
        f"cue sheet ({sheet_label})": _sheet_hash(sheet),
        "master (ffmpeg loudnorm available)": "yes" if ctx.ffmpeg else "no",
    }
    for path in MIX_CODE:
        inputs[f"mix code ({path.name if path.parent.name != 'tools' else 'tools/' + path.name})"] = (
            _sha256(path) if path.is_file() else "missing")
    return inputs


def _mix_record(out_wav: Path) -> Path:
    return out_wav.with_name(out_wav.stem + ".mix.json")


def _write_mix_record(out_wav: Path, inputs: dict[str, str], accepted_by: str) -> None:
    record = {"version": MIX_RECORD_VERSION, "accepted_by": accepted_by, "inputs": inputs,
              "output": {"file": out_wav.name, "sha256": _sha256(out_wav)}}
    target = _mix_record(out_wav)
    tmp = target.with_name(target.name + ".tmp")
    tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, target)


def mix_staleness(out_wav: Path, inputs: dict[str, str]) -> list[str]:
    """Why the existing mix cannot be trusted — an empty list means it still matches its record."""
    record_path = _mix_record(out_wav)
    if not record_path.is_file():
        return [f"no record of what it was mixed from ({record_path.name} is missing)"]
    try:
        record = json.loads(record_path.read_text(encoding="utf-8"))
        recorded, output = record["inputs"], record["output"]["sha256"]
        if record.get("version") != MIX_RECORD_VERSION or not isinstance(recorded, dict):
            raise ValueError("version")
    except (OSError, ValueError, KeyError, TypeError):
        return [f"{record_path.name} is unreadable or from another version"]
    reasons = [f"{label} changed" for label in sorted(set(recorded) | set(inputs))
               if recorded.get(label) != inputs.get(label)]
    if _sha256(out_wav) != output:
        reasons.append(f"{out_wav.name} itself was replaced after it was mixed")
    return reasons


def step_mix(project: Path, ctx) -> tuple[int, str]:
    out_wav = project / "out" / "final_audio.wav"
    sheet = _cue_sheet(project, ctx.mix_sheet)
    remix = False
    if out_wav.is_file():
        if sheet is None:
            return 0, ("out/final_audio.wav already exists — kept as-is (no cue sheet: an external mix, "
                       "not checked against the VO)")
        inputs = mix_inputs(project, sheet, ctx)
        reasons = mix_staleness(out_wav, inputs)
        if not reasons:
            return 0, "out/final_audio.wav already exists and matches its VO + cue sheet — kept"
        why = "; ".join(reasons)
        if getattr(ctx, "keep_mix", False):
            _write_mix_record(out_wav, inputs, "--keep-mix")
            return 0, f"out/final_audio.wav kept by --keep-mix although STALE ({why}) — recorded as accepted"
        if not getattr(ctx, "remix", False):
            return 1, (f"out/final_audio.wav is STALE: {why}. Nothing was changed. Rebuild it with --remix "
                       "(overwrites the WAV), or accept it as it is with --keep-mix")
        remix = True
    if sheet is None:
        ctx.skipped.add("mix")
        return 0, "no plan/cues.json — mix step SKIPPED (build the cue sheet first)"
    inputs = mix_inputs(project, sheet, ctx)
    cmd = [sys.executable, str(ROOT / "tools" / "audio_mix.py"), "--sheet", str(sheet),
           "--vo", str(project / "out" / "vo24.wav"), "--out", str(out_wav)]
    if remix:
        cmd.append("--force")
    code = run_cmd(cmd, project, log=ctx.log)
    if code != 0 or not out_wav.is_file():
        return code or 1, "mix failed (see cache/pipeline.log)"
    _write_mix_record(out_wav, inputs, "mixed")
    return 0, ("re-mixed (the previous mix was stale) -> out/final_audio.wav" if remix
               else "mixed -> out/final_audio.wav")


def _beats_duration_seconds(project: Path) -> float:
    beats = json.loads((project / "plan" / "beats.json").read_text(encoding="utf-8"))
    frames = int(beats.get("frames") or 0)
    fps = float(beats.get("fps") or 30)
    return (frames / fps) if frames > 0 else float(beats.get("duration") or 0.0)


def step_render(project: Path, ctx) -> tuple[int, str]:
    if ctx.engine == "p" and ctx.draft:
        # Half the frames, half the canvas: run_all renders every other source frame at 540x960
        # and writes out/draft.mp4, leaving out/video_only.mp4 (and its chunks) untouched.
        env = {**os.environ, "REEL_DIR": str(project), "REEL_DRAFT": "1"}
        if ctx.ffmpeg:
            env["FFMPEG_BIN"] = ctx.ffmpeg
        if ctx.ffprobe:
            env["FFPROBE_BIN"] = ctx.ffprobe
        code = run_cmd([sys.executable, str(project / "run_all.py")], project, env=env,
                       timeout=7200, log=ctx.log)
        if code != 0:
            return code, "draft render failed (see out_log-draft.txt)"
        preview = project / "out" / "draft.mp4"
        if not preview.is_file():
            return 1, "draft render produced no out/draft.mp4"
        return 0, "draft -> out/draft.mp4 (540x960 @15fps)"
    if ctx.engine == "p":
        env = {**os.environ, "REEL_DIR": str(project)}
        if ctx.ffmpeg:
            env["FFMPEG_BIN"] = ctx.ffmpeg
        if ctx.ffprobe:
            env["FFPROBE_BIN"] = ctx.ffprobe
        return run_cmd([sys.executable, str(project / "run_all.py")], project, env=env,
                       timeout=7200, log=ctx.log), "chunks encoded -> out/video_only.mp4"
    if ctx.engine == "k" and ctx.scene_cache:
        # Per-scene cache: each scene is encoded once and reused until its own module changes.
        cmd = [sys.executable, str(ROOT / "tools" / "render_scenes.py"), str(project),
               "--out", str(project / "out" / "master.mp4")]
        code = run_cmd(cmd, project, timeout=7200, log=ctx.log)
        if code != 0:
            return code, "scene cache render failed (see cache/scenes.log)"
        return 0, "scene-cached scenes -> out/master.mp4"
    if ctx.engine == "k" and ctx.draft:
        # Preview render: half resolution and half the frame rate — a review copy, never a master.
        dur = _beats_duration_seconds(project)
        cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
               f'node src/render.js --from 0 --to {dur:.6f} --fps 15 --scale 0.5 --crf 30 '
               f'--out out --name Draft')
        if run_cmd(["bash", "-c", cmd], project, env=os.environ.copy(), timeout=7200, log=ctx.log) != 0:
            return 1, "draft render failed"
        produced = project / "out" / "Draft.mp4"
        if not produced.is_file():
            return 1, "draft render produced no out/Draft.mp4"
        os.replace(produced, project / "out" / "draft.mp4")
        return 0, "draft -> out/draft.mp4 (540x960 @15fps)"
    if ctx.engine == "k":
        dur = _beats_duration_seconds(project)
        audio = project / "out" / "final_audio.wav"
        audio_arg = " --audio out/final_audio.wav" if audio.is_file() else ""
        if not audio.is_file():
            print("    ! out/final_audio.wav missing — rendering a SILENT picture; QA will use --mode video-only")
        cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
               f'node src/render.js --from 0 --to {dur:.6f} --fps 30 --scale 1 --crf 13 '
               f'--out out --name Master{audio_arg}')
        rc = run_cmd(["bash", "-c", cmd], project, env=os.environ.copy(), timeout=7200, log=ctx.log)
        if rc != 0:
            return rc, "K render failed"
        produced = project / "out" / "Master.mp4"
        target = project / "out" / "master.mp4"
        if produced.is_file():
            if target.exists():
                ctx.timings_note.append("out/master.mp4 exists — kept; K render is in out/Master.mp4")
            else:
                produced.replace(target)
        return 0, "K frames -> out/master.mp4"
    if ctx.engine == "r":
        npm = shutil.which("npm")
        if not npm:
            return 1, "npm not found"
        if not (project / "node_modules").is_dir():
            if run_cmd([npm, "ci"], project, log=ctx.log) != 0:
                return 1, "npm ci failed"
        # R canonically muxes the measured VO (its render gate enforces VO timing); fold any
        # music/SFX mix into the VO upstream as one WAV, or render with the VO and mix later.
        return run_cmd([npm, "run", "render", "--", "--audio", str(project / "out" / "vo24.wav"),
                        "--out", "out/master.mp4"], project, timeout=3600, log=ctx.log), "Remotion render -> out/master.mp4"
    if ctx.engine == "hybrid":
        if not ctx.ffmpeg or not ctx.ffprobe:
            return 1, "ffmpeg/ffprobe not found"
        node = shutil.which("node")
        if not node:
            return 1, "node not found"
        probe = subprocess.run([node, str(ROOT / "tools" / "chromium.mjs"), "--json"],
                               capture_output=True, text=True, timeout=180)
        if probe.returncode:
            return 1, f"chromium.mjs --json failed: {probe.stdout}{probe.stderr}"
        browser = json.loads(probe.stdout)
        env = {**os.environ, "MEDO_TOOLKIT": str(TOOLKIT), "MEDO_CHROMIUM": browser["executablePath"],
               "FFMPEG_BIN": ctx.ffmpeg, "FFPROBE_BIN": ctx.ffprobe, "PYTHONUNBUFFERED": "1"}
        if browser.get("libraryPath"):
            env["LD_LIBRARY_PATH"] = str(browser["libraryPath"]) + ":" + env.get("LD_LIBRARY_PATH", "")
        command = [sys.executable, str(ROOT / "tools" / "render_hybrid.py"), "--project", str(project),
                   "--ffmpeg", ctx.ffmpeg, "--ffprobe", ctx.ffprobe]
        if ctx.draft:
            command.append("--draft")
        code = run_cmd(command, project, env=env, timeout=7200, log=ctx.log)
        if not ctx.draft:
            return code, "hybrid segments -> out/hybrid.mp4"
        preview = project / "out" / "hybrid-draft.mp4"
        if code != 0:
            return code, "draft render failed (see the hybrid log)"
        if not preview.is_file():
            return 1, "draft render produced no out/hybrid-draft.mp4"
        return 0, "draft -> out/hybrid-draft.mp4 (540x960 @15fps)"
    return 1, f"unknown engine: {ctx.engine}"


def step_mux(project: Path, ctx) -> tuple[int, str]:
    if ctx.engine != "p":
        return 0, "engine handles its own mux — SKIPPED"
    video = project / "out" / "video_only.mp4"
    audio = project / "out" / "final_audio.wav"
    target = project / "out" / "master.mp4"
    if not video.is_file():
        return 1, "out/video_only.mp4 missing — P render did not produce a picture"
    if not audio.is_file():
        print("    ! out/final_audio.wav missing — master will be the SILENT picture; QA runs --mode video-only")
        return 0, "no audio to mux — video-only master"
    if target.exists():
        print("    ! out/master.mp4 exists — kept as-is (mux not re-run)")
        return 0, "out/master.mp4 already exists — kept"
    if not ctx.ffmpeg:
        return 1, "ffmpeg not found"
    cmd = [ctx.ffmpeg, "-y", "-i", str(video), "-i", str(audio), "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(target)]
    return run_cmd(cmd, project, log=ctx.log), "muxed -> out/master.mp4"


def _master(project: Path, engine: str) -> Path:
    return project / "out" / ("hybrid.mp4" if engine == "hybrid" else "master.mp4")


def step_qa(project: Path, ctx) -> tuple[int, str]:
    master = _master(project, ctx.engine)
    if not master.is_file():
        if ctx.engine == "p" and (project / "out" / "video_only.mp4").is_file():
            # silent P render: honest video-only QA, loudly labelled — never a delivery verdict
            master = project / "out" / "video_only.mp4"
            print("    ! no muxed master — QA runs --mode video-only on out/video_only.mp4 "
                  "(delivery gate will still require audio)")
            return run_cmd([sys.executable, str(ROOT / "tools" / "media_qa.py"), str(master),
                            "--mode", "video-only"], project, log=ctx.log), "media QA (video-only) on video_only.mp4"
        return 1, f"master {master.name} missing"
    has_audio = (project / "out" / "final_audio.wav").is_file() or ctx.engine in {"r", "hybrid"}
    mode = "master" if has_audio else "video-only"
    if not has_audio:
        print("    ! no audio present — QA runs --mode video-only (master WILL NOT pass delivery QA)")
    cmd = [sys.executable, str(ROOT / "tools" / "media_qa.py"), str(master), "--mode", mode]
    if mode == "master":
        cmd += ["--vo", str(project / "out" / "vo24.wav"), "--beats", str(project / "plan" / "beats.json")]
    return run_cmd(cmd, project, log=ctx.log), f"media QA ({mode}) on {master.name}"


def step_gate(project: Path, ctx) -> tuple[int, str]:
    master = _master(project, ctx.engine)
    cmd = [sys.executable, str(ROOT / "tools" / "stage_gate.py"), str(project),
           "--stage", "deliver", "--media", str(master)]
    if ctx.layout_report is not None:
        cmd += ["--layout-report", str(ctx.layout_report)]
    return run_cmd(cmd, project, log=ctx.log), "stage gate: deliver"


STEP_FNS = {"vo": step_vo, "lint": step_lint, "brand": step_brand, "mix": step_mix,
            "render": step_render, "mux": step_mux, "qa": step_qa, "gate": step_gate}


class Ctx:
    def __init__(self, engine: str, ffmpeg, ffprobe, mix_sheet, layout_report, log, draft: bool = False,
                 scene_cache: bool = False):
        self.engine = engine
        self.draft = draft
        self.scene_cache = scene_cache
        self.remix = False
        self.keep_mix = False
        self.ffmpeg = ffmpeg
        self.ffprobe = ffprobe
        self.mix_sheet = mix_sheet
        self.layout_report = layout_report
        self.log = log
        self.skipped: set[str] = set()
        self.timings_note: list[str] = []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", nargs="?", default=".", help="reel project directory (default: cwd)")
    parser.add_argument("--engine", choices=("p", "k", "r", "hybrid"), help="override auto-detection")
    parser.add_argument("--from", dest="start", choices=STEPS, help="resume from this step")
    parser.add_argument("--steps", help="comma-separated subset of: " + ",".join(STEPS))
    parser.add_argument("--mix-sheet", type=Path, help="cue sheet for the mix step (default: plan/cues.json)")
    stale = parser.add_mutually_exclusive_group()
    stale.add_argument("--remix", action="store_true",
                       help="mix step: rebuild out/final_audio.wav when it no longer matches its VO/cue sheet")
    stale.add_argument("--keep-mix", action="store_true",
                       help="mix step: keep a stale out/final_audio.wav on purpose and record that decision")
    parser.add_argument("--layout-report", type=Path, help="layout audit report.json for the deliver gate")
    parser.add_argument("--scene-cache", action="store_true",
                        help="engine K: render each scene once into cache/scenes and reuse unchanged ones")
    parser.add_argument("--draft", action="store_true",
                        help="preview render at 540x960 / 15fps -> out/draft.mp4 (engines P and K)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan, run nothing")
    args = parser.parse_args()

    project = Path(args.project).resolve()
    if not project.is_dir():
        print(f"pipeline: project not a directory: {project}", file=sys.stderr)
        return 2
    engine = args.engine or detect_engine(project)
    if engine is None:
        print("pipeline: cannot detect the engine (expected plan/hybrid.json, scripts/render.mjs + remotion "
              "in package.json, run_all.py + scenes.py, or src/render.js + package.json).\n"
              "Pass --engine explicitly.", file=sys.stderr)
        return 2

    if args.scene_cache and args.draft:
        print("pipeline: --scene-cache renders final-quality scenes; --draft renders one preview clip. "
              "Pick one.", file=sys.stderr)
        return 2
    if args.scene_cache and engine != "k":
        print("pipeline: --scene-cache is available for engine K only (its renderer takes absolute "
              "frame ranges per scene; P caches whole chunks, and R renders ranges but has one "
              "composition for every scene, so a per-scene key could never hit)", file=sys.stderr)
        return 2
    if args.draft and engine not in {"k", "p", "hybrid"}:
        print("pipeline: --draft is available for engines P, K and hybrid (whose base segments must "
              "be P or K). R/Remotion has no half-resolution path, and rendering at full quality "
              "then calling it a draft would lie.\nRun the normal pipeline for this engine, or "
              "preview a P/K segment alone.", file=sys.stderr)
        return 2

    if args.steps:
        chosen = [s.strip() for s in args.steps.split(",") if s.strip()]
        bad = [s for s in chosen if s not in STEPS]
        if bad:
            print(f"pipeline: unknown steps: {', '.join(bad)} (known: {', '.join(STEPS)})", file=sys.stderr)
            return 2
        steps = tuple(dict.fromkeys(chosen))
    else:
        steps = tuple(STEPS)
    if args.start:
        steps = tuple(s for s in steps if STEPS.index(s) >= STEPS.index(args.start))
    if args.draft:
        # A draft has no master to mux, QA against, or gate: only the preview picture is meaningful.
        steps = tuple(s for s in steps if s == "render")
        if not steps:
            print("pipeline: --draft only renders; drop --from/--steps that exclude 'render'", file=sys.stderr)
            return 2

    started = time.perf_counter()
    log = project / "cache" / "pipeline.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(f"# pipeline {time.strftime('%Y-%m-%dT%H:%M:%S')} engine={engine} steps={','.join(steps)}\n",
                   encoding="utf-8")
    ctx = Ctx(engine, _ffmpeg(), _ffprobe(), args.mix_sheet, args.layout_report, log,
              draft=args.draft, scene_cache=args.scene_cache)
    ctx.remix, ctx.keep_mix = args.remix, args.keep_mix

    print(f"Pipeline · {project} · engine={engine} · steps={','.join(steps)}")
    if args.draft:
        preview_name = "out/hybrid-draft.mp4" if engine == "hybrid" else "out/draft.mp4"
        print(f"DRAFT · 540x960 @15fps · {preview_name} · review copy, never a master")
    if args.scene_cache:
        print("SCENE CACHE · cache/scenes/<scene>-<hash>.mp4 · only edited scenes re-render")
    if args.dry_run:
        print("dry-run — commands would be logged to cache/pipeline.log; nothing executed")
        return 0

    results: list[dict] = []
    ok_all = True
    for name in steps:
        t0 = time.perf_counter()
        try:
            code, note = STEP_FNS[name](project, ctx)
        except subprocess.TimeoutExpired as error:
            code, note = 1, f"timed out after {error.timeout}s"
        ms = int((time.perf_counter() - t0) * 1000)
        state = "PASS" if code == 0 else "FAIL"
        results.append({"step": name, "status": state, "ms": ms, "note": note})
        print(f"  {name:<7}{state:<6}{ms / 1000:8.2f}s  {note}")
        if code != 0:
            ok_all = False
            print(f"\nPIPELINE FAILED at step '{name}'. Last log lines:\n{tail(log)}")
            break

    total_ms = int((time.perf_counter() - started) * 1000)
    report = {"version": 1, "engine": engine, "project": str(project),
              "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
              "steps": results, "skipped": sorted(ctx.skipped), "notes": ctx.timings_note,
              "total_ms": total_ms, "ok": ok_all}
    timings = project / "cache" / "pipeline-timings.json"
    timings.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n{'PIPELINE OK' if ok_all else 'PIPELINE FAILED'} · total {total_ms / 1000:.1f}s · timings -> {timings}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
