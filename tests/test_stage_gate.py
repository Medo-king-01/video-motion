"""Tests for `tools/stage_gate.py` — cumulative stage checkpoints & Delivery Promise verification."""
from __future__ import annotations

import json
import math
import subprocess
import sys
import wave
from pathlib import Path

import av
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

import stage_gate  # noqa: E402
from media_bin import ffmpeg  # noqa: E402


def _make_vo24(path: Path, duration: float = 3.0, sr: int = 24000, channels: int = 1) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(round(duration * sr))
    t = np.arange(n, dtype=np.float64) / sr
    sig = (0.7 * np.sin(2.0 * math.pi * 240.0 * t) + 0.3 * np.sin(2.0 * math.pi * 480.0 * t)) * 11000.0
    pcm = sig.astype("<i2")
    if channels == 2:
        pcm = np.repeat(pcm[:, None], 2, axis=1).reshape(-1)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _encode_master_for_project(out_mp4: Path, vo_wav: Path, frames: int = 90) -> Path:
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    ff = ffmpeg(required=True)
    p1 = subprocess.run(
        [ff, "-hide_banner", "-nostats", "-i", str(vo_wav),
         "-af", "loudnorm=I=-14.5:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True, check=True,
    )
    info = json.loads(p1.stderr[p1.stderr.rfind("{"): p1.stderr.rfind("}") + 1])
    af = (
        f"loudnorm=I=-14.5:TP=-1.5:LRA=9:linear=true:"
        f"measured_I={info['input_i']}:measured_TP={info['input_tp']}:"
        f"measured_LRA={info['input_lra']}:measured_thresh={info['input_thresh']}:"
        f"offset={info['target_offset']}"
    )
    mastered_wav = out_mp4.with_suffix(".mastered.wav")
    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(vo_wav),
         "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(mastered_wav)],
        check=True,
    )

    raw_mp4 = out_mp4.with_suffix(".raw.mp4")
    container = av.open(str(raw_mp4), mode="w")
    stream = container.add_stream("libx264", rate=30)
    stream.width = 1080
    stream.height = 1920
    stream.pix_fmt = "yuv420p"
    stream.options = {"crf": "13", "preset": "ultrafast", "profile": "high"}
    for idx in range(frames):
        rgb = np.full((1920, 1080, 3), 18, dtype=np.uint8)
        y = 300 + (idx * 13) % 500
        rgb[y: y + 120, 120:960] = (242, 242, 242)
        rgb[y + 30: y + 90, 160:460] = (203, 39, 27)
        for pkt in stream.encode(av.VideoFrame.from_ndarray(rgb, format="rgb24")):
            container.mux(pkt)
    for pkt in stream.encode():
        container.mux(pkt)
    container.close()

    subprocess.run(
        [ff, "-y", "-hide_banner", "-loglevel", "error", "-i", str(raw_mp4), "-i", str(mastered_wav),
         "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out_mp4)],
        check=True,
    )
    raw_mp4.unlink(missing_ok=True)
    mastered_wav.unlink(missing_ok=True)
    return out_mp4


def _scaffold_ready_project(tmp_path: Path) -> Path:
    proj = tmp_path / "reel-proj"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "new_project.py"), "reel-proj", "--engine", "p", "--out", str(proj)],
        cwd=str(ROOT), check=True, capture_output=True, text=True,
    )
    (proj / "BRIEF.md").write_text("# Brief\n\nشرح سريع لفكرة واحدة في ٣ ثواني.\n", encoding="utf-8")
    (proj / "plan" / "script.md").write_text("1. السر في القياس الحقيقي مش التخمين.\n", encoding="utf-8")
    _make_vo24(proj / "out" / "vo24.wav", duration=3.0)
    (proj / "plan" / "beats.json").write_text(json.dumps({
        "duration": 3.0, "fps": 30, "frames": 90, "audio": "out/vo24.wav",
        "bounds": [0.0, 1.5, 3.0],
        "scenes": [
            {"index": 1, "start": 0.0, "end": 1.5, "dur": 1.5, "frames": 45,
             "background": "aura", "theme": "dark", "events": [{"t": 0.08, "what": "cold open hook"}]},
            {"index": 2, "start": 1.5, "end": 3.0, "dur": 1.5, "frames": 45,
             "background": "grid-2d", "theme": "dark", "events": [{"t": 1.6, "what": "stat lands"}]},
        ],
    }, indent=2), encoding="utf-8")
    (proj / "plan" / "word-timings.json").write_text(json.dumps({
        "clock": "vo",
        "scenes": [
            {"scene": 1, "words": [{"text": "القياس", "start": 0.05, "end": 0.70}, {"text": "أولًا", "start": 0.75, "end": 1.40}]},
            {"scene": 2, "words": [{"text": "تلاتين", "start": 1.55, "end": 2.20}, {"text": "فريم", "start": 2.25, "end": 2.90}]},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps({
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "s1-h", "scene": 1, "role": "hook", "text": "القياس أولًا", "start": 0.05, "end": 1.4, "mode": "build", "color": "paper", "size": 84},
            {"id": "s2-n", "scene": 2, "role": "number", "text": "30fps", "start": 1.55, "end": 2.9, "mode": "build", "color": "blush", "size": 84},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps({
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "حركة النص تتبع التركيز الصوتي في المشهدين بوضوح",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "karaoke",
                "captionWhy": "مشهد البداية يحتاج متابعة بصرية للكلام",
                "textStyles": {"hook": "wordPop"},
                "textWhy": "الهوك الافتتاحي يدخل بنبضة سريعة تجذب العين",
                "fontStyles": {"hook": {"family": "Cairo", "weight": 800}},
                "fontWhy": "خط عربي ثقيل ومقروء من أول فريم",
            },
            {
                "scene": 2,
                "captionStyle": "softFade",
                "captionWhy": "تهدئة الكابشن عشان عين المشاهد تركز على الرقم",
                "textStyles": {"number": "zoomPunch"},
                "textWhy": "الرقم يدخل بوضوح مع كلمة تلاتين",
                "fontStyles": {"number": {"family": "Space Grotesk", "weight": 700}},
                "fontWhy": "خط هندسي للأرقام الغربية",
            },
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    (proj / "plan" / "visual-direction.json").write_text(json.dumps({
        "version": 1,
        "status": "ready",
        "decidedBy": "agent",
        "clock": "vo",
        "wordTimings": "plan/word-timings.json",
        "scenes": [
            {"scene": 1, "start": 0.0, "end": 1.5, "treatment": "presenter",
             "why": "ميدو يفتتح الفكرة مباشرة بدون زحمة بصرية", "elements": []},
            {"scene": 2, "start": 1.5, "end": 3.0, "treatment": "presenter",
             "why": "ميدو يختم بالرقم الأساسي في كادر نظيف", "elements": []},
        ],
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "techniques.py"), "--draw",
         "--from-plan", str(proj / "plan" / "beats.json"),
         "--json", str(proj / "plan" / "techniques.json"), "--seed", "7"],
        cwd=str(ROOT), check=True, capture_output=True, text=True,
    )
    # Write a clean directed scenes.py aligned with the 3.0s VO (no raw put() demo calls)
    (proj / "scenes.py").write_text(
        """from pathlib import Path
import numpy as np
import captions, lib, presenter
import text_direction as td

HERE = Path(__file__).resolve().parent
CHIP = None
B = [0.0, 1.5, 3.0]
DIR = td.load(HERE)

def render_frame(t: float) -> np.ndarray:
    fr = lib.gradient_bg("dark").copy()
    presenter.draw(fr, "explain", t, x=0.5, height=0.52, face_box={"x": 0.30, "y": 0.04, "w": 0.40, "h": 0.24})
    if t < 1.5:
        captions.draw_directed_text(
            fr, "القياس أولًا", direction=DIR, scene=1, role="hook", element_id="s1-h",
            t=t, start=0.05, end=1.4, cx=540, cy=280, size=84, color=lib.WHITE, theme="dark",
        )
    else:
        captions.draw_directed_text(
            fr, "30fps", direction=DIR, scene=2, role="number", element_id="s2-n",
            t=t, start=1.55, end=2.9, cx=540, cy=280, size=84, color=lib.EMER, theme="dark", rtl=False,
        )
    return np.clip(fr, 0, 255).astype(np.uint8)
""",
        encoding="utf-8",
    )
    return proj


def test_stage_gate_rejects_fresh_scaffold_at_intake(tmp_path):
    proj = tmp_path / "fresh"
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "new_project.py"), "fresh", "--engine", "p", "--out", str(proj)],
        cwd=str(ROOT), check=True, capture_output=True, text=True,
    )
    rep = stage_gate.evaluate_stage(proj, stage="intake")
    assert rep["status"] == "fail"
    assert any(e["code"] == "G01" for e in rep["errors"])


def test_stage_gate_end_to_end_plan_checkpoint_and_deliver(tmp_path):
    proj = _scaffold_ready_project(tmp_path)

    # Plan stage + checkpoint
    rc_plan = stage_gate.main([str(proj), "--stage", "plan", "--write-checkpoint"])
    assert rc_plan == 0
    ok, msg = stage_gate.verify_checkpoint(proj, "plan")
    assert ok is True, msg

    # Mutate copy.json -> checkpoint becomes stale immediately
    copy_path = proj / "plan" / "copy.json"
    orig_copy = copy_path.read_text(encoding="utf-8")
    copy_path.write_text(orig_copy + "\n", encoding="utf-8")
    ok_stale, stale_msg = stage_gate.verify_checkpoint(proj, "plan")
    assert ok_stale is False and "STALE_CHECKPOINT" in stale_msg
    copy_path.write_text(orig_copy, encoding="utf-8")

    # Render master + layout report -> deliver passes
    master_mp4 = _encode_master_for_project(proj / "out" / "master.mp4", proj / "out" / "vo24.wav", frames=90)
    layout_rep = proj / "cache" / "layout-p" / "report.json"
    layout_rep.parent.mkdir(parents=True, exist_ok=True)
    layout_rep.write_text(json.dumps({"status": "pass", "replay": {"status": "pass"}}), encoding="utf-8")

    rep_deliver = stage_gate.evaluate_stage(
        proj, stage="deliver", media=master_mp4, layout_report=layout_rep, min_mbps=0.1
    )
    assert rep_deliver["status"] == "pass", rep_deliver["errors"]

    # Add uncredited external asset -> G06 fails until credited in CREDITS.md
    ext_asset = proj / "assets" / "sfx" / "custom_swoosh.wav"
    ext_asset.parent.mkdir(parents=True, exist_ok=True)
    ext_asset.write_bytes(b"RIFF....")
    rep_uncredited = stage_gate.evaluate_stage(
        proj, stage="deliver", media=master_mp4, layout_report=layout_rep, min_mbps=0.1
    )
    assert rep_uncredited["status"] == "fail"
    assert any("CREDITS.md" in e["msg"] for e in rep_uncredited["errors"])

    (proj / "CREDITS.md").write_text("- `custom_swoosh.wav` — CC0 1.0\n", encoding="utf-8")
    rep_credited = stage_gate.evaluate_stage(
        proj, stage="deliver", media=master_mp4, layout_report=layout_rep, min_mbps=0.1
    )
    assert rep_credited["status"] == "pass", rep_credited["errors"]

    # Unapproved series CHIP in scenes.py -> G06 fails
    scenes_py = proj / "scenes.py"
    scenes_py.write_text(scenes_py.read_text(encoding="utf-8") + '\nCHIP = "سلسلة مخترعة"\n', encoding="utf-8")
    rep_chip = stage_gate.evaluate_stage(
        proj, stage="deliver", media=master_mp4, layout_report=layout_rep, min_mbps=0.1
    )
    assert rep_chip["status"] == "fail"
    assert any("CHIP" in e["msg"] for e in rep_chip["errors"])
