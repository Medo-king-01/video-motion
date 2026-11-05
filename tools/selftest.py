#!/usr/bin/env python3
"""End-to-end self test: prove this machine can really make a reel.

    python3 tools/selftest.py                 # doctor + unit tests + P/K smoke renders
    python3 tools/selftest.py --fast          # skip the engine renders
    python3 tools/selftest.py --remotion      # also npm ci + R typecheck + 6-frame render
    python3 tools/selftest.py --hybrid        # end-to-end 18-frame P + K + R assembly
    python3 tools/selftest.py --skip-tests     # skip pytest when tools/ci.sh already ran
    python3 tools/selftest.py --remotion --hybrid --reduced-motion  # explicit reduced-mode smoke

Each step prints PASS / FAIL / SKIP. Exit code 1 if anything failed. The `--remotion`
option installs pinned dependencies in a throwaway project under `projects/` and
removes it when finished.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
ENGINE_P = SKILL / "templates" / "procedural-reels"
ENGINE_K = SKILL / "templates" / "render"
TOOLKIT = ROOT / "tools" / "toolkit"
FAST = "--fast" in sys.argv
SKIP_TESTS = "--skip-tests" in sys.argv
WITH_REMOTION = "--remotion" in sys.argv
WITH_HYBRID = "--hybrid" in sys.argv
REDUCED = "--reduced-motion" in sys.argv or os.environ.get("MEDO_MOTION_MODE") == "reduced"

def motion_env():
    return {**os.environ, "MEDO_MOTION_MODE": "reduced"} if REDUCED else os.environ.copy()
results: list[tuple[str, str, str]] = []


def record(name: str, code: int, detail: str = "") -> bool:
    state = {0: "PASS", 1: "FAIL", 2: "SKIP"}.get(code, "FAIL")
    results.append((name, state, detail.strip().splitlines()[-1][:90] if detail.strip() else ""))
    return code == 0


def run(cmd, cwd=None, env=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)


def media_bin(name: str) -> str | None:
    """Resolve ffmpeg/ffprobe through the one shared precedence rule (tools/lib/media_bin.py)."""
    sys.path.insert(0, str(ROOT / "tools" / "lib"))
    from media_bin import ffmpeg, ffprobe  # noqa: PLC0415 - only needed once a render step runs

    return (ffmpeg if name == "ffmpeg" else ffprobe)()


def ffmpeg_bin() -> str | None:
    return media_bin("ffmpeg")


def ffprobe_bin() -> str | None:
    return media_bin("ffprobe")


def step_doctor() -> bool:
    r = run([sys.executable, str(ROOT / "tools" / "doctor.py"), "--fast"], cwd=ROOT)
    verdict = [ln for ln in r.stdout.splitlines() if ln.startswith(("READY", "DEGRADED", "BLOCKED"))]
    return record("doctor", 0 if r.returncode == 0 else 1, verdict[-1] if verdict else r.stderr)


def step_tests() -> bool:
    # Stream pytest output so CI logs retain the actual failing test and traceback.
    r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, text=True)
    return record("unit tests", 0 if r.returncode == 0 else 1,
                  f"pytest exit code {r.returncode}")


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
    env = {**motion_env(), "REEL_DIR": str(proj), "REEL_MAXFRAMES": "6", "FFMPEG_BIN": ff}
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
    timing = "--from 0.2 --to 0.4 --fps 30" if REDUCED else "--from 2.2 --to 3.0 --fps 2"
    cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
           f'node src/render.js {timing} --scale 0.4 --out frames --jpg')
    r = run(["bash", "-c", cmd], cwd=proj, env=motion_env())
    frames = list((proj / "frames").glob("*.jpg"))
    ok = r.returncode == 0 and len(frames) >= 1
    return record("engine K render", 0 if ok else 1,
                  f"{len(frames)} frames via Chromium" if ok else r.stdout + r.stderr)


def fill_story_cards(proj: Path) -> None:
    """render.mjs refuses the template's placeholder copy — give the scenes real cards."""
    data_ts = proj / "src" / "data.ts"
    if not data_ts.is_file():
        return
    src = data_ts.read_text(encoding="utf-8")
    for old, new in [("اكتب عنوان المشهد", "عنوان المشهد التجريبي"),
                     ("حط هنا الجملة الأساسية", "جملة أساسية تجريبية"),
                     ("الحركة والإيقاع بيساعدوا", "وضوح الفكرة.")]:
        src = src.replace(old, new)
    data_ts.write_text(src, encoding="utf-8")


