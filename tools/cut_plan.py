#!/usr/bin/env python3
"""Build, review and edit a `cut-plan.json` — and never execute it.

B4 stops at the plan. `build` reads a media report (from `video_ingest.py`), turns the visual deltas
into shots, and writes a plan a human can read, reject, and hand back. `check` is the contract;
`review` prints it; `set` flips one shot; `preview` draws the timeline. `render` refuses on purpose.

    python3 tools/cut_plan.py build out/media-report.json -o out/cut-plan.json
    python3 tools/cut_plan.py review out/cut-plan.json
    python3 tools/cut_plan.py set out/cut-plan.json cut-02=reject
    python3 tools/cut_plan.py preview out/cut-plan.json -o out/cut-plan.html
    python3 tools/cut_plan.py render …            # exit 3: B4 has no executor

Exit codes: 0 ok · 1 invalid plan/report · 2 unreadable file · 3 execution refused.
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

VERSION = 1
SETTINGS = {"threshold": 25.0, "minShot": 0.4}
REASONS = ("first-shot", "visual-cut")
ROOT_FIELDS = {"version", "source", "video", "settings", "cuts", "totals"}
CUT_FIELDS = {"id", "in", "out", "keep", "reason", "score"}
SOURCE_FIELDS = {"sha256", "duration", "fps"}
VIDEO_FIELDS = {"width", "height", "fps", "duration", "frames", "vfr"}
SETTINGS_FIELDS = {"threshold", "minShot"}
TOTALS_FIELDS = {"shots", "keptSeconds", "rejectedSeconds", "duration"}
EPS = 1e-6


class PlanError(RuntimeError):
    """Raised for a plan the contract refuses, with the codes already collected."""


def _is_num(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _round(value: float) -> float:
    return round(float(value) + 0.0, 3)


def _seconds(frame: int, fps: float, duration: float) -> float:
    """Frame index → seconds, with the last frame pinned to the measured duration."""
    t = min(duration, frame / fps)
    return _round(t)


# ------------------------------------------------------------------ build
def shots_from_deltas(deltas: list[float], fps: float, duration: float, threshold: float) -> list[tuple[int, int, float]]:
    """Split [0, frames] at every delta at/above `threshold`; returns (start,end,score) per shot."""
    frames = len(deltas) + 1
    starts = [0]
    scores = [0.0]
    for index, value in enumerate(deltas):
        if value >= threshold:
            starts.append(index + 1)
            scores.append(_round(value))
    starts.append(frames)
    scores.append(0.0)
    out = []
    for i in range(len(starts) - 1):
        out.append((starts[i], starts[i + 1], scores[i]))
    if not out:
        out = [(0, frames, 0.0)]
    return out


def merge_short(shots: list[tuple[int, int, float]], fps: float, min_shot: float) -> list[tuple[int, int, float, str]]:
    """Fold any shot shorter than `min_shot` into its neighbour; the boundary simply disappears."""
    merged: list[list] = []
    for start, end, score in shots:
        if merged and (end - start) / fps < min_shot - EPS:
            merged[-1][1] = end
        else:
            merged.append([start, end, score, "visual-cut"])
    if len(merged) > 1 and (merged[0][1] - merged[0][0]) / fps < min_shot - EPS:
        merged[1][0] = merged[0][0]
        merged.pop(0)
    merged[0][3] = "first-shot"
    return [(s, e, sc, reason) for s, e, sc, reason in merged]


def build_plan(report: dict, *, threshold: float | None = None, min_shot: float | None = None) -> dict:
    """Turn a media report into a plan. Pure: same report in, same plan out."""
    errors = _report_errors(report)
    if errors:
        raise PlanError("; ".join(errors))
    video = report["video"]
    fps = float(video["fps"])
    duration = float(video["duration"])
    threshold = SETTINGS["threshold"] if threshold is None else float(threshold)
    min_shot = SETTINGS["minShot"] if min_shot is None else float(min_shot)
    if not 0 < threshold <= 255:
        raise PlanError("threshold must be within (0, 255]")
    if min_shot < 0:
        raise PlanError("minShot must be >= 0")

    shots = shots_from_deltas(report["deltas"], fps, duration, threshold)
    merged = merge_short(shots, fps, min_shot)
    cuts = []
    for index, (start, end, score, reason) in enumerate(merged):
        cuts.append({
            "id": f"cut-{index + 1:02d}",
            "in": _seconds(start, fps, duration),
            "out": duration if index == len(merged) - 1 else _seconds(end, fps, duration),
            "keep": True,
            "reason": reason,
            "score": score,
        })
    plan = {
        "version": VERSION,
        "source": {"sha256": report["source"]["sha256"], "duration": duration, "fps": fps},
        "video": {key: video[key] for key in ("width", "height", "fps", "duration", "frames", "vfr")},
        "settings": {"threshold": threshold, "minShot": min_shot},
        "cuts": cuts,
        "totals": {},
    }
    plan["totals"] = totals(plan)
    return plan


def totals(plan: dict) -> dict:
    kept = round(sum(c["out"] - c["in"] for c in plan["cuts"] if c["keep"]), 3)
    rejected = round(sum(c["out"] - c["in"] for c in plan["cuts"] if not c["keep"]), 3)
    return {
        "shots": len(plan["cuts"]),
        "keptSeconds": kept,
        "rejectedSeconds": rejected,
        "duration": plan["source"]["duration"],
    }


# ------------------------------------------------------------------ validation
def _report_errors(report: dict) -> list[str]:
    errors = []
    if not isinstance(report, dict):
        return ["media report must be an object"]
    source = report.get("source")
    video = report.get("video")
    deltas = report.get("deltas")
    if not isinstance(source, dict) or len(str(source.get("sha256", ""))) != 64:
        errors.append("media report requires source.sha256 (64 hex characters)")
    if not isinstance(video, dict):
        errors.append("media report requires video{}")
        return errors
    for key in ("fps", "duration", "frames"):
        if not _is_num(video.get(key)) or video[key] <= 0:
            errors.append(f"media report video.{key} must be a positive number")
    if not isinstance(deltas, list) or len(deltas) != int(video.get("frames", 0)) - 1:
        errors.append("deltas must hold exactly frames-1 numbers")
    elif any(not _is_num(d) or d < 0 for d in deltas):
        errors.append("every delta must be a non-negative number")
    return errors


def validate(plan: dict) -> list[str]:
    """Return every contract violation, coded C00..C07 — empty means the plan is usable."""
    errors: list[str] = []
    if not isinstance(plan, dict):
        return ["C00 root: plan must be an object"]
    if plan.get("version") != VERSION:
        errors.append(f"C00 version: only version {VERSION} is accepted")
    unknown = set(plan) - ROOT_FIELDS
    if unknown:
        errors.append(f"C01 unknown fields: {sorted(unknown)}")
    missing = ROOT_FIELDS - set(plan)
    if missing:
        errors.append(f"C01 missing fields: {sorted(missing)}")
        return errors

    source = plan["source"]
    if not isinstance(source, dict) or set(source) != SOURCE_FIELDS:
        errors.append("C00 source: needs exactly {sha256, duration, fps}")
    else:
        if not isinstance(source["sha256"], str) or len(source["sha256"]) != 64:
            errors.append("C00 source.sha256: 64 hex characters required")
        if not _is_num(source["duration"]) or source["duration"] <= 0:
            errors.append("C00 source.duration: positive number required")
        if not _is_num(source["fps"]) or source["fps"] <= 0:
            errors.append("C00 source.fps: positive number required")

    video = plan["video"]
    if not isinstance(video, dict) or set(video) != VIDEO_FIELDS:
        errors.append("C01 video: needs exactly {width,height,fps,duration,frames,vfr}")
    else:
        if not isinstance(video["vfr"], bool):
            errors.append("C01 video.vfr: boolean required")
        if not all(_is_num(video[k]) and video[k] > 0 for k in ("width", "height", "fps", "duration", "frames")):
            errors.append("C00 video: width/height/fps/duration/frames must be positive numbers")
        elif _is_num(source.get("duration")) and abs(video["duration"] - source["duration"]) > 1e-3:
            errors.append("C00 video.duration must equal source.duration")

    settings = plan["settings"]
    if not isinstance(settings, dict) or set(settings) != SETTINGS_FIELDS:
        errors.append("C05 settings: needs exactly {threshold, minShot}")
    else:
        if not _is_num(settings["threshold"]) or not 0 < settings["threshold"] <= 255:
            errors.append("C05 settings.threshold: number within (0, 255]")
        if not _is_num(settings["minShot"]) or settings["minShot"] < 0:
            errors.append("C05 settings.minShot: non-negative number")

    cuts = plan["cuts"]
    if not isinstance(cuts, list) or not cuts:
        errors.append("C02 cuts: non-empty list required")
        return errors
    ids = set()
    previous_out = 0.0
    duration = source.get("duration") if isinstance(source, dict) else 0
    for index, cut in enumerate(cuts):
        where = f"cuts[{index}]"
        if not isinstance(cut, dict):
            errors.append(f"C02 {where}: object required")
            continue
        extra = set(cut) - CUT_FIELDS
        absent = CUT_FIELDS - set(cut)
        if extra or absent:
            errors.append(f"C01 {where}: unknown {sorted(extra)} missing {sorted(absent)}")
            continue
        if not isinstance(cut["id"], str) or not cut["id"]:
            errors.append(f"C02 {where}.id: non-empty string required")
        elif cut["id"] in ids:
            errors.append(f"C02 {where}.id: duplicate id {cut['id']!r}")
        else:
            ids.add(cut["id"])
        if not _is_num(cut["in"]) or not _is_num(cut["out"]):
            errors.append(f"C03 {where}: in/out must be numbers")
            continue
        if cut["in"] < 0 or cut["out"] <= cut["in"]:
            errors.append(f"C03 {where}: requires 0 <= in < out")
        if _is_num(duration) and cut["out"] > duration + 1e-3:
            errors.append(f"C03 {where}.out: beyond source.duration")
        if abs(cut["in"] - previous_out) > 1e-3:
            errors.append(f"C02 {where}: cuts must tile the source without gaps or overlaps")
        previous_out = cut["out"]
        if not isinstance(cut["keep"], bool):
            errors.append(f"C04 {where}.keep: boolean required")
        if cut["reason"] not in REASONS:
            errors.append(f"C02 {where}.reason: must be one of {list(REASONS)}")
        if not _is_num(cut["score"]) or cut["score"] < 0:
            errors.append(f"C03 {where}.score: non-negative number required")
        if isinstance(settings, dict) and _is_num(settings.get("minShot")) and _is_num(cut["in"]) and _is_num(cut["out"]):
            if cut["out"] - cut["in"] < settings["minShot"] - 1e-3:
                errors.append(f"C03 {where}: shorter than settings.minShot")
    if _is_num(duration) and abs(previous_out - duration) > 1e-3:
        errors.append("C02 cuts: the last cut must end at source.duration")

    expected = totals(plan) if not errors or all(isinstance(c, dict) for c in cuts) else None
    if expected and isinstance(plan.get("totals"), dict):
        if set(plan["totals"]) != TOTALS_FIELDS:
            errors.append("C06 totals: needs exactly {shots,keptSeconds,rejectedSeconds,duration}")
        else:
            for key in TOTALS_FIELDS:
                if not _is_num(plan["totals"][key]):
                    errors.append(f"C06 totals.{key}: number required")
                elif abs(plan["totals"][key] - expected[key]) > 1e-3:
                    errors.append(f"C06 totals.{key}: says {plan['totals'][key]} but cuts give {expected[key]}")
    return errors


# ------------------------------------------------------------------ review + edit
def review_lines(plan: dict) -> list[str]:
    lines = [f"{'id':8} {'in':>7} {'out':>7} {'keep':>5} {'reason':14} {'score':>7}"]
    for cut in plan["cuts"]:
        lines.append(f"{cut['id']:8} {cut['in']:7.2f} {cut['out']:7.2f} "
                     f"{'yes' if cut['keep'] else 'no':>5} {cut['reason']:14} {cut['score']:7.2f}")
    t = plan["totals"]
    lines.append("")
    lines.append(f"{t['shots']} shots · kept {t['keptSeconds']:.2f}s · rejected "
                 f"{t['rejectedSeconds']:.2f}s · of {t['duration']:.2f}s")
    return lines


def set_keep(plan: dict, cut_id: str, keep: bool) -> dict:
    found = False
    for cut in plan["cuts"]:
        if cut["id"] == cut_id:
            cut["keep"] = keep
            found = True
    if not found:
        raise PlanError(f"no cut with id {cut_id!r}")
    plan["totals"] = totals(plan)
    return plan


# ------------------------------------------------------------------ preview
PALETTE = {"ink": "#0A0A0A", "paper": "#F3F2F1", "red": "#CB271B", "gray": "#8E8E93", "line": "#D8D7D5"}


def preview_svg(plan: dict, *, width: int = 1080) -> str:
    """A static timeline: one bar per cut, kept in ink and rejected in red. No clock, no randomness."""
    duration = plan["source"]["duration"]
    pad, bar_y, bar_h = 40, 54, 64
    scale = (width - pad * 2) / duration
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 190" width="{width}" height="190">',
             f'<rect width="{width}" height="190" fill="{PALETTE["paper"]}"/>']
    for cut in plan["cuts"]:
        x = pad + cut["in"] * scale
        w = max(1.0, (cut["out"] - cut["in"]) * scale)
        fill = PALETTE["ink"] if cut["keep"] else PALETTE["red"]
        parts.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="{bar_h}" fill="{fill}"/>')
        if w > 46:
            parts.append(f'<text x="{x + w / 2:.2f}" y="{bar_y + 24}" text-anchor="middle" font-size="13" '
                         f'fill="{PALETTE["paper"]}" font-family="monospace">{html.escape(cut["id"])}</text>')
            parts.append(f'<text x="{x + w / 2:.2f}" y="{bar_y + 44}" text-anchor="middle" font-size="11" '
                         f'fill="{PALETTE["paper"]}" font-family="monospace">{cut["in"]:.2f}–{cut["out"]:.2f}</text>')
    for second in range(0, int(duration) + 1):
        x = pad + second * scale
        parts.append(f'<line x1="{x:.2f}" y1="{bar_y + bar_h}" x2="{x:.2f}" y2="{bar_y + bar_h + 6}" stroke="{PALETTE["gray"]}"/>')
        parts.append(f'<text x="{x:.2f}" y="{bar_y + bar_h + 20}" text-anchor="middle" font-size="10" '
                     f'fill="{PALETTE["gray"]}" font-family="monospace">{second}s</text>')
    t = plan["totals"]
    parts.append(f'<text x="{pad}" y="28" font-size="13" fill="{PALETTE["ink"]}" font-family="monospace">'
                 f'{t["shots"]} shots · keep {t["keptSeconds"]:.2f}s · reject {t["rejectedSeconds"]:.2f}s</text>')
    parts.append("</svg>")
    return "".join(parts)


def preview_html(plan: dict) -> str:
    rows = "".join(
        f"<tr><td>{html.escape(c['id'])}</td><td>{c['in']:.2f}</td><td>{c['out']:.2f}</td>"
        f"<td class=\"{'keep' if c['keep'] else 'drop'}\">{'keep' if c['keep'] else 'reject'}</td>"
        f"<td>{html.escape(c['reason'])}</td><td>{c['score']:.2f}</td></tr>"
        for c in plan["cuts"]
    )
    t = plan["totals"]
    return f"""<!doctype html><html lang="ar" dir="rtl"><meta charset="utf-8">
