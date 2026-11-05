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
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "medo-motion" / "templates" / "procedural-reels"))
import contrast  # noqa: E402
import machine_explainer as me  # noqa: E402
import one_take  # noqa: E402
import slide_wall  # noqa: E402
import stage as stage_mod  # noqa: E402
import text_direction as td  # noqa: E402
import visual_direction as vd  # noqa: E402

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

# Words and looks this studio never puts on screen on its own. Placeholders only: a name,
# title, episode number or logo is the USER's decision (AGENTS.md rule 1) — when he asks for
# one, the words he gave are his copy and C07 does not apply to them. The plan records that
# with `"approvedByUser": true` on the fragment.
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
RAW_TEXT = re.compile(r"\b(?:fillText|strokeText|text_sprite|txt)\s*\(")
RAW_ALLOW = re.compile(r"(?:#|//)\s*lint:\s*allow\s+([\w, -]+)")


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
        prev_end = scenes[i - 1]["end"]
        if scenes[i]["start"] < prev_end - 1e-6:
            rep.error("S02", f"scene {i + 1} starts before scene {i} ends (overlap)")
        elif scenes[i]["start"] > prev_end + 1e-6:
            rep.error("S02", f"gap of {scenes[i]['start'] - prev_end:.2f} s between scene {i} "
                             f"(ends {prev_end:g} s) and scene {i + 1} (starts {scenes[i]['start']:g} s) "
                             f"— scenes must be contiguous: no gaps, no overlaps")

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


def lint_first_frame(rep: Report, plan: dict, copy: dict) -> None:
    """S06 — frame 0 is the poster: social players freeze it, so it must not be an empty ground.

    A reel that fades a title in *from nothing* starts on its own background — and a reel that
    opens on a presenter model posed but unlit or off-frame has the same problem. The check is
    deliberately structural, not a claim about pixels: something must be already on screen at
    `t = 0`, either a declared picture event at 0 or a copy fragment that starts at 0.
    """
    scenes = plan.get("scenes") or []
    if not scenes:
        return
    first = scenes[0]
    if abs(first.get("start", 0.0)) > 0.05:
        return                                     # S02 already reports a timeline that does not start at 0
    at_zero = [e for e in (first.get("events") or []) if abs(float(e.get("t", -1))) <= 1e-6]
    copy_at_zero = [c for c in (copy.get("copy") or [])
                    if c.get("scene") == first.get("index") and abs(float(c.get("start", -1))) <= 1e-6]
    if at_zero or copy_at_zero:
        detail = at_zero[0].get("what") if at_zero else f"“{copy_at_zero[0].get('text', '')}”"
        rep.ok("S06", f"frame 0 already carries the picture ({detail})")
        return
    rep.warn("S06", f"frame 0 is an empty ground — social players show it as the thumbnail; put the "
                    f"title or the key image on screen at 0 s instead of entering from nothing "
                    f"(a copy fragment at 0 or events[0].t = 0 in scene {first.get('index')})")


# ---- copy ------------------------------------------------------------------------------------
def _fragment_errors(rep: Report, fragment: dict, pace: str, known: set[int]) -> tuple[dict, list[str]] | None:
    """Checks that need one fragment on its own. Returns (fragment, words) or None when unusable."""
    text = fragment.get("text", "")
    words_in_text = words(text)
    start, end = float(fragment.get("start", 0.0)), float(fragment.get("end", 0.0))
    where = f"scene {fragment.get('scene', '?')} “{text[:32]}”"
    scene = fragment.get("scene")
    if scene and scene not in known:
        rep.error("C10", f"{where}: scene {scene} is not in plan/beats.json")
    if not words_in_text:
        rep.error("C01", f"{where}: no words")
        return None
    limit = WORDS_PER_FRAGMENT[pace]
    if len(words_in_text) > limit:
        rep.error("C01", f"{where}: {len(words_in_text)} words in one fragment (max {limit} when {pace}) — "
                         f"split it, copy arrives in pieces")
    if len(words_in_text) > 6 and re.search(r"[.!؟?]$", text.strip()):
        rep.error("C08", f"{where}: a whole sentence arrives at once — chain it in fragments")
    # The user owns the name/title/episode slot: words he supplied are not this studio's
    # defaults, so C07 only guards copy the plan claims is the studio's own choice.
    banned = () if fragment.get("approvedByUser") is True else BANNED_WORDS
    for phrase in banned:
        if phrase in text.lower():
            rep.error("C07", f"{where}: “{phrase}” is on the banned-words list")
    if end <= start:
        rep.error("C09", f"{where}: end {end:g} s is not after start {start:g} s")
        return None
    return {"fragment": fragment, "where": where, "start": start, "end": end, "words": words_in_text}, words_in_text


