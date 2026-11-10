"""Phase 2A - Fixed Stage geometry, clipping and cross-engine parity (categories A-D).

Window maths, two-way transitions, the P clipping composite and layout audits. Nothing here opens a
browser: D1/D3 shell out to node only to read the shared JS core.
"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from fixed_stage_support import (
    ENGINE_K,
    ENGINE_R,
    ROOT,
    TOOLS,
    WHITE,
    YEL,
    _sample_direction,
    _sample_stage_spec,
    _sample_words,
    captions,
    layout_p,
    stage,
    transition,
)

pytestmark = [pytest.mark.slow, pytest.mark.usefixtures("_cleanup_stage_tmp")]



# ===========================================================================
# A-D. Window maths, transitions, P clipping, layout audits
# ===========================================================================


def test_a1_win_fullscreen_framed_boundaries_and_midpoints():
    spec = _sample_stage_spec(radius=48.0)
    # Fullscreen hold [0.0..0.5] and exact boundary t=0.5
    for t in (0.0, 0.25, 0.5):
        wb = stage.win(spec, t)
        assert wb == {"x": 0.0, "y": 0.0, "w": 1080.0, "h": 1920.0, "r": 0.0}
        assert stage.is_fullscreen_window(wb) is True

    # Exact midpoint of cubicInOut transition [0.5..1.1] -> t = 0.8 -> p = 0.5
    mid = stage.win(spec, 0.8)
    assert mid["x"] == pytest.approx(40.0)
    assert mid["y"] == pytest.approx(120.0)
    assert mid["w"] == pytest.approx(1000.0)
    assert mid["h"] == pytest.approx(1490.0)
    assert mid["r"] == pytest.approx(24.0)
    assert stage.is_fullscreen_window(mid) is False

    # Framed hold [1.1..2.1] and exact boundaries
    for t in (1.1, 1.6, 2.1):
        wb = stage.win(spec, t)
        assert wb == {"x": 80.0, "y": 240.0, "w": 920.0, "h": 1060.0, "r": 48.0}
        assert stage.is_fullscreen_window(wb) is False

    # Return to fullscreen at t=2.7..3.0 and post-end hold
    for t in (2.7, 3.0, 4.5):
        wb = stage.win(spec, t)
        assert wb == {"x": 0.0, "y": 0.0, "w": 1080.0, "h": 1920.0, "r": 0.0}
        assert stage.is_fullscreen_window(wb) is True

    # Safe inner envelope accounts for rounded-corner clearance
    env_framed = stage.stage_safe_envelope({"x": 80, "y": 240, "w": 920, "h": 1060, "r": 90})
    assert env_framed["x"][0] > 80.0 + 24.0
    assert env_framed["x"][1] < 1000.0 - 24.0
    assert not stage.box_clipped_by_window_corners(
        {
            "x": env_framed["x"][0],
            "y": env_framed["y"][0],
            "w": env_framed["w"],
            "h": env_framed["h"],
        },
        {"x": 80, "y": 240, "w": 920, "h": 1060, "r": 90},
    )


def test_a2_radius_clamping_and_invalid_geometry_rejection():
    # Radius clamping: r <= min(w, h) / 2 and r >= 0
    clamped_hi = stage.clamp_window_box({"x": 100, "y": 300, "w": 400, "h": 220, "r": 999})
    assert clamped_hi["r"] == pytest.approx(110.0)
    clamped_lo = stage.clamp_window_box({"x": 100, "y": 300, "w": 400, "h": 220, "r": -25})
    assert clamped_lo["r"] == 0.0

    spec_huge_r = {
        "version": 1,
        "mode": "framed",
        "defaultFramedBox": {"x": 140, "y": 400, "w": 800, "h": 300, "r": 500},
    }
    assert stage.win(spec_huge_r, 1.0)["r"] == pytest.approx(150.0)

    # Invalid geometry rejection: w<=0, h<=0, NaN, Infinity, negative sizes, booleans, huge ints, overflow, off-canvas
    huge_pos = 10**1000
    huge_neg = -(10**1000)
    bad_boxes = [
        {"x": 0, "y": 0, "w": 0, "h": 500, "r": 0},
        {"x": 0, "y": 0, "w": 500, "h": 0, "r": 0},
        {"x": 0, "y": 0, "w": -100, "h": 500, "r": 0},
        {"x": 0, "y": 0, "w": 500, "h": -50, "r": 0},
        {"x": float("nan"), "y": 0, "w": 500, "h": 500, "r": 0},
        {"x": 0, "y": float("inf"), "w": 500, "h": 500, "r": 0},
        {"x": 0, "y": 0, "w": float("-inf"), "h": 500, "r": 0},
        {"x": 0, "y": 0, "w": 500, "h": 500, "r": float("nan")},
        {"x": True, "y": 0, "w": 500, "h": 500, "r": 0},
        {"x": 0, "y": 0, "w": huge_pos, "h": 500, "r": 0},
        {"x": huge_neg, "y": 0, "w": 500, "h": 500, "r": 0},
        {"x": 1e308, "y": 0, "w": 1e308, "h": 500, "r": 0},
        {"x": -10, "y": 100, "w": 500, "h": 500, "r": 0},
        {"x": 700, "y": 100, "w": 500, "h": 500, "r": 0},
    ]
    for bad in bad_boxes:
        with pytest.raises(ValueError):
            stage.clamp_window_box(bad)

    for bad_t in (float("nan"), float("inf"), float("-inf"), True, False, huge_pos, huge_neg, "1.0"):
        with pytest.raises(ValueError):
            stage.win(spec_huge_r, bad_t)

    # Reject forbidden branding fields, raw hex colors, non-boolean enabled, and hardcoded inline header text
    assert stage.validate_stage_spec({"version": 1, "logo": "brand.png"})
    assert stage.validate_stage_spec({"version": 1, "seriesName": "My Series"})
    assert stage.validate_stage_spec({"version": 1, "under": {"surfaceRole": "#123456"}})
    assert stage.validate_stage_spec({"version": 1, "enabled": "yes"})
    assert stage.is_stage_enabled(None) is False
    assert stage.is_stage_enabled({"version": 1, "enabled": False}) is False
    assert stage.is_stage_enabled({"version": 1, "enabled": True}) is True
    assert stage.is_stage_enabled({"version": 1}) is True
    assert stage.validate_stage_spec({
        "version": 1,
        "over": {"header": {"enabled": True, "slots": [{"id": "h1", "scene": 1, "copyId": "c1", "text": "ممنوع", "start": 0, "end": 1}]}},
    })


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a3_python_and_js_core_parity_and_byte_identical_k_r_module():
    k_stage = ENGINE_K / "lib" / "stage.js"
    r_stage = ENGINE_R / "src" / "lib" / "stage.js"
    assert k_stage.read_bytes() == r_stage.read_bytes(), "stage.js drifted between render/lib and remotion/src/lib"

    spec = _sample_stage_spec(radius=42.0)
    sample_ts = [round(i * 0.125, 4) for i in range(26)]
    py_states = [stage.stage_state_at(spec, t, duration=3.0) for t in sample_ts]

    js_code = f"""
