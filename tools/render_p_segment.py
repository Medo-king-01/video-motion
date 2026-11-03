#!/usr/bin/env python3
"""Render an absolute, half-open frame range from an engine-P project as silent H.264."""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "medo-motion" / "scripts"))
from _safe_paths import checked_path  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="project root containing scenes.py")
    parser.add_argument("--from-frame", required=True, type=int)
    parser.add_argument("--to-frame", required=True, type=int, help="exclusive frame index")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--motion-mode", choices=("normal", "reduced"), default=os.environ.get("MEDO_MOTION_MODE", "normal"))
    parser.add_argument("--profile-out", type=Path, default=None, help="fresh JSON file for local render timing")
    args = parser.parse_args()

    started = time.perf_counter()
    project = args.project.resolve()
    output = checked_path(args.out)
    profile_path = checked_path(args.profile_out) if args.profile_out else None
    if profile_path is not None:
        if profile_path == output or profile_path.exists(): parser.error("profile output must be a fresh separate path")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
    count = args.to_frame - args.from_frame
    if not (project / "scenes.py").is_file():
        parser.error(f"{project} is not an engine-P project (scenes.py missing)")
    if args.from_frame < 0 or count <= 0 or args.fps != 30:
        parser.error("Use a non-empty half-open frame range and the locked 30 fps")
    if not Path(args.ffmpeg).is_file():
        parser.error(f"FFmpeg executable not found: {args.ffmpeg}")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        parser.error(f"refusing to overwrite segment output: {output}")
    fd, name = tempfile.mkstemp(prefix=output.stem + ".", suffix=".part.mp4", dir=output.parent)
    os.close(fd)
    temp = Path(name)

    sys.path.insert(0, str(project))
    # Older custom P projects may not contain the optional resource helper.
    sys.path.append(str(Path(__file__).resolve().parents[1] / "medo-motion" / "templates" / "procedural-reels"))
    old_cwd = Path.cwd()
    old_mode = os.environ.get("MEDO_MOTION_MODE")
    os.environ["MEDO_MOTION_MODE"] = args.motion_mode
    render_times, write_times = [], []
    encoder: subprocess.Popen[bytes] | None = None
    try:
        os.chdir(project)
        import scenes  # noqa: PLC0415
        import text_direction as td  # noqa: PLC0415
        from art import H, W  # noqa: PLC0415
        from resource_scope import ResourceScope  # noqa: PLC0415
        from scenes import render_frame  # noqa: PLC0415
        if args.motion_mode == "reduced" and getattr(scenes, "SUPPORTS_REDUCED_MOTION", False) is not True:
            raise RuntimeError("Reduced motion requires an explicit SUPPORTS_REDUCED_MOTION=True in scenes.py")

        beats_p = project / "plan" / "beats.json"
        if beats_p.is_file():
            beats = json.loads(beats_p.read_text(encoding="utf-8"))
            report = td.validate(td.load(project), beats, td.load_copy(project), td.load_fonts(project) or None)
            if report["errors"]:
                raise RuntimeError("Text direction incomplete — the agent must choose styles per scene:\n"
                                   + "\n".join(report["errors"]))

        command = [
            args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{W}x{H}",
            "-framerate", str(args.fps), "-i", "pipe:0", "-an", "-frames:v", str(count),
            "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-tune", "animation",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(temp),
        ]
        init_ms = (time.perf_counter()-started)*1000
        with ResourceScope() as resources:
            initializer = getattr(scenes, 'init_resources', None)
            if initializer is not None:
                if not callable(initializer): raise TypeError('init_resources must be callable')
                initializer(resources)
            encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
            assert encoder.stdin is not None
            for frame in range(args.from_frame, args.to_frame):
                t0 = time.perf_counter() if profile_path else 0
                image = render_frame(frame / args.fps)
                if profile_path: render_times.append((time.perf_counter()-t0)*1000)
                if image.shape != (H, W, 3) or image.dtype.name != "uint8":
                    raise RuntimeError(f"engine P returned an invalid frame at index {frame}: {image.shape} {image.dtype}")
                t0 = time.perf_counter() if profile_path else 0
                encoder.stdin.write(image.tobytes())
                if profile_path: write_times.append((time.perf_counter()-t0)*1000)
            t0 = time.perf_counter() if profile_path else 0
            encoder.stdin.close()
            code = encoder.wait()
            finalize_ms = (time.perf_counter()-t0)*1000 if profile_path else None
            encoder = None
            if code != 0 or not temp.is_file() or temp.stat().st_size <= 0:
                raise RuntimeError(f"FFmpeg failed to encode the P segment (exit {code})")
        # Publish without overwriting a file produced by another invocation.
        os.link(temp, output)
        temp.unlink()
        if profile_path:
            def summary(values):
                ordered = sorted(values)
                def quantile(q): return ordered[min(len(ordered)-1, max(0, math.ceil(q*len(ordered))-1))]
                return {'mean': sum(values)/len(values), 'p50': quantile(.5), 'p95': quantile(.95), 'max': ordered[-1]}
            report = {'version': 1, 'engine': 'P', 'motionMode': args.motion_mode, 'frames': count,
                      'initMs': init_ms, 'frameRenderMs': summary(render_times), 'frameWriteMs': summary(write_times),
                      'encoderFinalizeMs': finalize_ms, 'wallMs': (time.perf_counter()-started)*1000,
                      'scope': 'Frame render and pipe write/backpressure; FFmpeg overlaps writes; finalize is remaining flush only. No GPU metrics.'}
            with profile_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2); stream.write('\n')
        print(f"P segment: frames {args.from_frame}:{args.to_frame} -> {output}")
        return 0
    except BaseException:
        if encoder is not None:
            if encoder.stdin and not encoder.stdin.closed:
                try: encoder.stdin.close()
                except OSError: pass
            if encoder.poll() is None: encoder.kill()
            encoder.wait()
        temp.unlink(missing_ok=True)
        raise
    finally:
        os.chdir(old_cwd)
        if old_mode is None: os.environ.pop("MEDO_MOTION_MODE", None)
        else: os.environ["MEDO_MOTION_MODE"] = old_mode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"P segment render failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
