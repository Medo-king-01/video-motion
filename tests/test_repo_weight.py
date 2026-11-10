"""The repository-weight ratchet (N4).

No Git LFS here on purpose — a filter changes every clone and every CI job, and rewriting history is
an owner decision. What the repository lacked was cheaper: something that *notices* growth. These
tests pin the policy, not the numbers:

- small additions pass, a silent second asset folder does not;
- a new multi-megabyte file needs a deliberate `--update`, which shows up in the diff;
- the committed baseline still describes this repository, so `--check` stays meaningful in CI.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import repo_weight  # noqa: E402


def make_repo(tmp_path: Path, files: dict[str, int]) -> Path:
    """A throwaway Git repo whose files have the requested sizes, without writing the bytes."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=str(root), check=True)
    for name, size in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.truncate(size)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    return root


def test_categories_follow_the_extension_not_the_path():
    assert repo_weight.category_of("assets/fonts/x.ttf") == "fonts"
    assert repo_weight.category_of("docs/shot.PNG") == "images"
    assert repo_weight.category_of("docs/audition/01.mp3") == "audio"
    assert repo_weight.category_of("assets/poses/angry.png") == "images"
    assert repo_weight.category_of("tools/pipeline.py") == "text"


def test_snapshot_measures_bytes_and_lists_only_heavy_files(tmp_path):
    root = make_repo(tmp_path, {"a.ttf": 4 * repo_weight.MB, "b.png": 100, "c.py": 10})
    state = repo_weight.snapshot(root)
    assert state["total_mb"] == pytest.approx(4.0 + 110 / repo_weight.MB, abs=0.01)
    assert list(state["heavy"]) == ["a.ttf"]
    assert state["categories_files"]["fonts"] == 1
    assert state["categories_files"]["text"] == 1


def test_the_ratchet_tolerates_small_growth_only():
    baseline = {"total_mb": 100.0, "allowance_mb": 2.0, "heavy": {}}
    assert repo_weight.violations({"total_mb": 101.5, "heavy": {}}, baseline) == []
    problems = repo_weight.violations({"total_mb": 103.0, "heavy": {}}, baseline)
    assert len(problems) == 1 and "+3.00 MB" in problems[0]


def test_a_new_heavy_file_needs_a_deliberate_update():
    baseline = {"total_mb": 100.0, "allowance_mb": 2.0, "heavy": {"old.ttf": 4.0}}
    problems = repo_weight.violations({"total_mb": 100.5,
                                       "heavy": {"old.ttf": 4.0, "new/pose.png": 5.2}}, baseline)
    assert len(problems) == 1
    assert "new/pose.png" in problems[0] and "5.2 MB" in problems[0]


def test_update_records_a_baseline_that_check_accepts(tmp_path):
    root = make_repo(tmp_path, {"assets/a.ttf": 4 * repo_weight.MB})
    baseline = root / "docs" / "repo-weight-baseline.json"
    assert repo_weight.main(["--update", "--root", str(root)]) == 0
    stored = json.loads(baseline.read_text(encoding="utf-8"))
    assert stored["heavy"] == {"assets/a.ttf": 4.0}
    assert repo_weight.main(["--check", "--root", str(root)]) == 0

    # a second heavy asset must not slip in silently
    with (root / "assets" / "b.png").open("wb") as handle:
        handle.truncate(5 * repo_weight.MB)
    subprocess.run(["git", "add", "-A"], cwd=str(root), check=True)
    assert repo_weight.main(["--check", "--root", str(root)]) == 1
    assert repo_weight.main(["--update", "--root", str(root)]) == 0
    assert repo_weight.main(["--check", "--root", str(root)]) == 0


def test_check_without_a_baseline_fails_instead_of_guessing(tmp_path):
    root = make_repo(tmp_path, {"a.py": 10})
    assert repo_weight.main(["--check", "--root", str(root)]) == 1


def test_the_committed_baseline_still_describes_this_repository():
    """The guard is only real if the checked-in numbers match the tree that ships."""
    baseline = repo_weight.load_baseline()
    current = repo_weight.snapshot()
    assert repo_weight.violations(current, baseline) == []
    assert set(baseline["heavy"]) <= set(current["heavy"])


def test_the_lfs_decision_is_stated_or_actually_taken():
    """`.gitattributes` says "no LFS" today. If that ever flips, the doc has to flip with it.

    A silent `filter=lfs` line would change every clone and every CI job while the weight doc still
    told readers the opposite — the same contract-vs-reality drift this repository keeps hunting.
    """
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "repository-weight.md").read_text(encoding="utf-8")
    uses_lfs = "filter=lfs" in attributes
    states_no_lfs = "مافيش Git LFS" in doc
    assert uses_lfs != states_no_lfs, (
        "the attribute file and docs/repository-weight.md disagree about Git LFS"
    )
    if not uses_lfs:
        # The decision must carry its evidence, not just a preference.
        assert "152.3" in doc and "blob" in doc, "the LFS decision lost its measurements"
        assert "filter=blob:none" in doc, "the documented alternative to LFS disappeared"
