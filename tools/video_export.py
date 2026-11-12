#!/usr/bin/env python3
"""Video export (B7ب): the project to an H.264 MP4 through PyAV — no external ffmpeg binary.

The frames come from the same reference renderer the timeline uses, so the file matches the preview; PyAV's
bundled FFmpeg does the encoding. Optional audio is muxed from a WAV produced by `audio_export.py`.

    python3 tools/video_export.py build project.json -o out/reel.mp4
    python3 tools/video_export.py build project.json -o out/reel.mp4 --audio out/mix.wav
    python3 tools/video_export.py check out/reel.mp4.json

Exit codes: 0 ok · 1 project/encode refused (M-codes) · 2 unreadable file or missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402
from unified_project_time import frame_ticks  # noqa: E402
from unified_reference_preview import PreviewError, render_frame  # noqa: E402

VERSION = 1
MAX_FRAMES = 1800
CODEC = "libx264"
ROOT_FIELDS = {"version", "source", "video", "audio", "file", "totals", "decode"}


class VideoError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _av():
    try:
        import av  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - the studio venv ships PyAV
        raise VideoError("M03", "PyAV is required to encode MP4 (pip install av)") from exc
    if CODEC not in av.codecs_available:
        raise VideoError("M03", f"{CODEC} is not available in this PyAV build")
    return av


def project_frames(project: dict) -> int:
    return -(-project["duration"] // frame_ticks(project))


def build(project: dict, root: Path, out_path: Path, *, audio: Path | None = None,
          crf: int = 20, preset: str = "medium", max_frames: int = MAX_FRAMES) -> dict:
    errors = validate(project)
    if errors:
        raise VideoError("M01", "project is invalid: " + "; ".join(errors))
    fps = project["profile"]["fps"]
    if fps["den"] != 1:
        raise VideoError("M01", f"MP4 export needs an integer rate (got {fps['num']}/{fps['den']})")
    rate = fps["num"]
    width, height = project["profile"]["width"], project["profile"]["height"]
    if width % 2 or height % 2:
        raise VideoError("M01", f"{width}×{height} must be even for H.264 4:2:0")
    total = project_frames(project)
    if total > max_frames:
        raise VideoError("M04", f"{total} frames exceed the {max_frames}-frame export cap")
    if not 0 <= crf <= 51:
        raise VideoError("M01", "crf must be within 0..51")

    av = _av()
    import numpy as np  # noqa: PLC0415 - PyAV's from_ndarray needs it anyway

    out_path.parent.mkdir(parents=True, exist_ok=True)
    container = av.open(str(out_path), mode="w", format="mp4", options={"movflags": "+faststart"})
    try:
        stream = container.add_stream(CODEC, rate=rate)
        stream.width, stream.height = width, height
        stream.pix_fmt = "yuv420p"
        # x264's frame threading makes the byte output vary run to run; a single thread keeps the file
        # reproducible. The cost is speed, not quality.
        stream.options = {"crf": str(crf), "preset": preset, "threads": "1"}
        stream.codec_context.thread_count = 1

        audio_stream = None
        resampler = None
        if audio is not None:
            if not Path(audio).is_file():
                raise VideoError("M06", f"audio file {audio} does not exist")
            audio_stream = container.add_stream("aac", rate=project["profile"]["sampleRate"])
            audio_stream.layout = "mono"

        frame_hashes = []
        for index in range(total):
            try:
                frame = render_frame(project, Path(root), index)
            except PreviewError as exc:
                raise VideoError("M02", f"frame {index}: {exc.code} {exc.path} {exc.message}") from exc
            payload = bytes(frame["pixels"])
            frame_hashes.append(_sha(payload))
            rgb = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 4)[:, :, :3]
            video_frame = av.VideoFrame.from_ndarray(np.ascontiguousarray(rgb), format="rgb24")
            video_frame.pts = index
            for packet in stream.encode(video_frame):
                container.mux(packet)

        for packet in stream.encode():
            container.mux(packet)

        if audio_stream is not None:
            import wave  # noqa: PLC0415

            with wave.open(str(audio), "rb") as handle:
                rate_in, channels = handle.getframerate(), handle.getnchannels()
                if handle.getsampwidth() != 2:
                    raise VideoError("M06", "audio muxing reads 16-bit PCM WAV only")
                raw = handle.readframes(handle.getnframes())
            resampler = av.AudioResampler(format="fltp", layout="mono", rate=audio_stream.rate)
            block = 4096
            import array  # noqa: PLC0415

            values = array.array("h")
            values.frombytes(raw)
            if sys.byteorder == "big":
                values.byteswap()
            mono = [sum(values[i * channels:(i + 1) * channels]) / (channels * 32768.0)
                    for i in range(len(values) // channels)]
            for start in range(0, len(mono), block):
                chunk = np.array(mono[start:start + block], dtype=np.float32).reshape(1, -1)
                frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="mono")
                frame.rate = rate_in
                for converted in resampler.resample(frame):
                    for packet in audio_stream.encode(converted):
                        container.mux(packet)
            for converted in resampler.resample(None):
                for packet in audio_stream.encode(converted):
                    container.mux(packet)
            for packet in audio_stream.encode():
                container.mux(packet)
    finally:
        container.close()

    frame_root = _sha("".join(frame_hashes).encode("ascii"))
    probe = inspect(out_path)
    if probe["videoFrames"] != total:
        raise VideoError("M05", f"encoded {probe['videoFrames']} frames but rendered {total}")
    payload = out_path.read_bytes()
    manifest = {
        "version": VERSION,
        "source": {"name": project.get("name") or project["id"],
                   "sha256": _sha(json.dumps(project, ensure_ascii=False, sort_keys=True).encode("utf-8"))},
        "video": {"width": width, "height": height, "fps": rate, "frames": total, "codec": CODEC,
                  "crf": crf, "preset": preset, "frameRoot": frame_root},
        "audio": None if audio is None else {"file": Path(audio).name,
                                             "sha256": _sha(Path(audio).read_bytes())},
        "file": {"name": out_path.name, "sha256": _sha(payload), "bytes": len(payload)},
        "totals": {"durationSeconds": round(total / rate, 6), "encodedFrames": probe["videoFrames"],
                   "encodedDuration": probe["duration"]},
    }
    manifest["decode"] = {"frames": probe["videoFrames"], "sha256": decode_fingerprint(out_path)}
    return manifest


def decode_fingerprint(path: Path) -> str:
    """Hash the decoded RGB stream: the MP4's bytes are not reproducible, its picture sequence is."""
    av = _av()
    digest = hashlib.sha256()
    with av.open(str(path)) as container:
        for frame in container.decode(video=0):
            digest.update(frame.to_ndarray(format="rgb24").tobytes())
    return digest.hexdigest()


