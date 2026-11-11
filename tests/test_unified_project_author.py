"""Atomic authoring operations and integration with history and storage."""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_author import (  # noqa: E402
    add_clip,
    add_track,
    create_project,
    delete_clip,
    remove_asset,
    remove_track,
    reorder_track,
    set_duration,
    set_track_enabled,
)
from unified_project_history import History  # noqa: E402
from unified_project_store import load, save  # noqa: E402
from unified_render_graph import compile_project  # noqa: E402


def project():
    return json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))


def test_create_project_and_detach_profile():
    profile = project()["profile"]
    p = create_project("new", "مشروع", profile, 240000, duration=480000, seed=42)
    profile["fps"]["num"] = 1
    assert p["profile"]["fps"]["num"] == 30
    assert p["assets"] == p["tracks"] == [] and p["schemaVersion"] == "1.0"
    with pytest.raises(ValueError):
        create_project("new", "name", profile, 1)


def test_author_history_store_and_graph(tmp_path):
    p = project()
    h = History(p)
    h.apply(set_duration, 720000)
    h.apply(add_track, "top", "video", position=1)
    h.apply(add_clip, "top", "second", "a1", 480000, 240000, source_in=240000)
    h.apply(set_track_enabled, "top", False)
    snapshot = h.project
    assert [x["id"] for x in snapshot["tracks"]] == ["v1", "top"]
    assert not snapshot["tracks"][1]["enabled"]
    h.undo()
    assert h.project["tracks"][1]["enabled"]
    assert h.redo() == snapshot
    path = tmp_path / "project.json"
    revision = save(path, snapshot)
    loaded, loaded_revision = load(path)
    assert loaded == snapshot and loaded_revision == revision
    graph = compile_project(loaded)
    assert [t["trackId"] for t in graph["tracks"]] == ["v1", "top"]
    assert graph["tracks"][1]["clips"][0]["tickRange"] == [480000, 720000]
    assert p == project()


def test_reorder_remove_and_clip_deletion():
    p = project()
    p = add_track(p, "v2", "video", position=0)
    p = reorder_track(p, "v2", 1)
    assert [t["id"] for t in p["tracks"]] == ["v1", "v2"]
    with pytest.raises(ValueError, match="nonempty"):
        remove_track(p, "v1")
    with pytest.raises(ValueError, match="referenced"):
        remove_asset(p, "a1")
    p = delete_clip(p, "c1")
    assert p["duration"] == 480000
    p = remove_asset(p, "a1")
    p = remove_track(p, "v1")
    assert p["tracks"][0]["id"] == "v2" and p["assets"] == []


@pytest.mark.parametrize("operation", [
    lambda p: add_track(p, "v1", "video"),
    lambda p: add_track(p, "v2", "unknown"),
    lambda p: add_track(p, "v2", "video", position=True),
    lambda p: reorder_track(p, "v1", 1),
    lambda p: reorder_track(p, "missing", 0),
    lambda p: set_track_enabled(p, "v1", 1),
    lambda p: set_duration(p, 1),
    lambda p: set_duration(p, True),
    lambda p: add_clip(p, "v1", "c2", "a1", 0, 1),
    lambda p: add_clip(p, "v1", "c2", "missing", 0, 1),
    lambda p: add_clip(p, "v1", "c2", "a1", 0, 0),
    lambda p: add_clip(p, "v1", "c2", "a1", 0, 1, source_in=True),
    lambda p: delete_clip(p, "missing"),
    lambda p: remove_asset(p, "missing"),
    lambda p: remove_track(p, "missing"),
])
def test_rejections_are_atomic(operation):
    p = project()
    before = copy.deepcopy(p)
    with pytest.raises(ValueError):
        operation(p)
    assert p == before


def test_invalid_add_does_not_clear_redo():
    h = History(project())
    h.apply(add_track, "v2", "video")
    h.undo()
    with pytest.raises(ValueError):
        h.apply(add_track, "v1", "video")
    assert h.can_redo
    assert h.redo()["tracks"][1]["id"] == "v2"