<title>Cut plan</title>
<style>
 body{{font:14px/1.6 system-ui,sans-serif;margin:26px;background:#fff;color:#0A0A0A}}
 h1{{font-size:19px;margin:0 0 2px}} .sub{{color:#71717A;font-size:13px;margin:0 0 18px}}
 table{{border-collapse:collapse;margin-top:22px;font-variant-numeric:tabular-nums}}
 th,td{{padding:5px 12px;border-bottom:1px solid #E4E2E0;text-align:start;font-size:13px}}
 th{{color:#71717A;font-weight:600;font-size:12px}}
 .keep{{color:#0A0A0A;font-weight:600}} .drop{{color:#CB271B;font-weight:600}}
 .totals{{margin-top:14px;color:#71717A;font-size:13px}}
</style>
<h1>خطة القطع — {html.escape(plan['source']['sha256'][:12])}</h1>
<p class="sub">B4: الخطة تُراجع وتُعدّل ولا تُنفَّذ. · threshold {plan['settings']['threshold']} · minShot {plan['settings']['minShot']}s</p>
{preview_svg(plan)}
<table><thead><tr><th>#</th><th>in</th><th>out</th><th>الحالة</th><th>السبب</th><th>score</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="totals">{t['shots']} لقطة · محتفظ به {t['keptSeconds']:.2f}s · مرفوض {t['rejectedSeconds']:.2f}s · من {t['duration']:.2f}s</p>
</html>
"""


# ------------------------------------------------------------------ CLI
def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"error: cannot read {path}: {exc}") from exc


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and review cut plans; never execute them.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="media report → cut plan")
    build.add_argument("media", type=Path)
    build.add_argument("-o", "--out", type=Path, required=True)
    build.add_argument("--threshold", type=float, default=None)
    build.add_argument("--min-shot", type=float, default=None)

    check = sub.add_parser("check", help="validate a plan")
    check.add_argument("plan", type=Path)

    review = sub.add_parser("review", help="print the plan as a table")
    review.add_argument("plan", type=Path)
    review.add_argument("--json", action="store_true")

    edit = sub.add_parser("set", help="keep/reject one cut by id")
    edit.add_argument("plan", type=Path)
    edit.add_argument("change", help="cut-02=reject | cut-02=keep")
    edit.add_argument("-o", "--out", type=Path)

    preview = sub.add_parser("preview", help="write an HTML timeline")
    preview.add_argument("plan", type=Path)
    preview.add_argument("-o", "--out", type=Path, required=True)

    edl = sub.add_parser("edl", help="kept cuts → CMX3600 EDL (delivery, no executor)")
    edl.add_argument("plan", type=Path)
    edl.add_argument("-o", "--out", type=Path, required=True)
    edl.add_argument("--title", default=None)

    refused = sub.add_parser("render", help="refused on purpose: B4 has no executor")
    refused.add_argument("plan", nargs="?", type=Path, help="accepted and ignored: there is no executor")

    args = parser.parse_args(argv)

    if args.command == "render":
        print("refused: B4 ships a cut plan, not an executor. Review and edit it, then hand it to the "
              "timeline phase (B5).", file=sys.stderr)
        return 3

    if args.command == "build":
        plan = build_plan(_read_json(args.media), threshold=args.threshold, min_shot=args.min_shot)
        _write_json(args.out, plan)
        print(f"wrote {args.out} · {plan['totals']['shots']} shots · "
              f"keep {plan['totals']['keptSeconds']:.2f}s / {plan['totals']['duration']:.2f}s")
        return 0

    plan = _read_json(args.plan)

    if args.command == "check":
        errors = validate(plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid plan · {plan['totals']['shots']} shots · "
              f"{plan['totals']['keptSeconds']:.2f}s kept of {plan['totals']['duration']:.2f}s")
        return 0

    if args.command == "review":
        errors = validate(plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(plan["totals"], ensure_ascii=False))
        else:
            print("\n".join(review_lines(plan)))
        return 0

    if args.command == "set":
        if "=" not in args.change:
            print("error: expected cut-id=keep|reject", file=sys.stderr)
            return 2
        cut_id, _, raw = args.change.partition("=")
        if raw not in ("keep", "reject"):
            print("error: value must be keep or reject", file=sys.stderr)
            return 2
        try:
            set_keep(plan, cut_id.strip(), raw == "keep")
        except PlanError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        errors = validate(plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        target = args.out or args.plan
        _write_json(target, plan)
        t = plan["totals"]
        print(f"{cut_id.strip()} → {raw} · keep {t['keptSeconds']:.2f}s · reject {t['rejectedSeconds']:.2f}s")
        return 0

    if args.command == "edl":
        errors = validate(plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        import edl_export  # noqa: PLC0415 - EDL belongs to the delivery module, not the planner

        try:
            text, manifest = edl_export.build_from_plan(plan, title=args.title)
        except edl_export.EdlError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
        sidecar = args.out.with_suffix(args.out.suffix + ".json")
        sidecar.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {args.out} · {manifest['totals']['events']} kept cuts · "
              f"{manifest['fps']} fps · {manifest['totals']['durationTc']} · {sidecar}")
        return 0

    if args.command == "preview":
        errors = validate(plan)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(preview_html(plan), encoding="utf-8")
        print(f"wrote {args.out} · {plan['totals']['shots']} cuts")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
