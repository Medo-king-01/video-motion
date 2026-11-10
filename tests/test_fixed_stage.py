"""Phase 2A — Fixed Stage comprehensive test suite (Categories A–G across Engines P, K, and R)."""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
ENGINE_K = SKILL / "templates" / "render"
ENGINE_R = SKILL / "templates" / "remotion"
TOOLS = ROOT / "tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ENGINE_P) in sys.path:
    sys.path.remove(str(ENGINE_P))
sys.path.insert(0, str(ENGINE_P))

import captions  # noqa: E402
import layout_p  # noqa: E402
import stage  # noqa: E402
import transition  # noqa: E402
from lib import INK, RED, WHITE, YEL, fill_rect  # noqa: E402

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


def _sample_stage_spec(*, radius: float = 48.0, with_header: bool = True) -> dict:
    hdr_slots = (
        [
            {
                "id": "hdr-s1",
                "scene": 1,
                "copyId": "hdr-topic-1",
                "role": "label",
                "start": 0.6,
                "end": 2.4,
                "x": 540,
                "y": 136,
                "size": 38,
                "maxWidth": 880,
                "colorRole": "paper",
                "accentRole": "salmon",
                "pillRole": "ink",
                "pillBorderRole": "red",
                "pillAlpha": 0.92,
                "anchor": {"scene": 1, "word": 1, "text": "الفرق"},
            }
        ]
        if with_header
        else []
    )
    return {
        "version": 1,
        "id": "test-fixed-stage",
        "clock": "vo",
        "theme": "dark",
        "canvas": {"w": 1080, "h": 1920, "fps": 30},
        "defaultFramedBox": {"x": 80, "y": 240, "w": 920, "h": 1060, "r": radius},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": {"id": "wash", "theme": "dark", "density": 40, "angle": 0, "speed": 1.0},
            "frame": {
                "enabled": True,
                "strokeRole": "red",
                "strokeWidth": 3,
                "matRole": "ink_shadow",
                "matAlpha": 0.35,
            },
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.5},
            {
                "mode": "transition",
                "from": "fullscreen",
                "to": "framed",
                "start": 0.5,
                "end": 1.1,
                "ease": "cubicInOut",
                "anchor": {"scene": 1, "word": 1, "text": "الفرق"},
            },
            {"mode": "framed", "start": 1.1, "end": 2.1},
            {
                "mode": "transition",
                "from": "framed",
                "to": "fullscreen",
                "start": 2.1,
                "end": 2.7,
                "ease": "cubicInOut",
            },
            {"mode": "fullscreen", "start": 2.7, "end": 3.0},
        ],
        "over": {
            "progressBar": {
                "enabled": True,
                "y": 64,
                "height": 6,
                "marginX": 60,
                "trackRole": "paper",
                "trackAlpha": 0.18,
                "fillRole": "red",
            },
            "header": {
                "enabled": with_header,
                "slots": hdr_slots,
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }


def _sample_direction() -> dict:
    return {
        "version": 3,
        "status": "directed",
        "decidedBy": "agent",
        "concept": "Fixed Stage technical verification",
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "pop",
                "captionWhy": "clear word emphasis synchronized to VO",
                "textStyles": {
                    "title": "riseword",
                    "body": "softfade",
                    "label": "softfade",
                },
                "textWhy": "clean legible motion inside Fixed Stage",
                "fontStyles": {
                    "title": {"family": "Cairo", "weight": 800},
                    "body": {"family": "Cairo", "weight": 700},
                    "label": {"family": "Cairo", "weight": 800},
                },
                "fontWhy": "Cairo bold Arabic legibility",
            }
        ],
    }


def _sample_words() -> list[dict]:
    return [
        {"text": "إيه", "start": 0.15, "end": 0.48},
        {"text": "الفرق", "start": 0.55, "end": 1.05},
        {"text": "الحقيقي", "start": 1.15, "end": 1.75},
        {"text": "بينهم؟", "start": 1.80, "end": 2.45},
    ]


# ===========================================================================
# A. Unit Tests — Core Stage Geometry & Parity
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

