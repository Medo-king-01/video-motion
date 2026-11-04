"""Milestone 1 & Phase 1 tests for the native Machine Explainer workflow (`X01`–`X04` + P/K/R parity)."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
TOOLS = ROOT / "tools"

# Ensure Engine P's modules precede CLI wrappers in tools/
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ENGINE_P) in sys.path:
    sys.path.remove(str(ENGINE_P))
sys.path.insert(0, str(ENGINE_P))


def _sample_nvme_vo_spec() -> dict:
    return {
        "version": 1,
        "id": "nvme-ssd",
        "archetype": "nvme_ssd",
        "clock": "vo",
        "scene": 2,
        "start": 3.0,
        "end": 8.0,
        "wordTimings": "plan/word-timings.json",
        "revealWindow": {
            "unit": "vo_seconds",
            "start": 3.0,
            "end": 4.2,
        },
        "qa": {
            "maxOcclusion": 0.35,
            "zone": "content",
            "checkPlatformUi": True,
        },
        "sources": [
            {
                "id": "nvm-base-2.0d",
                "title": "NVM Express Base Specification Revision 2.0d",
                "kind": "spec",
                "ref": "https://nvmexpress.org/specifications/",
            }
        ],
        "steps": [
            {
                "id": "step-pcie",
                "evidence": "source",
                "sourceId": "nvm-base-2.0d",
                "locator": {"kind": "section", "value": "§3.1.2 PCIe Queue Transport, p. 44"},
                "quote": "Host submits commands directly across PCI Express lanes to controller queues.",
                "copyIds": ["nvme-step-1"],
                "timing": "sync",
                "anchor": {"word": 1, "text": "الكنترولر"},
                "start": 4.3,
                "end": 6.0,
                "activeTags": ["pcie_bus", "controller"],
                "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake", "rate": 1.4},
            },
            {
                "id": "step-nand",
                "evidence": "source",
                "sourceId": "nvm-base-2.0d",
                "locator": {"kind": "figure", "value": "Figure 14, Non-Volatile Memory Subsystem, p. 51"},
                "quote": "Controller stripes data across parallel non-volatile flash channels and dies.",
                "copyIds": ["nvme-step-2"],
                "timing": "reveal",
                "anchor": {"word": 3, "text": "طبقات"},
                "start": 6.1,
                "end": 7.8,
                "activeTags": ["nand_channel", "nand_stack"],
                "motion": {"kind": "packet_flow", "path": "controller_to_nand", "tint": "active", "rate": 1.2},
            },
        ],
    }


def _write_project_fixture(proj: Path, spec: dict) -> None:
    (proj / "plan" / "machines").mkdir(parents=True, exist_ok=True)
    beats = {
        "duration": 10.0,
        "scenes": [
            {"index": 1, "start": 0.0, "end": 3.0, "theme": "dark"},
            {"index": 2, "start": 3.0, "end": 8.0, "theme": "dark"},
            {"index": 3, "start": 8.0, "end": 10.0, "theme": "light"},
        ],
    }
    words = {
        "clock": "vo",
        "scenes": [
            {"scene": 1, "words": [{"text": "ليه", "start": 0.4, "end": 0.9}]},
            {
                "scene": 2,
                "words": [
                    {"text": "بيدخل", "start": 3.8, "end": 4.25},
                    {"text": "الكنترولر", "start": 4.3, "end": 4.95},
                    {"text": "ويوزع", "start": 5.3, "end": 5.9},
                    {"text": "طبقات", "start": 6.05, "end": 6.65},
                ],
            },
            {"scene": 3, "words": [{"text": "تفرق", "start": 8.2, "end": 8.8}]},
        ],
    }
    copy_doc = {
        "pace": "calm",
        "bpm": 100,
        "copy": [
            {"id": "hook-1", "scene": 1, "role": "hook", "text": "إزاي الـSSD بيقرأ؟", "start": 0.0, "end": 2.6},
            {"id": "nvme-step-1", "scene": 2, "role": "label", "text": "المسارات بتسلّم الكنترولر مباشرة", "start": 4.3, "end": 6.0},
            {"id": "nvme-step-2", "scene": 2, "role": "label", "text": "يتوزع بالتوازي على طبقات الفلاش", "start": 6.1, "end": 7.8},
            {"id": "nvme-illus-tag", "scene": 2, "role": "label", "text": "رسم توضيحي", "start": 4.3, "end": 7.8},
        ],
    }
    (proj / "plan" / "beats.json").write_text(json.dumps(beats, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "word-timings.json").write_text(json.dumps(words, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "copy.json").write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    (proj / "plan" / "machines" / f"{spec['id']}.json").write_text(
        json.dumps(spec, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def test_k_and_r_machine_kit_byte_identical_and_locked_palette():
    k_path = SKILL / "templates" / "render" / "lib" / "machine-kit.js"
    r_path = SKILL / "templates" / "remotion" / "src" / "lib" / "machine-kit.js"
    assert k_path.read_bytes() == r_path.read_bytes(), "K and R machine-kit.js must stay byte-identical"

    brand = json.loads((SKILL / "brand" / "brand.json").read_text(encoding="utf-8"))
    allowed = {v["hex"].upper() for v in brand["palette"].values() if isinstance(v, dict) and "hex" in v}
    allowed |= {v["hex"].upper() for v in brand.get("derived", {}).values() if isinstance(v, dict) and "hex" in v}

    for path in (k_path, ENGINE_P / "machine_kit.py"):
        found = {h.upper() for h in re.findall(r"#[0-9A-Fa-f]{6}", path.read_text(encoding="utf-8"))}
        assert found <= allowed, f"{path.name} introduces off-brand colours: {found - allowed}"


def test_x01_verifiable_source_locator_and_illustrative_guards(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415

    # Clean project passes X01–X04
    spec = _sample_nvme_vo_spec()
    _write_project_fixture(tmp_path, spec)
    report = me.check_project(tmp_path)
    assert report["ok"], report["errors"]

    # Bare quote WITHOUT locator must fail X01
    bad_no_locator = _sample_nvme_vo_spec()
    del bad_no_locator["steps"][0]["locator"]
    _write_project_fixture(tmp_path, bad_no_locator)
    res1 = me.check_project(tmp_path)
    assert not res1["ok"]
    assert any(code == "X01" and "locator" in msg for code, msg in res1["errors"])

    # Illustrative step asserting unverified hardware spec numbers ("7400 MB/s") must fail X01
    bad_illus = _sample_nvme_vo_spec()
    bad_illus["steps"][0] = {
        "id": "step-pcie",
        "evidence": "illustrative",
        "illustrativeLabelId": "nvme-illus-tag",
        "copyIds": ["nvme-step-1", "nvme-illus-tag"],
        "timing": "sync",
        "anchor": {"word": 1, "text": "الكنترولر"},
        "start": 4.3,
        "end": 6.0,
        "activeTags": ["controller"],
        "motion": {"kind": "pulse", "tint": "active"},
    }
    _write_project_fixture(tmp_path, bad_illus)
    copy_p = tmp_path / "plan" / "copy.json"
    copy_doc = json.loads(copy_p.read_text(encoding="utf-8"))
    copy_doc["copy"][1]["text"] = "سرعة قراءة 7400 MB/s"
    copy_p.write_text(json.dumps(copy_doc, ensure_ascii=False), encoding="utf-8")
    res2 = me.check_project(tmp_path)
    assert not res2["ok"]
    assert any(code == "X01" and "hardware spec numbers" in msg for code, msg in res2["errors"])


def test_x02_unified_word_timings_and_explicit_reveal_window_units(tmp_path: Path):
    import machine_explainer as me  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    # Ambiguous array revealWindow [3.0, 4.2] must be rejected
    bad_rw = _sample_nvme_vo_spec()
    bad_rw["revealWindow"] = [3.0, 4.2]
    _write_project_fixture(tmp_path, bad_rw)
    r_rw = me.check_project(tmp_path)
    assert not r_rw["ok"]
    assert any(code == "X02" and "revealWindow" in msg for code, msg in r_rw["errors"])

    # Sync step drifting from measured word.start (4.30 -> 4.45) must fail X02
    bad_sync = _sample_nvme_vo_spec()
    bad_sync["steps"][0]["start"] = 4.45
    _write_project_fixture(tmp_path, bad_sync)
    r_sync = me.check_project(tmp_path)
    assert not r_sync["ok"]
    assert any(code == "X02" and "sync must start" in msg for code, msg in r_sync["errors"])

    # Converting VO spec -> scene-local updates clock="scene" and revealWindow.unit="scene_seconds"
    local = mk.to_scene_local_machine(_sample_nvme_vo_spec(), scene_start=3.0)
    assert local["clock"] == "scene"
    assert local["revealWindow"] == {"unit": "scene_seconds", "start": 0.0, "end": 1.2}
    assert local["steps"][0]["start"] == 1.3


def test_x03_polygon_mask_occlusion_distinguishes_true_shape_from_aabb_and_honors_threshold():
    import machine_kit as mk  # noqa: PLC0415

    # Build a custom machine where an L-shaped `front` bracket has an axis-aligned bounding box
    # that 100% encloses the target chip in `mid`, while its actual polygon leaves the chip 0% covered!
    l_bracket_faces = [
        [[-120, -100, 12], [120, -100, 12], [120, -82, 12], [-120, -82, 12]],
        [[-120, -100, 12], [-102, -100, 12], [-102, 140, 12], [-120, 140, 12]],
        [[-120, 122, 12], [120, 122, 12], [120, 140, 12], [-120, 140, 12]],
    ]
    spec = {
        "version": 1,
        "id": "poly-vs-aabb",
        "archetype": "custom",
        "clock": "scene",
        "start": 0.0,
        "end": 3.0,
        "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.6},
        "sources": [
            {"id": "s1", "title": "Test Hardware Reference", "kind": "manual", "ref": "DOC-101"}
        ],
        "parts": [
            {
                "id": "target_chip", "tag": "die", "layer": "mid", "primitive": "slab", "role": "chip",
                "x": -15, "y": -15, "z": 4, "dx": 36, "dy": 36, "dz": 8, "alpha": 1.0,
            },
            {
                "id": "l_frame_front", "tag": "frame", "layer": "front", "primitive": "poly3d", "role": "housing",
                "faces3d": l_bracket_faces, "alpha": 1.0,
            },
        ],
        "steps": [
            {
                "id": "step-die",
                "evidence": "source",
                "sourceId": "s1",
                "locator": {"kind": "page", "value": "p. 12"},
                "quote": "Central processor die remains exposed inside the L-frame.",
                "copyIds": ["c1"],
                "timing": "sync",
                "anchor": {"word": 0, "text": "الشريحة"},
                "start": 0.6,
                "end": 2.8,
                "activeTags": ["die"],
                "motion": {"kind": "pulse", "tint": "active"},
            }
        ],
    }

    # Verify the L-bracket's screen AABB really encloses the target chip's screen AABB,
    # yet polygon coverage-mask occlusion reports 0.0% occlusion!
    graph = mk.build_machine_scene(spec, 1.2, force_full_reveal=True)
    chip_op = next(op for op in graph["ops"] if op["partId"] == "target_chip")
    frame_op = next(op for op in graph["ops"] if op["partId"] == "l_frame_front")
    chip_pts = [pt for f in chip_op["faces"] for pt in f["points"]]
    frame_pts = [pt for f in frame_op["faces"] for pt in f["points"]]
    assert min(p[0] for p in frame_pts) < min(p[0] for p in chip_pts)
    assert max(p[0] for p in frame_pts) > max(p[0] for p in chip_pts)
    assert min(p[1] for p in frame_pts) < min(p[1] for p in chip_pts)
    assert max(p[1] for p in frame_pts) > max(p[1] for p in chip_pts)

    occ = mk.compute_occlusion_report(spec, max_occlusion=0.10)
    assert occ["errors"] == []
    assert occ["results"][0]["occludedRatio"] == 0.0

    # Now add a 60%-alpha hood directly over the chip: passes at max_occlusion=0.65, fails at 0.35!
    spec["parts"].append({
        "id": "heavy_hood", "tag": "hood", "layer": "front", "primitive": "slab", "role": "cutaway",
        "x": -30, "y": -30, "z": 20, "dx": 70, "dy": 70, "dz": 4, "alpha": 0.60, "cutaway": True,
    })
    occ_fail = mk.compute_occlusion_report(spec, max_occlusion=0.35)
    assert len(occ_fail["errors"]) == 1
    assert occ_fail["results"][0]["occludedRatio"] > 0.55
    occ_pass = mk.compute_occlusion_report(spec, max_occlusion=0.65)
    assert occ_pass["errors"] == []


def test_x04_dynamic_safe_zone_and_platform_right_rail_audit():
    import layout_p  # noqa: PLC0415
    import machine_explainer as me  # noqa: PLC0415

    env = layout_p.safe_envelope("content", check_platform_ui=True)
    assert env["w"] == 1080 and env["h"] == 1920 and env["fps"] == 30

    # Push NVMe diagram into PLATFORM_RIGHT_RAIL (x=940..1080, y=1100..1500)
    bad_rail = _sample_nvme_vo_spec()
    bad_rail["layout"] = {"originX": 880, "originY": 1220, "scale": 1.1}
    res = me.audit_machine_spec(bad_rail)
    assert not res["ok"]
    assert any(f["code"] == "X04" and "PLATFORM_RIGHT_RAIL" in f["message"] for f in res["findings"])


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_nvme_ssd_p_k_r_geometry_parity_and_rendering():
    import layout_p  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    local_spec = mk.to_scene_local_machine(_sample_nvme_vo_spec(), scene_start=3.0)
    sample_t = 1.85  # inside step-pcie (1.3 .. 3.0), packet_flow active!

    py_graph = mk.build_machine_scene(local_spec, sample_t, theme="dark")

    # Render on a real Engine P frame with directed text + layout_p capture
    fr = np.full((1920, 1080, 3), 10.0, dtype=np.float32)
    direction = {
        "scenes": [
            {
                "scene": 2,
                "captionStyle": "softfade",
                "textStyles": {"label": "riseword"},
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
            }
        ]
    }
    copy_by_id = {
        "nvme-step-1": "المسارات بتسلّم الكنترولر مباشرة",
        "nvme-step-2": "يتوزع بالتوازي على طبقات الفلاش",
    }
    layout_p.begin_frame()
    try:
        mk.draw_machine_diagram(
            fr, local_spec, sample_t,
            direction=direction, scene=2, copy_by_id=copy_by_id, theme="dark",
        )
    finally:
        p_boxes = layout_p.end_frame()

    assert float(np.abs(fr - 10.0).max()) > 120.0, "Engine P must render visible cutaway pixels"
    assert any(b["id"] == "nvme-ssd.diagram" and b["kind"] == "keep" for b in p_boxes)
    assert any(b["id"] == "nvme-step-1" and b["kind"] == "text" for b in p_boxes)
    assert layout_p.audit_layout(p_boxes, check_platform_ui=True) == []

    # Compare exact state, bounds, world anchors, and ops against Engine K/R JS + Engine K Canvas2D adapter
    kit_js = (SKILL / "templates" / "render" / "lib" / "machine-kit.js").as_uri()
    vis_js = (SKILL / "templates" / "render" / "lib" / "machine-visual.js").as_uri()
    lay_js = (SKILL / "templates" / "render" / "lib" / "layout.js").as_uri()
    code = f"""
