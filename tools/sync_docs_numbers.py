#!/usr/bin/env python3
"""Keep every measured count in the docs true — one source, checked in CI.

The studio's operating contract is prose, and agents read it literally. When a
number in the docs drifts from the library it describes (the technique count was
written as 59, 334, 1,434 and 2,239 in four places), the agent makes a wrong
production decision. This tool removes the bookkeeping: the docs declare a slot

    <!-- AUTO:techniques -->2,239<!-- /AUTO -->

and the number inside it is *generated* from the library on disk.

    python3 tools/sync_docs_numbers.py            # rewrite every slot (default)
    python3 tools/sync_docs_numbers.py --check    # CI: exit 1 on any drift
    python3 tools/sync_docs_numbers.py --list     # print the measured values
    python3 tools/sync_docs_numbers.py --root .   # another checkout (tests)

Read-only when `--check` is used. Never invents a value: an unknown key is an
error, not a silent skip, and every key in `REQUIRED` must appear at least once
so a deleted slot cannot quietly bring the hand-written number back.

Metrics are derived from the same files the renderers read: `assets/techniques.json`,
`assets/fonts/fonts.json`, `assets/poses/poses.json`, `medo-motion/icons/manifest.json`,
`assets/styles/styles.json`, `assets/gl-transitions/`, `medo-motion/motion/*.json`
and `templates/procedural-reels/sfx.py` (parsed with `ast`, never imported).
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"

MARKER = re.compile(r"<!--\s*AUTO:([a-z0-9_]+)\s*-->(.*?)<!--\s*/AUTO\s*-->", re.DOTALL)
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "projects", "out", "cache", "__pycache__", ".ruff_cache",
             ".pytest_cache"}

# Every key must stay visible somewhere: a docs edit that deletes the last slot
# would otherwise re-introduce a hand-written number with nothing watching it.
REQUIRED = (
    "techniques", "technique_categories", "focus_techniques", "techniques_studio", "techniques_alansari",
    "techniques_opus", "techniques_glsl", "fonts", "fonts_arabic", "fonts_latin", "fonts_ofl", "poses",
    "icons", "styles", "gl_transitions", "transitions", "text_animations", "backgrounds", "looks",
    "recipes", "sfx", "music_presets",
)


def _json(path: str | Path, base: Path | None = None) -> dict:
    target = Path(path) if isinstance(path, Path) else (base or ROOT) / path
    return json.loads(target.read_text(encoding="utf-8"))


def _dict_len_assignment(path: Path, name: str) -> int:
    """Length of a literal `NAME = {...}` without importing the module (no numpy at import time)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name and isinstance(node.value, ast.Dict):
                    return len(node.value.keys)
    raise ValueError(f"{path}: no literal dict assignment named {name}")


def metrics(root: Path | None = None) -> dict[str, int]:
    """Measure every documented count from the source libraries."""
    base = (root or ROOT)
    skill = base / "medo-motion"

    def read(relative: str | Path) -> dict:
        return _json(relative, base)

    techniques = read("assets/techniques.json")["techniques"]
    by_source: dict[str, int] = {}
    studio_categories = set()
    for item in techniques:
        source = item.get("source")
        by_source[source or "studio"] = by_source.get(source or "studio", 0) + 1
        if not source:
            studio_categories.add(item.get("category"))

    families = read("assets/fonts/fonts.json")["families"]
    scripts = [family.get("script") for family in families.values()]
    licences = [family.get("licence") or family.get("license") for family in families.values()]

    looks = read("medo-motion/looks/looks.json")
    recipes = read("medo-motion/recipes/recipes.json")

    return {
        "techniques": len(techniques),
        "technique_categories": len({item.get("category") for item in techniques}),
        # The families the studio wrote itself (the `focus` draw in tools/techniques.py).
        "focus_techniques": len(studio_categories),
        "techniques_studio": by_source.get("studio", 0),
        "techniques_alansari": by_source.get("alansari-motion-library", 0),
        "techniques_opus": by_source.get("opus-motion-library", 0),
        "techniques_glsl": by_source.get("gl-transitions", 0),
        "fonts": len(families),
        "fonts_arabic": sum(1 for script in scripts if script == "arabic"),
        "fonts_latin": sum(1 for script in scripts if script == "latin"),
        "fonts_ofl": sum(1 for licence in licences if licence == "OFL-1.1"),
        "poses": len(read("assets/poses/poses.json")["poses"]),
        "icons": len(read("medo-motion/icons/manifest.json")["icons"]),
        "styles": len(read("assets/styles/styles.json")["styles"]),
        "gl_transitions": len(list((base / "assets" / "gl-transitions").glob("*.glsl"))),
        "transitions": len(read("medo-motion/motion/transitions.json")["transitions"]),
        "text_animations": len(read("medo-motion/motion/text-animations.json")["animations"]),
        "backgrounds": len(read("medo-motion/motion/backgrounds.json")["backgrounds"]),
        "looks": len(looks["looks"]),
        "recipes": len(recipes["recipes"]),
        "sfx": _dict_len_assignment(skill / "templates" / "procedural-reels" / "sfx.py", "CATALOG"),
        "music_presets": len(read("medo-motion/motion/music-presets.json")["presets"]),
    }


