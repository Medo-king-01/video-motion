"""One entry, one place — the two changelogs are consecutive, not duplicated (N8).

`CHANGELOG.md` and `medo-motion/CHANGELOG.md` look like the same document from a distance: same
product, overlapping subjects, no shared heading. Inspecting them showed they are actually a split
history — the toolkit's scaffold 1.0 → 2.7 (2026-11-01 → 11-09) and then the studio from 2026-11-09
onward. Nothing said so, so every new entry risked going into both (or neither).

The fix is not a merge (that would rewrite a versioned archive) but an enforced boundary: both
files declare their scope, the archive is frozen, and no heading may appear in both.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STUDIO = ROOT / "CHANGELOG.md"
TOOLKIT = ROOT / "medo-motion" / "CHANGELOG.md"
HEADING = re.compile(r"(?m)^##\s+(.+)$")


def headings(path: Path) -> list[str]:
    return [match.strip() for match in HEADING.findall(path.read_text(encoding="utf-8"))]


def test_both_logs_exist_and_declare_their_scope():
    studio = STUDIO.read_text(encoding="utf-8")
    toolkit = TOOLKIT.read_text(encoding="utf-8")
    assert "2026-11-09" in studio and "medo-motion/CHANGELOG.md" in studio
    assert "Frozen archive" in toolkit and "../CHANGELOG.md" in toolkit


def test_no_entry_is_written_twice():
    shared = set(headings(STUDIO)) & set(headings(TOOLKIT))
    assert not shared, f"the same entry is in both logs: {sorted(shared)}"


def test_the_archive_is_frozen_and_the_studio_log_is_live():
    toolkit = TOOLKIT.read_text(encoding="utf-8")
    assert "## Unreleased" not in toolkit, "the frozen archive grew an Unreleased section"
    studio = STUDIO.read_text(encoding="utf-8")
    assert "## Unreleased" in studio, "the live studio log lost its Unreleased section"


def test_the_split_is_documented_where_readers_start():
    readme = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "CHANGELOG.md" in readme
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "CHANGELOG" in agents, "AGENTS.md must point an agent at the log to update"
