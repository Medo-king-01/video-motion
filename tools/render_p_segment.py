#!/usr/bin/env python3
"""Render an absolute, half-open frame range from an engine-P project as silent H.264."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="project root containing scenes.py")
    parser.add_argument("--from-frame", required=True, type=int)
    parser.add_argument("--to-frame", required=True, type=int, help="exclusive frame index")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--fps", type=int, default=30)
    args = parser.parse_args()

    project = args.project.resolve()
    output = args.out.resolve()
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
    temp = output.with_name(output.stem + ".part.mp4")
    temp.unlink(missing_ok=True)

    sys.path.insert(0, str(project))
    old_cwd = Path.cwd()
    encoder: subprocess.Popen[bytes] | None = None
    try:
        os.chdir(project)
        import text_direction as td  # noqa: PLC0415
        from art import H, W  # noqa: PLC0415
        from scenes import render_frame  # noqa: PLC0415

        beats_p = project / "plan" / "beats.json"
        if beats_p.is_file():
            beats = json.loads(beats_p.read_text(encoding="utf-8"))
            report = td.validate(td.load(project), beats, td.load_copy(project))
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
        encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert encoder.stdin is not None
        for frame in range(args.from_frame, args.to_frame):
            image = render_frame(frame / args.fps)
            if image.shape != (H, W, 3) or image.dtype.name != "uint8":
                raise RuntimeError(f"engine P returned an invalid frame at index {frame}: {image.shape} {image.dtype}")
            encoder.stdin.write(image.tobytes())
        encoder.stdin.close()
        code = encoder.wait()
        encoder = None
        if code != 0 or not temp.is_file() or temp.stat().st_size <= 0:
            raise RuntimeError(f"FFmpeg failed to encode the P segment (exit {code})")
        os.replace(temp, output)
        print(f"P segment: frames {args.from_frame}:{args.to_frame} -> {output}")
        return 0
    except BaseException:
        if encoder is not None:
            if encoder.stdin and not encoder.stdin.closed:
                encoder.stdin.close()
            encoder.kill()
            encoder.wait()
        temp.unlink(missing_ok=True)
        raise
    finally:
        os.chdir(old_cwd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"P segment render failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
