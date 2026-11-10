"""Render and verify one half-open frame range for engine P."""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

FF = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"
HERE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("REEL_DIR") or HERE).resolve()
os.chdir(PROJECT)
sys.path.insert(0, str(HERE))

from scenes import *  # noqa: F403
import cv2
from PIL import Image as _PILImage  # after the star import: scenes owns names like `Image`
from chunk_utils import is_valid_chunk
from render_policy import motion_mode
from resource_scope import ResourceScope
import text_direction as td

# Text motion is an explicit agent decision for every visible text element.
beats_p = PROJECT / "plan" / "beats.json"
if beats_p.is_file():
    beats = json.loads(beats_p.read_text(encoding="utf-8"))
    report = td.validate(td.load(PROJECT), beats, td.load_copy(PROJECT), td.load_fonts(PROJECT) or None)
    if report["errors"]:
        raise SystemExit("Text direction incomplete — the agent must choose styles per scene:\n"
                         + "\n".join(report["errors"]))

if len(sys.argv) != 3:
    raise SystemExit("usage: chunk.py START_FRAME END_FRAME")
mode = motion_mode(os.environ.get("MEDO_MOTION_MODE", "normal"))
if mode == "reduced" and globals().get("SUPPORTS_REDUCED_MOTION") is not True:
    raise SystemExit("Reduced motion requires an explicit SUPPORTS_REDUCED_MOTION=True in scenes.py")
a, b = map(int, sys.argv[1:])
if a < 0 or b <= a:
    raise SystemExit("chunk frame range must satisfy 0 <= start < end")

# Draft preview (REEL_DRAFT=1): render every other source frame and half the canvas.
# Frame `i` of the preview is source frame `2*i`, so the timeline stays identical — only the
# sampling density and the pixel budget change. Nothing here runs unless the flag is set.
DRAFT = os.environ.get("REEL_DRAFT") == "1"
DFPS = 15
DW, DH = W // 2, H // 2
OUT_W, OUT_H = (DW, DH) if DRAFT else (W, H)
ENCODE_FPS = DFPS if DRAFT else 30
mode_tag = mode + ("-draft" if DRAFT else "")


def preview_frame(frame):
    """Half-size copy of one rendered frame: numpy/cv2 is the template's normal output."""
    if hasattr(frame, "shape"):  # cv2 frames are HxWx3 arrays, not PIL images
        return cv2.resize(frame, (DW, DH), interpolation=cv2.INTER_AREA)
    return frame.resize((DW, DH), _PILImage.BILINEAR)

out_dir = PROJECT / "out" / "draft_chunks" if DRAFT else PROJECT / "out"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"c_{a:05d}_{b:05d}.mp4"
tmp = out.with_name(out.stem + ".tmp.mp4")
mode_file = out.with_suffix(".mode")

# A cached file is reusable only after a full decode/count/dimension check.
if mode_file.is_file() and mode_file.read_text(encoding="ascii").strip() == mode_tag and is_valid_chunk(out, b - a, OUT_W, OUT_H):
    print(f"chunk cached and verified {a}:{b}", flush=True)
    raise SystemExit(0)
# Remove the old marker before publishing anything; an interrupted run is always a cache miss.
mode_file.unlink(missing_ok=True)
if out.exists():
    out.unlink()
if tmp.exists():
    tmp.unlink()

cmd = [
    FF, "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OUT_W}x{OUT_H}", "-r", str(ENCODE_FPS), "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-tune", "animation",
    "-x264-params", "aq-mode=3:ref=4:deblock=1,1",
    "-pix_fmt", "yuv420p", str(tmp),
]
with ResourceScope() as resources:
    init_resources = globals().get("init_resources")
    if init_resources is not None:
        if not callable(init_resources): raise TypeError("init_resources must be callable")
        init_resources(resources)
    try:
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        try:
            for frame_index in range(a, b):
                if DRAFT:
                    source = render_frame((frame_index * 2) / 30)  # noqa: F405
                    process.stdin.write(preview_frame(source).tobytes())
                else:
                    process.stdin.write(render_frame(frame_index / 30).tobytes())  # noqa: F405
            process.stdin.close()
            process.stdin = None
        except BaseException:
            if process.stdin and not process.stdin.closed:
                try:
                    process.stdin.close()
                except OSError:
                    pass
            if process.poll() is None:
                process.terminate()
            process.wait()
            raise
        return_code = process.wait()
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise

    if return_code != 0 or not is_valid_chunk(tmp, b - a, OUT_W, OUT_H):
        if tmp.exists():
            tmp.unlink()
        print(f"chunk FAILED {a}:{b}; ffmpeg exit={return_code} or output verification failed", flush=True)
        raise SystemExit(1)

os.replace(tmp, out)
mode_tmp = mode_file.with_suffix(".mode.tmp")
mode_tmp.write_text(mode_tag+"\n", encoding="ascii")
os.replace(mode_tmp, mode_file)
print(f"chunk verified {a}:{b}", flush=True)
