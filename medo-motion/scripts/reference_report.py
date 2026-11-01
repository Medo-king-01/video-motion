"""Small, deterministic metrics and visuals for the studio's reference-video workflow.

This module describes the reference; it does not choose the reel's colours or reproduce
its content. The locked Medo brand remains the source of truth.
"""
from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


def _rgb(hex_value: str) -> tuple[int, int, int]:
    return tuple(int(hex_value[i:i + 2], 16) for i in (1, 3, 5))


def _palette(frames: list[Path], out: Path, colors: int = 8) -> dict[str, Any]:
    """Create an approximate dominant palette from small, evenly sampled frames."""
    if not frames:
        return {"colors": [], "background": None, "accent": None}
    samples = []
    border_samples = []
    for frame in frames[:64]:
        with Image.open(frame) as image:
            image = image.convert("RGB").resize((64, 36))
            pixels = np.asarray(image, dtype=np.uint8)
        samples.append(pixels.reshape(-1, 3))
        border_samples.append(np.concatenate((pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1])))

    pixels = np.concatenate(samples)
    # Pillow quantization is deterministic for this fixed input and avoids another dependency.
    reduced = Image.fromarray(pixels.reshape(-1, 1, 3), "RGB").quantize(
        colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    counts = np.bincount(np.asarray(reduced, dtype=np.uint8).reshape(-1), minlength=colors)
    palette = reduced.getpalette() or []
    ranked = np.argsort(-counts)
    result = []
    for index in ranked:
        if counts[index] == 0:
            continue
        rgb = tuple(palette[index * 3:index * 3 + 3])
        result.append({"hex": "#%02X%02X%02X" % rgb, "share": round(float(counts[index] / counts.sum()), 4)})

    centers = np.array([_rgb(item["hex"]) for item in result], dtype=np.float32)
    edges = np.concatenate(border_samples).astype(np.float32)
    nearest = ((edges[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2).argmin(axis=1)
    background_index = int(np.bincount(nearest, minlength=len(centers)).argmax())
    saturation = (centers.max(axis=1) - centers.min(axis=1)) / np.maximum(centers.max(axis=1), 1)
    candidates = [i for i in range(len(result)) if i != background_index and result[i]["share"] >= 0.01]
    accent_index = max(candidates, key=lambda i: saturation[i] * (centers[i].max() / 255)) if candidates else background_index

    swatch = Image.new("RGB", (160 * len(result), 100), "white")
    draw = ImageDraw.Draw(swatch)
    for i, item in enumerate(result):
        draw.rectangle((i * 160, 0, (i + 1) * 160 - 1, 68), fill=item["hex"])
        draw.text((i * 160 + 6, 74), f"{item['hex']} · {item['share'] * 100:.1f}%", fill="black")
    swatch.save(out / "palette.png")
    data = {
        "note": "Observed reference colours only; translate to the locked Medo palette, do not copy these hex values into the reel.",
        "background": result[background_index]["hex"],
        "accent": result[accent_index]["hex"],
        "colors": result,
    }
    (out / "palette.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data


def _audio_metrics(audio: Path | None) -> dict[str, Any] | None:
    if audio is None or not audio.is_file():
        return None
    try:
        with wave.open(str(audio), "rb") as wav:
            rate = wav.getframerate()
            samples = np.frombuffer(wav.readframes(wav.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    except (wave.Error, OSError):
        return None
    hop = max(1, rate // 100)
    count = len(samples) // hop
    if count < 2:
        return None
    rms = np.sqrt(np.mean(samples[:count * hop].reshape(count, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(rms / max(float(rms.max()), 1e-9) + 1e-9)
    active = float(np.mean(db > -35))
    jumps = np.diff(db)
    onset_indices = np.flatnonzero((jumps[2:] > 9) & (db[3:] > -30))
    onsets = []
    for index in onset_indices:
        if not onsets or index - onsets[-1] > 12:
            onsets.append(int(index))
    duration = len(samples) / rate
    return {"active_share": round(active, 3), "rough_onsets_per_minute": round(len(onsets) / max(duration / 60, 1e-9), 1)}


def _motion_strips(ffmpeg: str, source: Path, out: Path, sample_paths: list[Path],
                   start: float, sample_fps: float, duration: float) -> list[dict[str, Any]]:
    if len(sample_paths) < 3:
        return []
    small = []
    for frame in sample_paths:
        with Image.open(frame) as image:
            small.append(np.asarray(image.convert("L").resize((96, 54)), dtype=np.float32))
    diff = np.array([np.abs(b - a).mean() / 255 for a, b in zip(small, small[1:])])
    if not len(diff):
        return []
    smooth = np.convolve(diff, np.ones(3) / 3, mode="same")
    selected: list[float] = []
    for index in np.argsort(-smooth):
        t = start + (int(index) + 1) / sample_fps
        if t < start + 0.5 or t > start + duration - 0.5:
            continue
        if any(abs(t - previous) < 1.5 for previous in selected):
            continue
        selected.append(float(t))
        if len(selected) >= 4:
            break
    selected.sort()
    target = out / "motion"
    target.mkdir(parents=True, exist_ok=True)
    for old in target.glob("strip_*.jpg"):
        if old.is_file() and not old.is_symlink():
            old.unlink()
    strips = []
    for index, t in enumerate(selected, 1):
        frame = target / f"strip_{index:02d}_{t:07.2f}s.jpg"
        begin = max(0.0, t - 0.4)
        result = subprocess.run([
            ffmpeg, "-v", "error", "-y", "-ss", f"{begin:.3f}", "-i", str(source),
            "-t", "0.8", "-vf", "fps=10,scale=480:-2,tile=4x2:padding=4:color=0x202020",
            "-frames:v", "1", "-q:v", "3", str(frame),
        ], capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode == 0 and frame.is_file():
            strips.append({"time": round(t, 3), "path": frame.relative_to(out).as_posix()})
        else:
            frame.unlink(missing_ok=True)
    return strips


def build_report(*, source: Path, out: Path, sample_paths: list[Path], sample_fps: float,
                 start: float, duration: float, info: dict[str, Any], cuts: list[float],
                 audio: Path | None, ffmpeg: str) -> dict[str, Any]:
    """Write palette, motion strips, JSON and a concise Markdown reference report."""
    out.mkdir(parents=True, exist_ok=True)
    palette = _palette(sample_paths, out)
    metrics = _motion_strips(ffmpeg, source, out, sample_paths, start, sample_fps, duration)
    gray = []
    for frame in sample_paths:
        with Image.open(frame) as image:
            gray.append(np.asarray(image.convert("L").resize((96, 54)), dtype=np.float32).mean() / 255)
    motion_values = []
    for left, right in zip(sample_paths, sample_paths[1:]):
        with Image.open(left) as a, Image.open(right) as b:
            x = np.asarray(a.convert("L").resize((96, 54)), dtype=np.float32)
            y = np.asarray(b.convert("L").resize((96, 54)), dtype=np.float32)
        motion_values.append(float(np.abs(y - x).mean() / 255))
    window_cuts = [float(c) - start for c in cuts if start < float(c) < start + duration]
    shot_bounds = [0.0] + window_cuts + [duration]
    shot_lengths = np.diff(shot_bounds) if len(shot_bounds) > 1 else np.array([duration])
    audio_info = _audio_metrics(audio)
    background = palette.get("background")
    accent = palette.get("accent")
    summary = {
        "source": source.name,
        "duration": round(duration, 3),
        "width": info.get("width"),
        "height": info.get("height"),
        "fps": info.get("fps"),
        "sample_fps": sample_fps,
        "sample_count": len(sample_paths),
        "window_start": round(start, 3),
        "cut_count": len(window_cuts),
        "cuts_per_minute": round(len(window_cuts) / max(duration / 60, 1e-9), 1),
        "mean_shot_seconds": round(float(np.mean(shot_lengths)), 3),
        "median_shot_seconds": round(float(np.median(shot_lengths)), 3),
        "mean_frame_change_pct": round(float(np.mean(motion_values)) * 100, 2) if motion_values else 0,
        "near_static_sample_share": round(float(np.mean(np.array(motion_values) < 0.004)), 3) if motion_values else 0,
        "mean_brightness_pct": round(float(np.mean(gray)) * 100, 1) if gray else 0,
        "background_observed": background,
        "accent_observed": accent,
        "palette": palette.get("colors", []),
        "audio": audio_info,
        "motion_strips": metrics,
        "cut_times": [round(float(c), 3) for c in cuts if start < float(c) < start + duration],
    }
    (out / "analysis.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        f"# Reference breakdown: {source.name}",
        "",
        "> Observational aid, not a style prescription. Keep the Medo palette, typography and safety rules locked; borrow visual techniques, not the reference's content, logo or assets.",
        "",
        "| Measure | Observation |",
        "|---|---|",
        f"| Duration / format | {duration:.2f}s · {info.get('width', '?')}×{info.get('height', '?')} · {info.get('fps', '?')} fps |",
        f"| Detected cuts | {len(window_cuts)} · {summary['cuts_per_minute']:.1f}/min |",
        f"| Shot duration | mean {summary['mean_shot_seconds']:.2f}s · median {summary['median_shot_seconds']:.2f}s |",
        f"| Sampled frame change | mean {summary['mean_frame_change_pct']:.2f}% · near-static samples {summary['near_static_sample_share'] * 100:.0f}% |",
        f"| Average brightness | {summary['mean_brightness_pct']:.1f}% (rough grayscale estimate) |",
        f"| Approx. background / accent | {background or 'n/a'} / {accent or 'n/a'} (reference only) |",
        f"| Audio | {('active about ' + str(round(audio_info['active_share'] * 100)) + '%; rough onsets ' + str(audio_info['rough_onsets_per_minute']) + '/min') if audio_info else 'none or not measurable'} |",
        "",
        "## Inspect",
        "- `sheet_*.jpg`: timestamped overview frames.",
        "- `strip_hook.jpg`: consecutive opening frames.",
        "- `motion/strip_*.jpg`: short strips around high-change moments (8 frames, 0.1s apart).",
        "- `palette.png` / `palette.json`: approximate sampled colours; translate through the locked brand, do not copy hex values.",
        "- `spectrogram.png` and `audio.wav`: only present when the reference contains audio.",
        "",
        "## Human/agent breakdown to complete in `STYLE.md`",
        "1. What creates the look: composition, texture, typography role, recurring visual device.",
        "2. Motion vocabulary: entrance/hold/exit and approximate timing, mapped to `motion/easings.json`.",
        "3. Pacing: which edits align to narration/music, and where the reference pauses.",
        "4. What to adapt with studio primitives, what to omit, and what must not be copied.",
    ]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return summary
