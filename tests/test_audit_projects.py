"""`tools/audit_projects.py`: a read-only report over real projects, before the hardening stops them."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import audit_projects  # noqa: E402
import render_scenes  # noqa: E402

DATA = "export const W = 1080, H = 1920, FPS = 30;\nexport const scenes = [\n{rows}\n];\nexport const DURATION = scenes.at(-1).end;\n"


def _project(root: Path, name: str, ids: list[str] | None, *, quote: str = "'") -> Path:
    project = root / name
    (project / "out").mkdir(parents=True)
    (project / "plan").mkdir()
    if ids is not None:
        (project / "src").mkdir()
        rows = "\n".join(f"  {{ id: {quote}{item}{quote}, start: {n}, end: {n + 1} }},  // note: id: 'not-an-id'"
                         for n, item in enumerate(ids))
        (project / "src" / "data.js").write_text(DATA.replace("{rows}", rows), encoding="utf-8")
    return project


def _snapshot(root: Path) -> dict[str, tuple]:
    return {str(p.relative_to(root)): (p.is_symlink(), p.is_dir(), p.stat().st_mtime_ns if not p.is_symlink() else 0,
                                       hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "")
            for p in sorted(root.rglob("*"))}


@pytest.mark.parametrize("bad", ["has space", "dot.ted", "_lead", "-lead", "مشهد", "a/b", "x;touch pwned", "a" * 65])
@pytest.mark.parametrize("quote", ["'", '"', "`"])
def test_an_id_outside_the_allowlist_is_reported(tmp_path: Path, bad: str, quote: str) -> None:
    project = _project(tmp_path, "reel", ["intro", bad, "outro"], quote=quote)
    report = audit_projects.audit(project)
    assert report["scene_ids"] == {"read_with": "static", "count": 3, "rejected": [bad]}
    assert len(report["findings"]) == 1 and repr(bad) in report["findings"][0]


def test_the_audit_and_the_renderer_use_the_same_allowlist(tmp_path: Path) -> None:
    assert audit_projects.SCENE_ID is render_scenes.SCENE_ID
    good = ["a", "intro", "arabic-example", "s_1", "9lives", "a" * 64]
    assert audit_projects.audit(_project(tmp_path, "reel", good))["findings"] == []


def test_ids_in_comments_and_outside_the_scenes_array_are_not_counted(tmp_path: Path) -> None:
    project = _project(tmp_path, "reel", ["intro"])
    data = project / "src" / "data.js"
    data.write_text(data.read_text(encoding="utf-8") + "/* { id: 'bad one' } */\nexport const FONT = { id: 'also bad' };\n",
                    encoding="utf-8")
    assert audit_projects.audit(project)["scene_ids"] == {"read_with": "static", "count": 1, "rejected": []}


def test_ids_built_at_run_time_are_called_out_not_passed(tmp_path: Path) -> None:
    project = _project(tmp_path, "reel", [])
    (project / "src" / "data.js").write_text("export const scenes = names.map((id, i) => ({ id, start: i, end: i + 1 }));\n",
                                             encoding="utf-8")
    report = audit_projects.audit(project)
    assert report["scene_ids"]["count"] == 0 and any("--node" in note for note in report["notes"])


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_node_reads_what_the_text_cannot(tmp_path: Path) -> None:
    project = _project(tmp_path, "reel", [])
    (project / "src" / "data.js").write_text(
        "const names = ['intro', 'bad id'];\nexport const scenes = names.map((id, i) => ({ id, start: i, end: i + 1 }));\n",
        encoding="utf-8")
    report = audit_projects.audit(project, use_node=True)
    assert report["scene_ids"] == {"read_with": "node", "count": 2, "rejected": ["bad id"]}


@pytest.mark.parametrize("wav, record, sheet, finding", [
    (True, False, True, True),    # the case the pipeline now stops on
    (True, True, True, False),
    (True, False, False, False),  # no cue sheet: kept unchecked — a note, not a finding
    (False, False, True, False),
])
def test_a_mix_without_a_record_is_reported(tmp_path: Path, wav: bool, record: bool, sheet: bool, finding: bool) -> None:
    project = _project(tmp_path, "reel", ["intro"])
    if wav:
        (project / "out" / "final_audio.wav").write_bytes(b"RIFF")
    if record:
        (project / "out" / "final_audio.mix.json").write_text("{}", encoding="utf-8")
    if sheet:
        (project / "plan" / "cues.json").write_text("{}", encoding="utf-8")
    report = audit_projects.audit(project)
    assert any("final_audio.mix.json" in item for item in report["findings"]) is finding
    if wav and not record and not sheet:
        assert any("without checking" in note for note in report["notes"])


def test_the_record_name_matches_the_pipeline() -> None:
    import pipeline

    assert pipeline._mix_record(Path("out/final_audio.wav")).name == "final_audio.mix.json"


def test_a_symlinked_cache_is_reported(tmp_path: Path) -> None:
    project = _project(tmp_path, "reel", ["intro"])
    (tmp_path / "elsewhere").mkdir()
    (project / "cache").symlink_to(tmp_path / "elsewhere", target_is_directory=True)
    assert any("cache is a symlink" in item for item in audit_projects.audit(project)["findings"])


def test_a_project_without_data_js_is_not_flagged_for_ids(tmp_path: Path) -> None:
    report = audit_projects.audit(_project(tmp_path, "p-reel", None))
    assert report["scene_ids"] is None and report["findings"] == []


@pytest.mark.parametrize("flags", [[], ["--json"], ["--node"]])
def test_the_run_changes_nothing_and_reports_every_project(tmp_path: Path, capsys: pytest.CaptureFixture, flags: list) -> None:
    root = tmp_path / "projects"
    _project(root, "clean", ["intro", "outro"])
    dirty = _project(root, "dirty", ["bad id"])
    (dirty / "out" / "final_audio.wav").write_bytes(b"RIFF")
    (dirty / "plan" / "cues.json").write_text("{}", encoding="utf-8")
    (root / "README.md").write_text("not a project\n", encoding="utf-8")
    before = _snapshot(tmp_path)
    assert audit_projects.main(["--root", str(root), *flags]) == 0
    assert _snapshot(tmp_path) == before, "the audit wrote, removed or touched something"
    out = capsys.readouterr().out
    if "--json" in flags:
        data = json.loads(out)
        assert [Path(p["project"]).name for p in data["projects"]] == ["clean", "dirty"] and data["with_findings"] == 1
    else:
        assert "2 project(s) checked, 1 with findings. Nothing was changed." in out
    assert audit_projects.main(["--root", str(root), "--fail-on-findings"]) == 1
    assert audit_projects.main([str(tmp_path / "missing")]) == 2
