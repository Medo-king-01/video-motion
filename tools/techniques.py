#!/usr/bin/env python3
"""Draw a reel's moves from the measured technique library, instead of reaching for the same four.

An agent left to choose picks the first familiar option: the same fade-up, the same push-in, the same
end card. This draws from `assets/techniques.json` instead — weighted toward proven moves and the
film's energy — and prints the build recipe for each draw. The seed is printed, so a plan is
reproducible and can be written into the project's `plan/techniques.json`.

The library is adapted from cinetic (MIT, (c) 2026 Leonxlnx): its entries were re-measured for a
vertical 1080x1920 Arabic reel and rewritten against **this** studio's primitives (`beat`, `space3d`,
`blur_steps`, `presenter`, `transition`, `sfx`), so every `how` is a build step, not a mood.

    python3 tools/techniques.py --draw --from-plan projects/x/plan/beats.json
    python3 tools/techniques.py --draw --seconds 24 --energy medium --seed 41
    python3 tools/techniques.py --list [--category camera]
    python3 tools/techniques.py --show tr-velocity-handoff-cut
    python3 tools/techniques.py --validate
    python3 tools/techniques.py --markdown docs/techniques.md [--check]

Weights: role (workhorse 3, accent 2, signature 1) x proof (1 + evidence/4, capped at 3) x energy
fit (same 1.0, "any" 0.7, other 0.25; a calm draw never takes a high-energy entry). A plan holds
about one technique per 3.5 s when calm and per 2.5 s otherwise, filled in the format's order of
need, with one signature move (two in a plan of 10 or more).

**Seconds come from the VO**, never from a target length: `--from-plan` reads the duration that
`tools/vo_length.py` measured into `plan/beats.json`.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "assets" / "techniques.json"

ROLES = ("workhorse", "accent", "signature")
ENERGIES = ("calm", "medium", "high", "any")
ROLE_WEIGHT = {"workhorse": 3.0, "accent": 2.0, "signature": 1.0}
ENERGY_FIT = {"any": 0.7}
REQUIRED = ("id", "name", "category", "role", "energy", "primitive", "summary", "how", "timing",
            "use_when", "avoid_when", "evidence")
PRIMITIVES = ("timeline", "type", "grid", "camera", "depth", "transition", "layout", "finish", "blur", "sound")
MIN_PICKS = 4


# ---------------------------------------------------------------- library
def load(path: Path = LIBRARY) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("techniques"), list):
        raise SystemExit(f"{path}: no 'techniques' list")
    return data


def categories(data: dict) -> list[str]:
    return list(data["format"]["reel"]["order"])


def validate(data: dict) -> list[str]:
    """Every problem in the library, as a list of messages (empty means good)."""
    bad: list[str] = []
    entries = data["techniques"]
    seen: set[str] = set()
    for i, e in enumerate(entries):
        where = e.get("id") or f"#{i}"
        for key in REQUIRED:
            if key not in e or e[key] in ("", None, []):
                bad.append(f"{where}: missing '{key}'")
        if e.get("id") in seen:
            bad.append(f"{where}: duplicate id")
        seen.add(e.get("id"))
        if e.get("role") not in ROLES:
            bad.append(f"{where}: role {e.get('role')!r} not in {ROLES}")
        if e.get("energy") not in ENERGIES:
            bad.append(f"{where}: energy {e.get('energy')!r} not in {ENERGIES}")
        if e.get("primitive") not in PRIMITIVES:
            bad.append(f"{where}: primitive {e.get('primitive')!r} not in {PRIMITIVES}")
        if not isinstance(e.get("evidence"), int) or e["evidence"] < 0:
            bad.append(f"{where}: evidence must be a non-negative integer")
        if not isinstance(e.get("bans"), list):
            bad.append(f"{where}: bans must be a list")
    order = categories(data)
    unknown = {e["category"] for e in entries} - set(order)
    if unknown:
        bad.append(f"categories not in format.reel.order: {sorted(unknown)}")
    for cat in order:
        if not any(e["category"] == cat for e in entries):
            bad.append(f"format.reel.order asks for '{cat}' but the library has none")
    return bad


# ---------------------------------------------------------------- draw
def plan_size(fmt: dict, seconds: float, energy: str) -> int:
    """How many techniques a reel of this length draws."""
    per = fmt["seconds_per_pick"].get(energy) or fmt["seconds_per_pick"]["medium"]
    return max(MIN_PICKS, min(len(fmt["order"]), int(round(seconds / per))))


def weight_of(e: dict, energy: str) -> float:
    fit = ENERGY_FIT["any"] if e["energy"] == "any" else (1.0 if e["energy"] == energy else 0.25)
    if energy == "calm" and e["energy"] == "high":
        fit = 0.0                      # a calm reel never draws a slam
    proof = min(1.0 + e["evidence"] / 4.0, 3.0)
    return ROLE_WEIGHT[e["role"]] * proof * fit


def draw(data: dict, seconds: float, energy: str = "calm", seed: int | None = None,
         only: str | None = None, exclude: list[str] | None = None,
         avoid: list[str] | None = None, n: int | None = None) -> dict:
    """A reproducible draw: a seed, a plan size and the picks in the format's order of need."""
    fmt = data["format"]["reel"]
    seed = random.randrange(1, 100_000) if seed is None else seed
    rnd = random.Random(seed)
    skip = set(exclude or []) | set(avoid or [])
    size = n or plan_size(fmt, seconds, energy)
    order = fmt["order"] if not only else [only] * size
    signatures = 2 if size >= 10 else 1
    pool = [e for e in data["techniques"] if e["id"] not in skip]
    used: set[str] = set()
    picks: list[dict] = []
    for cat in order:
        if len(picks) >= size:
            break
        cands = [e for e in pool if e["category"] == cat and e["id"] not in used
                 and weight_of(e, energy) > 0]
        if picks and sum(1 for p in picks if p["role"] == "signature") >= signatures:
            cands = [e for e in cands if e["role"] != "signature"] or cands
        if not cands:
            continue                    # the slot passes to the next category in the order
        weights = [weight_of(e, energy) for e in cands]
        pick = rnd.choices(cands, weights=weights, k=1)[0]
        used.add(pick["id"])
        picks.append(pick)
    return {"seed": seed, "seconds": round(seconds, 2), "energy": energy, "format": "reel",
            "planned": size, "picks": picks}


