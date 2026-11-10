"""Minimal contracts for tools that nothing else exercised.

Seven tools had no test at all (`ffprobe_shim`, `fonts_preview`, `itshover_import`,
`transitions_sheet`, `visual_verify`, `whisper_align`, `whisper_fetch`). A full test suite for each
would be its own project; what is missing is the *contract*: every one of them is a CLI that must
answer `--help`, reject bad input loudly, and either produce its declared artefact or fail with a
sentence a human can act on. That is what this file pins.

The heavy visual tools are covered elsewhere (fixtures, sheets), so here they only prove they are
CLIs with a usage screen rather than scripts that explode on import.
"""
from __future__ import annotations

import json
import subprocess
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
TOOLS = ROOT / "tools"


def run(tool: str, *args: str, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PY, str(TOOLS / f"{tool}.py"), *args],
                          capture_output=True, text=True, timeout=timeout,
                          cwd=str(ROOT), env={"PATH": f"{ROOT / 'tools' / 'bin'}:{__import__('os').environ.get('PATH', '')}",
                                              "HOME": str(Path.home())})


CLI_TOOLS = ("fonts_preview", "itshover_import", "transitions_sheet", "visual_verify",
             "whisper_align", "whisper_fetch")


@pytest.mark.parametrize("tool", CLI_TOOLS)
def test_every_cli_answers_help(tool: str) -> None:
    result = run(tool, "--help")
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


@pytest.mark.parametrize("tool", CLI_TOOLS)
def test_every_cli_rejects_unknown_flags(tool: str) -> None:
    result = run(tool, "--not-a-real-flag")
    assert result.returncode == 2
    assert "usage:" in (result.stdout + result.stderr)


def write_wav(path: Path, seconds: float = 0.5, rate: int = 24000) -> Path:
    frames = int(seconds * rate)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * frames)
    return path


