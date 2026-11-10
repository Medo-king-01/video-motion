#!/usr/bin/env python3
"""Render a frame-accurate hybrid P/K/R reel from plan/hybrid.json.

Segments are sequential. Each segment is rendered by one engine, or — since
version 2 — by one opaque base engine plus one transparent Engine-K overlay:
Engine K renders a PNG sequence with alpha and FFmpeg composites it over the
base. Audio is added once, after video assembly, so there is one continuous
soundtrack across all segments.

    {
      "version": 2,
      "duration_frames": 90,
      "segments": [
        {"id": "intro", "start_frame": 0, "end_frame": 60,
         "layers": [{"engine": "p"}, {"engine": "k", "alpha": true}]},
        {"id": "outro", "start_frame": 60, "end_frame": 90, "engine": "r"}
      ]
    }

A v2 overlay may also carry a static `mask`: white areas of the mask keep the
base frame, so Engine-K type can pass *behind* a P presenter instead of over it.

      {"engine": "k", "alpha": true,
       "mask": {"type": "rect", "x": 0.34, "y": 0.42, "w": 0.32, "h": 0.58, "feather": 8}}

    {"engine": "k", "alpha": true, "mask": {"type": "image", "path": "assets/presenter-matte.png"}}

Version 1 (`"engine": "p"` per segment) is still accepted and normalised to a
one-layer segment.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
# What this renderer actually enforces, as one explicit list.
#
# The operating contract (`AGENTS.md`) and the contract copied into every hybrid project
# (`medo-motion/templates/HYBRID.md`) describe each of these next to its marker:
#
#     <!-- CAP:alpha_layer -->
#
# `tests/test_capability_contract.py` compares the three sets and fails in both directions:
# a capability implemented here but undocumented dies in a contract nobody reads, and a
# documented capability that no longer exists sends agents down a dead path. Adding a feature
# therefore means adding it here and in both contracts — that is the point.
CAPABILITIES = frozenset({
    "sequence",            # v1: one engine owns a whole half-open frame range
    "layers",              # v2: a segment carries layers = opaque base + overlay
    "alpha_layer",         # that overlay is Engine K rendered transparent and composited
    "single_overlay",      # at most one overlay above the base
    "alpha_k_only",        # alpha is Engine-K only; an alpha base is rejected
    "overlay_masking",     # v2.1: a static mask hands pixels of the overlay back to the base
    "mask_rect",           # that mask may be a fractional, feathered rectangle
    "mask_image",          # ...or a 1080x1920 matte image inside the project
    "v1_normalised",       # v1 plans are normalised to layers on read, never rejected
    "audio_after_picture", # the soundtrack is added once, after picture assembly
    "frame_exact",         # dimensions/fps/frame counts/duration are verified, not hoped for
})

FPS = 30
WIDTH = 1080
HEIGHT = 1920
ENGINES = {"p", "k", "r"}


class PlanError(ValueError):
    """Invalid hybrid timeline or contract."""


def validate_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("version") not in (1, 2):
        raise PlanError("plan version must be 1 or 2")
    if raw.get("fps", FPS) != FPS:
        raise PlanError(f"frame rate is locked at {FPS} fps")
    if raw.get("width", WIDTH) != WIDTH or raw.get("height", HEIGHT) != HEIGHT:
        raise PlanError(f"canvas is locked at {WIDTH}x{HEIGHT}")
    total = raw.get("duration_frames")
    if isinstance(total, bool) or not isinstance(total, int) or total <= 0:
        raise PlanError("duration_frames must be a positive integer")
    segments = raw.get("segments")
    if not isinstance(segments, list) or not segments:
        raise PlanError("segments must be a non-empty array")
    cursor = 0
    ids: set[str] = set()
    clean: list[dict[str, Any]] = []
    for i, item in enumerate(segments, 1):
        if not isinstance(item, dict):
            raise PlanError(f"segment {i} must be an object")
        sid = item.get("id")
        start, end = item.get("start_frame"), item.get("end_frame")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sid):
            raise PlanError(f"segment {i} id must contain only letters, digits, _ or -")
        if sid in ids:
            raise PlanError(f"duplicate segment id: {sid}")
        ids.add(sid)
        layers = _validate_layers(item, sid)
        if isinstance(start, bool) or not isinstance(start, int) or isinstance(end, bool) or not isinstance(end, int):
            raise PlanError(f"segment {sid}: start_frame/end_frame must be integer frame indexes")
        if start != cursor:
            raise PlanError(f"segment {sid} starts at frame {start}; expected {cursor} (gap or overlap)")
        if end <= start:
            raise PlanError(f"segment {sid} must contain at least one frame")
        cursor = end
        clean.append({"id": sid, "start_frame": start, "end_frame": end,
                      "engine": layers[0]["engine"], "layers": layers})
    if cursor != total:
        raise PlanError(f"segments end at frame {cursor}; duration_frames is {total}")
    audio = raw.get("audio")
    if audio is not None:
        if not isinstance(audio, str) or not audio.strip():
            raise PlanError("audio must be a project-relative file path or null")
        audio_parts = Path(audio).parts
        if Path(audio).is_absolute() or ".." in audio_parts:
            raise PlanError("audio path must stay inside the project")
    return {"version": 2, "fps": FPS, "width": WIDTH, "height": HEIGHT,
            "duration_frames": total, "segments": clean, "audio": audio}


def _validate_layers(item: dict[str, Any], sid: str) -> list[dict[str, Any]]:
    """One opaque base (p/k/r), optionally one transparent Engine-K overlay on top."""
    raw_layers = item.get("layers")
    if raw_layers is None:
        engine = item.get("engine")
        if not isinstance(engine, str) or engine not in ENGINES:
            raise PlanError(f"segment {sid}: engine must be p, k, or r")
        return [{"engine": engine, "alpha": False}]
    if item.get("engine") is not None:
        raise PlanError(f"segment {sid}: use either engine or layers, not both")
    if not isinstance(raw_layers, list) or not 1 <= len(raw_layers) <= 2:
        raise PlanError(f"segment {sid}: layers must contain one base and at most one overlay")
    clean: list[dict[str, Any]] = []
    for position, layer in enumerate(raw_layers):
        if not isinstance(layer, dict):
            raise PlanError(f"segment {sid}: every layer must be an object")
        engine = layer.get("engine")
        if not isinstance(engine, str) or engine not in ENGINES:
            raise PlanError(f"segment {sid}: layer engine must be p, k, or r")
        alpha = layer.get("alpha", False)
        if not isinstance(alpha, bool):
            raise PlanError(f"segment {sid}: layer alpha must be a boolean")
        if position == 0 and alpha:
            raise PlanError(f"segment {sid}: the base layer cannot be transparent")
        if position > 0 and not alpha:
            raise PlanError(f"segment {sid}: only a transparent Engine-K overlay may follow the base")
        if alpha and engine != "k":
            raise PlanError(f"segment {sid}: transparent overlays are Engine K only")
        entry = {"engine": engine, "alpha": alpha}
        mask = _validate_mask(layer, sid, position, alpha)
        if mask is not None:
            entry["mask"] = mask
        clean.append(entry)
    return clean


MASK_KINDS = ("rect", "image")
MASK_FEATHER_MAX = 120.0


def _validate_mask(layer: dict[str, Any], sid: str, position: int, alpha: bool) -> dict[str, Any] | None:
    """A static matte where white keeps the base: Engine-K type can sit behind a presenter.

    Only a transparent overlay can be masked — a mask on an opaque base would mean nothing, and
    accepting it silently would make the plan lie about what the renderer does.
    """
    raw = layer.get("mask")
    if raw is None:
        return None
    if position == 0 or not alpha:
        raise PlanError(f"segment {sid}: only a transparent overlay can carry a mask")
    if not isinstance(raw, dict):
        raise PlanError(f"segment {sid}: mask must be an object")
    kind = raw.get("type")
    if kind not in MASK_KINDS:
        raise PlanError(f"segment {sid}: mask type must be rect or image")
    if kind == "rect":
        box: dict[str, float] = {}
        for key in ("x", "y", "w", "h"):
            value = raw.get(key)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise PlanError(f"segment {sid}: mask {key} must be a number between 0 and 1")
            if not 0.0 <= float(value) <= 1.0:
                raise PlanError(f"segment {sid}: mask {key} must be between 0 and 1")
            box[key] = float(value)
        if box["w"] <= 0 or box["h"] <= 0:
            raise PlanError(f"segment {sid}: mask width and height must be positive")
        if box["x"] + box["w"] > 1.0 + 1e-9 or box["y"] + box["h"] > 1.0 + 1e-9:
            raise PlanError(f"segment {sid}: mask rectangle must stay inside the canvas")
        feather = raw.get("feather", 0)
        if isinstance(feather, bool) or not isinstance(feather, (int, float)):
            raise PlanError(f"segment {sid}: mask feather must be a number of pixels")
        if not 0.0 <= float(feather) <= MASK_FEATHER_MAX:
            raise PlanError(f"segment {sid}: mask feather must be between 0 and {MASK_FEATHER_MAX:g} px")
        return {"type": "rect", **box, "feather": float(feather)}
    path = raw.get("path")
    if not isinstance(path, str) or not path.strip():
        raise PlanError(f"segment {sid}: mask path must be a project-relative file path")
    parts = Path(path).parts
    if Path(path).is_absolute() or ".." in parts:
        raise PlanError(f"segment {sid}: mask path must stay inside the project")
    return {"type": "image", "path": path}


def _as_program(candidate: str) -> str | None:
    """A CLI flag or `<NAME>_BIN` value: a path, or a name on PATH. Symlinks stay unresolved so a
    venv/managed-tool path keeps pointing at its own interpreter."""
    found = shutil.which(candidate)
    if found:
        return found
    path = Path(candidate)
    return str(path) if path.is_file() else None


def executable(value: str | None, name: str, fallback: str | None = None) -> str:
    """Resolve a program for the hybrid runner: explicit flag, then `<NAME>_BIN`, then the repo
    fallback, then PATH. Failing loudly matters here: a wrong binary silently ruins an assembly."""
    for candidate in (value, os.environ.get(f"{name.upper()}_BIN")):
        if not candidate:
            continue
        resolved = _as_program(candidate)
        if resolved is None:
            raise RuntimeError(f"{name} executable not found: {candidate}")
        return resolved
    if fallback and Path(fallback).is_file():
        return str(Path(fallback))
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f"{name} not found; pass --{name} or add it to PATH")


def run(cmd: list[str], *, cwd: Path, env: dict[str, str], label: str) -> None:
    print(f"[{label}] {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, cwd=cwd, env=env, check=False)
    if result.returncode:
        raise RuntimeError(f"{label} exited with status {result.returncode}")


def probe(ffprobe: str, media: Path) -> dict[str, Any]:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=codec_name,width,height,r_frame_rate,nb_read_frames,nb_frames:format=duration",
         "-of", "json", str(media)], capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe failed for {media}: {result.stderr.strip()}")
    try:
        streams = json.loads(result.stdout).get("streams", [])
        stream = streams[0]
        width, height = int(stream["width"]), int(stream["height"])
        raw_frames = stream.get("nb_read_frames", stream.get("nb_frames"))
        frame_count = int(raw_frames) if raw_frames is not None else -1
        numerator, denominator = (int(n) for n in stream["r_frame_rate"].split("/", 1))
    except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"could not read video stream metadata for {media}") from error
    rate = numerator / denominator if denominator else 0
    if frame_count < 0 and rate > 0:
        try:
            seconds = float(json.loads(result.stdout)["format"]["duration"])
            estimated = round(seconds * rate)
            if abs(seconds * rate - estimated) < 0.05:
                frame_count = estimated
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass
    if frame_count < 0:
        raise RuntimeError(f"frame count unavailable for {media}")
    return {"width": width, "height": height,
            "frames": frame_count, "fps": rate, "codec": stream.get("codec_name")}


def media_duration(ffprobe: str, path: Path) -> float:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe failed for {path}: {result.stderr.strip()}")
    try:
        value = float(json.loads(result.stdout)["format"]["duration"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError(f"could not read media duration for {path}") from error
    if not (value > 0):
        raise RuntimeError(f"media duration must be positive: {path}")
    return value


def verify_audio_stream(ffprobe: str, path: Path) -> None:
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=codec_name",
         "-of", "json", str(path)], capture_output=True, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError(f"ffprobe could not verify the final audio stream: {result.stderr.strip()}")
    try:
        streams = json.loads(result.stdout).get("streams", [])
    except json.JSONDecodeError as error:
        raise RuntimeError("ffprobe returned invalid audio metadata") from error
    if not streams or not streams[0].get("codec_name"):
        raise RuntimeError("audio was requested but the final file has no audio stream")


def verify_segment(ffprobe: str, path: Path, expected_frames: int, sid: str) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"engine output missing or empty for segment {sid}: {path}")
    metadata = probe(ffprobe, path)
    if (metadata["width"], metadata["height"], metadata["fps"], metadata["frames"]) != (
        WIDTH, HEIGHT, float(FPS), expected_frames
    ):
        raise RuntimeError(
            f"segment {sid} violates render contract: {metadata}; expected "
            f"{WIDTH}x{HEIGHT}, {FPS} fps, {expected_frames} frames"
        )


def build_segment_command(engine: str, *, python: str, node: str, ffmpeg: str,
                          project: Path, start: int, end: int, sid: str,
                          target: Path, frames_dir: Path) -> list[str]:
    """The CLI one engine needs to render [start, end) into its own output."""
    if engine == "p":
        return [python, str(ROOT / "tools" / "render_p_segment.py"), "--project", str(project),
                "--from-frame", str(start), "--to-frame", str(end), "--out", str(target),
                "--ffmpeg", ffmpeg, "--fps", str(FPS)]
    if engine == "k":
        return [node, "src/render.js", "--from", f"{start / FPS:.12g}", "--to", f"{end / FPS:.12g}",
                "--fps", str(FPS), "--scale", "1", "--out", str(frames_dir), "--name", sid]
    return [node, "scripts/render.mjs", "--silent", "--from-frame", str(start),
            "--to-frame", str(end), "--out", str(target)]


def build_alpha_command(node: str, start: int, end: int, frames_dir: Path) -> list[str]:
    """Engine K, transparent: one RGBA PNG per frame, no encoder."""
    return [node, "src/render.js", "--from", f"{start / FPS:.12g}", "--to", f"{end / FPS:.12g}",
            "--fps", str(FPS), "--scale", "1", "--alpha", "--out", str(frames_dir)]


def build_mask_source(mask: dict[str, Any]) -> str:
    """A gray generator where **white means the base wins** (the overlay is hidden there).

    Frame fractions keep the plan independent of the canvas constant; the rectangle is drawn at
    the locked 1080x1920 and optionally blurred, which is the cheapest honest feather.
    """
    x, y = round(mask["x"] * WIDTH), round(mask["y"] * HEIGHT)
    w, h = max(1, round(mask["w"] * WIDTH)), max(1, round(mask["h"] * HEIGHT))
    chain = (f"color=c=black:s={WIDTH}x{HEIGHT}:r={FPS},"
             f"drawbox=x={x}:y={y}:w={w}:h={h}:color=white:t=fill,format=gray")
    feather = float(mask.get("feather", 0) or 0)
    if feather > 0:
        chain += f",gblur=sigma={feather / 2:.3f}"
    return chain


def _composite_filter(mask: dict[str, Any] | None,
                      mask_image: Path | None) -> tuple[str, list[str]]:
    """Overlay graph, with the overlay's own alpha multiplied by `1 - mask` when masked."""
    if mask is None:
        return "[0:v][1:v]overlay=format=auto", []
    if mask["type"] == "image":
        if mask_image is None:
            raise RuntimeError("image mask requires a resolved matte path")
        source = "[2:v]format=gray,negate,fps=30,setsar=1"
        extra_inputs = ["-loop", "1", "-framerate", str(FPS), "-i", str(mask_image)]
    else:
        source = f"{build_mask_source(mask)},negate,setsar=1"
        extra_inputs = []
    graph = (
        "[0:v]format=yuv420p,setsar=1[mb];"
        "[1:v]format=rgba,setsar=1,split=2[ov][ova];"
        "[ova]alphaextract[ka];"
        f"{source}[mi];"
        "[ka][mi]blend=all_mode=multiply[am];"
        "[ov][am]alphamerge[ovm];"
        "[mb][ovm]overlay=format=auto"
    )
    return graph, extra_inputs


