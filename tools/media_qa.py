#!/usr/bin/env python3
"""Post-render Final Media QA gate for P, K, R, and Hybrid outputs.

    python3 tools/media_qa.py out/master.mp4 --vo out/vo24.wav --beats plan/beats.json
    python3 tools/media_qa.py out/video_only.mp4 --mode video-only
    python3 tools/media_qa.py out/master.mp4 --json cache/media-qa.json --sheet cache/media-sheet.png

Verifies the rendered file itself — not just that a render subprocess exited 0:
- `Q00`: container readability, H.264/yuv420p stream contract, and MP4 `faststart` (`moov` before `mdat`)
- `Q01`: locked `1080x1920 @ 30fps`, full frame decodability, and duration sync with VO / `plan/beats.json`
- `Q02`: master bitrate floor (`>= 2.5 Mbps`, hard reject `< 2.0 Mbps`, per `AGENTS.md` §7 and `brand.json`)
- `Q03`: non-blank frame 0 (rendered counterpart to lint `S06`) and unintended black frames
- `Q04`: continuous static/frozen holds exceeding `brand.json -> motion.idle_hold_max_s` (`2.5s`)
- `Q05`: AAC audio presence, EBU R128 loudness (`-14.5 +/- 0.3 LUFS`), True Peak (`<= -1.5 dBTP`), clipping, and dead silence
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
sys.path.insert(0, str(ROOT / "tools" / "lib"))
sys.path.insert(0, str(SKILL / "scripts"))
import media_bin  # noqa: E402
from _safe_paths import checked_path  # noqa: E402


def load_brand_defaults() -> dict[str, Any]:
    defaults = {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "idle_hold_max_s": 2.5,
        "lufs": -14.5,
        "lufs_tolerance": 0.3,
        "true_peak_max_dbtp": -1.5,
        "min_mbps": 2.5,
        "reject_mbps": 2.0,
    }
    brand_path = SKILL / "brand" / "brand.json"
    if not brand_path.is_file():
        return defaults
    try:
        brand = json.loads(brand_path.read_text(encoding="utf-8"))
        canvas = brand.get("canvas", {})
        motion = brand.get("motion", {})
        audio = brand.get("audio", {})
        export = brand.get("export", {})
        defaults["width"] = int(canvas.get("w", defaults["width"]))
        defaults["height"] = int(canvas.get("h", defaults["height"]))
        defaults["fps"] = int(canvas.get("fps", defaults["fps"]))
        defaults["idle_hold_max_s"] = float(motion.get("idle_hold_max_s", defaults["idle_hold_max_s"]))
        defaults["lufs"] = float(audio.get("lufs", defaults["lufs"]))
        defaults["lufs_tolerance"] = float(audio.get("lufs_tolerance", defaults["lufs_tolerance"]))
        defaults["true_peak_max_dbtp"] = float(audio.get("true_peak_max_dbtp", defaults["true_peak_max_dbtp"]))
        defaults["min_mbps"] = float(export.get("min_mbps", defaults["min_mbps"]))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return defaults


def scan_mp4_atoms(path: Path) -> dict[str, Any]:
    """Read top-level ISO BMFF / MP4 box headers to verify `moov` precedes `mdat` (`faststart`)."""
    atoms: list[dict[str, Any]] = []
    size = path.stat().st_size
    with path.open("rb") as handle:
        pos = 0
        while pos + 8 <= size:
            handle.seek(pos)
            header = handle.read(16)
            if len(header) < 8:
                break
            length = int.from_bytes(header[:4], "big")
            kind = header[4:8].decode("latin1", errors="replace")
            if length == 1:
                if len(header) < 16:
                    break
                length = int.from_bytes(header[8:16], "big")
            elif length == 0:
                length = size - pos
            atoms.append({"type": kind, "offset": pos, "size": length})
            if length < 8:
                break
            pos += length
    moov = next((a["offset"] for a in atoms if a["type"] == "moov"), None)
    mdat = next((a["offset"] for a in atoms if a["type"] == "mdat"), None)
    return {
        "atoms": [a["type"] for a in atoms],
        "moov_offset": moov,
        "mdat_offset": mdat,
        "faststart": bool(moov is not None and mdat is not None and moov < mdat),
    }


def _frame_visual_metrics(rgb: np.ndarray) -> dict[str, float]:
    sub = rgb[::4, ::4].astype(np.float32)
    luma = 0.2126 * sub[..., 0] + 0.7152 * sub[..., 1] + 0.0722 * sub[..., 2]
    gx = np.abs(luma[:, 1:] - luma[:, :-1])
    gy = np.abs(luma[1:, :] - luma[:-1, :])
    grad = np.maximum(gx[:-1, :], gy[:, :-1]) if gx.shape[0] > 1 and gy.shape[1] > 1 else np.zeros((1, 1), np.float32)
    h, w = grad.shape
    y0, y1 = int(round(h * (200.0 / 1920.0))), int(round(h * (1500.0 / 1920.0)))
    x0, x1 = max(0, int(round(w * (40.0 / 1080.0)))), max(1, int(round(w * (1040.0 / 1080.0))))
    zone = grad[y0:max(y0 + 1, y1), x0:max(x0 + 1, x1)]
    strong_pct = float((zone > 55.0).mean() * 100.0) if zone.size else 0.0
    return {
        "sub": sub,
        "luma_mean": float(luma.mean()),
        "luma_p99": float(np.percentile(luma, 99)),
        "grad_p995": float(np.percentile(grad, 99.5)),
        "grad_max": float(grad.max()),
        "strong_pct": strong_pct,
    }


def _audio_duration_seconds(path: Path) -> float:
    import av  # noqa: PLC0415

    with av.open(str(path)) as container:
        if container.duration is not None and container.duration > 0:
            return float(container.duration) / 1_000_000.0
        streams = [s for s in container.streams if s.type == "audio"]
        if not streams:
            raise ValueError(f"no audio stream in {path}")
        stream = streams[0]
        total_samples = 0
        rate = int(stream.codec_context.sample_rate or 0)
        for frame in container.decode(stream):
            total_samples += frame.samples
            if not rate and frame.sample_rate:
                rate = int(frame.sample_rate)
        if rate <= 0 or total_samples <= 0:
            raise ValueError(f"could not measure audio duration of {path}")
        return total_samples / float(rate)


def _max_silence_span_seconds(samples_mono: np.ndarray, sample_rate: int, threshold_dbfs: float = -52.0) -> tuple[float, list[dict[str, float]]]:
    if sample_rate <= 0 or samples_mono.size == 0:
        return 0.0, []
    win = max(1, int(sample_rate * 0.05))
    n_win = samples_mono.size // win
    if n_win == 0:
        return 0.0, []
    trimmed = samples_mono[: n_win * win].reshape(n_win, win)
    rms = np.sqrt(np.mean(trimmed * trimmed, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms)
    silent = db < threshold_dbfs
    spans: list[dict[str, float]] = []
    run_start: int | None = None
    for idx, is_silent in enumerate(silent):
        if is_silent and run_start is None:
            run_start = idx
        elif not is_silent and run_start is not None:
            dur = (idx - run_start) * (win / sample_rate)
            if dur >= 0.4:
                spans.append({
                    "start_s": round(run_start * (win / sample_rate), 3),
                    "end_s": round(idx * (win / sample_rate), 3),
                    "duration_s": round(dur, 3),
                })
            run_start = None
    if run_start is not None:
        dur = (n_win - run_start) * (win / sample_rate)
        if dur >= 0.4:
            spans.append({
                "start_s": round(run_start * (win / sample_rate), 3),
                "end_s": round(n_win * (win / sample_rate), 3),
                "duration_s": round(dur, 3),
            })
    longest = max((s["duration_s"] for s in spans), default=0.0)
    return longest, spans


def _decode_audio_mono(path: Path) -> dict[str, Any]:
    import av  # noqa: PLC0415

    with av.open(str(path)) as container:
        audio_streams = [s for s in container.streams if s.type == "audio"]
        if not audio_streams:
            return {"present": False}
        stream = audio_streams[0]
        codec_name = str(stream.codec_context.name or "")
        sample_rate = int(stream.codec_context.sample_rate or 0)
        channels = int(stream.codec_context.channels or 0)
        chunks: list[np.ndarray] = []
        clipped_samples = 0
        total_samples = 0
        peak = 0.0
        for frame in container.decode(stream):
            if not sample_rate and frame.sample_rate:
                sample_rate = int(frame.sample_rate)
            arr = frame.to_ndarray()
            if np.issubdtype(arr.dtype, np.integer):
                info = np.iinfo(arr.dtype)
                scale = float(max(abs(info.min), info.max))
                flt = arr.astype(np.float32) / scale
            else:
                flt = arr.astype(np.float32)
            if flt.ndim == 2:
                # PyAV planar: (channels, samples) or packed: (1, samples * channels)
                if flt.shape[0] <= 8 and flt.shape[1] >= flt.shape[0]:
                    abs_max = float(np.max(np.abs(flt))) if flt.size else 0.0
                    clipped_samples += int(np.sum(np.abs(flt) >= 0.9995))
                    total_samples += int(flt.size)
                    mono = flt.mean(axis=0)
                else:
                    abs_max = float(np.max(np.abs(flt))) if flt.size else 0.0
                    clipped_samples += int(np.sum(np.abs(flt) >= 0.9995))
                    total_samples += int(flt.size)
                    mono = flt.mean(axis=1)
            else:
                abs_max = float(np.max(np.abs(flt))) if flt.size else 0.0
                clipped_samples += int(np.sum(np.abs(flt) >= 0.9995))
                total_samples += int(flt.size)
                mono = flt.ravel()
            if abs_max > peak:
                peak = abs_max
            chunks.append(mono.astype(np.float32, copy=False))

    mono_all = np.concatenate(chunks) if chunks else np.zeros(0, dtype=np.float32)
    duration_s = (mono_all.size / float(sample_rate)) if sample_rate > 0 else 0.0
    rms = float(np.sqrt(np.mean(mono_all * mono_all))) if mono_all.size else 0.0
    rms_dbfs = 20.0 * math.log10(max(rms, 1e-9))
    peak_dbfs = 20.0 * math.log10(max(peak, 1e-9))
    longest_silence, spans = _max_silence_span_seconds(mono_all, sample_rate)
    return {
        "present": True,
        "codec": codec_name,
        "sample_rate": sample_rate,
        "channels": channels,
        "duration_s": round(duration_s, 4),
        "rms_dbfs": round(rms_dbfs, 2),
        "sample_peak_dbfs": round(peak_dbfs, 2),
        "clipped_samples": clipped_samples,
        "total_samples": total_samples,
        "clipped_ratio": round(clipped_samples / max(total_samples, 1), 6),
        "max_silence_s": round(longest_silence, 3),
        "silence_spans": spans[:10],
    }


def _measure_loudnorm(ffmpeg_exe: str, path: Path, target_lufs: float, target_tp: float) -> dict[str, Any]:
    cmd = [
        ffmpeg_exe, "-hide_banner", "-nostats", "-i", str(path),
        "-af", f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=180)
    stderr = proc.stderr or ""
    if "{" not in stderr or "}" not in stderr:
        return {"measured": False, "reason": f"ffmpeg loudnorm produced no JSON (exit {proc.returncode})"}
    try:
        raw = json.loads(stderr[stderr.rindex("{"): stderr.rindex("}") + 1])
        input_i = float(raw["input_i"])
        input_tp = float(raw["input_tp"])
        input_lra = float(raw.get("input_lra", 0.0))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"measured": False, "reason": f"non-numeric loudnorm output: {error}"}
    if not (math.isfinite(input_i) and math.isfinite(input_tp)):
        return {"measured": False, "reason": "clip too short or silent for EBU R128 integrated loudness"}
    return {
        "measured": True,
        "integrated_lufs": round(input_i, 2),
        "true_peak_dbtp": round(input_tp, 2),
        "lra_lu": round(input_lra, 2),
    }


def _write_contact_sheet(
    sheet_path: Path,
    sampled_frames: list[tuple[int, float, np.ndarray, str]],
) -> None:
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    if not sampled_frames:
        return
    cols = min(4, len(sampled_frames))
    rows = (len(sampled_frames) + cols - 1) // cols
    cell_w, cell_h = 270, 480
    pad, label_h = 12, 32
    sheet = Image.new(
        "RGB",
        (cols * (cell_w + pad) + pad, rows * (cell_h + label_h + pad) + pad),
        (10, 10, 10),
    )
    draw = ImageDraw.Draw(sheet)
    font_candidates = sorted((ROOT / "assets" / "fonts").rglob("Cairo*Regular*.ttf"))
    try:
        font = ImageFont.truetype(str(font_candidates[0]), 15) if font_candidates else ImageFont.load_default()
    except Exception:  # noqa: BLE001
        font = ImageFont.load_default()

    for idx, (frame_no, ts, rgb, tag) in enumerate(sampled_frames):
        r, c = divmod(idx, cols)
        x = pad + c * (cell_w + pad)
        y = pad + r * (cell_h + label_h + pad)
        thumb = Image.fromarray(rgb, "RGB").resize((cell_w, cell_h), Image.BILINEAR)
        sheet.paste(thumb, (x, y))
        border = (203, 39, 27) if tag else (113, 113, 122)
        draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline=border, width=3 if tag else 1)
        caption = f"#{frame_no} · {ts:.2f}s" + (f" · {tag}" if tag else "")
        draw.text((x + 4, y + cell_h + 6), caption, font=font, fill=(243, 242, 241) if not tag else (217, 127, 104))

    sheet_path.parent.mkdir(parents=True, exist_ok=True)
    with sheet_path.open("xb") as stream:
        sheet.save(stream, format="PNG")


def _safe_abs(path: Path) -> Path:
    """Validate path against symlinks/traversal BEFORE dereferencing."""
    checked_path(Path(os.path.abspath(path)))
    return checked_path(path.resolve())


def inspect_media(
    media_path: Path,
    *,
    mode: str = "master",
    vo_path: Path | None = None,
    beats_path: Path | None = None,
    expected_frames: int | None = None,
    min_mbps: float | None = None,
    max_hold_s: float | None = None,
    lufs_target: float | None = None,
    lufs_tol: float | None = None,
    tp_max_dbtp: float | None = None,
    sheet_path: Path | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Inspect a rendered MP4 and return a structured `PASS / FAIL / INCOMPLETE` report."""
    if mode not in ("master", "preview", "video-only"):
        raise ValueError(f"Unsupported QA mode: {mode}")
    media = _safe_abs(media_path)
    if vo_path is not None:
        vo_path = _safe_abs(vo_path)
    if beats_path is not None:
        beats_path = _safe_abs(beats_path)
    if sheet_path is not None:
        sheet_path = _safe_abs(sheet_path)
        if sheet_path.exists():
            raise ValueError(f"Refusing to overwrite existing contact sheet: {sheet_path}")

    brand = load_brand_defaults()
    req_w, req_h, req_fps = brand["width"], brand["height"], brand["fps"]
    hold_limit = float(brand["idle_hold_max_s"] if max_hold_s is None else max_hold_s)
    mbps_floor = float(brand["min_mbps"] if min_mbps is None else min_mbps)
    mbps_reject = float(brand["reject_mbps"]) if min_mbps is None else mbps_floor
    target_lufs = float(brand["lufs"] if lufs_target is None else lufs_target)
    tol_lufs = float(brand["lufs_tolerance"] if lufs_tol is None else lufs_tol)
    ceil_tp = float(brand["true_peak_max_dbtp"] if tp_max_dbtp is None else tp_max_dbtp)

    items: list[dict[str, str]] = []
    incomplete_reasons: list[str] = []

    def add(level: str, code: str, msg: str) -> None:
        items.append({"level": level, "code": code, "msg": msg})

    if not media.is_file() or media.stat().st_size == 0:
        add("error", "Q00", f"Media file missing or empty: {media}")
        return {
            "version": 1,
            "status": "fail",
            "mode": mode,
            "media": str(media),
            "items": items,
            "errors": [i for i in items if i["level"] == "error"],
            "warnings": [],
        }

    import av  # noqa: PLC0415

    atom_info = scan_mp4_atoms(media) if media.suffix.lower() in (".mp4", ".m4v", ".mov") else {
        "atoms": [], "moov_offset": None, "mdat_offset": None, "faststart": False
    }
    if media.suffix.lower() in (".mp4", ".m4v", ".mov"):
        if atom_info["faststart"]:
            add("ok", "Q00", f"MP4 faststart verified (moov@{atom_info['moov_offset']} < mdat@{atom_info['mdat_offset']})")
        elif mode == "master":
            add("error", "Q00", "MP4 is missing +faststart (`moov` atom appears after `mdat`)")
        else:
            add("warn", "Q00", "MP4 does not have `moov` before `mdat` (+faststart recommended)")

    try:
        container = av.open(str(media))
    except Exception as error:  # noqa: BLE001
        add("error", "Q00", f"Cannot open media container: {error}")
        return {
            "version": 1,
            "status": "fail",
            "mode": mode,
            "media": str(media),
            "items": items,
            "errors": [i for i in items if i["level"] == "error"],
            "warnings": [i for i in items if i["level"] == "warn"],
        }

    black_runs: list[dict[str, Any]] = []
    freeze_runs: list[dict[str, Any]] = []
    sampled_sheet: list[tuple[int, float, np.ndarray, str]] = []
    first_frame_metrics: dict[str, float] | None = None

    with container:
        v_streams = [s for s in container.streams if s.type == "video"]
        if len(v_streams) != 1:
            add("error", "Q00", f"Expected exactly 1 video stream, found {len(v_streams)}")
            return {
                "version": 1,
                "status": "fail",
                "mode": mode,
                "media": str(media),
                "items": items,
                "errors": [i for i in items if i["level"] == "error"],
                "warnings": [i for i in items if i["level"] == "warn"],
            }
        vs = v_streams[0]
        v_codec = str(vs.codec_context.name or "")
        v_profile = str(getattr(vs.codec_context, "profile", "") or "")
        v_pix_fmt = str(getattr(vs.codec_context, "pix_fmt", "") or "")
        width = int(vs.codec_context.width or 0)
        height = int(vs.codec_context.height or 0)
        rate = float(vs.average_rate) if vs.average_rate else (float(vs.guessed_rate) if vs.guessed_rate else 0.0)

        if v_codec != "h264":
            add("error", "Q00", f"Video codec must be h264, got {v_codec!r}")
        else:
            add("ok", "Q00", f"Video stream codec h264 ({v_profile or 'unspecified profile'}, {v_pix_fmt})")
        if v_pix_fmt == "yuv420p":
            pass
        elif v_pix_fmt == "yuvj420p":
            add("warn", "Q00", "Pixel format is yuvj420p (full-range); yuv420p is the studio standard")
        else:
            add("error", "Q00", f"Pixel format must be yuv420p, got {v_pix_fmt!r}")
        if mode == "master" and v_codec == "h264" and v_profile and "high" not in v_profile.lower():
            add("warn", "Q00", f"Master expects H.264 High profile, got {v_profile!r}")

        # Geometry & FPS
        if (width, height) == (req_w, req_h):
            add("ok", "Q01", f"Canvas matches locked {req_w}x{req_h}")
        elif mode == "preview" and width > 0 and height > 0 and abs((width / height) - (req_w / req_h)) < 0.015:
            add("warn", "Q01", f"Scaled 9:16 preview resolution {width}x{height} (master requires {req_w}x{req_h})")
        else:
            add("error", "Q01", f"Canvas must be {req_w}x{req_h}, got {width}x{height}")

        if abs(rate - req_fps) <= 0.05:
            add("ok", "Q01", f"Frame rate {rate:.2f} fps matches locked {req_fps} fps")
        elif mode == "preview" and rate > 0:
            add("warn", "Q01", f"Preview frame rate is {rate:.2f} fps (master requires {req_fps} fps)")
        else:
            add("error", "Q01", f"Frame rate must be {req_fps} fps, got {rate:.3f} fps")

        fps_eff = rate if rate > 0 else float(req_fps)
        decoded_frames = 0
        prev_sub: np.ndarray | None = None
        black_start: int | None = None
        freeze_start: int | None = None
        estimated_total = int(vs.frames or 0)
        sample_stride = max(1, (estimated_total // 7)) if estimated_total > 8 else 15
        issue_thumbs: dict[int, tuple[float, np.ndarray, str]] = {}

        try:
            for frame in container.decode(vs):
                rgb = frame.to_ndarray(format="rgb24")
                if rgb.shape[:2] != (height, width):
                    add("error", "Q01", f"Decoded frame {decoded_frames} changed geometry to {rgb.shape[1]}x{rgb.shape[0]}")
                    break
                metrics = _frame_visual_metrics(rgb)
                ts = decoded_frames / fps_eff
                if decoded_frames == 0:
                    first_frame_metrics = {k: round(v, 3) for k, v in metrics.items() if k != "sub"}

                is_black = metrics["luma_p99"] < 12.0 and metrics["grad_max"] < 12.0
                if is_black:
                    if black_start is None:
                        black_start = decoded_frames
                        if len(issue_thumbs) < 4:
                            issue_thumbs[decoded_frames] = (ts, rgb.copy(), "Q03-black")
                elif black_start is not None:
                    black_runs.append({
                        "start_frame": black_start,
                        "end_frame": decoded_frames,
                        "frames": decoded_frames - black_start,
                        "start_s": round(black_start / fps_eff, 3),
                        "end_s": round(decoded_frames / fps_eff, 3),
                    })
                    black_start = None

                if prev_sub is not None:
                    diff = np.abs(metrics["sub"] - prev_sub)
                    is_static = float(diff.mean()) < 0.25 and float(np.percentile(diff, 99)) < 3.0
                    if is_static:
                        if freeze_start is None:
                            freeze_start = decoded_frames - 1
                    elif freeze_start is not None:
                        span_frames = decoded_frames - freeze_start
                        span_s = (span_frames - 1) / fps_eff
                        if span_s > hold_limit:
                            freeze_runs.append({
                                "start_frame": freeze_start,
                                "end_frame": decoded_frames,
                                "frames": span_frames,
                                "start_s": round(freeze_start / fps_eff, 3),
                                "end_s": round((decoded_frames - 1) / fps_eff, 3),
                                "duration_s": round(span_s, 3),
                            })
                        freeze_start = None

                if sheet_path is not None and (decoded_frames == 0 or decoded_frames % sample_stride == 0) and len(sampled_sheet) < 8:
                    sampled_sheet.append((decoded_frames, ts, rgb.copy(), ""))
                if sheet_path is not None and freeze_start is not None:
                    span_s = (decoded_frames - freeze_start) / fps_eff
                    if span_s > hold_limit and freeze_start not in issue_thumbs and len(issue_thumbs) < 4:
                        issue_thumbs[decoded_frames] = (ts, rgb.copy(), "Q04-hold")

                prev_sub = metrics["sub"]
                decoded_frames += 1
        except Exception as error:  # noqa: BLE001
            add("error", "Q01", f"Frame decode failed at frame {decoded_frames}: {error}")

        if black_start is not None:
            black_runs.append({
                "start_frame": black_start,
                "end_frame": decoded_frames,
                "frames": decoded_frames - black_start,
                "start_s": round(black_start / fps_eff, 3),
                "end_s": round(decoded_frames / fps_eff, 3),
            })
        if freeze_start is not None:
            span_frames = decoded_frames - freeze_start
            span_s = max(0.0, (span_frames - 1) / fps_eff)
            if span_s > hold_limit:
                freeze_runs.append({
                    "start_frame": freeze_start,
                    "end_frame": decoded_frames,
                    "frames": span_frames,
                    "start_s": round(freeze_start / fps_eff, 3),
                    "end_s": round(max(0, decoded_frames - 1) / fps_eff, 3),
                    "duration_s": round(span_s, 3),
                })

    if decoded_frames <= 0:
        add("error", "Q01", "Video contains 0 decodable frames")
        video_duration = 0.0
    else:
        video_duration = decoded_frames / fps_eff

    if expected_frames is not None:
        if decoded_frames != expected_frames:
            add("error", "Q01", f"Decoded {decoded_frames} frame(s), expected {expected_frames}")
        else:
            add("ok", "Q01", f"Decoded exact expected {decoded_frames} frame(s)")

    tol_s = max(1.0 / max(fps_eff, 1.0) + 0.02, 0.055)
    if beats_path is not None:
        if not beats_path.is_file():
            add("error", "Q01", f"plan/beats.json not found: {beats_path}")
        else:
            beats = json.loads(beats_path.read_text(encoding="utf-8"))
            b_dur = beats.get("duration")
            if not isinstance(b_dur, (int, float)) or isinstance(b_dur, bool) or float(b_dur) <= 0:
                add("error", "Q01", f"plan/beats.json has no measured duration: {b_dur!r}")
            elif abs(video_duration - float(b_dur)) > tol_s:
                add("error", "Q01", f"Video duration {video_duration:.3f}s disagrees with beats.json {float(b_dur):.3f}s (tol {tol_s:.3f}s)")
            else:
                add("ok", "Q01", f"Video duration {video_duration:.3f}s matches beats.json ({float(b_dur):.3f}s)")

    vo_duration: float | None = None
    vo_max_silence: float | None = None
    if vo_path is not None:
        if not vo_path.is_file():
            add("error", "Q01", f"VO file not found: {vo_path}")
        else:
            try:
                vo_duration = _audio_duration_seconds(vo_path)
                vo_info = _decode_audio_mono(vo_path)
                vo_max_silence = float(vo_info.get("max_silence_s", 0.0)) if vo_info.get("present") else None
                if abs(video_duration - vo_duration) > tol_s:
                    add("error", "Q01", f"Video duration {video_duration:.3f}s disagrees with VO {vo_duration:.3f}s (tol {tol_s:.3f}s)")
                else:
                    add("ok", "Q01", f"Video duration {video_duration:.3f}s matches VO ({vo_duration:.3f}s)")
            except Exception as error:  # noqa: BLE001
                add("error", "Q01", f"Could not inspect VO file {vo_path}: {error}")

    # Q02: Bitrate
    file_bytes = media.stat().st_size
    bitrate_mbps = (file_bytes * 8.0 / max(video_duration, 1e-6)) / 1_000_000.0 if video_duration > 0 else 0.0
    if mode == "master":
        if bitrate_mbps < mbps_reject:
            add("error", "Q02", f"Master bitrate {bitrate_mbps:.2f} Mbps is below rejection floor ({mbps_reject:.2f} Mbps; target >= {mbps_floor:.2f} Mbps)")
        elif bitrate_mbps < mbps_floor:
            add("warn", "Q02", f"Master bitrate {bitrate_mbps:.2f} Mbps is slightly under {mbps_floor:.2f} Mbps target")
        else:
            add("ok", "Q02", f"Master bitrate {bitrate_mbps:.2f} Mbps clears {mbps_floor:.2f} Mbps floor")
    else:
        add("ok", "Q02", f"Bitrate {bitrate_mbps:.2f} Mbps ({mode} mode)")

    # Q03: First frame & black runs
    if first_frame_metrics is not None:
        f0_strong = first_frame_metrics["strong_pct"]
        f0_grad = first_frame_metrics["grad_p995"]
        if first_frame_metrics["luma_p99"] < 12.0 and first_frame_metrics["grad_max"] < 12.0:
            add("error", "Q03", "Frame 0 is black — social players use frame 0 as the thumbnail (S06/Q03)")
            if sheet_path is not None and sampled_sheet and sampled_sheet[0][0] == 0:
                sampled_sheet[0] = (0, 0.0, sampled_sheet[0][2], "Q03-f0")
        elif f0_strong < 0.02 and f0_grad < 15.0:
            add("error", "Q03", f"Frame 0 has no foreground contrast (grad_p995={f0_grad:.1f}) — empty background thumbnail")
            if sheet_path is not None and sampled_sheet and sampled_sheet[0][0] == 0:
                sampled_sheet[0] = (0, 0.0, sampled_sheet[0][2], "Q03-empty")
        elif f0_strong < 0.02 and f0_grad < 30.0:
            add("warn", "Q03", f"Frame 0 has low foreground contrast (grad_p995={f0_grad:.1f}); verify visible subject at t=0")
        else:
            add("ok", "Q03", f"Frame 0 carries visible contrast (grad_p995={f0_grad:.1f}, strong_edges={f0_strong:.2f}%)")

    severe_black = [r for r in black_runs if r["frames"] >= 2 or r["start_frame"] == 0]
    brief_black = [r for r in black_runs if r["frames"] == 1 and r["start_frame"] > 0]
    if severe_black:
        spans_desc = ", ".join(f"{r['start_s']:.2f}s–{r['end_s']:.2f}s ({r['frames']}f)" for r in severe_black[:4])
        add("error", "Q03", f"Unintended black frame run(s): {spans_desc}")
    elif brief_black:
        spans_desc = ", ".join(f"f{r['start_frame']}@{r['start_s']:.2f}s" for r in brief_black[:4])
        add("warn", "Q03", f"Isolated single black frame(s): {spans_desc}")
    else:
        add("ok", "Q03", "No black frame dropouts detected")

    # Q04: Static hold / freeze
    if freeze_runs:
        spans_desc = ", ".join(f"{r['start_s']:.2f}s–{r['end_s']:.2f}s ({r['duration_s']:.2f}s)" for r in freeze_runs[:4])
        add("error", "Q04", f"Static hold exceeds {hold_limit:.1f}s limit: {spans_desc}")
    else:
        add("ok", "Q04", f"No static hold exceeds {hold_limit:.1f}s")

    # Q05: Audio & loudness
    audio_report: dict[str, Any]
    if mode == "video-only":
        audio_info = _decode_audio_mono(media)
        if audio_info.get("present"):
            add("warn", "Q05", f"Audio stream ({audio_info.get('codec')}) present in video-only QA mode")
        else:
            add("ok", "Q05", "Audio check skipped in video-only mode")
        audio_report = {"status": "skipped-video-only", **audio_info}
    else:
        audio_info = _decode_audio_mono(media)
        if not audio_info.get("present"):
            level = "error" if mode == "master" else "warn"
            add(level, "Q05", "No audio stream present" + (" — master delivery requires muxed AAC audio" if mode == "master" else " (silent preview)"))
            audio_report = {"status": "missing", "present": False}
        else:
            a_codec = audio_info["codec"]
            if a_codec != "aac":
                add("error" if mode == "master" else "warn", "Q05", f"Audio codec is {a_codec!r} (master standard is 'aac')")
            else:
                add("ok", "Q05", f"Audio codec aac ({audio_info['sample_rate']} Hz, {audio_info['channels']} ch)")

            a_dur = float(audio_info["duration_s"])
            if video_duration > 0 and abs(a_dur - video_duration) > 0.12:
                add("error", "Q01", f"Audio/video duration drift inside container: video {video_duration:.3f}s vs audio {a_dur:.3f}s")

            if audio_info["rms_dbfs"] < -55.0:
                add("error", "Q05", f"Audio stream is effectively silent ({audio_info['rms_dbfs']:.1f} dBFS) — never ship a silent track as a master")
            else:
                if audio_info["clipped_samples"] >= 4 or audio_info["clipped_ratio"] > 0.0001:
                    add(
                        "error" if mode == "master" else "warn",
                        "Q05",
                        f"Audio sample clipping detected ({audio_info['clipped_samples']} samples, peak {audio_info['sample_peak_dbfs']:.2f} dBFS)",
                    )
                max_sil = float(audio_info["max_silence_s"])
                if vo_max_silence is not None and max_sil >= 1.5 and max_sil > vo_max_silence + 0.6:
                    add("error", "Q05", f"Audio contains {max_sil:.2f}s dead silence not present in VO (max VO pause {vo_max_silence:.2f}s)")
                elif vo_max_silence is None and max_sil >= 3.0:
                    add("warn", "Q05", f"Audio contains a {max_sil:.2f}s silent stretch; verify against the VO")

                ff = media_bin.ffmpeg()
                if ff is None:
                    incomplete_reasons.append("ffmpeg unavailable for EBU R128 loudnorm measurement")
                    add("warn", "Q05", "ffmpeg not found; EBU R128 loudness could not be measured")
                    audio_report = {"status": "incomplete", **audio_info}
                elif video_duration < 1.0:
                    if mode == "master":
                        incomplete_reasons.append(f"clip duration ({video_duration:.2f}s) is under 1.0s EBU R128 gating floor")
                    add("warn", "Q05", f"Clip is {video_duration:.2f}s (< 1.0s); EBU R128 integrated loudness requires >= 1.0s")
                    audio_report = {"status": "too-short", **audio_info}
                else:
                    ln = _measure_loudnorm(ff, media, target_lufs, ceil_tp)
                    audio_info.update(ln)
                    if not ln.get("measured"):
                        if mode == "master":
                            incomplete_reasons.append(str(ln.get("reason", "loudnorm unmeasurable")))
                        add("warn", "Q05", f"Loudness measurement incomplete: {ln.get('reason')}")
                        audio_report = {"status": "incomplete", **audio_info}
                    else:
                        lufs_v = float(ln["integrated_lufs"])
                        tp_v = float(ln["true_peak_dbtp"])
                        lufs_ok = abs(lufs_v - target_lufs) <= tol_lufs + 1e-6
                        tp_ok = tp_v <= ceil_tp + 1e-6
                        lvl = "error" if mode == "master" else "warn"
                        if not lufs_ok:
                            add(lvl, "Q05", f"Integrated loudness {lufs_v:.2f} LUFS outside {target_lufs:.1f} +/- {tol_lufs:.1f} LUFS")
                        if not tp_ok:
                            add(lvl, "Q05", f"True peak {tp_v:.2f} dBTP exceeds ceiling {ceil_tp:.1f} dBTP")
                        if lufs_ok and tp_ok:
                            add("ok", "Q05", f"Loudness {lufs_v:.2f} LUFS and true peak {tp_v:.2f} dBTP meet brand spec")
                        audio_report = {"status": "pass" if (lufs_ok and tp_ok) else "fail", **audio_info}
            if "audio_report" not in locals():
                audio_report = {"status": "fail", **audio_info}

    if sheet_path is not None:
        merged_thumbs = list(sampled_sheet)
        existing_indices = {f_idx for f_idx, _, _, _ in merged_thumbs}
        for f_idx, (ts, rgb, tag) in sorted(issue_thumbs.items()):
            if f_idx not in existing_indices:
                merged_thumbs.append((f_idx, ts, rgb, tag))
        merged_thumbs.sort(key=lambda item: item[0])
        _write_contact_sheet(sheet_path, merged_thumbs)

    errors = [i for i in items if i["level"] == "error"]
    warnings = [i for i in items if i["level"] == "warn"]
    if errors or (strict and warnings):
        status = "fail"
    elif incomplete_reasons:
        status = "incomplete"
    else:
        status = "pass"

    return {
        "version": 1,
        "status": status,
        "mode": mode,
        "strict": strict,
        "media": str(media),
        "container": atom_info,
        "video": {
            "codec": v_codec,
            "profile": v_profile,
            "pix_fmt": v_pix_fmt,
            "width": width,
            "height": height,
            "fps": round(rate, 4),
            "frames": decoded_frames,
            "duration_s": round(video_duration, 4),
            "bitrate_mbps": round(bitrate_mbps, 3),
            "faststart": atom_info["faststart"],
            "first_frame": first_frame_metrics,
            "black_runs": black_runs,
            "freeze_runs": freeze_runs,
        },
        "audio": audio_report,
        "thresholds": {
            "width": req_w,
            "height": req_h,
            "fps": req_fps,
            "min_mbps": mbps_floor,
            "reject_mbps": mbps_reject,
            "idle_hold_max_s": hold_limit,
            "lufs": target_lufs,
            "lufs_tolerance": tol_lufs,
            "true_peak_max_dbtp": ceil_tp,
        },
        "incomplete_reasons": incomplete_reasons,
        "limitations": (
            "Pixel and audio signal QA only: verifies container/stream specs, faststart, bitrate, "
            "frame-0 non-blankness on smooth/subtle grounds, black dropouts, static holds, EBU R128 "
            "loudness, true peak, clipping, and dead silence. Does not replace Arabic glyph visual "
            "reading, factual verification, or layout box collision audits (layout_audit / layout_audit_p)."
        ),
        "items": items,
        "errors": errors,
        "warnings": warnings,
    }


def render_human(report: dict[str, Any]) -> str:
    lines = [f"media_qa · {report['status'].upper()} ({report['mode']}) · {report['media']}"]
    for item in report.get("items", []):
        prefix = {"ok": "  OK  ", "warn": " WARN ", "error": " FAIL "}.get(item["level"], "      ")
        lines.append(f"{prefix}{item['code']}  {item['msg']}")
    for reason in report.get("incomplete_reasons", []):
        lines.append(f" INCOMPLETE  {reason}")
    lines.append(
        f"RESULT: {report['status'].upper()} — "
        f"{len(report.get('errors', []))} error(s), {len(report.get('warnings', []))} warning(s)"
    )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("media", type=Path, help="rendered MP4 file to inspect")
    parser.add_argument("--mode", choices=("master", "preview", "video-only"), default="master")
    parser.add_argument("--vo", type=Path, default=None, help="reference VO WAV/MP3 for duration and silence comparison")
    parser.add_argument("--beats", type=Path, default=None, help="plan/beats.json for approved timeline duration check")
    parser.add_argument("--expected-frames", type=int, default=None)
    parser.add_argument("--min-mbps", type=float, default=None, help="override master bitrate floor (recorded in report)")
    parser.add_argument("--max-hold", type=float, default=None, help="override max static hold seconds (default 2.5)")
    parser.add_argument("--lufs-tol", type=float, default=None, help="override LUFS tolerance around -14.5")
    parser.add_argument("--json", dest="json_out", type=Path, default=None, help="write full JSON report to a fresh path")
    parser.add_argument("--sheet", type=Path, default=None, help="write diagnostic contact sheet PNG to a fresh path")
    parser.add_argument("--strict", action="store_true", help="treat warnings as failures")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        json_out = _safe_abs(args.json_out) if args.json_out else None
        if json_out is not None and json_out.exists():
            print(f"media_qa blocked: refusing to overwrite existing report: {json_out}", file=sys.stderr)
            return 2
        report = inspect_media(
            args.media,
            mode=args.mode,
            vo_path=args.vo,
            beats_path=args.beats,
            expected_frames=args.expected_frames,
            min_mbps=args.min_mbps,
            max_hold_s=args.max_hold,
            lufs_tol=args.lufs_tol,
            sheet_path=args.sheet,
            strict=args.strict,
        )
        if json_out is not None:
            json_out.parent.mkdir(parents=True, exist_ok=True)
            with json_out.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, ensure_ascii=False)
                stream.write("\n")
        print(render_human(report))
        return 0 if report["status"] == "pass" else 1
    except ValueError as error:
        print(f"media_qa blocked: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
