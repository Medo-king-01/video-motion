#!/usr/bin/env python3
"""Delivery profiles (B6): 12 · 15 · 30 · 60 fps as *separate* declared profiles.

A profile never changes the project's timing — its duration and clip ticks stay exactly as they were.
It only changes how many frames those ticks are sampled into (`frameTicks = timebase × den / num`).
That is why 60 fps cannot leak into the 30 fps contract: the default profile stays `reel-30`, and
`motion-film-60` is marked `requiresApproval` because the go-ahead is the owner's decision.

    python3 tools/profiles.py list
    python3 tools/profiles.py check
    python3 tools/profiles.py apply project.json draft-15 -o out/draft.json
    python3 tools/profiles.py apply project.json motion-film-60 -o out/film.json --approval
    python3 tools/profiles.py canvas --profile draft-15 -o out/canvas.json

Exit codes: 0 ok · 1 invalid registry or project · 2 unreadable file · 3 approval missing.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "medo-motion" / "motion" / "profiles.json"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402

FIELDS = {"id", "label", "width", "height", "fps", "sampleRate", "use", "requiresApproval"}
ROOT_FIELDS = {"_doc", "version", "timebase", "profiles"}


class ProfileError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def load_registry(path: Path | None = None) -> dict:
    try:
        return json.loads(Path(path or REGISTRY).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProfileError("P01", f"cannot read registry: {exc}") from exc


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate_registry(registry: dict) -> list[str]:
    """P01 shape · P02 ids · P03 numbers · P06 non-integer frame ticks."""
    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["P01 root: registry must be an object"]
    extra = set(registry) - ROOT_FIELDS
    if extra:
        errors.append(f"P01 unknown root fields: {sorted(extra)}")
    if registry.get("version") != 1:
        errors.append("P01 version: only version 1 is accepted")
    timebase = registry.get("timebase")
    if not _is_int(timebase) or timebase <= 0:
        errors.append("P03 timebase: positive integer required")
        return errors
    profiles = registry.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        errors.append("P01 profiles: non-empty list required")
        return errors
    seen: set[str] = set()
    for index, profile in enumerate(profiles):
        where = f"profiles[{index}]"
        if not isinstance(profile, dict):
            errors.append(f"P01 {where}: object required")
            continue
        missing = FIELDS - set(profile)
        unknown = set(profile) - FIELDS
        if missing or unknown:
            errors.append(f"P01 {where}: missing {sorted(missing)} unknown {sorted(unknown)}")
            continue
        pid = profile["id"]
        if not isinstance(pid, str) or not pid.strip() or " " in pid:
            errors.append(f"P02 {where}.id: non-empty slug without spaces required")
        elif pid in seen:
            errors.append(f"P02 {where}.id: duplicate {pid!r}")
        else:
            seen.add(pid)
        for key in ("width", "height", "sampleRate"):
            if not _is_int(profile[key]) or profile[key] <= 0:
                errors.append(f"P03 {where}.{key}: positive integer required")
        if _is_int(profile["width"]) and _is_int(profile["height"]):
            if profile["width"] % 2 or profile["height"] % 2:
                errors.append(f"P03 {where}: width/height must be even for H.264 4:2:0")
        fps = profile["fps"]
        if not isinstance(fps, dict) or set(fps) != {"num", "den"}:
            errors.append(f"P03 {where}.fps: needs exactly {{num, den}}")
        elif not _is_int(fps["num"]) or not _is_int(fps["den"]) or fps["num"] <= 0 or fps["den"] <= 0:
            errors.append(f"P03 {where}.fps: positive integers required")
        elif math.gcd(fps["num"], fps["den"]) != 1:
            errors.append(f"P03 {where}.fps: fraction must be reduced")
        elif _is_int(timebase):
            if (timebase * fps["den"]) % fps["num"]:
                errors.append(f"P06 {where}: {fps['num']}/{fps['den']} does not divide timebase {timebase} "
                              "into whole frame ticks")
        if not isinstance(profile["requiresApproval"], bool):
            errors.append("P01 requiresApproval: boolean required")
        if not isinstance(profile["use"], str) or not profile["use"].strip():
            errors.append("P01 use: non-empty string required")
        if not isinstance(profile["label"], str) or not profile["label"].strip():
            errors.append("P01 label: non-empty string required")
    if seen and "reel-30" not in seen:
        errors.append("P02 reel-30: the 30 fps contract must stay declared as the default profile")
    return errors


def find(registry: dict, profile_id: str) -> dict:
    for profile in registry.get("profiles", []):
        if isinstance(profile, dict) and profile.get("id") == profile_id:
            return profile
    raise ProfileError("P02", f"unknown profile {profile_id!r}")


def frame_ticks(registry: dict, profile: dict) -> int:
    fps = profile["fps"]
    return registry["timebase"] * fps["den"] // fps["num"]


def apply_profile(project: dict, profile_id: str, *, registry: dict | None = None,
                  approval: bool = False) -> tuple[dict, dict]:
    """Return (project with the new profile, report). Timing is untouched; only sampling changes."""
    reg = registry or load_registry()
    errors = validate_registry(reg)
    if errors:
        raise ProfileError("P01", "; ".join(errors))
    profile = find(reg, profile_id)
    if profile["requiresApproval"] and not approval:
        raise ProfileError("P04", f"profile {profile_id!r} needs explicit approval (owner decision)")
    before_errors = validate(project)
    if before_errors:
        raise ProfileError("P05", "project is invalid before profiling: " + "; ".join(before_errors))
    if project["timebase"] != reg["timebase"]:
        raise ProfileError("P05", f"project timebase {project['timebase']} does not match registry {reg['timebase']}")
    ticks = frame_ticks(reg, profile)
    result = deepcopy(project)
    result["profile"] = {"width": profile["width"], "height": profile["height"],
                         "fps": dict(profile["fps"]), "sampleRate": profile["sampleRate"]}
    errors = validate(result)
    if errors:
        raise ProfileError("P05", "profile produced an invalid project: " + "; ".join(errors))
    report = {
        "profile": profile_id,
        "frameTicks": ticks,
        "framesBefore": -(-project["duration"] // (project["timebase"] * project["profile"]["fps"]["den"]
                                                   // project["profile"]["fps"]["num"])),
        "framesAfter": -(-project["duration"] // ticks),
        "duration": project["duration"],
        "requiresApproval": profile["requiresApproval"],
    }
    return result, report


def canvas_block(profile: dict) -> dict:
    """What the renderer needs from a profile: numbers only, and no hidden brand edit."""
    fps = profile["fps"]
    if fps["den"] != 1:
        raise ProfileError("P07", f"{profile['id']}: the renderer takes integer fps, not {fps['num']}/{fps['den']}")
    if profile["width"] % 2 or profile["height"] % 2:
        raise ProfileError("P03", f"{profile['id']}: width/height must be even")
    return {"profile": profile["id"], "w": profile["width"], "h": profile["height"], "fps": fps["num"],
            "note": "REEL_CANVAS: rate + device scale — engine P keeps its 9:16 design space "
                    "(a scaled copy only, never a reshape)"}


def canvas_for(profile_id: str, *, registry: dict | None = None, approval: bool = False) -> dict:
    reg = registry or load_registry()
    profile = find(reg, profile_id)
    if profile["requiresApproval"] and not approval:
        raise ProfileError("P04", f"profile {profile_id!r} needs explicit approval (owner decision)")
    return canvas_block(profile)


def canvas_from_project(project: dict, *, registry: dict | None = None) -> dict:
    """A project carries its own profile; refuse to hand the renderer a rate the registry never declared."""
    reg = registry or load_registry()
    errors = validate(project)
    if errors:
        raise ProfileError("P05", "project is invalid: " + "; ".join(errors))
    fps = project["profile"]["fps"]
    if fps["den"] != 1:
        raise ProfileError("P07", f"project fps {fps['num']}/{fps['den']} is not an integer rate")
    block = {"profile": f"project:{project['id']}", "w": project["profile"]["width"],
             "h": project["profile"]["height"], "fps": fps["num"],
             "note": "REEL_CANVAS: rate + device scale — engine P keeps its 9:16 design space "
                     "(a scaled copy only, never a reshape)"}
    declared = {(p["width"], p["height"], p["fps"]["num"]) for p in reg["profiles"]}
    block["declared"] = (block["w"], block["h"], block["fps"]) in declared
    return block


def table(registry: dict) -> str:
    rows = [f"{'id':16} {'size':>11} {'fps':>5} {'frameTicks':>10} {'approval':>8}"]
    for profile in registry["profiles"]:
        fps = profile["fps"]
        rows.append(f"{profile['id']:16} {profile['width']}×{profile['height']:<6} "
                    f"{fps['num']}/{fps['den']:<3} {frame_ticks(registry, profile):>10} "
                    f"{'yes' if profile['requiresApproval'] else 'no':>8}")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Declared delivery profiles; timing never changes.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="print the declared profiles")
    sub.add_parser("check", help="validate the registry contract")
    canvas = sub.add_parser("canvas", help="write the renderer canvas override (REEL_CANVAS)")
    canvas.add_argument("--profile", default=None)
    canvas.add_argument("--project", type=Path, default=None)
    canvas.add_argument("-o", "--out", type=Path, required=True)
    canvas.add_argument("--approval", action="store_true", help="allow a requiresApproval profile")
    apply = sub.add_parser("apply", help="apply one profile to a project")
    apply.add_argument("project", type=Path)
    apply.add_argument("profile")
    apply.add_argument("-o", "--out", type=Path, required=True)
    apply.add_argument("--approval", action="store_true", help="allow a requiresApproval profile")
    apply.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)
    try:
        registry = load_registry()
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.command == "list":
        print(table(registry))
        return 0

    if args.command == "check":
        errors = validate_registry(registry)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid registry · {len(registry['profiles'])} profiles · timebase {registry['timebase']}")
        return 0

    if args.command == "canvas":
        if bool(args.profile) == bool(args.project):
            print("error: pass exactly one of --profile or --project", file=sys.stderr)
            return 2
        try:
            if args.profile:
                block = canvas_for(args.profile, registry=registry, approval=args.approval)
            else:
                block = canvas_from_project(json.loads(args.project.read_text(encoding="utf-8")),
                                            registry=registry)
        except OSError as exc:
            print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
            return 2
        except json.JSONDecodeError as exc:
            print(f"error: {args.project} is not JSON: {exc}", file=sys.stderr)
            return 2
        except ProfileError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3 if exc.code == "P04" else 1
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(block, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"{block['profile']}: {block['w']}×{block['h']} · {block['fps']} fps → {args.out}")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    try:
        profiled, report = apply_profile(project, args.profile, registry=registry, approval=args.approval)
    except ProfileError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3 if exc.code == "P04" else 1
    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(profiled, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.profile}: {report['framesBefore']} → {report['framesAfter']} frames · "
          f"{report['frameTicks']} ticks/frame · duration {report['duration']} unchanged"
          + ("" if args.dry_run else f" · wrote {args.out}"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
