#!/usr/bin/env python3
"""End-to-end self test: prove this machine can really make a reel.

    python3 tools/selftest.py            # doctor + unit tests + a few real frames
    python3 tools/selftest.py --fast     # skip the engine renders

Each step prints PASS / FAIL / SKIP. Exit code 1 if anything failed. Nothing is
written outside a temporary directory.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
ENGINE_K = SKILL / "templates" / "render"
TOOLKIT = ROOT / "tools" / "toolkit"
FAST = "--fast" in sys.argv
results: list[tuple[str, str, str]] = []


def record(name: str, code: int, detail: str = "") -> bool:
    state = {0: "PASS", 1: "FAIL", 2: "SKIP"}.get(code, "FAIL")
    results.append((name, state, detail.strip().splitlines()[-1][:90] if detail.strip() else ""))
    return code == 0


def run(cmd, cwd=None, env=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def ffmpeg_bin() -> str | None:
    if os.environ.get("FFMPEG_BIN"):
        return os.environ["FFMPEG_BIN"]
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def step_doctor() -> bool:
    r = run([sys.executable, str(ROOT / "tools" / "doctor.py"), "--fast"], cwd=ROOT)
    verdict = [ln for ln in r.stdout.splitlines() if ln.startswith(("READY", "DEGRADED", "BLOCKED"))]
    return record("doctor", 0 if r.returncode == 0 else 1, verdict[-1] if verdict else r.stderr)


def step_tests() -> bool:
    r = run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT)
    line = r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr
    return record("unit tests", 0 if r.returncode == 0 else 1, line)


def step_engine_p(work: Path) -> bool:
    ff = ffmpeg_bin()
    if not ff:
        return record("engine P render", 2, "ffmpeg not found")
    proj = work / "p"
    proj.mkdir()
    for f in ENGINE_P.iterdir():
        if f.is_file():
            shutil.copy2(f, proj / f.name)
    fonts = proj / "assets" / "fonts" / "Cairo"
    fonts.mkdir(parents=True)
    for f in (ROOT / "assets" / "fonts" / "Cairo").glob("*.ttf"):
        shutil.copy2(f, fonts / f.name)
    env = {**os.environ, "REEL_DIR": str(proj), "REEL_MAXFRAMES": "6", "FFMPEG_BIN": ff}
    r = run([sys.executable, str(proj / "run_all.py")], cwd=proj, env=env)
    out = proj / "out" / "video_only.mp4"
    ok = r.returncode == 0 and out.is_file() and out.stat().st_size > 1000
    return record("engine P render", 0 if ok else 1, "6 frames encoded" if ok else r.stdout + r.stderr)


def step_engine_k(work: Path) -> bool:
    if not (TOOLKIT / "node_modules" / "playwright-core").exists():
        return record("engine K render", 2, "toolkit not installed")
    proj = work / "k"
    shutil.copytree(ENGINE_K, proj / "src")
    (proj / "package.json").write_text('{"type":"module","private":true}\n', encoding="utf-8")
    os.symlink(TOOLKIT / "node_modules", proj / "node_modules")
    fonts = proj / "assets" / "fonts" / "Cairo"
    fonts.mkdir(parents=True)
    for f in (ROOT / "assets" / "fonts" / "Cairo").glob("*.ttf"):
        shutil.copy2(f, fonts / f.name)
    cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
           f'node src/render.js --from 2.2 --to 3.0 --fps 2 --scale 0.4 --out frames --jpg')
    r = run(["bash", "-c", cmd], cwd=proj)
    frames = list((proj / "frames").glob("*.jpg"))
    ok = r.returncode == 0 and len(frames) >= 1
    return record("engine K render", 0 if ok else 1,
                  f"{len(frames)} frames via Chromium" if ok else r.stdout + r.stderr)


def main() -> int:
    print("medo-motion self test\n")
    step_doctor()
    step_tests()
    if FAST:
        record("engine P render", 2, "--fast")
        record("engine K render", 2, "--fast")
    else:
        with tempfile.TemporaryDirectory(prefix="medo-selftest-") as tmp:
            step_engine_p(Path(tmp))
            step_engine_k(Path(tmp))

    width = max(len(n) for n, _, _ in results) + 2
    print()
    for name, state, detail in results:
        colour = {"PASS": "\033[32m", "SKIP": "\033[90m"}.get(state, "\033[31m")
        print(f"  {name:<{width}}{colour}{state:<6}\033[0m {detail}")
    failed = [n for n, s, _ in results if s == "FAIL"]
    print("\n" + ("SELFTEST FAILED: " + ", ".join(failed) if failed else "SELFTEST OK — ready to make a reel"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
