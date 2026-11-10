"""The operating contract may not drift from the renderer's capabilities.

`AGENTS.md` is what an agent reads before deciding what is possible, and
`medo-motion/templates/HYBRID.md` is copied into every hybrid project. When hybrid v2 shipped,
both still said simultaneous layers were out of scope — a shipped feature nobody doc-driven
agents would use. Fixing the prose once does not fix the class, so every capability the renderer
enforces is listed in `render_hybrid.CAPABILITIES` and marked in both contracts:

    <!-- CAP:alpha_layer -->

This test compares the sets in both directions: an implemented-but-unmarked capability fails,
and a marked capability that no longer exists fails too.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import render_hybrid  # noqa: E402

CONTRACTS = {
    "AGENTS.md": ROOT / "AGENTS.md",
    "templates/HYBRID.md": ROOT / "medo-motion" / "templates" / "HYBRID.md",
}
MARKER = re.compile(r"<!--\s*CAP:([a-z0-9_]+)\s*-->")
SCAN_ROOTS = ("AGENTS.md", "README.md", "DESIGN_SYSTEM.md", "docs", "medo-motion")
SKIP_PARTS = {"node_modules", ".git", "out", "cache", "projects"}

# Each capability must be visible in the code as something more than a name in this set.
CODE_EVIDENCE = {
    "alpha_layer": "--alpha",
    "multi_overlay": "MAX_OVERLAYS",
    "overlay_scene_filter": "--only",
    "alpha_k_only": "alpha is Engine-K only",
    "layers": '"layers"',
    "sequence": "sequence",
    "v1_normalised": "normalise",
    "frame_exact": "-frames:v",
    "audio_after_picture": "audio",
    "overlay_masking": "alphamerge",
    "mask_rect": "drawbox",
    "mask_image": '"image"',
}


def marked(path: Path) -> set[str]:
    return set(MARKER.findall(path.read_text(encoding="utf-8")))


def test_the_registry_is_not_empty() -> None:
    assert isinstance(render_hybrid.CAPABILITIES, frozenset)
    assert len(render_hybrid.CAPABILITIES) >= 6


@pytest.mark.parametrize("name", sorted(CONTRACTS))
def test_each_contract_marks_exactly_the_implemented_capabilities(name: str) -> None:
    found = marked(CONTRACTS[name])
    missing = sorted(render_hybrid.CAPABILITIES - found)
    stale = sorted(found - render_hybrid.CAPABILITIES)
    assert not missing, f"{name} does not mark: {missing} — document the capability or remove it"
    assert not stale, f"{name} marks capabilities the renderer does not have: {stale}"


def test_capability_names_are_snake_case_ascii() -> None:
    for capability in render_hybrid.CAPABILITIES:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", capability), capability


def test_no_unknown_marker_anywhere_in_the_docs() -> None:
    """A typo in a marker must fail here, not disappear from the comparison above."""
    unknown: list[str] = []
    for entry in SCAN_ROOTS:
        target = ROOT / entry
        files = [target] if target.is_file() else sorted(target.rglob("*.md"))
        for path in files:
            if SKIP_PARTS & set(path.relative_to(ROOT).parts):
                continue
            for capability in MARKER.findall(path.read_text(encoding="utf-8")):
                if capability not in render_hybrid.CAPABILITIES:
                    unknown.append(f"{path.relative_to(ROOT)}: {capability}")
    assert not unknown, "unknown CAP markers: " + ", ".join(unknown)


@pytest.mark.parametrize("capability,needle", sorted(CODE_EVIDENCE.items()))
def test_every_capability_name_has_code_evidence(capability: str, needle: str) -> None:
    source = (ROOT / "tools" / "render_hybrid.py").read_text(encoding="utf-8")
    assert capability in render_hybrid.CAPABILITIES
    assert needle in source, f"'{capability}' is documented but '{needle}' is not in render_hybrid.py"


def test_the_contract_still_describes_both_shapes() -> None:
    """If a future rewrite drops v2 from AGENTS.md, the markers alone would not notice."""
    text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    section = text.split("When a concept genuinely needs multiple strengths", 1)[-1]
    assert "v1" in section and "v2" in section
    assert "transparent" in section.lower()
