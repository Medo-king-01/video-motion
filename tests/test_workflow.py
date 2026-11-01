"""Project scaffold, tools and one real engine-P frame."""
from __future__ import annotations

import json
import subprocess
import sys

from conftest import ENGINE_P, ROOT, SKILL


def test_brief_asks_for_four_inputs_only():
    src = (ROOT / "tools" / "new_project.py").read_text(encoding="utf-8")
    for needle in ("Script", "Scene direction", "VO", "Poses"):
        assert needle in src, needle
    assert "no logo" in src.lower()


def test_agents_contract_has_hard_rules():
    contract = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "No logo. No series name." in contract
    for needle in ("four inputs", "Egyptian Arabic", "Never print", "2.5 Mbps"):
        assert needle.lower() in contract.lower(), needle


def test_engine_templates_are_present():
    for f in ("scenes.py", "lib.py", "art.py", "mix.py", "chunk.py", "run_all.py",
              "sfx.py", "cutout.py", "arabic_shape.py"):
        assert (ENGINE_P / f).is_file(), f
    for f in ("render.js", "main.js", "data.js", "lib/kit.js", "lib/arabic.js", "lib/brand.js"):
        assert (SKILL / "templates" / "render" / f).is_file(), f


def test_new_project_scaffolds(tmp_path):
    slug = f"_pytest-{tmp_path.name}"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "p"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    proj = ROOT / "projects" / slug
    try:
        for sub in ("plan", "assets/vo", "assets/poses", "assets/fonts/Cairo", "out"):
            assert (proj / sub).is_dir(), sub
        brief = (proj / "BRIEF.md").read_text(encoding="utf-8")
        assert "Scene direction" in brief and "Poses" in brief
        assert "logo" not in brief.lower()
        assert (proj / "scenes.py").is_file()          # engine P copied in
        assert list((proj / "assets" / "fonts" / "Cairo").glob("*.ttf"))
        beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
        assert "scenes" in beats
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_preflight_reports_arabic_backend():
    r = subprocess.run([sys.executable, str(SKILL / "scripts" / "preflight.py")],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data["medo"]["arabic_shaping"] in ("raqm", "harfbuzz-fallback")
    assert data["medo"]["brand_files"] is True
    assert "error" not in data["medo"]


def test_one_engine_p_frame_has_brand_size(project, monkeypatch):
    """Real frame from the real engine: 1080x1920, uint8, with Arabic ink on it."""
    monkeypatch.chdir(project)
    import importlib

    import scenes
    importlib.reload(scenes)
    frame = scenes.render_frame(6.2)
    assert frame.shape == (1920, 1080, 3)
    assert frame.dtype.name == "uint8"
    assert frame.std() > 5, "frame looks blank"