@pytest.fixture(scope="module")
def _chromium_env():
    if shutil.which("node") is None:
        pytest.skip("node is not installed")
    chrom_proc = subprocess.run(
        ["node", str(TOOLS / "chromium.mjs"), "--json"],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if chrom_proc.returncode != 0:
        pytest.skip(f"Chromium unavailable: {chrom_proc.stderr}")
    chrom = json.loads(chrom_proc.stdout)
    env = {
        **os.environ,
        "PATH": f"{ROOT / 'tools' / 'bin'}:{ROOT / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
        "MEDO_TOOLKIT": str(ROOT / "tools" / "toolkit"),
        "MEDO_CHROMIUM": chrom["executablePath"],
        "REMOTION_BROWSER_EXECUTABLE": chrom["executablePath"],
    }
    if chrom.get("args"):
        env["REMOTION_CHROMIUM_ARGS"] = " ".join(chrom["args"])
    if chrom.get("libraryPath"):
        env["LD_LIBRARY_PATH"] = ":".join(
            [p for p in (chrom["libraryPath"], env.get("LD_LIBRARY_PATH")) if p]
        )
    return chrom, env


@pytest.fixture(autouse=True)
def _cleanup_stage_tmp(request):
    """Reclaim multi-hundred-MB scaffolded assets/fonts/bundles right after each test
    so multi-pass CI jobs (`ci.sh` + `selftest.py --remotion --hybrid`) never hit ENOSPC."""
    import tempfile  # noqa: PLC0415

    tmp_root = Path(tempfile.gettempdir())
    before_bundles = set(tmp_root.glob("remotion-webpack-bundle-*"))
    yield
    tp = request.node.funcargs.get("tmp_path")
    if isinstance(tp, Path) and tp.is_dir():
        for child in tp.iterdir():
            if child.is_symlink():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
    for leaked in set(tmp_root.glob("remotion-webpack-bundle-*")) - before_bundles:
        shutil.rmtree(leaked, ignore_errors=True)


@pytest.fixture(scope="module")
def _remotion_runtime(_chromium_env, tmp_path_factory):
    _chrom, env = _chromium_env
    env_mods = os.environ.get("MEDO_REMOTION_TEST_NODE_MODULES")
    owned_deps_dir: Path | None = None
    if env_mods and Path(env_mods).is_dir():
        modules_dir = Path(env_mods).resolve()
    else:
        if shutil.which("npm") is None:
            pytest.skip("npm is not installed and MEDO_REMOTION_TEST_NODE_MODULES is unset")
        owned_deps_dir = tmp_path_factory.mktemp("remotion_stage_deps")
        shutil.copy2(ENGINE_R / "package.json", owned_deps_dir / "package.json")
        shutil.copy2(ENGINE_R / "package-lock.json", owned_deps_dir / "package-lock.json")
        ci_res = subprocess.run(
            ["npm", "ci", "--prefer-offline", "--no-audit", "--no-fund"],
            cwd=owned_deps_dir,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if ci_res.returncode != 0:
            shutil.rmtree(owned_deps_dir, ignore_errors=True)
            pytest.skip(f"Remotion npm ci unavailable offline: {ci_res.stderr[:240]}")
        modules_dir = owned_deps_dir / "node_modules"
    try:
        yield modules_dir, env
    finally:
        if owned_deps_dir is not None:
            shutil.rmtree(owned_deps_dir, ignore_errors=True)


def _run_remotion_stills_batch(proj: Path, env: dict, tasks: list[dict]) -> dict[str, dict]:
    """Bundle `src/index.ts` ONCE and render multiple stills/props in ONE persistent Chromium
    instance (`@remotion/bundler` + `@remotion/renderer`), avoiding redundant Webpack builds."""
    runner_js = """
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const tasks = JSON.parse(process.argv[1]);
const entryPoint = path.resolve('src/index.ts');
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE;
const serveUrl = await bundle({entryPoint, onProgress: () => {}});
const puppeteerInstance = await openBrowser('chrome', {
  browserExecutable,
  chromiumOptions: {disableWebSecurity: false},
});
const results = {};
try {
  for (const t of tasks) {
    try {
      const inputProps = t.props || {};
      const composition = await selectComposition({
        serveUrl,
        id: t.compId,
        puppeteerInstance,
        inputProps,
      });
      await renderStill({
        composition,
        serveUrl,
        frame: t.frame,
        imageFormat: 'png',
        output: t.outPath ? path.resolve(t.outPath) : null,
        puppeteerInstance,
        inputProps,
      });
      results[t.key] = {ok: true, error: null};
    } catch (err) {
      results[t.key] = {ok: false, error: String(err?.stack || err?.message || err)};
    }
  }
  console.log('__BATCH_RESULTS__' + JSON.stringify(results));
} finally {
  process.on('unhandledRejection', () => {});
  await new Promise((r) => setTimeout(r, 150));
  try {
    await puppeteerInstance.close({silent: true});
  } catch {}
  try {
    fs.rmSync(serveUrl, {recursive: true, force: true});
  } catch {}
}
process.exit(0);
"""
    res = subprocess.run(
        ["node", "--input-type=module", "-e", runner_js, json.dumps(tasks)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert res.returncode == 0, res.stdout + "\n" + res.stderr
    marker_lines = [ln for ln in res.stdout.splitlines() if ln.startswith("__BATCH_RESULTS__")]
    assert marker_lines, res.stdout + "\n" + res.stderr
    return json.loads(marker_lines[-1][len("__BATCH_RESULTS__"):])


def test_e1_engine_k_real_chromium_render_and_audit_replay(tmp_path: Path, _chromium_env):
    _chrom, env = _chromium_env
    proj = tmp_path / "k_stage_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "k-stage-test", "--engine", "k", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )

    beats = {
        "duration": 2.0,
        "fps": 30,
        "frames": 60,
        "bounds": [0.0, 2.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 2.0, "dur": 2.0, "frames": 60, "theme": "dark"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-k-1", "scene": 1, "role": "label", "text": "موضوع الحلقة: معمارية المعالج", "start": 0.4, "end": 1.9},
            {"id": "body-k-1", "scene": 1, "role": "title", "text": "الفرق بين اللابتوب والمكتبي", "start": 0.0, "end": 2.0},
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "k-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 100, "y": 280, "w": 880, "h": 1000, "r": 100},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.3},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.3, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 2.0},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-k",
                        "scene": 1,
                        "copyId": "hdr-k-1",
                        "role": "label",
                        "start": 0.4,
                        "end": 1.9,
                        "x": 540,
                        "y": 136,
                        "size": 40,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }

    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    (proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 2.0 }];\n"
        "export const DURATION = 2.0;\n",
        encoding="utf-8",
    )
    words_js = json.dumps([
        {"text": "الفرق", "start": 0.1, "end": 0.9},
        {"text": "الحقيقي", "start": 0.95, "end": 1.85},
    ], ensure_ascii=False)
    (proj / "src" / "scenes" / "s1.js").write_text(
        f"""import {{ renderFixedStage }} from '../lib/stage-canvas.js';
import {{ drawDirectedText, useDirectedFonts }} from '../lib/captions.js';
import {{ compositeTransition, makeLayer }} from '../lib/transition.js';
import {{ PALETTE }} from '../lib/brand.js';

export const supportsReducedMotion = true;
export const manualFixedStage = true;
let stageSpec = null;
let copyMap = {{}};
const WORDS = {words_js};

export async function init() {{
  const [stRes, cpRes, tdRes] = await Promise.all([
    fetch('/plan/stage.json'),
    fetch('/plan/copy.json'),
    fetch('/plan/text-direction.json'),
  ]);
  stageSpec = await stRes.json();
  const cpDoc = await cpRes.json();
  for (const item of cpDoc.copy || []) copyMap[item.id] = item.text;
  const tdDoc = await tdRes.json();
  await useDirectedFonts(tdDoc, 1);
}}

export async function draw(ctx, localT, {{ W, H, t, direction, motionMode }}) {{
  await renderFixedStage(ctx, stageSpec, t, {{
    duration: 2.0,
    direction,
    copyById: copyMap,
    words: WORDS,
    captionStyle: 'pop',
    motionMode,
    drawContent: (c) => {{
      // Bright paper fill + salmon wipe transition spanning the whole 1080x1920 CONTENT space
      const layA = makeLayer(W, H, (g) => {{ g.fillStyle = PALETTE.paper; g.fillRect(0, 0, W, H); }});
      const layB = makeLayer(W, H, (g) => {{ g.fillStyle = PALETTE.salmon; g.fillRect(0, 0, W, H); }});
      compositeTransition(c, layA, layB, 'wipe', 0.5, W, H);
      drawDirectedText(c, copyMap['body-k-1'], {{
        direction, scene: 1, role: 'title', elementId: 'body-k-1',
        time: localT, start: 0, end: 2.0, x: 540, y: 740, size: 54,
        color: PALETTE.ink, theme: 'light', shadow: 'transparent',
      }});
    }},
  }});
}}
""",
        encoding="utf-8",
    )

    # 1. Run Engine K layout audit + reverse-seek RGBA SHA-256 replay + social right-rail check
    audit_out = proj / "cache" / "audit-k"
    audit_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "2.0", "--fps", "30", "--audit", "--replay", "--platform-ui", "--out", str(audit_out)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert audit_res.returncode == 0, audit_res.stdout + "\n" + audit_res.stderr
    report = json.loads((audit_out / "report.json").read_text(encoding="utf-8"))
    assert report["status"] == "pass"
    assert report["replay"]["status"] == "pass"
    assert report["replay"]["checkedFrames"] == 60
    assert report["replay"]["failedFrames"] == 0

    # 2. Render actual JPG frames and inspect fullscreen vs framed rounded clipping & unclipped OVER
    frames_out = proj / "cache" / "frames-k"
    jpg_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "2.0", "--fps", "30", "--jpg", "--out", str(frames_out)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert jpg_res.returncode == 0, jpg_res.stdout + "\n" + jpg_res.stderr

    # Frame 3 (t=0.10s -> fullscreen): extreme corner (10, 10) has bright content
    im_full = np.asarray(Image.open(frames_out / "00003.jpg").convert("RGB"))
    assert int(im_full[10, 10].max()) > 180

    # Frame 36 (t=1.20s -> framed x=100..980, y=280..1280, r=100):
    im_framed = np.asarray(Image.open(frames_out / "00036.jpg").convert("RGB"))
    # Outside window on left (x=50, y=800) & inside exterior rounded corner luna (x=106, y=286): dark #030303 (JPEG <= 12)
    assert int(im_framed[800, 50].max()) <= 12
    assert int(im_framed[286, 106].max()) <= 12
    assert int(im_framed[286, 974].max()) <= 12
    assert int(im_framed[1274, 106].max()) <= 12
    assert int(im_framed[1274, 974].max()) <= 12
    # Interior of window has bright wipe transition (left side salmon, right side paper)
    assert int(im_framed[600, 300].max()) > 180
    assert int(im_framed[600, 800].max()) > 220
    # Unclipped OVER header (y~136), progress bar (y~66), and caption (y~1455) render outside win(t)!
    assert int(im_framed[64:72, 100:500, 0].max()) > 170
    assert int(im_framed[115:160, 250:830].max()) > 180
    assert int(im_framed[1425:1485, 250:830].max()) > 180


def test_e2_engine_r_real_remotion_chromium_render_and_dom_layout_audit(tmp_path: Path, _remotion_runtime):
    modules_dir, env = _remotion_runtime
    proj = tmp_path / "r_stage_proj"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-stage-test", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)

    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "r-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 100, "y": 280, "w": 880, "h": 1000, "r": 100},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.4},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.4, "end": 1.0, "ease": "cubicInOut"},
            {"mode": "framed", "start": 1.0, "end": 3.0},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-r",
                        "scene": 1,
                        "copyId": "hdr-r-1",
                        "role": "label",
                        "start": 0.5,
                        "end": 2.8,
                        "x": 540,
                        "y": 136,
                        "size": 40,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }
    copy_map = {
        "hdr-r-1": "موضوع الحلقة: معمارية الذاكرة",
        "body-r-1": "الفرق بين DDR5 و DDR4",
        "cap-r-1": "سرعة نقل أعلى بكثير",
    }

    (proj / "plan" / "beats.json").write_text(
        json.dumps({"duration": 3.0, "fps": 30, "frames": 90, "bounds": [0, 3.0], "scenes": [{"index": 1, "start": 0, "end": 3.0, "dur": 3.0, "frames": 90}]}),
        encoding="utf-8",
    )
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")

    root_tsx = f"""import React, {{useEffect, useLayoutEffect, useRef, useState}} from 'react';
import {{AbsoluteFill, Composition, cancelRender, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND, PALETTE}} from './brand';
import {{FixedStage}} from './lib/FixedStage';
import {{DirectedText}} from './lib/DirectedText';
import {{auditLayout, collectDomLayoutBoxes, collectDomStageWindow}} from './lib/layout';

const STAGE_SPEC = {json.dumps(stage_spec)};
const TD = {json.dumps(td_doc)};
const COPY = {json.dumps(copy_map, ensure_ascii=False)};

type StageTestProps = {{ mode?: 'clean' | 'outside_win' | 'corner_clip' }};

const StageComp: React.FC<StageTestProps> = ({{mode = 'clean'}}) => {{
  const frame = useCurrentFrame();
  const {{fps, durationInFrames}} = useVideoConfig();
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [fontsReady, setFontsReady] = useState(false);
  const [fontGate] = useState(() => delayRender('Load Cairo font'));

  useEffect(() => {{
    Promise.all([
      new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_800ExtraBold.ttf')}}')`, {{weight: '800'}}).load(),
      new FontFace('Cairo', `url('${{staticFile('fonts/Cairo/Cairo_700Bold.ttf')}}')`, {{weight: '700'}}).load(),
    ])
      .then((faces) => {{
        faces.forEach((f) => document.fonts.add(f));
        setFontsReady(true);
        continueRender(fontGate);
      }})
      .catch((e) => cancelRender(e));
  }}, [fontGate]);

  useLayoutEffect(() => {{
    if (!fontsReady || !rootRef.current) return;
    const boxes = collectDomLayoutBoxes(rootRef.current);
    const stageWin = collectDomStageWindow(rootRef.current);
    const issues = auditLayout(boxes, {{checkPlatformUi: true, stageWin}});
    if (issues.length > 0) {{
      cancelRender(
        new Error(`Remotion Stage Audit Failed: ${{issues.map((i) => `${{i.code}}: ${{i.message}}`).join('; ')}}`),
      );
    }}
  }}, [fontsReady, frame, mode]);

  const t = frame / fps;
  const contentStyle: React.CSSProperties =
    mode === 'outside_win'
      ? {{position: 'absolute', top: 680, left: 48, fontSize: 48, textAlign: 'left'}}
      : mode === 'corner_clip'
        ? {{position: 'absolute', top: 284, right: 104, fontSize: 44, textAlign: 'right'}}
        : {{position: 'absolute', top: 680, left: 180, right: 180, fontSize: 52, textAlign: 'center'}};

  return (
    <AbsoluteFill ref={{rootRef}}>
      <FixedStage
        spec={{STAGE_SPEC}}
        time={{t}}
        duration={{durationInFrames / fps}}
        direction={{TD}}
        copyById={{COPY}}
        over={{
          <DirectedText
            direction={{TD}}
            scene={{1}}
            role="label"
            elementId="cap-r-1"
            zone="caption"
            time={{t}}
            start={{0}}
            end={{3.0}}
            size={{46}}
            color={{PALETTE.paper}}
            style={{{{position: 'absolute', top: 1425, left: 140, right: 140, fontSize: 46, textAlign: 'center'}}}}
          >
            {{COPY['cap-r-1']}}
          </DirectedText>
        }}
      >
        <AbsoluteFill style={{{{backgroundColor: PALETTE.paper}}}}>
          <DirectedText
            direction={{TD}}
            scene={{1}}
            role="title"
            elementId="body-r-1"
            zone="content"
            time={{t}}
            start={{0}}
            end={{3.0}}
            size={{48}}
            color={{PALETTE.ink}}
            theme="light"
            style={{contentStyle}}
          >
            {{COPY['body-r-1']}}
          </DirectedText>
        </AbsoluteFill>
      </FixedStage>
    </AbsoluteFill>
  );
}};

export const RemotionRoot: React.FC = () => (
  <Composition
    id="FixedStageRealTest"
    component={{StageComp}}
    durationInFrames={{90}}
    fps={{BRAND.fps}}
    width={{BRAND.width}}
    height={{BRAND.height}}
    defaultProps={{{{mode: 'clean'}}}}
  />
);
"""
    (proj / "src" / "Root.tsx").write_text(root_tsx, encoding="utf-8")

    # 1. Strict TypeScript check (`tsc --noEmit`) across FixedStage.tsx, stage.js, layout.tsx, and Root.tsx
    tsc = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc.returncode == 0, tsc.stdout + "\n" + tsc.stderr

    batch_e2 = _run_remotion_stills_batch(
        proj,
        env,
        [
            {"key": "full", "compId": "FixedStageRealTest", "frame": 6, "outPath": str(proj / "full.png"), "props": {"mode": "clean"}},
            {"key": "framed", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "framed.png"), "props": {"mode": "clean"}},
            {"key": "l05", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "bad_l05.png"), "props": {"mode": "outside_win"}},
            {"key": "l06", "compId": "FixedStageRealTest", "frame": 48, "outPath": str(proj / "bad_l06.png"), "props": {"mode": "corner_clip"}},
        ],
    )
    assert batch_e2["full"]["ok"], batch_e2["full"]["error"]
    im_full = np.asarray(Image.open(proj / "full.png").convert("RGB"))
    assert tuple(im_full[10, 10]) == (243, 242, 241)

    assert batch_e2["framed"]["ok"], batch_e2["framed"]["error"]
    im_framed = np.asarray(Image.open(proj / "framed.png").convert("RGB"))
    # Outside window & inside exterior rounded-corner lunas -> exact ink_shadow (#030303 -> RGB 3,3,3)
    assert tuple(im_framed[800, 50]) == (3, 3, 3)
    for cx, cy in ((106, 286), (974, 286), (106, 1274), (974, 1274)):
        assert tuple(im_framed[cy, cx]) == (3, 3, 3), f"Engine R rounded clip leaked at ({cx}, {cy}): {im_framed[cy, cx]}"
    # Interior of window -> bright paper (#F3F2F1)
    assert tuple(im_framed[500, 540]) == (243, 242, 241)
    # Unclipped OVER layer: progress bar (y=66), header (y~136), caption (y~1445)
    assert int(im_framed[66, 200, 0]) == 203
    assert int(im_framed[115:160, 260:820].max()) > 200
    assert int(im_framed[1420:1480, 260:820].max()) > 200

    # DOM Layout Audit in Chromium catches L05 (outside win(t)) and L06 (rounded-corner Arabic glyph clipping)
    assert not batch_e2["l05"]["ok"]
    assert "L05" in batch_e2["l05"]["error"]
    assert not batch_e2["l06"]["ok"]
    assert "L06" in batch_e2["l06"]["error"]


