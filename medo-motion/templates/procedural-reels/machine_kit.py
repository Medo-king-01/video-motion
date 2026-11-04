"""Native studio Machine Explainer geometry, state, coverage-mask occlusion, and Engine P renderer.

Mirrors `templates/render/lib/machine-kit.js` (K & R) mathematically while providing
raster polygon coverage-mask occlusion auditing (`compute_occlusion_report`) and
OpenCV/NumPy cutaway rendering (`draw_machine_diagram`).

All colours come strictly from the locked 12-colour `brand/brand.json` v2.6 palette
(+ derived `ink_shadow`). Safe-zone envelopes are read dynamically from `layout_p.py`.
"""
from __future__ import annotations

import copy
import math
from typing import Any

import cv2
import numpy as np

import layout_p
from captions import draw_directed_text
from lib import BLACK, DRED, EMER, GRAY, INK, LGRAY, RED, TEAL, WHITE, YEL

COS30 = 0.8660254037844386
SIN30 = 0.5
LAYER_RANK = {"back": 0, "mid": 1, "front": 2, "overlay": 3}
DEFAULT_MAX_OCCLUSION = 0.35

GRAY_1 = (216, 215, 213)
GRAY_3 = (191, 186, 183)
RED_BRIGHT = (203, 8, 1)

HEX_TO_RGB: dict[str, tuple[int, int, int]] = {
    "#CB271B": RED,
    "#CB0801": RED_BRIGHT,
    "#9F0803": DRED,
    "#0A0A0A": INK,
    "#71717A": TEAL,
    "#F3F2F1": WHITE,
    "#D8D7D5": GRAY_1,
    "#C9C5C2": LGRAY,
    "#BFBAB7": GRAY_3,
    "#A3A2A0": GRAY,
    "#D97F68": YEL,
    "#D5AEA6": EMER,
    "#030303": BLACK,
}

MACHINE_PALETTE: dict[str, str] = {
    "red": "#CB271B",
    "red_bright": "#CB0801",
    "red_deep": "#9F0803",
    "ink": "#0A0A0A",
    "ink_soft": "#71717A",
    "paper": "#F3F2F1",
    "gray_1": "#D8D7D5",
    "gray_2": "#C9C5C2",
    "gray_3": "#BFBAB7",
    "gray_4": "#A3A2A0",
    "salmon": "#D97F68",
    "blush": "#D5AEA6",
    "inkShadow": "#030303",
}

