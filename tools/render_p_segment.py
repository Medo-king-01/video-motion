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

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "medo-motion" / "scripts"))
from _safe_paths import checked_path  # noqa: E402


def shrink(image: np.ndarray, width: int, height: int) -> np.ndarray:
    """Half-size copy of one rendered frame (cv2 is the template's normal path)."""
    try:
        import cv2  # noqa: PLC0415  (optional fast path)
    except ImportError:
        from PIL import Image as PILImage  # noqa: PLC0415

        return np.asarray(PILImage.fromarray(image).resize((width, height), PILImage.BILINEAR))
    return cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="project root containing scenes.py")
    parser.add_argument("--from-frame", required=True, type=int)
    parser.add_argument("--to-frame", required=True, type=int, help="exclusive frame index")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--motion-mode", choices=("normal", "reduced"), default=os.environ.get("MEDO_MOTION_MODE", "normal"))
    parser.add_argument("--draft", action="store_true",
                        help="hybrid draft preview: every other frame at 540x960 / 15 fps")
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
    # A draft is addressed in *draft frames* (15 fps) so the timeline stays anchored to absolute
    # frame numbers: draft frame k is source frame 2k. Segment [start, end) therefore covers
    # draft frames [start // 2, end // 2), and the total stays duration_frames / 2.
    draft_first = (args.from_frame // 2) * 2
    draft_count = args.to_frame // 2 - args.from_frame // 2
    if args.draft and draft_count <= 0:
        parser.error("draft preview needs at least one whole draft frame in the range")
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
    # Engine P spends its pixels supersampling every sprite (SS=3) and LANCZOS-downsampling it.
    # A draft is delivered at half the buffer, so that extra supersampling buys nothing the encoder
    # keeps: SS=1 measured 874 -> 215 ms per frame with a preview-identical picture. The caller
    # still wins when REEL_SS is set explicitly.
    old_ss = os.environ.get("REEL_SS")
    if args.draft and old_ss is None:
        os.environ["REEL_SS"] = "1"
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

        out_w, out_h = (W // 2, H // 2) if args.draft else (W, H)
        out_fps = args.fps // 2 if args.draft else args.fps
        command = [
            args.ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "rawvideo", "-pixel_format", "rgb24", "-video_size", f"{out_w}x{out_h}",
            "-framerate", str(out_fps), "-i", "pipe:0", "-an",
            "-frames:v", str(draft_count if args.draft else count),
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
            frames = (range(draft_first, args.to_frame, 2) if args.draft
                      else range(args.from_frame, args.to_frame))
            for frame in frames:
                t0 = time.perf_counter() if profile_path else 0
                image = render_frame(frame / args.fps)
                if profile_path: render_times.append((time.perf_counter()-t0)*1000)
                if image.shape != (H, W, 3) or image.dtype.name != "uint8":
                    raise RuntimeError(f"engine P returned an invalid frame at index {frame}: {image.shape} {image.dtype}")
                # P still renders at 1080x1920 and shrinks here: the draft saves frames, not pixels.
                if args.draft: image = shrink(image, out_w, out_h)
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
            report = {'version': 1, 'engine': 'P', 'motionMode': args.motion_mode,
                       'draft': args.draft, 'supersample': int(os.environ.get("REEL_SS", "3")),
                       'frames': draft_count if args.draft else count,
                      'initMs': init_ms, 'frameRenderMs': summary(render_times), 'frameWriteMs': summary(write_times),
                      'encoderFinalizeMs': finalize_ms, 'wallMs': (time.perf_counter()-started)*1000,
                      'scope': 'Frame render and pipe write/backpressure; FFmpeg overlaps writes; finalize is remaining flush only. No GPU metrics.'}
            with profile_path.open('x', encoding='utf-8') as stream: json.dump(report, stream, indent=2); stream.write('\n')
        print(f"P segment{' (draft 540x960 @15fps)' if args.draft else ''}: "
              f"frames {args.from_frame}:{args.to_frame} -> {output}")
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
        if old_ss is None: os.environ.pop("REEL_SS", None)
        else: os.environ["REEL_SS"] = old_ss


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"P segment render failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