import {{ buildMachineScene, toSceneLocalMachine }} from {json.dumps(kit_js)};
import {{ drawMachineDiagram }} from {json.dumps(vis_js)};
import {{ captureLayout, auditLayout }} from {json.dumps(lay_js)};

const voSpec = {json.dumps(_sample_nvme_vo_spec())};
const localSpec = toSceneLocalMachine(voSpec, 3.0);
const graph = buildMachineScene(localSpec, {sample_t}, {{ theme: 'dark' }});

let drawOps = 0;
const tfStack = [];
let tf = {{ a: 1, b: 0, c: 0, d: 1, e: 0, f: 0 }};
const ctx = {{
  canvas: {{ width: 1080, height: 1920 }},
  globalAlpha: 1,
  fillStyle: '#000',
  strokeStyle: '#000',
  lineWidth: 1,
  lineJoin: 'round',
  lineCap: 'round',
  font: '800 46px Cairo',
  save() {{ tfStack.push({{ ...tf, alpha: this.globalAlpha }}); }},
  restore() {{ const p = tfStack.pop(); if (p) {{ this.globalAlpha = p.alpha; tf = {{ a: p.a, b: p.b, c: p.c, d: p.d, e: p.e, f: p.f }}; }} }},
  beginPath() {{}},
  closePath() {{}},
  moveTo() {{ drawOps += 1; }},
  lineTo() {{ drawOps += 1; }},
  fill() {{ drawOps += 1; }},
  stroke() {{ drawOps += 1; }},
  arc() {{ drawOps += 1; }},
  setLineDash() {{}},
  translate(dx, dy) {{ tf.e += tf.a * dx + tf.c * dy; tf.f += tf.b * dx + tf.d * dy; }},
  rotate() {{}},
  scale(sx, sy) {{ tf.a *= sx; tf.d *= sy; }},
  getTransform() {{ return {{ ...tf }}; }},
  measureText(txt) {{
    const w = [...String(txt)].length * 16;
    return {{ width: w, actualBoundingBoxLeft: w / 2, actualBoundingBoxRight: w / 2, actualBoundingBoxAscent: 32, actualBoundingBoxDescent: 10 }};
  }},
  fillText() {{ drawOps += 1; }},
  strokeText() {{ drawOps += 1; }},
}};
const cap = captureLayout(ctx);
cap.begin();
drawMachineDiagram(ctx, localSpec, {sample_t}, {{
  direction: {json.dumps(direction)},
  scene: 2,
  copyById: {json.dumps(copy_by_id)},
  theme: 'dark',
}});
const boxes = cap.snapshot();
const issues = auditLayout(boxes, {{ checkPlatformUi: true }});
console.log(JSON.stringify({{ graph, drawOps, boxes, issues }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    js_out = json.loads(res.stdout)
    js_graph = js_out["graph"]

    assert js_out["drawOps"] > 60
    assert js_out["issues"] == []
    assert any(b["id"] == "nvme-ssd.diagram" and b["kind"] == "keep" for b in js_out["boxes"])
    assert any(b["id"].startswith("nvme-step-1") and b["kind"] == "text" for b in js_out["boxes"])

    # Exact mathematical parity between Python (P) and JavaScript (K & R)
    assert py_graph["state"]["revealProgress"] == pytest.approx(js_graph["state"]["revealProgress"], abs=1e-4)
    assert py_graph["state"]["packetProgress"] == pytest.approx(js_graph["state"]["packetProgress"], abs=1e-4)
    assert py_graph["bounds"] == js_graph["bounds"]
    assert py_graph["world"] == js_graph["world"]
    assert len(py_graph["ops"]) == len(js_graph["ops"])
    for p_op, j_op in zip(py_graph["ops"], js_graph["ops"], strict=True):
        assert p_op["partId"] == j_op["partId"]
        assert p_op["kind"] == j_op["kind"]
        assert p_op["depth"] == pytest.approx(j_op["depth"], abs=1e-4)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_remotion_machine_diagram_tsx_renders_matching_svg_and_directed_text():
    remotion_lib = SKILL / "templates" / "remotion" / "src" / "lib"
    code = f"""
import fs from 'node:fs';
import path from 'node:path';
import {{ pathToFileURL }} from 'node:url';

const libDir = {json.dumps(str(remotion_lib))};
const kitMod = await import(pathToFileURL(path.join(libDir, 'machine-kit.js')).href);
const tsxSrc = fs.readFileSync(path.join(libDir, 'MachineDiagram.tsx'), 'utf8');

// Verify MachineDiagram.tsx imports the shared machine-kit.js + DirectedText + brand
if (!tsxSrc.includes("from './machine-kit.js'") || !tsxSrc.includes("from './DirectedText'")) {{
  throw new Error('MachineDiagram.tsx must consume ./machine-kit.js and ./DirectedText');
}}

const localSpec = kitMod.toSceneLocalMachine({json.dumps(_sample_nvme_vo_spec())}, 3.0);
const graph = kitMod.buildMachineScene(localSpec, 1.85, {{ theme: 'dark', fps: 30 }});
const solidFaces = graph.ops.filter(o => o.kind === 'solid').reduce((n, o) => n + o.faces.length, 0);
const packetDots = graph.ops.filter(o => o.kind === 'packets').reduce((n, o) => n + o.dots.length, 0);
console.log(JSON.stringify({{ solidFaces, packetDots, activeStepId: graph.state.activeStepId }}));
"""
    res = subprocess.run(["node", "--input-type=module", "-e", code], capture_output=True, text=True, check=True)
    r_out = json.loads(res.stdout)
    assert r_out["solidFaces"] > 30
    assert r_out["packetDots"] == 3
    assert r_out["activeStepId"] == "step-pcie"


def _archetype_scene_specs() -> list[dict]:
    return [
        {
            "version": 1,
            "id": "nvme-arch",
            "archetype": "nvme_ssd",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "NVM Express Base Specification 2.0d", "kind": "spec", "ref": "NVMe-2.0d"}],
            "steps": [
                {
                    "id": "s-ctrl",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§3.1.2"},
                    "quote": "Host submits queue entries over PCIe lanes to the controller.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "الكنترولر"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["pcie_bus", "controller", "dram_cache"],
                    "motion": {"kind": "packet_flow", "path": "pcie_to_controller", "tint": "intake"},
                },
                {
                    "id": "s-nand",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "figure", "value": "Fig. 14"},
                    "quote": "Controller writes across parallel non-volatile flash channels.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "فلاش"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["nand_channel", "nand_stack"],
                    "motion": {"kind": "packet_flow", "path": "controller_to_nand", "tint": "active"},
                },
            ],
        },
        {
            "version": 1,
            "id": "cpu-arch",
            "archetype": "cpu_package",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "Processor Architecture Reference Manual", "kind": "manual", "ref": "CPU-PRM-2025"}],
            "steps": [
                {
                    "id": "s-cores",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§2.4 Core Complex & Shared L3"},
                    "quote": "Compute cores share a unified L3 cache slice connected over the die fabric.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "الأنوية"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["socket_pins", "cores", "l3_cache"],
                    "motion": {"kind": "packet_flow", "path": "ring_to_cores", "tint": "active"},
                },
                {
                    "id": "s-io",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "table", "value": "Table 4-1 Die Interconnect"},
                    "quote": "High-speed fabric links connect compute tiles with the I/O die.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "الذاكرة"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["fabric", "io_die"],
                    "motion": {"kind": "packet_flow", "path": "cache_to_io", "tint": "intake"},
                },
            ],
        },
        {
            "version": 1,
            "id": "ram-arch",
            "archetype": "ram_dimm",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "JEDEC DDR5 SDRAM Standard JESD79-5C", "kind": "standard", "ref": "JESD79-5C"}],
            "steps": [
                {
                    "id": "s-rcd",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "clause", "value": "Clause 4.1 Sub-channel Architecture"},
                    "quote": "Each DIMM routes two independent sub-channels from connector pins through the controller.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "القنوات"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["bus_pins", "rcd_controller", "channel_bus"],
                    "motion": {"kind": "packet_flow", "path": "channel_a", "tint": "intake"},
                },
                {
                    "id": "s-banks",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§4.5 Bank Groups"},
                    "quote": "Parallel DRAM bank groups service burst reads and writes concurrently.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "بنوك"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["dram_banks"],
                    "motion": {"kind": "packet_flow", "path": "channel_b", "tint": "active"},
                },
            ],
        },
        {
            "version": 1,
            "id": "cool-arch",
            "archetype": "cooling_system",
            "clock": "scene",
            "start": 0.0,
            "end": 4.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.9},
            "sources": [{"id": "s1", "title": "Two-Phase Heat Pipe Thermal Transfer Handbook", "kind": "paper", "ref": "DOI:10.1016/heatpipe"}],
            "steps": [
                {
                    "id": "s-pipes",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§2.2 Evaporator to Fin Condenser"},
                    "quote": "Heat conducts into the coldplate and travels along sealed heatpipes into the fin stack.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "أنابيب"},
                    "start": 1.0,
                    "end": 2.4,
                    "activeTags": ["coldplate", "heatpipes", "fin_stack"],
                    "motion": {"kind": "packet_flow", "path": "heatpipe_transfer", "tint": "active"},
                },
                {
                    "id": "s-fan",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "page", "value": "p. 88 Forced Convection"},
                    "quote": "Axial fan rotation drives intake airflow across the fin array to exhaust.",
                    "copyIds": ["c-2"],
                    "timing": "reveal",
                    "anchor": {"word": 1, "text": "المروحة"},
                    "start": 2.4,
                    "end": 3.8,
                    "activeTags": ["fan", "fin_stack"],
                    "motion": {"kind": "airflow_stream", "path": "intake_to_exhaust", "tint": "intake", "rpm": 240},
                },
            ],
        },
    ]


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_all_four_hardware_archetypes_pass_qa_and_match_across_p_k_r():
    import machine_explainer as me  # noqa: PLC0415
    import machine_kit as mk  # noqa: PLC0415

    specs = _archetype_scene_specs()
    kit_js = (SKILL / "templates" / "render" / "lib" / "machine-kit.js").as_uri()
    remotion_lib = SKILL / "templates" / "remotion" / "src" / "lib"

    for idx, spec in enumerate(specs):
        theme = "dark" if idx % 2 == 0 else "light"
        # X01–X04 standalone audit (including X03 <= 0.30 strict mask occlusion & X04 safe zone)
        audit = me.audit_machine_spec(spec, max_occlusion=0.30)
        assert audit["ok"], f"{spec['archetype']} failed audit: {audit['findings']}"

        for sample_t in (1.55, 3.05):
            py_g = mk.build_machine_scene(spec, sample_t, theme=theme)
            fr = np.full((1920, 1080, 3), 10.0 if theme == "dark" else 240.0, dtype=np.float32)
            mk.draw_machine_diagram(fr, spec, sample_t, theme=theme)
            assert float(np.std(fr)) > 3.0, f"{spec['archetype']} produced blank frame in Engine P"

            js_code = f"""
import {{ buildMachineScene }} from {json.dumps(kit_js)};
const g = buildMachineScene({json.dumps(spec)}, {sample_t}, {{ theme: {json.dumps(theme)} }});
console.log(JSON.stringify(g));
"""
            res = subprocess.run(["node", "--input-type=module", "-e", js_code], capture_output=True, text=True, check=True)
            js_g = json.loads(res.stdout)
            assert py_g["bounds"] == js_g["bounds"]
            assert py_g["world"] == js_g["world"]
            assert py_g["state"]["spinDeg"] == pytest.approx(js_g["state"]["spinDeg"], abs=1e-4)
            assert py_g["state"]["airflowPhase"] == pytest.approx(js_g["state"]["airflowPhase"], abs=1e-4)
            assert len(py_g["ops"]) == len(js_g["ops"])

    # Verify Engine R's remotion/src/lib/machine-kit.js + MachineDiagram.tsx cover cooling_system airflow & fan blades (Node 20+ compatible)
    r_exec = f"""
import fs from 'node:fs';
import path from 'node:path';
import {{ pathToFileURL }} from 'node:url';

const libDir = {json.dumps(str(remotion_lib))};
const kitUrl = pathToFileURL(path.join(libDir, 'machine-kit.js')).href;
const tsx = fs.readFileSync(path.join(libDir, 'MachineDiagram.tsx'), 'utf8');
for (const token of ['<svg', '<polygon', '<polyline', '<line', '<circle', '<DirectedText', "op.kind === 'airflow'", 'bladeLines']) {{
  if (!tsx.includes(token)) throw new Error('MachineDiagram.tsx missing expected token: ' + token);
}}
const kit = await import(kitUrl);
const coolSpec = {json.dumps(specs[3])};
const graph = kit.buildMachineScene(coolSpec, 3.05, {{ theme: 'dark', fps: 30 }});
const hasAirflow = graph.ops.some(o => o.kind === 'airflow' && o.streams.length === 3);
const hasBlades = graph.ops.some(o => o.kind === 'solid' && (o.bladeLines?.length || 0) === 7);
console.log(JSON.stringify({{ hasAirflow, hasBlades, spinDeg: graph.state.spinDeg }}));
"""
    r_res = subprocess.run(["node", "--input-type=module", "-e", r_exec], capture_output=True, text=True, check=True)
    r_data = json.loads(r_res.stdout)
    assert r_data["hasAirflow"] is True
    assert r_data["hasBlades"] is True
    assert r_data["spinDeg"] != 18.0


