"""Tests for native studio upgrades distilled from `majedphotos/video-ad-editor` (MIT)."""
from __future__ import annotations

import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import cv2
import numpy as np
import pytest
from conftest import ENGINE_P, ROOT, SKILL
from PIL import Image

sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ENGINE_P))


def _write_wav(path: Path, samples: np.ndarray, sr: int = 24000) -> None:
    pcm = np.clip(samples * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())


# ---------------------------------------------------------------------------
# 1. Fit doc & MIT attribution contract
# ---------------------------------------------------------------------------
def test_fit_doc_and_credits_attribution():
    fit = (ROOT / "docs" / "video-ad-editor-fit.md").read_text(encoding="utf-8")
    assert "majedphotos/video-ad-editor" in fit
    assert "a69492df61c2bd3d3e8c85af16266c70304ace0a" in fit
    assert "MIT License" in fit
    for rejected in ("facetrack.swift", "logo3d.html", "40_capcut.py"):
        assert rejected in fit, rejected

    credits_md = (ROOT / "assets" / "CREDITS.md").read_text(encoding="utf-8")
    assert "majedphotos/video-ad-editor" in credits_md
    assert "wheresryan22/anatomy" in credits_md
    assert "MIT" in credits_md


def test_k_and_r_shared_modules_are_byte_identical():
    for name in ("iso-kit.js", "shutter-blur.js", "tile3d.js", "three-tile3d.js"):
        k_bytes = (SKILL / "templates" / "render" / "lib" / name).read_bytes()
        r_bytes = (SKILL / "templates" / "remotion" / "src" / "lib" / name).read_bytes()
        assert k_bytes == r_bytes, f"{name} drifted between render/lib and remotion/src/lib"


