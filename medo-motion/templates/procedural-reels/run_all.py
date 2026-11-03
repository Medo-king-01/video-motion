"""Chunked, restartable render with content-addressed cache and verified chunks."""
import json
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

FPS = 30
CH = int(os.environ.get("REEL_CHUNK", "276"))
if CH <= 0:
    raise SystemExit("REEL_CHUNK must be a positive integer")

import scenes
from scenes import B
from render_policy import motion_mode
from lib import W, H, FONT
from chunk_utils import build_signature, expected_chunks, is_valid_chunk
import text_direction as td


def _vo_seconds(path):
    """The reel follows the VO duration; scenes.B is the fallback."""
    try:
        result = subprocess.run(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration", "-of", "json", path],
            capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            return None
        duration = float(json.loads(result.stdout)["format"]["duration"])
        return duration if duration > 0 else None
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


total = _vo_seconds(str(PROJECT / "out" / "vo24.wav"))
if total is None:
    total = B[-1]
    print(f"note: no out/vo24.wav -> using scenes.B ({total:.2f}s)")
elif abs(B[-1] - total) > 0.05:
    print(f"note: scenes.B ends at {B[-1]:.2f}s but the VO is {total:.2f}s -> rendering the VO length")
    print("      rebuild the bounds: python3 tools/vo_length.py out/vo24.wav --json plan/beats.json")

MODE = motion_mode(os.environ.get("MEDO_MOTION_MODE", "normal"))
if MODE == "reduced" and getattr(scenes, "SUPPORTS_REDUCED_MOTION", False) is not True:
    raise SystemExit("Reduced motion requires an explicit SUPPORTS_REDUCED_MOTION=True in scenes.py")
N = round(total * FPS)
if os.environ.get("REEL_MAXFRAMES"):
    N = min(N, int(os.environ["REEL_MAXFRAMES"]))  # smoke test only
if N <= 0:
    raise SystemExit("render frame count must be positive")

# Text motion is an explicit agent decision per scene. When a measured timeline exists,
# refuse to render until plan/text-direction.json is complete (no default style).
beats_p = PROJECT / "plan" / "beats.json"
if beats_p.is_file():
    beats = json.loads(beats_p.read_text(encoding="utf-8"))
    report = td.validate(td.load(PROJECT), beats, td.load_copy(PROJECT), td.load_fonts(PROJECT) or None)
    if report["errors"]:
        raise SystemExit("Text direction incomplete — the agent must choose styles per scene:\n"
                         + "\n".join(report["errors"]))

OUT = PROJECT / "out"
OUT.mkdir(parents=True, exist_ok=True)
ranges = expected_chunks(N, CH)
# presenter.py searches the repository-level assets/poses as its secondary source.
# Include that exact fallback tree in the signature so fallback sprite changes invalidate cache.
STUDIO_ASSETS = HERE.parents[2] / "assets" / "poses"
signature = build_signature(
    HERE, PROJECT / "assets", N, CH, B, FPS, W, H, FONT, STUDIO_ASSETS, motion_mode=MODE
)
signature_file = OUT / "chunks.sig"
previous_signature = None
try:
    previous_signature = signature_file.read_text(encoding="ascii").strip()
except OSError:
    pass

# Missing signatures are treated as cache misses, never as permission to reuse old chunks.
if previous_signature != signature:
    for stale in OUT.glob("c_*.mp4*"):
        if stale.is_file():
            stale.unlink()
    for stale_output in (OUT / "video_only.mp4", OUT / "list.txt"):
        if stale_output.exists():
            stale_output.unlink()
    print("source/cache signature changed or missing: old chunks invalidated")

# Commit the signature atomically so an interrupted write cannot look valid.
signature_tmp = signature_file.with_suffix(".sig.tmp")
signature_tmp.write_text(signature + "\n", encoding="ascii")
os.replace(signature_tmp, signature_file)

log_path = PROJECT / "out_log.txt"
with log_path.open("a", encoding="utf-8") as log:
    expected_parts = []
    for start, end in ranges:
        part = OUT / f"c_{start:05d}_{end:05d}.mp4"
        expected_parts.append(part)
        result = subprocess.run(
            [sys.executable, str(HERE / "chunk.py"), str(start), str(end)],
            stdout=log, stderr=log, check=False,
        )
        if result.returncode != 0:
            print(f"chunk failed {start}:{end} - see out_log.txt; re-run to resume")
            raise SystemExit(1)
        if not is_valid_chunk(part, end - start, W, H):
            print(f"chunk invalid after render: {part.name} - see out_log.txt")
            raise SystemExit(1)

    # Only the exact ranges from this run may be concatenated; never glob the cache.
    list_file = OUT / "list.txt"
    with list_file.open("w", encoding="utf-8", newline="\n") as stream:
        for part in expected_parts:
            escaped = str(part.resolve()).replace("\\", "/").replace("'", "'\\''")
            stream.write(f"file '{escaped}'\n")

    final_tmp = OUT / "video_only.tmp.mp4"
    if final_tmp.exists():
        final_tmp.unlink()
    result = subprocess.run(
        [FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
         "-i", str(list_file), "-c", "copy", str(final_tmp)],
        stdout=log, stderr=log, check=False,
    )
    merged = result.returncode == 0 and final_tmp.is_file() and final_tmp.stat().st_size > 0
    if merged:
        merged = is_valid_chunk(final_tmp, N, W, H)
    if merged:
        os.replace(final_tmp, OUT / "video_only.mp4")
        log.write("VIDEODONE\n")
    else:
        if final_tmp.exists():
            final_tmp.unlink()
        old_final = OUT / "video_only.mp4"
        if old_final.exists():
            old_final.unlink()
        log.write("CONCAT_FAILED\n")
        print(f"CONCAT_FAILED {len(expected_parts)} expected chunks, N={N} - see out_log.txt")
        raise SystemExit(1)

print(f"VIDEODONE {len(ranges)} chunks, N={N}")
