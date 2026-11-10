#!/usr/bin/env python3
"""Split the pytest suite into the three CI groups, with one guard against drift.

A single job running all 1,394 tests takes ~9 minutes, so pull requests used to
run a hand-picked subset (12 of 78 files). The suite is now split into three
disjoint groups that run as parallel jobs, and `--check` fails if a test file is
not assigned, is assigned twice, or if the workflow stops asking for a group.

    python3 tools/ci_groups.py --check             # CI: coverage + workflow wiring
    python3 tools/ci_groups.py --list unit         # print the file list for a job
    python3 tools/ci_groups.py --json              # the whole mapping

Groups:

- `contracts` — docs, schemas, brand, fonts, lint policy, skills. No browser, no media.
- `unit`      — pure Python/JS logic: Arabic shaping, audio DSP, motion maths, icons.
- `render`    — anything that renders, decodes, or launches Chromium (the default).

Unassigned files land in `render`: a new heavy test is then validated by the job
that has the full runtime, never silently skipped by a light one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
GROUPS = ("contracts", "unit", "render")

ASSIGNED: dict[str, tuple[str, ...]] = {
    "contracts": (
        "test_beats_schema", "test_brand", "test_ci_groups", "test_contrast", "test_dependencies",
        "test_design_system", "test_docs_numbers", "test_file_safety", "test_fonts",
        "test_fonts_install", "test_fonts_lock", "test_hyperframes_fit", "test_import_precedence",
        "test_looks", "test_openmontage_fit", "test_recipes", "test_reel_lint",
        "test_reference_report", "test_remotion_skill", "test_scene_director", "test_setup",
        "test_skillry_fit", "test_studio_not_archive", "test_styles", "test_techniques",
        "test_text_animations", "test_video_motion_paths", "test_vo_length",
    ),
    "unit": (
        "test_arabic_shape", "test_audio_engine", "test_audio_generate", "test_caption_align",
        "test_frame_graph",
        "test_icons", "test_motion", "test_motion_effects", "test_motion_final", "test_music",
        "test_presenter", "test_render_policy", "test_rhythm", "test_shared_libs", "test_sfx",
        "test_sfx_engine",
        "test_space3d_offline", "test_text_direction", "test_transitions",
    ),
}


def test_files(root: Path | None = None) -> list[str]:
    base = root or ROOT
    return sorted(path.stem for path in (base / "tests").glob("test_*.py"))


def assignment(root: Path | None = None) -> dict[str, str]:
    """Map every test module to exactly one group (unassigned → render)."""
    mapping = {name: group for group, names in ASSIGNED.items() for name in names}
    return {name: mapping.get(name, "render") for name in test_files(root)}


def members(group: str, root: Path | None = None) -> list[Path]:
    base = root or ROOT
    if group not in GROUPS:
        raise SystemExit(f"unknown group '{group}' (known: {', '.join(GROUPS)})")
    return [base / "tests" / f"{name}.py" for name, owner in assignment(root).items() if owner == group]


def check(root: Path | None = None) -> list[str]:
    base = root or ROOT
    problems: list[str] = []
    files = set(test_files(base))

    listed: dict[str, str] = {}
    for group, names in ASSIGNED.items():
        for name in names:
            if name in listed:
                problems.append(f"{name} is assigned to both {listed[name]} and {group}")
            listed[name] = group
            if name not in files:
                problems.append(f"{group} lists {name}, but tests/{name}.py does not exist")

    for name, group in assignment(base).items():
        if group not in GROUPS:
            problems.append(f"{name} resolved to unknown group {group}")

    for group in GROUPS:
        if not members(group, base):
            problems.append(f"group '{group}' is empty")

    workflow = (base / ".github" / "workflows" / "ci.yml")
    if workflow.is_file():
        text = workflow.read_text(encoding="utf-8")
        for group in GROUPS:
            if f"ci_groups.py {group}" not in text:
                problems.append(f"ci.yml never runs the '{group}' group (tools/ci_groups.py {group})")
        if "ci_groups.py --check" not in text:
            problems.append("ci.yml never runs tools/ci_groups.py --check")
    elif (base / ".github").is_dir():
        problems.append("ci.yml is missing, so the group wiring cannot be checked")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The pytest groups the CI jobs run.")
    parser.add_argument("--check", action="store_true", help="verify coverage and workflow wiring")
    parser.add_argument("--list", metavar="GROUP", help="print the files of one group, space-separated")
    parser.add_argument("group", nargs="?", choices=GROUPS, help="shorthand for --list GROUP")
    parser.add_argument("--json", action="store_true", help="print the whole mapping")
    parser.add_argument("--root", help="repository root (default: the parent of this script's folder)")
    options = parser.parse_args(argv)
    root = Path(options.root).resolve() if options.root else ROOT

    wanted = options.list or options.group
    if wanted:
        print(" ".join(str(path) for path in members(wanted, root)))
        return 0

    mapping = assignment(root)
    if options.json:
        print(json.dumps({group: sorted(n for n, g in mapping.items() if g == group) for group in GROUPS}, indent=2))
        return 0

    problems = check(root)
    for problem in problems:
        print(f"FAIL  {problem}")
    counts = {group: sum(1 for owner in mapping.values() if owner == group) for group in GROUPS}
    summary = " · ".join(f"{group} {counts[group]}" for group in GROUPS)
    if problems:
        return 1
    if options.check:
        print(f"OK CI groups cover all {len(mapping)} test files ({summary})")
    else:
        print(f"CI groups ({summary}) — run --check to verify")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
