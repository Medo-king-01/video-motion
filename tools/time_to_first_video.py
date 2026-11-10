#!/usr/bin/env python3
"""Measure "time to first video": from a clean checkout to a playable MP4, per phase.

    python3 tools/time_to_first_video.py                  # one run, 2-second video, engine K
    python3 tools/time_to_first_video.py --runs 3 --json docs/metrics/ttfv.json
    python3 tools/time_to_first_video.py --dry-run        # list the phases and exit

Why engine K: it is the only lane whose first render needs no VO, no cue sheet and no music, so
"first video" stays a pure infrastructure number. The phases (Node deps, scaffold, plan, render,
probe) are timed separately; the total is what a newcomer actually waits.

The target is documented in docs/ttfv.md: on the reference laptop (Quadro M3000M, 4 GB, 2 vCPU)
a first 2-second video must appear in under 180 s with warm Node deps. This script prints
`TARGET met|missed` so a regression is a number, not an opinion.

Nothing is written outside `--keep-dir` (default: a temp directory that is deleted); the JSON
report is the only artifact and is written only when `--json` is given.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

import media_bin  # noqa: E402

TARGET_SECONDS = 180.0
PHASES = ("deps", "scaffold", "plan", "render", "probe")

DIRECTION = {
    "version": 3,
    "status": "directed",
    "decidedBy": "agent",
    "concept": "قياس زمن أول فيديو: مشهد واحد قصير بلا صوت",
    "scenes": [{
        "scene": 1,
        "captionStyle": "pop",
        "captionWhy": "كلمة واحدة تظهر بسرعة أثناء قياس الزمن",
        "textStyles": {"title": "riseword"},
        "textWhy": "ستايل واضح ومقروء للعنوان القصير",
        "fontStyles": {"title": {"family": "Cairo", "weight": 800}},
        "fontWhy": "Cairo 800 هو خط الهوية المعتمد للعناوين",
    }],
}


class Clock:
    """Phase timer that records wall-clock seconds the way the report prints them."""

    def __init__(self) -> None:
        self.spans: dict[str, float] = {}
        self.notes: dict[str, str] = {}

    def phase(self, name: str):
        clock = self

        class _Span:
            def __enter__(self):
                self.started = time.perf_counter()
                return self

            def __exit__(self, exc_type, exc, tb):
                clock.spans[name] = time.perf_counter() - self.started
                return False

        return _Span()


def run(command: list[str], cwd: Path, log: Path) -> int:
    with log.open("a", encoding="utf-8") as handle:
        handle.write("\n$ " + " ".join(command) + "\n")
        handle.flush()
        return subprocess.run(command, cwd=str(cwd), stdout=handle, stderr=subprocess.STDOUT,
                              check=False).returncode


def prepare_deps(project: Path, clock: Clock, log: Path) -> None:
    """A project resolves `playwright-core` from its own node_modules; the toolkit provides it."""
    toolkit = ROOT / "tools" / "toolkit" / "node_modules" / "playwright-core"
    if not toolkit.is_dir():
        code = run(["npm", "ci"], ROOT / "tools" / "toolkit", log)
        if code:
            raise SystemExit("npm ci --prefix tools/toolkit failed; see " + str(log))
        clock.notes["deps"] = "installed with npm ci"
    else:
        clock.notes["deps"] = "toolkit already installed"
    link = project / "node_modules"
    if not link.exists():
        os.symlink(ROOT / "tools" / "toolkit" / "node_modules", link)


def write_plan(project: Path, seconds: float) -> None:
    """The smallest honest plan: one directed scene, no copy, no VO."""
    (project / "plan" / "beats.json").write_text(json.dumps({
        "duration": seconds, "bpm": 100,
        "scenes": [{"id": "example", "start": 0.0, "end": seconds}],
    }, ensure_ascii=False), encoding="utf-8")
    (project / "plan" / "text-direction.json").write_text(
        json.dumps(DIRECTION, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    data = project / "src" / "data.js"
    text = data.read_text(encoding="utf-8")
    start = text.index("export const scenes = [")
    end = text.index("];", start) + 2
    data.write_text(text[:start] + f"export const scenes = [\n  {{ id: 'example', start: 0, end: {seconds} }},\n];"
                    + text[end:], encoding="utf-8")


def probe(media: Path) -> dict:
    ffprobe = media_bin.ffprobe()
    if not ffprobe or not media.is_file():
        return {"ok": False}
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height,nb_frames,duration", "-of", "json", str(media)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return {"ok": False}
    streams = json.loads(result.stdout).get("streams") or [{}]
    info = streams[0]
    return {"ok": True, "width": info.get("width"), "height": info.get("height"),
            "frames": info.get("nb_frames"), "duration_s": float(info.get("duration") or 0)}


def machine() -> dict:
    name = None
    if shutil.which("nvidia-smi"):
        out = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                             capture_output=True, text=True, check=False)
        name = out.stdout.strip().splitlines()[0] if out.returncode == 0 and out.stdout.strip() else None
    return {"cpu_count": os.cpu_count(), "python": platform.python_version(),
            "system": f"{platform.system()} {platform.release()}", "gpu": name}


def one_run(workdir: Path, seconds: float, slug: str) -> dict:
    project = workdir / slug
    log = workdir / "ttfv.log"
    if project.exists():
        # A measurement always starts from nothing: a half-written scaffold would flatter the number.
        shutil.rmtree(project)
    clock = Clock()
    with clock.phase("scaffold"):
        code = run([sys.executable, str(ROOT / "tools" / "new_project.py"), slug, "--engine", "k",
                    "--out", str(project)], workdir, log)
        if code:
            raise SystemExit("scaffold failed; see " + str(log))
    with clock.phase("deps"):
        prepare_deps(project, clock, log)
    with clock.phase("plan"):
        write_plan(project, seconds)
    with clock.phase("render"):
        code = run([sys.executable, str(ROOT / "tools" / "pipeline.py"), str(project), "--steps", "render"],
                   ROOT, log)
    with clock.phase("probe"):
        media = project / "out" / "master.mp4"
        info = probe(media) if code == 0 else {"ok": False}
    total = sum(clock.spans.values())
    return {
        "ok": bool(info.get("ok")) and info.get("duration_s", 0) >= seconds - 0.1,
        "seconds": round(total, 2),
        "phases": {name: round(value, 3) for name, value in clock.spans.items()},
        "notes": clock.notes,
        "media": info,
        "project": str(project),
        "exit_code": code,
        "target_seconds": TARGET_SECONDS,
        "target_met": total <= TARGET_SECONDS,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seconds", type=float, default=2.0, help="length of the first video")
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--slug", default="ttfv", help="project slug used inside the temp dir")
    parser.add_argument("--keep-dir", type=Path, default=None, help="keep the project here (debugging)")
    parser.add_argument("--json", type=Path, default=None, help="write the report (e.g. docs/metrics/ttfv.json)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    if args.dry_run:
        for phase in PHASES:
            print(f"{phase:<10} planned")
        print(f"target: {TARGET_SECONDS:.0f}s · {args.seconds:g}s video · engine K")
        return 0
    if args.seconds <= 0:
        print("time_to_first_video: --seconds must be positive", file=sys.stderr)
        return 2
    if args.runs < 1:
        print("time_to_first_video: --runs must be >= 1", file=sys.stderr)
        return 2
    if not shutil.which("node"):
        print("time_to_first_video: node is required (engine K renders in Chromium)", file=sys.stderr)
        return 2

    runs: list[dict] = []
    for index in range(args.runs):
        if args.keep_dir:
            workdir = args.keep_dir / f"run-{index + 1}"
            workdir.mkdir(parents=True, exist_ok=True)
            result = one_run(workdir, args.seconds, args.slug)
        else:
            with tempfile.TemporaryDirectory(prefix="ttfv-") as scratch:
                result = one_run(Path(scratch), args.seconds, args.slug)
        runs.append(result)
        print(f"run {index + 1}/{args.runs}: {result['seconds']}s "
              f"({'ok' if result['ok'] else 'FAILED — see log'}) · " +
              " · ".join(f"{name} {value:.2f}s" for name, value in result["phases"].items()))

    totals = [run["seconds"] for run in runs]
    report = {
        "target_seconds": TARGET_SECONDS,
        "video_seconds": args.seconds,
        "engine": "k",
        "runs": runs,
        "total_seconds": {"min": min(totals), "median": round(statistics.median(totals), 2),
                          "max": max(totals)},
        "target_met": all(run["target_met"] for run in runs) and all(run["ok"] for run in runs),
        "machine": machine(),
    }
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"report -> {args.json}")
    verdict = "TARGET met" if report["target_met"] else "TARGET missed"
    print(f"{verdict} · min {report['total_seconds']['min']}s · median {report['total_seconds']['median']}s "
          f"· هدف {TARGET_SECONDS:.0f}s")
    return 0 if report["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