MACHINE_ROLES: dict[str, dict[str, dict[str, str]]] = {
    "dark": {
        "substrate": {
            "top": MACHINE_PALETTE["ink_soft"],
            "left": MACHINE_PALETTE["ink"],
            "right": MACHINE_PALETTE["inkShadow"],
            "stroke": MACHINE_PALETTE["gray_4"],
        },
        "housing": {
            "top": MACHINE_PALETTE["gray_4"],
            "left": MACHINE_PALETTE["ink_soft"],
            "right": MACHINE_PALETTE["ink"],
            "stroke": MACHINE_PALETTE["paper"],
        },
        "chip": {
            "top": MACHINE_PALETTE["ink"],
            "left": MACHINE_PALETTE["inkShadow"],
            "right": MACHINE_PALETTE["inkShadow"],
            "stroke": MACHINE_PALETTE["gray_3"],
        },
        "contact": {
            "top": MACHINE_PALETTE["blush"],
            "left": MACHINE_PALETTE["salmon"],
            "right": MACHINE_PALETTE["ink_soft"],
            "stroke": MACHINE_PALETTE["paper"],
        },
        "intake": {
            "top": MACHINE_PALETTE["paper"],
            "left": MACHINE_PALETTE["blush"],
            "right": MACHINE_PALETTE["gray_2"],
            "stroke": MACHINE_PALETTE["paper"],
        },
        "active": {
            "top": MACHINE_PALETTE["salmon"],
            "left": MACHINE_PALETTE["red"],
            "right": MACHINE_PALETTE["red_deep"],
            "stroke": MACHINE_PALETTE["paper"],
        },
        "cutaway": {
            "top": MACHINE_PALETTE["gray_3"],
            "left": MACHINE_PALETTE["ink_soft"],
            "right": MACHINE_PALETTE["ink"],
            "stroke": MACHINE_PALETTE["blush"],
        },
    },
    "light": {
        "substrate": {
            "top": MACHINE_PALETTE["gray_2"],
            "left": MACHINE_PALETTE["gray_3"],
            "right": MACHINE_PALETTE["ink_soft"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "housing": {
            "top": MACHINE_PALETTE["paper"],
            "left": MACHINE_PALETTE["gray_1"],
            "right": MACHINE_PALETTE["gray_3"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "chip": {
            "top": MACHINE_PALETTE["ink_soft"],
            "left": MACHINE_PALETTE["ink"],
            "right": MACHINE_PALETTE["inkShadow"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "contact": {
            "top": MACHINE_PALETTE["blush"],
            "left": MACHINE_PALETTE["salmon"],
            "right": MACHINE_PALETTE["red_deep"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "intake": {
            "top": MACHINE_PALETTE["paper"],
            "left": MACHINE_PALETTE["blush"],
            "right": MACHINE_PALETTE["gray_2"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "active": {
            "top": MACHINE_PALETTE["red"],
            "left": MACHINE_PALETTE["red_deep"],
            "right": MACHINE_PALETTE["ink"],
            "stroke": MACHINE_PALETTE["ink"],
        },
        "cutaway": {
            "top": MACHINE_PALETTE["paper"],
            "left": MACHINE_PALETTE["gray_1"],
            "right": MACHINE_PALETTE["gray_2"],
            "stroke": MACHINE_PALETTE["ink_soft"],
        },
    },
}

ALLOWED_SOURCE_KINDS = ("spec", "datasheet", "manual", "paper", "standard", "encyclopedia", "user")
ALLOWED_LOCATOR_KINDS = ("section", "page", "table", "figure", "clause", "line")
ALLOWED_MOTION_KINDS = ("packet_flow", "heat_tint", "spin", "airflow_stream", "pulse")
SUPPORTED_ARCHETYPES = ("nvme_ssd", "cpu_package", "ram_dimm", "cooling_system", "custom")


def _finite(n: Any) -> bool:
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return False
    try:
        return math.isfinite(float(n))
    except (OverflowError, TypeError, ValueError):
        return False


def _non_empty(s: Any) -> bool:
    return isinstance(s, str) and bool(s.strip())


def _clamp01(v: float) -> float:
    return min(1.0, max(0.0, float(v)))


def _ease_out_cubic(x: float) -> float:
    u = _clamp01(x)
    return 1.0 - ((1.0 - u) ** 3)


def _round4(v: float) -> float:
    return math.floor(float(v) * 1e4 + 0.5) / 1e4


def iso_project_point(
    x: float,
    y: float,
    z: float,
    *,
    origin_x: float = 500.0,
    origin_y: float = 760.0,
    scale: float = 1.35,
) -> list[float]:
    return [
        _round4(origin_x + (x - y) * COS30 * scale),
        _round4(origin_y + (x + y) * SIN30 * scale - z * scale),
        _round4(x + y + z),
    ]


def _build_nvme_ssd(params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params or {}
    raw_layers = p.get("nandLayers")
    nand_layers = raw_layers if isinstance(raw_layers, int) and not isinstance(raw_layers, bool) and raw_layers >= 2 else 4
    cutaway_alpha = _clamp01(p["cutawayAlpha"]) if _finite(p.get("cutawayAlpha")) else 0.18

    parts: list[dict[str, Any]] = [
        {
            "id": "pcb", "tag": "pcb", "layer": "back", "primitive": "slab", "role": "substrate",
            "x": -130, "y": -44, "z": 0, "dx": 260, "dy": 88, "dz": 8, "alpha": 1.0,
        },
        {
            "id": "m2_pins", "tag": "pcie_bus", "layer": "mid", "primitive": "ticks", "role": "contact",
            "x": -128, "y": -33, "z": 8, "count": 8, "stepX": 0, "stepY": 9, "dx": 14, "dy": 5, "dz": 2, "alpha": 1.0,
        },
    ]
    for lane in range(4):
        ly = -22 + lane * 14
        parts.append({
            "id": f"pcie_lane_{lane + 1}",
            "tag": "pcie_bus",
            "layer": "mid",
            "primitive": "wire",
            "role": "intake",
            "points": [[-114, ly, 9.5], [-82, ly * 0.75, 10], [-54, ly * 0.45, 12]],
            "width": 3.2,
            "alpha": 1.0,
        })
    parts.extend([
        {
            "id": "controller_pkg", "tag": "controller", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -54, "y": -24, "z": 8, "dx": 52, "dy": 48, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "controller_die", "tag": "controller", "layer": "mid", "primitive": "slab", "role": "contact",
            "x": -43, "y": -14, "z": 19, "dx": 30, "dy": 28, "dz": 3, "alpha": 1.0,
        },
        {
            "id": "dram_cache", "tag": "dram_cache", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -34, "y": 26, "z": 8, "dx": 30, "dy": 15, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "dram_link", "tag": "dram_cache", "layer": "mid", "primitive": "wire", "role": "contact",
            "points": [[-20, 22, 14], [-20, 26, 14]], "width": 3.0, "alpha": 1.0,
        },
        {
            "id": "nand_ch_0", "tag": "nand_channel", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[-2, 14, 9.5], [26, 18, 9.5], [52, 16, 10]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "nand_ch_1", "tag": "nand_channel", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[-2, 24, 9.5], [26, 28, 9.5], [52, 26, 10]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "nand_stack", "tag": "nand_stack", "layer": "mid", "primitive": "slab_stack", "role": "chip",
            "x": 52, "y": -24, "z": 8, "dx": 64, "dy": 56, "layerDz": 5, "gapDz": 2, "layers": nand_layers, "alpha": 1.0,
        },
        {
            "id": "heatsink_rear_rail", "tag": "heatsink", "layer": "back", "primitive": "slab", "role": "housing",
            "x": -116, "y": -44, "z": 8, "dx": 238, "dy": 8, "dz": 28, "alpha": 0.9,
        },
        {
            "id": "heatsink_cutaway_hood", "tag": "heatsink", "layer": "front", "primitive": "slab", "role": "cutaway",
            "x": -116, "y": -34, "z": 38, "dx": 238, "dy": 74, "dz": 4, "alpha": cutaway_alpha, "cutaway": True,
        },
    ])
    top_nand_z = 8 + nand_layers * 7
    return {
        "parts": parts,
        "paths": {
            "pcie_to_controller": [[-124, -4, 10], [-82, -2, 11], [-28, 0, 22]],
            "controller_to_dram": [[-22, 12, 20], [-19, 33, 20]],
            "controller_to_nand": [[-2, 18, 12], [26, 22, 12], [84, 4, top_nand_z]],
            "heat_rise": [[-28, 0, 24], [-28, -6, 48], [-28, -12, 74]],
        },
        "world": {
            "pcie_entry": [-120, 0, 10],
            "controller_center": [-28, 0, 22],
            "dram_center": [-19, 33, 19],
            "nand_center": [84, 4, top_nand_z],
            "callout_anchor": [0, -56, 68],
        },
    }


def _build_cpu_package(params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params or {}
    cutaway_alpha = _clamp01(p["cutawayAlpha"]) if _finite(p.get("cutawayAlpha")) else 0.18
    parts: list[dict[str, Any]] = [
        {
            "id": "substrate", "tag": "substrate", "layer": "back", "primitive": "slab", "role": "substrate",
            "x": -95, "y": -95, "z": 0, "dx": 190, "dy": 190, "dz": 10, "alpha": 1.0,
        },
        {
            "id": "socket_pins_front", "tag": "socket_pins", "layer": "mid", "primitive": "ticks", "role": "contact",
            "x": -76, "y": 83, "z": 10, "count": 6, "stepX": 28, "stepY": 0, "dx": 16, "dy": 10, "dz": 2.5, "alpha": 1.0,
        },
        {
            "id": "core_0", "tag": "cores", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -72, "y": -70, "z": 10, "dx": 28, "dy": 54, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "core_1", "tag": "cores", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -38, "y": -70, "z": 10, "dx": 28, "dy": 54, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "core_2", "tag": "cores", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -72, "y": -6, "z": 10, "dx": 28, "dy": 54, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "core_3", "tag": "cores", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": -38, "y": -6, "z": 10, "dx": 28, "dy": 54, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "l3_cache", "tag": "l3_cache", "layer": "mid", "primitive": "slab", "role": "contact",
            "x": -2, "y": -66, "z": 10, "dx": 26, "dy": 118, "dz": 12, "alpha": 1.0,
        },
        {
            "id": "io_die", "tag": "io_die", "layer": "mid", "primitive": "slab", "role": "chip",
            "x": 34, "y": -52, "z": 10, "dx": 40, "dy": 96, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "fabric_bridge", "tag": "fabric", "layer": "mid", "primitive": "slab", "role": "contact",
            "x": 18, "y": 54, "z": 10, "dx": 28, "dy": 18, "dz": 9, "alpha": 1.0,
        },
        {
            "id": "fabric_top", "tag": "fabric", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[-56, 60, 11.5], [18, 60, 14], [58, 58, 11.5]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "fabric_bot", "tag": "fabric", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[-56, 70, 11.5], [32, 70, 14], [64, 68, 11.5]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "ihs_rear_wall", "tag": "ihs", "layer": "back", "primitive": "slab", "role": "housing",
            "x": -84, "y": -84, "z": 10, "dx": 168, "dy": 10, "dz": 24, "alpha": 0.9,
        },
        {
            "id": "ihs_cutaway_lid", "tag": "ihs", "layer": "front", "primitive": "slab", "role": "cutaway",
            "x": -84, "y": -74, "z": 34, "dx": 168, "dy": 158, "dz": 4, "alpha": cutaway_alpha, "cutaway": True,
        },
    ]
    return {
        "parts": parts,
        "paths": {
            "ring_to_cores": [[54, -12, 23], [11, -12, 23], [-52, -36, 23]],
            "cores_to_cache": [[-52, 18, 23], [11, 18, 23]],
            "cache_to_io": [[11, -24, 23], [54, -24, 23]],
            "ihs_heat_spread": [[-38, -20, 24], [8, 0, 38], [42, 18, 44]],
        },
        "world": {
            "cores_center": [-40, -11, 21],
            "l3_center": [11, -7, 22],
            "io_center": [54, -4, 21],
            "ihs_top": [0, 0, 38],
            "callout_anchor": [0, -88, 66],
        },
    }


def _build_ram_dimm(params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params or {}
    cutaway_alpha = _clamp01(p["cutawayAlpha"]) if _finite(p.get("cutawayAlpha")) else 0.16
    parts: list[dict[str, Any]] = [
        {
            "id": "dimm_pcb", "tag": "pcb", "layer": "back", "primitive": "slab", "role": "substrate",
            "x": -146, "y": -32, "z": 0, "dx": 292, "dy": 64, "dz": 7, "alpha": 1.0,
        },
        {
            "id": "edge_pins_a", "tag": "bus_pins", "layer": "mid", "primitive": "ticks", "role": "contact",
            "x": -136, "y": 23, "z": 7, "count": 6, "stepX": 20, "stepY": 0, "dx": 11, "dy": 9, "dz": 2.5, "alpha": 1.0,
        },
        {
            "id": "edge_pins_b", "tag": "bus_pins", "layer": "mid", "primitive": "ticks", "role": "contact",
            "x": 24, "y": 23, "z": 7, "count": 6, "stepX": 20, "stepY": 0, "dx": 11, "dy": 9, "dz": 2.5, "alpha": 1.0,
        },
        {
            "id": "rcd_controller", "tag": "rcd_controller", "layer": "mid", "primitive": "slab", "role": "contact",
            "x": -16, "y": -18, "z": 7, "dx": 32, "dy": 30, "dz": 11, "alpha": 1.0,
        },
        {
            "id": "dram_banks_a", "tag": "dram_banks", "layer": "mid", "primitive": "ticks", "role": "chip",
            "x": -134, "y": -20, "z": 7, "count": 4, "stepX": 28, "stepY": 0, "dx": 20, "dy": 28, "dz": 9, "alpha": 1.0,
        },
        {
            "id": "dram_banks_b", "tag": "dram_banks", "layer": "mid", "primitive": "ticks", "role": "chip",
            "x": 28, "y": -20, "z": 7, "count": 4, "stepX": 28, "stepY": 0, "dx": 20, "dy": 28, "dz": 9, "alpha": 1.0,
        },
        {
            "id": "channel_a_bus", "tag": "channel_bus", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[-16, 15, 9], [-72, 15, 9], [-124, 15, 9]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "channel_b_bus", "tag": "channel_bus", "layer": "mid", "primitive": "wire", "role": "intake",
            "points": [[16, 15, 9], [72, 15, 9], [124, 15, 9]], "width": 3.4, "alpha": 1.0,
        },
        {
            "id": "spreader_rear", "tag": "heatspreader", "layer": "back", "primitive": "slab", "role": "housing",
            "x": -140, "y": -32, "z": 7, "dx": 280, "dy": 7, "dz": 26, "alpha": 0.9,
        },
        {
            "id": "spreader_cutaway", "tag": "heatspreader", "layer": "front", "primitive": "slab", "role": "cutaway",
            "x": -140, "y": -25, "z": 32, "dx": 280, "dy": 55, "dz": 3, "alpha": cutaway_alpha, "cutaway": True,
        },
    ]
    return {
        "parts": parts,
        "paths": {
            "channel_a": [[0, 15, 18], [-48, 15, 11], [-122, 6, 17]],
            "channel_b": [[0, 15, 18], [48, 15, 11], [122, 6, 17]],
            "pins_to_rcd": [[-10, 28, 10], [0, -2, 18]],
        },
        "world": {
            "rcd_center": [0, -3, 18],
            "bank_a_center": [-82, -6, 16],
            "bank_b_center": [80, -6, 16],
            "callout_anchor": [0, -48, 62],
        },
    }


def _build_cooling_system(params: dict[str, Any] | None = None) -> dict[str, Any]:
    p = params or {}
    raw_fins = p.get("finLayers")
    fin_layers = raw_fins if isinstance(raw_fins, int) and not isinstance(raw_fins, bool) and raw_fins >= 3 else 5
    cutaway_alpha = _clamp01(p["cutawayAlpha"]) if _finite(p.get("cutawayAlpha")) else 0.16
    parts: list[dict[str, Any]] = [
        {
            "id": "coldplate", "tag": "coldplate", "layer": "mid", "primitive": "slab", "role": "contact",
            "x": -102, "y": -32, "z": 0, "dx": 62, "dy": 64, "dz": 12, "alpha": 1.0,
        },
        {
            "id": "heatpipe_front", "tag": "heatpipes", "layer": "mid", "primitive": "wire", "role": "active",
            "points": [[-66, 26, 11], [-16, 36, 22], [44, 36, 46]], "width": 5.0, "alpha": 1.0,
        },
        {
            "id": "heatpipe_coil", "tag": "heatpipes", "layer": "mid", "primitive": "coil", "role": "active",
            "x": -36, "y": 36, "z": 20, "length": 34, "radius": 6, "turns": 4, "axis": "x", "alpha": 1.0,
        },
        {
            "id": "fin_stack", "tag": "fin_stack", "layer": "mid", "primitive": "slab_stack", "role": "housing",
            "x": 6, "y": -38, "z": 16, "dx": 68, "dy": 68, "layerDz": 4, "gapDz": 6, "layers": fin_layers, "alpha": 1.0,
        },
        {
            "id": "fan", "tag": "fan", "layer": "mid", "primitive": "ring", "role": "chip",
            "x": 118, "y": 4, "z": 20, "rOuter": 38, "rInner": 14, "h": 16, "blades": 7, "segments": 24, "alpha": 1.0,
        },
        {
            "id": "shroud_rear", "tag": "shroud", "layer": "back", "primitive": "slab", "role": "substrate",
            "x": 0, "y": -46, "z": 12, "dx": 158, "dy": 8, "dz": 52, "alpha": 0.88,
        },
        {
            "id": "shroud_cutaway", "tag": "shroud", "layer": "front", "primitive": "slab", "role": "cutaway",
            "x": 0, "y": -38, "z": 64, "dx": 158, "dy": 84, "dz": 4, "alpha": cutaway_alpha, "cutaway": True,
        },
    ]
    return {
        "parts": parts,
        "paths": {
            "heatpipe_transfer": [[-70, 24, 12], [-16, 36, 24], [44, 34, 48]],
            "intake_to_exhaust": [[148, 4, 36], [106, 4, 36], [42, 0, 38], [-18, 0, 42]],
        },
        "world": {
            "coldplate_center": [-71, 0, 12],
            "fin_stack_center": [40, -4, 40],
            "fan_axis": [118, 4, 28],
            "callout_anchor": [18, -60, 82],
        },
    }


def expand_machine_model(spec: dict[str, Any]) -> dict[str, Any]:
    arch = spec.get("archetype") or "custom"
    builders = {
        "nvme_ssd": _build_nvme_ssd,
        "cpu_package": _build_cpu_package,
        "ram_dimm": _build_ram_dimm,
        "cooling_system": _build_cooling_system,
    }
    if arch in builders:
        base = builders[arch](spec.get("params"))
        extra = spec.get("extraParts")
        return {
            "parts": [*base["parts"], *copy.deepcopy(extra)] if isinstance(extra, list) else base["parts"],
            "paths": {**base["paths"], **(spec.get("paths") or {})},
            "world": {**base["world"], **(spec.get("world") or {})},
        }
    if arch == "custom":
        raw_parts = spec.get("parts")
        return {
            "parts": copy.deepcopy(raw_parts) if isinstance(raw_parts, list) else [],
            "paths": dict(spec.get("paths") or {}),
            "world": dict(spec.get("world") or {}),
        }
    raise ValueError(f"Unsupported machine archetype: {arch}")


def validate_machine_spec(spec: Any, *, fps: int | None = None) -> list[str]:
    resolved_fps = int(fps or layout_p.FPS or 30)
    errors: list[str] = []
    if not isinstance(spec, dict):
        return ["machine spec must be an object"]
    if spec.get("version") != 1:
        errors.append("machine spec version must be 1")
    if not _non_empty(spec.get("id")):
        errors.append("machine spec requires a non-empty id")
    arch = spec.get("archetype")
    if arch not in SUPPORTED_ARCHETYPES:
        errors.append(f'unsupported archetype "{arch}"; expected one of {", ".join(SUPPORTED_ARCHETYPES)}')
    clock = spec.get("clock")
    if clock not in ("vo", "scene"):
        errors.append('clock must be "vo" or "scene"')
    scene = spec.get("scene")
    if clock == "vo" and (not isinstance(scene, int) or isinstance(scene, bool) or scene < 1):
        errors.append("vo-clock machine spec requires a positive integer scene index")
    start, end = spec.get("start"), spec.get("end")
    if not _finite(start) or not _finite(end) or float(start) < 0 or float(end) <= float(start):
        errors.append("machine spec requires finite 0 <= start < end")

    rw = spec.get("revealWindow")
    expected_unit = "scene_seconds" if clock == "scene" else "vo_seconds"
    if not isinstance(rw, dict):
        errors.append(f'revealWindow must be an object {{unit: "{expected_unit}", start, end}}')
    else:
        if rw.get("unit") != expected_unit:
            errors.append(f'revealWindow.unit must be "{expected_unit}" when clock="{clock}"')
        if (
            not _finite(rw.get("start"))
            or not _finite(rw.get("end"))
            or (_finite(start) and float(rw["start"]) < float(start) - 1e-9)
            or float(rw["end"]) <= float(rw["start"])
            or (_finite(end) and float(rw["end"]) > float(end) + 1e-9)
        ):
            errors.append("revealWindow requires finite bounds inside [spec.start, spec.end] with start < end")

    source_map: dict[str, dict[str, Any]] = {}
    sources = spec.get("sources")
    if not isinstance(sources, list):
        errors.append("sources must be an array (may be empty only when all steps are illustrative)")
    else:
        for src in sources:
            if not isinstance(src, dict) or not _non_empty(src.get("id")) or src["id"] in source_map:
                errors.append("each source needs a unique non-empty id")
                continue
            sid = src["id"]
            source_map[sid] = src
            if not _non_empty(src.get("title")) or len(src["title"].strip()) < 3:
                errors.append(f'source "{sid}": title must be at least 3 characters')
            if src.get("kind") not in ALLOWED_SOURCE_KINDS:
                errors.append(f'source "{sid}": kind must be one of {", ".join(ALLOWED_SOURCE_KINDS)}')
            if not _non_empty(src.get("ref")) or len(src["ref"].strip()) < 4:
                errors.append(f'source "{sid}": ref must provide a verifiable URI, DOI, standard ID, or user brief reference')

    model = {"parts": [], "paths": {}, "world": {}}
    if arch in SUPPORTED_ARCHETYPES:
        model = expand_machine_model(spec)
        if not model["parts"]:
            errors.append("expanded machine model contains zero parts")
    known_tags = {p.get("tag") for p in model["parts"] if _non_empty(p.get("tag"))}

    steps = spec.get("steps")
    if not isinstance(steps, list) or not steps:
        errors.append("steps must be a non-empty array")
        return errors

    step_ids: set[str] = set()
    for step in steps:
        if not isinstance(step, dict) or not _non_empty(step.get("id")) or step["id"] in step_ids:
            errors.append("each step requires a unique non-empty id")
            continue
        stid = step["id"]
        step_ids.add(stid)
        ev = step.get("evidence")
        if ev not in ("source", "user", "illustrative"):
            errors.append(f'{stid}: evidence must be "source", "user", or "illustrative"')
        elif ev in ("source", "user"):
            src = source_map.get(step.get("sourceId") or "")
            if src is None:
                errors.append(f'{stid}: sourceId "{step.get("sourceId") or ""}" is not declared in sources[]')
            elif ev == "source" and src.get("kind") == "user":
                errors.append(f'{stid}: evidence="source" cannot cite a source of kind="user"')
            loc = step.get("locator")
            if (
                not isinstance(loc, dict)
                or loc.get("kind") not in ALLOWED_LOCATOR_KINDS
                or not _non_empty(loc.get("value"))
                or len(loc["value"].strip()) < 2
            ):
                errors.append(
                    f'{stid}: requires locator {{kind: {"|".join(ALLOWED_LOCATOR_KINDS)}, value: "<specific section/page/clause>"}}'
                )
            if not _non_empty(step.get("quote")) or len(step["quote"].strip()) < 10:
                errors.append(f"{stid}: requires supporting quote/excerpt of at least 10 characters")
        elif ev == "illustrative":
            il_id = step.get("illustrativeLabelId")
            cids = step.get("copyIds")
            if not _non_empty(il_id) or not isinstance(cids, list) or il_id not in cids:
                errors.append(f"{stid}: illustrative evidence requires illustrativeLabelId included in copyIds")

        cids = step.get("copyIds")
        if not isinstance(cids, list) or not cids or any(not _non_empty(c) for c in cids):
            errors.append(f"{stid}: copyIds must be a non-empty list of copy.json fragment ids")

        s_start, s_end = step.get("start"), step.get("end")
        if (
            not _finite(s_start)
            or not _finite(s_end)
            or (_finite(start) and float(s_start) < float(start) - 1e-9)
            or float(s_end) <= float(s_start)
            or (_finite(end) and float(s_end) > float(end) + 1e-9)
        ):
            errors.append(f"{stid}: step start/end must be finite and within [spec.start, spec.end]")

        timing = step.get("timing")
        if timing not in ("lead", "sync", "reveal"):
            errors.append(f'{stid}: timing must be "lead", "sync", or "reveal"')
        elif timing == "lead" and step.get("fact") is not False:
            errors.append(f"{stid}: lead timing is structure-only and requires fact=false")

        anc = step.get("anchor")
        w_idx = anc.get("word") if isinstance(anc, dict) else None
        if (
            not isinstance(anc, dict)
            or not isinstance(w_idx, int)
            or isinstance(w_idx, bool)
            or w_idx < 0
            or not _non_empty(anc.get("text"))
        ):
            errors.append(f"{stid}: anchor requires {{word: non-negative int, text: non-empty string}}")
        elif "wordStart" in anc or "wordEnd" in anc:
            if (
                not _finite(anc.get("wordStart"))
                or not _finite(anc.get("wordEnd"))
                or float(anc["wordStart"]) < 0
                or float(anc["wordEnd"]) <= float(anc["wordStart"])
            ):
                errors.append(
                    f"{stid}: anchor wordStart/wordEnd must be finite non-boolean numbers with 0 <= wordStart < wordEnd"
                )
            elif _finite(s_start) and _finite(s_end):
                ws, we = float(anc["wordStart"]), float(anc["wordEnd"])
                ss, se = float(s_start), float(s_end)
                lead_max = 6.0 / max(1, resolved_fps) + 1e-8
                if timing == "lead" and not (-1e-9 <= ws - ss <= lead_max):
                    errors.append(f"{stid}: lead may precede its word by at most 6 frames at {resolved_fps}fps")
                elif timing == "sync" and abs(ss - ws) > 1e-6:
                    errors.append(f"{stid}: sync must start exactly at anchor word start")
                elif timing == "reveal" and ss < ws - 1e-9:
                    errors.append(f"{stid}: reveal cannot appear before its anchor word")
                if se < we - 1e-9:
                    errors.append(f"{stid}: step must survive through the end of its anchor word")

        tags = step.get("activeTags")
        if not isinstance(tags, list) or not tags or any(not _non_empty(t) for t in tags):
            errors.append(f"{stid}: activeTags must name at least one part tag")
        elif known_tags:
            for tag in tags:
                if tag not in known_tags:
                    errors.append(f'{stid}: activeTag "{tag}" does not match any part in archetype "{arch}"')

        mot = step.get("motion")
        if not isinstance(mot, dict) or mot.get("kind") not in ALLOWED_MOTION_KINDS:
            errors.append(f'{stid}: motion.kind must be one of {", ".join(ALLOWED_MOTION_KINDS)}')
        elif (
            mot.get("kind") in ("packet_flow", "airflow_stream")
            and _non_empty(mot.get("path"))
            and model["paths"]
            and mot["path"] not in model["paths"]
        ):
            errors.append(f'{stid}: motion.path "{mot["path"]}" is not defined in machine paths')

    return errors


def to_scene_local_machine(spec: dict[str, Any], scene_start: float = 0.0) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("machine spec must be an object")
    if spec.get("clock") == "scene":
        return copy.deepcopy(spec)
    offset = float(scene_start)
    out = copy.deepcopy(spec)
    out["clock"] = "scene"
    out["start"] = _round4(float(spec["start"]) - offset)
    out["end"] = _round4(float(spec["end"]) - offset)
    out["revealWindow"] = {
        "unit": "scene_seconds",
        "start": _round4(float(spec["revealWindow"]["start"]) - offset),
        "end": _round4(float(spec["revealWindow"]["end"]) - offset),
    }
    for st in out["steps"]:
        st["start"] = _round4(float(st["start"]) - offset)
        st["end"] = _round4(float(st["end"]) - offset)
        anc = st.get("anchor")
        if isinstance(anc, dict):
            if _finite(anc.get("wordStart")):
                anc["wordStart"] = _round4(float(anc["wordStart"]) - offset)
            if _finite(anc.get("wordEnd")):
                anc["wordEnd"] = _round4(float(anc["wordEnd"]) - offset)
    return out


def machine_state_at(spec: dict[str, Any], time: float, *, fps: int | None = None) -> dict[str, Any]:
    errs = validate_machine_spec(spec, fps=fps)
    if errs:
        raise ValueError("; ".join(errs))
    if not _finite(time):
        raise ValueError("time must be finite")
    t = float(time)
    active = float(spec["start"]) <= t < float(spec["end"])
    rw_span = max(1e-6, float(spec["revealWindow"]["end"]) - float(spec["revealWindow"]["start"]))
    reveal_progress = _ease_out_cubic((t - float(spec["revealWindow"]["start"])) / rw_span) if active else 0.0

    active_step = None
    if active:
        for st in spec["steps"]:
            if float(st["start"]) <= t < float(st["end"]):
                active_step = st

    step_progress = 0.0
    highlight_mix = 0.0
    spin_deg = 18.0
    packet_progress = -1.0
    airflow_phase = -1.0
    pulse_boost = 0.0

    if active_step is not None:
        elapsed = max(0.0, t - float(active_step["start"]))
        dur = max(1e-6, float(active_step["end"]) - float(active_step["start"]))
        step_progress = _round4(_clamp01(elapsed / dur))
        highlight_mix = _round4(_ease_out_cubic(elapsed / min(0.24, dur * 0.5)))
        mot = active_step["motion"]
        rate = float(mot["rate"]) if _finite(mot.get("rate")) and float(mot["rate"]) > 0 else 1.25
        kind = mot["kind"]
        if kind == "spin":
            rpm = float(mot["rpm"]) if _finite(mot.get("rpm")) and float(mot["rpm"]) > 0 else 180.0
            spin_deg = _round4((18.0 + elapsed * rpm * 6.0) % 360.0)
        elif kind == "packet_flow":
            packet_progress = _round4((elapsed * rate) % 1.0)
        elif kind == "airflow_stream":
            airflow_phase = _round4((elapsed * rate) % 1.0)
            rpm = float(mot["rpm"]) if _finite(mot.get("rpm")) and float(mot["rpm"]) > 0 else 180.0
            spin_deg = _round4((18.0 + elapsed * rpm * 6.0) % 360.0)
        elif kind in ("pulse", "heat_tint"):
            pulse_boost = _round4(0.5 + 0.5 * math.sin(elapsed * math.pi * 4.0))

    return {
        "id": spec["id"],
        "active": active,
        "revealProgress": _round4(reveal_progress),
        "activeStepId": active_step["id"] if active_step else None,
        "activeStep": active_step,
        "activeTags": list(active_step["activeTags"]) if active_step else [],
        "stepProgress": step_progress,
        "highlightMix": highlight_mix,
        "spinDeg": spin_deg,
        "packetProgress": packet_progress,
        "airflowPhase": airflow_phase,
        "pulseBoost": pulse_boost,
    }


def _polyline_length_2d(pts: list[list[float]]) -> float:
    return sum(math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]) for i in range(1, len(pts)))


def point_along_polyline_2d(pts: list[list[float]], p: float) -> list[float]:
    if not pts:
        return [0.0, 0.0]
    if len(pts) == 1:
        return list(pts[0])
    budget = _polyline_length_2d(pts) * _clamp01(p)
    for i in range(1, len(pts)):
        a, b = pts[i - 1], pts[i]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if budget <= seg or i == len(pts) - 1:
            f = _clamp01(budget / seg) if seg > 1e-6 else 0.0
            return [_round4(a[0] + (b[0] - a[0]) * f), _round4(a[1] + (b[1] - a[1]) * f)]
        budget -= seg
    return list(pts[-1])


def partial_polyline_2d(pts: list[list[float]], progress: float, close: bool = False) -> list[list[float]]:
    closed = [*pts, pts[0]] if (close and len(pts) > 2) else list(pts)
    p = _clamp01(progress)
    if len(closed) < 2 or p <= 0.002:
        return []
    if p >= 0.999:
        return closed
    budget = _polyline_length_2d(closed) * p
    out: list[list[float]] = [closed[0]]
    for i in range(1, len(closed)):
        if budget <= 0:
            break
        a, b = closed[i - 1], closed[i]
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if seg <= 1e-6:
            continue
        if budget >= seg:
            out.append(b)
            budget -= seg
        else:
            f = budget / seg
            out.append([_round4(a[0] + (b[0] - a[0]) * f), _round4(a[1] + (b[1] - a[1]) * f)])
            budget = 0.0
    return out


def _normalize_primitives(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for part in parts:
        prim = part.get("primitive")
        if prim == "slab_stack":
            layers = max(1, int(part.get("layers") or 1))
            layer_dz = float(part.get("layerDz") or 5)
            gap_dz = float(part.get("gapDz") or 2)
            step_z = layer_dz + gap_dz
            for i in range(layers):
                flat.append({
                    **part,
                    "id": f"{part['id']}_L{i + 1}",
                    "parentPartId": part["id"],
                    "primitive": "slab",
                    "z": float(part["z"]) + i * step_z,
                    "dz": layer_dz,
                })
        elif prim == "ticks":
            count = max(1, int(part.get("count") or 1))
            step_x = float(part.get("stepX") or 0)
            step_y = float(part.get("stepY") or 0)
            for i in range(count):
                flat.append({
                    **part,
                    "id": f"{part['id']}_{i + 1}",
                    "parentPartId": part["id"],
                    "primitive": "slab",
                    "x": float(part["x"]) + i * step_x,
                    "y": float(part["y"]) + i * step_y,
                })
        else:
            flat.append({**part, "parentPartId": part.get("id")})
    return flat


def build_machine_scene(
    spec: dict[str, Any],
    time: float,
    *,
    origin_x: float | None = None,
    origin_y: float | None = None,
    scale: float | None = None,
    theme: str = "dark",
    line_width: float = 2.6,
    fps: int | None = None,
    force_full_reveal: bool = False,
) -> dict[str, Any]:
    state = machine_state_at(spec, time, fps=fps)
    layout_cfg = spec.get("layout") or {}
    ox = float(origin_x) if _finite(origin_x) else (float(layout_cfg["originX"]) if _finite(layout_cfg.get("originX")) else 500.0)
    oy = float(origin_y) if _finite(origin_y) else (float(layout_cfg["originY"]) if _finite(layout_cfg.get("originY")) else 760.0)
    sc = float(scale) if _finite(scale) else (float(layout_cfg["scale"]) if _finite(layout_cfg.get("scale")) else 1.35)
    th = "light" if theme == "light" else "dark"
    roles = MACHINE_ROLES[th]

    def proj(x: float, y: float, z: float) -> list[float]:
        return iso_project_point(x, y, z, origin_x=ox, origin_y=oy, scale=sc)

    model = expand_machine_model(spec)
    flat_parts = _normalize_primitives(model["parts"])
    rev = 1.0 if force_full_reveal else float(state["revealProgress"])
    active_tag_set = set(state["activeTags"])
    active_step = state["activeStep"]
    active_tint = "intake" if (active_step and active_step.get("motion", {}).get("tint") == "intake") else "active"

    ops: list[dict[str, Any]] = []
    all_vertices: list[list[float]] = []

    def push_verts(pts: list[list[float]]) -> None:
        for pt in pts:
            all_vertices.append([pt[0], pt[1]])

    for seq, part in enumerate(flat_parts):
        base_alpha = _clamp01(part["alpha"]) if _finite(part.get("alpha")) else 1.0
        if base_alpha <= 0 or rev <= 0:
            continue
        is_cutaway = bool(part.get("cutaway"))
        is_highlighted = (part.get("tag") in active_tag_set) and not is_cutaway
        role_name = active_tint if is_highlighted else (part.get("role") or "housing")
        c = roles.get(role_name, roles["housing"])
        layer_rank = LAYER_RANK.get(part.get("layer") or "mid", 1)
        fill_ramp = _clamp01((rev - 0.22) / 0.78)
        fill_alpha = _round4(base_alpha * fill_ramp)
        prim = part.get("primitive")

        if prim == "slab":
            x, y, z = float(part["x"]), float(part["y"]), float(part["z"])
            dx, dy, dz = float(part["dx"]), float(part["dy"]), float(part["dz"])
            p100 = proj(x + dx, y, z)
            p010 = proj(x, y + dy, z)
            p110 = proj(x + dx, y + dy, z)
            p001 = proj(x, y, z + dz)
            p101 = proj(x + dx, y, z + dz)
            p011 = proj(x, y + dy, z + dz)
            p111 = proj(x + dx, y + dy, z + dz)
            left_f = [[p010[0], p010[1]], [p110[0], p110[1]], [p111[0], p111[1]], [p011[0], p011[1]]]
            right_f = [[p100[0], p100[1]], [p110[0], p110[1]], [p111[0], p111[1]], [p101[0], p101[1]]]
            top_f = [[p001[0], p001[1]], [p101[0], p101[1]], [p111[0], p111[1]], [p011[0], p011[1]]]
            push_verts([*left_f, *right_f, *top_f])
            ops.append({
                "kind": "solid",
                "partId": part["id"],
                "parentPartId": part["parentPartId"],
                "tag": part.get("tag") or "",
                "layer": part.get("layer") or "mid",
                "layerRank": layer_rank,
                "depth": _round4(x + dx * 0.5 + y + dy * 0.5 + z + dz * 0.5),
                "seq": seq,
                "cutaway": is_cutaway,
                "fillAlpha": fill_alpha,
                "strokeAlpha": base_alpha,
                "lineWidth": line_width * 1.25 if is_highlighted else line_width,
                "reveal": rev,
                "faces": [
                    {"points": left_f, "fill": c["left"], "stroke": c["stroke"], "close": True},
                    {"points": right_f, "fill": c["right"], "stroke": c["stroke"], "close": True},
                    {"points": top_f, "fill": c["top"], "stroke": c["stroke"], "close": True},
                ],
            })
        elif prim == "poly3d" and isinstance(part.get("faces3d"), list):
            cx = cy = cz = 0.0
            cnt = 0
            faces = []
            for fi, f3 in enumerate(part["faces3d"]):
                pts2 = []
                for vx, vy, vz in f3:
                    cx += float(vx)
                    cy += float(vy)
                    cz += float(vz)
                    cnt += 1
                    p = proj(float(vx), float(vy), float(vz))
                    pts2.append([p[0], p[1]])
                push_verts(pts2)
                faces.append({
                    "points": pts2,
                    "fill": c["top"] if fi == 0 else (c["left"] if fi % 2 == 1 else c["right"]),
                    "stroke": c["stroke"],
                    "close": True,
                })
            if faces:
                ops.append({
                    "kind": "solid",
                    "partId": part["id"],
                    "parentPartId": part["parentPartId"],
                    "tag": part.get("tag") or "",
                    "layer": part.get("layer") or "mid",
                    "layerRank": layer_rank,
                    "depth": _round4((cx + cy + cz) / cnt) if cnt else 0.0,
                    "seq": seq,
                    "cutaway": is_cutaway,
                    "fillAlpha": fill_alpha,
                    "strokeAlpha": base_alpha,
                    "lineWidth": line_width,
                    "reveal": rev,
                    "faces": faces,
                })
        elif prim in ("cylinder", "ring"):
            segs = max(12, int(part.get("segments") or 24))
            r_outer = float(part.get("rOuter") or 52.0) if prim == "ring" else float(part.get("r") or 32.0)
            h = float(part.get("h") or 20.0)
            px0, py0, pz0 = float(part["x"]), float(part["y"]), float(part["z"])
            top_pts: list[list[float]] = []
            bot_pts: list[list[float]] = []
            for i in range(segs):
                ang = (i / segs) * math.tau
                px = px0 + math.cos(ang) * r_outer
                py = py0 + math.sin(ang) * r_outer
                tp = proj(px, py, pz0 + h)
                bp = proj(px, py, pz0)
                top_pts.append([tp[0], tp[1]])
                bot_pts.append([bp[0], bp[1]])
            min_i = min(range(segs), key=lambda idx: top_pts[idx][0])
            max_i = max(range(segs), key=lambda idx: top_pts[idx][0])
            front_arc: list[list[float]] = []
            cur = min_i
            while len(front_arc) <= segs:
                front_arc.append(bot_pts[cur])
                if cur == max_i:
                    break
                cur = (cur + 1) % segs
            side_poly = [top_pts[min_i], *front_arc, top_pts[max_i]]
            push_verts([*side_poly, *top_pts])
            blade_lines: list[list[list[float]]] = []
            blades = int(part.get("blades") or 0)
            if prim == "ring" and blades > 0:
                r_in = float(part.get("rInner") or (r_outer * 0.36))
                spin_rad = math.radians(float(state["spinDeg"]) if is_highlighted else 18.0)
                for b in range(blades):
                    ang = spin_rad + (b / blades) * math.tau
                    p0 = proj(px0 + math.cos(ang) * r_in, py0 + math.sin(ang) * r_in, pz0 + h)
                    p1 = proj(
                        px0 + math.cos(ang + 0.28) * (r_outer * 0.88),
                        py0 + math.sin(ang + 0.28) * (r_outer * 0.88),
                        pz0 + h,
                    )
                    blade_lines.append([[p0[0], p0[1]], [p1[0], p1[1]]])
            ops.append({
                "kind": "solid",
                "partId": part["id"],
                "parentPartId": part["parentPartId"],
                "tag": part.get("tag") or "",
                "layer": part.get("layer") or "mid",
                "layerRank": layer_rank,
                "depth": _round4(px0 + py0 + pz0 + h * 0.5),
                "seq": seq,
                "cutaway": is_cutaway,
                "fillAlpha": fill_alpha,
                "strokeAlpha": base_alpha,
                "lineWidth": line_width,
                "reveal": rev,
                "faces": [
                    {"points": side_poly, "fill": c["left"], "stroke": c["stroke"], "close": False},
                    {"points": top_pts, "fill": c["top"], "stroke": c["stroke"], "close": True},
                ],
                "bladeLines": blade_lines,
                "bladeStroke": roles["active"]["top"],
            })
        elif prim in ("wire", "coil"):
            pts3d = part.get("points") or []
            if prim == "coil":
                turns = max(2, int(part.get("turns") or 6))
                steps = turns * 12
                length = float(part.get("length") or 120.0)
                rad = float(part.get("radius") or 12.0)
                axis = part.get("axis") or "x"
                px0, py0, pz0 = float(part["x"]), float(part["y"]), float(part["z"])
                pts3d = []
                for i in range(steps + 1):
                    u = i / steps
                    ang = u * turns * math.tau
                    along = u * length
                    c1 = math.cos(ang) * rad
                    c2 = math.sin(ang) * rad
                    pts3d.append([
                        px0 + along if axis == "x" else px0 + c1,
                        py0 + along if axis == "y" else (py0 + c1 if axis == "x" else py0 + c2),
                        pz0 + along if axis == "z" else pz0 + c2,
                    ])
            if len(pts3d) >= 2:
                pts2d = []
                for px, py, pz in pts3d:
                    p = proj(float(px), float(py), float(pz))
                    pts2d.append([p[0], p[1]])
                push_verts(pts2d)
                avg_depth = sum(float(p[0]) + float(p[1]) + float(p[2]) for p in pts3d) / len(pts3d)
                ops.append({
                    "kind": "wire",
                    "partId": part["id"],
                    "parentPartId": part["parentPartId"],
                    "tag": part.get("tag") or "",
                    "layer": part.get("layer") or "mid",
                    "layerRank": layer_rank,
                    "depth": _round4(avg_depth),
                    "seq": seq,
                    "stroke": c["top"],
                    "strokeAlpha": base_alpha,
                    "lineWidth": float(part.get("width") or 3.2) * (1.25 if is_highlighted else 1.0),
                    "reveal": rev,
                    "points": pts2d,
                })

    if active_step is not None and rev > 0.25:
        mot = active_step["motion"]
        mkind = mot["kind"]
        mpath = mot.get("path")
        if mkind == "packet_flow" and mpath and mpath in model["paths"] and state["packetProgress"] >= 0:
            path2d = []
            for px, py, pz in model["paths"][mpath]:
                p = proj(float(px), float(py), float(pz))
                path2d.append([p[0], p[1]])
            push_verts(path2d)
            dots = [point_along_polyline_2d(path2d, (state["packetProgress"] + off) % 1.0) for off in (0.0, 0.33, 0.66)]
            ops.append({
                "kind": "packets",
                "partId": f"{active_step['id']}_packets",
                "tag": active_step["activeTags"][0],
                "layer": "overlay",
                "layerRank": LAYER_RANK["overlay"],
                "depth": 1e6,
                "seq": len(flat_parts) + 1,
                "path": path2d,
                "dots": dots,
                "radius": 6,
                "fill": MACHINE_PALETTE["paper"] if mot.get("tint") == "intake" else MACHINE_PALETTE["salmon"],
                "stroke": MACHINE_PALETTE["ink"] if th == "dark" else MACHINE_PALETTE["paper"],
                "alpha": state["highlightMix"],
            })
        elif mkind == "airflow_stream" and mpath and mpath in model["paths"] and state["airflowPhase"] >= 0:
            base3d = model["paths"][mpath]
            streams = []
            for si, dy_off in enumerate((-14.0, 0.0, 14.0)):
                pts2d = []
                for px, py, pz in base3d:
                    p = proj(float(px), float(py) + dy_off, float(pz))
                    pts2d.append([p[0], p[1]])
                push_verts(pts2d)
                bead = point_along_polyline_2d(pts2d, (state["airflowPhase"] + si * 0.28) % 1.0)
                streams.append({"points": pts2d, "bead": bead})
            ops.append({
                "kind": "airflow",
                "partId": f"{active_step['id']}_airflow",
                "tag": active_step["activeTags"][0],
                "layer": "overlay",
                "layerRank": LAYER_RANK["overlay"],
                "depth": 1e6 + 1,
                "seq": len(flat_parts) + 2,
                "streams": streams,
                "stroke": MACHINE_PALETTE["salmon"] if mot.get("tint") == "active" else MACHINE_PALETTE["blush"],
                "beadFill": MACHINE_PALETTE["paper"],
                "alpha": state["highlightMix"],
            })

    ops.sort(key=lambda item: (item["layerRank"], item["depth"], item["seq"]))

    if all_vertices:
        xs = [v[0] for v in all_vertices]
        ys = [v[1] for v in all_vertices]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        bounds = {
            "x": _round4(min_x),
            "y": _round4(min_y),
            "w": _round4(max(1.0, max_x - min_x)),
            "h": _round4(max(1.0, max_y - min_y)),
        }
    else:
        bounds = {"x": ox, "y": oy, "w": 0.0, "h": 0.0}

    world_projected: dict[str, dict[str, float]] = {}
    for key, coords in model["world"].items():
        if isinstance(coords, (list, tuple)) and len(coords) == 3:
            p = proj(float(coords[0]), float(coords[1]), float(coords[2]))
            world_projected[key] = {"x": p[0], "y": p[1], "depth": p[2]}

    return {
        "state": state,
        "theme": th,
        "origin": {"x": ox, "y": oy, "scale": sc},
        "ops": ops,
        "bounds": bounds,
        "vertices": all_vertices,
        "world": world_projected,
    }


def _rasterize_op_mask(op: dict[str, Any], w: int, h: int) -> np.ndarray:
    mask = np.zeros((h, w), dtype=np.uint8)
    if op["kind"] == "solid":
        for face in op["faces"]:
            pts = face["points"]
            if len(pts) >= 3:
                arr = np.round(np.array(pts, dtype=np.float32)).astype(np.int32)
                cv2.fillPoly(mask, [arr], 255)
    elif op["kind"] == "wire":
        pts = op["points"]
        if len(pts) >= 2:
            arr = np.round(np.array(pts, dtype=np.float32)).astype(np.int32)
            thickness = max(3, int(round(float(op["lineWidth"]) * 2)))
            cv2.polylines(mask, [arr], False, 255, thickness)
    return mask


def compute_occlusion_report(
    spec: dict[str, Any],
    *,
    max_occlusion: float | None = None,
    theme: str = "dark",
    origin_x: float | None = None,
    origin_y: float | None = None,
    scale: float | None = None,
) -> dict[str, Any]:
    """Compute true projected-polygon coverage-mask occlusion per step and active tag."""
    env = layout_p.safe_envelope("content")
    w, h = int(env["w"]), int(env["h"])
    sample_t = (float(spec["start"]) + float(spec["end"])) * 0.5
    graph = build_machine_scene(
        spec,
        sample_t,
        origin_x=origin_x,
        origin_y=origin_y,
        scale=scale,
        theme=theme,
        fps=int(env["fps"]),
        force_full_reveal=True,
    )
    drawable_ops = [op for op in graph["ops"] if op["kind"] in ("solid", "wire")]
    masks = [_rasterize_op_mask(op, w, h) for op in drawable_ops]

    spec_qa_max = (spec.get("qa") or {}).get("maxOcclusion")
    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for step in spec["steps"]:
        step_max = step.get("maxOcclusion")
        if _finite(max_occlusion):
            threshold = _clamp01(float(max_occlusion))
        elif _finite(step_max):
            threshold = _clamp01(float(step_max))
        elif _finite(spec_qa_max):
            threshold = _clamp01(float(spec_qa_max))
        else:
            threshold = DEFAULT_MAX_OCCLUSION

        for tag in step["activeTags"]:
            solid_indices = [
                i for i, op in enumerate(drawable_ops)
                if op["tag"] == tag and op["kind"] == "solid" and not op.get("cutaway")
            ]
            target_indices = solid_indices or [
                i for i, op in enumerate(drawable_ops) if op["tag"] == tag
            ]
            if not target_indices:
                errors.append(f'{step["id"]}: activeTag "{tag}" produced zero projected geometry')
                results.append({
                    "stepId": step["id"], "tag": tag, "areaPx": 0,
                    "occludedRatio": 1.0, "maxOcclusion": _round4(threshold), "ok": False,
                })
                continue

            union_mask = np.zeros((h, w), dtype=bool)
            best_visibility = np.zeros((h, w), dtype=np.float32)

            for ti in target_indices:
                t_bool = masks[ti] > 0
                if not np.any(t_bool):
                    continue
                union_mask |= t_bool
                vis = np.zeros((h, w), dtype=np.float32)
                vis[t_bool] = 1.0
                for fi in range(ti + 1, len(drawable_ops)):
                    fg = drawable_ops[fi]
                    if fg["kind"] != "solid" or fg["tag"] == tag:
                        continue
                    fg_alpha = float(fg.get("fillAlpha", 0.0))
                    if fg_alpha <= 0.01:
                        continue
                    fg_overlap = t_bool & (masks[fi] > 0)
                    if np.any(fg_overlap):
                        vis[fg_overlap] *= (1.0 - fg_alpha)
                best_visibility = np.maximum(best_visibility, vis)

            area_px = int(np.count_nonzero(union_mask))
            if area_px == 0:
                occluded_ratio = 1.0
                ok = False
                errors.append(f'{step["id"]}: activeTag "{tag}" has 0 visible pixels inside the {w}x{h} canvas')
            else:
                occluded_ratio = float(np.mean(1.0 - best_visibility[union_mask]))
                ok = occluded_ratio <= threshold + 1e-6
                if not ok:
                    errors.append(
                        f'{step["id"]}: activeTag "{tag}" is {occluded_ratio * 100:.1f}% occluded by foreground geometry '
                        f'(max allowed {threshold * 100:.1f}%)'
                    )
            results.append({
                "stepId": step["id"],
                "tag": tag,
                "areaPx": area_px,
                "occludedRatio": _round4(occluded_ratio),
                "maxOcclusion": _round4(threshold),
                "ok": ok,
            })

    return {
        "bounds": graph["bounds"],
        "results": results,
        "errors": errors,
    }


def _pt_rect_dist_sq(px: float, py: float, rx0: float, ry0: float, rx1: float, ry1: float) -> float:
    dx = max(rx0 - px, 0.0, px - rx1)
    dy = max(ry0 - py, 0.0, py - ry1)
    return dx * dx + dy * dy


def _pt_seg_dist_sq(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    dx, dy = bx - ax, by - ay
    len_sq = dx * dx + dy * dy
    if len_sq <= 1e-12:
        return (px - ax) ** 2 + (py - ay) ** 2
    u = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / len_sq))
    cx, cy = ax + u * dx, ay + u * dy
    return (px - cx) ** 2 + (py - cy) ** 2


def _seg_intersects_rect(ax: float, ay: float, bx: float, by: float, rx0: float, ry0: float, rx1: float, ry1: float) -> bool:
    dx, dy = bx - ax, by - ay
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, ax - rx0), (dx, rx1 - ax), (-dy, ay - ry0), (dy, ry1 - ay)):
        if abs(p) <= 1e-12:
            if q < 0.0:
                return False
        else:
            r = q / p
            if p < 0.0:
                if r > t1:
                    return False
                if r > t0:
                    t0 = r
            else:
                if r < t0:
                    return False
                if r < t1:
                    t1 = r
    return t0 <= t1


def _dist_seg_to_rect(ax: float, ay: float, bx: float, by: float, rx0: float, ry0: float, rx1: float, ry1: float) -> float:
    if _seg_intersects_rect(ax, ay, bx, by, rx0, ry0, rx1, ry1):
        return 0.0
    best_sq = min(
        _pt_rect_dist_sq(ax, ay, rx0, ry0, rx1, ry1),
        _pt_rect_dist_sq(bx, by, rx0, ry0, rx1, ry1),
        _pt_seg_dist_sq(rx0, ry0, ax, ay, bx, by),
        _pt_seg_dist_sq(rx1, ry0, ax, ay, bx, by),
        _pt_seg_dist_sq(rx1, ry1, ax, ay, bx, by),
        _pt_seg_dist_sq(rx0, ry1, ax, ay, bx, by),
    )
    return math.sqrt(max(0.0, best_sq))


def _point_in_poly(px: float, py: float, poly: list[list[float]]) -> bool:
    inside = False
    n = len(poly)
    if n < 3:
        return False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i][0], poly[i][1]
        xj, yj = poly[j][0], poly[j][1]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / ((yj - yi) or 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def _polyline_overlaps_rect(pts: list[list[float]], rad: float, rx0: float, ry0: float, rx1: float, ry1: float) -> bool:
    if not pts:
        return False
    if len(pts) == 1:
        return _pt_rect_dist_sq(pts[0][0], pts[0][1], rx0, ry0, rx1, ry1) <= rad * rad
    for i in range(len(pts) - 1):
        if _dist_seg_to_rect(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], rx0, ry0, rx1, ry1) <= rad:
            return True
    return False


def _poly_overlaps_rect(poly: list[list[float]], rad: float, rx0: float, ry0: float, rx1: float, ry1: float) -> bool:
    if len(poly) < 3:
        return _polyline_overlaps_rect(poly, rad, rx0, ry0, rx1, ry1)
    r_sq = rad * rad
    for vx, vy in poly:
        if _pt_rect_dist_sq(vx, vy, rx0, ry0, rx1, ry1) <= r_sq:
            return True
    for qx, qy in (
        (rx0, ry0),
        (rx1, ry0),
        (rx1, ry1),
        (rx0, ry1),
        ((rx0 + rx1) * 0.5, (ry0 + ry1) * 0.5),
    ):
        if _point_in_poly(qx, qy, poly):
            return True
    n = len(poly)
    for i in range(n):
        ax, ay = poly[i][0], poly[i][1]
        bx, by = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        if _dist_seg_to_rect(ax, ay, bx, by, rx0, ry0, rx1, ry1) <= rad:
            return True
    return False


def compute_envelope_report(
    spec: dict[str, Any],
    *,
    zone: str = "content",
    check_platform_ui: bool = True,
    origin_x: float | None = None,
    origin_y: float | None = None,
    scale: float | None = None,
    theme: str = "dark",
) -> dict[str, Any]:
    """Conservative, deterministic X04 safe-zone & right-rail envelope check.

    Audits static cutaway geometry AND every step across its active 30fps window
    plus full swept trajectories for `packets` (path + dots + stroke), `airflow`
    (all 3 streamlines + beads + stroke), `wire` (including active 1.25x width),
    and rotating `bladeLines` (`spin`), without per-frame rasterization.
    """
    env = layout_p.safe_envelope(zone, check_platform_ui=check_platform_ui)
    fps = int(env["fps"])
    sx0, sx1 = float(env["x"][0]), float(env["x"][1])
    sy0, sy1 = float(env["y"][0]), float(env["y"][1])
    dead_y = float(env["nothing_important_below_y"])
    rail = env.get("platform_right_rail")
    rx0 = float(rail["x"]) if rail else 0.0
    ry0 = float(rail["y"]) if rail else 0.0
    rx1 = float(rail["x"] + rail["w"]) if rail else 0.0
    ry1 = float(rail["y"] + rail["h"]) if rail else 0.0

    min_x, min_y = float("inf"), float("inf")
    max_x, max_y = float("-inf"), float("-inf")
    rail_hits: list[tuple[str, str]] = []
    safe_hits: list[tuple[str, str]] = []
    seen_rail: set[tuple[str, str]] = set()
    seen_safe: set[tuple[str, str]] = set()

    def record_extent(scope: str, label: str, x0: float, y0: float, x1: float, y1: float) -> None:
        nonlocal min_x, min_y, max_x, max_y
        min_x = min(min_x, x0)
        min_y = min(min_y, y0)
        max_x = max(max_x, x1)
        max_y = max(max_y, y1)
        if (x0 < sx0 - 1e-3 or x1 > sx1 + 1e-3 or y0 < sy0 - 1e-3 or y1 > sy1 + 1e-3) and (scope, label) not in seen_safe:
            seen_safe.add((scope, label))
            safe_hits.append((
                scope,
                f"{label} [{x0:.1f}..{x1:.1f}, {y0:.1f}..{y1:.1f}] exceeds dynamic {zone} safe zone "
                f"[{sx0:.0f}..{sx1:.0f}, {sy0:.0f}..{sy1:.0f}]",
            ))
        if y1 > dead_y + 1e-3 and (scope, f"{label}:dead") not in seen_safe:
            seen_safe.add((scope, f"{label}:dead"))
            safe_hits.append((
                scope,
                f"{label} crosses nothing_important_below_y ({y1:.1f} > {dead_y:.0f})",
            ))

    def record_rail(scope: str, label: str) -> None:
        if rail is not None and (scope, label) not in seen_rail:
            seen_rail.add((scope, label))
            rail_hits.append((
                scope,
                f"{label} overlaps PLATFORM_RIGHT_RAIL (x={rx0:.0f}..{rx1:.0f}, y={ry0:.0f}..{ry1:.0f})",
            ))

    def inspect_ops(scope: str, ops: list[dict[str, Any]], *, include_swept_paths: bool) -> None:
        for op in ops:
            kind = op["kind"]
            pid = op.get("partId") or kind
            if kind == "solid":
                r_stroke = max(0.0, float(op.get("lineWidth") or 0.0) * 0.5)
                for face in op["faces"]:
                    pts = face["points"]
                    if not pts:
                        continue
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    record_extent(scope, f"solid {pid}", min(xs) - r_stroke, min(ys) - r_stroke, max(xs) + r_stroke, max(ys) + r_stroke)
                    if rail is not None:
                        hit = (
                            _poly_overlaps_rect(pts, r_stroke, rx0, ry0, rx1, ry1)
                            if face.get("close") and float(op.get("fillAlpha", 0.0)) > 0.01
                            else _polyline_overlaps_rect(pts, r_stroke, rx0, ry0, rx1, ry1)
                        )
                        if hit:
                            record_rail(scope, f"solid {pid}")
                if op.get("bladeLines"):
                    r_blade = max(0.5, float(op.get("lineWidth") or 2.6) * 1.15 * 0.5)
                    for seg in op["bladeLines"]:
                        xs = [p[0] for p in seg]
                        ys = [p[1] for p in seg]
                        record_extent(scope, f"blades {pid}", min(xs) - r_blade, min(ys) - r_blade, max(xs) + r_blade, max(ys) + r_blade)
                        if rail is not None and _polyline_overlaps_rect(seg, r_blade, rx0, ry0, rx1, ry1):
                            record_rail(scope, f"blades {pid}")
            elif kind == "wire":
                pts = op["points"]
                if len(pts) >= 2:
                    r_wire = max(0.5, float(op.get("lineWidth") or 3.2) * 0.5)
                    xs = [p[0] for p in pts]
                    ys = [p[1] for p in pts]
                    record_extent(scope, f"wire {pid}", min(xs) - r_wire, min(ys) - r_wire, max(xs) + r_wire, max(ys) + r_wire)
                    if rail is not None and _polyline_overlaps_rect(pts, r_wire, rx0, ry0, rx1, ry1):
                        record_rail(scope, f"wire {pid}")
            elif kind == "packets":
                # Packet circle has radius `op["radius"]` (6px) + strokeWidth 2px (1px outward)
                r_pkt = float(op.get("radius") or 6.0) + 1.0
                if include_swept_paths and len(op.get("path") or []) >= 2:
                    path_pts = op["path"]
                    xs = [p[0] for p in path_pts]
                    ys = [p[1] for p in path_pts]
                    record_extent(scope, f"packet_flow path ({pid})", min(xs) - r_pkt, min(ys) - r_pkt, max(xs) + r_pkt, max(ys) + r_pkt)
                    if rail is not None and _polyline_overlaps_rect(path_pts, r_pkt, rx0, ry0, rx1, ry1):
                        record_rail(scope, f"packet_flow path ({pid})")
                for dot in op.get("dots") or []:
                    dx, dy = float(dot[0]), float(dot[1])
                    record_extent(scope, f"packet particle ({pid})", dx - r_pkt, dy - r_pkt, dx + r_pkt, dy + r_pkt)
                    if rail is not None and _pt_rect_dist_sq(dx, dy, rx0, ry0, rx1, ry1) <= r_pkt * r_pkt:
                        record_rail(scope, f"packet_flow path ({pid})")
            elif kind == "airflow":
                # Airflow streamline has strokeWidth 2.4px (1.2px half) and moving bead radius 4.5px
                r_stream = 1.2
                r_bead = 4.5
                r_swept = max(r_stream, r_bead)
                for si, stream in enumerate(op.get("streams") or []):
                    s_pts = stream.get("points") or []
                    if include_swept_paths and len(s_pts) >= 2:
                        xs = [p[0] for p in s_pts]
                        ys = [p[1] for p in s_pts]
                        record_extent(scope, f"airflow_stream[{si}] ({pid})", min(xs) - r_swept, min(ys) - r_swept, max(xs) + r_swept, max(ys) + r_swept)
                        if rail is not None and _polyline_overlaps_rect(s_pts, r_swept, rx0, ry0, rx1, ry1):
                            record_rail(scope, f"airflow_stream ({pid})")
                    bead = stream.get("bead")
                    if bead:
                        bx, by = float(bead[0]), float(bead[1])
                        record_extent(scope, f"airflow bead[{si}] ({pid})", bx - r_bead, by - r_bead, bx + r_bead, by + r_bead)
                        if rail is not None and _pt_rect_dist_sq(bx, by, rx0, ry0, rx1, ry1) <= r_bead * r_bead:
                            record_rail(scope, f"airflow_stream ({pid})")

    # 1. Base static cutaway envelope
    mid_t = (float(spec["start"]) + float(spec["end"])) * 0.5
    base_graph = build_machine_scene(
        spec, mid_t, origin_x=origin_x, origin_y=origin_y, scale=scale, theme=theme, fps=fps, force_full_reveal=True,
    )
    inspect_ops("base", base_graph["ops"], include_swept_paths=True)

    # 2. Every step audited across its active window (analytical swept trajectory + 30fps grid samples)
    for step in spec["steps"]:
        sid = step["id"]
        st_start = float(step["start"])
        st_end = float(step["end"])
        step_mid = (st_start + st_end) * 0.5

        # Swept analytical check with force_full_reveal=True so motion paths are checked even during early reveal
        swept_graph = build_machine_scene(
            spec, step_mid, origin_x=origin_x, origin_y=origin_y, scale=scale, theme=theme, fps=fps, force_full_reveal=True,
        )
        inspect_ops(sid, swept_graph["ops"], include_swept_paths=True)

        # Deterministic 30fps frame-grid sampling across the step's active window (covers spin angles & exact frame states)
        f_first = int(math.ceil((st_start - 1e-9) * fps))
        f_last = int(math.floor((st_end - 1e-6) * fps))
        if f_last >= f_first:
            total_frames = f_last - f_first + 1
            stride = max(1, total_frames // 24)
            frame_indices = sorted({*range(f_first, f_last + 1, stride), f_first, f_last})
            for f_idx in frame_indices:
                t_frame = f_idx / fps
                fr_graph = build_machine_scene(
                    spec, t_frame, origin_x=origin_x, origin_y=origin_y, scale=scale, theme=theme, fps=fps,
                )
                motion_ops = [
                    op for op in fr_graph["ops"]
                    if op["kind"] in ("packets", "airflow") or (op["kind"] == "solid" and op.get("bladeLines"))
                ]
                if motion_ops:
                    inspect_ops(sid, motion_ops, include_swept_paths=False)

    errors = [msg for _, msg in safe_hits] + [msg for _, msg in rail_hits]
    bounds = (
        {
            "x": _round4(min_x),
            "y": _round4(min_y),
            "w": _round4(max(1.0, max_x - min_x)),
            "h": _round4(max(1.0, max_y - min_y)),
        }
        if min_x < float("inf")
        else base_graph["bounds"]
    )
    return {
        "ok": len(errors) == 0,
        "bounds": bounds,
        "errors": errors,
    }


def _fill_poly_cv(fr: np.ndarray, pts: list[list[float]], hex_col: str, alpha: float) -> None:
    if alpha <= 0.004 or len(pts) < 3:
        return
    rgb = HEX_TO_RGB[hex_col]
    arr = np.round(np.array(pts, dtype=np.float32)).astype(np.int32)
    x0 = max(0, int(arr[:, 0].min()) - 2)
    y0 = max(0, int(arr[:, 1].min()) - 2)
    x1 = min(fr.shape[1], int(arr[:, 0].max()) + 3)
    y1 = min(fr.shape[0], int(arr[:, 1].max()) + 3)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    shifted = arr - np.array([[x0, y0]], dtype=np.int32)
    cv2.fillPoly(mask, [shifted], 255, lineType=cv2.LINE_AA)
    m = (mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    roi[:] = roi * (1.0 - m) + np.array(rgb, dtype=np.float32) * m


def _stroke_polyline_cv(
    fr: np.ndarray,
    pts: list[list[float]],
    hex_col: str,
    width: float,
    alpha: float,
    dashed: bool = False,
) -> None:
    if alpha <= 0.004 or len(pts) < 2:
        return
    rgb = HEX_TO_RGB[hex_col]
    arr = np.round(np.array(pts, dtype=np.float32)).astype(np.int32)
    pad = max(4, int(math.ceil(width)) + 3)
    x0 = max(0, int(arr[:, 0].min()) - pad)
    y0 = max(0, int(arr[:, 1].min()) - pad)
    x1 = min(fr.shape[1], int(arr[:, 0].max()) + pad + 1)
    y1 = min(fr.shape[0], int(arr[:, 1].max()) + pad + 1)
    if x1 <= x0 or y1 <= y0:
        return
    mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    shifted = arr - np.array([[x0, y0]], dtype=np.int32)
    thickness = max(1, int(round(width)))
    if not dashed:
        cv2.polylines(mask, [shifted], False, 255, thickness, lineType=cv2.LINE_AA)
    else:
        for i in range(1, len(pts)):
            a, b = pts[i - 1], pts[i]
            seg_len = math.hypot(b[0] - a[0], b[1] - a[1])
            if seg_len <= 1e-4:
                continue
            pos = 0.0
            while pos < seg_len:
                end_p = min(seg_len, pos + 8.0)
                f0, f1 = pos / seg_len, end_p / seg_len
                p0 = (int(round(a[0] + (b[0] - a[0]) * f0)) - x0, int(round(a[1] + (b[1] - a[1]) * f0)) - y0)
                p1 = (int(round(a[0] + (b[0] - a[0]) * f1)) - x0, int(round(a[1] + (b[1] - a[1]) * f1)) - y0)
                cv2.line(mask, p0, p1, 255, thickness, lineType=cv2.LINE_AA)
                pos += 14.0
    m = (mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    roi[:] = roi * (1.0 - m) + np.array(rgb, dtype=np.float32) * m


def _draw_dot_cv(fr: np.ndarray, cx: float, cy: float, radius: int, fill_hex: str, stroke_hex: str, alpha: float) -> None:
    if alpha <= 0.004:
        return
    pad = radius + 4
    x0, y0 = max(0, int(cx) - pad), max(0, int(cy) - pad)
    x1, y1 = min(fr.shape[1], int(cx) + pad + 1), min(fr.shape[0], int(cy) + pad + 1)
    if x1 <= x0 or y1 <= y0:
        return
    pc = (int(round(cx)) - x0, int(round(cy)) - y0)
    fill_mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    cv2.circle(fill_mask, pc, radius, 255, -1, lineType=cv2.LINE_AA)
    m = (fill_mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi = fr[y0:y1, x0:x1]
    roi[:] = roi * (1.0 - m) + np.array(HEX_TO_RGB[fill_hex], dtype=np.float32) * m

    ring_mask = np.zeros((y1 - y0, x1 - x0), dtype=np.uint8)
    cv2.circle(ring_mask, pc, radius, 255, 2, lineType=cv2.LINE_AA)
    rm = (ring_mask.astype(np.float32) / 255.0)[..., None] * float(alpha)
    roi[:] = roi * (1.0 - rm) + np.array(HEX_TO_RGB[stroke_hex], dtype=np.float32) * rm


def draw_machine_diagram(
    fr: np.ndarray,
    spec: dict[str, Any],
    time: float,
    *,
    direction: dict[str, Any] | None = None,
    scene: int | None = None,
    copy_by_id: dict[str, str] | None = None,
    diagram_id: str | None = None,
    origin_x: float | None = None,
    origin_y: float | None = None,
    scale: float | None = None,
    theme: str = "dark",
    callout_y: float | None = None,
    note_y: float | None = None,
) -> dict[str, Any]:
    """Render a Machine Explainer cutaway diagram onto Engine P float32/uint8 frame `fr`."""
    is_u8 = fr.dtype.name == "uint8"
    work = fr.astype(np.float32) if is_u8 else fr

    check_platform = (spec.get("qa") or {}).get("checkPlatformUi") is not False
    env = layout_p.safe_envelope("content", check_platform_ui=check_platform)
    graph = build_machine_scene(
        spec,
        time,
        origin_x=origin_x,
        origin_y=origin_y,
        scale=scale,
        theme=theme,
        fps=int(env["fps"]),
    )
    if not graph["state"]["active"]:
        return graph

    for op in graph["ops"]:
        kind = op["kind"]
        if kind == "solid":
            for face in op["faces"]:
                _fill_poly_cv(work, face["points"], face["fill"], op["fillAlpha"])
                stroke_pts = partial_polyline_2d(face["points"], op["reveal"], face["close"])
                _stroke_polyline_cv(work, stroke_pts, face["stroke"], op["lineWidth"], op["strokeAlpha"], op["cutaway"])
            if op.get("bladeLines") and op["reveal"] > 0.25:
                for seg in op["bladeLines"]:
                    _stroke_polyline_cv(
                        work, seg, op["bladeStroke"], op["lineWidth"] * 1.15, op["strokeAlpha"] * op["reveal"], False
                    )
        elif kind == "wire":
            stroke_pts = partial_polyline_2d(op["points"], op["reveal"], False)
            _stroke_polyline_cv(work, stroke_pts, op["stroke"], op["lineWidth"], op["strokeAlpha"], False)
        elif kind == "packets" and op["alpha"] > 0.004:
            for dx, dy in op["dots"]:
                _draw_dot_cv(work, dx, dy, op["radius"], op["fill"], op["stroke"], op["alpha"])
        elif kind == "airflow" and op["alpha"] > 0.004:
            for stream in op["streams"]:
                _stroke_polyline_cv(work, stream["points"], op["stroke"], 2.4, op["alpha"], True)
                _draw_dot_cv(work, stream["bead"][0], stream["bead"][1], 5, op["beadFill"], op["stroke"], op["alpha"])

    resolved_id = diagram_id or spec.get("id") or "machine"
    if layout_p.is_capturing() and graph["bounds"]["w"] > 0 and graph["bounds"]["h"] > 0:
        layout_p.protect_box(f"{resolved_id}.diagram", graph["bounds"], kind="keep")

    active_step = graph["state"]["activeStep"]
    copies = copy_by_id or {}
    if active_step is not None and direction is not None and scene is not None:
        center_x = (env["x"][0] + env["x"][1]) * 0.5
        step_y = (
            float(callout_y)
            if _finite(callout_y)
            else min(env["y"][1] - 90.0, max(env["y"][0] + 60.0, graph["bounds"]["y"] + graph["bounds"]["h"] + 86.0))
        )
        txt_col = INK if theme == "light" else WHITE
        primary_id = active_step["copyIds"][0]
        primary_text = copies.get(primary_id)
        if _non_empty(primary_text):
            draw_directed_text(
                work,
                primary_text,
                direction=direction,
                scene=scene,
                role="label",
                element_id=primary_id,
                t=time,
                start=float(active_step["start"]),
                end=float(active_step["end"]),
                cx=center_x,
                cy=step_y,
                size=46,
                color=txt_col,
                theme=theme,
            )
        if active_step.get("evidence") == "illustrative" and _non_empty(active_step.get("illustrativeLabelId")):
            il_id = active_step["illustrativeLabelId"]
            il_text = copies.get(il_id)
            if _non_empty(il_text):
                badge_y = float(note_y) if _finite(note_y) else max(env["y"][0] + 44.0, graph["bounds"]["y"] - 68.0)
                draw_directed_text(
                    work,
                    il_text,
                    direction=direction,
                    scene=scene,
                    role="label",
                    element_id=il_id,
                    t=time,
                    start=float(active_step["start"]),
                    end=float(active_step["end"]),
                    cx=center_x,
                    cy=badge_y,
                    size=38,
                    color=DRED if theme == "light" else YEL,
                    theme=theme,
                )

    if is_u8:
        fr[:] = np.clip(np.round(work), 0, 255).astype(np.uint8)
    return graph
