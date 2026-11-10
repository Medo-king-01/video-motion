"""Tests for `tools/media_qa.py` — post-render MP4/AAC Final Media QA."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import av
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

import media_qa  # noqa: E402
from media_bin import ffmpeg  # noqa: E402

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


def _write_speech_like_wav(path: Path, duration: float = 3.0, sr: int = 24000) -> Path:
    n = int(round(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    env = 0.65 + 0.35 * np.sin(2.0 * math.pi * 2.5 * t)
    sig = env * (
        0.55 * np.sin(2.0 * math.pi * 220.0 * t)
        + 0.30 * np.sin(2.0 * math.pi * 440.0 * t)
        + 0.15 * np.sin(2.0 * math.pi * 660.0 * t)
    )
    pcm = np.clip(sig * 12000.0, -32767, 32767).astype("<i2")
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _master_audio_wav(src_wav: Path, dst_wav: Path) -> Path:
    ff = ffmpeg(required=True)
    p1 = subprocess.run(
        [ff, "-hide_banner", "-nostats", "-i", str(src_wav),
         "-af", "loudnorm=I=-14.5:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    log = p1.stderr
    info = json.loads(log[log.rfind("{"): log.rfind("}") + 1])
    af = (
        f"loudnorm=I=-14.5:TP=-1.5:LRA=9:linear=true:"
        f"measured_I={info['input_i']}:measured_TP={info['input_tp']}:"
        f"measured_LRA={info['input_lra']}:measured_thresh={info['input_thresh']}:"
        f"offset={info['target_offset']}"
    )
    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(src_wav),
         "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dst_wav)],
        check=True,
    )
    return dst_wav


def _encode_test_mp4(
    out_mp4: Path,
    *,
    frames: int = 90,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    audio_wav: Path | None = None,
    faststart: bool = True,
    freeze_after: int | None = None,
    black_range: tuple[int, int] | None = None,
    blank_frame0: bool = False,
    crf: int = 13,
) -> Path:
    raw_mp4 = out_mp4.with_suffix(".video_raw.mp4")
    container = av.open(str(raw_mp4), mode="w")
    stream = container.add_stream("libx264", rate=fps)
    stream.width = width
    stream.height = height
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": str(crf), "preset": "ultrafast", "profile": "high"}

    yy = np.linspace(0, 1, height, dtype=np.float32)[:, None]
    xx = np.linspace(0, 1, width, dtype=np.float32)[None, :]
    cached_rgb: np.ndarray | None = None

    for idx in range(frames):
        if black_range and black_range[0] <= idx < black_range[1]:
            rgb = np.zeros((height, width, 3), dtype=np.uint8)
        elif idx == 0 and blank_frame0:
            base = (242.0 - 14.0 * yy + 0.0 * xx)[..., None]
            rgb = np.repeat(base, 3, axis=2).astype(np.uint8)
        elif freeze_after is not None and idx >= freeze_after and cached_rgb is not None:
            rgb = cached_rgb
        else:
            phase = idx * 0.21
            checker = (((np.arange(height)[:, None] + idx * 9) // 48 + (np.arange(width)[None, :] + idx * 7) // 48) % 2)
            rgb = np.empty((height, width, 3), dtype=np.uint8)
            rgb[..., 0] = np.clip(18 + 30 * yy + checker * 28, 0, 255).astype(np.uint8)
            rgb[..., 1] = np.clip(16 + 22 * xx + checker * 18, 0, 255).astype(np.uint8)
            rgb[..., 2] = np.clip(20 + 25 * math.sin(phase) + checker * 22, 0, 255).astype(np.uint8)
            # Crisp high-contrast foreground card + moving bar inside content zone
            bar_y = 320 + int((idx * 17) % 620)
            rgb[bar_y: bar_y + 110, 120: width - 120] = (242, 242, 242)
            rgb[bar_y + 24: bar_y + 86, 160: 460] = (203, 39, 27)
            cached_rgb = rgb

        vf = av.VideoFrame.from_ndarray(rgb, format="rgb24")
        for pkt in stream.encode(vf):
            container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()

    ff = ffmpeg(required=True)
    cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw_mp4)]
    if audio_wav is not None:
        cmd += ["-i", str(audio_wav), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        cmd += ["-c:v", "copy", "-an"]
    if faststart:
        cmd += ["-movflags", "+faststart"]
    cmd.append(str(out_mp4))
    subprocess.run(cmd, check=True)
    raw_mp4.unlink(missing_ok=True)
    return out_mp4


@pytest.fixture(scope="module")
def mastered_bundle(tmp_path_factory):
    work = tmp_path_factory.mktemp("media_qa_bundle")
    vo_wav = _write_speech_like_wav(work / "vo24.wav", duration=3.0)
    mastered_wav = _master_audio_wav(vo_wav, work / "mastered.wav")
    beats = work / "beats.json"
    beats.write_text(json.dumps({
        "duration": 3.0, "fps": 30, "frames": 90,
        "scenes": [{"index": 1, "start": 0.0, "end": 3.0, "dur": 3.0, "frames": 90}],
    }), encoding="utf-8")
    good_mp4 = _encode_test_mp4(work / "good_master.mp4", frames=90, audio_wav=mastered_wav, faststart=True)
    return {"dir": work, "vo": vo_wav, "mastered_wav": mastered_wav, "beats": beats, "good_mp4": good_mp4}


def test_media_qa_passes_compliant_master_and_writes_sheet_and_json(mastered_bundle, tmp_path):
    sheet = tmp_path / "qa-sheet.png"
    report_path = tmp_path / "qa-report.json"
    rc = media_qa.main([
        str(mastered_bundle["good_mp4"]),
        "--mode", "master",
        "--vo", str(mastered_bundle["vo"]),
        "--beats", str(mastered_bundle["beats"]),
        "--min-mbps", "0.5",
        "--sheet", str(sheet),
        "--json", str(report_path),
    ])
    assert rc == 0
    assert sheet.is_file() and sheet.stat().st_size > 1000
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["errors"] == []
    assert report["container"]["faststart"] is True
    assert -14.8 <= report["audio"]["integrated_lufs"] <= -14.2
    assert report["audio"]["true_peak_dbtp"] <= -1.5


def test_media_qa_rejects_missing_faststart_and_low_bitrate(mastered_bundle, tmp_path):
    no_fs = _encode_test_mp4(
        tmp_path / "no_faststart.mp4",
        frames=90,
        audio_wav=mastered_bundle["mastered_wav"],
        faststart=False,
    )
    rep = media_qa.inspect_media(no_fs, mode="master", min_mbps=99.0)
    codes = {e["code"] for e in rep["errors"]}
    assert rep["status"] == "fail"
    assert "Q00" in codes
    assert "Q02" in codes


def test_media_qa_detects_blank_frame0_black_dropouts_and_static_hold(mastered_bundle, tmp_path):
    blank0 = _encode_test_mp4(tmp_path / "blank0.mp4", frames=90, blank_frame0=True)
    rep_b0 = media_qa.inspect_media(blank0, mode="video-only")
    assert any(e["code"] == "Q03" for e in rep_b0["errors"])

    dropout = _encode_test_mp4(tmp_path / "dropout.mp4", frames=90, black_range=(30, 35))
    rep_drop = media_qa.inspect_media(dropout, mode="video-only")
    assert any(e["code"] == "Q03" and "black frame" in e["msg"] for e in rep_drop["errors"])

    frozen = _encode_test_mp4(tmp_path / "frozen.mp4", frames=95, freeze_after=5)
    rep_freeze = media_qa.inspect_media(frozen, mode="video-only")
    assert any(e["code"] == "Q04" for e in rep_freeze["errors"])


def test_media_qa_detects_vo_mismatch_bad_loudness_and_short_clip_incomplete(mastered_bundle, tmp_path):
    rep_sync = media_qa.inspect_media(
        mastered_bundle["good_mp4"], mode="preview", expected_frames=120
    )
    assert any(e["code"] == "Q01" for e in rep_sync["errors"])

    # Unmastered raw VO is way off -14.5 LUFS
    unmastered = _encode_test_mp4(
        tmp_path / "unmastered.mp4", frames=90, audio_wav=mastered_bundle["vo"]
    )
    rep_loud = media_qa.inspect_media(unmastered, mode="master", min_mbps=0.1)
    assert any(e["code"] == "Q05" for e in rep_loud["errors"])

    # Short < 1.0s master clip -> incomplete, never silent pass
    short_vo = _write_speech_like_wav(tmp_path / "short.wav", duration=0.5)
    short_mp4 = _encode_test_mp4(tmp_path / "short.mp4", frames=15, audio_wav=short_vo)
    rep_short = media_qa.inspect_media(short_mp4, mode="master", min_mbps=0.1)
    assert rep_short["status"] == "incomplete"
    assert rep_short["incomplete_reasons"]


def test_media_qa_refuses_overwrite_and_symlinks(mastered_bundle, tmp_path):
    existing = tmp_path / "existing.json"
    existing.write_text("{}", encoding="utf-8")
    assert media_qa.main([str(mastered_bundle["good_mp4"]), "--mode", "video-only", "--json", str(existing)]) == 2

    sym = tmp_path / "link.mp4"
    sym.symlink_to(mastered_bundle["good_mp4"])
    assert media_qa.main([str(sym), "--mode", "video-only"]) == 2