def fill_text_direction(proj: Path, beats: dict) -> None:
    """The render gates require an explicit, agent-chosen style per scene."""
    styles = ["karaoke", "softFade", "zoomPunch", "underline", "fadeTilt", "wordPop"]
    scenes = []
    for i, s in enumerate(beats.get("scenes") or []):
        st = styles[i % len(styles)]
        scenes.append({"scene": s.get("index", i + 1), "captionStyle": st,
                       "captionWhy": f"selftest scene {i+1} uses {st}",
                       "textStyles": {"title": st, "body": "softFade", "label": st},
                       "textWhy": f"selftest scene {i+1} title/body/label styles",
                       "fontStyles": {"title": {"family": "Alexandria", "weight": 800},
                                      "body": {"family": "Readex Pro", "weight": 600},
                                      "label": {"family": "Tajawal", "weight": 700}},
                       "fontWhy": f"selftest scene {i+1} agent-chosen faces"})
    direction = {"version": 3, "status": "directed", "decidedBy": "agent",
                 "concept": "selftest text direction exercising the per-scene style gate",
                 "scenes": scenes}
    (proj / "plan" / "text-direction.json").write_text(json.dumps(direction) + "\n", encoding="utf-8")


def step_engine_r() -> bool:
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        return record("engine R render", 2, "npm/Node.js not found")
    proj = ROOT / "projects" / f"_selftest-remotion-{os.getpid()}"
    if proj.exists():
        return record("engine R render", 1, f"refusing to overwrite {proj.relative_to(ROOT)}")
    scaffold = run([sys.executable, str(ROOT / "tools" / "new_project.py"), proj.name, "--engine", "r"],
                   cwd=ROOT, timeout=60)
    if scaffold.returncode:
        return record("engine R render", 1, scaffold.stdout + scaffold.stderr)
    try:
        installed = run([npm, "ci"], cwd=proj, timeout=600)
        if installed.returncode:
            return record("engine R render", 1, installed.stdout + installed.stderr)
        beats = {"duration": 0.4, "fps": 30, "frames": 12, "bounds": [0, 0.4],
                 "scenes": [{"index": 1, "start": 0, "end": 0.4, "dur": 0.4, "frames": 12}]}
        (proj / "plan" / "beats.json").write_text(json.dumps(beats) + "\n", encoding="utf-8")
        fill_story_cards(proj)
        fill_text_direction(proj, beats)
        # Exercise all three declarative scene effects in the actual Remotion renderer.
        public_effects = proj / "public" / "effects"
        public_effects.mkdir(parents=True, exist_ok=True)
        (public_effects / "selftest.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">'
            '<rect width="320" height="320" fill="#d94848"/>'
            '<circle cx="160" cy="160" r="92" fill="#ffffff"/>'
            '<path d="M60 160h200M160 60v200" stroke="#202020" stroke-width="12"/>'
            '</svg>\n',
            encoding="utf-8",
        )
        (proj / "plan" / "effects.json").write_text(json.dumps({
            "scenes": [{
                "scene": 1,
                "effects": [
                    {"type": "lightSweep", "start": 0, "duration": 0.32},
                    {"type": "whipPan", "start": 0.02, "duration": 0.24, "distance": 0.12},
                    {"type": "particleDissolve", "source": "effects/selftest.svg",
                     "start": 0.08, "duration": 0.28, "count": 16, "seed": 7},
                ],
            }],
        }) + "\n", encoding="utf-8")
        # render.mjs refuses placeholder copy — give the one scene its real card
        data_ts = proj / "src" / "data.ts"
        src = data_ts.read_text(encoding="utf-8")
        for old, new in [("اكتب عنوان المشهد", "عنوان المشهد التجريبي"),
                         ("حط هنا الجملة الأساسية", "جملة أساسية تجريبية"),
                         ("الحركة والإيقاع بيساعدوا الفكرة توصل بوضوح.", "وضوح الفكرة.")]:
            src = src.replace(old, new)
        data_ts.write_text(src, encoding="utf-8")
        stills = run([npm, "run", "stills", "--", "0", "0.1"], cwd=proj, env=motion_env(), timeout=300)
        if stills.returncode:
            return record("engine R render", 1, stills.stdout + stills.stderr)
        checked = run([npm, "run", "typecheck"], cwd=proj, timeout=180)
        if checked.returncode:
            return record("engine R render", 1, checked.stdout + checked.stderr)
        rendered = run([node, str(proj / "scripts" / "render.mjs"), "--silent",
                        "--from-frame", "2", "--to-frame", "8", "--out", "out/selftest.mp4"],
                       cwd=proj, env=motion_env(), timeout=600)
        output = proj / "out" / "selftest.mp4"
        ok = rendered.returncode == 0 and output.is_file() and output.stat().st_size > 1000
        return record("engine R render", 0 if ok else 1,
                      "6 frames via Remotion + shared Chromium" if ok else rendered.stdout + rendered.stderr)
    finally:
        shutil.rmtree(proj, ignore_errors=True)


