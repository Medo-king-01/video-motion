"""Engine-K scene cache: one scene's edit must not cost the whole reel."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import render_scenes  # noqa: E402

TOOLKIT = ROOT / "tools" / "toolkit" / "node_modules"
HAS_NODE = shutil.which("node") is not None


def make_skeleton(tmp_path: Path, scenes: list[dict]) -> Path:
    """A project with real `data.js` (Node parses it) but no renderer to launch."""
    project = tmp_path / "reel"
    (project / "src" / "scenes").mkdir(parents=True)
    (project / "src" / "lib").mkdir()
    (project / "src" / "index.html").write_text("<canvas id=c></canvas>\n", encoding="utf-8")
    (project / "src" / "main.js").write_text("// main\n", encoding="utf-8")
    (project / "src" / "render.js").write_text("// render\n", encoding="utf-8")
    (project / "src" / "lib" / "kit.js").write_text("// kit\n", encoding="utf-8")
    entries = ", ".join(f"{{ id: '{s['id']}', start: {s['start']}, end: {s['end']} }}" for s in scenes)
    (project / "src" / "data.js").write_text(
        f"export const W = 1080, H = 1920, FPS = 30;\nexport const scenes = [{entries}];\n"
        "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    for scene in scenes:
        (project / "src" / "scenes" / f"{scene['id']}.js").write_text(
            f"export function draw() {{ /* {scene['id']} */ }}\n", encoding="utf-8")
    return project


TWO = [{"id": "intro", "start": 0, "end": 1}, {"id": "outro", "start": 1, "end": 2.5}]


def test_scene_key_ignores_other_scenes(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    shared = render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)
    intro_before = render_scenes.scene_key(shared, project, TWO[0])
    outro_before = render_scenes.scene_key(shared, project, TWO[1])

    (project / "src" / "scenes" / "outro.js").write_text("export function draw() { /* v2 */ }\n",
                                                         encoding="utf-8")
    shared_after = render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)
    assert shared_after == shared  # the shared layer did not change
    assert render_scenes.scene_key(shared_after, project, TWO[0]) == intro_before
    assert render_scenes.scene_key(shared_after, project, TWO[1]) != outro_before


def test_shared_key_tracks_libs_and_encode_settings(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    base = render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)
    assert base == render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)
    assert base != render_scenes.shared_key(project, fps=30, scale=1.0, crf=18)
    assert base != render_scenes.shared_key(project, fps=15, scale=1.0, crf=13)
    (project / "src" / "lib" / "kit.js").write_text("// kit v2\n", encoding="utf-8")
    assert base != render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)


def test_expected_frames_rounds_half_open_ranges() -> None:
    assert render_scenes.expected_frames({"start": 0, "end": 1}, 30) == 30
    assert render_scenes.expected_frames({"start": 1, "end": 2.5}, 30) == 45
    assert render_scenes.expected_frames({"start": 2, "end": 2}, 30) == 1  # never zero frames


@pytest.mark.skipif(not HAS_NODE, reason="node is required to read data.js")
def test_load_scenes_reads_the_renderers_own_source(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    assert render_scenes.load_scenes(project) == TWO


@pytest.mark.skipif(not HAS_NODE, reason="node is required to read data.js")
def test_missing_scene_module_names_the_file(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    (project / "src" / "scenes" / "outro.js").unlink()
    shared = render_scenes.shared_key(project, fps=30, scale=1.0, crf=13)
    with pytest.raises(SystemExit) as error:
        render_scenes.scene_key(shared, project, TWO[1])
    assert "src/scenes/outro.js" in str(error.value)


def test_non_k_project_is_rejected(tmp_path: Path, capsys) -> None:
    project = tmp_path / "p"
    project.mkdir()
    assert render_scenes.main([str(project)]) == 2
    assert "not an engine-K project" in capsys.readouterr().err


@pytest.mark.slow
def test_real_run_reuses_unchanged_scene_and_refuses_overwrite(tmp_path: Path) -> None:
    """The acceptance criterion, measured: edit one scene, one scene renders."""
    if not (TOOLKIT / "playwright-core").is_dir() or not HAS_NODE:
        pytest.skip("toolkit node_modules missing — run: npm ci --prefix tools/toolkit")
    sys.path.insert(0, str(ROOT / "tools"))
    import time_to_first_video as ttfv  # noqa: PLC0415 - test helper shared with the TTFV suite

    project = tmp_path / "k"
    subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "k", "--engine", "k",
                    "--out", str(project)], check=True, capture_output=True)
    (project / "node_modules").symlink_to(TOOLKIT)
    (project / "src" / "data.js").write_text(
        (project / "src" / "data.js").read_text(encoding="utf-8").split("export const scenes = [")[0]
        + "export const scenes = [\n  { id: 'example', start: 0, end: 1 },\n"
          "  { id: 'second', start: 1, end: 2.5 },\n];\n"
        + "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    shutil.copy(project / "src" / "scenes" / "example.js", project / "src" / "scenes" / "second.js")
    (project / "plan" / "beats.json").write_text(json.dumps({
        "duration": 2.5, "bpm": 100,
        "scenes": [{"id": "example", "start": 0.0, "end": 1.0},
                   {"id": "second", "start": 1.0, "end": 2.5}],
    }), encoding="utf-8")
    direction = dict(ttfv.DIRECTION)
    direction["scenes"] = [dict(ttfv.DIRECTION["scenes"][0], scene=index) for index in (1, 2)]
    (project / "plan" / "text-direction.json").write_text(json.dumps(direction, ensure_ascii=False),
                                                          encoding="utf-8")

    assert render_scenes.main([str(project)]) == 0
    manifest = json.loads((project / "cache" / "scenes" / "manifest.json").read_text(encoding="utf-8"))
    assert (manifest["hits"], manifest["misses"]) == (0, 2)
    master = project / "out" / "master.mp4"
    info = ttfv.probe(master)
    assert (info["width"], info["height"]) == (1080, 1920)
    assert info["duration_s"] == pytest.approx(2.5, abs=0.1)

    intro_segment = next(project.glob("cache/scenes/example-*.mp4"))
    intro_mtime = intro_segment.stat().st_mtime_ns

    # a second run with no edits: everything is a hit, nothing is touched
    assert render_scenes.main([str(project), "--force"]) == 0
    manifest = json.loads((project / "cache" / "scenes" / "manifest.json").read_text(encoding="utf-8"))
    assert (manifest["hits"], manifest["misses"]) == (2, 0)
    assert intro_segment.stat().st_mtime_ns == intro_mtime

    # editing `second` only must leave `example` on disk and render exactly one scene
    (project / "src" / "scenes" / "second.js").write_text(
        (project / "src" / "scenes" / "second.js").read_text(encoding="utf-8") + "\n// v2\n",
        encoding="utf-8")
    assert render_scenes.main([str(project), "--force"]) == 0
    manifest = json.loads((project / "cache" / "scenes" / "manifest.json").read_text(encoding="utf-8"))
    assert (manifest["hits"], manifest["misses"]) == (1, 1)
    assert next(project.glob("cache/scenes/second-*.mp4")).stat().st_mtime_ns > intro_mtime
    assert intro_segment.stat().st_mtime_ns == intro_mtime

    # the output is never overwritten silently
    assert render_scenes.main([str(project)]) == 2
