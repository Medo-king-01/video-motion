"""The reel length is the voice-over length — nothing in the toolkit may prescribe a target length.

These tests pin the rule itself, the tool that measures it, and the two mixers that consume it.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "vo_length.py"
SR = 24000


def _vo(path: Path, spans: list[float], freq: float = 180.0) -> Path:
    """Alternating tone/silence of `spans` seconds each (tone first)."""
    parts = []
    for i, dur in enumerate(spans):
        n = int(dur * SR)
        if i % 2 == 0:
            t = np.arange(n) / SR
            parts.append((0.3 * np.sin(2 * np.pi * freq * t) * 32767).astype(np.int16))
        else:
            parts.append(np.zeros(n, np.int16))
    data = np.concatenate(parts)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())
    return path


@pytest.fixture()
def vo(tmp_path: Path) -> Path:
    return _vo(tmp_path / "vo.wav", [1.0, 0.6, 1.4, 0.5, 0.9])   # 4.40 s, cuts at 1.30 / 3.25


def test_duration_and_bounds_come_from_the_audio(vo: Path, tmp_path: Path):
    beats = tmp_path / "beats.json"
    r = subprocess.run([sys.executable, str(TOOL), str(vo), "--json", str(beats)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(beats.read_text(encoding="utf-8"))
    assert d["duration"] == pytest.approx(4.4, abs=0.02)
    assert d["frames"] == round(d["duration"] * 30)
    # cuts land on the midpoint of each silence (1.0–1.6 and 3.0–3.5)
    assert d["bounds"][0] == 0
    assert d["bounds"][-1] == pytest.approx(d["duration"], abs=0.02)
    assert d["bounds"][1] == pytest.approx(1.30, abs=0.06)
    assert d["bounds"][2] == pytest.approx(3.25, abs=0.06)
    assert len(d["scenes"]) == len(d["bounds"]) - 1
    assert sum(s["dur"] for s in d["scenes"]) == pytest.approx(d["duration"], abs=0.02)


def test_cuts_can_be_snapped_to_a_tempo(vo: Path, tmp_path: Path):
    """Optional: pull each cut onto the beat grid, so the edit lands with the music."""
    beats = tmp_path / "beats.json"
    r = subprocess.run([sys.executable, str(TOOL), str(vo), "--json", str(beats),
                        "--bpm", "120", "--snap-tol", "0.3"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads(beats.read_text(encoding="utf-8"))
    # 1.30 → the nearest eighth note at 120 BPM (0.25 s grid) is 1.25
    assert d["bounds"][1] == pytest.approx(1.25, abs=1e-6)
    assert d["bounds"][-1] == pytest.approx(d["duration"], abs=0.02)   # the VO end never moves
    assert "snapped" in r.stdout
    # without --bpm the cut stays on the silence midpoint
    plain = tmp_path / "plain.json"
    subprocess.run([sys.executable, str(TOOL), str(vo), "--json", str(plain)], check=True,
                   capture_output=True)
    assert json.loads(plain.read_text(encoding="utf-8"))["bounds"][1] == pytest.approx(1.30, abs=0.06)


def test_check_flags_a_reel_that_is_not_the_vo_length(vo: Path, tmp_path: Path):
    proj = tmp_path / "proj"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "data.js").write_text(
        "export const scenes = [\n  { id: 'a', start: 0, end: 1.3 },\n  { id: 'b', start: 1.3, end: 4.4 },\n];\n"
        "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    ok = subprocess.run([sys.executable, str(TOOL), str(vo), "--check", str(proj)],
                        capture_output=True, text=True)
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert "OK" in ok.stdout

    (proj / "src" / "data.js").write_text(
        "export const scenes = [\n  { id: 'a', start: 0, end: 3.1 },\n];\n"
        "export const DURATION = scenes.at(-1).end;\n", encoding="utf-8")
    bad = subprocess.run([sys.executable, str(TOOL), str(vo), "--check", str(proj)],
                         capture_output=True, text=True)
    assert bad.returncode == 1
    assert "MISMATCH" in bad.stdout


def test_remotion_project_bounds_use_the_shared_beats_json(vo: Path, tmp_path: Path):
    proj = tmp_path / "remotion-project"
    (proj / "plan").mkdir(parents=True)
    beats = {
        "duration": 4.4,
        "fps": 30,
        "scenes": [
            {"start": 0.0, "end": 1.3},
            {"start": 1.3, "end": 3.25},
            {"start": 3.25, "end": 4.4},
        ],
    }
    (proj / "plan" / "beats.json").write_text(json.dumps(beats), encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), str(vo), "--check", str(proj)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "OK — the reel is exactly as long as the voice-over" in r.stdout


def test_sfx_bus_length_defaults_to_the_vo(vo: Path, tmp_path: Path):
    cues = tmp_path / "cues.json"
    cues.write_text(json.dumps([{"t": 0.2, "sfx": "pop"}]), encoding="utf-8")
    out = tmp_path / "mix.wav"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "sfx_kit.py"), "--cues", str(cues),
                        "--vo", str(vo), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    from scipy.io import wavfile  # noqa: PLC0415

    sr, data = wavfile.read(out)
    # no --length was passed: the bus is exactly the VO
    assert abs(data.shape[0] / sr - 4.4) <= 0.02


# (pattern, what it means, optional file glob it applies to)
FORBIDDEN = [
    (r"\b30\s*[–-]\s*55\s*(s|ث|sec)", "a 30–55 s length range", None),
    (r"\b45\s*[-–]\s*60\s*s", "a 45–60 s length range", None),
    (r"٥٥\s*ثاني", "a fixed 55 s length", None),
    (r"--length\s+\d", "a hard-coded --length", None),
    (r"\bTOTAL\s*=\s*B\[-1\]\s*$", "a mix length taken from the demo's scene bounds", "mix.py"),
]


def test_nothing_prescribes_a_fixed_reel_length():
    files = [
        *(ROOT / "docs").glob("*.md"),
        ROOT / "AGENTS.md",
        ROOT / "README.md",
        ROOT / "medo-motion" / "templates" / "TASTE.md",
        *(ROOT / "medo-motion" / "styles").glob("*.md"),
        *(ROOT / "medo-motion" / "templates" / "procedural-reels").glob("*.py"),
        *(ROOT / "medo-motion" / "templates" / "render").glob("*.js"),
        *(ROOT / "medo-motion" / "templates" / "remotion" / "src").glob("*.ts*"),
        ROOT / "medo-motion" / "brand" / "brand.json",
    ]
    offenders = []
    for f in files:
        if not f.is_file():
            continue
        text = f.read_text(encoding="utf-8")
        for pattern, what, only in FORBIDDEN:
            if only and f.name != only:
                continue
            for m in re.finditer(pattern, text, re.M):
                line = text[: m.start()].count("\n") + 1
                offenders.append(f"{f.relative_to(ROOT)}:{line} — {what}")
    assert not offenders, "the reel length must be derived from the VO:\n" + "\n".join(offenders)


def test_both_engines_measure_the_vo():
    """Wiring: no engine may take its length from anything but the audio."""
    p_render = (ROOT / "medo-motion" / "templates" / "procedural-reels" / "run_all.py").read_text(encoding="utf-8")
    assert "vo24.wav" in p_render and "TOTAL=" in p_render
    k_render = (ROOT / "medo-motion" / "templates" / "render" / "render.js").read_text(encoding="utf-8")
    assert "probeDuration" in k_render and "VO length" in k_render
    mix_py = (ROOT / "medo-motion" / "templates" / "procedural-reels" / "mix.py").read_text(encoding="utf-8")
    assert "TOTAL=len(v)/SR" in mix_py


def test_the_toolkit_says_the_length_is_the_vo():
    agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert "duration = VO duration" in agents
    brand = json.loads((ROOT / "medo-motion" / "brand" / "brand.json").read_text(encoding="utf-8"))
    assert brand["export"]["duration"].startswith("= VO duration")
    assert "vo_length.py" in brand["export"]["duration"]
