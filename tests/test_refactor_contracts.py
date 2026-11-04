"""Regression tests for the refactored seams: transition dispatch, binary resolution, doctor, scaffold.

These are not "does it still render" tests (the engine suites prove that). They pin the structure
the refactor introduced, so a future edit cannot silently bring back the old shape:

* `transition.layer` is a table of small builders — an unknown kind fails loudly instead of
  rendering a blank mask;
* `composite` blends a masked layer through the same helper at both ends (alpha 0 / 1);
* every tool resolves ffmpeg/ffprobe through `tools/lib/media_bin.py`, with one precedence rule;
* `doctor` is importable and its verdict logic is testable without touching the machine;
* `new_project` splits slugging, targeting and scaffolding instead of one 138-line `main`.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from conftest import ENGINE_P, ROOT

sys.path.insert(0, str(ROOT / "tools" / "lib"))
import media_bin  # noqa: E402

sys.path.insert(0, str(ENGINE_P))
import transition  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
import doctor  # noqa: E402
import new_project  # noqa: E402


# ---------------------------------------------------------------- transitions
def test_every_catalogue_kind_has_a_builder():
    """Adding a transition kind without a builder must fail here, not at render time."""
    spec = json.loads((ROOT / "medo-motion" / "motion" / "transitions.json").read_text(encoding="utf-8"))
    kinds = {entry["kind"] for entry in spec["transitions"].values()}
    assert kinds <= set(transition._KIND_BUILDERS), kinds - set(transition._KIND_BUILDERS)


def test_unknown_kind_fails_loudly(monkeypatch):
    """A typo in the catalogue is a bug: never a silent fallback to an empty mask."""
    broken = dict(transition.TRANSITIONS)
    broken["broken"] = {"kind": "not-a-kind", "ease": "linear", "params": {}}
    monkeypatch.setattr(transition, "TRANSITIONS", broken)
    with pytest.raises(ValueError, match="unknown kind"):
        transition.layer("broken", 0.5)


def test_layer_progress_is_recorded_for_every_transition():
    """`p` is the eased progress the renderers read — it must match the requested curve."""
    from motion import ease

    for name in transition.NAMES:
        assert transition.layer(name, 0.4)["p"] == pytest.approx(ease(
            transition.TRANSITIONS[name]["ease"], 0.4))


def test_composite_masked_layer_is_exact_at_both_ends():
    """At p=0 nothing of `b` shows; at p=1 the frame is `b` (per transition, per pixel)."""
    rng = np.random.default_rng(4)
    a = rng.integers(0, 256, (60, 40, 3), dtype=np.uint8)
    b = rng.integers(0, 256, (60, 40, 3), dtype=np.uint8)
    # `irisClose` is an inverted mask by design (a closing hole), so it is checked separately:
    # every *other* transition must start on the outgoing frame and land exactly on the incoming one.
    for name in transition.NAMES:
        start = transition.composite(a, b, name, 0.0)
        end = transition.composite(a, b, name, 1.0)
        assert start.shape == a.shape and end.shape == b.shape
        if name == "irisClose":
            continue
        assert np.array_equal(start, a), f"{name} leaks the incoming frame at p=0"
        assert np.array_equal(end, b), f"{name} does not resolve to the incoming frame at p=1"


def test_iris_close_is_an_inverted_reveal():
    """`irisClose` closes a hole instead of opening one — the mask inverts, the geometry does not."""
    closed, open_ = transition.layer("irisClose", 0.0), transition.layer("irisClose", 1.0)
    assert closed["invert"] is True and closed["circles"][0]["r"] == pytest.approx(0.0)
    assert open_["circles"][0]["r"] > 1.0          # at full progress the hole covers the frame


# ---------------------------------------------------------------- media binaries
def test_media_bin_precedence(monkeypatch, tmp_path):
    """An explicit override wins over PATH; a missing override falls back to PATH."""
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\nexit 0\n")
    fake.chmod(0o755)
    monkeypatch.setenv("FFMPEG_BIN", str(fake))
    assert media_bin.ffmpeg() == str(fake)
    monkeypatch.delenv("FFMPEG_BIN")
    on_path = media_bin.ffmpeg()
    assert on_path is None or Path(on_path).exists()


def test_media_bin_reports_instead_of_crashing(monkeypatch):
    """`required=True` turns a missing binary into a FileNotFoundError with the fix in it."""
    monkeypatch.setattr(media_bin, "_first_executable", lambda candidates: None)
    monkeypatch.setattr(media_bin, "_bundled_ffmpeg", lambda: None)
    assert media_bin.ffmpeg() is None
    with pytest.raises(FileNotFoundError, match="FFMPEG_BIN"):
        media_bin.ffmpeg(required=True)


def test_tools_do_not_reinvent_the_binary_lookup():
    """The duplicated `os.environ.get(...) or shutil.which(...)` pattern must not come back."""
    offenders = []
    for path in sorted((ROOT / "tools").glob("*.py")):
        if path.name in {"media_bin.py", "selftest.py", "doctor.py"}:
            continue                       # these are the shared resolver and its two callers
        text = path.read_text(encoding="utf-8")
        if 'shutil.which("ffmpeg")' in text or "shutil.which('ffmpeg')" in text:
            offenders.append(path.name)
        if 'os.environ.get("FFMPEG_BIN")' in text or "os.environ.get('FFMPEG_BIN')" in text:
            offenders.append(path.name)
    assert not offenders, f"resolve media binaries through tools/lib/media_bin.py: {sorted(set(offenders))}"


# ---------------------------------------------------------------- doctor
def test_doctor_verdict_rules():
    """READY / DEGRADED / BLOCKED are one pure function of the findings."""
    ok = [doctor.Finding("ffmpeg", doctor.OK), doctor.Finding("node", doctor.OK)]
    assert doctor.verdict(ok).startswith("READY")
    assert doctor.verdict([*ok, doctor.Finding("drawtext filter", "WARN")]).startswith("DEGRADED")
    assert "BLOCKED" in doctor.verdict([*ok, doctor.Finding("ffprobe", doctor.MISSING)])
    assert "Chromium" in doctor.verdict([*ok, doctor.Finding("Chromium (engines K/R)", doctor.BLOCKED)])


def test_doctor_is_importable_without_running():
    """It used to be a module-level script: importing it printed the machine's report."""
    result = subprocess.run([sys.executable, "-c", "import doctor; print('imported')"],
                            cwd=str(ROOT / "tools"), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "imported", "doctor must not run on import"


def test_doctor_report_renders_findings():
    findings = [doctor.Finding("ffmpeg", doctor.OK, "9.0"), doctor.Finding("ffprobe", doctor.BLOCKED, "missing")]
    report = doctor.render(findings, "harfbuzz-fallback")
    assert "ffmpeg" in report and "BLOCKED" in report
    assert "Arabic backend: harfbuzz-fallback" in report


def test_doctor_json_envelope_per_engine():
    base = [
        doctor.Finding("Pillow", doctor.OK),
        doctor.Finding("numpy", doctor.OK),
        doctor.Finding("scipy", doctor.OK),
        doctor.Finding("OpenCV", doctor.OK),
        doctor.Finding("PyAV", doctor.OK),
        doctor.Finding("HarfBuzz", doctor.OK),
        doctor.Finding("FreeType", doctor.OK),
        doctor.Finding("Arabic shaping", doctor.OK),
        doctor.Finding("Arabic render smoke", doctor.OK),
        doctor.Finding("Type system", doctor.OK),
        doctor.Finding("Cairo font", doctor.OK),
        doctor.Finding("ffmpeg", doctor.OK),
        doctor.Finding("ffprobe", doctor.OK),
        doctor.Finding("brand lock", doctor.OK),
        doctor.Finding("engine P template", doctor.OK),
        doctor.Finding("engine K template", doctor.OK),
        doctor.Finding("engine R template", doctor.OK),
        doctor.Finding("node", doctor.OK),
        doctor.Finding("playwright-core", doctor.OK),
        doctor.Finding("Chromium (engines K/R)", doctor.OK),
    ]
    ready = doctor.envelope(base, "harfbuzz-fallback")
    assert ready["status"] == "READY"
    assert ready["engines"] == {"P": "READY", "K": "READY", "R": "READY", "Hybrid": "READY"}

    no_chromium = [
        doctor.Finding("Chromium (engines K/R)", doctor.BLOCKED) if f.capability.startswith("Chromium") else f
        for f in base
    ]
    partial = doctor.envelope(no_chromium, "harfbuzz-fallback")
    assert partial["status"] == "BLOCKED"
    assert partial["engines"]["P"] == "READY"
    assert partial["engines"]["K"] == "BLOCKED"
    assert partial["engines"]["R"] == "BLOCKED"
    assert partial["engines"]["Hybrid"] == "BLOCKED"


def test_doctor_cli_json_output():
    import json

    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "doctor.py"), "--json", "--fast"],
        cwd=str(ROOT), capture_output=True, text=True, check=False,
    )
    payload = json.loads(result.stdout)
    assert payload["version"] == 1
    assert payload["status"] in ("READY", "DEGRADED", "BLOCKED")
    assert set(payload["engines"]) == {"P", "K", "R", "Hybrid"}
    assert isinstance(payload["findings"], list) and payload["findings"]