def inspect(path: Path) -> dict:
    """Read the file back: frames, rate, duration. Verification, not trust."""
    av = _av()
    frames = 0
    rate = 0.0
    duration = 0.0
    streams = {"video": 0, "audio": 0}
    with av.open(str(path)) as container:
        for stream in container.streams:
            streams[stream.type] = streams.get(stream.type, 0) + 1
        video = next((s for s in container.streams if s.type == "video"), None)
        if video is not None:
            rate = float(video.average_rate) if video.average_rate else 0.0
            for _ in container.decode(video):
                frames += 1
        duration = float(container.duration / av.time_base) if container.duration else 0.0
    return {"videoFrames": frames, "fps": rate, "duration": round(duration, 6), "streams": streams}


def validate_manifest(data: dict) -> list[str]:
    """M05: the sidecar must match a file that is still there and still hashed the same."""
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return [f"M01 version: only version {VERSION} is accepted"]
    if set(data) != ROOT_FIELDS:
        return [f"M01 root: needs exactly {sorted(ROOT_FIELDS)}"]
    errors: list[str] = []
    video = data["video"]
    if video["fps"] * data["totals"]["encodedFrames"] and abs(
            video["frames"] / video["fps"] - data["totals"]["durationSeconds"]) > 1e-6:
        errors.append("M05 totals.durationSeconds: does not match frames ÷ fps")
    if data["file"]["bytes"] <= 0:
        errors.append("M05 file.bytes: empty output")
    if len(data["file"]["sha256"]) != 64:
        errors.append("M05 file.sha256: 64 hex characters required")
    if len(video.get("frameRoot", "")) != 64:
        errors.append("M05 video.frameRoot: 64 hex characters required")
    if data["decode"]["frames"] != data["totals"]["encodedFrames"]:
        errors.append("M05 decode.frames: differs from the encoded count")
    return errors


def verify(manifest: dict, path: Path, *, decode: bool = False) -> list[str]:
    errors = validate_manifest(manifest)
    if errors:
        return errors
    if not Path(path).is_file():
        return errors + [f"M05 {path}: missing"]
    if _sha(Path(path).read_bytes()) != manifest["file"]["sha256"]:
        errors.append(f"M05 {path}: bytes no longer match the manifest")
    if decode and decode_fingerprint(path) != manifest["decode"]["sha256"]:
        errors.append(f"M05 {path}: decoded pictures no longer match the manifest")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render a project to an H.264 MP4 with PyAV.")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="project.json → reel.mp4 + reel.mp4.json")
    build_cmd.add_argument("project", type=Path)
    build_cmd.add_argument("-o", "--out", type=Path, required=True)
    build_cmd.add_argument("--audio", type=Path, default=None)
    build_cmd.add_argument("--crf", type=int, default=20)
    build_cmd.add_argument("--preset", default="medium")
    build_cmd.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    check = sub.add_parser("check", help="verify a video manifest against the file")
    check.add_argument("manifest", type=Path)
    check.add_argument("--file", type=Path, default=None)
    check.add_argument("--decode", action="store_true", help="also re-decode and compare pictures")
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
            return 2
        target = args.file or args.manifest.parent / data.get("file", {}).get("name", "")
        errors = verify(data, target, decode=args.decode)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid video · {data['totals']['encodedFrames']} frames · {data['video']['width']}×"
              f"{data['video']['height']} · {data['video']['fps']} fps · {data['file']['bytes']} bytes")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    try:
        manifest = build(project, args.project.parent, args.out, audio=args.audio, crf=args.crf,
                         preset=args.preset, max_frames=args.max_frames)
    except VideoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    sidecar = args.out.with_suffix(args.out.suffix + ".json")
    sidecar.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} · {manifest['totals']['encodedFrames']} frames · "
          f"{manifest['video']['width']}×{manifest['video']['height']} · {manifest['video']['fps']} fps · "
          f"{manifest['file']['bytes']} bytes · {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