def build_composite_command(ffmpeg: str, base: Path, frames_dir: Path, frames: int, out: Path,
                            mask: dict[str, Any] | None = None,
                            mask_image: Path | None = None) -> list[str]:
    """Overlay the transparent PNG sequence on the base footage, frame for frame."""
    graph, extra_inputs = _composite_filter(mask, mask_image)
    return [ffmpeg, "-hide_banner", "-loglevel", "error", "-n",
            "-i", str(base), "-framerate", str(FPS), "-i", str(frames_dir / "%05d.png"),
            *extra_inputs,
            "-filter_complex", graph,
            "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium", "-crf", "13",
            "-pix_fmt", "yuv420p", "-r", str(FPS), str(out)]


def resolve_mask_image(mask: dict[str, Any], project: Path, label: str) -> Path:
    """A matte path must exist and stay inside the project — no absolute escape hatches."""
    project = project.resolve()
    candidate = (project / mask["path"]).resolve()
    try:
        candidate.relative_to(project)
    except ValueError as error:
        raise RuntimeError(f"{label}: mask path escapes the project: {mask['path']}") from error
    if not candidate.is_file():
        raise RuntimeError(f"{label}: mask matte not found: {mask['path']}")
    return candidate


def composite_overlay(ffmpeg: str, base: Path, frames_dir: Path, frames: int,
                      project: Path, env: dict[str, str], label: str,
                      mask: dict[str, Any] | None = None) -> None:
    """Composite in place (via a temp file) and refuse a frame-count mismatch."""
    rendered = sorted(frames_dir.glob("[0-9][0-9][0-9][0-9][0-9].png"))
    if len(rendered) != frames:
        raise RuntimeError(
            f"{label}: transparent overlay produced {len(rendered)} frame(s), expected {frames}"
        )
    mask_image = resolve_mask_image(mask, project, label) if mask and mask["type"] == "image" else None
    temp = base.with_name(base.stem + ".overlay.mp4")
    run(build_composite_command(ffmpeg, base, frames_dir, frames, temp, mask=mask, mask_image=mask_image),
        cwd=project, env=env, label=label)
    os.replace(temp, base)



def escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def main() -> int:
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "projects" / "hybrid-project")
    parser.add_argument("--plan", type=Path, default=None, help="defaults to <project>/plan/hybrid.json")
    parser.add_argument("--out", type=Path, default=None, help="defaults to <project>/out/hybrid.mp4")
    parser.add_argument("--audio", type=Path, default=None, help="override the plan audio path; pass '-' for no audio")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    parser.add_argument("--node", default=None)
    parser.add_argument("--python", default=None)
    parser.add_argument("--profile", action="store_true", help="write end-to-end segment/assembly timing")
    parser.add_argument("--qa", action="store_true", help="run post-render Final Media QA before publishing output")
    parser.add_argument("--qa-mode", choices=("master", "preview", "video-only"), default=None,
                        help="media_qa mode when --qa is set (defaults to master with audio, video-only without)")
    parser.add_argument("--qa-report", type=Path, default=None, help="fresh JSON path for the --qa report")
    parser.add_argument("--motion-mode", choices=("normal", "reduced"), default=os.environ.get("MEDO_MOTION_MODE", "normal"))
    args = parser.parse_args()

    project = args.project.resolve()
    plan_path = (args.plan or project / "plan" / "hybrid.json").resolve()
    output = (args.out or project / "out" / "hybrid.mp4").resolve()
    profile_path = output.with_name(output.name + ".profile.json")
    if args.profile and profile_path.exists(): raise RuntimeError(f"profile already exists: {profile_path}")
    qa_report_path = args.qa_report.resolve() if args.qa_report else None
    if qa_report_path is not None and qa_report_path.exists():
        raise RuntimeError(f"QA report already exists: {qa_report_path}")
    if output.exists():
        raise RuntimeError(f"refusing to overwrite existing output: {output}; choose a new --out path")
    temp_out = output.with_name(output.stem + ".part.mp4")
    if temp_out.exists():
        raise RuntimeError(f"temporary final output already exists: {temp_out}")
    raw = json.loads(plan_path.read_text(encoding="utf-8"))
    plan = validate_plan(raw)
    if not project.is_dir():
        raise RuntimeError(f"project directory not found: {project}")
    ffmpeg = executable(args.ffmpeg, "ffmpeg", str(ROOT / "tools" / "bin" / "ffmpeg"))
    ffprobe = executable(args.ffprobe, "ffprobe", str(ROOT / "tools" / "bin" / "ffprobe"))
    node = executable(args.node, "node")
    python = executable(args.python, "python", sys.executable)
    audio_value = None if args.audio == Path("-") else (
        args.audio if args.audio is not None else Path(plan["audio"]) if plan["audio"] is not None else None
    )
    audio_path = None
    if audio_value is not None:
        audio_path = (project / audio_value).resolve() if not audio_value.is_absolute() else audio_value.resolve()
        if not audio_path.is_file():
            raise RuntimeError(f"audio file not found: {audio_path}")
        audio_duration = media_duration(executable(args.ffprobe, "ffprobe", str(ROOT / "tools" / "bin" / "ffprobe")), audio_path)
        expected_duration = plan["duration_frames"] / FPS
        if abs(audio_duration - expected_duration) > 0.15:
            raise RuntimeError(
                f"audio is {audio_duration:.3f}s but the hybrid timeline is {expected_duration:.3f}s "
                "(maximum allowed difference: 0.15s)"
            )

    run_dir = project / "cache" / f"hybrid-{uuid.uuid4().hex[:12]}"
    run_dir.mkdir(parents=True, exist_ok=False)
    output.parent.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "MEDO_MOTION_MODE": args.motion_mode,
        "MEDO_ASSETS_DIR": str(project / "assets"),
        "MEDO_FFMPEG": ffmpeg,
        "MEDO_FFPROBE": ffprobe,
    }
    env.setdefault("PYTHONUNBUFFERED", "1")

    segment_times = []
    for segment in plan["segments"]:
        sid = segment["id"]
        start, end = segment["start_frame"], segment["end_frame"]
        target = run_dir / f"{sid}.mp4"
        base, overlays = segment["layers"][0], segment["layers"][1:]
        engine = base["engine"]
        t0 = time.perf_counter()
        run(build_segment_command(engine, python=python, node=node, ffmpeg=ffmpeg, project=project,
                                  start=start, end=end, sid=sid, target=target, frames_dir=run_dir),
            cwd=project, env=env, label=f"engine {engine.upper()} · {sid}")
        if overlays:
            overlay = overlays[0]
            frames_dir = run_dir / f"{sid}-overlay"
            frames_dir.mkdir(parents=True, exist_ok=False)
            run(build_alpha_command(node, start, end, frames_dir), cwd=project, env=env,
                label=f"engine K overlay · {sid}")
            # Fail before the composite if the matte is missing: a silent unmasked overlay would
            # look like a working render with the wrong layering.
            if overlay.get("mask", {}).get("type") == "image":
                resolve_mask_image(overlay["mask"], project, f"segment {sid}")
            composite_overlay(ffmpeg, target, frames_dir, end - start, project, env,
                              label=f"composite K over {engine.upper()} · {sid}",
                              mask=overlay.get("mask"))
            if overlay.get("mask"):
                overlay = {**overlay, "masked": True}
        render_ms = (time.perf_counter()-t0)*1000
        t0 = time.perf_counter(); verify_segment(ffprobe, target, end - start, sid)
        if args.profile: segment_times.append({'id': sid, 'engine': engine.upper(), 'frames': end-start,
                                               'overlays': len(overlays),
                                               'masked': bool(overlays and overlays[0].get("mask")),
                                               'renderMs': render_ms, 'verifyMs': (time.perf_counter()-t0)*1000})

    list_file = run_dir / "segments.txt"
    list_file.write_text("".join(f"file '{escape_concat_path(run_dir / (s['id'] + '.mp4'))}'\n"
                                 for s in plan["segments"]), encoding="utf-8")
    total_seconds = plan["duration_frames"] / FPS
    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-n", "-f", "concat", "-safe", "0",
               "-i", str(list_file)]
    if audio_path:
        command += ["-i", str(audio_path), "-map", "0:v:0", "-map", "1:a:0", "-af", "apad",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        command += ["-map", "0:v:0", "-an"]
    command += ["-frames:v", str(plan["duration_frames"]), "-t", f"{total_seconds:.12g}",
                "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-pix_fmt", "yuv420p",
                "-r", str(FPS), "-movflags", "+faststart", str(temp_out)]
    try:
        assembly_started = time.perf_counter()
        run(command, cwd=project, env=env, label="assemble final hybrid reel")
        assembly_ms = (time.perf_counter()-assembly_started)*1000
        final = probe(ffprobe, temp_out)
        if (final["width"], final["height"], final["fps"], final["frames"]) != (
            WIDTH, HEIGHT, float(FPS), plan["duration_frames"]
        ):
            raise RuntimeError(f"final output violates timeline contract: {final}")
        if audio_path:
            verify_audio_stream(ffprobe, temp_out)
        if args.qa or qa_report_path is not None:
            sys.path.insert(0, str(ROOT / "tools"))
            import media_qa  # noqa: PLC0415

            qa_mode = args.qa_mode or ("master" if audio_path else "video-only")
            beats_candidate = project / "plan" / "beats.json"
            qa_report = media_qa.inspect_media(
                temp_out,
                mode=qa_mode,
                vo_path=audio_path,
                beats_path=beats_candidate if beats_candidate.is_file() else None,
                expected_frames=plan["duration_frames"],
            )
            if qa_report_path is not None:
                qa_report_path.parent.mkdir(parents=True, exist_ok=True)
                with qa_report_path.open("x", encoding="utf-8") as stream:
                    json.dump(qa_report, stream, indent=2, ensure_ascii=False)
                    stream.write("\n")
            if qa_report["status"] != "pass":
                raise RuntimeError(
                    f"post-render media QA {qa_report['status']}: "
                    + "; ".join(f"{e['code']}: {e['msg']}" for e in qa_report.get("errors", []))
                    + (f" ({'; '.join(qa_report.get('incomplete_reasons', []))})" if qa_report.get("incomplete_reasons") else "")
                )
        os.replace(temp_out, output)
        if args.profile:
            report = {'version': 1, 'engine': 'Hybrid', 'motionMode': args.motion_mode, 'frames': plan['duration_frames'],
                      'segments': segment_times, 'assemblyMs': assembly_ms, 'wallMs': (time.perf_counter()-started)*1000,
                      'scope': 'Segment render subprocesses and verification measured separately; assembly includes final FFmpeg encode. No GPU metrics.'}
            with profile_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2); stream.write('\n')
    except BaseException:
        temp_out.unlink(missing_ok=True)
        raise
    layered = sum(1 for segment in plan["segments"] if len(segment["layers"]) > 1)
    masked = sum(1 for segment in plan["segments"]
                 if len(segment["layers"]) > 1 and segment["layers"][1].get("mask"))
    print(f"HYBRID OK · {len(plan['segments'])} sequential segments"
          f"{f' ({layered} with a transparent K overlay)' if layered else ''}"
          f"{f' ({masked} masked)' if masked else ''} · {plan['duration_frames']} frames "
          f"({total_seconds:.3f}s) · {output}")
    print(f"segment diagnostics retained at {run_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, PlanError, json.JSONDecodeError) as error:
        print(f"hybrid render failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
