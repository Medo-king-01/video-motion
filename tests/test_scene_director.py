"""The Creative Scene Director add-on skill must match the studio's real capabilities.

These tests pin the claims in ``medo-motion/skills/scene-director/SKILL.md`` to the
manifests and engine source. When a manifest grows or a module moves, the skill text
is what goes stale — update the skill, not the test.
"""
from __future__ import annotations

import json
import re

from conftest import ENGINE_P, ROOT, SKILL

ADDON = SKILL / "skills" / "scene-director" / "SKILL.md"


def _skill_text() -> str:
    return ADDON.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_addon_skill_exists_with_frontmatter():
    assert ADDON.is_file(), "the add-on skill must live at medo-motion/skills/scene-director/SKILL.md"
    head = _skill_text().split("---", 2)[1]
    assert "name: video-motion-scene-director" in head
    assert "description:" in head


def test_addon_defers_to_the_core_contract_without_replacing_it():
    text = _skill_text()
    assert "AGENTS.md" in text
    assert "medo-motion/SKILL.md" in text
    # The add-on must declare its optional, non-destructive role.
    assert re.search(r"never\s+(?:>\s+)?replace", text), "the add-on must say it never replaces the core contract"
    core = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "video-motion-scene-director" not in core, "core skill must not depend on the add-on"


def test_inspection_targets_exist():
    for rel in (
        "AGENTS.md",
        "DESIGN_SYSTEM.md",
        "medo-motion/SKILL.md",
        "medo-motion/brand/BRAND.md",
        "medo-motion/brand/brand.json",
        "assets/poses/poses.json",
        "assets/styles/styles.json",
        "assets/fonts/fonts.json",
        "assets/techniques.json",
        "medo-motion/motion/backgrounds.json",
        "medo-motion/motion/easings.json",
        "medo-motion/motion/transitions.json",
        "medo-motion/motion/text-animations.json",
    ):
        assert (ROOT / rel).is_file(), rel
        assert rel in _skill_text(), f"{rel} missing from the skill's inspection list"


def test_tool_paths_referenced_by_the_skill_exist():
    text = _skill_text()
    refs = set(re.findall(r"`(tools/[\w./-]+\.(?:py|mjs|sh))`", text))
    refs |= set(re.findall(r"^(tools/[\w./-]+\.(?:py|mjs|sh))$", text, flags=re.M))
    assert refs, "the skill should reference concrete tools"
    for rel in sorted(refs):
        assert (ROOT / rel).is_file(), f"{rel} referenced by the skill does not exist"


def test_machine_archetypes_match_both_engines():
    text = _skill_text()
    src = (ENGINE_P / "machine_kit.py").read_text(encoding="utf-8")
    match = re.search(r"SUPPORTED_ARCHETYPES = \(([^)]*)\)", src)
    assert match
    archetypes = tuple(re.findall(r'"([a-z_]+)"', match.group(1)))
    assert archetypes == ("nvme_ssd", "cpu_package", "ram_dimm", "cooling_system", "custom")
    js = (SKILL / "templates" / "render" / "lib" / "machine-kit.js").read_text(encoding="utf-8")
    for name in archetypes:
        assert f"'{name}'" in js
        assert f"- {name}" in text, f"machine archetype {name} missing from the skill"


def test_custom_primitives_match_all_three_engines():
    """The `custom` primitive list is a draw-switch contract, not prose.

    A review round caught the skill saying `coil` while the report said
    `cylinder` — both engines accept a strict union. Pin the skill and the
    report to the actual dispatch in the three machine-kit sources.
    """
    expected = {"slab", "slab_stack", "ticks", "poly3d", "cylinder", "ring", "wire", "coil"}
    js_sets = []
    for rel in ("templates/remotion/src/lib/machine-kit.js",
                "templates/render/lib/machine-kit.js"):
        src = (SKILL / rel).read_text(encoding="utf-8")
        js_sets.append(set(re.findall(r"primitive === '([a-z0-9_]+)'", src)))
    py = (ENGINE_P / "machine_kit.py").read_text(encoding="utf-8")
    py_prims = set(re.findall(r'prim == "([a-z0-9_]+)"', py))
    for group in re.findall(r"prim in \(([^)]*)\)", py):
        py_prims |= set(re.findall(r'"([a-z0-9_]+)"', group))
    assert js_sets[0] == expected, f"engine K primitives drifted: {sorted(js_sets[0])}"
    assert js_sets[1] == expected, f"engine R primitives drifted: {sorted(js_sets[1])}"
    assert py_prims == expected, f"engine P primitives drifted: {sorted(py_prims)}"
    text = _skill_text()
    match = re.search(r"available primitives \(([^)]*)\)", text)
    assert match, "the skill must list the custom primitives it relies on"
    listed = {p.strip() for p in match.group(1).split(",")}
    assert listed == expected, f"the skill's primitive list drifted: {sorted(listed)}"
    report = (ROOT / "docs" / "scene-director-skill.md").read_text(encoding="utf-8")
    row = next((line for line in report.splitlines() if "slab_stack" in line), "")
    assert row, "the implementation report must list the custom primitives"
    reported = set(re.findall(r"`([a-z0-9_]+)`", row)) - {"custom"}
    assert reported == expected, f"the report's primitive list drifted: {sorted(reported)}"


