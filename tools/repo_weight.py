#!/usr/bin/env python3
"""Tracked-repository weight: report it, and stop it from growing by accident.

The review (N4) found 152 MB of binary assets behind a 112 MB `.git`, with `poses/source` at ~34 MB
of near-duplicate PNGs. There is deliberately no Git LFS here — adding a filter changes every clone
and every CI job, and moving history is an owner decision, not a refactor. What was missing is
cheaper and more useful: nothing *noticed* when the repository got heavier.

Two rules, both honest about what they can and cannot do:

1. **Ratchet** — total tracked weight may not exceed the recorded baseline by more than
   `ALLOWANCE_MB`. Small additions are fine; a second silent 30 MB folder is not.
2. **Named heavy files** — any tracked file of `HEAVY_MB` or more must appear in the baseline's
   `heavy` map. A new heavy asset therefore requires a deliberate `--update`, which prints exactly
   what was added so the decision is visible in the diff.

`--update` also records the baseline in the JSON, so `git diff` shows the weight change next to the
code change that caused it.

Usage:
  python3 tools/repo_weight.py            # human report
  python3 tools/repo_weight.py --check    # exit 1 if a rule is broken (CI)
  python3 tools/repo_weight.py --update   # record the current state as the baseline
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "repo-weight-baseline.json"
ALLOWANCE_MB = 2.0
HEAVY_MB = 3.0

CATEGORIES = (
    ("fonts", (".ttf", ".otf", ".woff", ".woff2")),
    ("images", (".png", ".jpg", ".jpeg", ".webp", ".gif", ".psd")),
    ("audio", (".mp3", ".wav", ".m4a", ".flac", ".aiff", ".ogg")),
    ("video", (".mp4", ".mov", ".webm")),
    ("data", (".json", ".csv", ".bin", ".npy", ".npz", ".pkl")),
)
MB = 1024 * 1024


def category_of(path: str) -> str:
    suffix = Path(path).suffix.lower()
    for name, suffixes in CATEGORIES:
        if suffix in suffixes:
            return name
    return "text"


def tracked_files(root: Path = ROOT) -> list[str]:
    """Paths Git tracks, NUL-separated so Unicode filenames survive."""
    result = subprocess.run(["git", "ls-files", "-z"], cwd=str(root), capture_output=True, check=True)
    return [name for name in result.stdout.decode("utf-8").split("\0") if name]


def inventory(root: Path = ROOT) -> dict:
    """Per-file byte sizes plus totals per category — the raw measurement, no policy."""
    sizes: dict[str, int] = {}
    for name in tracked_files(root):
        path = root / name
        try:
            if path.is_file():
                sizes[name] = path.stat().st_size
        except OSError:
            continue  # a broken symlink is not weight
    totals: dict[str, int] = {name: 0 for name, _ in CATEGORIES}
    totals["text"] = 0
    counts: dict[str, int] = {key: 0 for key in totals}
    for name, size in sizes.items():
        key = category_of(name)
        totals[key] += size
        counts[key] += 1
    return {"files": sizes, "totals": totals, "counts": counts,
            "total": sum(sizes.values()), "tracked": len(sizes)}


def snapshot(root: Path = ROOT) -> dict:
    """The baseline document: totals per category and every file that needs a deliberate decision."""
    data = inventory(root)
    return {
        "version": 1,
        "allowance_mb": ALLOWANCE_MB,
        "heavy_mb": HEAVY_MB,
        "total_mb": round(data["total"] / MB, 2),
        "tracked_files": data["tracked"],
        "categories_mb": {key: round(value / MB, 2) for key, value in data["totals"].items()},
        "categories_files": dict(data["counts"]),
        "heavy": {name: round(size / MB, 2) for name, size in data["files"].items() if size >= HEAVY_MB * MB},
    }


def load_baseline(path: Path = BASELINE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def violations(current: dict, baseline: dict) -> list[str]:
    """Both rules as sentences a human can act on — no silent pass, no vague failure."""
    problems: list[str] = []
    growth = current["total_mb"] - float(baseline["total_mb"])
    allowance = float(baseline.get("allowance_mb", ALLOWANCE_MB))
    if growth > allowance:
        problems.append(
            f"tracked weight grew by {growth:+.2f} MB (allowed {allowance:.1f} MB over the "
            f"{baseline['total_mb']:.2f} MB baseline) — trim it, or record the decision with "
            "--update and say why in the commit message"
        )
    known = set(baseline.get("heavy", {}))
    for name, size in sorted(current["heavy"].items(), key=lambda item: -item[1]):
        if name not in known:
            problems.append(
                f"{name} is a new {size:.1f} MB tracked file (threshold {HEAVY_MB:.0f} MB) — "
                "keep it out of Git, or record it deliberately with --update"
            )
    return problems


def report(current: dict, baseline: dict | None) -> str:
    lines = [f"tracked weight: {current['total_mb']:.1f} MB across {current['tracked_files']} files"]
    for name, size in sorted(current["categories_mb"].items(), key=lambda item: -item[1]):
        if size:
            lines.append(f"  {name:<7} {size:8.1f} MB  ({current['categories_files'].get(name, 0)} files)")
    for name, size in sorted(current["heavy"].items(), key=lambda item: -item[1])[:5]:
        lines.append(f"  heavy   {size:8.1f} MB  {name}")
    if baseline:
        lines.append(f"baseline: {baseline['total_mb']:.1f} MB "
                     f"({current['total_mb'] - baseline['total_mb']:+.2f} MB)")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 when a rule is broken")
    parser.add_argument("--update", action="store_true", help="record the current state as the baseline")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository to measure (default: this one)")
    parser.add_argument("--baseline", type=Path, default=None, help="baseline file (default: docs/repo-weight-baseline.json)")
    args = parser.parse_args(argv)
    baseline_path = args.baseline or (args.root / "docs" / "repo-weight-baseline.json")
    current = snapshot(args.root)

    if args.update:
        old = load_baseline(baseline_path) if baseline_path.is_file() else None
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(current, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(report(current, old))
        delta = current["total_mb"] - (old["total_mb"] if old else 0.0)
        print(f"baseline written to {baseline_path} ({delta:+.2f} MB)")
        return 0

    baseline = load_baseline(baseline_path) if baseline_path.is_file() else None
    print(report(current, baseline))
    if baseline is None:
        if args.check:
            print("no baseline recorded — run: python3 tools/repo_weight.py --update", file=sys.stderr)
            return 1
        return 0
    problems = violations(current, baseline)
    if problems:
        for problem in problems:
            print(f"WEIGHT: {problem}", file=sys.stderr)
        return 1 if args.check else 0
    if args.check:
        print("OK weight within budget")
    return 0


if __name__ == "__main__":
    sys.exit(main())
