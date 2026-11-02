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
from chunk_utils import is_valid_chunk
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
a, b = map(int, sys.argv[1:])
if a < 0 or b <= a:
    raise SystemExit("chunk frame range must satisfy 0 <= start < end")

out_dir = PROJECT / "out"
out_dir.mkdir(parents=True, exist_ok=True)
out = out_dir / f"c_{a:05d}_{b:05d}.mp4"
tmp = out.with_name(out.stem + ".tmp.mp4")

# A cached file is reusable only after a full decode/count/dimension check.
if is_valid_chunk(out, b - a, W, H):
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

if return_code != 0 or not is_valid_chunk(tmp, b - a, W, H):
    if tmp.exists():
        tmp.unlink()
    print(f"chunk FAILED {a}:{b}; ffmpeg exit={return_code} or output verification failed", flush=True)
    raise SystemExit(1)

os.replace(tmp, out)
print(f"chunk verified {a}:{b}", flush=True)