def test_e3_scaffolded_projects_auto_apply_plan_stage_json_without_rewriting_entrypoints(
    tmp_path: Path, _remotion_runtime
):
    """Scaffold fresh P, K, and R projects via `tools/new_project.py` and activate Fixed Stage
    purely via project plan/data files — without modifying any engine runtime entrypoint."""
    modules_dir, env = _remotion_runtime
    ff = shutil.which("ffmpeg", path=env["PATH"])
    assert ff is not None

    # ---- 1. Engine P scaffolded project (scenes.py untouched!) ----
    p_proj = tmp_path / "auto_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    draft_stage = json.loads((p_proj / "plan" / "stage.json").read_text(encoding="utf-8"))
    assert draft_stage["enabled"] is False
    assert draft_stage["defaultFramedBox"] == {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 36}

    scenes_py_before = hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest()
    from chunk_utils import build_signature  # noqa: PLC0415

    sig_disabled = build_signature(p_proj, p_proj / "assets", 45, 15, [0.0, 1.5], 30, 1080, 1920)

    p_beats = {
        "duration": 1.5,
        "fps": 30,
        "frames": 45,
        "bounds": [0.0, 1.5],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.5, "dur": 1.5, "frames": 45, "theme": "dark"}],
    }
    p_copy = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-auto", "scene": 1, "role": "label", "text": "موضوع الحلقة: التفعيل التلقائي", "start": 0.5, "end": 1.45}
        ],
    }
    p_td = _sample_direction()
    # Engine K's example.js fills #030303, so UNDER="paper" (#F3F2F1) contrasts cleanly;
    # Engine P's scene1 (THEME[0]==0) & Engine R's MotionReel scene 0 are light scenes, so UNDER="ink_shadow" (#030303) contrasts cleanly!
    auto_stage_paper = {
        "version": 1,
        "enabled": True,
        "id": "auto-stage-k",
        "clock": "vo",
        "theme": "light",
        "defaultFramedBox": {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 90},
        "under": {
            "surfaceRole": "paper",
            "background": None,
            "frame": {"enabled": False},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.3},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.3, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 1.5},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "ink", "trackAlpha": 0.18, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-auto-slot",
                        "scene": 1,
                        "copyId": "hdr-auto",
                        "role": "label",
                        "start": 0.5,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                        "colorRole": "ink",
                    }
                ],
            },
            "captions": {"enabled": True, "y": 1455},
        },
    }
    auto_stage_dark = {
        **auto_stage_paper,
        "id": "auto-stage-pr",
        "theme": "dark",
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 8, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.2, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-auto-dark",
                        "scene": 1,
                        "copyId": "hdr-auto",
                        "role": "label",
                        "start": 0.5,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                        "colorRole": "paper",
                    }
                ],
            },
            "captions": {"enabled": False, "y": 1455},
        },
    }
    (p_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (p_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (p_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (p_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_dark), encoding="utf-8")

    sig_enabled = build_signature(p_proj, p_proj / "assets", 45, 15, [0.0, 1.5], 30, 1080, 1920)
    assert sig_enabled != sig_disabled, "Modifying plan/stage.json must invalidate Engine P chunk cache signature"
    assert hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest() == scenes_py_before

    p_seg = p_proj / "out" / "auto_p.mp4"
    p_run = subprocess.run(
        [
            sys.executable, str(TOOLS / "render_p_segment.py"),
            "--project", str(p_proj),
            "--from-frame", "0", "--to-frame", "36",
            "--out", str(p_seg),
            "--ffmpeg", ff,
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert p_run.returncode == 0, p_run.stdout + "\n" + p_run.stderr
    assert hashlib.sha256((p_proj / "scenes.py").read_bytes()).hexdigest() == scenes_py_before

    import av  # noqa: PLC0415

    with av.open(str(p_seg)) as container:
        decoded_p = [f.to_ndarray(format="rgb24") for f in container.decode(video=0)]
    assert len(decoded_p) == 36
    # Frame 3 (t=0.10s, fullscreen): corner (10, 10) is scene1's light background (>190 luma)
    assert int(decoded_p[3][10, 10].min()) > 190
    # Frame 30 (t=1.00s, framed x=56..1024, y=224..1320, r=90): exterior (20, 700) & corner luna (62, 230) -> UNDER ink_shadow (<15)
    assert int(decoded_p[30][700, 20].max()) < 15
    assert int(decoded_p[30][230, 62].max()) < 15
    # OVER progress bar (y=66, x=150) -> RED, and OVER header (y=115..160) has bright paper glyphs (>200) on dark UNDER!
    assert int(decoded_p[30][66, 150, 0]) > 180 and int(decoded_p[30][66, 150, 2]) < 60
    assert int(decoded_p[30][115:160, 260:820].max()) > 200

    # ---- 2. Engine K scaffolded project (src/main.js, src/data.js & src/scenes/*.js ALL untouched!) ----
    k_proj = tmp_path / "auto_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    k_main_before = hashlib.sha256((k_proj / "src" / "main.js").read_bytes()).hexdigest()
    k_data_before = hashlib.sha256((k_proj / "src" / "data.js").read_bytes()).hexdigest()
    k_scene_before = hashlib.sha256((k_proj / "src" / "scenes" / "example.js").read_bytes()).hexdigest()

    (k_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (k_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_paper), encoding="utf-8")

    k_frames = k_proj / "cache" / "auto-k-frames"
    k_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "1.2", "--fps", "30", "--jpg", "--out", str(k_frames)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res.returncode == 0, k_res.stdout + "\n" + k_res.stderr
    assert hashlib.sha256((k_proj / "src" / "main.js").read_bytes()).hexdigest() == k_main_before
    assert hashlib.sha256((k_proj / "src" / "data.js").read_bytes()).hexdigest() == k_data_before
    assert hashlib.sha256((k_proj / "src" / "scenes" / "example.js").read_bytes()).hexdigest() == k_scene_before

    k_full = np.asarray(Image.open(k_frames / "00003.jpg").convert("RGB"))
    k_framed = np.asarray(Image.open(k_frames / "00030.jpg").convert("RGB"))
    # Frame 3 (t=0.10s, fullscreen): example.js fills #030303 -> corner (10, 10) is dark (<20)
    assert int(k_full[10, 10].max()) < 20
    # Frame 30 (t=1.00s, framed r=90): exterior (20, 700) & rounded-corner luna (62, 230) -> UNDER paper (>230), interior (540, 500) -> dark (<20)
    assert int(k_framed[700, 20].min()) > 230
    assert int(k_framed[230, 62].min()) > 230
    assert int(k_framed[500, 540].max()) < 20
    assert int(k_framed[66, 150, 0]) > 180 and int(k_framed[66, 150, 2]) < 50
    assert int(k_framed[115:160, 260:820].min()) < 80

    # ---- 3. Engine R scaffolded project (src/RemotionRoot.tsx, src/Root.tsx, src/index.ts untouched!) ----
    r_proj = tmp_path / "auto_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "auto-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    r_root_before = hashlib.sha256((r_proj / "src" / "RemotionRoot.tsx").read_bytes()).hexdigest()
    r_entry_before = hashlib.sha256((r_proj / "src" / "Root.tsx").read_bytes()).hexdigest()

    (r_proj / "plan" / "beats.json").write_text(json.dumps(p_beats), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(p_copy, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(p_td), encoding="utf-8")
    (r_proj / "plan" / "stage.json").write_text(json.dumps(auto_stage_dark), encoding="utf-8")

    # Replace data.ts placeholder copy cards (standard data configuration required by render.mjs)
    data_ts = (r_proj / "src" / "data.ts").read_text(encoding="utf-8")
    for old_s, new_s in (
        ("اكتب عنوان المشهد", "عنوان المشهد الأول"),
        ("حط هنا الجملة الأساسية اللي عايز المشاهد يفتكرها.", "جملة أساسية واضحة داخل النافذة."),
    ):
        data_ts = data_ts.replace(old_s, new_s)
    (r_proj / "src" / "data.ts").write_text(data_ts, encoding="utf-8")

    tsc_r = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_r.returncode == 0, tsc_r.stdout + "\n" + tsc_r.stderr

    batch_e3 = _run_remotion_stills_batch(
        r_proj,
        env,
        [
            {"key": "full", "compId": "MedoReel", "frame": 3, "outPath": str(r_proj / "r_auto_full.png")},
            {"key": "framed", "compId": "MedoReel", "frame": 30, "outPath": str(r_proj / "r_auto_framed.png")},
        ],
    )
    assert batch_e3["full"]["ok"], batch_e3["full"]["error"]
    assert batch_e3["framed"]["ok"], batch_e3["framed"]["error"]

    assert hashlib.sha256((r_proj / "src" / "RemotionRoot.tsx").read_bytes()).hexdigest() == r_root_before
    assert hashlib.sha256((r_proj / "src" / "Root.tsx").read_bytes()).hexdigest() == r_entry_before

    r_im_full = np.asarray(Image.open(r_proj / "r_auto_full.png").convert("RGB"))
    r_im_framed = np.asarray(Image.open(r_proj / "r_auto_framed.png").convert("RGB"))
    # Frame 3 (t=0.10s, fullscreen): corner (10, 10) is MotionReel's light paper gradient (>230)
    assert int(r_im_full[10, 10].min()) > 230
    # Frame 30 (t=1.00s, framed r=90): exterior (20, 700) & rounded-corner luna (62, 230) -> exact UNDER #030303 (3,3,3)!
    assert tuple(r_im_framed[700, 20]) == (3, 3, 3)
    assert tuple(r_im_framed[230, 62]) == (3, 3, 3)
    # Interior (540, 300) has bright MotionReel content, and OVER progress bar + header are unclipped!
    assert int(r_im_framed[300, 540].min()) > 200
    assert tuple(r_im_framed[66, 150]) == (203, 39, 27)
    assert int(r_im_framed[115:160, 260:820].max()) > 200


def test_e4_autowrap_false_prevents_double_wrapping_and_preserves_manual_stage_p_k_r(
    tmp_path: Path, _remotion_runtime
):
    """Explicitly verify `autoWrap: false` across Engines P, K, and R:
    1) Default runtime entrypoints do NOT auto-wrap when `plan/stage.json` sets `enabled: true, autoWrap: false`.
    2) Manual Fixed Stage invocation works cleanly with ZERO double-wrapping (verified geometrically via
       a wider manual window `x=80..1000` vs `plan/stage.json`'s narrower `x=220..860` window).
    """
    modules_dir, env = _remotion_runtime
    td_doc = _sample_direction()
    beats_doc = {
        "duration": 1.0,
        "fps": 30,
        "frames": 30,
        "bounds": [0.0, 1.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.0, "dur": 1.0, "frames": 30, "theme": "light"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "manual-title", "scene": 1, "role": "title", "text": "تحكم يدوي بدون تغليف مزدوج", "start": 0.0, "end": 1.0}
        ],
    }
    # Narrow box in plan/stage.json (x=220..860) with enabled=true, autoWrap=false
    plan_stage_no_autowrap = {
        "version": 1,
        "enabled": True,
        "autoWrap": False,
        "id": "plan-narrow-no-autowrap",
        "clock": "vo",
        "mode": "framed",
        "theme": "dark",
        "defaultFramedBox": {"x": 220, "y": 360, "w": 640, "h": 900, "r": 40},
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
    }
    # Wider box used by manual Fixed Stage invocation (x=80..1000)
    manual_wider_stage = {
        "version": 1,
        "enabled": True,
        "id": "manual-wider-stage",
        "clock": "vo",
        "mode": "framed",
        "theme": "dark",
        "defaultFramedBox": {"x": 80, "y": 240, "w": 920, "h": 1060, "r": 40},
        "under": {"surfaceRole": "ink_shadow", "background": None, "frame": {"enabled": False}},
        "over": {"progressBar": {"enabled": False}, "header": {"enabled": False}, "captions": {"enabled": False}},
    }

    # --- 1. Engine P ---
    p_proj = tmp_path / "autowrap_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (p_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (p_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (p_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (p_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")

    assert stage.load_project_stage(p_proj) is None
    manual_bundle = stage.load_project_stage(p_proj, include_manual=True)
    assert manual_bundle is not None
    assert manual_bundle["spec"]["autoWrap"] is False
    assert manual_bundle["spec"]["defaultFramedBox"]["x"] == 220.0

    # 1a. Unedited scenes.py does NOT auto-wrap when autoWrap=False
    p_unwrapped_png = p_proj / "p_unwrapped.png"
    p_res1 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; from PIL import Image; import scenes; "
            f"Image.fromarray(scenes.render_frame(0.5)).save({str(p_unwrapped_png)!r})",
        ],
        cwd=p_proj,
        env={**env, "REEL_DIR": str(p_proj)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p_res1.returncode == 0, p_res1.stdout + "\n" + p_res1.stderr
    p_im_unwrapped = np.asarray(Image.open(p_unwrapped_png).convert("RGB"))
    assert int(p_im_unwrapped[10, 10].min()) > 200  # light scene1 corner, NOT #030303

    # 1b. Manual Fixed Stage wrapper around scenes.render_frame(t) applies wider box once (no double-wrap!)
    p_manual_png = p_proj / "p_manual.png"
    p_res2 = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json; from PIL import Image; import scenes, stage; "
            f"ms = json.loads({json.dumps(manual_wider_stage)!r}); "
            "fr = stage.render_fixed_stage(ms, 0.5, lambda ts, _st: scenes.render_frame(ts)); "
            f"Image.fromarray(fr).save({str(p_manual_png)!r})",
        ],
        cwd=p_proj,
        env={**env, "REEL_DIR": str(p_proj)},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert p_res2.returncode == 0, p_res2.stdout + "\n" + p_res2.stderr
    p_im_manual = np.asarray(Image.open(p_manual_png).convert("RGB"))
    assert tuple(p_im_manual[700, 40]) == (3, 3, 3)  # Outside manual box (x=40 < 80) -> #030303
    assert int(p_im_manual[700, 140].max()) > 180  # Inside manual box (80 < 140 < 220), NOT clipped to #030303!

    # --- 2. Engine K ---
    k_proj = tmp_path / "autowrap_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (k_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (k_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")
    (k_proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 1.0 }];\n"
        "export const DURATION = 1.0;\n",
        encoding="utf-8",
    )

    # 2a. Scene WITHOUT manualFixedStage does NOT get auto-wrapped when autoWrap=false
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        """import { PALETTE } from '../lib/brand.js';
export const supportsReducedMotion = true;
export async function draw(ctx, _lt, { W, H, stageSpec }) {
  if (!stageSpec || stageSpec.defaultFramedBox.x !== 220) {
    throw new Error('Expected loaded stageSpec with x=220 to be passed to manual scene');
  }
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, W, H);
}
""",
        encoding="utf-8",
    )
    k_unwrap_out = k_proj / "cache" / "k_unwrapped"
    k_res1 = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_unwrap_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res1.returncode == 0, k_res1.stdout + "\n" + k_res1.stderr
    k_im_unwrap = np.asarray(Image.open(k_unwrap_out / "00003.jpg").convert("RGB"))
    assert int(k_im_unwrap[10, 10].min()) > 220

    # 2b. Manual Fixed Stage inside s1.js (STILL without `manualFixedStage = true`!) works with zero double-wrapping
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        f"""import {{ renderFixedStage }} from '../lib/stage-canvas.js';
import {{ drawDirectedText, useDirectedFonts }} from '../lib/captions.js';
import {{ PALETTE }} from '../lib/brand.js';

export const supportsReducedMotion = true;
const MANUAL_SPEC = {json.dumps(manual_wider_stage)};

export async function init() {{
  const r = await fetch('/plan/text-direction.json');
  await useDirectedFonts(await r.json(), 1);
}}

export async function draw(ctx, localT, {{ W, H, t, direction, copyById, motionMode }}) {{
  await renderFixedStage(ctx, MANUAL_SPEC, t, {{
    duration: 1.0,
    direction,
    copyById,
    motionMode,
    drawContent: (c) => {{
      c.fillStyle = PALETTE.paper;
      c.fillRect(0, 0, W, H);
      drawDirectedText(c, copyById['manual-title'], {{
        direction, scene: 1, role: 'title', elementId: 'manual-title',
        time: localT, start: 0, end: 1.0, x: 540, y: 740, size: 48,
        color: PALETTE.ink, theme: 'light', shadow: 'transparent',
      }});
    }},
  }});
}}
""",
        encoding="utf-8",
    )
    k_audit_out = k_proj / "cache" / "k_manual_audit"
    k_audit = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.4", "--fps", "30", "--audit", "--replay", "--out", str(k_audit_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_audit.returncode == 0, k_audit.stdout + "\n" + k_audit.stderr

    k_manual_out = k_proj / "cache" / "k_manual_frames"
    k_res2 = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_manual_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_res2.returncode == 0, k_res2.stdout + "\n" + k_res2.stderr
    k_im_manual = np.asarray(Image.open(k_manual_out / "00003.jpg").convert("RGB"))
    assert int(k_im_manual[700, 40].max()) <= 12  # Outside manual box -> #030303
    assert int(k_im_manual[700, 140].min()) > 220  # Inside manual box (x=140), NOT clipped by plan/stage.json (x=220..860)!

    # --- 3. Engine R ---
    r_proj = tmp_path / "autowrap_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "autowrap-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (r_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (r_proj / "plan" / "stage.json").write_text(json.dumps(plan_stage_no_autowrap), encoding="utf-8")

    # Add a second composition `ManualStageReel` in Root.tsx that wraps `<MotionReel />` manually in `<FixedStage>`
    (r_proj / "src" / "Root.tsx").write_text(
        f"""import React from 'react';
import {{Composition, useCurrentFrame, useVideoConfig}} from 'remotion';
import {{BRAND}} from './brand';
import {{DURATION_IN_FRAMES, DURATION_SECONDS, IS_PREVIEW_TIMELINE}} from './data';
import {{MotionReel, STAGE_PLAN}} from './RemotionRoot';
import {{FixedStage}} from './lib/FixedStage';

const MANUAL_SPEC = {json.dumps(manual_wider_stage)};

const ManualWrappedReel: React.FC = () => {{
  const frame = useCurrentFrame();
  const {{fps}} = useVideoConfig();
  if (!STAGE_PLAN || STAGE_PLAN.defaultFramedBox?.x !== 220) {{
    throw new Error('Expected STAGE_PLAN with x=220 to remain accessible');
  }}
  return (
    <FixedStage spec={{MANUAL_SPEC}} time={{frame / fps}} duration={{DURATION_SECONDS}}>
      <MotionReel />
    </FixedStage>
  );
}};

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id="MedoReel"
      component={{MotionReel}}
      durationInFrames={{DURATION_IN_FRAMES}}
      fps={{BRAND.fps}}
      width={{BRAND.width}}
      height={{BRAND.height}}
      defaultProps={{{{audioFile: null, previewOnly: IS_PREVIEW_TIMELINE, motionMode: 'normal'}}}}
    />
    <Composition
      id="ManualStageReel"
      component={{ManualWrappedReel}}
      durationInFrames={{DURATION_IN_FRAMES}}
      fps={{BRAND.fps}}
      width={{BRAND.width}}
      height={{BRAND.height}}
    />
  </>
);
""",
        encoding="utf-8",
    )

    tsc_r = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_r.returncode == 0, tsc_r.stdout + "\n" + tsc_r.stderr

    batch_e4 = _run_remotion_stills_batch(
        r_proj,
        env,
        [
            {"key": "unwrap", "compId": "MedoReel", "frame": 10, "outPath": str(r_proj / "r_unwrapped.png")},
            {"key": "manual", "compId": "ManualStageReel", "frame": 10, "outPath": str(r_proj / "r_manual.png")},
        ],
    )
    assert batch_e4["unwrap"]["ok"], batch_e4["unwrap"]["error"]
    assert batch_e4["manual"]["ok"], batch_e4["manual"]["error"]

    r_im_unwrap = np.asarray(Image.open(r_proj / "r_unwrapped.png").convert("RGB"))
    r_im_manual = np.asarray(Image.open(r_proj / "r_manual.png").convert("RGB"))
    assert int(r_im_unwrap[10, 10].min()) > 230  # Default MotionReel NOT wrapped when autoWrap=false
    assert tuple(r_im_manual[700, 40]) == (3, 3, 3)  # Manual FixedStage IS active outside x=80..1000
    assert int(r_im_manual[700, 140].max()) > 180  # Inside manual box (x=140), NOT double-wrapped to #030303!


def test_e5_legacy_projects_without_stage_json_and_enabled_false_equivalence(
    tmp_path: Path, _remotion_runtime
):
    """Verify two critical backward-compatibility guarantees across P, K, R, and reel_lint.py:
    1) Legacy projects that do NOT have `plan/stage.json` at all work out-of-the-box with zero migration
       (including Engine R `tsc --noEmit` and `@remotion/bundler` compilation).
    2) New projects with `plan/stage.json` set to `enabled: false` produce 100% pixel-identical output
       to legacy projects without `plan/stage.json`.
    """
    modules_dir, env = _remotion_runtime
    td_doc = _sample_direction()
    beats_doc = {
        "duration": 1.0,
        "fps": 30,
        "frames": 30,
        "bounds": [0.0, 1.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.0, "dur": 1.0, "frames": 30, "theme": "light"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "leg-title", "scene": 1, "role": "title", "text": "توافق المشاريع القديمة والجديدة", "start": 0.0, "end": 1.0}
        ],
    }

    # --- 0. reel_lint.py on legacy fixture (no stage.json) vs enabled:false ---
    lint_legacy = tmp_path / "lint_legacy"
    shutil.copytree(ROOT / "tests" / "fixtures" / "reel" / "good", lint_legacy)
    assert not (lint_legacy / "plan" / "stage.json").exists()
    lint_res_leg = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(lint_legacy)],
        capture_output=True,
        text=True,
    )
    assert lint_res_leg.returncode == 0, lint_res_leg.stdout + "\n" + lint_res_leg.stderr

    # --- 1. Engine P: enabled:false == legacy missing plan/stage.json ---
    p_proj = tmp_path / "compat_p"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-p", "--engine", "p", "--out", str(p_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    # Even if mode is changed to 'framed', enabled: false must preserve 100% legacy behavior!
    p_stage_doc = json.loads((p_proj / "plan" / "stage.json").read_text(encoding="utf-8"))
    assert p_stage_doc["enabled"] is False
    p_stage_doc["mode"] = "framed"
    (p_proj / "plan" / "stage.json").write_text(json.dumps(p_stage_doc), encoding="utf-8")

    p_disabled_png = p_proj / "p_disabled.png"
    p_legacy_png = p_proj / "p_legacy.png"
    for target_png, remove_stage in ((p_disabled_png, False), (p_legacy_png, True)):
        if remove_stage:
            (p_proj / "plan" / "stage.json").unlink()
            assert not (p_proj / "plan" / "stage.json").exists()
        res = subprocess.run(
            [
                sys.executable,
                "-c",
                "from PIL import Image; import scenes; "
                f"Image.fromarray(scenes.render_frame(0.4)).save({str(target_png)!r})",
            ],
            cwd=p_proj,
            env={**env, "REEL_DIR": str(p_proj)},
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert res.returncode == 0, res.stdout + "\n" + res.stderr

    p_arr_disabled = np.asarray(Image.open(p_disabled_png).convert("RGB"))
    p_arr_legacy = np.asarray(Image.open(p_legacy_png).convert("RGB"))
    assert np.array_equal(p_arr_disabled, p_arr_legacy)
    assert int(p_arr_legacy[10, 10].min()) > 200

    # --- 2. Engine K: enabled:false == legacy missing plan/stage.json (+ --audit passes without 404) ---
    k_proj = tmp_path / "compat_k"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-k", "--engine", "k", "--out", str(k_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (k_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (k_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (k_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (k_proj / "src" / "data.js").write_text(
        "export const W = 1080, H = 1920, FPS = 30;\n"
        "export const scenes = [{ id: 's1', start: 0, end: 1.0 }];\n"
        "export const DURATION = 1.0;\n",
        encoding="utf-8",
    )
    (k_proj / "src" / "scenes" / "s1.js").write_text(
        """import { drawDirectedText, useDirectedFonts } from '../lib/captions.js';
import { PALETTE } from '../lib/brand.js';
export const supportsReducedMotion = true;
export async function init() {
  const r = await fetch('/plan/text-direction.json');
  await useDirectedFonts(await r.json(), 1);
}
export async function draw(ctx, localT, { W, H, direction }) {
  ctx.fillStyle = PALETTE.paper;
  ctx.fillRect(0, 0, W, H);
  drawDirectedText(ctx, 'توافق المشاريع القديمة والجديدة', {
    direction, scene: 1, role: 'title', elementId: 'leg-title',
    time: localT, start: 0, end: 1.0, x: 540, y: 740, size: 48,
    color: PALETTE.ink, theme: 'light', shadow: 'transparent',
  });
}
""",
        encoding="utf-8",
    )

    k_dis_out = k_proj / "cache" / "k_disabled"
    k_dis_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_dis_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_dis_res.returncode == 0, k_dis_res.stdout + "\n" + k_dis_res.stderr

    # Delete plan/stage.json to simulate legacy Engine K project
    (k_proj / "plan" / "stage.json").unlink()
    k_leg_audit = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--audit", "--out", str(k_proj / "cache" / "k_leg_audit")],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_leg_audit.returncode == 0, k_leg_audit.stdout + "\n" + k_leg_audit.stderr

    k_leg_out = k_proj / "cache" / "k_legacy"
    k_leg_res = subprocess.run(
        ["node", "src/render.js", "--from", "0", "--to", "0.2", "--fps", "30", "--jpg", "--out", str(k_leg_out)],
        cwd=k_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert k_leg_res.returncode == 0, k_leg_res.stdout + "\n" + k_leg_res.stderr
    assert (k_dis_out / "00003.jpg").read_bytes() == (k_leg_out / "00003.jpg").read_bytes()

    # --- 3. Engine R: enabled:false == legacy missing plan/stage.json (tsc + bundler + pixel equality!) ---
    r_proj = tmp_path / "compat_r"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "compat-r", "--engine", "r", "--out", str(r_proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (r_proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)
    (r_proj / "plan" / "beats.json").write_text(json.dumps(beats_doc), encoding="utf-8")
    (r_proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (r_proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")

    # 3a. With scaffolded plan/stage.json (enabled: false)
    tsc_dis = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_dis.returncode == 0, tsc_dis.stdout + "\n" + tsc_dis.stderr
    batch_dis = _run_remotion_stills_batch(
        r_proj,
        env,
        [{"key": "dis", "compId": "MedoReel", "frame": 10, "outPath": str(r_proj / "r_disabled.png")}],
    )
    assert batch_dis["dis"]["ok"], batch_dis["dis"]["error"]

    # 3b. Delete plan/stage.json completely -> legacy Engine R project without plan/stage.json!
    # Exercise `scripts/launch-remotion.mjs still` CLI end-to-end here too!
    (r_proj / "plan" / "stage.json").unlink()
    assert not (r_proj / "plan" / "stage.json").exists()

    tsc_leg = subprocess.run(
        ["node", "node_modules/typescript/bin/tsc", "--noEmit"],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert tsc_leg.returncode == 0, tsc_leg.stdout + "\n" + tsc_leg.stderr
    st_leg = subprocess.run(
        [
            "node", "scripts/launch-remotion.mjs", "still", "src/index.ts",
            "MedoReel", str(r_proj / "r_legacy.png"), "--frame=10", "--log=error",
        ],
        cwd=r_proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert st_leg.returncode == 0, st_leg.stdout + "\n" + st_leg.stderr

    r_arr_dis = np.asarray(Image.open(r_proj / "r_disabled.png").convert("RGB"))
    r_arr_leg = np.asarray(Image.open(r_proj / "r_legacy.png").convert("RGB"))
    assert np.array_equal(r_arr_dis, r_arr_leg)
    assert int(r_arr_leg[10, 10].min()) > 230


# ===========================================================================
# F. Determinism, Reverse-Seek & Engine P Chunked Rendering Tests
# ===========================================================================

def test_f1_engine_p_forward_reverse_random_seek_determinism():
    spec = _sample_stage_spec(radius=54.0)
    direction = _sample_direction()
    copy_by_id = {"hdr-topic-1": "موضوع الحلقة: استقرار الفريمات"}
    words = _sample_words()

    def _render_at(t: float) -> bytes:
        fr = stage.render_fixed_stage(
            spec,
            t,
            lambda ts, _st: (
                lambda buf: (
                    fill_rect(buf, 0, 0, 1080, 1920, INK, 1.0),
                    fill_rect(buf, 120, 400, 120 + int(600 * (ts / 3.0)), 480, RED, 1.0),
                    captions.draw_directed_text(
                        buf,
                        "اختبار الثبات الزمني",
                        direction=direction,
                        scene=1,
                        role="title",
                        element_id="det-title",
                        t=ts,
                        start=0.0,
                        end=3.0,
                        cx=540,
                        cy=760,
                        size=54,
                        color=WHITE,
                    ),
                    buf.astype(np.uint8),
                )[3]
            )(np.zeros((1920, 1080, 3), dtype=np.float32)),
            duration=3.0,
            direction=direction,
            copy_by_id=copy_by_id,
            words=words,
            caption_style="pop",
        )
        return hashlib.sha256(fr.tobytes()).hexdigest().encode("ascii")

    indices = list(range(0, 90, 3))
    fwd = {i: _render_at(i / 30.0) for i in indices}
    rev = {i: _render_at(i / 30.0) for i in reversed(indices)}

    shuffled = list(indices)
    random.Random(99).shuffle(shuffled)
    rnd = {i: _render_at(i / 30.0) for i in shuffled}

    assert fwd == rev
    assert fwd == rnd


def test_f2_engine_p_chunked_rendering_and_layout_audit_replay(tmp_path: Path):
    proj = tmp_path / "p_stage_proj"
    env = {
        **os.environ,
        "PATH": f"{ROOT / 'tools' / 'bin'}:{ROOT / '.venv' / 'bin'}:{os.environ.get('PATH', '')}",
    }
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "p-stage-test", "--engine", "p", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )

    beats = {
        "duration": 2.0,
        "fps": 30,
        "frames": 60,
        "bounds": [0.0, 2.0],
        "scenes": [{"index": 1, "start": 0.0, "end": 2.0, "dur": 2.0, "frames": 60, "theme": "dark"}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-p-1", "scene": 1, "role": "label", "text": "موضوع الحلقة: الرندر بالمقاطع", "start": 0.3, "end": 1.9},
            {"id": "title-p-1", "scene": 1, "role": "title", "text": "نفس النتيجة في كل مقطع", "start": 0.0, "end": 2.0},
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "id": "p-chunk-stage",
        "clock": "vo",
        "theme": "dark",
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.5},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.5, "end": 1.1, "ease": "cubicInOut"},
            {"mode": "framed", "start": 1.1, "end": 2.0},
        ],
        "over": {
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-p",
                        "scene": 1,
                        "copyId": "hdr-p-1",
                        "role": "label",
                        "start": 0.3,
                        "end": 1.9,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                    }
                ],
            }
        },
    }

    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    (proj / "scenes.py").write_text(
        """import json
import numpy as np
from pathlib import Path
import captions
import stage
from lib import W, H, INK, RED, WHITE, fill_rect
from render_policy import motion_mode
import os

SUPPORTS_REDUCED_MOTION = True
FPS = 30
B = [0.0, 2.0]
CHIP = None

_ROOT = Path(__file__).resolve().parent
_STAGE = stage.create_stage(json.loads((_ROOT / 'plan' / 'stage.json').read_text(encoding='utf-8')))
_TD = json.loads((_ROOT / 'plan' / 'text-direction.json').read_text(encoding='utf-8'))
_CP_DOC = json.loads((_ROOT / 'plan' / 'copy.json').read_text(encoding='utf-8'))
_COPY = {item['id']: item['text'] for item in _CP_DOC['copy']}
_WORDS = [
    {'text': 'نفس', 'start': 0.15, 'end': 0.85},
    {'text': 'النتيجة', 'start': 0.90, 'end': 1.80},
]

def _content(t, _st):
    fr = np.zeros((H, W, 3), dtype=np.float32)
    fill_rect(fr, 0, 0, W, H, INK, 1.0)
    fill_rect(fr, 140, 420, 940, 460, RED, 0.85)
    captions.draw_directed_text(
        fr, _COPY['title-p-1'],
        direction=_TD, scene=1, role='title', element_id='title-p-1',
        t=t, start=0.0, end=2.0, cx=540, cy=740, size=54, color=WHITE,
    )
    return fr.astype(np.uint8)

def render_frame(t):
    mode = motion_mode(os.environ.get('MEDO_MOTION_MODE', 'normal'))
    return stage.render_fixed_stage(
        _STAGE['spec'], t, _content,
        duration=2.0, direction=_TD, copy_by_id=_COPY,
        words=_WORDS, caption_style='pop', motion_mode=mode,
    )
""",
        encoding="utf-8",
    )

    # 1. Run layout_audit_p.py --replay --platform-ui across all 60 frames (including transition 0.5..1.1s!)
    audit_out = proj / "cache" / "audit-p"
    audit_p = subprocess.run(
        [sys.executable, str(TOOLS / "layout_audit_p.py"), "--project", str(proj), "--out", str(audit_out), "--replay", "--platform-ui"],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert audit_p.returncode == 0, audit_p.stdout + "\n" + audit_p.stderr
    rep = json.loads((audit_out / "report.json").read_text(encoding="utf-8"))
    assert rep["status"] == "pass"
    assert rep["replay"]["status"] == "pass"
    assert rep["replay"]["checkedFrames"] == 60
    assert rep["replay"]["failedFrames"] == 0

    # 2. Render 3 chunks out-of-order (40..60, then 0..20, then 20..40 splitting right through [0.5..1.1s]!)
    from chunk_utils import is_valid_chunk  # noqa: PLC0415

    for a, b in ((40, 60), (0, 20), (20, 40)):
        c_res = subprocess.run(
            [sys.executable, str(proj / "chunk.py"), str(a), str(b)],
            cwd=proj,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert c_res.returncode == 0, c_res.stdout + "\n" + c_res.stderr
        chunk_mp4 = proj / "out" / f"c_{a:05d}_{b:05d}.mp4"
        assert is_valid_chunk(chunk_mp4, b - a, 1080, 1920)


def test_f3_engine_r_persistent_browser_reverse_and_random_seek_determinism(
    tmp_path: Path, _remotion_runtime
):
    """Verify Engine R reverse-seeking and random-timestamp scrubbing inside ONE persistent
    Chromium browser instance (`openBrowser` + `renderStill`) across fullscreen, transition, and framed states."""
    modules_dir, env = _remotion_runtime
    proj = tmp_path / "r_reverse_seek"
    subprocess.run(
        [sys.executable, str(TOOLS / "new_project.py"), "r-reverse-seek", "--engine", "r", "--out", str(proj)],
        check=True,
        capture_output=True,
        text=True,
    )
    (proj / "node_modules").symlink_to(modules_dir, target_is_directory=True)

    beats = {
        "duration": 1.5,
        "fps": 30,
        "frames": 45,
        "bounds": [0.0, 1.5],
        "scenes": [{"index": 1, "start": 0.0, "end": 1.5, "dur": 1.5, "frames": 45}],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hdr-rev", "scene": 1, "role": "label", "text": "اختبار القفز العكسي في Remotion", "start": 0.25, "end": 1.45}
        ],
    }
    td_doc = _sample_direction()
    stage_spec = {
        "version": 1,
        "enabled": True,
        "id": "r-reverse-stage",
        "clock": "vo",
        "theme": "dark",
        "defaultFramedBox": {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 72},
        "under": {
            "surfaceRole": "ink_shadow",
            "background": {"id": "wash", "theme": "dark", "speed": 1.0},
            "frame": {"enabled": True, "strokeRole": "red", "strokeWidth": 3, "matRole": "ink_shadow", "matAlpha": 0.36},
        },
        "timeline": [
            {"mode": "fullscreen", "start": 0.0, "end": 0.2},
            {"mode": "transition", "from": "fullscreen", "to": "framed", "start": 0.2, "end": 0.7, "ease": "cubicInOut"},
            {"mode": "framed", "start": 0.7, "end": 1.5},
        ],
        "over": {
            "progressBar": {"enabled": True, "y": 64, "height": 6, "marginX": 60, "trackRole": "paper", "trackAlpha": 0.18, "fillRole": "red"},
            "header": {
                "enabled": True,
                "slots": [
                    {
                        "id": "hdr-rev-slot",
                        "scene": 1,
                        "copyId": "hdr-rev",
                        "role": "label",
                        "start": 0.25,
                        "end": 1.45,
                        "x": 540,
                        "y": 136,
                        "size": 38,
                        "maxWidth": 880,
                    }
                ],
            },
        },
    }
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    (proj / "plan" / "stage.json").write_text(json.dumps(stage_spec), encoding="utf-8")

    # Run a single persistent Chromium instance via @remotion/renderer and scrub forward, backward, and shuffled!
    scrub_mjs = proj / "scrub_verify.mjs"
    scrub_mjs.write_text(
        """import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const entryPoint = path.resolve('src/index.ts');
const browserExecutable = process.env.REMOTION_BROWSER_EXECUTABLE;
const serveUrl = await bundle({entryPoint, onProgress: () => {}});
const puppeteerInstance = await openBrowser('chrome', {
  browserExecutable,
  chromiumOptions: {disableWebSecurity: false},
});

try {
  const composition = await selectComposition({
    serveUrl,
    id: 'MedoReel',
    puppeteerInstance,
    inputProps: {motionMode: 'normal'},
  });

  async function renderOrder(frames) {
    const out = {};
    for (const f of frames) {
      const {buffer} = await renderStill({
        composition,
        serveUrl,
        frame: f,
        imageFormat: 'png',
        scale: 0.5,
        puppeteerInstance,
        inputProps: {motionMode: 'normal'},
      });
      out[String(f)] = crypto.createHash('sha256').update(buffer).digest('hex');
    }
    return out;
  }

  const forward = await renderOrder([3, 9, 15, 21, 30]);
  const reverse = await renderOrder([30, 21, 15, 9, 3]);
  const shuffled = await renderOrder([15, 3, 30, 9, 21]);
  console.log(JSON.stringify({forward, reverse, shuffled}));
} finally {
  process.on('unhandledRejection', () => {});
  await new Promise((r) => setTimeout(r, 150));
  try {
    await puppeteerInstance.close({silent: true});
  } catch {}
  try {
    fs.rmSync(serveUrl, {recursive: true, force: true});
  } catch {}
}
process.exit(0);
""",
        encoding="utf-8",
    )

    res = subprocess.run(
        ["node", str(scrub_mjs)],
        cwd=proj,
        env=env,
        capture_output=True,
        text=True,
        timeout=240,
    )
    assert res.returncode == 0, res.stdout + "\n" + res.stderr
    last_json = [ln for ln in res.stdout.strip().splitlines() if ln.strip().startswith("{")][-1]
    digests = json.loads(last_json)
    assert digests["forward"] == digests["reverse"], f"Engine R reverse-seek drift: {digests}"
    assert digests["forward"] == digests["shuffled"], f"Engine R random-seek drift: {digests}"
    # Distinct frames across fullscreen -> transition -> framed must not collapse to identical images
    assert len(set(digests["forward"].values())) == 5


# ===========================================================================
# G. Brand Lock, Dependency & Scope Guard Tests
# ===========================================================================

def test_g1_brand_palette_lock_and_zero_threejs_or_archive_drift():
    brand_doc = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed_hex = {"#" + v["hex"].lstrip("#").upper() for v in brand_doc["palette"].values()}
    allowed_hex.add(brand_doc["derived"]["ink_shadow"]["hex"].upper())
    assert brand_doc["brand"]["logo"] is None
    assert brand_doc["brand"]["on_screen_name"] is None

    stage_files = [
        ENGINE_P / "stage.py",
        ENGINE_K / "lib" / "stage.js",
        ENGINE_K / "lib" / "stage-canvas.js",
        ENGINE_R / "src" / "lib" / "stage.js",
        ENGINE_R / "src" / "lib" / "FixedStage.tsx",
    ]
    for path in stage_files:
        text = path.read_text(encoding="utf-8")
        assert not re.search(
            r"\bthree\.js\b|from\s+['\"]three['\"]|import\s+three\b|@remotion/three",
            text,
            re.IGNORECASE,
        ), f"{path.name} must not depend on Three.js in Phase 2A"
        for hx in re.findall(r"#[0-9A-Fa-f]{6}", text):
            assert hx.upper() in allowed_hex, f"{path.name} contains off-palette hex {hx}"

    # Run official brand_check.py against templates
    bc = subprocess.run(
        [sys.executable, str(SKILL / "scripts" / "brand_check.py"), "--project", str(SKILL / "templates")],
        capture_output=True,
        text=True,
    )
    assert bc.returncode == 0, bc.stdout + "\n" + bc.stderr