def test_data_recipe_kinds_match_code():
    text = _skill_text()
    kinds = ("comparison", "timeline", "counter")
    js = (SKILL / "templates" / "render" / "lib" / "data-recipes.js").read_text(encoding="utf-8")
    py = (ROOT / "tools" / "data_recipe.py").read_text(encoding="utf-8")
    for kind in kinds:
        assert f"'{kind}'" in js
        assert f"'{kind}'" in py
        assert kind in text
    # Evidence classification is a visual-direction contract, not a data-recipe field.
    vd = (ROOT / "tools" / "visual_direction.py").read_text(encoding="utf-8")
    assert "{'user', 'source', 'illustrative'}" in vd
    for word in ("user", "source", "illustrative"):
        assert word in text


def test_library_counts_match_manifests():
    flat = _flat(_skill_text())

    techniques = json.loads((ROOT / "assets" / "techniques.json").read_text(encoding="utf-8"))["techniques"]
    match = re.search(r"contains ([\d,]+) techniques across (\d+) categories", flat)
    assert match, "the skill must state the technique library size in this exact phrasing"
    assert int(match.group(1).replace(",", "")) == len(techniques)
    categories = {item["category"] for item in techniques}
    assert int(match.group(2)) == len(categories)

    styles = json.loads((ROOT / "assets" / "styles" / "styles.json").read_text(encoding="utf-8"))["styles"]
    match = re.search(r"visual style library contains ([\d,]+) entries", flat)
    assert match
    assert int(match.group(1).replace(",", "")) == len(styles)

    poses = json.loads((ROOT / "assets" / "poses" / "poses.json").read_text(encoding="utf-8"))["poses"]
    match = re.search(r"(\d+) poses — (\d+) full-body and (\d+) half-body", flat)
    assert match, "the skill must state the pose catalogue size in this exact phrasing"
    framing = [pose["framing"] for pose in poses.values()]
    assert int(match.group(1)) == len(poses)
    assert int(match.group(2)) == framing.count("full")
    assert int(match.group(3)) == framing.count("bust")


def test_local_style_references_resolve():
    text = _skill_text()
    for name in ("medo-red-circle", "editorial-explainer", "jazari-notebook", "ink-in-water",
                 "pixel-art", "risograph", "ascii-terminal", "showreel"):
        assert f"- {name}" in text
        assert (SKILL / "styles" / f"{name}.md").is_file(), name


def test_primary_engine_modules_named_by_the_skill_exist():
    for name in ("presenter.py", "machine_kit.py", "slide_wall.py", "space3d.py",
                 "backgrounds.py", "motion.py", "transition.py", "svg_art.py"):
        assert (ENGINE_P / name).is_file(), name
    klib = SKILL / "templates" / "render" / "lib"
    for name in ("motion.js", "motion-plan.js", "motion-geometry.js", "motion-state.js",
                 "transition.js", "slide-wall.js", "stage.js", "text-direction.js",
                 "geometry-canvas.js"):
        assert (klib / name).is_file(), name
    rlib = SKILL / "templates" / "remotion" / "src" / "lib"
    for name in ("DirectedText", "MachineDiagram", "SlideWall", "OneTake",
                 "SceneEffects", "ThreeCanvas", "DataRecipe"):
        assert (rlib / f"{name}.tsx").is_file(), name


def test_directed_text_helpers_exist_in_all_engines():
    assert "def draw_directed_text" in (ENGINE_P / "captions.py").read_text(encoding="utf-8")
    assert "function drawDirectedText" in (
        SKILL / "templates" / "render" / "lib" / "captions.js").read_text(encoding="utf-8")
    assert (SKILL / "templates" / "remotion" / "src" / "lib" / "DirectedText.tsx").is_file()


def test_availability_matrix_claims_hold():
    """Data recipes and icons are K/R-scoped exactly as the skill's matrix says."""
    klib = SKILL / "templates" / "render" / "lib"
    rlib = SKILL / "templates" / "remotion" / "src" / "lib"
    # Data recipes: K + R, not P.
    assert (klib / "data-recipes.js").is_file()
    assert (rlib / "DataRecipe.tsx").is_file()
    assert not list(ENGINE_P.glob("data_*")), "engine P has no data-recipe module — keep the matrix honest"
    # Animated icons: P + K, not R.
    assert (ENGINE_P / "icons.py").is_file()
    assert (klib / "icons.js").is_file()
    assert not list(rlib.glob("*[Ii]con*")), "engine R has no icon layer — keep the matrix honest"
    # Three.js: K + R opt-in, no P adapter.
    assert (klib / "three-layer.js").is_file()
    assert (rlib / "ThreeCanvas.tsx").is_file()
    assert not list(ENGINE_P.glob("three*")), "engine P has no Three adapter — keep the matrix honest"


def test_qa_tools_named_by_the_skill_exist():
    text = _skill_text()
    for rel in ("tools/reel_lint.py", "tools/visual_direction.py", "tools/data_recipe.py",
                "tools/machine_explainer.py", "tools/layout_audit.mjs", "tools/layout_audit_p.py",
                "medo-motion/scripts/brand_check.py", "tools/media_qa.py"):
        assert rel in text
        assert (ROOT / rel).is_file(), rel