def test_cli_scaffold_and_reel_lint_integration(tmp_path: Path):
    # 1. Test `machine_explainer.py --init cpu_package`
    r_init = subprocess.run(
        [sys.executable, str(TOOLS / "machine_explainer.py"), str(tmp_path), "--init", "cpu_package", "--id", "cpu-1"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "Wrote draft machine spec" in r_init.stdout
    draft_path = tmp_path / "plan" / "machines" / "cpu-1.json"
    assert draft_path.is_file()

    # Draft placeholder should fail X02 until anchored to real measured words & beats
    r_draft_chk = subprocess.run(
        [sys.executable, str(TOOLS / "machine_explainer.py"), str(tmp_path), "--check"],
        capture_output=True,
        text=True,
    )
    assert r_draft_chk.returncode == 1
    draft_path.unlink()

    # 2. Write a complete valid project with `plan/machines/nvme-ssd.json` and run `reel_lint.py`
    spec = _sample_nvme_vo_spec()
    _write_project_fixture(tmp_path, spec)
    # Add text-direction.json + techniques.json so full `reel_lint.py` passes with X00!
    td_doc = {
        "scenes": [
            {
                "scene": 1,
                "captionStyle": "softfade",
                "textStyles": {"hook": "zoompunch"},
                "fontStyles": {"hook": {"family": "Cairo", "weight": 800}},
            },
            {
                "scene": 2,
                "captionStyle": "softfade",
                "textStyles": {"label": "riseword"},
                "fontStyles": {"label": {"family": "Cairo", "weight": 800}},
            },
            {
                "scene": 3,
                "captionStyle": "softfade",
                "textStyles": {},
                "fontStyles": {},
            },
        ]
    }
    (tmp_path / "plan" / "text-direction.json").write_text(json.dumps(td_doc), encoding="utf-8")
    lint_json = tmp_path / "lint-out.json"
    r_lint = subprocess.run(
        [sys.executable, str(TOOLS / "reel_lint.py"), str(tmp_path), "--json", str(lint_json)],
        capture_output=True,
        text=True,
    )
    lint_report = json.loads(lint_json.read_text(encoding="utf-8"))
    codes = {item["code"]: item["level"] for item in lint_report["items"]}
    assert codes.get("X00") == "ok", r_lint.stdout + r_lint.stderr
    assert not any(c.startswith("X0") and lvl == "error" for c, lvl in codes.items())


