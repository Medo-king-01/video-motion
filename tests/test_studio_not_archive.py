"""The studio is a tool, not a video archive.

A delivered video leaves the repository with its project folder: no finished project,
old render or past-video CI workflow may stay behind as "memory". The name/title slot is
also the user's decision, never the agent's.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest
from conftest import ROOT

GITIGNORE = (ROOT / ".gitignore").read_text(encoding="utf-8")


def _git_ignored(relative: str) -> bool:
    result = subprocess.run(["git", "check-ignore", "--no-index", relative],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode in (0, 1), result.stderr
    return result.returncode == 0


def test_project_folders_are_not_part_of_the_repository_history():
    assert "projects/*" in GITIGNORE
    assert "!projects/README.md" in GITIGNORE
    for relative in ("projects/some-video/BRIEF.md",
                     "projects/some-video/plan/beats.json",
                     "projects/some-video/out/master.mp4"):
        assert _git_ignored(relative), relative


def test_no_finished_project_is_kept_in_the_repository():
    """projects/ holds only its README: the studio does not archive past videos."""
    projects = ROOT / "projects"
    entries = sorted(p.name for p in projects.iterdir() if p.name != "__pycache__")
    assert entries == ["README.md"], f"remove past video folders from the repo: {entries}"


def test_no_workflow_targets_one_past_video():
    workflows = ROOT / ".github" / "workflows"
    for path in sorted(workflows.glob("*.yml")):
        text = path.read_text(encoding="utf-8").lower()
        assert "projects/" not in text, f"{path.name} renders a single past project"
        assert "episode" not in path.name.lower(), f"{path.name} is a per-video workflow"
        assert "ram-episode" not in text


def test_scaffold_is_ignored_by_git_and_gitignores_itself(tmp_path):
    slug = f"_pytest-archive-{tmp_path.name}"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug],
                            cwd=str(ROOT), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    proj = ROOT / "projects" / slug
    try:
        marker = (proj / ".gitignore").read_text(encoding="utf-8")
        assert marker.splitlines()[-1].strip() == "*"
        assert _git_ignored(f"projects/{slug}/BRIEF.md")
        ignored = subprocess.run(["git", "check-ignore", "--no-index", "projects/README.md"],
                                 cwd=ROOT, capture_output=True)
        assert ignored.returncode == 1, "the projects/README.md must stay tracked"
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_scaffold_can_live_outside_the_repository(tmp_path):
    target = tmp_path / "my-reel"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "my-reel",
                             "--out", str(target)], cwd=str(ROOT), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert (target / "plan" / "beats.json").is_file()
    assert (target / ".gitignore").is_file()
    assert not (ROOT / "projects" / "my-reel").exists()


@pytest.mark.parametrize("read_only", ["medo-motion/reels", "tools/reels", "tests/reels", "assets/reels"])
def test_scaffold_refuses_read_only_toolkit_paths(tmp_path, read_only):
    target = ROOT / read_only
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "x",
                             "--out", str(target)], cwd=str(ROOT), capture_output=True, text=True)
    assert result.returncode != 0
    assert "read-only" in result.stderr
    assert not target.exists()


def test_template_demo_has_no_default_series_label():
    """Engine P: no episode chip, and no caption talking about "the series"."""
    scenes = (ROOT / "medo-motion" / "templates" / "procedural-reels" / "scenes.py").read_text(encoding="utf-8")
    assert "CHIP=None" in scenes.replace(" ", "")
    for phrase in ("الحلقة الأولى", "تابع السلسلة", "بدأنا السلسلة"):
        # they may only appear inside a comment explaining that they are NOT drawn by default
        for line in scenes.splitlines():
            if phrase in line:
                assert line.strip().startswith("#"), f"default on-screen series wording: {line.strip()}"
    assert "if CHIP:" in scenes


def test_contract_states_the_archive_rule():
    contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "tool, not a video archive" in contract
    assert "never add\n    a per-project CI workflow" in contract


def test_changelog_records_the_rule():
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8").lower()
    assert "archive" in changelog
    assert "series name" in changelog
    serialised = json.dumps(changelog)
    assert serialised  # keep the file readable, just prove it parses as text


def test_toolkit_has_no_per_video_workflow_and_no_stale_branch():
    """CI validates the studio, never one past video, and never a dead feature branch."""
    for path in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = path.read_text(encoding="utf-8")
        assert "fix/engine-p-chunk-integrity" not in text, f"{path.name} targets a stale branch"
        assert "episode" not in path.name.lower(), f"{path.name} is a per-video workflow"


def test_no_past_video_is_a_starting_point():
    """The archived brief is a read-only inventory: no recipe, no default name or timing.

    A new video starts from the four inputs plus the toolkit. If the archive still carries a
    ready-made script, palette or chip, some agent (or human) will copy it again.
    """
    source = ROOT / "medo-motion" / "reference" / "source"
    archived = (source / "AGENT_MASTER_BRIEF_v4.md").read_text(encoding="utf-8")
    for stale in ("بدأنا السلسلة دي", "الحلقة الأولى", "chip السلسلة مركزه",
                  "chip وصفي مؤقت + دايرة فاضية للوجو"):
        assert stale not in archived, f"the archive still hands over a past video's {stale!r}"
    assert "ملوش سلطة" in archived
    assert "المرجع الحالي هو `brand/brand.json`" in archived


def test_the_studio_memory_is_the_toolkit():
    """AGENTS rule 12 says what IS the memory, so keeping a video is never the way to 'remember'."""
    contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "The studio's memory is this toolkit" in contract
    assert "never use a past video as the starting point of a new one" in contract
