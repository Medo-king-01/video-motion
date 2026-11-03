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
              "sfx.py", "cutout.py", "arabic_shape.py", "motion_plan.py", "motion_state.py", "motion_geometry.py", "text_measure.py", "geometry_draw.py", "svg_art.py", "svg_morph.py", "render_policy.py", "resource_scope.py", "frame_batch.py"):
        assert (ENGINE_P / f).is_file(), f
    for f in ("render.js", "main.js", "data.js", "lib/kit.js", "lib/arabic.js", "lib/brand.js", "lib/motion-state.js", "lib/motion-geometry.js", "lib/text-measure.js", "lib/geometry-canvas.js", "lib/svg-art.js", "lib/svg-morph.js", "lib/svg-canvas.js", "lib/render-policy.js", "lib/resource-scope.js", "lib/frame-batch.js"):
        assert (SKILL / "templates" / "render" / f).is_file(), f
    for f in ("package.json", "src/index.ts", "src/Root.tsx", "src/RemotionRoot.tsx",
              "src/brand.ts", "src/lib/motion.js", "src/lib/motion-state.js", "src/lib/motion-geometry.js", "src/lib/text-measure.js", "src/lib/GeometryBindings.tsx", "src/lib/SvgArt.tsx", "src/lib/svg-morph.js", "src/lib/Presenter.tsx", "scripts/render.mjs"):
        assert (SKILL / "templates" / "remotion" / f).is_file(), f


def test_new_project_scaffolds(tmp_path):
    slug = f"_pytest-{tmp_path.name}"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "p"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    proj = ROOT / "projects" / slug
    try:
        for sub in ("plan", "assets/vo", "assets/poses", "assets/refs", "assets/fonts/Cairo", "out"):
            assert (proj / sub).is_dir(), sub
        brief = (proj / "BRIEF.md").read_text(encoding="utf-8")
        assert "Scene direction" in brief and "Poses" in brief
        assert "logo" not in brief.lower()
        style = (proj / "STYLE.md").read_text(encoding="utf-8")
        assert "brand/brand.json" in style and "Do not reproduce" in style
        assert (proj / "scenes.py").is_file()          # engine P copied in
        assert list((proj / "assets" / "fonts" / "Cairo").glob("*.ttf"))
        beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
        assert "scenes" in beats
        visual = json.loads((proj / "plan/visual-direction.json").read_text(encoding="utf-8"))
        assert visual["status"] == "draft" and visual["clock"] == "vo" and visual["scenes"] == []
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_reference_analysis_workflow_is_documented_and_scaffolded():
    assert (ROOT / "docs" / "reference-workflow.md").is_file()
    assert (ROOT / "medo-motion" / "scripts" / "reference_report.py").is_file()
    assert (ROOT / "medo-motion" / "templates" / "STYLE.md").is_file()


def test_new_project_scaffolds_remotion(tmp_path):
    slug = f"_pytest-remotion-{tmp_path.name}"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "r"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    proj = ROOT / "projects" / slug
    try:
        package = json.loads((proj / "package.json").read_text(encoding="utf-8"))
        assert package["dependencies"]["remotion"] == "4.0.539"
        assert (proj / "src" / "index.ts").is_file()
        assert (proj / "src" / "lib" / "Presenter.tsx").is_file()
        assert (proj / "STYLE.md").is_file()
        assert (proj / "assets" / "refs").is_dir()
        assert (proj / "public" / "fonts" / "Cairo" / "Cairo_800ExtraBold.ttf").is_file()
        assert (proj / "public" / "fonts" / "Rubik" / "Rubik_900Black.ttf").is_file()
        assert (proj / "public" / "fonts" / "fonts.json").is_file()
        assert (proj / "public" / "assets" / "poses" / "poses.json").is_file()
        beats = json.loads((proj / "plan" / "beats.json").read_text(encoding="utf-8"))
        assert beats["duration"] is None
        import shutil
        if shutil.which("node"):
            blocked = subprocess.run(["node", str(proj / "scripts" / "render.mjs"), "--silent"],
                                     capture_output=True, text=True, cwd=str(proj))
            assert blocked.returncode == 2
            assert "measured VO duration" in blocked.stderr
    finally:
        import shutil
        shutil.rmtree(proj, ignore_errors=True)


def test_new_project_scaffolds_three_engine_hybrid(tmp_path):
    slug = f"_pytest-hybrid-{tmp_path.name}"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "hybrid"],
                       capture_output=True, text=True, cwd=str(ROOT))
    assert r.returncode == 0, r.stderr
    proj = ROOT / "projects" / slug
    try:
        assert (proj / "scenes.py").is_file()                 # P
        assert (proj / "src" / "render.js").is_file()        # K
        assert (proj / "src" / "index.html").is_file()       # K
        assert (proj / "src" / "index.ts").is_file()         # R
        assert (proj / "scripts" / "render.mjs").is_file()   # R
        assert (proj / "HYBRID.md").is_file()
        assert (proj / "package-lock.json").is_file()
        plan = json.loads((proj / "plan" / "hybrid.json").read_text(encoding="utf-8"))
        assert plan["version"] == 1 and plan["segments"] == []
        package = json.loads((proj / "package.json").read_text(encoding="utf-8"))
        assert package["dependencies"]["remotion"] == "4.0.539"
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


def test_collection_paths_do_not_shadow_standard_library_wave(tmp_path):
    # Cold process: wave may already be cached by pytest in this process.
    # Python 3.10 imports stdlib chunk when loading wave; the engine's chunk.py
    # must not run as a side effect of that import (it changes cwd and exits).
    script = '''
import io
import os
import runpy
import sys
before = os.getcwd()
runpy.run_path(sys.argv[1])
import wave
stream = io.BytesIO()
with wave.open(stream, "wb") as writer:
    writer.setnchannels(1)
    writer.setsampwidth(2)
    writer.setframerate(24000)
    writer.writeframes(b"\\0\\0" * 2400)
stream.seek(0)
with wave.open(stream, "rb") as reader:
    assert reader.getnframes() == 2400
assert os.getcwd() == before
assert "scenes" not in sys.modules
'''
    result = subprocess.run([sys.executable, '-c', script, str(ROOT / 'tests' / 'conftest.py')],
                            cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_svg_art_and_phase_four_templates_are_scaffolded():
    assert (SKILL / 'templates/procedural-reels/svg_art.py').is_file()
    assert (SKILL / 'templates/render/lib/svg-art.js').read_bytes() == (SKILL / 'templates/remotion/src/lib/svg-art.js').read_bytes()
    assert (SKILL / 'templates/render/lib/svg-canvas.js').is_file()
    assert (SKILL / 'templates/remotion/src/lib/SvgArt.tsx').is_file()
