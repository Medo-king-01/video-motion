"""Statements in README.md that a config file can contradict are checked against that file."""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

README = (ROOT / "README.md").read_text(encoding="utf-8")


def _minimum_python() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    return re.search(r'^requires-python\s*=\s*">=\s*([0-9.]+)"', text, re.M).group(1)


def _projects_are_ignored() -> bool:
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    return "projects/*" in [line.strip() for line in lines]


def test_the_facts_the_wording_depends_on() -> None:
    assert _minimum_python() == "3.10", "the minimum changed: update README 'أول تشغيل' and this test"
    assert _projects_are_ignored(), "projects/ is tracked again: update README and this test"
    setup = (ROOT / "tools" / "setup.sh").read_text(encoding="utf-8")
    assert "sys.version_info >= (3,10)" in setup, "setup.sh and pyproject.toml disagree on the minimum"


def test_readme_does_not_say_project_files_are_tracked() -> None:
    for claim in ("قابلة للتتبع بـGit", "قابلة للتتبع"):
        assert claim not in README, f"README says project files are tracked ({claim}), but .gitignore has projects/*"


def test_readme_says_projects_are_untracked_and_backed_up_elsewhere() -> None:
    section = README[README.index("## أول تشغيل"):README.index("## اللي جوه")]
    assert "مش بيتتبّع" in section and "projects/*" in section
    assert "نسخة احتياطية" in section and ("مستودع منفصل" in section or "مكان منفصل" in section)
    assert "projects/README.md" in section


def test_readme_states_the_supported_minimum_and_the_recommended_version() -> None:
    section = README[README.index("## أول تشغيل"):README.index("## اللي جوه")]
    line = next(line for line in section.splitlines() if "Python" in line and "Node" in line)
    assert f"{_minimum_python()}+" in line, f"the install line does not name the supported minimum: {line}"
    assert "3.12" in line and "الموصى به" in line, f"the install line does not name 3.12 as recommended: {line}"


@pytest.mark.parametrize("readme, pyproject, gitignore, problems", [
    ("ثبّت Python 3.12 وNode\nملفات المشروع قابلة للتتبع بـGit", 'requires-python = ">=3.10"', "projects/*\n", 2),
    ("ثبّت Python 3.10+ (الموصى به 3.12) وNode\nprojects/* مش بيتتبّع", 'requires-python = ">=3.10"', "projects/*\n", 0),
    ("ثبّت Python 3.10+ (الموصى به 3.12) وNode", 'requires-python = ">=3.11"', "projects/*\n", 1),
    ("ثبّت Python 3.10+ (الموصى به 3.12) وNode\nقابلة للتتبع بـGit", 'requires-python = ">=3.10"', "", 0),
])
def test_the_check_tool_reports_each_contradiction(tmp_path: Path, readme: str, pyproject: str, gitignore: str,
                                                   problems: int) -> None:
    import sync_docs_numbers

    (tmp_path / "README.md").write_text(readme, encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(f"[project]\n{pyproject}\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(gitignore, encoding="utf-8")
    assert len(sync_docs_numbers.claim_problems(tmp_path)) == problems


def test_the_repository_passes_the_claim_check() -> None:
    import sync_docs_numbers

    assert sync_docs_numbers.claim_problems(ROOT) == []
