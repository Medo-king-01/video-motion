#!/usr/bin/env python3
"""Ingest one video file into a deterministic media report — the only B4 step that touches a codec.

The report is data: size, fps, VFR flag, and a per-frame **visual delta** series produced from a
16×9 RGB grid. `cut_plan.py` reads only this report, so the editorial decisions are reviewable
without opening the video again, and rerunning the ingest on the same bytes gives the same JSON.

    python3 tools/video_ingest.py clip.mp4 -o out/media-report.json
    python3 tools/video_ingest.py clip.mp4 --json          # summary only

Exit codes: 0 report written · 2 unreadable/too long/no video stream · 3 PyAV missing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GRID_W, GRID_H = 16, 9
MAX_FRAMES = 7200  # 4 minutes at 30 fps: a review clip, not a feature
VFR_TOLERANCE = 0.05
VFR_SHARE = 0.02


class IngestError(RuntimeError):
    """Anything that makes the file unusable — always surfaces as exit code 2."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def signature(rgb) -> list[int]:
    """16×9 block means per RGB channel (0..255), integer — stable, and blind to neither hue nor luma.

    A luma-only grid cannot see a green→red cut; the B4 detector must, so colour is part of the signal.
    """
    import numpy as np  # noqa: PLC0415

    h, w = rgb.shape[:2]
    bh, bw = max(1, h // GRID_H), max(1, w // GRID_W)
    cropped = rgb[: bh * GRID_H, : bw * GRID_W, :3].astype("float32")
    blocks = cropped.reshape(GRID_H, bh, GRID_W, bw, 3).mean(axis=(1, 3))
    return [int(round(v)) for v in blocks.reshape(-1)]


def delta(a: list[int], b: list[int]) -> float:
    """Mean absolute difference between two signatures, rounded to 3 decimals."""
    return round(sum(abs(x - y) for x, y in zip(a, b, strict=True)) / len(a), 3)


def _fps_parts(rate) -> float:
    try:
        value = float(rate)
    except (TypeError, ValueError):
        return 0.0
    return round(value, 3)


def _probe(container, path: Path) -> dict:
    import av  # noqa: PLC0415

    stream = next((s for s in container.streams if s.type == "video"), None)
    if stream is None:
        raise IngestError(f"{path.name}: no video stream")
    if not stream.average_rate:
        raise IngestError(f"{path.name}: video stream has no frame rate")
    fps = _fps_parts(stream.average_rate)
    if fps <= 0:
        raise IngestError(f"{path.name}: video stream has an invalid frame rate")
    duration = 0.0
    if stream.duration is not None and stream.time_base is not None:
        duration = float(stream.duration * stream.time_base)
    elif container.duration:
        duration = float(container.duration / av.time_base)
    if duration <= 0:
        raise IngestError(f"{path.name}: could not read a positive duration")
    return {
        "width": int(stream.codec_context.width),
        "height": int(stream.codec_context.height),
        "fps": fps,
        "duration": round(duration, 3),
        "codec": stream.codec_context.name or "unknown",
        "container": container.format.name or "unknown",
    }


def _decode(path: Path, max_frames: int) -> tuple[dict, list[float], list[int], int]:
    import av  # noqa: PLC0415

    with av.open(str(path)) as container:
        meta = _probe(container, path)
        stream = container.streams.video[0]
        pts: list[float] = []
        deltas: list[int] = []
        prev: list[int] | None = None
        decoded = 0
        for frame in container.decode(stream):
            if decoded >= max_frames:
                raise IngestError(
                    f"{path.name}: more than {max_frames} frames — trim the clip or raise --max-frames")
            sig = signature(frame.to_ndarray(format="rgb24"))
            if prev is not None:
                deltas.append(delta(prev, sig))
            prev = sig
            pts.append(round(float(frame.pts * stream.time_base), 4) if frame.pts is not None else -1.0)
            decoded += 1
    if decoded < 2:
        raise IngestError(f"{path.name}: fewer than two decodable frames")
    return meta, pts, deltas, decoded


def _vfr(pts: list[float], fps: float) -> bool:
    """True when the frame timestamps drift from a constant cadence more than the tolerance."""
    if len(pts) < 3 or fps <= 0:
        return False
    step = 1.0 / fps
    bad = 0
    for a, b in zip(pts[:-1], pts[1:], strict=True):
        if a < 0 or b < 0:
            continue
        if abs((b - a) - step) > step * VFR_TOLERANCE:
            bad += 1
    return bad / max(1, len(pts) - 1) > VFR_SHARE


def ingest(path: Path, *, max_frames: int = MAX_FRAMES) -> dict:
    """Read the file once; return the JSON-able report."""
    path = Path(path)
    if not path.exists():
        raise IngestError(f"cannot read {path}")
    try:
        import av  # noqa: F401, PLC0415
    except ImportError as exc:  # pragma: no cover - exercised only on a broken install
        raise SystemExit("PyAV is required for ingest (pip install av==16.0.1); B4 will not shell out to ffmpeg") from exc
    meta, pts, deltas, frames = _decode(path, max_frames)
    fps = meta["fps"]
    duration = meta["duration"]
    if abs(frames / fps - duration) > max(0.15, duration * 0.05):
        # container says one thing, the decoded stream another: trust the stream we actually measured
        duration = round(frames / fps, 3)
    return {
        "version": 1,
        "source": {
            "name": path.name,
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        },
        "video": {
            **meta,
            "duration": duration,
            "frames": frames,
            "vfr": _vfr(pts, fps),
        },
        "sampling": {"grid": [GRID_W, GRID_H], "decoded": frames, "step": 1, "maxFrames": max_frames},
        "deltas": deltas,
    }


def summary(report: dict) -> str:
    v = report["video"]
    return (f"Ingested {report['source']['name']}: {v['width']}×{v['height']} · {v['fps']:g} fps · "
            f"{v['duration']:.2f}s · {v['frames']} frames · VFR {'yes' if v['vfr'] else 'no'} · "
            f"{len(report['deltas'])} deltas")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest a video into a deterministic media report.")
    parser.add_argument("video", type=Path)
    parser.add_argument("-o", "--out", type=Path, help="write the report here")
    parser.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    parser.add_argument("--json", action="store_true", help="print the summary as JSON")
    args = parser.parse_args(argv)
    try:
        report = ingest(args.video, max_frames=args.max_frames)
    except IngestError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    payload = summary(report)
    if args.json:
        v = report["video"]
        print(json.dumps({"name": report["source"]["name"], "width": v["width"], "height": v["height"],
                          "fps": v["fps"], "duration": v["duration"], "frames": v["frames"],
                          "vfr": v["vfr"], "deltas": len(report["deltas"])}, ensure_ascii=False))
    else:
        print(payload)
        if args.out:
            print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
