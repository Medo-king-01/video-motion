"""Sample specs and project fixtures for the Machine Explainer suite.

The three builders below are shared by `test_machine_explainer.py` (X01-X03 validation) and
`test_machine_explainer_parity.py` (X04 safe zones, P/K/R parity, archetypes), so they live here
instead of being copy-pasted or imported across test modules.

No tests live here on purpose: pytest only collects `test_*.py`, so a `test_` function in this file
would never run - `tests/test_test_layout.py` fails if one appears.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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