def _fragment_timing_warnings(rep: Report, item: dict, bpm: float) -> None:
    """Dwell, short-shot and grid checks: a fragment that cannot be read in time."""
    shown = item["end"] - item["start"]
    count = len(item["words"])
    needed = max(DWELL_FLOOR, DWELL_PER_WORD * count)
    where = item["where"]
    if shown < needed * 0.75:
        rep.error("C03", f"{where}: on screen {shown:.2f} s for {count} words — "
                         f"needs {needed:.2f} s ({DWELL_PER_WORD:g} s per word, floor {DWELL_FLOOR:g} s)")
    elif shown < needed:
        rep.warn("C03", f"{where}: {shown:.2f} s is under the {needed:.2f} s read pace")
    if item["fragment"].get("scene") and shown < SHORT_SHOT and count > 2:
        rep.warn("S03", f"{where}: {count} words in {shown:.2f} s — under {SHORT_SHOT} s the eye "
                        f"registers punctuation, not words")
    if bpm:
        drift = off_grid(item["start"], bpm)
        if drift > GRID_TOL:
            rep.warn("C11", f"{where}: arrives {drift * 1000:.0f} ms off the {bpm:g} BPM grid")


def _visible_words_worst_case(items: list[dict], pace: str) -> tuple[int, float]:
    """Peak number of words on screen and when, sampled on every fragment edge."""
    edges = sorted({round(t, 3) for item in items for t in (item["start"], item["end"])})
    worst = (0, 0.0)
    for moment in edges:
        live = [i for i in items if i["start"] <= moment < i["end"]]
        count = sum(len(i["words"]) for i in live)
        if count > worst[0]:
            worst = (count, moment)
        limit = REPLACE_VISIBLE if any(i["fragment"].get("mode") == "replace" for i in live) else VISIBLE_AT_ONCE[pace]
        if count > limit:
            return count, moment
    return worst