def faded(entries: list[dict]) -> list[dict]:
    """The picks without the long prose, for a project's plan/techniques.json."""
    keys = ("id", "name", "category", "role", "timing", "primitive", "how", "bans")
    return [{k: e[k] for k in keys} for e in entries]


# ---------------------------------------------------------------- printing
def wrap(text: str, indent: str = "    ") -> str:
    return textwrap.fill(text, width=96, initial_indent=indent, subsequent_indent=indent)


def print_draw(result: dict, target: str | None = None) -> None:
    print(f"draw     seed {result['seed']} · {result['seconds']:g} s · {result['energy']} · "
          f"{len(result['picks'])} of {result['planned']} slots\n")
    for i, e in enumerate(result["picks"], 1):
        print(f"{i:>2}. {e['name']}  [{e['id']}]")
        print(f"    {e['category']} · {e['role']} · {e['primitive']} · {e['timing']}")
        print(wrap(e["how"]))
        print(wrap(f"avoid: {e['avoid_when']}", indent="    × "))
        print()
    if target:
        print(f"write it into {target} as plan/techniques.json, then build only what the concept can carry.")


def to_markdown(data: dict) -> str:
    lines = ["# Technique library", "",
             "Adapted from [cinetic](https://github.com/Leonxlnx/cinetic) (MIT) and re-measured for this studio.",
             "Draw a plan with `python3 tools/techniques.py --draw --from-plan plan/beats.json`; this page is",
             "generated from `assets/techniques.json` (`--markdown docs/techniques.md`), so edit the JSON, not this.", "",
             f"**{len(data['techniques'])} techniques** · seconds per pick: "
             + ", ".join(f"{k} {v:g}s" for k, v in data["format"]["reel"]["seconds_per_pick"].items()), ""]
    for cat in categories(data):
        entries = [e for e in data["techniques"] if e["category"] == cat]
        if not entries:
            continue
        lines += [f"## {cat.replace('_', ' ').title()}", ""]
        for e in entries:
            lines += [f"### `{e['id']}` — {e['name']}", "",
                      f"*{e['role']} · {e['energy']} · {e['primitive']} · evidence {e['evidence']} · "
                      f"{e['timing']}*", "", e["summary"], "", f"**How:** {e['how']}", "",
                      f"**Use when:** {e['use_when']}", "",
                      f"**Avoid when:** {e['avoid_when']}", ""]
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------- cli
def main() -> int:
    ap = argparse.ArgumentParser(description="Draw, inspect and validate the reel technique library.")
    ap.add_argument("--library", type=Path, default=LIBRARY)
    ap.add_argument("--draw", action="store_true", help="draw a whole-film plan")
    ap.add_argument("--seconds", type=float, help="reel length (use --from-plan so it comes from the VO)")
    ap.add_argument("--from-plan", type=Path, metavar="PLAN", help="read the duration from plan/beats.json")
    ap.add_argument("--energy", default="calm", choices=["calm", "medium", "high"])
    ap.add_argument("--seed", type=int)
    ap.add_argument("--n", type=int, help="force the number of picks")
    ap.add_argument("--category", help="draw only from one category")
    ap.add_argument("--exclude", action="append", default=[], help="id to reroll (repeatable)")
    ap.add_argument("--avoid", type=Path, help="a previous draw json whose ids must not repeat")
    ap.add_argument("--json", type=Path, help="write the draw as JSON")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show", metavar="ID")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--markdown", type=Path, metavar="FILE")
    ap.add_argument("--check", action="store_true", help="with --markdown: fail if the file is stale")
    a = ap.parse_args()

    data = load(a.library)

    if a.validate:
        problems = validate(data)
        for p in problems:
            print(f"!! {p}")
        if problems:
            return 1
        print(f"OK {len(data['techniques'])} techniques · {len(categories(data))} slots in the reel order · "
              f"{len({e['category'] for e in data['techniques']})} categories")
        return 0

    if a.show:
        found = [e for e in data["techniques"] if e["id"] == a.show]
        if not found:
            print(f"no technique with id {a.show!r}", file=sys.stderr)
            return 2
        e = found[0]
        for key in REQUIRED:
            print(f"{key:<12} {e[key]}")
        print(f"{'bans':<12} {', '.join(e.get('bans') or []) or '—'}")
        return 0

    if a.list:
        for cat in categories(data):
            entries = [e for e in data["techniques"] if e["category"] == cat
                       and (not a.category or a.category == cat)]
            if not entries:
                continue
            print(f"\n{cat}")
            for e in entries:
                print(f"  {e['id']:<34} {e['role']:<9} {e['energy']:<6} {e['name']}")
        return 0

    if a.markdown:
        text = to_markdown(data)
        if a.check:
            old = a.markdown.read_text(encoding="utf-8") if a.markdown.is_file() else ""
            if old != text:
                print(f"!! {a.markdown} is stale — regenerate: python3 tools/techniques.py "
                      f"--markdown {a.markdown}")
                return 1
            print(f"OK {a.markdown} matches the library")
            return 0
        a.markdown.parent.mkdir(parents=True, exist_ok=True)
        a.markdown.write_text(text, encoding="utf-8")
        print(f"wrote {a.markdown}")
        return 0

    # --draw is the default once a length is known
    seconds = a.seconds
    if a.from_plan:
        plan = json.loads(a.from_plan.read_text(encoding="utf-8"))
        seconds = plan.get("duration")
        if not seconds:
            print(f"{a.from_plan}: duration is null — measure the VO first: "
                  f"python3 tools/vo_length.py out/vo.wav --json {a.from_plan}", file=sys.stderr)
            return 2
    if seconds is None:
        ap.error("give --seconds or --from-plan (the reel's length comes from the VO)")

    avoid: list[str] = []
    if a.avoid and a.avoid.is_file():
        avoid = [p["id"] for p in json.loads(a.avoid.read_text(encoding="utf-8")).get("picks", [])]

    result = draw(data, float(seconds), a.energy, a.seed, a.category, a.exclude, avoid, a.n)
    if not result["picks"]:
        print("nothing fits those filters", file=sys.stderr)
        return 1
    print_draw(result, str(a.json) if a.json else None)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({**result, "picks": faded(result["picks"]),
                                      "library": str(a.library.relative_to(ROOT))
                                      if a.library.is_relative_to(ROOT) else str(a.library)},
                                     indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