import {{ stageStateAt, validateStageSpec, clampWindowBox }} from {json.dumps(k_stage.as_uri())};
const spec = {json.dumps(spec)};
const ts = {json.dumps(sample_ts)};
const states = ts.map(t => stageStateAt(spec, t, {{ duration: 3.0 }}));
const clampHi = clampWindowBox({{ x: 100, y: 300, w: 400, h: 220, r: 999 }});
const clampLo = clampWindowBox({{ x: 100, y: 300, w: 400, h: 220, r: -15 }});
const badLogo = validateStageSpec({{ version: 1, logo: 'x.png' }});
const badInline = validateStageSpec({{
  version: 1,
  over: {{ header: {{ enabled: true, slots: [{{ id: 'h', scene: 1, copyId: 'c', text: 'inline', start: 0, end: 1 }}] }} }}
}});
console.log(JSON.stringify({{ states, clampHi, clampLo, badLogo, badInline }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", js_code], capture_output=True, text=True, check=True)
    js_data = json.loads(res.stdout)
    assert js_data["clampHi"]["r"] == pytest.approx(110.0)
    assert js_data["clampLo"]["r"] == 0.0
    assert len(js_data["badLogo"]) >= 1
    assert len(js_data["badInline"]) >= 1

    for py_s, js_s in zip(py_states, js_data["states"], strict=True):
        assert py_s["mode"] == js_s["mode"]
        assert py_s["isFullscreen"] is js_s["isFullscreen"]
        assert py_s["transitionProgress"] == pytest.approx(js_s["transitionProgress"], abs=1e-9)
        assert py_s["chromeOpacity"] == pytest.approx(js_s["chromeOpacity"], abs=1e-9)
        assert py_s["progress"] == pytest.approx(js_s["progress"], abs=1e-9)
        for key in ("x", "y", "w", "h", "r"):
            assert py_s["win"][key] == pytest.approx(js_s["win"][key], abs=1e-9)


# ===========================================================================
# B. Stage Transition Tests
# ===========================================================================

def test_b1_bidirectional_fullscreen_framed_transitions_and_discontinuity_guard():
    box_a = {"x": 60, "y": 230, "w": 960, "h": 1080, "r": 36}
    box_b = {"x": 120, "y": 320, "w": 840, "h": 920, "r": 64}
    for ease_name in ("linear", "cubicOut", "cubicInOut", "quintOut", "quadInOut"):
        spec = {
            "version": 1,
            "timeline": [
                {"mode": "transition", "from": "fullscreen", "to": box_a, "start": 0.4, "end": 1.0, "ease": ease_name},
                {"mode": "transition", "from": box_a, "to": box_b, "start": 1.5, "end": 2.1, "ease": ease_name},
                {"mode": "transition", "from": box_b, "to": "fullscreen", "start": 2.5, "end": 3.1, "ease": ease_name},
            ],
        }
        assert stage.win(spec, 0.2) == {"x": 0.0, "y": 0.0, "w": 1080.0, "h": 1920.0, "r": 0.0}
        assert stage.win(spec, 1.25) == {k: float(v) for k, v in box_a.items()}
        assert stage.win(spec, 2.3) == {k: float(v) for k, v in box_b.items()}
        assert stage.win(spec, 3.4) == {"x": 0.0, "y": 0.0, "w": 1080.0, "h": 1920.0, "r": 0.0}

        if ease_name in ("linear", "cubicInOut", "quadInOut"):
            sym_spec = {
                "version": 1,
                "defaultFramedBox": box_a,
                "timeline": [
                    {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 1.0, "end": 2.0, "ease": ease_name},
                    {"mode": "transition", "from": "framed", "to": "fullscreen", "start": 3.0, "end": 4.0, "ease": ease_name},
                ],
            }
            for du in (0.1, 0.25, 0.5, 0.75, 0.9):
                w_in = stage.win(sym_spec, 1.0 + du)
                w_out = stage.win(sym_spec, 4.0 - du)
                for k in ("x", "y", "w", "h", "r"):
                    assert w_in[k] == pytest.approx(w_out[k], abs=1e-9)

    # Reject overlapping segments
    overlap_errs = stage.validate_stage_spec({
        "version": 1,
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 1.2},
            {"mode": "framed", "start": 1.0, "end": 2.0},
        ],
    })
    assert any("overlaps" in e for e in overlap_errs)

    # Reject discontinuous teleport between segments
    jump_errs = stage.validate_stage_spec({
        "version": 1,
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 1.0},
            {"mode": "framed", "start": 1.0, "end": 2.0},
        ],
    })
    assert any("discontinuous" in e for e in jump_errs)


