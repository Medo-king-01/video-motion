"""Render and verify one half-open frame range for engine P."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

FF = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE_BIN") or shutil.which("ffprobe") or "ffprobe"
HERE = Path(__file__).resolve().parent
PROJECT = Path(os.environ.get("REEL_DIR") or HERE).resolve()
os.chdir(PROJECT)
sys.path.insert(0, str(HERE))

from scenes import *  # noqa: F403
from chunk_utils import is_valid_chunk

if len(sys.argv) != 3:
    raise SystemExit("usage: chunk.py START_FRAME END_FRAME")
a, b = map(int, sys.argv[1:])
if a < 0 or b <= a:
    raise SystemExit("chunk frame range must satisfy 0 <= start < end")

out_dir = PROJECT / "out"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"c_{a:05d}_{b:05d}.mp4"
tmp = out.with_name(out.stem + ".tmp.mp4")

# A cached file is reusable only after a full decode/count/dimension check.
if is_valid_chunk(out, b - a, W, H, FFPROBE):
    print(f"chunk cached and verified {a}:{b}", flush=True)
    raise SystemExit(0)
if out.exists():
    out.unlink()
if tmp.exists():
    tmp.unlink()

cmd = [
    FF, "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", "30", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "13", "-tune", "animation",
    "-x264-params", "aq-mode=3:ref=4:deblock=1,1",
    "-pix_fmt", "yuv420p", str(tmp),
]
try:
    process = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for frame_index in range(a, b):
            process.stdin.write(render_frame(frame_index / 30).tobytes())  # noqa: F405
        process.stdin.close()
        process.stdin = None
    except BaseException:
        if process.stdin and not process.stdin.closed:
            process.stdin.close()
        process.terminate()
        process.wait()
        raise
    return_code = process.wait()
except BaseException:
    if tmp.exists():
        tmp.unlink()
    raise

if return_code != 0 or not is_valid_chunk(tmp, b - a, W, H, FFPROBE):
    if tmp.exists():
        tmp.unlink()
    print(f"chunk FAILED {a}:{b}; ffmpeg exit={return_code} or output verification failed", flush=True)
    raise SystemExit(1)

os.replace(tmp, out)
print(f"chunk verified {a}:{b}", flush=True)
