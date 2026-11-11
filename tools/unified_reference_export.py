#!/usr/bin/env python3
"""Export a small, silent reference preview as lossless FFV1/Matroska.

Requires a trusted local ffmpeg executable and trusted project/output directories.
This is not a P/K/R/Hybrid backend or a general video editor export.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from pathlib import Path

from unified_project_store import load
from unified_reference_preview import PreviewError, render_frame
from unified_render_graph import compile_project

# This prototype buffers all frames before spawning ffmpeg, so impose a hard bound.
MAX_RAW_BYTES = 64 * 1024 * 1024
MAX_FRAMES = 10000


def export_reference(project, root, destination, *, ffmpeg="ffmpeg", timeout=120):
    """Create a new silent FFV1 MKV without overwriting; return frame metadata.

    Each frame uses the reference preview's strict support and asset checks. The
    raw buffer is capped; no output is published on validation or encoder error.
    Publishing uses an atomic hard link and fails if the destination exists.
    """
    graph = compile_project(project)
    snapshot = graph["project"]
    count = graph["clock"]["frameCount"]
    width, height = snapshot["profile"]["width"], snapshot["profile"]["height"]
    if count == 0:
        raise PreviewError("E01", "$.duration", "cannot export an empty project")
    if count > MAX_FRAMES or count * width * height * 4 > MAX_RAW_BYTES:
        raise PreviewError("E01", "$", "reference export frame or memory limit exceeded")
    destination = Path(destination)
    if destination.suffix.lower() != ".mkv":
        raise PreviewError("E01", "$", "reference export requires an .mkv destination")
    if os.path.lexists(destination):
        raise FileExistsError(f"Destination already exists: {destination}")
    # Render the whole range before touching the destination or launching ffmpeg.
    frames = b"".join(render_frame(snapshot, root, n)["pixels"] for n in range(count))
    fps = snapshot["profile"]["fps"]
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".reference-export-", suffix=".mkv",
                                         delete=False) as temp:
            temp_name = temp.name
        command = [os.fspath(ffmpeg), "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
                   "-f", "rawvideo", "-pixel_format", "rgba", "-video_size", f"{width}x{height}",
                   "-framerate", f"{fps['num']}/{fps['den']}", "-i", "pipe:0", "-map_metadata", "-1",
                   "-an", "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgra", "-f", "matroska", temp_name]
        try:
            result = subprocess.run(command, input=frames, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                    timeout=timeout, check=False)
        except subprocess.TimeoutExpired as exc:
            raise PreviewError("E02", "$", "ffmpeg timed out") from exc
        except OSError as exc:
            raise PreviewError("E02", "$", f"cannot start ffmpeg: {exc}") from exc
        if result.returncode:
            message = result.stderr.decode("utf-8", errors="replace")[-1000:]
            raise PreviewError("E02", "$", f"ffmpeg failed ({result.returncode}): {message}")
        if Path(temp_name).stat().st_size == 0:
            raise PreviewError("E02", "$", "ffmpeg returned success without an output file")
        # No replacement even if another process creates the destination mid-encode.
        os.link(temp_name, destination)
    finally:
        if temp_name is not None:
            Path(temp_name).unlink(missing_ok=True)
    return {"frameCount": count, "width": width, "height": height, "fps": dict(fps),
            "container": "matroska", "codec": "ffv1", "audio": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    args = parser.parse_args(argv)
    try:
        project, _ = load(args.project)
        info = export_reference(project, args.project.parent, args.output, ffmpeg=args.ffmpeg)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Reference export failed: {exc}\n")
    print(f"Reference export created: {info['frameCount']} frames, silent FFV1 in Matroska")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