def test_b2_stateless_forward_reverse_and_random_access_evaluation():
    spec = _sample_stage_spec()
    bound = stage.create_stage(spec)
    grid = [round(i / 30.0, 6) for i in range(91)]
    fwd = [bound["state_at"](t, duration=3.0) for t in grid]
    rev = list(reversed([bound["state_at"](t, duration=3.0) for t in reversed(grid)]))

    rng = random.Random(20261104)
    shuffled = list(enumerate(grid))
    rng.shuffle(shuffled)
    rnd_out: list[dict | None] = [None] * len(grid)
    for idx, t in shuffled:
        rnd_out[idx] = bound["state_at"](t, duration=3.0)

    assert fwd == rev
    assert fwd == rnd_out


# ===========================================================================
# C. Clipping Tests (Rectangular, Rounded Corners, Passthrough, Unclipped OVER)
# ===========================================================================

def test_c1_engine_p_rectangular_and_rounded_clipping_plus_unclipped_over():
    direction = _sample_direction()
    copy_by_id = {"hdr-topic-1": "مقارنة اللابتوب والكمبيوتر"}
    words = _sample_words()

    def _solid_white_with_transition(ts: float, _st: dict) -> np.ndarray:
        a = np.full((1920, 1080, 3), 243, dtype=np.uint8)
        b = np.full((1920, 1080, 3), 217, dtype=np.uint8)
        return transition.composite(a, b, "wipe", 0.5)

    # 1. Rectangular clip (r == 0): interior corners filled, 2px outside strictly UNDER (#030303)
    rect_spec = {
        "version": 1,
        "mode": "framed",
        "defaultFramedBox": {"x": 100, "y": 300, "w": 880, "h": 1000, "r": 0},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": None,
            "frame": {"enabled": False},
        },
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 6, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [{
                    "id": "hdr-1", "scene": 1, "copyId": "hdr-topic-1", "role": "label",
                    "start": 0.2, "end": 2.5, "x": 540, "y": 136, "size": 42, "colorRole": "paper",
                }],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }
    fr_rect = stage.render_fixed_stage(
        rect_spec,
        1.3,
        _solid_white_with_transition,
        duration=3.0,
        direction=direction,
        copy_by_id=copy_by_id,
        words=words,
        caption_style="pop",
    )
    # Outside window on left/right/top/bottom (avoiding OVER header/caption/progress zones) -> pure #030303
    assert tuple(fr_rect[800, 96]) == (3, 3, 3)
    assert tuple(fr_rect[800, 984]) == (3, 3, 3)
    assert tuple(fr_rect[295, 200]) == (3, 3, 3)
    assert tuple(fr_rect[1305, 200]) == (3, 3, 3)
    # Sharp corner inside (103, 303) has bright content (>200)
    assert int(fr_rect[303, 103, 0]) > 200

    # 2. Rounded-corner clip (r == 120): exterior corner luna (106, 306), (974, 306), (106, 1294), (974, 1294) -> pure #030303!
    round_spec = {
        **rect_spec,
        "defaultFramedBox": {"x": 100, "y": 300, "w": 880, "h": 1000, "r": 120},
    }
    fr_round = stage.render_fixed_stage(
        round_spec,
        1.3,
        _solid_white_with_transition,
        duration=3.0,
        direction=direction,
        copy_by_id=copy_by_id,
        words=words,
        caption_style="pop",
    )
    for cx, cy in ((106, 306), (974, 306), (106, 1294), (974, 1294)):
        assert tuple(fr_round[cy, cx]) == (3, 3, 3), f"Rounded corner leaked content at ({cx}, {cy}): {fr_round[cy, cx]}"
    # Center of window has bright content
    assert int(fr_round[800, 500, 0]) > 200

    # 3. OVER layer (progress bar y=64..70, header y~136, caption y~1455) is UNCLIPPED outside win(t)!
    assert int(fr_round[66, 200, 0]) == 203  # progress bar RED (#CB271B)
    assert int(fr_round[115:160, 280:800].max()) > 200  # header Arabic glyphs rendered above win(t)
    assert int(fr_round[1425:1485, 240:840].max()) > 200  # caption Arabic glyphs rendered below win(t)

    # 4. Full-screen passthrough: extreme canvas corners receive full content with zero clipping
    full_spec = {
        **rect_spec,
        "mode": "fullscreen",
        "over": {
            "progressBar": {"enabled": False},
            "header": {"enabled": False, "slots": []},
            "captions": {"enabled": False},
        },
    }
    fr_full = stage.render_fixed_stage(full_spec, 1.3, _solid_white_with_transition)
    assert int(fr_full[4, 4, 0]) > 200
    assert int(fr_full[1915, 1075, 0]) > 200