def format_number(value: int) -> str:
    return f"{value:,}"


def replace_markers(text: str, values: dict[str, int], *, source: str = "") -> tuple[str, list[str], list[str]]:
    """Fill every AUTO slot in `text`. Returns (new_text, problems, changed_keys)."""
    problems: list[str] = []
    changed: list[str] = []

    def _fill(match: re.Match[str]) -> str:
        key = match.group(1)
        current = match.group(2).strip()
        if key not in values:
            problems.append(f"{source}: unknown AUTO key '{key}'")
            return match.group(0)
        wanted = format_number(values[key])
        if current != wanted:
            changed.append(f"{key}: {current} -> {wanted}")
        return f"<!-- AUTO:{key} -->{wanted}<!-- /AUTO -->"

    return MARKER.sub(_fill, text), problems, changed


def doc_files(root: Path | None = None) -> list[Path]:
    """Every Markdown file that could carry a slot (the repo's own docs, not dependencies)."""
    base = root or ROOT
    files: list[Path] = []
    for path in base.rglob("*.md"):
        if any(part in SKIP_DIRS for part in path.relative_to(base).parts):
            continue
        files.append(path)
    return sorted(files)


def sync(root: Path | None = None, *, write: bool = True, values: dict[str, int] | None = None,
         require_slots: bool = True) -> tuple[list[str], list[str]]:
    """Apply the measured values to every slot. Returns (problems, changes)."""
    base = root or ROOT
    values = values if values is not None else metrics(base)
    problems: list[str] = []
    changes: list[str] = []
    seen: set[str] = set()

    for path in doc_files(base):
        text = path.read_text(encoding="utf-8")
        if "<!-- AUTO:" not in text:
            continue
        relative = path.relative_to(base) if path.is_relative_to(base) else path
        seen.update(match.group(1) for match in MARKER.finditer(text))
        new_text, file_problems, file_changes = replace_markers(text, values, source=str(relative))
        problems.extend(file_problems)
        changes.extend(f"{relative}: {change}" for change in file_changes)
        if write and new_text != text:
            path.write_text(new_text, encoding="utf-8")

    missing = [key for key in REQUIRED if key not in seen] if require_slots else []
    if missing:
        problems.append("no AUTO slot in any doc for: " + ", ".join(missing))
    return problems, changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keep documented counts derived from the libraries.")
    parser.add_argument("--check", action="store_true", help="report drift and exit 1 (writes nothing)")
    parser.add_argument("--list", action="store_true", help="print the measured values and exit")
    parser.add_argument("--root", help="repository root (default: the parent of this script's folder)")
    options = parser.parse_args(argv)

    root = Path(options.root).resolve() if options.root else ROOT
    values = metrics(root)

    if options.list:
        width = max(len(key) for key in values)
        for key, value in sorted(values.items()):
            print(f"{key:<{width}}  {format_number(value)}")
        return 0

    problems, changes = sync(root, write=not options.check)
    if options.check:
        for change in changes:
            print(f"DRIFT {change}")
        for problem in problems:
            print(f"FAIL  {problem}")
        if problems or changes:
            print("docs numbers drifted from the libraries — run: python3 tools/sync_docs_numbers.py")
            return 1
        print(f"OK docs numbers match the libraries ({len(values)} keys)")
        return 0

    for change in changes:
        print(f"UPDATED {change}")
    for problem in problems:
        print(f"FAIL    {problem}", file=sys.stderr)
    if not changes and not problems:
        print("OK nothing to update")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