def _merge_spans(spans: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _longest_gap(spans: list[tuple[float, float]], start: float, end: float) -> float:
    """Longest stretch without copy inside [start, end]."""
    cursor, best = start, 0.0
    for span_start, span_end in spans:
        if span_end <= cursor or span_start >= end:
            continue
        best = max(best, max(0.0, span_start - cursor))
        cursor = max(cursor, span_end)
    return max(best, end - cursor)


def lint_copy(rep: Report, copy: dict, dur: float, pace: str, bpm: float, scenes: list[dict]) -> None:
    """Readability gates for what appears on screen: words, dwell, density, coverage."""
    fragments = copy.get("copy") or []
    if not fragments:
        state = "plan/copy.json lists no fragments yet" if copy else "no plan/copy.json"
        rep.warn("C00", f"{state} — nothing checks what appears on screen "
                        f"(words per fragment, dwell, coverage)")
        return
    pace = copy.get("pace", pace)
    known = {scene["index"] for scene in scenes}

    measured: list[dict] = []
    for fragment in fragments:                      # document order, so the report reads in order
        checked = _fragment_errors(rep, fragment, pace, known)
        if not checked:
            continue
        _fragment_timing_warnings(rep, checked[0], bpm)
        measured.append(checked[0])

    count, moment = _visible_words_worst_case(measured, pace)
    crowded = any(item["fragment"].get("mode") == "replace" for item in measured)
    visible_limit = REPLACE_VISIBLE if crowded else VISIBLE_AT_ONCE[pace]
    if count > visible_limit:
        rep.error("C02", f"{count} words on screen at {moment:.2f} s (max {visible_limit}) — remove the weakest one")
    elif count:
        rep.ok("C02", f"peak {count} words on screen at {moment:.2f} s")

    total_words = sum(len(item["words"]) for item in measured)
    rate = total_words / dur if dur else 0.0
    low, high = COPY_RATE
    if not low <= rate <= high:
        rep.warn("C04", f"{rate:.2f} on-screen words per second — the read range is {low:g}–{high:g}/s")
    else:
        rep.ok("C04", f"{total_words} words, {rate:.2f}/s")

    merged = _merge_spans([(item["start"], item["end"]) for item in measured])
    covered = sum(end - start for start, end in merged if end > start)
    share = covered / dur if dur else 0.0
    limit_share = COPY_COVERAGE[pace]
    if share > limit_share:
        rep.warn("C05", f"copy covers {share:.0%} of the reel (max {limit_share:.0%}) — "
                        f"leave the picture alone to breathe")
    else:
        rep.ok("C05", f"copy covers {share:.0%}")

    worst_free, worst_at = 99.0, 0.0
    if dur >= WINDOW + 1.0:
        moment = 0.0
        while moment + WINDOW <= dur + 1e-9:
            free = _longest_gap(merged, moment, moment + WINDOW)
            if free < worst_free:
                worst_free, worst_at = free, moment
            moment += 1.0
    if worst_free < FREE_STRETCH:
        rep.warn("C06", f"only {worst_free:.2f} s without copy in the window at "
                        f"{worst_at:.1f} s — every 10 s wants {FREE_STRETCH:g} s of pure picture")
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


# ---- text direction (agent-chosen styles, no default) ---------------------------------------
def lint_text_direction(rep: Report, project: Path, beats: dict, copy: dict) -> None:
    direction = td.load(project)
    if not direction:
        rep.error("T00", "no plan/text-direction.json — the agent must choose caption/text styles per scene: "
                         "python3 tools/text_direction.py <project> --init")
        return
    fonts = td.load_fonts(project)
    report = td.validate(direction, beats, fonts=fonts or None)
    for e in report["errors"]:
        rep.error("T01", e)
    for w in report["warnings"]:
        rep.warn("T02", w)
    # EVERY on-screen text fragment (not just captions) must resolve to an explicit motion + font.
    for c in copy.get("copy") or []:
        label = c.get("id") or f"copy[{c.get('scene')}]"
        role = c.get("role")
        if role not in td.TEXT_ROLES:
            rep.error("T03", f"{label}: every on-screen text fragment needs a known role (got {role!r})")
            continue
        try:
            td.text_style_for(direction, c.get("scene"), role, c.get("id"))
        except ValueError as e:
            rep.error("T03", f"{label}: {e}")
        if fonts:
            try:
                font = td.font_for(direction, c.get("scene"), role, c.get("id"))
            except ValueError as e:
                rep.error("T05", f"{label}: {e}")
                continue
            meta = fonts.get(font["family"])
            if not meta or font["weight"] not in {w["weight"] for w in meta.get("weights", [])}:
                rep.error("T05", f"{label}: font {font['family']} {font['weight']} is not in the manifest")
            elif td.has_arabic(c.get("text")) and meta.get("script") != "arabic":
                rep.error("T05", f"{label}: Arabic text needs an Arabic-capable family (got {font['family']})")
    if not report["errors"]:
        rep.ok("T01", f"text direction: {len(direction.get('scenes') or [])} scenes directed by {direction.get('decidedBy')}")


def lint_contrast(rep: Report, copy: dict, plan: dict) -> None:
    """T06 — every on-screen fragment is readable against the ground it is actually drawn on.

    A fragment may name its own `color` (a brand token) and `size` (stage px) and the scene may
    name its `theme` (`dark`/`light`, the same word the backgrounds use). Nothing here guesses:
    a fragment that names no colour is skipped, because the renderer's default is not this
    tool's to assume — the count of unchecked fragments is reported instead.
    """
    fragments = copy.get("copy") or []
    if not fragments:
        return
    brand = contrast.load_brand()
    themes = {s.get("index"): s.get("theme") for s in plan.get("scenes") or []}
    checked = skipped = 0
    for fragment in fragments:
        token = fragment.get("color")
        if not token:
            skipped += 1
            continue
        label = fragment.get("id") or f"copy[{fragment.get('scene')}]"
        theme = themes.get(fragment.get("scene")) or "dark"
        result = contrast.solve(brand, token, theme, fragment.get("size"))
        checked += 1
        if result["ok"]:
            continue
        size = fragment.get("size")
        at = f" at {size:g} px" if isinstance(size, (int, float)) and not isinstance(size, bool) else ""
        if result["reason"] == "forbidden":
            why = f"is banned on the {theme} ground — {result['against']}"
        elif result["reason"] == "unknown-token":
            why = f"is not a brand token ({result['against']})"
        else:
            why = (f"reads {result['worst']:.2f}:1 on the {theme} ground{at} and needs "
                   f"{result['required']:.1f}:1 (weakest at {result['against']})")
        rep.error("T06", f"{label}: {token} {why} — pick a brand.json token that clears the bar")
    if checked:
        rep.ok("T06", f"{checked} coloured fragment(s) clear WCAG contrast on their ground"
                      + (f" · {skipped} name no colour (renderer default, unchecked)" if skipped else ""))
    elif skipped:
        rep.ok("T06", f"{skipped} fragment(s) name no colour — nothing to measure "
                      f"(add \"color\": a brand token and \"theme\": dark|light per scene to gate them)")


# ---- optional code scan ----------------------------------------------------------------------
def lint_code(rep: Report, project: Path) -> None:
    files = [p for p in list(project.glob("*.py")) + list(project.glob("*.ts")) + list(project.glob("*.tsx"))
             + list(project.glob("src/**/*.js")) + list(project.glob("src/**/*.ts"))
             + list(project.glob("src/**/*.tsx"))
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

    # Raw text drawing bypasses the agent's direction. Scene code must use the
    # directed helpers (drawDirectedText / draw_directed_text / DirectedText).
    scene_files = [p for p in list(project.glob("scenes.py")) + list(project.glob("scene*.py"))
                   + list(project.glob("src/scenes/**/*.js")) + list(project.glob("src/scenes/**/*.ts"))
                   + list(project.glob("src/scenes/**/*.tsx")) + list(project.glob("src/**/*.tsx"))
                   if p.is_file() and "src/lib" not in p.as_posix()]
    raw_hits = 0
    for f in scene_files:
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            allowed = RAW_ALLOW.search(line)
            allow = {t.strip().lower() for t in allowed.group(1).split(",")} if allowed else set()
            if "raw-text" in allow:
                continue
            if RAW_TEXT.search(line):
                rep.error("T04", f"{f.relative_to(project)}:{n}: raw text drawing bypasses plan/text-direction.json — "
                                 "use drawDirectedText / draw_directed_text / DirectedText (or annotate a deliberate exception)")
                raw_hits += 1
    if not raw_hits:
        rep.ok("T04", f"all scene text goes through the directed helpers ({len(scene_files)} file(s))")


# ---- optional Fixed Stage plan check (plan/stage.json) ---------------------------------------
def _load_strict_json(path: Path) -> Any:
    def _bad_const(val: str) -> None:
        raise ValueError(f"non-finite JSON constant {val!r} is forbidden")

    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_bad_const)


def _scene_words_map(project: Path) -> dict[int, list[dict]]:
    wt_path = project / "plan" / "word-timings.json"
    if not wt_path.is_file():
        return {}
    try:
        doc = _load_strict_json(wt_path)
    except Exception:
        return {}
    out: dict[int, list[dict]] = {}
    if isinstance(doc, dict):
        for sc in doc.get("scenes") or []:
            if isinstance(sc, dict) and isinstance(sc.get("scene"), int):
                out[sc["scene"]] = list(sc.get("words") or [])
    return out


def lint_slide_wall(rep: Report, project: Path, plan: dict) -> None:
    """Optional Phase 2B contract gate; no wall plan means no wall and no warning."""
    path = project / "plan" / "slide-wall.json"
    if not path.is_file():
        return
    try:
        spec = _load_strict_json(path)
    except Exception as exc:
        rep.error("W01", f"plan/slide-wall.json invalid JSON: {exc}")
        return
    duration = plan.get("duration")
    has_duration = isinstance(duration, (int, float)) and not isinstance(duration, bool) and float(duration) > 0
    errors = slide_wall.validate_slide_wall_spec(spec, duration=float(duration) if has_duration else None)
    for error in errors:
        rep.error("W01", f"plan/slide-wall.json: {error}")
    if not errors:
        rep.ok("W00", "slide wall: stable ids, geometry, bounds, separation and continuous VO timeline verified")


def lint_one_take(rep: Report, project: Path, plan: dict) -> None:
    """Optional Phase 2C contract gate; no One-Take plan means no One-Take warning."""
    path = project / "plan" / "one-take.json"
    if not path.is_file():
        return
    try:
        spec = _load_strict_json(path)
    except Exception as exc:
        rep.error("O01", f"plan/one-take.json invalid JSON: {exc}")
        return
    duration = plan.get("duration")
    if not one_take._finite(duration) or duration <= 0:
        errors = ["plan/beats.json must contain a finite positive duration when plan/one-take.json exists"]
        errors += one_take.validate_one_take_spec(spec)
    else:
        errors = one_take.validate_one_take_spec(spec, duration=float(duration))
    for error in errors:
        rep.error("O01", f"plan/one-take.json: {error}")
    if not errors:
        rep.ok("O00", "one-take: stable elements, continuous camera states and deterministic interactions verified")


def lint_stage(rep: Report, project: Path, plan: dict, copy: dict) -> None:
    stage_path = project / "plan" / "stage.json"
    if not stage_path.is_file():
        return
    try:
        stage_doc = _load_strict_json(stage_path)
    except Exception as exc:
        rep.error("F01", f"plan/stage.json invalid JSON: {exc}")
        return

    spec_errors = stage_mod.validate_stage_spec(stage_doc)
    for err in spec_errors:
        rep.error("F01", f"plan/stage.json: {err}")
    if spec_errors:
        return

    norm = stage_mod.normalize_stage_spec(stage_doc)
    if not norm["enabled"]:
        return
    dur = plan.get("duration")
    has_dur = isinstance(dur, (int, float)) and not isinstance(dur, bool) and float(dur) > 0
    scene_ids = {
        s.get("index", idx + 1)
        for idx, s in enumerate(plan.get("scenes") or [])
        if isinstance(s, dict)
    }
    copy_map = {
        c.get("id"): c
        for c in (copy.get("copy") or [])
        if isinstance(c, dict) and isinstance(c.get("id"), str)
    }
    direction = td.load(project)
    words_by_scene = _scene_words_map(project)
    stage_had_error = False

    if stage_doc.get("timeline") is not None and has_dur:
        for idx, seg in enumerate(norm["segments"]):
            if seg["end"] > float(dur) + 1e-6:
                rep.error("F02", f"plan/stage.json timeline[{idx}] ends at {seg['end']:g}s past VO duration {float(dur):g}s")
                stage_had_error = True
            anc = seg.get("anchor")
            if anc and words_by_scene:
                sc_words = words_by_scene.get(anc["scene"])
                if not sc_words or anc["word"] >= len(sc_words):
                    rep.error("F04", f"plan/stage.json timeline[{idx}].anchor word {anc['word']} missing in scene {anc['scene']}")
                    stage_had_error = True
                else:
                    w_obj = sc_words[anc["word"]]
                    if "text" in anc and anc["text"] not in str(w_obj.get("text", "")):
                        rep.error("F04", f"plan/stage.json timeline[{idx}].anchor text {anc['text']!r} != {w_obj.get('text')!r}")
                        stage_had_error = True
                    elif abs(seg["start"] - float(w_obj["start"])) > 0.35:
                        rep.error(
                            "F04",
                            f"plan/stage.json timeline[{idx}] start {seg['start']:g}s drifts >0.35s from anchored word onset {float(w_obj['start']):g}s",
                        )
                        stage_had_error = True

    for slot in norm["over"]["header"]["slots"]:
        if has_dur and slot["end"] > float(dur) + 1e-6:
            rep.error("F02", f"plan/stage.json header slot {slot['id']!r} ends at {slot['end']:g}s past VO duration {float(dur):g}s")
            stage_had_error = True
        if scene_ids and slot["scene"] not in scene_ids:
            rep.error("F03", f"plan/stage.json header slot {slot['id']!r} references missing scene {slot['scene']}")
            stage_had_error = True
        frag = copy_map.get(slot["copyId"])
        if frag is None or not str(frag.get("text") or "").strip():
            rep.error("F03", f"plan/stage.json header slot {slot['id']!r} copyId {slot['copyId']!r} not found in plan/copy.json")
            stage_had_error = True
        if not direction:
            rep.error("F03", f"plan/stage.json header slot {slot['id']!r} requires plan/text-direction.json")
            stage_had_error = True
        else:
            try:
                td.text_style_for(direction, slot["scene"], slot["role"], slot["copyId"])
                td.font_for(direction, slot["scene"], slot["role"], slot["copyId"])
            except ValueError as exc:
                rep.error("F03", f"plan/stage.json header slot {slot['id']!r}: {exc}")
                stage_had_error = True
        anc = slot.get("anchor")
        if anc and words_by_scene:
            sc_words = words_by_scene.get(anc["scene"])
            if not sc_words or anc["word"] >= len(sc_words):
                rep.error("F04", f"plan/stage.json header slot {slot['id']!r} anchor word {anc['word']} missing in scene {anc['scene']}")
                stage_had_error = True

    if not stage_had_error:
        rep.ok(
            "F00",
            f"fixed stage: {len(norm['segments'])} segment(s) · {len(norm['over']['header']['slots'])} header slot(s) verified",
        )


# ---- cli -------------------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Lint a reel plan against the measured craft norms.")
    ap.add_argument("project", type=Path)
    ap.add_argument("--pace", default=None, choices=["calm", "crisp"], help="default calm")
    ap.add_argument("--bpm", type=float, default=None, help="tempo; defaults to plan/copy.json")
    ap.add_argument("--tol", type=float, default=GRID_TOL)
    ap.add_argument("--strict", action="store_true", help="warnings fail too")
    ap.add_argument("--scan-code", action="store_true")
    ap.add_argument("--max-occlusion", type=float, default=None, help="override X03 max foreground occlusion (0..1)")
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
    lint_first_frame(rep, plan, copy)
    dur = float(plan.get("duration") or 0)
    scenes = plan.get("scenes") or []
    if dur and scenes:
        lint_copy(rep, copy, dur, pace, bpm, scenes)
    lint_moves(rep, draw)
    if dur and scenes:
        lint_text_direction(rep, a.project, plan, copy)
        lint_contrast(rep, copy, plan)
    if (a.project / 'plan/visual-direction.json').is_file():
        for error in vd.check_project(a.project)['errors']:
            rep.error('V01', error)
    if (a.project / 'plan/machines').is_dir():
        m_res = me.check_project(a.project, max_occlusion=a.max_occlusion)
        if m_res['errors']:
            for code, msg in m_res['errors']:
                rep.error(code, msg)
        elif m_res['machines']:
            rep.ok('X00', f"machine explainer: {len(m_res['machines'])} spec(s) verified (X01–X04)")
    if (a.project / 'plan/stage.json').is_file():
        lint_stage(rep, a.project, plan, copy)
    if (a.project / 'plan/slide-wall.json').is_file():
        lint_slide_wall(rep, a.project, plan)
    if (a.project / 'plan/one-take.json').is_file():
        lint_one_take(rep, a.project, plan)
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
