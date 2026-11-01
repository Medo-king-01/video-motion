#!/usr/bin/env python3
"""medo-motion doctor — is this machine ready to make a reel?

One command any agent can run before starting work:

    python3 tools/doctor.py            # full check (launches Chromium once)
    python3 tools/doctor.py --fast     # skip the browser launch

Prints READY / DEGRADED / BLOCKED with a reason per capability, then a verdict.
Read-only apart from a Chromium launch and one temporary 64×64 PNG.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
FAST = "--fast" in sys.argv
rows: list[tuple[str, str, str]] = []          # (capability, state, detail)


def add(cap, state, detail=""):
    rows.append((cap, state, detail))


def have(mod):
    try:
        m = __import__(mod)
    except Exception:
        return None
    return str(getattr(m, "__version__", "") or "installed")


def run(cmd, timeout=60, env=None):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env or os.environ)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:
        return 127, str(e)


# ------------------------------------------------------------------ python stack
for mod, label in [("PIL", "Pillow"), ("numpy", "numpy"), ("scipy", "scipy"),
                   ("cv2", "OpenCV"), ("av", "PyAV"), ("uharfbuzz", "HarfBuzz"),
                   ("freetype", "FreeType")]:
    v = have(mod)
    add(label, "OK" if v else "MISSING", v if v else "pip install " + {
        "PIL": "pillow", "cv2": "opencv-python-headless", "av": "av",
        "uharfbuzz": "uharfbuzz", "freetype": "freetype-py"}.get(mod, mod))

# ------------------------------------------------------------------ arabic shaping
backend = "none"
detail = ""
try:
    from PIL import features
    if features.check("raqm"):
        backend, detail = "raqm", "Pillow RAQM layout"
except Exception:
    pass
if backend == "none":
    try:
        sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
        import arabic_shape  # noqa: PLC0415 — path is injected right above                                        # noqa: F401
        backend = "harfbuzz-fallback"
        detail = "Pillow has no libraqm; arabic_shape.py (HarfBuzz+FreeType) used"
    except Exception as e:
        backend, detail = "none", f"no shaping backend: {e}"
add("Arabic shaping", "OK" if backend != "none" else "BLOCKED", f"{backend} — {detail}")

# real render check: shape one Arabic word and require ink
# the type system: manifest first, then the brand file (Cairo 800 preferred — see docs/fonts.md)
try:
    _sys_fams = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))["families"]
    add("Type system", "OK" if len(_sys_fams) >= 14 else "DEGRADED",
        f"{len(_sys_fams)} free families (OFL) in assets/fonts/fonts.json")
except Exception as e:
    _sys_fams = {}
    add("Type system", "DEGRADED", f"no assets/fonts/fonts.json ({e}) — run: make fonts")
_cairo = sorted((ROOT / "assets" / "fonts" / "Cairo").glob("*800*.ttf")) \
    or sorted((ROOT / "assets" / "fonts" / "Cairo").glob("*.ttf"))
font = next(iter(_cairo), None)
if font and backend != "none":
    try:
        sys.path.insert(0, str(SKILL / "templates" / "procedural-reels"))
        import arabic_shape  # noqa: PLC0415 — path is injected right above
        spr = arabic_shape.text_sprite(str(font), "مرحبا", 48, (255, 255, 255), True, 0)
        ink = float((spr[..., 3] > 0).mean())
        add("Arabic render smoke", "OK" if ink > 0.02 else "FAIL", f"ink coverage {ink:.0%} with {font.name}")
    except Exception as e:
        add("Arabic render smoke", "FAIL", str(e))
else:
    add("Arabic render smoke", "SKIP" if not font else "BLOCKED",
        "no Cairo font in assets/fonts/Cairo" if not font else "no backend")

# ------------------------------------------------------------------ ffmpeg
ff = shutil.which("ffmpeg")
if ff:
    code, out = run([ff, "-version"], 20)
    ver = out.splitlines()[0] if code == 0 else "unknown"
    enc = run([ff, "-hide_banner", "-encoders"], 20)[1]
    x264 = "libx264" in enc
    add("ffmpeg", "OK" if x264 else "DEGRADED", f"{ver} · libx264 {'yes' if x264 else 'NO'}")
    add("drawtext filter", "OK" if "drawtext" in run([ff, "-hide_banner", "-filters"], 20)[1] else "WARN",
        "optional: contact-sheet timestamps fall back to ImageMagick")
else:
    add("ffmpeg", "BLOCKED", "not on PATH — bash tools/setup.sh")

fprobe = shutil.which("ffprobe")
if fprobe:
    code, out = run([fprobe, "-version"], 20)
    add("ffprobe", "OK", "shim" if "shim" in out or code != 0 else "native")
else:
    add("ffprobe", "BLOCKED", "not on PATH — needed for duration/loudness checks")

# ------------------------------------------------------------------ node + browser
node = shutil.which("node")
add("node", "OK" if node else "BLOCKED", run([node, "--version"], 20)[1].strip() if node else "install Node 18+")
toolkit = ROOT / "tools" / "toolkit" / "node_modules"
add("playwright-core", "OK" if (toolkit / "playwright-core").exists() else "MISSING",
    "tools/toolkit — npm install" if not (toolkit / "playwright-core").exists() else "")

if node and (toolkit / "playwright-core").exists() and not FAST:
    code, out = run([node, str(ROOT / "tools" / "chromium.mjs"), "--check"], 120)
    good = "CHROMIUM_OK" in out
    add("Chromium (engines K/R)", "OK" if good else "BLOCKED",
        out.strip().splitlines()[-1] if out.strip() else "no output")
elif FAST:
    add("Chromium (engines K/R)", "SKIP", "--fast")

# ------------------------------------------------------------------ brand + templates
add("brand lock", "OK" if (SKILL / "brand" / "brand.json").is_file() else "BLOCKED",
    str((SKILL / "brand" / "brand.json").relative_to(ROOT)))
add("engine P template", "OK" if (SKILL / "templates" / "procedural-reels" / "scenes.py").is_file() else "BLOCKED")
add("engine K template", "OK" if (SKILL / "templates" / "render" / "render.js").is_file() else "BLOCKED")
remotion_template = SKILL / "templates" / "remotion"
remotion_ready = all((remotion_template / f).is_file() for f in ("package.json", "src/index.ts", "src/Root.tsx"))
add("engine R template", "OK" if remotion_ready else "BLOCKED",
    "Remotion scaffold; install its pinned npm deps in each R project" if remotion_ready else "template files missing")
add("Cairo font", "OK" if font else "BLOCKED", str(font.name) if font else "python3 tools/setup.sh")

# ------------------------------------------------------------------ report
width = max(len(r[0]) for r in rows) + 2
print("medo-motion doctor\n" + "-" * (width + 46))
for cap, state, detail in rows:
    colour = {"OK": "\033[32m", "WARN": "\033[33m", "SKIP": "\033[90m"}.get(state, "\033[31m")
    print(f"{cap:<{width}}{colour}{state:<10}\033[0m {detail[:70]}")
print("-" * (width + 46))

blocked = [r for r in rows if r[1] in ("BLOCKED", "MISSING", "FAIL")]
degraded = [r for r in rows if r[1] in ("WARN", "DEGRADED")]
if blocked:
    verdict = f"BLOCKED — {len(blocked)} item(s): " + ", ".join(r[0] for r in blocked)
elif degraded:
    verdict = "DEGRADED — usable, but check: " + ", ".join(r[0] for r in degraded)
else:
    verdict = "READY — P/K templates and the R scaffold are present; install Remotion deps per R project"
print(verdict)
print(f"\nArabic backend: {backend} · project scaffold: python3 tools/new_project.py <slug>")
sys.exit(1 if blocked else 0)