def test_ffprobe_shim_answers_the_subset_the_studio_uses(tmp_path: Path) -> None:
    audio = write_wav(tmp_path / "tone.wav", seconds=0.5)
    listed = run_ffprobe("-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio))
    assert listed.returncode == 0, listed.stderr
    payload = json.loads(listed.stdout)
    assert float(payload["format"]["duration"]) == pytest.approx(0.5, abs=0.02)

    streams = run_ffprobe("-v", "error", "-select_streams", "a:0", "-show_streams",
                          "-print_format", "json", str(audio))
    assert streams.returncode == 0, streams.stderr
    stream = json.loads(streams.stdout)["streams"][0]
    assert stream["codec_name"] == "pcm_s16le"
    assert int(stream["sample_rate"]) == 24000


def run_ffprobe(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([PY, str(TOOLS / "ffprobe_shim.py"), *args],
                          capture_output=True, text=True, timeout=120, cwd=str(ROOT))


def write_executable(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)
    return path


def run_shim(*args: str, path_prefix: Path | None = None,
             extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    import os  # noqa: PLC0415 - only these tests need to build a PATH
    env = {"PATH": f"{path_prefix}{os.pathsep}{os.environ.get('PATH', '')}" if path_prefix
           else os.environ.get("PATH", ""), "HOME": str(Path.home())}
    env.update(extra_env or {})
    return subprocess.run([PY, str(TOOLS / "ffprobe_shim.py"), *args], capture_output=True,
                          text=True, timeout=120, cwd=str(ROOT), env=env)


def test_ffprobe_shim_delegates_to_a_real_ffprobe(tmp_path: Path) -> None:
    """The shim is the fallback: a real binary on PATH must answer instead (N10)."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "ffprobe", '#!/bin/sh\necho \'{"delegated": true}\'\n')
    result = run_shim("-show_entries", "format=duration", "x.wav", path_prefix=bin_dir)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"delegated": True}


def test_ffprobe_shim_never_delegates_to_itself(tmp_path: Path) -> None:
    """`tools/bin/ffprobe` is a wrapper that runs this script — execing it would loop forever."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "ffprobe",
                     f'#!/bin/sh\nexec "{PY}" "{TOOLS / "ffprobe_shim.py"}" "$@"\n')
    audio = write_wav(tmp_path / "tone.wav", seconds=0.25)
    result = run_shim("-v", "error", "-show_entries", "format=duration", "-of", "json",
                      str(audio), path_prefix=bin_dir)
    assert result.returncode == 0, result.stderr
    assert float(json.loads(result.stdout)["format"]["duration"]) == pytest.approx(0.25, abs=0.02)


def test_ffprobe_shim_only_mode_keeps_the_fallback(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    write_executable(bin_dir / "ffprobe", '#!/bin/sh\necho \'{"delegated": true}\'\n')
    audio = write_wav(tmp_path / "tone.wav", seconds=0.25)
    result = run_shim("-show_entries", "format=duration", "-of", "json", str(audio),
                      path_prefix=bin_dir, extra_env={"MEDO_FFPROBE_SHIM_ONLY": "1"})
    assert result.returncode == 0, result.stderr
    assert "delegated" not in result.stdout
    assert float(json.loads(result.stdout)["format"]["duration"]) == pytest.approx(0.25, abs=0.02)


def test_ffprobe_shim_declares_every_field_it_emits(tmp_path: Path) -> None:
    """`--supported` is a promise: anything the fallback prints must be in the catalogue."""
    catalogue = json.loads(run_shim("--supported").stdout)
    audio = write_wav(tmp_path / "tone.wav", seconds=0.25)
    payload = json.loads(run_shim("-show_streams", "-show_format", str(audio),
                                  extra_env={"MEDO_FFPROBE_SHIM_ONLY": "1"}).stdout)
    streams = set().union(*(set(stream) for stream in payload["streams"]))
    assert streams <= set(catalogue["streams"]), f"streams: undeclared {streams - set(catalogue['streams'])}"
    fmt = set(payload["format"])
    assert fmt <= set(catalogue["format"]), f"format: undeclared {fmt - set(catalogue['format'])}"


def test_ffprobe_shim_fails_loudly_on_a_missing_file(tmp_path: Path) -> None:
    result = run_ffprobe("-show_entries", "format=duration", str(tmp_path / "absent.wav"))
    assert result.returncode != 0
    assert "absent.wav" in result.stdout + result.stderr


def test_fonts_preview_writes_a_sheet_of_the_requested_width(tmp_path: Path) -> None:
    from PIL import Image  # noqa: PLC0415 - only this test needs it

    out = tmp_path / "fonts.png"
    result = run("fonts_preview", "--out", str(out), "--width", "360", "--light")
    assert result.returncode == 0, result.stderr
    with Image.open(out) as image:
        assert image.width == 360
        assert image.height > 0


def test_transitions_sheet_can_render_one_transition(tmp_path: Path) -> None:
    catalog = json.loads((ROOT / "medo-motion" / "motion" / "transitions.json").read_text(encoding="utf-8"))
    name = next(iter(catalog["transitions"]))
    out = tmp_path / "one.png"
    result = run("transitions_sheet", "--only", name, "--out", str(out))
    assert result.returncode == 0, result.stderr
    assert out.is_file() and out.stat().st_size > 0


def test_itshover_list_prints_the_registry() -> None:
    result = run("itshover_import", "--list")
    assert result.returncode == 0, result.stderr
    assert "-icon" in result.stdout


def test_whisper_align_explains_a_missing_optional_dependency() -> None:
    """`faster-whisper` is optional; the tool must say so instead of raising ImportError."""
    try:
        import faster_whisper  # noqa: F401, PLC0415 - probing the optional dependency
    except ImportError:
        missing = True
    else:
        missing = False
    result = run("whisper_align", "missing.wav", "--model", "m", "--out", "o.json")
    if missing:
        assert result.returncode == 2
        assert "faster-whisper" in result.stderr and "pip install" in result.stderr
        assert "Traceback" not in result.stderr
    else:
        assert result.returncode != 0  # still fails on the missing inputs, never silently succeeds
