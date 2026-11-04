#!/usr/bin/env python3
"""medo-motion doctor — is this machine ready to make a reel?

One command any agent can run before starting work:

    python3 tools/doctor.py            # full check (launches Chromium once)
    python3 tools/doctor.py --fast     # skip the browser launch
    python3 tools/doctor.py --json     # structured capability envelope for agents

Prints READY / DEGRADED / BLOCKED with a reason per capability, then a verdict.
Read-only apart from a Chromium launch and one temporary 64×64 PNG.

Every check is a small function returning a `Finding`, so the report can be tested
(`tests/test_doctor.py` drives the parsing and verdict rules without depending on the
machine's packages) and one broken capability can never abort the whole report.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
TMP_ROOT = Path(tempfile.gettempdir()).resolve()

OK, DEGRADED, MISSING, BLOCKED, FAIL, SKIP = "OK", "DEGRADED", "MISSING", "BLOCKED", "FAIL", "SKIP"
# States that make the machine unusable for a reel (MISSING is a subset of blocked work).
BLOCKING_STATES = frozenset({BLOCKED, MISSING, FAIL})
SOFT_STATES = frozenset({"WARN", DEGRADED, SKIP})

PYTHON_PACKAGES = (
    ("PIL", "Pillow", "pillow"),
    ("numpy", "numpy", "numpy"),
    ("scipy", "scipy", "scipy"),
    ("cv2", "OpenCV", "opencv-python-headless"),
    ("av", "PyAV", "av"),
    ("uharfbuzz", "HarfBuzz", "uharfbuzz"),
    ("freetype", "FreeType", "freetype-py"),
)
MIN_NODE = (20, 11)   # the toolkit's package-lock engines field


@dataclass(frozen=True)
class Finding:
    """One capability, its state, and the sentence explaining that state."""

    capability: str
    state: str
    detail: str = ""


# ------------------------------------------------------------------ helpers
def run(argv, timeout: int = 60, env: dict | None = None) -> tuple[int, str]:
    """Run a command and return (exit code, combined output); never raises."""
    try:
        completed = subprocess.run(argv, capture_output=True, text=True, timeout=timeout,
                                   env=env or os.environ)
    except (OSError, subprocess.SubprocessError) as error:
        return 127, str(error)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def module_version(module: str) -> str | None:
    """The installed version string, or None when the import fails for any reason."""
    try:
        imported = __import__(module)
    except ImportError:
        return None
    except Exception:  # noqa: BLE001 - a package can import-and-crash; that is still "unusable"
        return None
    return str(getattr(imported, "__version__", "") or "installed")


def _probe_duration(probe: str, media: Path) -> float | None:
    code, out = run([probe, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(media)], 20)
    if code != 0:
        return None
    try:
        return float(json.loads(out)["format"]["duration"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None


def _write_silence(path: Path, seconds: float = 0.1, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\0\0" * int(rate * seconds))


# ------------------------------------------------------------------ checks
def check_python_stack() -> list[Finding]:
    findings = []
    for module, label, package in PYTHON_PACKAGES:
        version = module_version(module)
        findings.append(Finding(label, OK if version else MISSING,
                                version or f"pip install {package}"))
    return findings


def check_arabic_shaping() -> tuple[Finding, str]:
    """Return the shaping-backend finding and the backend name the rest of the report reuses."""
    try:
        from PIL import features  # noqa: PLC0415 - optional until Pillow is installed
        if features.check("raqm"):
            return Finding("Arabic shaping", OK, "raqm — Pillow RAQM layout"), "raqm"
    except ImportError:
        pass
    sys.path.insert(0, str(ENGINE_P))
    try:
        import arabic_shape  # noqa: F401,PLC0415 - probing the module is the point
    except ImportError as error:
        return Finding("Arabic shaping", BLOCKED, f"none — no shaping backend: {error}"), "none"
    return Finding("Arabic shaping", OK,
                   "harfbuzz-fallback — Pillow has no libraqm; arabic_shape.py (HarfBuzz+FreeType) used"), "harfbuzz-fallback"


def check_type_system() -> Finding:
    """The full 21-family manifest and every declared weight must be on disk."""
    sys.path.insert(0, str(ROOT / "tools"))
    try:
        from fonts_install import FAMILIES, check_type_system  # noqa: PLC0415
    except ImportError as error:
        return Finding("Type system", DEGRADED, f"fonts_install unavailable ({error}) — run: make fonts")
    problems = check_type_system()
    if problems:
        return Finding("Type system", BLOCKED, "; ".join(problems))
    return Finding("Type system", OK, f"{len(FAMILIES)} free families (OFL), files verified")


def brand_font() -> Path | None:
    """Cairo ExtraBold when present, otherwise any Cairo face: the system-chrome fallback."""
    directory = ROOT / "assets" / "fonts" / "Cairo"
    return next(iter(sorted(directory.glob("*800*.ttf")) or sorted(directory.glob("*.ttf"))), None)


def check_arabic_render(font: Path | None, backend: str) -> Finding:
    """Shape one Arabic word and require real ink — a font file alone proves nothing."""
    if font is None:
        return Finding("Arabic render smoke", BLOCKED, "no Cairo font in assets/fonts/Cairo")
    if backend == "none":
        return Finding("Arabic render smoke", BLOCKED, "no backend")
    sys.path.insert(0, str(ENGINE_P))
    try:
        import arabic_shape  # noqa: PLC0415
        sprite = arabic_shape.text_sprite(str(font), "مرحبا", 48, (255, 255, 255), True, 0)
    except Exception as error:  # noqa: BLE001 - any failure here is the finding
        return Finding("Arabic render smoke", FAIL, str(error))
    ink = float((sprite[..., 3] > 0).mean())
    return Finding("Arabic render smoke", OK if ink > 0.02 else FAIL, f"ink coverage {ink:.0%} with {font.name}")


def check_ffmpeg() -> list[Finding]:
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffmpeg  # noqa: PLC0415 - shared precedence rule, see the module docstring

    binary = ffmpeg()
    if not binary:
        return [Finding("ffmpeg", BLOCKED, "not on PATH — bash tools/setup.sh")]
    code, out = run([binary, "-version"], 20)
    version = out.splitlines()[0] if code == 0 and out.strip() else "unknown"
    has_x264 = "libx264" in run([binary, "-hide_banner", "-encoders"], 20)[1]
    has_drawtext = "drawtext" in run([binary, "-hide_banner", "-filters"], 20)[1]
    return [
        Finding("ffmpeg", OK if has_x264 else DEGRADED, f"{version} · libx264 {'yes' if has_x264 else 'NO'}"),
        Finding("drawtext filter", OK if has_drawtext else "WARN",
                "optional: contact-sheet timestamps fall back to ImageMagick"),
    ]


def check_ffprobe() -> Finding:
    """A present binary is not proof: probe a real file and require the real duration."""
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffprobe  # noqa: PLC0415

    probe = ffprobe()
    if not probe:
        return Finding("ffprobe", BLOCKED, "not on PATH — needed for duration/loudness checks")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
        probe_file = Path(handle.name)
    try:
        _write_silence(probe_file)
        duration = _probe_duration(probe, probe_file)
    finally:
        probe_file.unlink(missing_ok=True)
    if duration is None or abs(duration - 0.1) >= 0.01:
        return Finding("ffprobe", BLOCKED,
                       f"present but not functional (duration={duration}) — reinstall: bash tools/setup.sh")
    version = run([probe, "-version"], 20)[1]
    return Finding("ffprobe", OK, "shim (tools/ffprobe_shim.py)" if "shim" in version.lower() else "native")


def check_node(toolkit: Path) -> Finding:
    node = shutil.which("node")
    if not node:
        return Finding("node", BLOCKED, "install Node 20.11+")
    version = run([node, "--version"], 20)[1].strip()
    match = re.match(r"v(\d+)\.(\d+)", version)
    if match and (int(match.group(1)), int(match.group(2))) >= MIN_NODE:
        return Finding("node", OK, f"{version} (>={MIN_NODE[0]}.{MIN_NODE[1]} as the toolkit lockfile requires)")
    return Finding("node", DEGRADED, f"{version} — toolkit deps need >={MIN_NODE[0]}.{MIN_NODE[1]} (package-lock engines)")


def check_chromium(toolkit: Path, fast: bool) -> Finding:
    if fast:
        return Finding("Chromium (engines K/R)", SKIP, "--fast")
    if not shutil.which("node") or not (toolkit / "playwright-core").exists():
        return Finding("Chromium (engines K/R)", SKIP, "node + toolkit deps are missing (checked above)")
    code, out = run(["node", str(ROOT / "tools" / "chromium.mjs"), "--check"], 120)
    lines = out.strip().splitlines()
    return Finding("Chromium (engines K/R)", OK if "CHROMIUM_OK" in out else BLOCKED,
                   lines[-1] if lines else "no output")


def check_templates(font: Path | None) -> list[Finding]:
    remotion = SKILL / "templates" / "remotion"
    remotion_ready = all((remotion / name).is_file() for name in ("package.json", "src/index.ts", "src/Root.tsx"))
    return [
        Finding("brand lock", OK if (SKILL / "brand" / "brand.json").is_file() else BLOCKED,
                str((SKILL / "brand" / "brand.json").relative_to(ROOT))),
        Finding("engine P template", OK if (SKILL / "templates" / "procedural-reels" / "scenes.py").is_file() else BLOCKED),
        Finding("engine K template", OK if (SKILL / "templates" / "render" / "render.js").is_file() else BLOCKED),
        Finding("engine R template", OK if remotion_ready else BLOCKED,
                "Remotion scaffold; install its pinned npm deps in each R project" if remotion_ready
                else "template files missing"),
        Finding("Cairo font", OK if font else BLOCKED, font.name if font else "python3 tools/setup.sh"),
    ]


def collect(fast: bool = False) -> tuple[list[Finding], str]:
    """Run every check and return the findings plus the active Arabic backend."""
    toolkit = ROOT / "tools" / "toolkit" / "node_modules"
    shaping, backend = check_arabic_shaping()
    font = brand_font()
    findings: list[Finding] = [*check_python_stack(), shaping, check_type_system(),
                               check_arabic_render(font, backend), *check_ffmpeg(), check_ffprobe(),
                               check_node(toolkit),
                               Finding("playwright-core", OK if (toolkit / "playwright-core").exists() else MISSING,
                                       "" if (toolkit / "playwright-core").exists() else "tools/toolkit — npm install"),
                               check_chromium(toolkit, fast), *check_templates(font)]
    return findings, backend


# ------------------------------------------------------------------ report
def verdict(findings: list[Finding]) -> str:
    blocked = [f.capability for f in findings if f.state in BLOCKING_STATES]
    soft = [f.capability for f in findings if f.state in SOFT_STATES and f.state != SKIP]
    if blocked:
        return f"BLOCKED — {len(blocked)} item(s): " + ", ".join(blocked)
    if soft:
        return "DEGRADED — usable, but check: " + ", ".join(soft)
    return "READY — P/K templates and the R scaffold are present; install Remotion deps per R project"


def _engine_state(by_name: dict[str, str], required: tuple[str, ...]) -> str:
    states = [by_name.get(name, MISSING) for name in required]
    if any(state in BLOCKING_STATES for state in states):
        return BLOCKED
    if any(state == SKIP for state in states):
        return DEGRADED
    if any(state in SOFT_STATES for state in states):
        return DEGRADED
    return "READY"


def envelope(findings: list[Finding], backend: str) -> dict:
    """Machine-readable capability report so agents do not scrape ANSI output."""
    blocked = [f.capability for f in findings if f.state in BLOCKING_STATES]
    soft = [f.capability for f in findings if f.state in SOFT_STATES and f.state != SKIP]
    status = BLOCKED if blocked else (DEGRADED if soft else "READY")
    by_name = {f.capability: f.state for f in findings}
    p_req = ("Pillow", "numpy", "scipy", "OpenCV", "PyAV", "HarfBuzz", "FreeType",
             "Arabic shaping", "Type system", "Arabic render smoke", "ffmpeg", "ffprobe",
             "brand lock", "engine P template", "Cairo font")
    k_req = ("Type system", "ffmpeg", "ffprobe", "node", "playwright-core",
             "Chromium (engines K/R)", "brand lock", "engine K template")
    r_req = ("Type system", "ffmpeg", "ffprobe", "node",
             "Chromium (engines K/R)", "brand lock", "engine R template")
    engines = {
        "P": _engine_state(by_name, p_req),
        "K": _engine_state(by_name, k_req),
        "R": _engine_state(by_name, r_req),
    }
    engines["Hybrid"] = (
        BLOCKED if BLOCKED in engines.values()
        else (DEGRADED if DEGRADED in engines.values() else "READY")
    )
    return {
        "version": 1,
        "status": status,
        "verdict": verdict(findings),
        "arabic_backend": backend,
        "engines": engines,
        "blocked": blocked,
        "warnings": soft,
        "findings": [
            {"capability": f.capability, "state": f.state, "detail": f.detail}
            for f in findings
        ],
    }


def render(findings: list[Finding], backend: str) -> str:
    width = max(len(f.capability) for f in findings) + 2
    rule = "-" * (width + 46)
    colours = {OK: "\033[32m", "WARN": "\033[33m", SKIP: "\033[90m"}
    lines = ["medo-motion doctor", rule]
    for finding in findings:
        colour = colours.get(finding.state, "\033[31m")
        lines.append(f"{finding.capability:<{width}}{colour}{finding.state:<10}\033[0m {finding.detail[:70]}")
    lines += [rule, verdict(findings),
              f"\nArabic backend: {backend} · project scaffold: python3 tools/new_project.py <slug>"]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    findings, backend = collect(fast="--fast" in args)
    if "--json" in args:
        print(json.dumps(envelope(findings, backend), indent=2))
    else:
        print(render(findings, backend))
    return 1 if any(f.state in BLOCKING_STATES for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
