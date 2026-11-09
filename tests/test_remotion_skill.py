"""The Remotion (Engine R) add-on skill must stay honest about the studio.

These tests pin the claims in ``medo-motion/skills/remotion/SKILL.md`` to the
R scaffold, the manifests, and the integration report. When a manifest grows or
the scaffold moves, the skill text is what goes stale — update the skill, the
report, and this test together, never silently.
"""
from __future__ import annotations

import json
import re

from conftest import ROOT, SKILL

ADDON = SKILL / "skills" / "remotion" / "SKILL.md"
REPORT = ROOT / "docs" / "remotion-skill.md"
TEMPLATE = SKILL / "templates" / "remotion"

UPSTREAM_SKILLS = (
    "remotion-best-practices",
    "remotion-create",
    "remotion-markup",
    "remotion-studio",
    "remotion-render",
    "remotion-maps",
    "remotion-captions",
    "remotion-saas",
    "remotion-interactivity",
    "remotion-multimedia",
    "remotion-license",
    "remotion-upgrade",
    "remotion-docs",
)

FORBIDDEN_PACKAGES = (
    "@remotion/media",
    "@remotion/effects",
    "@remotion/captions",
    "@remotion/gif",
    "@remotion/lottie",
    "@remotion/shapes",
    "@remotion/paths",
    "@remotion/whisper-webgpu",
)


def _skill_text() -> str:
    return ADDON.read_text(encoding="utf-8")


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_addon_skill_exists_with_frontmatter():
    assert ADDON.is_file(), "the add-on skill must live at medo-motion/skills/remotion/SKILL.md"
    head = _skill_text().split("---", 2)[1]
    assert "name: video-motion-remotion" in head
    assert "description:" in head


def test_addon_defers_to_the_core_contract_without_replacing_it():
    text = _skill_text()
    flat = _flat(text)
    assert "AGENTS.md" in text
    assert "medo-motion/SKILL.md" in text
    assert re.search(r"never\s+replaces", flat), "the add-on must say it never replaces the core contract"
    core = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert "video-motion-remotion" not in core, "core skill must not depend on the add-on"


def test_all_thirteen_upstream_skills_are_accounted_for():
    text = _skill_text()
    missing = [slug for slug in UPSTREAM_SKILLS if slug not in text]
    assert not missing, f"upstream skills missing from the disposition table: {missing}"


def test_provenance_pins_are_recorded():
    text = _skill_text()
    for token in ("remotion-dev/skills", "4.0.541", "a2824c6", "2026-11-09"):
        assert token in text, f"provenance token missing: {token}"


def test_scaffold_version_pins_match_package_json():
    pkg = json.loads((TEMPLATE / "package.json").read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    assert deps["remotion"] == "4.0.539"
    assert deps["@remotion/cli"] == "4.0.539"
    assert deps["@remotion/renderer"] == "4.0.539"
    assert deps["react"] == "19.3.1"
    assert pkg.get("overrides", {}).get("zod") == "^4.6.7"
    text = _skill_text()
    for token in ("4.0.539", "19.3.1", "^4.6.7"):
        assert token in text, f"the skill must state the scaffold pin {token}"


def test_studio_commands_are_the_allowed_path():
    text = _skill_text()
    for token in ("npm run studio", "npm run render -- --audio", "npm run stills",
                  "npm run typecheck", "tools/new_project.py"):
        assert token in text, f"{token} missing from the studio R path"
    # The upstream-only commands must appear solely as explicitly rejected paths.
    assert "not `npx remotion studio`" in text
    assert "never a bare `npx remotion render`" in text


def test_tool_paths_referenced_by_the_skill_exist():
    text = _skill_text()
    refs = set(re.findall(r"(?<![\w./-])(tools/[\w./-]+\.(?:py|mjs|sh))", text))
    assert refs, "the skill should reference concrete tools"
    for rel in sorted(refs):
        assert (ROOT / rel).is_file(), f"{rel} referenced by the skill does not exist"


def test_medo_paths_referenced_by_the_skill_exist():
    for rel in (
        "medo-motion/templates/remotion/scripts/launch-remotion.mjs",
        "medo-motion/templates/remotion/scripts/render.mjs",
        "medo-motion/templates/remotion/scripts/stills.mjs",
        "medo-motion/templates/remotion/src/lib/effects.js",
        "medo-motion/templates/render/lib/captions.js",
        "medo-motion/reference/arabic-typography.md",
        "medo-motion/brand/brand.json",
        "assets/fonts/fonts.json",
        "assets/CREDITS.md",
        "docs/remotion.md",
        "docs/remotion-skill.md",
        "docs/motion-three.md",
        "docs/length.md",
        "docs/alignment.md",
        "tools/optional-three/package.json",
    ):
        assert (ROOT / rel).is_file(), rel


def test_r_template_components_named_by_the_skill_exist():
    lib = TEMPLATE / "src" / "lib"
    for name in ("DirectedText", "MachineDiagram", "SlideWall", "OneTake",
                 "FixedStage", "SceneEffects", "TextMotion", "SvgArt", "ThreeCanvas"):
        assert (lib / f"{name}.tsx").is_file(), f"{name}.tsx missing from the R template"


def test_three_pin_matches_optional_three():
    pkg = json.loads((ROOT / "tools" / "optional-three" / "package.json").read_text(encoding="utf-8"))
    assert pkg["dependencies"]["three"] == "0.187.0"
    lock = json.loads((ROOT / "tools" / "optional-three" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/three"]["version"] == "0.187.0"
    assert "0.187.0" in _skill_text()


def test_scaffold_ships_core_remotion_only():
    pkg = json.loads((TEMPLATE / "package.json").read_text(encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    for name in FORBIDDEN_PACKAGES:
        assert name not in deps, f"{name} is now installed — update the skill, the report and this test deliberately"


def test_report_exists_and_accounts_for_all_thirteen_skills():
    assert REPORT.is_file(), "docs/remotion-skill.md is missing"
    flat = _flat(REPORT.read_text(encoding="utf-8"))
    assert "remotion-dev/skills" in flat
    assert "Remotion License" in flat
    missing = [slug for slug in UPSTREAM_SKILLS if slug not in flat]
    assert not missing, f"the integration report must cover every upstream skill: {missing}"


def test_credits_attribution_is_registered():
    credits = (ROOT / "assets" / "CREDITS.md").read_text(encoding="utf-8")
    assert "remotion-dev/skills" in credits


def test_addon_directory_contains_no_vendored_upstream():
    contents = list(ADDON.parent.iterdir())
    assert contents == [ADDON], "the add-on directory must hold only SKILL.md — upstream is never vendored"