def test_repo_only_svg_emblem_uses_locked_palette_only():
    import re  # noqa: PLC0415
    import xml.etree.ElementTree as ET  # noqa: PLC0415

    brand_doc = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed = {"#" + v["hex"].lstrip("#").upper() for v in brand_doc["palette"].values()}
    allowed.add("#" + "".join(f"{c:02X}" for c in brand_doc["derived"]["ink_shadow"]["rgb"]))

    for svg_name in ("studio-banner.svg", "studio-mark.svg"):
        svg_path = ROOT / "docs" / "assets" / svg_name
        assert svg_path.is_file(), svg_name
        raw = svg_path.read_text(encoding="utf-8")
        root_el = ET.fromstring(raw)
        assert root_el.tag.endswith("svg")
        for hx in re.findall(r"#[0-9A-Fa-f]{6}", raw):
            assert hx.upper() in allowed, f"{svg_name} contains off-palette hex {hx}"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/assets/studio-banner.svg" in readme
    # On-screen brand rule stays untouched: rendered reels still have no default logo
    assert brand_doc["brand"]["logo"] is None


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_tile3d_pose_parity_and_rendering():
    import tile3d  # noqa: PLC0415
    from lib import INK, checkmark  # noqa: PLC0415

    tile_js = (SKILL / "templates" / "render" / "lib" / "tile3d.js").as_uri()
    three_tile_js = (SKILL / "templates" / "render" / "lib" / "three-tile3d.js").as_uri()
    spec = {
        "x": 540,
        "y": 780,
        "size": 300,
        "role": "accent",
        "float": 1.0,
        "phase": 0.4,
        "shinePeriod": 2.4,
        "keys": [
            {"t": 0.0, "scale": 0.6, "ry": -55, "opacity": 0.0},
            {"t": 0.6, "scale": 1.0, "ry": 12, "opacity": 1.0, "ease": "out"},
            {"t": 2.0, "x": 600, "rx": -14, "ease": "inout"},
        ],
    }

    code = f"""
import {{ sampleTilePose, drawTile3d }} from {json.dumps(tile_js)};
import {{ buildThreeTileScene }} from {json.dumps(three_tile_js)};
const spec = {json.dumps(spec)};
const samples = [0.0, 0.3, 0.6, 1.25, 2.2].map(t => sampleTilePose(spec, t));
let symbolCalls = 0, fills = 0;
const ctx = new Proxy({{ globalAlpha: 1 }}, {{
  get(target, prop) {{
    if (prop in target) return target[prop];
    if (prop === 'fill') return () => {{ fills++; }};
    if (prop === 'createLinearGradient') return () => ({{ addColorStop() {{}} }});
    return () => {{}};
  }},
  set(target, prop, val) {{ target[prop] = val; return true; }},
}});
drawTile3d(ctx, 1.25, {{ ...spec, drawSymbol: () => {{ symbolCalls++; }} }});

// Verify Three r187 builder contract & resource disposal
let disposedCount = 0;
class FakeObj {{ constructor() {{ this.position = {{ set() {{}}, z: 0 }}; this.rotation = {{ set() {{}} }}; this.scale = {{ setScalar() {{}} }}; }} add() {{}} lookAt() {{}} dispose() {{ disposedCount++; }} center() {{}} }}
const FakeTHREE = {{
  Scene: FakeObj,
  Group: FakeObj,
  PerspectiveCamera: FakeObj,
  DirectionalLight: FakeObj,
  AmbientLight: FakeObj,
  Color: FakeObj,
  Shape: class {{ moveTo() {{}} lineTo() {{}} quadraticCurveTo() {{}} }},
  ExtrudeGeometry: FakeObj,
  PlaneGeometry: FakeObj,
  MeshStandardMaterial: FakeObj,
  MeshBasicMaterial: FakeObj,
  CanvasTexture: FakeObj,
  Mesh: FakeObj,
  AdditiveBlending: 2,
}};
const deferred = [];
const rig = buildThreeTileScene({{
  THREE: FakeTHREE,
  tiles: [{{ ...spec, drawSymbol: () => {{ symbolCalls++; }} }}],
  resources: {{ defer: fn => deferred.push(fn) }},
  canvasFactory: () => ({{
    getContext: () => new Proxy({{}}, {{
      get(_, p) {{
        if (p === 'createLinearGradient') return () => ({{ addColorStop() {{}} }});
        return () => {{}};
      }},
      set() {{ return true; }},
    }}),
  }}),
}});
rig.update(1.25);
deferred.forEach(fn => fn());
console.log(JSON.stringify({{ samples, symbolCalls, fills, disposedCount }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
    js_out = json.loads(res.stdout)

    for idx, t in enumerate([0.0, 0.3, 0.6, 1.25, 2.2]):
        py_pose = tile3d.sample_tile_pose(spec, t)
        js_pose = js_out["samples"][idx]
        for key in ("x", "y", "z", "scale", "rx", "ry", "rz", "opacity", "shineCenter"):
            assert py_pose[key] == pytest.approx(js_pose[key], abs=1e-4), f"{key} @ {t}"

    assert js_out["symbolCalls"] == 2
    assert js_out["fills"] >= 10
    assert js_out["disposedCount"] >= 6

    # Engine P perspective-homography tile render with icon sprite + determinism check
    fr1 = np.full((1920, 1080, 3), INK, dtype=np.float32)
    fr2 = np.full((1920, 1080, 3), INK, dtype=np.float32)
    spr = checkmark(140)
    tile3d.draw_tile3d(fr1, 1.25, spec, icon_sprite=spr)
    tile3d.draw_tile3d(fr2, 1.25, spec, icon_sprite=spr)
    assert np.array_equal(fr1, fr2)
    assert float(fr1.std()) > 6.0


# ---------------------------------------------------------------------------
# 2. Arabic kashida & mixed RTL/LTR phrase ordering (P + K parity)
# ---------------------------------------------------------------------------
def test_arabic_shape_multiword_ltr_run_and_kashida(cairo_bold):
    import arabic_shape as A  # noqa: PLC0415

    runs = A._runs("جرّب Claude Code النهاردة", True)
    run_texts = [t for t, _ in runs]
    assert "Claude Code" in run_texts, f"Expected intact LTR phrase, got {run_texts}"

    ordered = A.visual_word_order(["جرّب", "Claude", "Code", "2.0", "النهاردة"])
    # Stepping from right to left: "جرّب" (rightmost), then "2.0", "Code", "Claude" (so L->R reads Claude Code 2.0), then "النهاردة"
    assert [w["text"] for w in ordered] == ["جرّب", "2.0", "Code", "Claude", "النهاردة"]
    assert [w["logical_index"] for w in ordered] == [0, 3, 2, 1, 4]

    # Kashida rules: never after right-only letters (ر د ا و), never splitting harakat, never breaking لا
    assert A.insert_kashida("تحرّك", 1) == "تحـرّك"
    assert "رّـ" not in A.insert_kashida("تحرّك", 4)
    assert A.insert_kashida("سلام", 1) == "سـلام"
    assert "لـا" not in A.insert_kashida("سلام", 5)
    assert A.kashida_slots("دار") == []
    assert A.insert_kashida("دار", 3) == "دار"

    stretched = A.stretch_kashida(cairo_bold, "تصميم", 64, 340.0)
    assert stretched["tatweels"] >= 1
    assert stretched["width"] > stretched["natural_width"]
    assert 1.0 <= stretched["scale_x"] <= 1.06

    assert A.fix_ruqaa_taa_marbuta("حياة") == "حيا\u200dة"
    assert A.fix_ruqaa_taa_marbuta("مدرسة") == "مدرسة"


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_arabic_helpers_match_python():
    import arabic_shape as A  # noqa: PLC0415

    arabic_js = (SKILL / "templates" / "render" / "lib" / "arabic.js").as_uri()
    code = f"""
