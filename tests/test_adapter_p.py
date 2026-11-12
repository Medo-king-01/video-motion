"""Engine P satisfies the frozen render-backend contract, and says what it cannot draw.

These tests are the evidence behind the `P` column of
`medo-motion/schema/backend-capabilities.json`: every state claimed there has a test here
that either renders a frame or watches the refusal happen.
"""
from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import adapter_p  # noqa: E402
import render_backend  # noqa: E402
from unified_project_check import validate  # noqa: E402

WIDTH, HEIGHT = 36, 64


def write_still(folder: Path, name: str = "shot.ppm", color=(20, 20, 22)) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    raw = bytes(color) * (WIDTH * HEIGHT)
    payload = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii") + raw
    (folder / name).write_bytes(payload)
    return {"id": "a1", "kind": "image", "uri": name, "sha256": hashlib.sha256(payload).hexdigest()}


def project(tmp_path: Path, **overrides) -> dict:
    data = {
        "schemaVersion": "1.3", "id": "adapter-demo", "name": "Adapter demo",
        "profile": {"width": WIDTH, "height": HEIGHT, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000},
        "timebase": 240_000, "duration": 240_000, "seed": 0,
        "assets": [write_still(tmp_path)],
        "texts": [{"id": "cap", "value": "وجه واحد", "font": "Cairo", "size": 14,
                   "color": "#f3f2f1", "align": "center", "direction": "rtl"}],
        "tracks": [
            {"id": "v1", "kind": "video", "enabled": True, "clips": [
                {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 240_000,
                 "sourceIn": 0, "effects": [], "keyframes": []}]},
            {"id": "t1", "kind": "text", "enabled": True, "clips": [
                {"id": "x1", "kind": "media", "textId": "cap", "start": 0, "duration": 240_000,
                 "sourceIn": 0, "effects": [], "keyframes": []}]},
        ],
    }
    data.update(overrides)
    assert validate(data) == []
    return data


def test_the_adapter_is_conformant_and_matches_the_manifest() -> None:
    adapter = adapter_p.PAdapter()
    assert render_backend.conformance_problems(adapter) == []
    assert adapter.capabilities()["backendVersion"] == adapter_p.VERSION


def test_compile_marks_the_graph_executable_and_keeps_the_project_untouched(tmp_path: Path) -> None:
    data = project(tmp_path)
    before = copy.deepcopy(data)
    graph = adapter_p.PAdapter().compile(data)
    assert graph["executable"] is True and graph["backend"]["name"] == "P"
    assert graph["graphSha256"] == json.loads(json.dumps(graph))["graphSha256"]
    assert data == before


def test_preflight_is_supported_for_stills_text_and_crossfades(tmp_path: Path) -> None:
    adapter = adapter_p.PAdapter()
    readiness = adapter.preflight(adapter.compile(project(tmp_path)))
    assert readiness["status"] == "supported" and readiness["diagnostics"] == []


@pytest.mark.parametrize("mutation,code", [
    # A graphics track is still refused: nothing draws it.
    (lambda p: p["tracks"].append({"id": "g", "kind": "graphics", "enabled": True, "clips": []}), "R02"),

])
def test_unsupported_features_are_refused_before_a_frame_is_drawn(tmp_path: Path, mutation, code) -> None:
    data = project(tmp_path)
    if code == "R02":
        data["assets"].append({"id": "a3", "kind": "audio", "uri": "tone.wav",
                               "sha256": data["assets"][0]["sha256"], "duration": 480_000})
        (tmp_path / "tone.wav").write_bytes(b"RIFF")
    mutation(data)
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(data)
    readiness = adapter.preflight(graph)
    assert readiness["status"] == "unsupported"
    assert any(diagnostic["code"] == code for diagnostic in readiness["diagnostics"])
    with pytest.raises(adapter_p.AdapterError) as excinfo:
        adapter.render(graph, (0, 1), tmp_path / "out", {"root": tmp_path})
    assert excinfo.value.code == code


