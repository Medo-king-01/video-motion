"""Tests for Engine P layout box capture (`layout_p.py`) and `tools/layout_audit_p.py`."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))
sys.path.insert(0, str(ROOT / "tools"))

import layout_audit_p  # noqa: E402
import layout_p  # noqa: E402


def test_layout_p_audit_rules_and_camera_projection():
    layout_p.begin_frame()
    layout_p.record_text("عنوان آمن", {"x": 120, "y": 300, "w": 840, "h": 90}, box_id="headline", zone="content")
    layout_p.record_text("كابشن", {"x": 200, "y": 1410, "w": 680, "h": 65}, box_id="cap", zone="caption")
    layout_p.record_text("01", {"x": 80, "y": 90, "w": 100, "h": 48}, box_id="hud-tag", zone="hud")
    layout_p.protect_box("face-neutral", {"x": 420, "y": 520, "w": 220, "h": 240}, kind="face")
    layout_p.apply_camera(1.06, 12.0, -8.0)
    boxes = layout_p.end_frame()

    issues = layout_p.audit_layout(boxes)
    assert issues == []
    # HUD and caption stay fixed in screen space while content moves with camera
    by_id = {t["id"]: t for t in boxes}
    assert by_id["hud-tag"]["y"] == 90.0
    assert by_id["cap"]["y"] == 1410.0
    assert by_id["headline"]["y"] != 300.0


def test_layout_p_detects_l00_l01_l02_l03():
    boxes = [
        {"id": "bad-zone", "kind": "text", "text": "x", "zone": "mystery", "x": 100, "y": 400, "w": 200, "h": 50},
        {"id": "oob", "kind": "text", "text": "بره", "zone": "content", "x": 10, "y": 120, "w": 300, "h": 80},
        {"id": "a", "kind": "text", "text": "أول", "zone": "content", "x": 200, "y": 500, "w": 400, "h": 80},
        {"id": "b", "kind": "text", "text": "تاني", "zone": "content", "x": 250, "y": 520, "w": 400, "h": 80},
        {"id": "over-face", "kind": "text", "text": "فوق الوش", "zone": "content", "x": 460, "y": 760, "w": 200, "h": 60},
        {"id": "missing-faceBox-wave", "kind": "face", "x": 0, "y": 0, "w": 0, "h": 0},
        {"id": "face-explain", "kind": "face", "x": 430, "y": 720, "w": 220, "h": 220},
    ]
    issues = layout_p.audit_layout(boxes)
    codes = {e["code"] for e in issues}
    assert codes == {"L00", "L01", "L02", "L03"}


def _make_mini_p_project(proj: Path, scenes_code: str) -> Path:
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "plan").mkdir(exist_ok=True)
    (proj / "assets").mkdir(exist_ok=True)
    (proj / "plan" / "beats.json").write_text(json.dumps({
        "duration": 0.4, "fps": 30, "frames": 12,
        "scenes": [{"index": 1, "start": 0.0, "end": 0.4, "dur": 0.4, "frames": 12}],
    }), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps({
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "حركة النص تتبع التركيز الصوتي في المشهد بوضوح",
        "scenes": [{
            "scene": 1,
            "captionStyle": "wordPop",
            "captionWhy": "إبراز الكلمة المنطوقة في مشهد الاختبار",
            "textStyles": {"title": "softFade"},
            "textWhy": "دخول هادئ للعنوان بدون تشتيت العين",
            "fontStyles": {"title": {"family": "Cairo", "weight": 800}},
            "fontWhy": "خط عربي واضح ومقروء على الموبايل",
        }],
    }, ensure_ascii=False), encoding="utf-8")
    (proj / "scenes.py").write_text(scenes_code, encoding="utf-8")
    return proj


def test_layout_audit_p_cli_pass_with_replay_and_pose_face_box(tmp_path):
    proj = _make_mini_p_project(
        tmp_path / "proj_pass",
        """from pathlib import Path
import numpy as np
import captions, lib, presenter
import text_direction as td

