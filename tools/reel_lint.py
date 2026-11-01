#!/usr/bin/env python3
"""Lint a reel plan before anything is rendered: the numbers the eye judges, measured in code.

The rules are the measured norms from the cinetic study (MIT, (c) 2026 Leonxlnx), re-scaled for a
1080x1920 / 30 fps Arabic reel and trimmed to what this studio actually allows. They are **not** a
length rule: nothing here has an opinion about how long the reel is — the VO decides that
(`tools/vo_length.py`). They only say whether the plan is readable, on the grid and free of the
tells that make a film look generated.

    python3 tools/reel_lint.py projects/<slug>                 # check the project's plan
    python3 tools/reel_lint.py projects/<slug> --strict        # warnings are failures too
    python3 tools/reel_lint.py projects/<slug> --json out/qa/lint.json
    python3 tools/reel_lint.py projects/<slug> --scan-code     # also scan the scene code for banned looks

Reads (all optional except `plan/beats.json`):

- `plan/beats.json` — the timeline `vo_length.py` derived from the VO: `duration`, `scenes[]`
  (`start`, `end`, optional `events: [{"t": s, "what": "…"}]`, `theme`).
- `plan/copy.json` — what appears on screen: `{"pace": "calm"|"crisp", "bpm": 100,
  "copy": [{"scene": 1, "text": "…", "start": 0.8, "end": 2.9, "mode": "build"|"replace"}]}`.
  Optional `bpm` alone is enough for the grid check.
- `plan/techniques.json` — the draw from `tools/techniques.py` (variety and signature budget eat it).

Exit 0 clean · 1 errors (or warnings with `--strict`) · 2 nothing to check.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ---- measured norms (30 fps, 9:16) ------------------------------------------------------------
WORDS_PER_FRAGMENT = {"calm": 4, "crisp": 5}
VISIBLE_AT_ONCE = {"calm": 8, "crisp": 10}
REPLACE_VISIBLE = 5                  # a line that replaces itself carries fewer words
DWELL_PER_WORD = 0.40                # median 0.4 s/word, range 0.30-0.55
DWELL_FLOOR = 0.50                   # nothing under half a second reads
COPY_RATE = (0.40, 1.70)             # on-screen words per second
COPY_COVERAGE = {"calm": 0.65, "crisp": 0.80}
FREE_STRETCH = 1.50                  # text-free picture, at least once per 10 s
WINDOW = 10.0
MAX_PICTURE_GAP = 4.0                # 5-10 s with nothing changing reads as a sag
GRID_TOL = 0.12                      # a cut further than this from the grid drifts
SHORT_SHOT = 0.45                    # no copy under this
TINY_SHOT = 0.27
LONG_SCENE = 2.20                    # past this the picture itself must change
UI_MIN = 1.20                        # a UI insert needs time for its interaction to read
FIRST_CHANGE = 0.43
SIGNATURE_BUDGET = 2

# Words and looks this studio never puts on screen.
BANNED_WORDS = ("introducing", "lorem ipsum", "نقدم لكم", "اسم السلسلة", "لوجو")
BANNED_CODE = {
    "sparkle": "sparkles standing in for an idea",
    "confetti": "confetti",
    "particle": "particle bursts",
    "lensflare": "lens flare",
    "lens_flare": "lens flare",
    "rgbsplit": "RGB split",
    "rgb_split": "RGB split",
    "crossfade": "crossfade (hard cuts only)",
    "shake": "camera shake",
}
ALLOW = re.compile(r"#\s*lint:\s*allow\s+([\w, -]+)")


class Report:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, level: str, code: str, msg: str) -> None:
        self.items.append({"level": level, "code": code, "msg": msg})

    def error(self, code: str, msg: str) -> None:
        self.add("error", code, msg)

    def warn(self, code: str, msg: str) -> None:
        self.add("warn", code, msg)

    def ok(self, code: str, msg: str) -> None:
        self.add("ok", code, msg)

    @property
    def errors(self) -> list[dict]:
        return [i for i in self.items if i["level"] == "error"]

    @property
    def warns(self) -> list[dict]:
        return [i for i in self.items if i["level"] == "warn"]


# ---- helpers ---------------------------------------------------------------------------------
def words(text: str) -> list[str]:
    """Real words only: punctuation-only tokens don't count and don't get read."""
    return [w for w in str(text).split() if re.search(r"\w", w)]


def grid_step(bpm: float, div: float) -> float:
    return 60.0 / bpm / div


def off_grid(t: float, bpm: float, div: float = 2.0) -> float:
    step = grid_step(bpm, div)
    return abs(t - round(t / step) * step)


def union(intervals: list[tuple[float, float]]) -> list[tuple[float, float]]:
    out: list[tuple[float, float]] = []
    for s, e in sorted(intervals):
        if out and s <= out[-1][1] + 1e-9:
            out[-1] = (out[-1][0], max(out[-1][1], e))
        else:
            out.append((s, e))
    return out


def longest_free(spans: list[tuple[float, float]], a: float, b: float) -> float:
    """Longest stretch without copy inside [a, b]."""
    best, cursor = 0.0, a
    for s, e in spans:
        if e <= a or s >= b:
            continue
        if s > cursor:
            best = max(best, min(s, b) - cursor)
        cursor = max(cursor, e)
    return max(best, b - min(cursor, b))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


# ---- structure -------------------------------------------------------------------------------
def lint_timeline(rep: Report, plan: dict, bpm: float, tol: float) -> list[tuple[float, float]]:
    """Checks on plan/beats.json; returns the copy spans it can infer (scene-level)."""
    dur = plan.get("duration")
    scenes = plan.get("scenes") or []
    if not dur:
        rep.error("S01", "plan/beats.json has no duration — measure the VO first: "
                         "python3 tools/vo_length.py out/vo.wav --json plan/beats.json")
        return []
    rep.ok("S01", f"timeline {dur:g} s, {len(scenes)} scenes (length = the VO)")
    if not scenes:
        rep.error("S02", "plan/beats.json has a duration but no scenes")
        return []
    if abs(scenes[0]["start"]) > 0.05:
        rep.error("S02", f"the first scene starts at {scenes[0]['start']:g} s, not 0")
    if abs(scenes[-1]["end"] - dur) > 0.15:
        rep.error("S02", f"the last scene ends at {scenes[-1]['end']:.2f} s but the VO is {dur:.2f} s")
    for i in range(1, len(scenes)):
        if scenes[i]["start"] < scenes[i - 1]["end"] - 1e-6:
            rep.error("S02", f"scene {i + 1} starts before scene {i} ends")

    for s in scenes:
        length = s["end"] - s["start"]
        n_events = len(s.get("events") or [])
        if length < TINY_SHOT:
            rep.warn("S03", f"scene {s['index']}: {length:.2f} s — too short to register "
                            f"(0.27 s is the floor, and only as punctuation)")
        elif length > LONG_SCENE and n_events < 1:
            rep.warn("S04", f"scene {s['index']}: {length:.2f} s with no picture event — "
                            f"change the picture about every second, not just at the cut "
                            f"(add events[] or a fragment mid-scene)")
    for s in scenes:
        if not s.get("ui"):
            continue
        length = s["end"] - s["start"]
        if not s.get("events"):
            rep.warn("U01", f"scene {s['index']}: flagged ui but no interaction — a screen that "
                            f"never changes is a mock, not a scene (add events[] with the tap)")
        if length < UI_MIN:
            rep.warn("U01", f"scene {s['index']}: ui insert of {length:.2f} s — an interface needs "
                            f"{UI_MIN:.1f} s before the change can be read")

    if bpm:
        cuts = sorted({round(s["start"], 3) for s in scenes[1:]})
        for edge in cuts:
            d = off_grid(edge, bpm)
            if d > tol:
                rep.warn("S05", f"cut at {edge:.2f} s is {d * 1000:.0f} ms off the {bpm:g} BPM grid "
                                f"— hero cuts land within ±1 frame")
    return [(s["start"], s["end"]) for s in scenes]


# ---- copy ------------------------------------------------------------------------------------
def lint_copy(rep: Report, copy: dict, dur: float, pace: str, bpm: float, scenes: list[dict]) -> None:
    items = copy.get("copy") or []
    if not items:
        state = "plan/copy.json lists no fragments yet" if copy else "no plan/copy.json"
        rep.warn("C00", f"{state} — nothing checks what appears on screen "
                        f"(words per fragment, dwell, coverage)")
        return
    pace = copy.get("pace", pace)
    limit = WORDS_PER_FRAGMENT[pace]
    visible_limit = VISIBLE_AT_ONCE[pace]
    known = {s["index"] for s in scenes}

    pairs: list[tuple[dict, tuple[float, float]]] = []
    for c in items:
        text = c.get("text", "")
        ws = words(text)
        start, end = float(c.get("start", 0.0)), float(c.get("end", 0.0))
        where = f"scene {c.get('scene', '?')} “{text[:32]}”"
        if c.get("scene") and c["scene"] not in known:
            rep.error("C10", f"{where}: scene {c['scene']} is not in plan/beats.json")
        if not ws:
            rep.error("C01", f"{where}: no words")
            continue
        if len(ws) > limit:
            rep.error("C01", f"{where}: {len(ws)} words in one fragment (max {limit} when {pace}) — "
                             f"split it, copy arrives in pieces")
        if len(ws) > 6 and re.search(r"[.!؟?]$", text.strip()):
            rep.error("C08", f"{where}: a whole sentence arrives at once — chain it in fragments")
        for bad in BANNED_WORDS:
            if bad in text.lower():
                rep.error("C07", f"{where}: “{bad}” is on the banned-words list")
        if end <= start:
            rep.error("C09", f"{where}: end {end:g} s is not after start {start:g} s")
            continue
        need = max(DWELL_FLOOR, DWELL_PER_WORD * len(ws))
        shown = end - start
        if shown < need * 0.75:
            rep.error("C03", f"{where}: on screen {shown:.2f} s for {len(ws)} words — "
                             f"needs {need:.2f} s (0.4 s per word, floor 0.5 s)")
        elif shown < need:
            rep.warn("C03", f"{where}: {shown:.2f} s is under the {need:.2f} s read pace")
        if c.get("scene") and shown < SHORT_SHOT and len(ws) > 2:
            rep.warn("S03", f"{where}: {shown:.2f} s carries no copy — under 0.45 s the eye "
                            f"registers punctuation, not words")
        if bpm:
            d = off_grid(start, bpm)
            if d > GRID_TOL:
                rep.warn("C11", f"{where}: arrives {d * 1000:.0f} ms off the {bpm:g} BPM grid")
        pairs.append((c, (start, end)))

    spans = [span for _, span in pairs]
    # visible at once, sampled on every fragment edge
    edges = sorted({round(t, 3) for _, (s, e) in pairs for t in (s, e)})
    worst = (0, 0.0)
    for t in edges:
        live = [c for c, (s, e) in pairs if s <= t < e]
        n = sum(len(words(c.get("text", ""))) for c in live)
        lim = REPLACE_VISIBLE if any(c.get("mode") == "replace" for c in live) else visible_limit
        if n > worst[0]:
            worst = (n, t)
        if n > lim:
            rep.error("C02", f"{n} words on screen at {t:.2f} s (max {lim}) — remove the weakest one")
            break
    if worst[0] and not any(i["code"] == "C02" and i["level"] == "error" for i in rep.items):
        rep.ok("C02", f"peak {worst[0]} words on screen at {worst[1]:.2f} s")

    total_words = sum(len(words(c.get("text", ""))) for c in items)
    rate = total_words / dur if dur else 0.0
    lo, hi = COPY_RATE
    if not lo <= rate <= hi:
        rep.warn("C04", f"{rate:.2f} on-screen words per second — the read range is "
                        f"{lo:g}–{hi:g}/s")
    else:
        rep.ok("C04", f"{total_words} words, {rate:.2f}/s")

    merged = union(spans)
    covered = sum(e - s for s, e in merged if e > s)
    share = covered / dur if dur else 0.0
    limit_share = COPY_COVERAGE[pace]
    if share > limit_share:
        rep.warn("C05", f"copy covers {share:.0%} of the reel (max {limit_share:.0%}) — "
                        f"leave the picture alone to breathe")
    else:
        rep.ok("C05", f"copy covers {share:.0%}")

    worst_free, worst_at = (99.0, 0.0)
    if dur >= WINDOW + 1.0:
        t = 0.0
        while t + WINDOW <= dur + 1e-9:
            free = longest_free(merged, t, t + WINDOW)
            if free < worst_free:
                worst_free, worst_at = free, t
            t += 1.0
    if worst_free < FREE_STRETCH:
        rep.warn("C06", f"only {worst_free:.2f} s without copy in the window at "
                        f"{worst_at:.1f} s — every 10 s wants 1.5 s of pure picture")
    else:
        rep.ok("C06", f"{worst_free:.2f} s of text-free picture in the tightest 10 s window")


# ---- moves -----------------------------------------------------------------------------------
def lint_moves(rep: Report, draw: dict) -> None:
    picks = draw.get("picks") or []
    if not picks:
        rep.warn("M00", "no plan/techniques.json — draw the moves: "
                        "python3 tools/techniques.py --draw --from-plan plan/beats.json")
        return
    sigs = sum(1 for p in picks if p.get("role") == "signature")
    if sigs > SIGNATURE_BUDGET:
        rep.warn("M02", f"{sigs} signature moves — one is a statement, {SIGNATURE_BUDGET} is a limit")
    run, last = 1, None
    for p in picks:
        cat = p.get("category")
        if cat == last:
            run += 1
            if run > 2:
                rep.warn("M01", f"three moves in a row from '{cat}' — reroll one "
                                f"(python3 tools/techniques.py --draw --exclude {p['id']})")
                break
        else:
            run, last = 1, cat
    rep.ok("M01", f"{len(picks)} moves drawn · seed {draw.get('seed', '?')}")


# ---- optional code scan ----------------------------------------------------------------------
def lint_code(rep: Report, project: Path) -> None:
    files = [p for p in list(project.glob("*.py")) + list(project.glob("src/**/*.js"))
             if p.is_file() and p.name not in ("run_all.py", "chunk.py")]
    if not files:
        return
    hits = 0
    for f in files:
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            allowed = ALLOW.search(line)
            allow = {t.strip().lower() for t in allowed.group(1).split(",")} if allowed else set()
            low = line.lower()
            for token, why in BANNED_CODE.items():
                if token in low and token not in allow:
                    rep.warn("K01", f"{f.relative_to(project)}:{n}: {why} ({token})")
                    hits += 1
    if not hits:
        rep.ok("K01", f"no banned looks in {len(files)} scene file(s)")


# ---- cli -------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a reel plan against the measured craft norms.")
    ap.add_argument("project", type=Path)
    ap.add_argument("--pace", default=None, choices=["calm", "crisp"], help="default calm")
    ap.add_argument("--bpm", type=float, default=None, help="tempo; defaults to plan/copy.json")
    ap.add_argument("--tol", type=float, default=GRID_TOL)
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    ap.add_argument("--scan-code", action="store_true")
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()

    plan_p = a.project / "plan" / "beats.json"
    if not plan_p.is_file():
        print(f"no plan/beats.json in {a.project} — measure the VO first "
              f"(python3 tools/vo_length.py out/vo.wav --json {plan_p})", file=sys.stderr)
        return 2
    plan = load(plan_p)
    copy = load(a.project / "plan" / "copy.json")
    draw = load(a.project / "plan" / "techniques.json")
    pace = a.pace or copy.get("pace") or "calm"
    bpm = a.bpm if a.bpm is not None else float(copy.get("bpm") or draw.get("bpm") or 0)

    rep = Report()
    lint_timeline(rep, plan, bpm, a.tol)
    dur = float(plan.get("duration") or 0)
    scenes = plan.get("scenes") or []
    if dur and scenes:
        lint_copy(rep, copy, dur, pace, bpm, scenes)
    lint_moves(rep, draw)
    if a.scan_code:
        lint_code(rep, a.project)

    icon = {"error": "!!", "warn": " ?", "ok": "  "}
    for item in rep.items:
        if item["level"] != "ok":
            print(f"{icon[item['level']]} {item['code']}  {item['msg']}")
    for item in rep.items:
        if item["level"] == "ok":
            print(f"{icon['ok']} {item['code']}  {item['msg']}")

    failed = bool(rep.errors) or (a.strict and bool(rep.warns))
    summary = (f"{len(rep.errors)} error(s), {len(rep.warns)} warning(s) · "
               f"{pace} pace · {dur:g} s · {bpm:g} BPM" if bpm else
               f"{len(rep.errors)} error(s), {len(rep.warns)} warning(s) · {pace} pace · {dur:g} s")
    print(f"\n{'FAIL' if failed else 'PASS'}  {a.project.name} — {summary}")
    if failed and not a.strict:
        print("fix the errors first; warnings are the difference between good and directed.")

    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"project": str(a.project), "pace": pace, "bpm": bpm,
                                      "duration": dur, "failed": failed, "items": rep.items},
                                     indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
