#!/usr/bin/env python3
"""Render a frame-accurate hybrid P/K/R reel from plan/hybrid.json.

Segments are sequential and each is rendered by exactly one engine. This is
not a simultaneous multi-engine layer compositor. Audio is added once, after
video assembly, so there is one continuous soundtrack across all segments.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
WIDTH = 1080
HEIGHT = 1920
ENGINES = {"p", "k", "r"}


class PlanError(ValueError):
    """Invalid hybrid timeline or contract."""


def validate_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise PlanError("plan version must be 1")
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
        sid, engine = item.get("id"), item.get("engine")
        start, end = item.get("start_frame"), item.get("end_frame")
        if not isinstance(sid, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", sid):
            raise PlanError(f"segment {i} id must contain only letters, digits, _ or -")
        if sid in ids:
            raise PlanError(f"duplicate segment id: {sid}")
        ids.add(sid)
        if not isinstance(engine, str) or engine not in ENGINES:
            raise PlanError(f"segment {sid}: engine must be p, k, or r")
        if isinstance(start, bool) or not isinstance(start, int) or isinstance(end, bool) or not isinstance(end, int):
            raise PlanError(f"segment {sid}: start_frame/end_frame must be integer frame indexes")
        if start != cursor:
            raise PlanError(f"segment {sid} starts at frame {start}; expected {cursor} (gap or overlap)")
        if end <= start:
            raise PlanError(f"segment {sid} must contain at least one frame")
        cursor = end
        clean.append({"id": sid, "engine": engine, "start_frame": start, "end_frame": end})
    if cursor != total:
        raise PlanError(f"segments end at frame {cursor}; duration_frames is {total}")
    audio = raw.get("audio")
    if audio is not None:
        if not isinstance(audio, str) or not audio.strip():
            raise PlanError("audio must be a project-relative file path or null")
        audio_parts = Path(audio).parts
        if Path(audio).is_absolute() or ".." in audio_parts:
            raise PlanError("audio path must stay inside the project")
    return {"version": 1, "fps": FPS, "width": WIDTH, "height": HEIGHT,
            "duration_frames": total, "segments": clean, "audio": audio}


def executable(value: str | None, name: str, fallback: str | None = None) -> str:
    candidate = value or os.environ.get(name.upper() + "_BIN")
    if candidate:
        found = shutil.which(candidate)
        if found:
            return found
        path = Path(candidate)
        if path.is_file():
            return str(path.resolve())
        raise RuntimeError(f"{name} executable not found: {candidate}")
    if fallback and Path(fallback).is_file():
        # Preserve venv/managed-tool symlink paths; resolving them can bypass the environment.
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


def escape_concat_path(path: Path) -> str:
    return str(path.resolve()).replace("'", "'\\''")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=ROOT / "projects" / "hybrid-project")
    parser.add_argument("--plan", type=Path, default=None, help="defaults to <project>/plan/hybrid.json")
    parser.add_argument("--out", type=Path, default=None, help="defaults to <project>/out/hybrid.mp4")
    parser.add_argument("--audio", type=Path, default=None, help="override the plan audio path; pass '-' for no audio")
    parser.add_argument("--ffmpeg", default=None)
    parser.add_argument("--ffprobe", default=None)
    parser.add_argument("--node", default=None)
    parser.add_argument("--python", default=None)
    args = parser.parse_args()

    project = args.project.resolve()
    plan_path = (args.plan or project / "plan" / "hybrid.json").resolve()
    output = (args.out or project / "out" / "hybrid.mp4").resolve()
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
        "MEDO_ASSETS_DIR": str(project / "assets"),
        "MEDO_FFMPEG": ffmpeg,
        "MEDO_FFPROBE": ffprobe,
    }
    env.setdefault("PYTHONUNBUFFERED", "1")

    for segment in plan["segments"]:
        sid = segment["id"]
        start, end = segment["start_frame"], segment["end_frame"]
        target = run_dir / f"{sid}.mp4"
        engine = segment["engine"]
        if engine == "p":
            cmd = [python, str(ROOT / "tools" / "render_p_segment.py"), "--project", str(project),
                   "--from-frame", str(start), "--to-frame", str(end), "--out", str(target),
                   "--ffmpeg", ffmpeg, "--fps", str(FPS)]
        elif engine == "k":
            cmd = [node, "src/render.js", "--from", f"{start / FPS:.12g}", "--to", f"{end / FPS:.12g}",
                   "--fps", str(FPS), "--scale", "1", "--out", str(run_dir), "--name", sid]
        else:
            cmd = [node, "scripts/render.mjs", "--silent", "--from-frame", str(start),
                   "--to-frame", str(end), "--out", str(target)]
        run(cmd, cwd=project, env=env, label=f"engine {engine.upper()} · {sid}")
        verify_segment(ffprobe, target, end - start, sid)

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
        run(command, cwd=project, env=env, label="assemble final hybrid reel")
        final = probe(ffprobe, temp_out)
        if (final["width"], final["height"], final["fps"], final["frames"]) != (
            WIDTH, HEIGHT, float(FPS), plan["duration_frames"]
        ):
            raise RuntimeError(f"final output violates timeline contract: {final}")
        if audio_path:
            verify_audio_stream(ffprobe, temp_out)
        os.replace(temp_out, output)
    except BaseException:
        temp_out.unlink(missing_ok=True)
        raise
    print(f"HYBRID OK · {len(plan['segments'])} sequential segments · {plan['duration_frames']} frames "
          f"({total_seconds:.3f}s) · {output}")
    print(f"segment diagnostics retained at {run_dir}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, PlanError, json.JSONDecodeError) as error:
        print(f"hybrid render failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
