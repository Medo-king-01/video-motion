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
    shared = _shared(project)
    intro_before = render_scenes.scene_key(shared, project, TWO[0])
    outro_before = render_scenes.scene_key(shared, project, TWO[1])

    (project / "src" / "scenes" / "outro.js").write_text("export function draw() { /* v2 */ }\n",
                                                         encoding="utf-8")
    shared_after = _shared(project)
    assert shared_after == shared  # the shared layer did not change
    assert render_scenes.scene_key(shared_after, project, TWO[0]) == intro_before
    assert render_scenes.scene_key(shared_after, project, TWO[1]) != outro_before


def test_shared_key_tracks_libs_and_encode_settings(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    base = _shared(project)
    assert base == _shared(project)
    assert base != _shared(project, crf=18)
    assert base != _shared(project, fps=15)
    (project / "src" / "lib" / "kit.js").write_text("// kit v2\n", encoding="utf-8")
    assert base != _shared(project)


def _shared(project: Path, *, fps: int = 30, crf: int = 13, scenes: list[dict] = TWO, **options) -> str:
    return render_scenes.shared_key(project, fps=fps, scale=1.0, crf=crf,
                                    scene_ids=[scene["id"] for scene in scenes], **options)


def _keys(project: Path, scenes: list[dict] = TWO, **options) -> dict[str, str]:
    """Every scene's cache key, exactly as `run()` builds it."""
    shared = _shared(project, scenes=scenes, **options)
    return {scene["id"]: render_scenes.scene_key(shared, project, scene) for scene in scenes}


def _write(project: Path, relative: str, content: str | bytes) -> None:
    target = project / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8")


# Every file the renderer can put on screen. The plan list is render.js's own ALLOWED_PLANS (asserted
# below against the template, so a plan the server starts serving cannot be forgotten here); the
# rest is one representative per class the loopback server exposes: /assets/**, and all of src/.
PLAN_INPUTS = ("plan/text-direction.json", "plan/beats.json", "plan/stage.json", "plan/slide-wall.json",
               "plan/one-take.json", "plan/copy.json", "plan/word-timings.json")
ASSET_INPUTS = ("assets/fonts/fonts.json", "assets/fonts/Cairo/Cairo_800ExtraBold.ttf",
                "assets/poses/poses.json", "assets/poses/wave.png", "assets/images/deep/hero.jpg",
                "assets/icons/arrow.svg", "assets/clips/b-roll.mp4")
SRC_INPUTS = ("src/lib/brand.js", "src/lib/nested/tokens.json", "src/brand.json", "src/style.css",
              "src/scenes/shared-helper.js", "src/components/card.js")
VISUAL_INPUTS = PLAN_INPUTS + ASSET_INPUTS + SRC_INPUTS

# Files that exist in every project but never reach a frame: the server refuses them (not in
# ALLOWED_PLANS, dot-paths) or they are sound/notes/outputs.
INERT_INPUTS = ("plan/script.md", "plan/visual-direction.json", "plan/cues.json", "BRIEF.md", "PROGRESS.md",
                "assets/vo/vo.wav", "assets/sfx/whoosh.mp3", "assets/vo/TAKE2.WAV", "assets/music/bed.Flac",
                "assets/a.m4a", "assets/a.aac", "assets/a.ogg", "assets/.DS_Store", "src/.cache/x.js", "plan/.stage.json.swp",
                "out/final_audio.wav", "cache/scenes/old-000000000000.mp4", "cache/scenes.log")


def test_the_plan_list_is_the_renderers_own() -> None:
    """`ALLOWED_PLANS` in the K template is the source of truth for which plans can be fetched."""
    import re  # noqa: PLC0415
    source = (ROOT / "medo-motion" / "templates" / "render" / "render.js").read_text(encoding="utf-8")
    declared = re.search(r"const ALLOWED_PLANS=\[([^\]]*)\]", source)
    assert declared, "render.js no longer declares ALLOWED_PLANS — the scene cache must learn the new rule"
    served = sorted(item.strip("'\" /") for item in declared.group(1).split(","))
    assert served == sorted(PLAN_INPUTS)


@pytest.mark.parametrize("relative", VISUAL_INPUTS)
@pytest.mark.parametrize("change", ["edit", "create", "delete"])
def test_every_visual_input_changes_every_scene_key(tmp_path: Path, relative: str, change: str) -> None:
    """Edit, add or remove any file a frame can read: no scene may keep its old key."""
    project = make_skeleton(tmp_path, TWO)
    if change != "create":
        _write(project, relative, "v1")
    before = _keys(project)
    if change == "delete":
        (project / relative).unlink()
    else:
        _write(project, relative, "v2")
    after = _keys(project)
    assert all(after[scene] != before[scene] for scene in before), f"{change} {relative}: a stale segment would be reused"


@pytest.mark.parametrize("relative", INERT_INPUTS)
def test_inert_files_do_not_touch_the_cache(tmp_path: Path, relative: str) -> None:
    """The reverse: a file no frame can read must not cost a re-render."""
    project = make_skeleton(tmp_path, TWO)
    before = _keys(project)
    _write(project, relative, "v1")
    assert _keys(project) == before
    _write(project, relative, "v2 — longer")
    assert _keys(project) == before


def test_equal_bytes_under_another_name_is_a_different_input(tmp_path: Path) -> None:
    """Renaming an asset changes what a URL resolves to, even though no byte changed."""
    project = make_skeleton(tmp_path, TWO)
    _write(project, "assets/poses/wave.png", "same")
    before = _keys(project)
    (project / "assets/poses/wave.png").rename(project / "assets/poses/point.png")
    assert all(_keys(project)[scene] != before[scene] for scene in before)


def test_the_assets_override_is_the_one_that_is_hashed(tmp_path: Path, monkeypatch) -> None:
    """render.js serves /assets/ from MEDO_ASSETS_DIR (or KHAAM_…) when set — hash what it serves."""
    project = make_skeleton(tmp_path, TWO)
    external = tmp_path / "shared-assets"
    _write(external, "img/hero.png", "v1")
    for name in ("MEDO_ASSETS_DIR", "KHAAM_ASSETS_DIR"):
        monkeypatch.delenv("MEDO_ASSETS_DIR", raising=False)
        monkeypatch.delenv("KHAAM_ASSETS_DIR", raising=False)
        local = _keys(project)
        monkeypatch.setenv(name, str(external))
        _write(external, "img/hero.png", "v1")
        redirected = _keys(project)
        assert redirected != local, name
        _write(external, "img/hero.png", "v2")
        assert all(_keys(project)[scene] != redirected[scene] for scene in redirected), name


def test_the_motion_mode_is_part_of_the_key(tmp_path: Path, monkeypatch) -> None:
    """render.js defaults --motion-mode from MEDO_MOTION_MODE, and reduced motion draws other frames."""
    project = make_skeleton(tmp_path, TWO)
    monkeypatch.delenv("MEDO_MOTION_MODE", raising=False)
    normal = _keys(project)
    monkeypatch.setenv("MEDO_MOTION_MODE", "normal")
    assert _keys(project) == normal  # the explicit default is the default
    monkeypatch.setenv("MEDO_MOTION_MODE", "reduced")
    assert all(_keys(project)[scene] != normal[scene] for scene in normal)


def test_a_scene_edit_still_costs_one_scene_with_plans_and_assets_present(tmp_path: Path) -> None:
    """Widening the key must not turn every edit into a full re-render."""
    project = make_skeleton(tmp_path, TWO)
    for relative in VISUAL_INPUTS:
        _write(project, relative, "v1")
    before = _keys(project)
    _write(project, "src/scenes/outro.js", "export function draw() { /* v2 */ }\n")
    after = _keys(project)
    assert after["intro"] == before["intro"] and after["outro"] != before["outro"]


def test_a_helper_beside_the_scene_modules_is_shared(tmp_path: Path) -> None:
    """Only `src/scenes/<id>.js` for a real scene id is that scene's own. Anything else — a helper
    in src/scenes/, a module in src/components/, a module named like a scene that data.js does not
    list — may be imported by any scene, so it invalidates all of them."""
    project = make_skeleton(tmp_path, TWO)
    for helper in ("src/scenes/draw-card.js", "src/components/card.js", "src/scenes/retired-scene.js"):
        _write(project, helper, "export const v = 1;\n")
        before = _keys(project)
        _write(project, helper, "export const v = 2;\n")
        after = _keys(project)
        assert after["intro"] != before["intro"] and after["outro"] != before["outro"], helper
    # …while the same edit to a listed scene's module still costs that scene only
    before = _keys(project)
    _write(project, "src/scenes/intro.js", "export function draw() { /* v2 */ }\n")
    after = _keys(project)
    assert after["intro"] != before["intro"] and after["outro"] == before["outro"]


def test_old_cache_entries_cannot_match_the_new_keys(tmp_path: Path) -> None:
    """A segment cached before plans/assets were hashed must miss. Rebuild the v1 key exactly as the
    old code did and prove no scene keeps it — even for a project with nothing but v1's inputs."""
    import hashlib  # noqa: PLC0415
    project = make_skeleton(tmp_path, TWO)
    src = project / "src"
    old = hashlib.sha256()
    old.update(b"engine-k-scene-cache-v1|30|1.0|13")
    for path in [src / "data.js", src / "main.js", src / "render.js", src / "index.html", *sorted((src / "lib").rglob("*.js"))]:
        old.update(f"src/{path.relative_to(src).as_posix()}".encode() + b"\0" + path.read_bytes() + b"\0")
    for scene in TWO:
        legacy = hashlib.sha256(old.hexdigest().encode("ascii"))
        legacy.update(f"scene/{scene['id']}".encode() + b"\0" + (src / "scenes" / f"{scene['id']}.js").read_bytes() + b"\0")
        legacy.update(repr((float(scene["start"]), float(scene["end"]))).encode("utf-8"))
        assert _keys(project)[scene["id"]][:12] != legacy.hexdigest()[:12]
    assert render_scenes.KEY_VERSION != "engine-k-scene-cache-v1"


@pytest.mark.parametrize("tree", ["src", "assets"])
@pytest.mark.parametrize("kind", ["file", "directory"])
def test_a_symlink_that_leaves_the_root_stops_the_run(tmp_path: Path, tree: str, kind: str) -> None:
    """render.js would serve the link's target, so it is a visual input the key cannot see. Leaving
    it out silently is the stale-cache bug again; the tool refuses and names the link."""
    project = make_skeleton(tmp_path, TWO)
    outside = tmp_path / "outside"
    _write(outside, "pic.png", "v1")
    (project / tree).mkdir(exist_ok=True)
    (project / tree / "escape").symlink_to(outside / "pic.png" if kind == "file" else outside,
                                           target_is_directory=kind == "directory")
    with pytest.raises(SystemExit) as error:
        _keys(project)
    assert f"{tree}/escape" in str(error.value) and "symlink" in str(error.value)


def test_a_symlink_inside_the_root_is_followed_and_a_loop_ends(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    _write(project, "assets/real/hero.png", "v1")
    (project / "assets" / "alias").symlink_to(project / "assets" / "real", target_is_directory=True)
    (project / "assets" / "real" / "loop").symlink_to(project / "assets", target_is_directory=True)
    before = _keys(project)
    _write(project, "assets/real/hero.png", "v2")
    assert all(_keys(project)[scene] != before[scene] for scene in before)


def test_the_assets_root_itself_may_be_a_symlink(tmp_path: Path) -> None:
    """Sharing one assets folder between projects is legitimate: the *resolved* root is the boundary."""
    project = make_skeleton(tmp_path, TWO)
    library = tmp_path / "library"
    _write(library, "img/hero.png", "v1")
    (project / "assets").symlink_to(library, target_is_directory=True)
    before = _keys(project)
    _write(library, "img/hero.png", "v2")
    assert all(_keys(project)[scene] != before[scene] for scene in before)


@pytest.mark.parametrize("relative", ["node_modules/.package-lock.json", "package.json", "package-lock.json",
                                      "pnpm-lock.yaml", "yarn.lock"])
def test_package_files_stand_in_for_node_modules(tmp_path: Path, relative: str) -> None:
    """A bumped dependency (three, …) re-renders everything; the tree itself is never walked."""
    project = make_skeleton(tmp_path, TWO)
    _write(project, relative, '{"packages": {"node_modules/three": {"version": "0.187.0"}}}')
    before = _keys(project)
    _write(project, relative, '{"packages": {"node_modules/three": {"version": "0.188.0"}}}')
    assert all(_keys(project)[scene] != before[scene] for scene in before)


def test_lockfiles_are_hashed_as_bytes_not_parsed(tmp_path: Path) -> None:
    """pnpm/yarn locks are not JSON; nothing may try to parse them."""
    project = make_skeleton(tmp_path, TWO)
    _write(project, "pnpm-lock.yaml", "lockfileVersion: '9.0'\npackages:\n  three@0.187.0: {}\n")
    _write(project, "yarn.lock", '# yarn lockfile v1\n"three@0.187.0":\n  version "0.187.0"\n')
    _write(project, "package.json", b"\xff\xfe not even utf-8")
    assert _keys(project) == _keys(project)


def test_no_package_files_is_not_an_error_and_is_stable(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    assert not any((project / name).exists() for name in render_scenes.PACKAGE_FILES)
    assert _keys(project) == _keys(project)


def test_the_contents_of_node_modules_are_not_walked(tmp_path: Path) -> None:
    """The documented limit, pinned: a hand edit inside node_modules is not seen (and a toolkit of
    thousands of files does not slow every run)."""
    project = make_skeleton(tmp_path, TWO)
    _write(project, "node_modules/three/build/three.module.js", "v1")
    before = _keys(project)
    _write(project, "node_modules/three/build/three.module.js", "v2")
    assert _keys(project) == before


def test_hash_audio_opts_one_sound_file_into_the_shared_key(tmp_path: Path) -> None:
    """Audio is left out by extension. A scene that *draws* from a sound file (a waveform) names it
    with --hash-audio, and from then on that file invalidates every scene like any other asset."""
    project = make_skeleton(tmp_path, TWO)
    _write(project, "assets/vo/vo.wav", "v1")
    plain = _keys(project)
    opted = _keys(project, extra=(Path("assets/vo/vo.wav"),))
    assert all(opted[scene] != plain[scene] for scene in plain)  # adding the path invalidates all
    _write(project, "assets/vo/vo.wav", "v2")
    assert _keys(project) == plain  # still inert without the option
    assert all(_keys(project, extra=(Path("assets/vo/vo.wav"),))[scene] != opted[scene] for scene in opted)
    with pytest.raises(SystemExit) as error:
        _keys(project, extra=(Path("assets/vo/missing.wav"),))
    assert "missing.wav" in str(error.value)


def test_motion_mode_is_resolved_cli_then_env_then_normal(monkeypatch) -> None:
    monkeypatch.delenv("MEDO_MOTION_MODE", raising=False)
    assert render_scenes.resolve_motion_mode(None) == "normal"
    monkeypatch.setenv("MEDO_MOTION_MODE", "")
    assert render_scenes.resolve_motion_mode(None) == "normal"  # render.js: `env || 'normal'`
    monkeypatch.setenv("MEDO_MOTION_MODE", "reduced")
    assert render_scenes.resolve_motion_mode(None) == "reduced"
    assert render_scenes.resolve_motion_mode("normal") == "normal"  # the CLI wins over the environment
    monkeypatch.setenv("MEDO_MOTION_MODE", "wild")
    with pytest.raises(SystemExit):
        render_scenes.resolve_motion_mode(None)


def test_the_resolved_motion_mode_is_what_render_js_is_told(tmp_path: Path, monkeypatch) -> None:
    """The key and the render must agree: the mode is passed explicitly, never left to the child's env."""
    project = make_skeleton(tmp_path, TWO)
    seen: list = []

    def fake_run(cmd, **kwargs):
        seen.append(cmd)
        browser = json.dumps({"executablePath": "/opt/chrome", "libraryPath": None, "args": []})
        return subprocess.CompletedProcess(cmd, 0, stdout=browser if "--json" in cmd else "", stderr="")

    monkeypatch.setattr(render_scenes.subprocess, "run", fake_run)
    render_scenes.render_segment(project, TWO[0], project / "cache" / "scenes" / "intro-abc.mp4", fps=30, crf=13,
                                 log=project / "log.txt", motion_mode="reduced")
    render_cmd = seen[-1]
    assert render_cmd[render_cmd.index("--motion-mode") + 1] == "reduced"


def test_the_explicit_motion_mode_changes_the_key(tmp_path: Path, monkeypatch) -> None:
    project = make_skeleton(tmp_path, TWO)
    monkeypatch.setenv("MEDO_MOTION_MODE", "reduced")
    assert _keys(project, motion_mode="normal") != _keys(project)
    assert _keys(project, motion_mode="reduced") == _keys(project)


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
    shared = _shared(project)
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


def _silence(path: Path, seconds: float, rate: int = 48000) -> Path:
    import wave  # noqa: PLC0415
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * round(seconds * rate))
    return path


def _audio_seconds(path: Path) -> float | None:
    """Decoded audio duration of a container, or None when it has no audio stream."""
    import av  # noqa: PLC0415
    with av.open(str(path)) as container:
        if not container.streams.audio:
            return None
        stream = container.streams.audio[0]
        samples = sum(frame.samples for frame in container.decode(stream))
        return samples / stream.rate


@pytest.mark.slow
def test_real_run_rerenders_on_shared_inputs_and_only_then(tmp_path: Path) -> None:
    """The cache bug, end to end: after a plan or an asset changes, the old MP4s must not be reused —
    and a file no frame can read (notes, voice-over, the muxed mix itself) must not cost a render."""
    if not (TOOLKIT / "playwright-core").is_dir() or not HAS_NODE:
        pytest.skip("toolkit node_modules missing — run: npm ci --prefix tools/toolkit")
    import time_to_first_video as ttfv  # noqa: PLC0415 - test helper shared with the TTFV suite

    project = tmp_path / "k"
    subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), "k", "--engine", "k",
                    "--out", str(project)], check=True, capture_output=True)
    (project / "node_modules").symlink_to(TOOLKIT)
    (project / "src" / "data.js").write_text(
        (project / "src" / "data.js").read_text(encoding="utf-8").split("export const scenes = [")[0]
        + "export const scenes = [\n  { id: 'example', start: 0, end: 0.5 },\n"
          "  { id: 'second', start: 0.5, end: 1 },\n];\n"
        + "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    shutil.copy(project / "src" / "scenes" / "example.js", project / "src" / "scenes" / "second.js")
    (project / "plan" / "beats.json").write_text(json.dumps({
        "duration": 1.0, "bpm": 100,
        "scenes": [{"id": "example", "start": 0.0, "end": 0.5}, {"id": "second", "start": 0.5, "end": 1.0}],
    }), encoding="utf-8")
    direction = dict(ttfv.DIRECTION)
    direction["scenes"] = [dict(ttfv.DIRECTION["scenes"][0], scene=index) for index in (1, 2)]
    (project / "plan" / "text-direction.json").write_text(json.dumps(direction, ensure_ascii=False),
                                                          encoding="utf-8")

    def render(*extra: str) -> tuple[int, int, set[str]]:
        assert render_scenes.main([str(project), "--force", *extra]) == 0
        manifest = json.loads((project / "cache" / "scenes" / "manifest.json").read_text(encoding="utf-8"))
        return manifest["hits"], manifest["misses"], {entry["segment"] for entry in manifest["scenes"]}

    def touch(relative: str) -> None:
        target = project / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((target.read_bytes() if target.exists() else b"") + b"\n")

    hits, misses, first = render()
    assert (hits, misses) == (0, 2)
    assert render()[:2] == (2, 0)

    segments = first
    for relative in ("plan/stage.json", "plan/copy.json", "assets/fonts/fonts.json", "assets/images/new.png",
                     "src/lib/kit.js", "package.json"):
        hits, misses, now = render()
        assert (hits, misses) == (2, 0), f"cache was not warm before touching {relative}"
        touch(relative)
        hits, misses, now = render()
        assert (hits, misses) == (0, 2), f"{relative} changed but the old segments were reused"
        assert not (now & segments), f"{relative}: a segment kept its old name"
        segments = now

    for relative in ("plan/script.md", "plan/visual-direction.json", "BRIEF.md", "assets/vo/take.wav"):
        touch(relative)
        hits, misses, now = render()
        assert (hits, misses) == (2, 0), f"{relative} cannot reach a frame but cost a re-render"
        assert now == segments

    # The mix is muxed once over the finished reel — it is in no segment, so swapping it re-renders
    # nothing, and the new sound is what the output carries.
    master = project / "out" / "master.mp4"
    assert _audio_seconds(master) is None
    mix = _silence(project / "out" / "final_audio.wav", 1.0)
    hits, misses, now = render()
    assert (hits, misses) == (2, 0) and now == segments
    assert _audio_seconds(master) == pytest.approx(1.0, abs=0.05)
    _silence(mix, 1.0, rate=44100)
    hits, misses, now = render()
    assert (hits, misses) == (2, 0) and now == segments

    # --hash-audio: naming a sound file a scene draws from invalidates everything, once
    assert render("--hash-audio", "assets/vo/take.wav")[:2] == (0, 2)
    assert render("--hash-audio", "assets/vo/take.wav")[:2] == (2, 0)
    touch("assets/vo/take.wav")
    assert render("--hash-audio", "assets/vo/take.wav")[:2] == (0, 2)

    # reduced motion draws different frames: it cannot share segments with a normal render
    hits, misses, reduced = render("--motion-mode", "reduced")
    assert misses == 2 and not (reduced & segments)


# --- audio mux: a length mismatch is refused, never cut silently ------------------------------

def _picture(path: Path, frames: int, fps: int = 30) -> Path:
    """A real H.264 clip of exactly `frames` frames (no Chromium: the mux does not care who drew it)."""
    ffmpeg = render_scenes.media_bin.ffmpeg()
    if not ffmpeg or not render_scenes.media_bin.ffprobe():
        pytest.skip("ffmpeg/ffprobe missing — run: bash tools/setup.sh")
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"color=c=red:s=1080x1920:r={fps}",
                    "-frames:v", str(frames), "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                    str(path)], check=True)
    return path


def _video_frames(path: Path) -> int:
    """Frames actually decodable — not the container's claim."""
    import av  # noqa: PLC0415
    with av.open(str(path)) as container:
        return sum(1 for _ in container.decode(container.streams.video[0]))


HALF_FRAME = 0.5 / 30


@pytest.mark.slow
@pytest.mark.parametrize("audio_seconds", [0.5, 1.0 - HALF_FRAME - 0.004, 1.0 + HALF_FRAME + 0.004, 1.5, 3.0])
def test_mux_refuses_audio_that_does_not_fit_the_picture(tmp_path: Path, audio_seconds: float) -> None:
    """The reported bug: 1 s of picture + 0.5 s of sound produced a 13-frame file and "success"."""
    picture = _picture(tmp_path / "picture.mp4", 30)
    audio = _silence(tmp_path / "mix.wav", audio_seconds)
    target = tmp_path / "out" / "master.mp4"
    target.parent.mkdir()
    target.write_bytes(b"previous good master")
    with pytest.raises(SystemExit) as error:
        render_scenes.mux_audio(picture, audio, target, tmp_path / "log.txt")
    message = str(error.value)
    assert "audio" in message and "picture" in message and "--audio-fit" in message
    assert f"{audio_seconds:.3f}" in message and "1.000" in message  # both lengths, so the fix is obvious
    assert target.read_bytes() == b"previous good master", "a refused mux must not touch the existing output"
    assert not list(target.parent.glob("*.tmp.*")), "a refused mux left a partial file behind"


@pytest.mark.slow
@pytest.mark.parametrize("audio_seconds", [1.0, 1.0 - HALF_FRAME + 0.004, 1.0 + HALF_FRAME - 0.004])
def test_mux_keeps_every_frame_when_the_lengths_agree(tmp_path: Path, audio_seconds: float) -> None:
    picture = _picture(tmp_path / "picture.mp4", 30)
    audio = _silence(tmp_path / "mix.wav", audio_seconds)
    target = tmp_path / "master.mp4"
    assert render_scenes.mux_audio(picture, audio, target, tmp_path / "log.txt") is True
    assert _video_frames(target) == 30
    assert _audio_seconds(target) == pytest.approx(audio_seconds, abs=0.05)
    render_scenes.verify_output(target, frames=30, fps=30, audio_seconds=audio_seconds)


@pytest.mark.slow
@pytest.mark.parametrize("policy, audio_seconds, accepted", [
    ("pad", 0.5, True), ("pad", 1.5, False), ("trim", 1.5, True), ("trim", 0.5, False),
    ("pad", 1.0, True), ("trim", 1.0, True),
])
def test_audio_fit_is_an_explicit_one_directional_policy(tmp_path: Path, policy: str, audio_seconds: float,
                                                         accepted: bool) -> None:
    """--audio-fit pad only lengthens the sound, trim only shortens it; the picture is never cut."""
    picture = _picture(tmp_path / "picture.mp4", 30)
    audio = _silence(tmp_path / "mix.wav", audio_seconds)
    target = tmp_path / "master.mp4"
    if not accepted:
        with pytest.raises(SystemExit):
            render_scenes.mux_audio(picture, audio, target, tmp_path / "log.txt", audio_fit=policy)
        assert not target.exists()
        return
    assert render_scenes.mux_audio(picture, audio, target, tmp_path / "log.txt", audio_fit=policy) is True
    assert _video_frames(target) == 30
    assert _audio_seconds(target) == pytest.approx(1.0, abs=0.05)
    render_scenes.verify_output(target, frames=30, fps=30, audio_seconds=1.0)


@pytest.mark.slow
@pytest.mark.parametrize("fault", ["frames", "no-audio", "short-audio", "unreadable"])
def test_verify_output_catches_a_bad_file(tmp_path: Path, fault: str) -> None:
    """The last gate before the manifest: measured on the written file, not computed."""
    good = _picture(tmp_path / "picture.mp4", 30)
    target = tmp_path / "master.mp4"
    if fault == "frames":
        shutil.copy(_picture(tmp_path / "short.mp4", 13), target)
        expect = {"frames": 30, "fps": 30, "audio_seconds": None}
    elif fault == "no-audio":
        shutil.copy(good, target)
        expect = {"frames": 30, "fps": 30, "audio_seconds": 1.0}
    elif fault == "short-audio":
        render_scenes.mux_audio(good, _silence(tmp_path / "mix.wav", 1.0), target, tmp_path / "log.txt")
        expect = {"frames": 30, "fps": 30, "audio_seconds": 2.0}
    else:
        target.write_bytes(b"not a video")
        expect = {"frames": 30, "fps": 30, "audio_seconds": None}
    with pytest.raises(SystemExit) as error:
        render_scenes.verify_output(target, **expect)
    assert "master.mp4" in str(error.value)


@pytest.mark.slow
@pytest.mark.skipif(not HAS_NODE, reason="node is required to read data.js")
@pytest.mark.parametrize("audio_seconds, extra, ok", [
    (2.5, [], True), (1.0, [], False), (4.0, [], False),
    (1.0, ["--audio-fit", "pad"], True), (4.0, ["--audio-fit", "trim"], True),
])
def test_cli_reports_success_only_for_a_verified_master(tmp_path: Path, monkeypatch, capsys, audio_seconds: float,
                                                        extra: list[str], ok: bool) -> None:
    """Through main(): exit code, stderr, the output file and the manifest all tell the same story."""
    project = make_skeleton(tmp_path, TWO)  # 1.0 s + 1.5 s = 75 frames

    def fake_segment(project, scene, target, *, fps, crf, log, motion_mode="normal") -> bool:
        _picture(target, render_scenes.expected_frames(scene, fps), fps)
        return True

    monkeypatch.setattr(render_scenes, "render_segment", fake_segment)
    _silence(project / "out" / "final_audio.wav", audio_seconds)
    code = render_scenes.main([str(project), *extra])
    master = project / "out" / "master.mp4"
    manifest = project / "cache" / "scenes" / "manifest.json"
    if not ok:
        assert code == 2
        assert "--audio-fit" in capsys.readouterr().err
        assert not master.exists() and not manifest.exists()
        return
    assert code == 0
    assert _video_frames(master) == 75
    assert _audio_seconds(master) == pytest.approx(2.5, abs=0.05)
    assert not list(master.parent.glob("*.tmp.*"))
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    assert recorded["verified"]["frames"] == 75 and recorded["verified"]["audio_seconds"] == pytest.approx(2.5, abs=0.05)


@pytest.mark.slow
def test_a_short_concat_never_becomes_the_output(tmp_path: Path) -> None:
    """The silent path has no mux to catch it: the joined picture is counted before it is published."""
    segments = [_picture(tmp_path / "a.mp4", 15), _picture(tmp_path / "b.mp4", 15)]
    target = tmp_path / "out" / "master.mp4"
    target.parent.mkdir()
    target.write_bytes(b"previous good master")
    with pytest.raises(SystemExit) as error:
        render_scenes.concat(segments, target, tmp_path / "log.txt", frames=45, fps=30)
    assert "30 frames, expected 45" in str(error.value)
    assert target.read_bytes() == b"previous good master" and not list(target.parent.glob("*.tmp.*"))
    assert render_scenes.concat(segments, target, tmp_path / "log.txt", frames=30, fps=30) is True
    assert _video_frames(target) == 30


# --- hardening: scene ids, paths, and no shell ------------------------------------------------
# Engine K runs the project's own JavaScript, so none of this is a sandbox. It closes the ways a
# *value* (a scene id, a path with a quote in it) could become a command or leave the cache.

BAD_IDS = ["../escape", "..", "a/b", "a\\b", "/abs", "a;b", "x;touch pwned", "$(touch pwned)", "`touch pwned`",
           "a|b", "a&b", "a>b", "a b", " intro", "intro ", "intro\n", "a\nb", "a\tb", "a\x00b", "", ".hidden",
           "a.b", "-rf", "--name", "_private", "a" * 65, "مشهد", "ｉｎｔｒｏ", "intro\u200b", "é", "a'b", 'a"b', "a*", "~"]
BAD_ID_VALUES = [*BAD_IDS, 5, 1.5, True, None, ["intro"], {"id": "intro"}]
GOOD_IDS = ["a", "A", "0", "intro", "arabic-example", "s_1", "9lives", "Scene-02_final", "a" * 64]


def _project_with_ids(tmp_path: Path, ids: list) -> Path:
    project = make_skeleton(tmp_path, [])
    entries = ", ".join(f"{{ id: {json.dumps(value)}, start: {index}, end: {index + 1} }}"
                        for index, value in enumerate(ids))
    (project / "src" / "data.js").write_text(f"export const scenes = [{entries}];\n", encoding="utf-8")
    for value in ids:
        if isinstance(value, str) and value and "/" not in value and "\x00" not in value:
            try:
                (project / "src" / "scenes" / f"{value}.js").write_text("export function draw() {}\n", encoding="utf-8")
            except OSError:
                pass
    return project


def _snapshot(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*")}


@pytest.mark.parametrize("scene_id", BAD_ID_VALUES, ids=repr)
def test_validate_scene_id_rejects_everything_outside_the_allowlist(scene_id) -> None:
    with pytest.raises(SystemExit) as error:
        render_scenes.validate_scene_id(scene_id)
    assert "scene id" in str(error.value) and "letters, digits" in str(error.value)


@pytest.mark.parametrize("scene_id", GOOD_IDS)
def test_validate_scene_id_accepts_the_ids_projects_use(scene_id: str) -> None:
    assert render_scenes.validate_scene_id(scene_id) == scene_id


def test_every_scene_id_in_the_templates_and_fixtures_is_still_valid() -> None:
    """The allowlist must not break a shipped project: check every `data.js` in the repository."""
    import re  # noqa: PLC0415
    found: dict[str, str] = {}
    for data in [*ROOT.glob("medo-motion/**/data.js"), *ROOT.glob("tests/fixtures/**/data.js"),
                 *ROOT.glob("tools/**/data.js")]:
        if "node_modules" in data.parts:
            continue
        for scene_id in re.findall(r"\bid:\s*['\"]([^'\"]*)['\"]\s*,\s*start\b", data.read_text(encoding="utf-8")):
            found[scene_id] = str(data.relative_to(ROOT))
    assert "arabic-example" in found, "the scan found no template scene ids — the pattern is stale"
    for scene_id in found:
        render_scenes.validate_scene_id(scene_id)


@pytest.mark.skipif(not HAS_NODE, reason="node is required to read data.js")
@pytest.mark.parametrize("scene_id", BAD_ID_VALUES, ids=repr)
def test_a_bad_scene_id_stops_before_any_file_is_touched_or_any_command_runs(tmp_path: Path, monkeypatch, capsys,
                                                                             scene_id) -> None:
    """Rejected in load_scenes: the only process that ran is `node -e` reading data.js, as an argv
    list; nothing is hashed, rendered, written or deleted, in the project or beside it."""
    project = _project_with_ids(tmp_path, ["intro", scene_id])
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")
    before = _snapshot(tmp_path)
    real_run = subprocess.run
    calls: list = []

    def spy(cmd, *args, **kwargs):
        calls.append((cmd, kwargs))
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(render_scenes.subprocess, "run", spy)
    monkeypatch.setattr(render_scenes, "shared_key", lambda *a, **k: pytest.fail("hashing started"))
    monkeypatch.setattr(render_scenes, "render_segment", lambda *a, **k: pytest.fail("a render started"))
    assert render_scenes.main([str(project)]) == 2
    assert "scene id" in capsys.readouterr().err
    assert len(calls) == 1
    cmd, kwargs = calls[0]
    assert isinstance(cmd, list) and Path(cmd[0]).name.startswith("node") and not kwargs.get("shell")
    assert _snapshot(tmp_path) - before <= {"reel/cache", "reel/cache/scenes.log"}
    assert outside.read_text(encoding="utf-8") == "keep"


@pytest.mark.skipif(not HAS_NODE or shutil.which("bash") is None, reason="needs node and bash")
@pytest.mark.parametrize("scene_id", ["x;touch pwned", "x$(touch pwned)", "x`touch pwned`", "x&&touch pwned;"])
def test_a_scene_id_is_never_executed(tmp_path: Path, scene_id: str) -> None:
    """The reported injection, run for real (no mocks): with the old `bash -c` string this created
    `pwned…` in the project."""
    project = _project_with_ids(tmp_path, [scene_id])
    code = render_scenes.main([str(project)])
    created = [path.name for path in tmp_path.rglob("*pwned*") if path.suffix != ".js"]
    assert not created, f"the scene id ran as a shell command and created {created}"
    assert code == 2


def test_scene_key_and_run_validate_too(tmp_path: Path) -> None:
    """Defence in depth: the id is checked wherever it becomes a path, not only where it is read."""
    project = make_skeleton(tmp_path, TWO)
    (project / "secret.js").write_text("// outside src/scenes\n", encoding="utf-8")
    with pytest.raises(SystemExit) as error:
        render_scenes.scene_key("0" * 64, project, {"id": "../../secret", "start": 0, "end": 1})
    assert "scene id" in str(error.value)


def test_a_scene_module_that_links_out_of_the_project_is_refused(tmp_path: Path) -> None:
    project = make_skeleton(tmp_path, TWO)
    outside = tmp_path / "outside.js"
    outside.write_text("export function draw() {}\n", encoding="utf-8")
    (project / "src" / "scenes" / "intro.js").unlink()
    (project / "src" / "scenes" / "intro.js").symlink_to(outside)
    with pytest.raises(SystemExit) as error:
        render_scenes.scene_key("0" * 64, project, TWO[0])
    assert "intro.js" in str(error.value)


@pytest.mark.skipif(not HAS_NODE, reason="node is required to read data.js")
@pytest.mark.parametrize("link", ["cache", "cache/scenes", "segment"])
def test_nothing_outside_the_cache_is_deleted_or_written(tmp_path: Path, monkeypatch, capsys, link: str) -> None:
    """A stale segment is unlinked before it is re-rendered. If the cache (or the segment) is a
    symlink, that unlink/write would land somewhere else — the run refuses instead."""
    project = make_skeleton(tmp_path, TWO)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    keys = _keys(project)
    name = f"intro-{keys['intro'][:12]}.mp4"
    victim = elsewhere / name
    victim.write_bytes(b"someone else's file")  # not a decodable video: the cache check would 'miss' and unlink it
    if link == "cache":
        (elsewhere / "scenes").mkdir()
        victim = elsewhere / "scenes" / name
        victim.write_bytes(b"someone else's file")
        (project / "cache").symlink_to(elsewhere, target_is_directory=True)
    elif link == "cache/scenes":
        (project / "cache").mkdir()
        (project / "cache" / "scenes").symlink_to(elsewhere, target_is_directory=True)
    else:
        (project / "cache" / "scenes").mkdir(parents=True)
        (project / "cache" / "scenes" / name).symlink_to(victim)
    monkeypatch.setattr(render_scenes, "render_segment", lambda *a, **k: pytest.fail("rendered through a symlink"))
    before = _snapshot(elsewhere)
    assert render_scenes.main([str(project)]) == 2
    assert "symlink" in capsys.readouterr().err
    assert victim.read_bytes() == b"someone else's file"
    assert _snapshot(elsewhere) == before


def test_render_segment_runs_argv_lists_and_reads_the_browser_env_as_json(tmp_path: Path, monkeypatch) -> None:
    """No `bash -c`, no `eval` of another program's output: two argv lists, and a parsed JSON object."""
    project = make_skeleton(tmp_path, TWO)
    calls: list = []

    def fake_run(cmd, *args, **kwargs):
        calls.append((cmd, kwargs))
        if "--json" in cmd:
            payload = {"executablePath": "/opt/chrome; touch pwned", "libraryPath": "/opt/lib $(touch pwned)",
                       "args": ["--no-sandbox", "--x='a b'"]}
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(render_scenes.subprocess, "run", fake_run)
    monkeypatch.setenv("LD_LIBRARY_PATH", "/usr/lib/existing")
    target = project / "cache" / "scenes" / "intro-0123456789ab.mp4"
    assert render_scenes.render_segment(project, TWO[0], target, fps=30, crf=13, log=project / "log.txt") is True
    assert len(calls) == 2
    for cmd, kwargs in calls:
        assert isinstance(cmd, list) and all(isinstance(part, str) for part in cmd)
        assert not kwargs.get("shell")
        assert Path(cmd[0]).name.startswith("node"), cmd
        assert not any(part in {"bash", "sh", "-c"} or "eval" in part for part in cmd)
    render_cmd, render_kwargs = calls[1]
    assert render_cmd[1] == "src/render.js"
    assert render_cmd[render_cmd.index("--name") + 1] == "intro-0123456789ab"
    assert render_cmd[render_cmd.index("--out") + 1] == "cache/scenes"
    env = render_kwargs["env"]
    assert env["MEDO_CHROMIUM"] == "/opt/chrome; touch pwned"  # a value, verbatim — never evaluated
    assert env["LD_LIBRARY_PATH"] == "/opt/lib $(touch pwned):/usr/lib/existing"
    assert env["MEDO_CHROMIUM_ARGS"] == "--no-sandbox --x='a b'"
    assert not list(tmp_path.rglob("pwned*"))


@pytest.mark.parametrize("stdout, code", [("not json", 0), ("{}", 0), ('{"executablePath": 5}', 0), ("", 2)])
def test_a_broken_browser_probe_fails_the_segment_without_rendering(tmp_path: Path, monkeypatch, stdout, code) -> None:
    project = make_skeleton(tmp_path, TWO)
    calls: list = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, code, stdout=stdout, stderr="boom")

    monkeypatch.setattr(render_scenes.subprocess, "run", fake_run)
    target = project / "cache" / "scenes" / "intro-0123456789ab.mp4"
    assert render_scenes.render_segment(project, TWO[0], target, fps=30, crf=13, log=project / "log.txt") is False
    assert len(calls) == 1, "render.js must not start without a browser"
    assert "chromium" in (project / "log.txt").read_text(encoding="utf-8").lower()


@pytest.mark.slow
def test_concat_survives_a_quote_in_the_project_path(tmp_path: Path) -> None:
    """The concat list is a small language of its own: a `'` in a path must stay part of the path."""
    weird = tmp_path / "it's a 'reel'"
    weird.mkdir()
    segments = [_picture(weird / "a.mp4", 15), _picture(weird / "b.mp4", 15)]
    target = weird / "master.mp4"
    assert render_scenes.concat(segments, target, tmp_path / "log.txt", frames=30, fps=30) is True
    assert _video_frames(target) == 30


def test_concat_refuses_a_line_break_in_a_segment_path(tmp_path: Path) -> None:
    """A newline cannot be quoted in an ffconcat list: it would start a new directive."""
    if not render_scenes.media_bin.ffmpeg():
        pytest.skip("ffmpeg missing")
    weird = tmp_path / "reel\nfile 'injected.mp4'"
    try:
        weird.mkdir()
    except OSError:
        pytest.skip("this filesystem does not allow a line break in a name")
    (weird / "a.mp4").write_bytes(b"x")
    with pytest.raises(SystemExit) as error:
        render_scenes.concat([weird / "a.mp4"], tmp_path / "master.mp4", tmp_path / "log.txt")
    assert "line break" in str(error.value) and not (tmp_path / "scenes.txt").exists()