# ---------------------------------------------------------------- scaffold
@pytest.mark.parametrize("raw,expected", [("My Reel!", "my-reel"), ("  Laptop  EP1  ", "laptop-ep1"),
                                          ("a_b__c", "a_b__c"), ("مرحبا", "")])
def test_slugify(raw, expected):
    if expected:
        assert new_project.slugify(raw) == expected
    else:
        with pytest.raises(SystemExit):
            new_project.slugify(raw)


def test_resolve_target_refuses_the_toolkit(tmp_path):
    for read_only in new_project.READ_ONLY_DIRS:
        with pytest.raises(SystemExit, match="read-only"):
            new_project.resolve_target("x", str(ROOT / read_only / "x"))
    with pytest.raises(SystemExit, match="named folder"):
        new_project.resolve_target("x", str(ROOT))


def test_scaffold_is_assembled_from_small_named_steps(tmp_path):
    """`scaffold()` writes the same tree the CLI does, without argparse or printing."""
    project = new_project.scaffold("unit-probe", "p", out=str(tmp_path / "unit-probe"))
    assert (project / ".gitignore").read_text(encoding="utf-8").strip().endswith("*")
    for name in ("beats.json", "copy.json", "text-direction.json", "visual-direction.json"):
        document = json.loads((project / "plan" / name).read_text(encoding="utf-8"))
        assert isinstance(document, dict) and document            # a valid draft, not an empty file
    assert (project / "scenes.py").is_file()                      # engine P copied in
    assert (project / "TASTE.md").is_file()


def test_scaffold_refuses_to_overwrite_without_force(tmp_path):
    new_project.scaffold("twice", "none", out=str(tmp_path / "twice"))
    with pytest.raises(SystemExit, match="already exists"):
        new_project.scaffold("twice", "none", out=str(tmp_path / "twice"))
    new_project.scaffold("twice", "none", out=str(tmp_path / "twice"), force=True)   # --force is explicit