def step_hybrid() -> bool:
    npm = shutil.which("npm")
    node = shutil.which("node")
    ff = ffmpeg_bin()
    ffprobe = ffprobe_bin()
    if not npm or not node or not ff or not ffprobe:
        return record("hybrid P/K/R render", 2, "npm, Node.js, ffmpeg or ffprobe not found")
    if not (TOOLKIT / "node_modules" / "playwright-core").exists():
        return record("hybrid P/K/R render", 2, "shared K toolkit not installed")
    proj = ROOT / "projects" / f"_selftest-hybrid-{os.getpid()}"
    if proj.exists():
        return record("hybrid P/K/R render", 1, f"refusing to overwrite {proj.relative_to(ROOT)}")
    scaffold = run([sys.executable, str(ROOT / "tools" / "new_project.py"), proj.name, "--engine", "hybrid"],
                   cwd=ROOT, timeout=60)
    if scaffold.returncode:
        return record("hybrid P/K/R render", 1, scaffold.stdout + scaffold.stderr)
    try:
        installed = run([npm, "ci"], cwd=proj, timeout=600)
        if installed.returncode:
            return record("hybrid P/K/R render", 1, installed.stdout + installed.stderr)
        checked = run([npm, "run", "typecheck"], cwd=proj, timeout=180)
        if checked.returncode:
            return record("hybrid P/K/R render", 1, checked.stdout + checked.stderr)
        browser_info = run([node, str(ROOT / "tools" / "chromium.mjs"), "--json"], cwd=ROOT, timeout=180)
        if browser_info.returncode:
            return record("hybrid P/K/R render", 1, browser_info.stdout + browser_info.stderr)
        browser = json.loads(browser_info.stdout)
        env = {**motion_env(), "MEDO_TOOLKIT": str(TOOLKIT), "MEDO_CHROMIUM": browser["executablePath"],
               "FFMPEG_BIN": ff, "FFPROBE_BIN": ffprobe, "PYTHONUNBUFFERED": "1"}
        if browser.get("libraryPath"):
            env["LD_LIBRARY_PATH"] = browser["libraryPath"] + ":" + env.get("LD_LIBRARY_PATH", "")
        audio_path = proj / "assets" / "vo" / "hybrid-selftest.wav"
        with wave.open(str(audio_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(48_000)
            wav.writeframes(bytes(2 * int(0.6 * 48_000)))
        (proj / "plan" / "hybrid.json").write_text(json.dumps({
            "version": 1, "fps": 30, "width": 1080, "height": 1920, "duration_frames": 18,
            "audio": "assets/vo/hybrid-selftest.wav",
            "segments": [
                {"id": "p-smoke", "engine": "p", "start_frame": 0, "end_frame": 6},
                {"id": "k-smoke", "engine": "k", "start_frame": 6, "end_frame": 12},
                {"id": "r-smoke", "engine": "r", "start_frame": 12, "end_frame": 18},
            ],
        }) + chr(10), encoding="utf-8")
        beats = {"duration": 0.6, "fps": 30, "frames": 18, "bounds": [0, 0.6],
                 "scenes": [{"index": 1, "start": 0, "end": 0.6, "dur": 0.6, "frames": 18}]}
        (proj / "plan" / "beats.json").write_text(json.dumps(beats) + chr(10), encoding="utf-8")
        fill_story_cards(proj)
        fill_text_direction(proj, beats)
        rendered = run([sys.executable, str(ROOT / "tools" / "render_hybrid.py"), "--project", str(proj),
                        "--ffmpeg", ff, "--ffprobe", ffprobe, "--profile"],
                       cwd=proj, env=env, timeout=900)
        output = proj / "out" / "hybrid.mp4"
        profile = output.with_name(output.name + ".profile.json")
        ok = rendered.returncode == 0 and output.is_file() and output.stat().st_size > 1000 and profile.is_file()
        if ok: ok = json.loads(profile.read_text())["motionMode"] == ("reduced" if REDUCED else env.get("MEDO_MOTION_MODE", "normal"))
        return record("hybrid P/K/R render", 0 if ok else 1,
                      "P + K + R segments assembled and probed" if ok else rendered.stdout + rendered.stderr)
    finally:
        shutil.rmtree(proj, ignore_errors=True)


def main() -> int:
    print("Video Motion self-test\n")
    step_doctor()
    if SKIP_TESTS:
        record("unit tests", 2, "--skip-tests; run tools/ci.sh first")
    else:
        step_tests()
    if FAST:
        record("engine P render", 2, "--fast")
        record("engine K render", 2, "--fast")
        record("engine R render", 2, "--fast")
        record("hybrid P/K/R render", 2, "--fast")
    else:
        with tempfile.TemporaryDirectory(prefix="medo-selftest-") as tmp:
            step_engine_p(Path(tmp))
            step_engine_k(Path(tmp))
        if WITH_REMOTION:
            step_engine_r()
        else:
            record("engine R render", 2, "per-project npm deps; pass --remotion to test this engine")
        if WITH_HYBRID:
            step_hybrid()
        else:
            record("hybrid P/K/R render", 2, "pass --hybrid to test end-to-end assembly")

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
