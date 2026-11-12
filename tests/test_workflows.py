"""The eight working methods each produce an editable project — not a finished video.

`docs/unified-editor-roadmap.md` §4 asks for the methods; the honest test is that what comes out
validates, opens in the editor, and can be drawn by engine P. Anything a method cannot do (an audio
bed it must not invent, captions it was not given) fails with a code instead of a guess.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

import adapter_p  # noqa: E402
import workflows  # noqa: E402
from unified_project_check import validate  # noqa: E402

PROFILE = {"width": 108, "height": 192, "fps": {"num": 30, "den": 1}, "sampleRate": 48_000}
CAPTIONS = ["وجه واحد", "نفس المشروع", "القياس أولًا", "بلا ادّعاء"]


def stills(folder: Path, count: int = 3) -> list[dict]:
    folder.mkdir(parents=True, exist_ok=True)
    assets = []
    for index in range(count):
        payload = b"P6\n4 4\n255\n" + bytes([index * 40 % 255, 20, 30]) * 16
        (folder / f"s{index}.ppm").write_bytes(payload)
        assets.append({"id": f"a{index + 1}", "kind": "image", "uri": f"{folder.name}/s{index}.ppm",
                       "sha256": __import__("hashlib").sha256(payload).hexdigest()})
    return assets


@pytest.mark.parametrize("name", sorted(workflows.METHODS))
def test_every_method_builds_a_valid_renderable_project(tmp_path: Path, name: str) -> None:
    project = workflows.build(name, assets=stills(tmp_path / "shots"), captions=CAPTIONS, profile=PROFILE)
    assert validate(project) == []
    assert project["schemaVersion"] == "1.3" and project["name"]
    adapter = adapter_p.PAdapter()
    assert adapter.preflight(adapter.compile(project))["status"] == "supported"


@pytest.mark.parametrize("name", sorted(workflows.METHODS))
def test_captions_never_overlap_on_the_text_track(tmp_path: Path, name: str) -> None:
    project = workflows.build(name, assets=stills(tmp_path / "shots"), captions=CAPTIONS, profile=PROFILE)
    text_tracks = [track for track in project["tracks"] if track["kind"] == "text"]
    for track in text_tracks:
        spans = sorted((clip["start"], clip["start"] + clip["duration"]) for clip in track["clips"])
        for left, right in zip(spans, spans[1:], strict=False):
            assert right[0] >= left[1]


def test_a_method_that_needs_captions_refuses_to_invent_them(tmp_path: Path) -> None:
    with pytest.raises(workflows.WorkflowError) as excinfo:
        workflows.build("script", assets=stills(tmp_path / "shots"), captions=[])
    assert excinfo.value.code == "W03"


def test_one_still_can_carry_a_whole_method(tmp_path: Path) -> None:
    project = workflows.build("montage", assets=stills(tmp_path / "shots", count=1), profile=PROFILE)
    assert len(project["tracks"][0]["clips"]) == len(workflows.METHODS["montage"][1])
    assert validate(project) == []


def test_montage_carries_crossfades_between_every_pair(tmp_path: Path) -> None:
    project = workflows.build("montage", assets=stills(tmp_path / "shots"), profile=PROFILE)
    video = project["tracks"][0]
    assert len(video["transitions"]) == len(video["clips"]) - 1
    assert all(transition["kind"] == "crossfade" for transition in video["transitions"])


def test_free_edit_has_no_transitions(tmp_path: Path) -> None:
    project = workflows.build("free", assets=stills(tmp_path / "shots"), profile=PROFILE)
    assert project["tracks"][0]["transitions"] == []


def test_an_audio_bed_is_only_added_when_one_is_supplied(tmp_path: Path) -> None:
    assets = stills(tmp_path / "shots")
    project = workflows.build("podcast", assets=assets, captions=CAPTIONS, profile=PROFILE)
    assert [track["kind"] for track in project["tracks"]] == ["video", "text"]
    audio = {"id": "bed", "kind": "audio", "uri": "shots/s0.ppm", "duration": 9_600_000,
             "sha256": assets[0]["sha256"]}
    project = workflows.build("podcast", assets=assets, captions=CAPTIONS, audio=audio, profile=PROFILE)
    assert [track["kind"] for track in project["tracks"]] == ["video", "text", "audio"]


def test_caption_ink_flips_on_a_light_picture(tmp_path: Path) -> None:
    """A caption nobody can read is a caption that lies about what shipped."""
    root = tmp_path
    media = stills(root / "shots", count=2)
    (root / media[0]["uri"]).write_bytes(b"P6\n4 4\n255\n" + bytes([250, 250, 250]) * 16)
    import hashlib

    media[0]["sha256"] = hashlib.sha256((root / media[0]["uri"]).read_bytes()).hexdigest()
    (root / media[1]["uri"]).write_bytes(b"P6\n4 4\n255\n" + bytes([12, 12, 14]) * 16)
    media[1]["sha256"] = hashlib.sha256((root / media[1]["uri"]).read_bytes()).hexdigest()
    project = workflows.build("script", assets=media, captions=["أول", "ثاني"], profile=PROFILE, root=root)
    colors = [text["color"] for text in project["texts"]]
    assert colors[0] == workflows.INK_DARK and colors[1] == workflows.INK_LIGHT


def test_without_a_root_the_ink_stays_the_default_light(tmp_path: Path) -> None:
    project = workflows.build("script", assets=stills(tmp_path / "shots"), captions=["أول"], profile=PROFILE)
    assert project["texts"][0]["color"] == workflows.INK_LIGHT


def test_an_unknown_method_is_refused(tmp_path: Path) -> None:
    with pytest.raises(workflows.WorkflowError) as excinfo:
        workflows.build("wedding-video", assets=stills(tmp_path / "shots"))
    assert excinfo.value.code == "W02"


def test_the_cli_lists_and_writes(tmp_path: Path) -> None:
    listed = subprocess.run([sys.executable, str(TOOLS / "workflows.py"), "--list"],
                            capture_output=True, text=True, timeout=60)
    assert listed.returncode == 0
    assert all(name in listed.stdout for name in workflows.METHODS)
    media = tmp_path / "shots"
    stills(media)
    captions = tmp_path / "lines.txt"
    captions.write_text("\n".join(CAPTIONS), encoding="utf-8")
    out = tmp_path / "project.json"
    written = subprocess.run([sys.executable, str(TOOLS / "workflows.py"), "script",
                              "--media", str(media), "--captions", str(captions), "--out", str(out)],
                             capture_output=True, text=True, timeout=60)
    assert written.returncode == 0, written.stderr
    assert validate(json.loads(out.read_text(encoding="utf-8"))) == []
