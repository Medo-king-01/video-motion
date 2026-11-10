"""Machine Explainer X04 + cross-engine parity: safe zones, P/K/R geometry, archetypes.

The rendering-agreement half of the Machine Explainer suite: does the dynamic safe zone and the
right rail audit agree across engines, do all four hardware archetypes match, and does the CLI
scaffold produce a project that lints. Validation rules live in `test_machine_explainer.py`, the
Remotion renders in `test_machine_explainer_remotion.py`, sample specs in
`machine_explainer_support.py`.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from machine_explainer_support import (
    SKILL,
    TOOLS,
    _sample_nvme_vo_spec,
    _write_project_fixture,
)

pytestmark = pytest.mark.slow  # real synthesis/render/Chromium work: -m 'not slow' is the quick loop


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

    # Push NVMe diagram above content top safe-zone boundary (y < 200)
    bad_top = _sample_nvme_vo_spec()
    bad_top["layout"] = {"originX": 540, "originY": 180, "scale": 1.4}
    res_top = me.audit_machine_spec(bad_top)
    assert not res_top["ok"]
    assert any(f["code"] == "X04" and "safe zone" in f["message"] for f in res_top["findings"])

    # Intentional motion-path X04 tests:
    # Static solid/wire geometry stays completely safe near (500, 760), and the motion step is ONLY
    # active in [4.2, 5.8] (NOT active at spec midpoint 3.0s!).
    # Note: 3D point [527, 125, 0] projects to screen (sx=970, sy=1200), which is INSIDE the content
    # safe zone [40..1040, 200..1350] yet RIGHT INSIDE PLATFORM_RIGHT_RAIL [940..1080, 1100..1500]!
    def _motion_rail_spec(motion_kind: str, path_pts: list[list[float]]) -> dict:
        return {
            "version": 1,
            "id": f"rail-{motion_kind}",
            "archetype": "custom",
            "clock": "scene",
            "start": 0.0,
            "end": 6.0,
            "revealWindow": {"unit": "scene_seconds", "start": 0.0, "end": 0.6},
            "sources": [{"id": "s1", "title": "Motion Envelope Test Spec", "kind": "spec", "ref": "ENV-01"}],
            "parts": [
                {
                    "id": "safe_chip", "tag": "chip", "layer": "mid", "primitive": "slab", "role": "chip",
                    "x": -20, "y": -20, "z": 0, "dx": 40, "dy": 40, "dz": 12, "alpha": 1.0,
                }
            ],
            "paths": {"test_route": path_pts},
            "steps": [
                {
                    "id": "late-step",
                    "evidence": "source",
                    "sourceId": "s1",
                    "locator": {"kind": "section", "value": "§4.2"},
                    "quote": "Late step motion trajectory must be audited across its active window.",
                    "copyIds": ["c-1"],
                    "timing": "sync",
                    "anchor": {"word": 0, "text": "حركة"},
                    "start": 4.2,
                    "end": 5.8,
                    "activeTags": ["chip"],
                    "motion": {"kind": motion_kind, "path": "test_route", "tint": "active"},
                }
            ],
        }

    # 1. packet_flow crossing PLATFORM_RIGHT_RAIL during late step [4.2, 5.8] must fail X04
    bad_pkt = _motion_rail_spec("packet_flow", [[0, 0, 14], [527, 125, 0]])
    res_pkt = me.audit_machine_spec(bad_pkt)
    assert not res_pkt["ok"]
    assert any(
        f["code"] == "X04" and "packet_flow" in f["message"] and "PLATFORM_RIGHT_RAIL" in f["message"]
        for f in res_pkt["findings"]
    ), res_pkt["findings"]

    # 2. airflow_stream crossing PLATFORM_RIGHT_RAIL during late step [4.2, 5.8] must fail X04
    bad_air = _motion_rail_spec("airflow_stream", [[0, 0, 14], [527, 125, 0]])
    res_air = me.audit_machine_spec(bad_air)
    assert not res_air["ok"]
    assert any(
        f["code"] == "X04" and "airflow_stream" in f["message"] and "PLATFORM_RIGHT_RAIL" in f["message"]
        for f in res_air["findings"]
    ), res_air["findings"]

    # 3. Safe packet_flow and airflow_stream paths stay completely clean
    ok_pkt = _motion_rail_spec("packet_flow", [[-30, -10, 14], [45, 25, 18]])
    ok_air = _motion_rail_spec("airflow_stream", [[-30, -10, 14], [45, 25, 18]])
    assert me.audit_machine_spec(ok_pkt)["ok"]
    assert me.audit_machine_spec(ok_air)["ok"]


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
