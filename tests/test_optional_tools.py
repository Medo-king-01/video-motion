"""Contracts for the two optional bridges: `stems.py` (Demucs) and `html_scene.py` (HyperFrames).

Neither dependency is part of the base install, so nothing here needs Demucs, PyTorch, Node 22 or
the HyperFrames CLI: the tests pin the command builders, the static guards and the failure
sentences. A real separation / render is exercised by hand (CHANGELOG, 2026-11-11).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def load(name: str):
    spec = importlib.util.spec_from_file_location(f"optional_{name}", TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stems = load("stems")
html_scene = load("html_scene")


def cli(tool: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOLS / f"{tool}.py"), *args],
                          capture_output=True, text=True, timeout=120, cwd=str(ROOT))


# ---------------------------------------------------------------- stems.py

def test_stems_convert_command_is_44k_stereo_and_windowed() -> None:
    command = stems.build_convert_command("ffmpeg", Path("in.mp4"), Path("o.wav"), start=15, dur=7.5)
    assert command[command.index("-ss") + 1] == "15" and command[command.index("-t") + 1] == "7.5"
    assert command.index("-ss") < command.index("-i"), "seek before the input, not after"
    assert command[-5:] == ["-ac", "2", "-ar", "44100", "o.wav"]
    assert "-ss" not in stems.build_convert_command("ffmpeg", Path("in.mp4"), Path("o.wav"))


def test_stems_demucs_command_passes_only_what_was_asked() -> None:
    plain = stems.build_demucs_command("py", Path("a.wav"), Path("w"))
    assert plain == ["py", "-m", "demucs", "-n", "htdemucs", "-o", "w", "-d", "cpu", "a.wav"]
    full = stems.build_demucs_command("py", Path("a.wav"), Path("w"), two_stems="vocals",
                                      segment=5, weights=Path("local"))
    assert full[-7:] == ["--two-stems", "vocals", "--segment", "5", "--repo", "local", "a.wav"]


def test_stems_rejects_bad_input_before_touching_demucs(tmp_path: Path) -> None:
    missing = cli("stems", str(tmp_path / "nope.wav"), "--out", str(tmp_path / "o"))
    assert missing.returncode == 2 and "input not found" in missing.stderr
    source = tmp_path / "a.wav"
    source.write_bytes(b"RIFF")
    bad = cli("stems", str(source), "--out", str(tmp_path / "o"), "--dur", "0")
    assert bad.returncode == 2 and "--dur" in bad.stderr
    assert not (tmp_path / "o").exists(), "nothing is written for rejected input"


def test_stems_explains_a_missing_optional_dependency(tmp_path: Path) -> None:
    if not stems.missing_dependencies():
        pytest.skip("Demucs is installed here; the missing-dependency sentence cannot be triggered")
    source = tmp_path / "a.wav"
    source.write_bytes(b"RIFF")
    result = cli("stems", str(source), "--out", str(tmp_path / "o"))
    assert result.returncode == 1
    assert "requirements-stems.txt" in result.stderr and "Traceback" not in result.stderr


def test_stems_requirements_stay_below_the_torch_that_breaks_demucs() -> None:
    text = (TOOLS / "requirements-stems.txt").read_text(encoding="utf-8")
    assert "demucs==4.0.1" in text
    assert "torch>=2.2,<2.6" in text and "torchaudio>=2.2,<2.6" in text
    assert "soundfile" in text, "torchaudio needs a WAV backend that does not depend on system FFmpeg libs"


# ---------------------------------------------------------------- html_scene.py

@pytest.fixture()
def scene(tmp_path: Path) -> Path:
    path = tmp_path / "intro"
    assert html_scene.main(["new", str(path), "--frames", "45"]) == 0
    return path


def colours() -> dict:
    return html_scene.brand_colours(json.loads(html_scene.BRAND.read_text(encoding="utf-8")))


def rules(path: Path) -> list[str]:
    return [rule for rule, _ in html_scene.static_findings(path, colours())]


def test_scaffold_is_offline_brand_locked_and_passes_its_own_guards(scene: Path) -> None:
    html = (scene / "index.html").read_text(encoding="utf-8")
    assert "http" not in html and "gsap" not in html.lower()
    assert 'data-duration="1.5"' in html and "data-no-timeline" in html
    assert 'dir="rtl"' in html
    assert (scene / "fonts" / "Cairo_800ExtraBold.ttf").is_file()
    assert (scene / "fonts" / "Cairo - OFL.txt").is_file(), "the font licence travels with the font"
    assert json.loads((scene / "scene.json").read_text(encoding="utf-8"))["frames"] == 45
    assert rules(scene) == []
    assert html_scene.main(["check", str(scene), "--no-lint"]) == 0


def test_scaffold_declares_every_brand_colour_and_no_other(scene: Path) -> None:
    html = (scene / "index.html").read_text(encoding="utf-8")
    brand = json.loads(html_scene.BRAND.read_text(encoding="utf-8"))
    for token, entry in brand["palette"].items():
        assert f"--{token.replace('_', '-')}: {entry['hex'].upper()};" in html


def test_new_refuses_to_overwrite_and_rejects_unknown_fonts(scene: Path, tmp_path: Path) -> None:
    assert html_scene.main(["new", str(scene), "--frames", "30"]) == 2
    with pytest.raises(SystemExit, match="not in assets/fonts"):
        html_scene.main(["new", str(tmp_path / "x"), "--frames", "30", "--font", "Comic Sans"])


def test_variable_font_gets_a_weight_range() -> None:
    faces = html_scene.font_faces("Fustat")
    assert [face["weight"] for face in faces] == ["100 900"]
    assert {face["weight"] for face in html_scene.font_faces("Cairo")} == {"400", "700", "800", "900"}


def edit(scene: Path, old: str, new: str) -> None:
    index = scene / "index.html"
    text = index.read_text(encoding="utf-8")
    assert old in text
    index.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_h01_network_urls_are_rejected_but_xml_namespaces_are_not(scene: Path) -> None:
    edit(scene, "<style>", '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n<style>')
    assert rules(scene) == []
    edit(scene, "<style>", '<script src="https://cdn.jsdelivr.net/npm/gsap@3/dist/gsap.min.js"></script>\n<style>')
    assert rules(scene) == ["H01"]
    (scene / "extra.css").write_text('@import url("//fonts.googleapis.com/css2?family=Cairo");\n', encoding="utf-8")
    assert rules(scene) == ["H01", "H01"]


@pytest.mark.parametrize("css, expected", [
    ("#title { color: #fff; }", ["H02"]),
    ("#title { color: #CB271B; background: rgb(10, 10, 10); }", []),
    ("#title { color: rgba(1, 2, 3, 0.5); }", ["H02"]),
    ("#title { color: hsl(0 80% 40%); }", ["H02"]),
    ("#face { color: var(--ink); }", []),
    ("#fade,\n#bed { opacity: 1; }", []),
])
def test_h02_only_brand_colours(scene: Path, css: str, expected: list[str]) -> None:
    (scene / "extra.css").write_text(css + "\n", encoding="utf-8")
    assert rules(scene) == expected


def test_h03_canvas_and_whole_frame_duration(scene: Path) -> None:
    edit(scene, 'data-width="1080"', 'data-width="1920"')
    assert rules(scene) == ["H03"]
    edit(scene, 'data-width="1920"', 'data-width="1080"')
    edit(scene, 'data-duration="1.5"', 'data-duration="1.51"')
    assert rules(scene) == ["H03"]
    assert html_scene.main(["check", str(scene), "--no-lint"]) == 1


def test_a_folder_that_is_not_a_scene_is_named_as_such(tmp_path: Path) -> None:
    assert rules(tmp_path) == ["H03"]


def test_render_refuses_a_failing_scene_before_launching_anything(scene: Path, tmp_path: Path) -> None:
    (scene / "extra.css").write_text("#title { color: #123456; }\n", encoding="utf-8")
    out = tmp_path / "clip.mp4"
    assert html_scene.main(["render", str(scene), "--out", str(out)]) == 1
    assert not out.exists()


def test_hyperframes_is_pinned_isolated_and_not_a_base_dependency() -> None:
    package = json.loads((TOOLS / "optional-hyperframes" / "package.json").read_text(encoding="utf-8"))
    assert package["dependencies"] == {"hyperframes": "0.9.9"}, "exact reviewed version (docs/hyperframes-fit.md)"
    lock = json.loads((TOOLS / "optional-hyperframes" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/hyperframes"]["version"] == "0.9.9"
    toolkit = json.loads((TOOLS / "toolkit" / "package.json").read_text(encoding="utf-8"))
    assert "hyperframes" not in toolkit["dependencies"]
    assert "hyperframes" not in (TOOLS / "setup.sh").read_text(encoding="utf-8")
    assert "hyperframes" not in (TOOLS / "render_hybrid.py").read_text(encoding="utf-8").lower()
    wrapper = (TOOLS / "hyperframes.sh").read_text(encoding="utf-8")
    assert "HYPERFRAMES_NO_TELEMETRY=1" in wrapper and "HYPERFRAMES_SKIP_SKILLS=1" in wrapper


@pytest.mark.parametrize("tool", ["stems", "html_scene"])
def test_cli_answers_help_and_rejects_unknown_flags(tool: str) -> None:
    assert "usage:" in cli(tool, "--help").stdout
    bad = cli(tool, "--not-a-real-flag")
    assert bad.returncode == 2 and "usage:" in bad.stderr
