"""Pure media editing is atomic, tick-exact and does not imply rendering support."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_project_check import validate  # noqa: E402
from unified_project_edit import move_clip, split_clip, trim_clip  # noqa: E402


def project():
    return json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))


def test_split_exact_and_immutable():
    p = project()
    before = copy.deepcopy(p)
    edited = split_clip(p, "c1", 120000, "c2")
    a, b = edited["tracks"][0]["clips"]
    assert (a["start"], a["duration"], a["sourceIn"]) == (0, 120000, 0)
    assert (b["start"], b["duration"], b["sourceIn"]) == (120000, 360000, 120000)
    assert p == before and not validate(edited)


def test_trim_and_move():
    p = project()
    p["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": []})
    trimmed = trim_clip(p, "c1", 20000, 200000)
    clip = trimmed["tracks"][0]["clips"][0]
    assert (clip["start"], clip["duration"], clip["sourceIn"]) == (20000, 180000, 20000)
    moved = move_clip(trimmed, "c1", "v2", 300000)
    assert not moved["tracks"][0]["clips"]
    assert moved["tracks"][1]["clips"][0]["sourceIn"] == 20000
    assert not validate(moved)


def test_image_split_and_trim_keep_source_zero():
    p = project()
    p["assets"][0]["kind"] = "image"
    del p["assets"][0]["duration"]
    result = split_clip(p, "c1", 200, "c2")
    result = trim_clip(result, "c2", 300, 400)
    assert result["tracks"][0]["clips"][1]["sourceIn"] == 0


@pytest.mark.parametrize("edit", [
    lambda p: split_clip(p, "c1", 0, "new"),
    lambda p: split_clip(p, "c1", 480000, "new"),
    lambda p: split_clip(p, "c1", 200, "a1"),
    lambda p: split_clip(p, "c1", True, "new"),
    lambda p: trim_clip(p, "c1", 0, 480001),
    lambda p: trim_clip(p, "c1", 10, 10),
    lambda p: move_clip(p, "c1", "unknown", 0),
    lambda p: move_clip(p, "c1", "v1", 1),
    lambda p: split_clip(p, "unknown", 1, "new"),
])
def test_failure_is_atomic(edit):
    p = project()
    before = copy.deepcopy(p)
    with pytest.raises(ValueError):
        edit(p)
    assert p == before


def test_move_rejects_overlap_and_incompatible_track():
    p = split_clip(project(), "c1", 240000, "c2")
    with pytest.raises(ValueError, match="overlaps"):
        move_clip(p, "c2", "v1", 100)
    p["tracks"].append({"id": "text", "kind": "text", "enabled": True, "clips": []})
    with pytest.raises(ValueError, match="incompatible"):
        move_clip(p, "c1", "text", 0)


def test_rejects_unsupported_input_without_dropping_data():
    p = project()
    p["tracks"][0]["clips"][0]["effects"] = [{"id": "effect"}]
    before = copy.deepcopy(p)
    with pytest.raises(ValueError, match="Invalid or unsupported"):
        split_clip(p, "c1", 1, "c2")
    assert p == before


def test_ripple_delete_selected_only_and_preserves_duration():
    from unified_project_edit import ripple_delete

    p = split_clip(project(), "c1", 120000, "c2")
    p = split_clip(p, "c2", 240000, "c3")
    p["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": []})
    p["tracks"][1]["clips"].append({**p["tracks"][0]["clips"][0], "id": "c4"})
    before = copy.deepcopy(p)
    result = ripple_delete(p, 120000, 240000, ["v1"])
    clips = result["tracks"][0]["clips"]
    assert [(c["id"], c["start"], c["sourceIn"]) for c in clips] == [("c1", 0, 0), ("c3", 120000, 240000)]
    assert result["tracks"][1] == before["tracks"][1]
    assert result["duration"] == before["duration"] and p == before
    assert not validate(result)


@pytest.mark.parametrize("start,end,ids", [
    (1, 100, ["v1"]), (0, 1, ["v1"]), (0, 0, ["v1"]),
    (0, 480001, ["v1"]), (0, 480000, []), (0, 480000, ["v1", "v1"]),
    (0, 480000, ["missing"]), (0, 480000, "v1"),
])
def test_ripple_delete_rejects_without_mutation(start, end, ids):
    from unified_project_edit import ripple_delete

    p = project()
    before = copy.deepcopy(p)
    with pytest.raises(ValueError):
        ripple_delete(p, start, end, ids)
    assert p == before


def test_ripple_on_gap_and_end_boundaries():
    from unified_project_edit import ripple_delete

    p = trim_clip(project(), "c1", 200000, 300000)
    r = ripple_delete(p, 0, 100000, ["v1"])
    assert r["tracks"][0]["clips"][0]["start"] == 100000
    r = ripple_delete(r, 100000, 200000, ["v1"])
    assert not r["tracks"][0]["clips"]


def test_history_undo_redo_atomicity_and_snapshots():
    from unified_project_history import History

    original = project()
    history = History(original, limit=2)
    original["name"] = "outside mutation"
    first = history.apply(split_clip, "c1", 120000, "c2")
    history.apply(trim_clip, "c2", 180000, 480000)
    assert history.undo() == first
    assert history.redo()["tracks"][0]["clips"][1]["start"] == 180000
    history.undo()
    exposed = history.project
    exposed["name"] = "not saved"
    assert history.project == first
    with pytest.raises(ValueError):
        history.apply(move_clip, "c2", "missing", 0)
    assert history.can_redo and history.project == first
    history.apply(move_clip, "c2", "v1", 120000)  # no-op preserves redo
    assert history.can_redo
    history.apply(trim_clip, "c2", 150000, 480000)
    assert not history.can_redo
    assert history.undo() == first
    assert history.undo()["name"] == "Example"
    with pytest.raises(ValueError, match="No edit"):
        history.undo()


def test_history_defends_against_malicious_or_invalid_operation():
    from unified_project_history import History

    h = History(project())
    before = h.project

    def invalid(p):
        p["duration"] = -1
        return p

    with pytest.raises(ValueError):
        h.apply(invalid)
    assert h.project == before and not h.can_undo


def test_exact_time_and_snap_ties():
    from unified_project_time import frame_ticks, output_lengths, snap

    p = project()
    assert frame_ticks(p) == 8000
    assert output_lengths(p) == (60, 96000)
    p["duration"] += 1
    assert output_lengths(p) == (61, 96001)
    assert snap(p, 4000, 4000, playhead=8000) == (8000, "playhead", None)
    assert snap(p, 4000, 4000, exclude_clip_id="c1") == (0, "frame", None)
    assert snap(p, 100, 99, frames=False) == (100, None, None)
    assert snap(p, 100, 100, frames=False) == (0, "clip", "c1")


def test_fractional_fps_and_input_bounds():
    from unified_project_time import frame_ticks, snap

    p = project()
    p["profile"]["fps"] = {"num": 30000, "den": 1001}
    assert frame_ticks(p) == 8008
    with pytest.raises(ValueError):
        snap(p, p["duration"] + 1, 0)
    with pytest.raises(ValueError):
        snap(p, 0, -1)


def test_store_create_roundtrip_and_conflict(tmp_path):
    from unified_project_store import ConflictError, load, save

    path = tmp_path / "project.json"
    p = project()
    p["name"] = "مشروع عربي"
    rev = save(path, p)
    loaded, old_rev = load(path)
    assert loaded == p and rev == old_rev
    with pytest.raises(ConflictError):
        save(path, p)
    changed = trim_clip(loaded, "c1", 1, 480000)
    new_rev = save(path, changed, old_rev)
    assert load(path) == (changed, new_rev)
    with pytest.raises(ConflictError):
        save(path, p, old_rev)
    assert load(path) == (changed, new_rev)


def test_store_never_overwrites_unknown_data_or_invalid_input(tmp_path):
    import hashlib

    from unified_project_store import save

    path = tmp_path / "project.json"
    unsupported = b'{"schemaVersion": "2.0", "unknown": 42}'
    path.write_bytes(unsupported)
    rev = hashlib.sha256(unsupported).hexdigest()
    with pytest.raises(ValueError):
        save(path, project(), rev)
    assert path.read_bytes() == unsupported
    invalid = project()
    invalid["unknown"] = 1
    with pytest.raises(ValueError):
        save(path, invalid, rev)
    assert path.read_bytes() == unsupported


def test_store_lock_and_failure_cleanup(tmp_path, monkeypatch):
    import unified_project_store as store

    path = tmp_path / "project.json"
    rev = store.save(path, project())
    lock = tmp_path / "project.json.lock"
    lock.write_text("other writer")
    with pytest.raises(store.ConflictError):
        store.save(path, project(), rev)
    assert lock.exists()
    lock.unlink()
    before = path.read_bytes()

    def fail(*args):
        raise OSError("replace failed")

    monkeypatch.setattr(store.os, "replace", fail)
    with pytest.raises(OSError):
        store.save(path, project(), rev)
    assert path.read_bytes() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["project.json"]


def test_store_rejects_symlink(tmp_path):
    from unified_project_store import load, save

    real = tmp_path / "real.json"
    real.write_text("untouched")
    link = tmp_path / "project.json"
    try:
        link.symlink_to(real)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(ValueError, match="symlink"):
        load(link)
    with pytest.raises(ValueError, match="symlink"):
        save(link, project())
    assert real.read_text() == "untouched"


def test_history_limit_and_redo_end():
    from unified_project_history import History

    h = History(project(), limit=1)
    h.apply(split_clip, "c1", 120000, "c2")
    first = h.project
    h.apply(trim_clip, "c2", 180000, 480000)
    assert h.undo() == first
    with pytest.raises(ValueError, match="No edit"):
        h.undo()
    h.redo()
    with pytest.raises(ValueError, match="No edit"):
        h.redo()


def test_store_missing_changed_and_duplicate_keys(tmp_path):
    import hashlib

    from unified_project_store import ConflictError, load, save

    path = tmp_path / "project.json"
    rev = save(path, project())
    path.unlink()
    with pytest.raises(ConflictError, match="no longer exists"):
        save(path, project(), rev)
    content = b'{"id": "x", "id": "y"}'
    path.write_bytes(content)
    with pytest.raises(ValueError, match="duplicate"):
        load(path)
    with pytest.raises(ValueError, match="duplicate"):
        save(path, project(), hashlib.sha256(content).hexdigest())
    assert path.read_bytes() == content
