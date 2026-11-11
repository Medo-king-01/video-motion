"""Engine-K scene cache hardening: scene ids, paths that stay inside the cache, and no shell.

Hardening, not isolation — engine K executes the project's own JavaScript. Split from
`test_render_scenes.py` (review budget); the builders are shared with it.
"""
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
from test_render_scenes import HAS_NODE, TWO, _keys, _picture, _video_frames, make_skeleton  # noqa: E402

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
