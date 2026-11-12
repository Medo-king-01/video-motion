"""The local editor: the same core functions, reachable from a page without a framework.

What is worth testing here is not the HTML — it is that every editing endpoint goes through the
validated core, that an edit is autosaved before the page can crash, and that a refusal is shown as
a refusal (HTTP 400 with the real message) instead of a silent no-op.
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import editor_server  # noqa: E402
import unified_project_store as store  # noqa: E402
import workflows  # noqa: E402


def stills(folder: Path, count: int = 2, size=(36, 64)) -> list[dict]:
    import hashlib

    folder.mkdir(parents=True, exist_ok=True)
    assets = []
    for index in range(count):
        payload = (f"P6\n{size[0]} {size[1]}\n255\n".encode("ascii")
                   + bytes([30 + index * 20, 20, 30]) * (size[0] * size[1]))
        (folder / f"s{index}.ppm").write_bytes(payload)
        assets.append({"id": f"a{index + 1}", "kind": "image", "uri": f"{folder.name}/s{index}.ppm",
                       "sha256": hashlib.sha256(payload).hexdigest()})
    return assets


@pytest.fixture()
def editor(tmp_path: Path):
    root = tmp_path
    project = workflows.build("script", assets=stills(root / "shots"), captions=["أول", "ثاني", "ثالث"],
                              profile={"width": 36, "height": 64, "fps": {"num": 30, "den": 1},
                                       "sampleRate": 48_000})
    path = root / "project.json"
    store.save(path, project)
    session = editor_server.Session(path)
    server = ThreadingHTTPServer(("127.0.0.1", 0),
                                 editor_server.make_handler(session, exporter=lambda s, p: {"file": "x.mp4"}))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        yield base, session, path
    finally:
        server.shutdown()
        server.server_close()


def call(base: str, path: str, payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(base + path, data=data,
                                     headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def test_the_page_and_the_project_are_served(editor) -> None:
    base, session, _ = editor
    status, body = call(base, "/")
    assert status == 200 and b"<html" in body.lower()
    status, body = call(base, "/api/project")
    payload = json.loads(body)
    assert status == 200 and payload["undo"] is False
    assert [track["kind"] for track in payload["project"]["tracks"]] == ["video", "text"]


def test_splitting_a_clip_autosaves_immediately(editor) -> None:
    base, session, path = editor
    status, body = call(base, "/api/op", {"op": "split", "clipId": "c1", "at": 120_000, "newId": "c1b"})
    assert status == 200
    project = json.loads(body)["project"]
    assert [clip["id"] for clip in project["tracks"][0]["clips"]][:2] == ["c1", "c1b"]
    candidate = store.recover(path)
    assert candidate is not None and candidate["project"]["tracks"][0]["clips"][1]["id"] == "c1b"


def test_undo_returns_the_previous_project_and_keeps_the_autosave_honest(editor) -> None:
    base, session, path = editor
    call(base, "/api/op", {"op": "split", "clipId": "c1", "at": 120_000, "newId": "c1b"})
    status, body = call(base, "/api/op", {"op": "undo"})
    project = json.loads(body)["project"]
    assert status == 200 and [clip["id"] for clip in project["tracks"][0]["clips"]][:1] == ["c1"]
    assert store.recover(path)["project"] == project


def test_saving_writes_the_file_and_drops_the_autosave(editor) -> None:
    base, session, path = editor
    call(base, "/api/op", {"op": "split", "clipId": "c1", "at": 120_000, "newId": "c1b"})
    status, body = call(base, "/api/save", {})
    assert status == 200 and json.loads(body)["saved"] is True
    assert store.recover(path) is None
    assert len(store.load(path)[0]["tracks"][0]["clips"]) >= 2


def test_a_caption_edit_reaches_the_project(editor) -> None:
    base, _, _ = editor
    status, body = call(base, "/api/op", {"op": "caption", "textId": "cap1", "value": "نفس المشروع"})
    assert status == 200
    assert json.loads(body)["project"]["texts"][0]["value"] == "نفس المشروع"


def test_an_invalid_edit_is_a_diagnosed_refusal(editor) -> None:
    base, _, _ = editor
    status, body = call(base, "/api/op", {"op": "split", "clipId": "c1", "at": 0, "newId": "x"})
    assert status == 400 and "split must be strictly inside" in body.decode("utf-8")
    status, body = call(base, "/api/op", {"op": "nonsense"})
    assert status == 400 and "unknown op" in body.decode("utf-8")


def test_a_frame_is_served_as_png(editor) -> None:
    base, _, _ = editor
    status, body = call(base, "/api/frame?index=0")
    assert status == 200 and body.startswith(b"\x89PNG")
    status, body = call(base, "/api/frame?index=999999")
    assert status == 400 and "V01" in body.decode("utf-8")


def test_the_capability_endpoint_reports_engine_p(editor) -> None:
    base, _, _ = editor
    status, body = call(base, "/api/capabilities")
    payload = json.loads(body)
    assert status == 200
    assert payload["capabilities"]["backend"] == "P"
    assert payload["preflight"]["status"] == "supported"


def test_recovery_is_offered_and_applied(editor) -> None:
    base, session, path = editor
    call(base, "/api/op", {"op": "split", "clipId": "c1", "at": 120_000, "newId": "c1b"})
    status, body = call(base, "/api/recover")
    assert status == 200 and json.loads(body)["candidate"]["stale"] is False
    status, body = call(base, "/api/recover", {"action": "discard"})
    assert status == 200 and store.recover(path) is None
    status, _ = call(base, "/api/recover", {"action": "apply"})
    assert status == 400


def test_the_media_bin_serves_a_thumbnail(editor) -> None:
    base, session, _ = editor
    status, body = call(base, "/api/media?asset=a1")
    assert status == 200 and body.startswith(b"\x89PNG")
    status, body = call(base, "/api/media?asset=ghost")
    assert status == 404


def test_uploading_media_copies_hashes_and_attaches_it(editor) -> None:
    base, session, path = editor
    payload = b"P6\n36 64\n255\n" + bytes([10, 20, 30]) * (36 * 64)
    request = urllib.request.Request(base + "/api/media/upload", data=payload,
                                     headers={"Content-Type": "application/octet-stream",
                                              "X-Filename": "still.ppm"})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read())
    assert response.status == 200
    asset = body["asset"]
    assert asset["uri"] == "media/still.ppm"
    assert (path.parent / "media/still.ppm").read_bytes() == payload
    import hashlib

    assert asset["sha256"] == hashlib.sha256(payload).hexdigest()
    assert any(item["id"] == asset["id"] for item in body["assets"])


def test_an_unsupported_upload_type_is_refused(editor) -> None:
    base, session, _ = editor
    request = urllib.request.Request(base + "/api/media/upload", data=b"hello",
                                     headers={"X-Filename": "notes.txt"})
    try:
        urllib.request.urlopen(request, timeout=60)
        raise AssertionError("expected a refusal")
    except urllib.error.HTTPError as error:
        assert error.code == 400
        assert "unsupported media type" in error.read().decode("utf-8")


def test_the_new_ops_edit_the_project(editor) -> None:
    base, session, _ = editor
    status, body = call(base, "/api/op", {"op": "add_track", "trackId": "t3", "kind": "text"})
    assert status == 200 and len(json.loads(body)["project"]["tracks"]) == 3
    status, body = call(base, "/api/op", {"op": "update_clip", "clipId": "c1", "duration": 120_000})
    assert status == 200 and json.loads(body)["project"]["tracks"][0]["clips"][0]["duration"] == 120_000
    status, body = call(base, "/api/op", {"op": "add_effect", "clipId": "c1",
                                           "effect": {"id": "op", "type": "opacity", "version": 1,
                                                      "enabled": True, "params": {"value": 8000}}})
    assert status == 200
    status, body = call(base, "/api/op", {"op": "add_keyframe", "clipId": "c1", "effectId": "op",
                                           "tick": 0, "value": 0})
    assert status == 200
    curve = json.loads(body)["project"]["tracks"][0]["clips"][0]["keyframes"][0]
    assert curve["points"][0]["value"] == 0
    status, body = call(base, "/api/op", {"op": "add_text", "textId": "cap9", "value": "جديد",
                                           "wrap": True})
    assert status == 200 and json.loads(body)["project"]["texts"][-1]["id"] == "cap9"
    status, body = call(base, "/api/op", {"op": "text", "textId": "cap1", "wrap": True,
                                           "animation": {"kind": "words-up", "stagger": 24_000}})
    assert status == 200 and json.loads(body)["project"]["texts"][0]["animation"]["kind"] == "words-up"
    status, body = call(base, "/api/op", {"op": "enabled", "trackId": "tx1", "enabled": False})
    assert status == 200 and json.loads(body)["project"]["tracks"][1]["enabled"] is False