import {{ visualWordOrder, layoutWords, insertKashida, kashidaSlots, fixRuqaaTaaMarbuta }} from {json.dumps(arabic_js)};
const ctx = {{
  font: '800 60px "Cairo", sans-serif',
  textAlign: 'center',
  measureText: s => ({{ width: [...String(s)].length * 24 }}),
}};
const laid = layoutWords(ctx, 'جرّب Claude Code النهاردة', {{ x: 540, y: 500, maxWidth: 960 }});
const claude = laid.find(w => w.text === 'Claude');
const codeW = laid.find(w => w.text === 'Code');
console.log(JSON.stringify({{
  claudeLeftOfCode: claude.x < codeW.x,
  claudeLogical: claude.logicalIndex,
  codeLogical: codeW.logicalIndex,
  taharrak: insertKashida('تحرّك', 1),
  salam: insertKashida('سلام', 2),
  darSlots: kashidaSlots('دار').length,
  ruqaa: fixRuqaaTaaMarbuta('حياة'),
  madrasa: fixRuqaaTaaMarbuta('مدرسة'),
}}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["claudeLeftOfCode"] is True
    assert out["claudeLogical"] == 1 and out["codeLogical"] == 2
    assert out["taharrak"] == A.insert_kashida("تحرّك", 1) == "تحـرّك"
    assert out["salam"] == A.insert_kashida("سلام", 2)
    assert out["darSlots"] == 0
    assert out["ruqaa"] == "حيا\u200dة"
    assert out["madrasa"] == "مدرسة"


# ---------------------------------------------------------------------------
# 3. Phrase-chunk captions, glue-word cohesion, hideRanges & slot ticker
# ---------------------------------------------------------------------------
def test_phrase_caption_chunks_and_engine_p_rendering():
    import captions as C  # noqa: PLC0415
    import layout_p  # noqa: PLC0415
    from lib import INK, draw_kashida  # noqa: PLC0415

    words = [
        {"text": "السر", "start": 0.20, "end": 0.50},
        {"text": "في", "start": 0.52, "end": 0.68},      # glue preposition at word #2!
        {"text": "اختيار", "start": 0.70, "end": 1.05},
        {"text": "الرام", "start": 1.08, "end": 1.45},
        {"text": "الصح", "start": 2.10, "end": 2.55},    # pause > 0.45s splits here
    ]
    chunks = C.group_caption_chunks(words, max_words=2, max_gap=0.45)
    # "في" must NOT be orphaned at the end of chunk 0: chunk 0 carries "السر في اختيار"
    assert chunks[0]["text"] == "السر في اختيار"
    assert chunks[1]["text"] == "الرام"
    assert chunks[2]["text"] == "الصح"

    fr = np.full((1920, 1080, 3), INK, dtype=np.float32)
    # Suppressed during hero kinetic window [0.0, 0.6]
    assert C.draw_phrase_caption(fr, 0.35, chunks, style="pop", hide_ranges=[(0.0, 0.6)]) is None

    layout_p.begin_frame()
    try:
        drawn = C.draw_phrase_caption(fr, 0.80, chunks, style="pop", still=True)
        slot_cur = C.draw_text_slot(
            fr, 0.80,
            [{"start": 0.0, "text": "أسرع"}, {"start": 0.70, "text": "أهدى"}],
            cx=540, cy=620, size=70, box_id="hero-slot",
        )
        k_res = draw_kashida(fr, "تصميم", 540, 420, 72, 360, progress=0.8, box_id="hero-kashida")
    finally:
        boxes = layout_p.end_frame()

    assert drawn is not None and drawn["index"] == 0
    assert slot_cur is not None and slot_cur["text"] == "أهدى"
    assert k_res["tatweels"] >= 1
    ids = {b["id"] for b in boxes}
    assert "hero-slot" in ids and "hero-kashida" in ids
    assert any(b["zone"] == "caption" for b in boxes)
    assert layout_p.audit_layout(boxes) == []


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_js_phrase_captions_and_slot_ticker():
    captions_js = (SKILL / "templates" / "render" / "lib" / "captions.js").as_uri()
    code = f"""
import {{ groupCaptionChunks, drawPhraseCaption, drawTextSlot }} from {json.dumps(captions_js)};
const words = [
  {{ text: 'السر', start: 0.2, end: 0.5 }},
  {{ text: 'في', start: 0.52, end: 0.68 }},
  {{ text: 'VS', start: 0.70, end: 0.88 }},
  {{ text: 'Code', start: 0.90, end: 1.20 }},
];
const chunks = groupCaptionChunks(words, {{ maxWords: 2 }});
const drawn = [];
const ctx = new Proxy({{}}, {{
  get(_, prop) {{
    if (prop === 'measureText') return s => ({{ width: String(s).length * 22 }});
    if (prop === 'fillText') return (txt) => {{ drawn.push(txt); }};
    return () => {{}};
  }},
  set() {{ return true; }},
}});
const hidden = drawPhraseCaption(ctx, 0.8, chunks, {{ style: 'pop', hideRanges: [[0.5, 1.0]] }});
const shown = drawPhraseCaption(ctx, 0.8, chunks, {{ style: 'pop', still: true }});
const slot = drawTextSlot(ctx, 0.55, [{{ start: 0.0, text: 'قبل' }}, {{ start: 0.4, text: 'بعد' }}], {{ x: 540, y: 600 }});
console.log(JSON.stringify({{ firstChunk: chunks[0].text, hidden, shownText: shown?.text, drawnCount: drawn.length, slot: slot?.text }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
    out = json.loads(res.stdout)
    assert out["firstChunk"] == "السر في VS"
    assert out["hidden"] is None
    assert out["shownText"] == "السر في VS"
    assert out["drawnCount"] >= 3
    assert out["slot"] == "بعد"


# ---------------------------------------------------------------------------
# 4. Isometric cutaway kit & shutter motion blur (P + K/R parity)
# ---------------------------------------------------------------------------
@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_iso_kit_and_shutter_blur_parity():
    import iso_kit  # noqa: PLC0415
    from lib import INK, shutter_blur  # noqa: PLC0415

    iso_js = (SKILL / "templates" / "render" / "lib" / "iso-kit.js").as_uri()
    blur_js = (SKILL / "templates" / "render" / "lib" / "shutter-blur.js").as_uri()
    code = f"""
import {{ isoProject, createIsoScene }} from {json.dumps(iso_js)};
import {{ shutterTimes }} from {json.dumps(blur_js)};
const p = isoProject(80, -40, 30, {{ originX: 540, originY: 820, scale: 1.25 }});
let strokes = 0, fills = 0;
const ctx = new Proxy({{ globalAlpha: 1 }}, {{
  get(target, prop) {{
    if (prop in target) return target[prop];
    if (prop === 'stroke') return () => {{ strokes++; }};
    if (prop === 'fill') return () => {{ fills++; }};
    return () => {{}};
  }},
  set(target, prop, val) {{ target[prop] = val; return true; }},
}});
const sc = createIsoScene({{ scale: 1.2, theme: 'dark' }})
  .slab({{ x: -90, y: -60, z: 0, dx: 180, dy: 120, dz: 24, role: 'housing', layer: 'back' }})
  .ring({{ x: 0, y: 0, z: 24, rOuter: 52, rInner: 18, h: 14, blades: 5, spinDeg: 42, layer: 'mid' }})
  .coil({{ x: -60, y: 20, z: 30, length: 120, turns: 5, role: 'warm', layer: 'mid' }})
  .wire({{ points: [[-60, 0, 26], [40, 0, 26], [40, 50, 26]], flowP: 0.5, layer: 'front' }});
const opCount = sc.render(ctx);
const calm = shutterTimes(1.0, {{ fps: 30, shutter: 0.5, samples: 5, windows: [[2.0, 2.5]] }});
const active = shutterTimes(2.2, {{ fps: 30, shutter: 0.6, samples: 5, windows: [[2.0, 2.5]] }});
console.log(JSON.stringify({{ p, opCount, strokes, fills, calm, active }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=False)
    assert res.returncode == 0, res.stderr
    js_out = json.loads(res.stdout)

    px, py, pd = iso_kit.iso_project(80, -40, 30, origin_x=540, origin_y=820, scale=1.25)
    assert px == pytest.approx(js_out["p"]["x"], abs=1e-4)
    assert py == pytest.approx(js_out["p"]["y"], abs=1e-4)
    assert pd == pytest.approx(js_out["p"]["depth"], abs=1e-4)
    assert js_out["opCount"] == 6 and js_out["strokes"] > 5 and js_out["fills"] > 5
    assert len(js_out["calm"]) == 1 and len(js_out["active"]) == 5

    # Engine P cutaway render + deterministic shutter blur
    fr_a = np.full((1920, 1080, 3), INK, dtype=np.float32)
    scene_p = (
        iso_kit.IsoScene(scale=1.2, theme="dark")
        .slab(x=-90, y=-60, z=0, dx=180, dy=120, dz=24, role="housing", layer="back")
        .ring(x=0, y=0, z=24, r_outer=52, r_inner=18, h=14, blades=5, spin_deg=42, layer="mid")
        .coil(x=-60, y=20, z=30, length=120, turns=5, role="warm", layer="mid")
        .wire(points=[(-60, 0, 26), (40, 0, 26), (40, 50, 26)], flow_p=0.5, layer="front")
    )
    assert scene_p.render(fr_a) == 6
    assert float(fr_a.std()) > 4.0

    calls = []

    def _moving_dot(sub_t: float) -> np.ndarray:
        calls.append(sub_t)
        img = np.zeros((120, 240, 3), dtype=np.uint8)
        cx = int(40 + sub_t * 100)
        cv2.circle(img, (cx, 60), 14, (243, 242, 241), -1)
        return img

    calm_img = shutter_blur(_moving_dot, 0.5, samples=5, windows=[(1.0, 1.5)])
    assert len(calls) == 1 and calm_img.dtype.name == "uint8"
    calls.clear()
    blur_img = shutter_blur(_moving_dot, 1.2, fps=30.0, shutter=0.6, samples=5, windows=[(1.0, 1.5)])
    assert len(calls) == 5 and blur_img.dtype.name == "uint8"


# ---------------------------------------------------------------------------
# 5. Phone preview QA sheet & L04 right-rail platform UI check
# ---------------------------------------------------------------------------
def test_phone_preview_and_l04_platform_ui(tmp_path: Path):
    import layout_p  # noqa: PLC0415
    import phone_preview  # noqa: PLC0415

    # Clean cover frame (detail inside safe content zone only)
    clean = np.full((1920, 1080, 3), 10, dtype=np.uint8)
    for row in range(320, 820, 36):
        cv2.rectangle(clean, (160, row), (860, row + 18), (243, 242, 241), -1)
    clean_png = tmp_path / "clean_cover.png"
    Image.fromarray(clean, "RGB").save(clean_png)

    out_sheet = tmp_path / "sheet_clean.png"
    rep_json = tmp_path / "sheet_clean.json"
    res = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "phone_preview.py"), str(clean_png), "--out", str(out_sheet), "--report", str(rep_json), "--json"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert res.returncode == 0, res.stderr
    payload = json.loads(res.stdout)
    assert payload["status"] == "pass"
    assert payload["sheet_size"] == [1360, 920]
    assert out_sheet.is_file() and rep_json.is_file()

    # Intruding right-rail frame (sharp text-like bars inside x:940..1080, y:1100..1500)
    cluttered = clean.copy()
    for row in range(1140, 1460, 22):
        cv2.rectangle(cluttered, (955, row), (1065, row + 10), (217, 127, 104), -1)
    bad_png = tmp_path / "bad_cover.png"
    Image.fromarray(cluttered, "RGB").save(bad_png)
    bad_res = phone_preview.generate_phone_preview(bad_png, out_path=tmp_path / "sheet_bad.png")
    assert bad_res["status"] == "warn"
    assert any(w["code"] == "P01" for w in bad_res["warnings"])

    # Symlink input refused
    sym = tmp_path / "sym.png"
    sym.symlink_to(clean_png)
    sym_run = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "phone_preview.py"), str(sym), "--out", str(tmp_path / "out_sym.png")],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert sym_run.returncode != 0

    # Opt-in L04 in layout_p
    right_box = [{"id": "rtl-line", "kind": "text", "zone": "content", "x": 760.0, "y": 1180.0, "w": 240.0, "h": 60.0}]
    assert layout_p.audit_layout(right_box, check_platform_ui=False) == []
    issues_l04 = layout_p.audit_layout(right_box, check_platform_ui=True)
    assert [i["code"] for i in issues_l04] == ["L04"]


# ---------------------------------------------------------------------------
# 6. ASR check (hallucinations, stutter loops, bad bounds & voiced speech gaps)
# ---------------------------------------------------------------------------
def test_asr_check_hallucination_stutter_and_voiced_gap(tmp_path: Path):
    import asr_check  # noqa: PLC0415

    sr = 24000
    t = np.arange(int(sr * 4.0), dtype=np.float32) / sr
    # Quiet noise floor everywhere, PLUS active speech energy from 2.2s..3.3s (1.1s voiced!)
    audio = np.random.default_rng(7).normal(0.0, 0.001, size=len(t)).astype(np.float32)
    speech_idx = (t >= 0.2) & (t <= 1.2)
    gap_speech_idx = (t >= 2.2) & (t <= 3.3)
    audio[speech_idx] += 0.22 * np.sin(2.0 * math.pi * 220.0 * t[speech_idx])
    audio[gap_speech_idx] += 0.24 * np.sin(2.0 * math.pi * 260.0 * t[gap_speech_idx])
    vo_wav = tmp_path / "vo24.wav"
    _write_wav(vo_wav, audio, sr=sr)

    # Clean timings covering both speech regions -> PASS
    good_json = tmp_path / "good-timings.json"
    good_json.write_text(
        json.dumps({
            "words": [
                {"text": "اختار", "start": 0.20, "end": 0.65},
                {"text": "الرام", "start": 0.68, "end": 1.22},
                {"text": "بدقة", "start": 2.18, "end": 3.32},
            ]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    rep_good = asr_check.audit_asr(good_json, vo_path=vo_wav)
    assert rep_good["status"] == "pass", rep_good

    # Missing second phrase -> A04 untranscribed voiced gap warning (fails with --strict)
    gap_json = tmp_path / "gap-timings.json"
    gap_json.write_text(
        json.dumps({"words": [{"text": "اختار", "start": 0.20, "end": 1.22}]}, ensure_ascii=False),
        encoding="utf-8",
    )
    rep_gap = asr_check.audit_asr(gap_json, vo_path=vo_wav)
    assert rep_gap["status"] == "warn"
    assert any(w["code"] == "A04" for w in rep_gap["warnings"])

    strict_run = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "asr_check.py"), str(gap_json), "--vo", str(vo_wav), "--strict"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    assert strict_run.returncode == 1

    # Hallucination + 4x stutter -> A01 & A02 errors, unless script explicitly contains the phrase
    bad_json = tmp_path / "bad-timings.json"
    bad_json.write_text(
        json.dumps({
            "words": [
                {"text": "ده", "start": 0.10, "end": 0.20},
                {"text": "ده", "start": 0.21, "end": 0.30},
                {"text": "ده", "start": 0.31, "end": 0.40},
                {"text": "ده", "start": 0.41, "end": 0.50},
                {"text": "اشتركوا", "start": 0.55, "end": 0.75},
                {"text": "في", "start": 0.76, "end": 0.85},
                {"text": "القناة", "start": 0.86, "end": 1.15},
            ]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    script_md = tmp_path / "script.md"
    script_md.write_text("النهاردة هنتكلم عن الرامات\n", encoding="utf-8")
    rep_bad = asr_check.audit_asr(bad_json, script_path=script_md)
    codes = {e["code"] for e in rep_bad["errors"]}
    assert "A01" in codes and "A02" in codes

    # When the creator intentionally wrote "اشتركوا في القناة" in script.md, A01 does NOT fire
    script_with_cta = tmp_path / "script_cta.md"
    script_with_cta.write_text("اشتركوا في القناة دلوقتي\n", encoding="utf-8")
    cta_only_json = tmp_path / "cta.json"
    cta_only_json.write_text(
        json.dumps({
            "words": [
                {"text": "اشتركوا", "start": 0.1, "end": 0.4},
                {"text": "في", "start": 0.42, "end": 0.55},
                {"text": "القناة", "start": 0.56, "end": 0.9},
            ]
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    rep_cta = asr_check.audit_asr(cta_only_json, script_path=script_with_cta)
    assert rep_cta["status"] == "pass"