def test_audio_speed_is_mixed_not_refused(tmp_path: Path) -> None:
    """R03 is retired: a 2x clip is resampled by the mixer and recorded as the audio artifact."""
    import wave

    tone = tmp_path / "vo.wav"
    with wave.open(str(tone), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(48_000)
        handle.writeframes(b"\x10\x00" * 24_000)
    data = project(tmp_path)
    data["assets"].append({"id": "au", "kind": "audio", "uri": "vo.wav", "duration": 240_000,
                           "sha256": __import__("hashlib").sha256(tone.read_bytes()).hexdigest()})
    data["tracks"].append({"id": "at", "kind": "audio", "enabled": True, "clips": [
        {"id": "am", "kind": "media", "assetId": "au", "start": 0, "duration": 120_000,
         "sourceIn": 0, "speed": {"num": 2, "den": 1}, "effects": [], "keyframes": []}]})
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(data)
    assert adapter.preflight(graph)["status"] == "supported"
    result = adapter.render(graph, (0, 2), tmp_path / "out", {"root": tmp_path})
    assert result["manifest"]["audio"]["file"] == "mix.wav"
    assert (tmp_path / "out" / "mix.wav").is_file()


def test_a_video_clip_is_decoded_not_refused(tmp_path: Path) -> None:
    """The old R05 refusal is gone: a real video frame is pulled at the clip's source tick."""
    import av

    video = tmp_path / "clip.mp4"
    with av.open(str(video), mode="w") as container:
        stream = container.add_stream("mpeg4", rate=30)
        stream.width, stream.height, stream.pix_fmt = WIDTH, HEIGHT, "yuv420p"
        for index in range(6):
            frame = av.VideoFrame.from_ndarray(
                __import__("numpy").full((HEIGHT, WIDTH, 3), 40 + index * 30, dtype="uint8"), format="rgb24")
            frame.pts = index
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    data = project(tmp_path)
    payload = video.read_bytes()
    data["assets"] = [{"id": "a1", "kind": "video", "uri": "clip.mp4", "duration": 240_000,
                       "sha256": hashlib.sha256(payload).hexdigest()}]
    data["tracks"][0]["clips"][0]["speed"] = {"num": 1, "den": 1}
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(data)
    assert adapter.preflight(graph)["status"] == "supported"
    out = tmp_path / "frames"
    adapter.render(graph, (0, 2), out, {"root": tmp_path, "audio": False})
    manifest = json.loads((out / "render.json").read_text(encoding="utf-8"))
    first = (out / manifest["written"][0]["file"]).read_bytes()
    assert first[3::4] == b"\xff" * (WIDTH * HEIGHT)


def test_keyframed_opacity_is_drawn(tmp_path: Path) -> None:
    data = project(tmp_path)
    clip = data["tracks"][0]["clips"][0]
    clip["effects"] = [{"id": "o", "type": "opacity", "version": 1, "enabled": True,
                        "params": {"value": 10000}}]
    clip["keyframes"] = [{"property": "value", "effectId": "o",
                          "points": [{"t": 0, "value": 0, "interpolation": "linear"},
                                     {"t": 240_000, "value": 10000, "interpolation": "linear"}]}]
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(data)
    assert adapter.preflight(graph)["status"] == "supported"
    from unified_reference_preview import render_frame

    early = render_frame(data, tmp_path, 1)["pixels"]
    late = render_frame(data, tmp_path, 25)["pixels"]
    assert early[3] < late[3]


def test_a_wipe_transition_is_drawn_left_to_right(tmp_path: Path) -> None:
    data = project(tmp_path)
    second = {"id": "a2", "kind": "image", "uri": "dark.ppm",
              "sha256": data["assets"][0]["sha256"]}
    payload = f"P6\n{WIDTH} {HEIGHT}\n255\n".encode("ascii") + bytes([250, 250, 250]) * (WIDTH * HEIGHT)
    (tmp_path / "dark.ppm").write_bytes(payload)
    second["sha256"] = hashlib.sha256(payload).hexdigest()
    data["assets"].append(second)
    video = data["tracks"][0]
    video["clips"] = [
        {"id": "c1", "kind": "media", "assetId": "a1", "start": 0, "duration": 120_000,
         "sourceIn": 0, "effects": [], "keyframes": []},
        {"id": "c2", "kind": "media", "assetId": "a2", "start": 120_000, "duration": 120_000,
         "sourceIn": 0, "effects": [], "keyframes": []}]
    video["transitions"] = [{"id": "tw1", "kind": "wipe", "direction": "left",
                             "fromClipId": "c1", "toClipId": "c2", "duration": 8_000}]
    from unified_project_check import validate
    from unified_reference_preview import render_frame

    assert validate(data) == []
    tick_mid = 120_000
    frame = render_frame(data, tmp_path, tick_mid // 8_000)["pixels"]
    left = frame[(HEIGHT // 2) * WIDTH * 4 + 4]
    right = frame[(HEIGHT // 2) * WIDTH * 4 + (WIDTH - 2) * 4]
    assert left != right  # half the frame already switched to the incoming picture


def test_render_writes_the_range_and_a_manifest_atomically(tmp_path: Path) -> None:
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(project(tmp_path))
    out = tmp_path / "frames"
    seen = []
    result = adapter.render(graph, (0, 3), out, {"root": tmp_path,
                                                 "progress": lambda done, total: seen.append((done, total))})
    assert seen == [(1, 3), (2, 3), (3, 3)]
    manifest = json.loads((out / "render.json").read_text(encoding="utf-8"))
    assert manifest["frames"] == [0, 3] and len(manifest["written"]) == 3
    assert result["artifact"] == str(out)
    for entry in manifest["written"]:
        payload = (out / entry["file"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == entry["sha256"]


def test_the_exported_frame_is_the_previewed_frame(tmp_path: Path) -> None:
    """The claim the whole adapter rests on: same graph in, same pixels out."""
    from unified_reference_preview import render_frame

    data = project(tmp_path)
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(data)
    out = tmp_path / "frames"
    adapter.render(graph, (0, 2), out, {"root": tmp_path})
    manifest = json.loads((out / "render.json").read_text(encoding="utf-8"))
    for entry in manifest["written"]:
        assert entry["sha256"] == hashlib.sha256(
            render_frame(data, tmp_path, entry["frame"])["pixels"]).hexdigest()


def test_cancelling_leaves_no_half_artifact(tmp_path: Path) -> None:
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(project(tmp_path))
    adapter.cancel()
    out = tmp_path / "cancelled"
    with pytest.raises(adapter_p.AdapterError) as excinfo:
        adapter.render(graph, (0, 2), out, {"root": tmp_path})
    assert excinfo.value.code == "R09"
    assert not out.exists()
    assert not list(tmp_path.glob(".p-render-*"))


def test_an_existing_output_folder_is_not_overwritten(tmp_path: Path) -> None:
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(project(tmp_path))
    out = tmp_path / "frames"
    out.mkdir()
    (out / "keep.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(adapter_p.AdapterError) as excinfo:
        adapter.render(graph, (0, 1), out, {"root": tmp_path})
    assert excinfo.value.code == "R10"
    assert (out / "keep.txt").read_text(encoding="utf-8") == "mine"


def test_the_range_is_half_open_and_bounded(tmp_path: Path) -> None:
    adapter = adapter_p.PAdapter()
    graph = adapter.compile(project(tmp_path))
    with pytest.raises(adapter_p.AdapterError) as excinfo:
        adapter.render(graph, (0, 999), tmp_path / "out", {"root": tmp_path})
    assert excinfo.value.code == "R08"


def test_the_cli_reports_readiness_and_renders(tmp_path: Path) -> None:
    data = project(tmp_path)
    path = tmp_path / "project.json"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    readiness = subprocess.run([sys.executable, str(TOOLS / "adapter_p.py"), str(path), "--preflight"],
                               capture_output=True, text=True, timeout=120)
    assert readiness.returncode == 0 and '"supported"' in readiness.stdout
    rendered = subprocess.run([sys.executable, str(TOOLS / "adapter_p.py"), str(path), "--out",
                               str(tmp_path / "cli-frames"), "--frames", "0:2"],
                              capture_output=True, text=True, timeout=120)
    assert rendered.returncode == 0, rendered.stderr
    assert (tmp_path / "cli-frames" / "render.json").exists()