# ===========================================================================
# D. Layout Audit, Arabic/RTL & Plan Lint Tests
# ===========================================================================

@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_d1_three_boundary_layout_audit_across_p_and_k():
    stage_win = {"x": 80.0, "y": 240.0, "w": 920.0, "h": 1060.0, "r": 90.0}

    # Case 1: Valid Fixed Stage frame (intentional OVER header + OVER caption + safe CONTENT text + CONTENT face whose lower torso is clipped by win(t)) -> 0 issues!
    clean_boxes = [
        {"id": "hdr", "kind": "text", "zone": "hud", "layer": "over", "text": "موضوع الحلقة", "x": 360, "y": 112, "w": 360, "h": 48},
        {"id": "cap", "kind": "text", "zone": "caption", "layer": "over", "text": "الفرق الحقيقي", "x": 350, "y": 1430, "w": 380, "h": 50},
        {"id": "body", "kind": "text", "zone": "content", "layer": "content", "text": "شرح عملي", "x": 340, "y": 500, "w": 400, "h": 60},
        # Presenter sprite in CONTENT whose lower region (y=1280..1460) is clipped off at win.y+win.h=1300 -> must NOT falsely collide with OVER caption at y=1430!
        {"id": "medo-body", "kind": "keep", "layer": "content", "x": 340, "y": 900, "w": 400, "h": 560},
        # Intentional UNDER structural decoration -> must NOT trigger false positives
        {"id": "under-deco", "kind": "keep", "layer": "under", "x": 0, "y": 0, "w": 1080, "h": 1920},
    ]
    assert layout_p.audit_layout(clean_boxes, check_platform_ui=True, stage_win=stage_win) == []

    # Case 2: Violations across all 3 boundaries:
    # - L05: CONTENT text extending outside win(t) (x=55 < win.x=80, though >= margin 40!)
    # - L06: CONTENT RTL Arabic text inside win(t) rect [80..1000]x[240..1300] but clipped by top-right rounded corner (x+w=996, y=244, r=90)
    # - L03: OVER caption colliding with visible presenter `face` inside win(t) / content text colliding with face
    # - L04: Subtitle overlapping PLATFORM_RIGHT_RAIL (x=940..1080, y=1100..1500)
    # - L01: Foreground OVER badge escaping safe margin (x=12 < 40)
    violation_boxes = [
        {"id": "out-win", "kind": "text", "zone": "content", "layer": "content", "text": "خارج النافذة", "x": 50, "y": 600, "w": 300, "h": 52},
        {"id": "corner-ar", "kind": "text", "zone": "content", "layer": "content", "text": "أداء المعالج", "x": 720, "y": 244, "w": 276, "h": 48},
        {"id": "presenter-face", "kind": "face", "layer": "content", "x": 420, "y": 760, "w": 220, "h": 220},
        {"id": "face-hit", "kind": "text", "zone": "content", "layer": "content", "text": "تصادم الوجه", "x": 450, "y": 820, "w": 180, "h": 48},
        {"id": "rail-sub", "kind": "text", "zone": "caption", "layer": "over", "text": "يمين الشاشة", "x": 700, "y": 1420, "w": 330, "h": 52},
        {"id": "over-escape", "kind": "keep", "layer": "over", "x": 12, "y": 120, "w": 120, "h": 48},
    ]
    py_issues = layout_p.audit_layout(violation_boxes, check_platform_ui=True, stage_win=stage_win)
    py_codes_by_id: dict[str, set[str]] = {}
    for iss in py_issues:
        for bid in iss["ids"]:
            py_codes_by_id.setdefault(bid, set()).add(iss["code"])

    assert "L05" in py_codes_by_id["out-win"]
    assert "L06" in py_codes_by_id["corner-ar"]
    assert "L03" in py_codes_by_id["face-hit"]
    assert "L04" in py_codes_by_id["rail-sub"]
    assert "L01" in py_codes_by_id["over-escape"]

    # Verify Engine K layout.js produces identical issue codes on both clean and violation suites
    layout_js = (ENGINE_K / "lib" / "layout.js").as_uri()
    js_script = f"""
import {{ auditLayout }} from {json.dumps(layout_js)};
const stageWin = {json.dumps(stage_win)};
const clean = auditLayout({json.dumps(clean_boxes)}, {{ checkPlatformUi: true, stageWin }});
const bad = auditLayout({json.dumps(violation_boxes)}, {{ checkPlatformUi: true, stageWin }});
console.log(JSON.stringify({{ clean, bad }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", js_script], capture_output=True, text=True, check=True)
    js_out = json.loads(res.stdout)
    assert js_out["clean"] == []
    js_codes = {( tuple(i["ids"]), i["code"] ) for i in js_out["bad"]}
    py_codes = {( tuple(i["ids"]), i["code"] ) for i in py_issues}
    assert js_codes == py_codes


def test_d2_multiline_mixed_arabic_english_numerals_rtl_in_stage():
    spec = _sample_stage_spec(radius=96.0, with_header=False)
    direction = _sample_direction()
    multiline_ar = "ليه SSD PCIe 5.0 أغلى بـ ٢٥٪؟\nالمعالج والرامات 16GB DDR5"

    # Safe placement inside stage_safe_envelope -> 0 layout issues
    wb = stage.win(spec, 1.5)
    safe_env = stage.stage_safe_envelope(wb)
    safe_cx = (safe_env["x"][0] + safe_env["x"][1]) / 2.0
    safe_cy = safe_env["y"][0] + 110.0

    layout_p.begin_frame()
    try:
        stage.render_fixed_stage(
            spec,
            1.5,
            lambda ts, _st: (
                lambda buf: (
                    captions.draw_directed_text(
                        buf,
                        multiline_ar,
                        direction=direction,
                        scene=1,
                        role="title",
                        element_id="ar-safe",
                        t=ts,
                        start=0.0,
                        end=3.0,
                        cx=safe_cx,
                        cy=safe_cy,
                        size=46,
                        color=WHITE,
                        accent=YEL,
                    ),
                    buf.astype(np.uint8),
                )[1]
            )(np.zeros((1920, 1080, 3), dtype=np.float32)),
        )
        win_snap = layout_p.stage_window()
        boxes_safe = layout_p.end_frame()
    except BaseException:
        layout_p.end_frame()
        raise

    assert len([b for b in boxes_safe if b["kind"] == "text"]) == 2
    assert layout_p.audit_layout(boxes_safe, check_platform_ui=True, stage_win=win_snap) == []

    # Unsafe placement pushed into top-right rounded corner of win(t) -> triggers L06!
    layout_p.begin_frame()
    try:
        stage.render_fixed_stage(
            spec,
            1.5,
            lambda ts, _st: (
                lambda buf: (
                    captions.draw_directed_text(
                        buf,
                        "أداء فائق السرعة",
                        direction=direction,
                        scene=1,
                        role="title",
                        element_id="ar-corner",
                        t=ts,
                        start=0.0,
                        end=3.0,
                        cx=865.0,
                        cy=268.0,
                        size=42,
                        color=WHITE,
                        accent=YEL,
                    ),
                    buf.astype(np.uint8),
                )[1]
            )(np.zeros((1920, 1080, 3), dtype=np.float32)),
        )
        win_snap2 = layout_p.stage_window()
        boxes_corner = layout_p.end_frame()
    except BaseException:
        layout_p.end_frame()
        raise

    issues_corner = layout_p.audit_layout(boxes_corner, stage_win=win_snap2)
    assert any(i["code"] == "L06" for i in issues_corner), issues_corner


def test_d3_reel_lint_validates_plan_stage_json_contract_and_anchors(tmp_path: Path):
    proj = tmp_path / "lint-stage-proj"
    shutil.copytree(ROOT / "tests" / "fixtures" / "reel" / "good", proj)

    beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
    copy_doc = json.loads((proj / "plan" / "copy.json").read_text(encoding="utf-8"))
    first_copy = copy_doc["copy"][0]
    cid = first_copy["id"]
    sc_idx = first_copy["scene"]

    (proj / "plan" / "word-timings.json").write_text(
        json.dumps({
            "clock": "vo",
            "scenes": [
                {
                    "scene": sc_idx,
                    "words": [
                        {"text": "البداية", "start": 0.2, "end": 0.7},
                        {"text": "السبب", "start": 1.0, "end": 1.5},
                    ],
                }
            ],
        }, ensure_ascii=False),
        encoding="utf-8",
    )

    valid_stage = {
        "version": 1,
        "id": "good-stage",
        "clock": "vo",
        "theme": "dark",
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 1.0},
            {
                "mode": "transition",
                "from": "fullscreen",
                "to": "framed",
                "start": 1.0,
                "end": 1.6,
                "anchor": {"scene": sc_idx, "word": 1, "text": "السبب"},
            },
            {"mode": "framed", "start": 1.6, "end": float(beats["duration"])},
        ],
        "over": {
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-main",
                        "scene": sc_idx,
                        "copyId": cid,
                        "role": first_copy["role"],
                        "start": 1.0,
                        "end": min(3.0, float(beats["duration"])),
                    }
                ],
            }
        },
    }
    (proj / "plan" / "stage.json").write_text(json.dumps(valid_stage, ensure_ascii=False), encoding="utf-8")

    ok = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(proj)],
        capture_output=True,
        text=True,
    )
    assert ok.returncode == 0, ok.stdout + "\n" + ok.stderr
    assert "F00" in ok.stdout

    # Mutate with missing copyId, past-duration timeline, and drifted word anchor -> F02 + F03 + F04
    bad_stage = json.loads(json.dumps(valid_stage))
    bad_stage["timeline"][1]["start"] = 2.2
    bad_stage["timeline"][0]["end"] = 2.2
    bad_stage["timeline"][1]["end"] = 2.6
    bad_stage["timeline"][2]["start"] = 2.6
    bad_stage["timeline"][2]["end"] = float(beats["duration"]) + 5.0
    bad_stage["over"]["header"]["slots"][0]["copyId"] = "non-existent-copy-id"
    (proj / "plan" / "stage.json").write_text(json.dumps(bad_stage, ensure_ascii=False), encoding="utf-8")

    bad = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(proj)],
        capture_output=True,
        text=True,
    )
    assert bad.returncode == 1
    for code in ("F02", "F03", "F04"):
        assert code in bad.stdout, bad.stdout


# ===========================================================================
# E. Cross-Engine Real Rendering Verification (Engines K & R in Chromium)
# ===========================================================================
