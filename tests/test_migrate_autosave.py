"""Forward-only migration and crash recovery: no silent loss in either direction.

The migration is allowed to add what the newer contract requires and nothing else; the autosave
is allowed to survive a crash but never to overwrite work it does not belong to.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import unified_project_migrate as migrate  # noqa: E402
import unified_project_store as store  # noqa: E402

FIXTURE = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))


def test_a_1_0_project_migrates_to_the_current_contract_and_validates() -> None:
    migrated, report = migrate.migrate(FIXTURE)
    assert report["from"] == "1.0" and report["to"] == migrate.CURRENT and report["changed"]
    assert migrated["schemaVersion"] == migrate.CURRENT
    assert all("transitions" in track for track in migrated["tracks"])
    assert list(migrated).count("schemaVersion") == 1


def test_migration_is_idempotent_and_does_not_mutate_the_input() -> None:
    before = copy.deepcopy(FIXTURE)
    first, _ = migrate.migrate(FIXTURE)
    second, report = migrate.migrate(first)
    assert report["changed"] is False and second == first
    assert FIXTURE == before


def test_a_1_2_project_keeps_its_transitions() -> None:
    data = copy.deepcopy(FIXTURE)
    data["schemaVersion"] = "1.2"
    for track in data["tracks"]:
        track["transitions"] = []
    migrated, report = migrate.migrate(data)
    assert report["counts"]["transitions"] == 0
    assert migrated["schemaVersion"] == migrate.CURRENT


def test_an_unknown_or_newer_version_is_refused() -> None:
    newer = copy.deepcopy(FIXTURE)
    newer["schemaVersion"] = "1.6"
    with pytest.raises(migrate.MigrationError) as newer_error:
        migrate.migrate(newer)
    assert newer_error.value.code == "M02"


def test_an_invalid_project_is_not_blessed_by_migration() -> None:
    broken = copy.deepcopy(FIXTURE)
    broken["assets"][0]["uri"] = "../escape.mp4"
    with pytest.raises(migrate.MigrationError) as excinfo:
        migrate.migrate(broken)
    assert excinfo.value.code == "M01"


def test_the_cli_writes_and_checks(tmp_path: Path) -> None:
    path = tmp_path / "project.json"
    path.write_text(json.dumps(FIXTURE), encoding="utf-8")
    check = subprocess.run([sys.executable, str(TOOLS / "unified_project_migrate.py"), str(path), "--check"],
                           capture_output=True, text=True, timeout=60)
    assert check.returncode == 1
    written = subprocess.run([sys.executable, str(TOOLS / "unified_project_migrate.py"), str(path), "--write"],
                             capture_output=True, text=True, timeout=60)
    assert written.returncode == 0 and "migrated" in written.stdout
    assert json.loads(path.read_text(encoding="utf-8"))["schemaVersion"] == migrate.CURRENT
    again = subprocess.run([sys.executable, str(TOOLS / "unified_project_migrate.py"), str(path), "--check"],
                           capture_output=True, text=True, timeout=60)
    assert again.returncode == 0


def save_project(tmp_path: Path):
    path = tmp_path / "project.json"
    project = copy.deepcopy(FIXTURE)
    store.save(path, project)
    return path, store.load(path)


def test_autosave_is_a_sibling_file_that_records_its_base(tmp_path: Path) -> None:
    path, (project, revision) = save_project(tmp_path)
    record = store.autosave(path, project, base_revision=revision)
    assert (tmp_path / "project.json.autosave.json").exists()
    assert record["baseRevision"] == revision
    candidate = store.recover(path)
    assert candidate["stale"] is False and candidate["project"] == project


def test_recovery_reports_a_stale_candidate_instead_of_using_it(tmp_path: Path) -> None:
    path, (project, revision) = save_project(tmp_path)
    store.autosave(path, project, base_revision=revision)
    changed = copy.deepcopy(project)
    changed["name"] = "edited after the crash"
    store.save(path, changed, expected_revision=revision)
    candidate = store.recover(path)
    assert candidate["stale"] is True
    run = subprocess.run([sys.executable, str(TOOLS / "unified_project_store.py"), str(path), "recover"],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 1 and "refused" in run.stdout
    assert json.loads(path.read_text(encoding="utf-8"))["name"] == "edited after the crash"


def test_recovery_writes_the_autosave_back_when_it_is_current(tmp_path: Path) -> None:
    path, (project, revision) = save_project(tmp_path)
    newer = copy.deepcopy(project)
    newer["name"] = "work in progress"
    store.autosave(path, newer, base_revision=revision)
    run = subprocess.run([sys.executable, str(TOOLS / "unified_project_store.py"), str(path), "recover"],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0 and "recovered" in run.stdout
    assert store.load(path)[0]["name"] == "work in progress"
    assert store.recover(path) is None


def test_discard_removes_the_candidate_only(tmp_path: Path) -> None:
    path, (project, revision) = save_project(tmp_path)
    store.autosave(path, project, base_revision=revision)
    assert store.discard_autosave(path) is True
    assert store.load(path)[0] == project
    assert store.recover(path) is None
    assert store.discard_autosave(path) is False


def test_an_unreadable_autosave_is_an_error_not_a_silent_delete(tmp_path: Path) -> None:
    path, _ = save_project(tmp_path)
    (tmp_path / "project.json.autosave.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="Unreadable autosave"):
        store.recover(path)
    assert (tmp_path / "project.json.autosave.json").exists()