HERE = Path(__file__).resolve().parent
DIR = td.load(HERE)
WORDS = [{"text": "اختبار", "start": 0.0, "end": 0.4}]
TRACK = presenter.PoseTrack([{"t": 0.0, "pose": "neutral"}, {"t": 0.2, "pose": "explain"}])
FACES = {
    "neutral": {"x": 0.30, "y": 0.04, "w": 0.40, "h": 0.24},
    "explain": {"x": 0.30, "y": 0.04, "w": 0.40, "h": 0.24},
}

def render_frame(t: float) -> np.ndarray:
    fr = np.full((1920, 1080, 3), 10.0, np.float32)
    TRACK.draw(fr, t, x=0.5, height=0.52, face_boxes=FACES)
    captions.draw_directed_text(
        fr, "عنوان واضح", direction=DIR, scene=1, role="title", element_id="h1",
        t=t, start=0.0, end=0.4, cx=540, cy=280, size=64, theme="dark",
    )
    captions.draw_word_caption(fr, t, WORDS, style="wordPop", y=1430, size=60, theme="dark")
    return np.clip(fr, 0, 255).astype(np.uint8)
""",
    )
    out_dir = tmp_path / "audit-pass"
    rc = layout_audit_p.main(["--project", str(proj), "--out", str(out_dir), "--replay"])
    assert rc == 0
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert rep["status"] == "pass"
    assert rep["replay"]["status"] == "pass"
    assert rep["capturedText"] >= 12


def test_layout_audit_p_cli_catches_collisions_and_writes_annotated_png(tmp_path):
    proj = _make_mini_p_project(
        tmp_path / "proj_fail",
        """from pathlib import Path
import numpy as np
import captions, lib, presenter
import text_direction as td

HERE = Path(__file__).resolve().parent
DIR = td.load(HERE)

def render_frame(t: float) -> np.ndarray:
    fr = np.full((1920, 1080, 3), 10.0, np.float32)
    presenter.draw(fr, "neutral", t, x=0.5, height=0.58)  # missing face_box -> L00
    captions.draw_directed_text(
        fr, "نص أول", direction=DIR, scene=1, role="title", element_id="t1",
        t=t, start=0.0, end=0.4, cx=540, cy=500, size=68, theme="dark",
    )
    captions.draw_directed_text(
        fr, "نص متصادم", direction=DIR, scene=1, role="title", element_id="t2",
        t=t, start=0.0, end=0.4, cx=540, cy=515, size=68, theme="dark",
    )
    return np.clip(fr, 0, 255).astype(np.uint8)
""",
    )
    out_dir = tmp_path / "audit-fail"
    rc = layout_audit_p.main(["--project", str(proj), "--out", str(out_dir)])
    assert rc == 1
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert rep["status"] == "fail"
    codes = {e["code"] for f in rep["frames"] for e in f["issues"]}
    assert "L00" in codes and "L02" in codes
    imgs = [f["image"] for f in rep["frames"] if f.get("image")]
    assert imgs and (out_dir / imgs[0]).is_file()


def test_layout_audit_p_replay_catches_hidden_mutable_state(tmp_path):
    proj = _make_mini_p_project(
        tmp_path / "proj_stateful",
        """from pathlib import Path
import numpy as np
import captions, lib
import text_direction as td

HERE = Path(__file__).resolve().parent
DIR = td.load(HERE)
CALLS = 0

def render_frame(t: float) -> np.ndarray:
    global CALLS
    CALLS += 1
    fr = np.full((1920, 1080, 3), 10.0, np.float32)
    fr[220:260, 100:100 + (CALLS * 5) % 400] = (203, 39, 27)
    captions.draw_directed_text(
        fr, "عنوان", direction=DIR, scene=1, role="title", element_id="h1",
        t=t, start=0.0, end=0.4, cx=540, cy=340, size=64, theme="dark",
    )
    return np.clip(fr, 0, 255).astype(np.uint8)
""",
    )
    out_dir = tmp_path / "audit-stateful"
    rc = layout_audit_p.main(["--project", str(proj), "--out", str(out_dir), "--replay"])
    assert rc == 1
    rep = json.loads((out_dir / "report.json").read_text(encoding="utf-8"))
    assert rep["replay"]["status"] == "fail"
    assert rep["status"] == "fail"
