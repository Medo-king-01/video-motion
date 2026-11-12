#!/usr/bin/env python3
"""Check the executable motion catalog and separate it from the descriptive library.

`medo-motion/motion/moves.json` is the one place that answers "how many moves can this studio
actually run?". A family is `executable` only when every supported engine names a real
implementation file, the symbols are present in it, and the evidence exists. A family is
`descriptive` when it is prose and cannot be called — the 2,239-entry technique library is the
big one, and it must never be counted as a move bank again (docs/exploitation-map.md §1).

    python3 tools/moves.py --check      # exit 1 on a claim the tree cannot back up
    python3 tools/moves.py --audit      # per-family states and executable totals
    python3 tools/moves.py --json       # the registry as-is

Exit codes: 0 consistent, 1 inconsistent, 2 unreadable/invalid JSON.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "medo-motion" / "motion" / "moves.json"
ENGINES = ("P", "K", "R", "Hybrid")
FAMILY_STATES = ("executable", "descriptive")
ENGINE_STATES = ("supported", "conditional", "unsupported", "unknown")
FAMILY_KEYS = {"title", "state", "source", "sourceCollection", "count", "members", "unit",
               "timing", "preview", "limits", "why", "engines"}
ENGINE_KEYS = {"state", "impl", "symbols", "evidence", "conditions"}


def _no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key {key!r}")
        obj[key] = value
    return obj


def load(path: Path = REGISTRY):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"invalid constant {value}")))


def measure(family: dict) -> int:
    """How many units the family's own source declares (never the hand-written count)."""
    if "sourceCollection" in family:
        data = json.loads((ROOT / family["source"]).read_text(encoding="utf-8"))
        return len(data[family["sourceCollection"]])
    return len(family.get("members", []))


def _evidence_ok(value: str) -> bool:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in value:
        return False
    return (ROOT / candidate).is_file()


def _check_engines(family_id: str, engines, errors: list[str]) -> None:
    if not isinstance(engines, dict):
        errors.append(f"M04 families.{family_id}.engines: object expected")
        return
    for name, entry in engines.items():
        where = f"families.{family_id}.engines.{name}"
        if name not in ENGINES:
            errors.append(f"M04 {where}: unknown engine (expected {list(ENGINES)})")
            continue
        if not isinstance(entry, dict):
            errors.append(f"M04 {where}: object expected")
            continue
        for key in sorted(set(entry) - ENGINE_KEYS):
            errors.append(f"M04 {where}: unknown field {key!r}")
        state = entry.get("state")
        if state not in ENGINE_STATES:
            errors.append(f"M04 {where}.state: expected one of {list(ENGINE_STATES)}")
            continue
        if state in ("supported", "conditional"):
            impl = entry.get("impl")
            if not isinstance(impl, str) or not impl.strip():
                errors.append(f"M05 {where}.impl: required for {state}")
            elif not (ROOT / impl).is_file():
                errors.append(f"M05 {where}.impl: {impl!r} does not exist")
            else:
                text = (ROOT / impl).read_text(encoding="utf-8")
                symbols = entry.get("symbols")
                if not isinstance(symbols, list) or not symbols:
                    errors.append(f"M05 {where}.symbols: nonempty list required for {state}")
                else:
                    for symbol in symbols:
                        if not isinstance(symbol, str) or symbol not in text:
                            errors.append(f"M05 {where}.symbols: {symbol!r} not found in {impl}")
            evidence = entry.get("evidence")
            if not isinstance(evidence, list) or not evidence:
                errors.append(f"M05 {where}.evidence: {state} needs evidence")
            else:
                for item in evidence:
                    if not isinstance(item, str) or not _evidence_ok(item):
                        errors.append(f"M05 {where}.evidence: {item!r} is not an existing repo file")
        if state == "conditional":
            conditions = entry.get("conditions")
            if not isinstance(conditions, list) or not conditions or any(
                    not isinstance(item, str) or not item.strip() for item in conditions):
                errors.append(f"M05 {where}.conditions: conditional needs at least one condition")
        if state in ("unsupported", "unknown"):
            for item in entry.get("evidence", []) or []:
                if not isinstance(item, str) or not _evidence_ok(item):
                    errors.append(f"M05 {where}.evidence: {item!r} is not an existing repo file")


def validate(registry) -> list[str]:
    errors: list[str] = []
    if not isinstance(registry, dict):
        return ["M00 $: expected an object"]
    for key in sorted(set(registry) - {"version", "note", "families"}):
        errors.append(f"M00 $.{key}: unknown top-level field")
    if registry.get("version") != 1:
        errors.append("M00 $.version: only version 1 is defined")
    if not isinstance(registry.get("note"), str) or not registry["note"].strip():
        errors.append("M00 $.note: nonempty string required")
    families = registry.get("families")
    if not isinstance(families, dict) or not families:
        return errors + ["M01 $.families: nonempty object expected"]

    for fid, family in families.items():
        where = f"families.{fid}"
        if not isinstance(family, dict):
            errors.append(f"M02 {where}: object expected")
            continue
        for key in sorted(set(family) - FAMILY_KEYS):
            errors.append(f"M02 {where}: unknown field {key!r}")
        for key in ("title", "state", "source", "unit", "timing", "engines"):
            if key not in family:
                errors.append(f"M02 {where}.{key}: required")
        if errors and any(error.startswith(f"M02 {where}.") for error in errors):
            continue
        source = family["source"]
        if not isinstance(source, str) or not (ROOT / source).is_file():
            errors.append(f"M03 {where}.source: {source!r} is not an existing repo file")
            continue
        state = family["state"]
        if state not in FAMILY_STATES:
            errors.append(f"M03 {where}.state: expected one of {list(FAMILY_STATES)}")
            continue
        if not isinstance(family["timing"], str) or not family["timing"].strip():
            errors.append(f"M03 {where}.timing: nonempty string required")
        preview = family.get("preview")
        if preview is not None and (not isinstance(preview, str) or not _evidence_ok(preview)):
            errors.append(f"M03 {where}.preview: {preview!r} is not an existing repo file")
        try:
            measured = measure(family)
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(f"M03 {where}.sourceCollection: cannot read source ({exc})")
            measured = None
        if measured is not None:
            count = family.get("count")
            if isinstance(count, bool) or not isinstance(count, int):
                errors.append(f"M03 {where}.count: integer required")
            elif count != measured:
                errors.append(f"M03 {where}.count: says {count}, source has {measured}")
            members = family.get("members")
            if members is not None:
                if not isinstance(members, list) or not members or any(
                        not isinstance(item, str) or not item.strip() for item in members):
                    errors.append(f"M03 {where}.members: nonempty list of ids expected")
                else:
                    if family.get("sourceCollection"):
                        known = set(json.loads((ROOT / source).read_text(encoding="utf-8"))[
                            family["sourceCollection"]])
                        unknown = sorted(set(members) - known)
                        if unknown:
                            errors.append(f"M03 {where}.members: not in source: {unknown}")
                    if count != len(members):
                        errors.append(f"M03 {where}.count: says {count}, members has {len(members)}")
        limits = family.get("limits")
        if limits is not None and (not isinstance(limits, list) or any(
                not isinstance(item, str) or not item.strip() for item in limits)):
            errors.append(f"M03 {where}.limits: list of nonempty strings expected")
        _check_engines(fid, family["engines"], errors)

        engines = family["engines"] if isinstance(family["engines"], dict) else {}
        supported = [name for name, entry in engines.items()
                     if isinstance(entry, dict) and entry.get("state") in ("supported", "conditional")]
        if state == "executable" and not supported:
            errors.append(f"M06 {where}: executable family needs at least one supported engine")
        if state == "descriptive":
            if supported:
                errors.append(f"M06 {where}: descriptive family cannot claim engines {supported}")
            if not isinstance(family.get("why"), str) or not family["why"].strip():
                errors.append(f"M06 {where}.why: descriptive family must say why it is not runnable")
    return errors


def audit(registry) -> dict:
    """Machine-readable summary; totals are measured from each family's source."""
    summary: dict = {"families": {}, "executable_moves": 0, "descriptive_units": 0,
                     "by_engine": {name: [] for name in ENGINES}}
    for fid, family in registry["families"].items():
        count = measure(family)
        engines = {name: entry["state"] for name, entry in family["engines"].items()}
        summary["families"][fid] = {"state": family["state"], "count": count, "engines": engines}
        if family["state"] == "executable":
            summary["executable_moves"] += count
        else:
            summary["descriptive_units"] += count
        for name, state in engines.items():
            if state in ("supported", "conditional"):
                summary["by_engine"][name].append(fid)
    return summary


def _print_audit(summary: dict) -> None:
    width = max(len(fid) for fid in summary["families"])
    print(f"{'family':<{width}}  {'state':<12}{'count':>7}  engines")
    for fid, row in summary["families"].items():
        engines = ", ".join(f"{name}={state}" for name, state in row["engines"].items()) or "—"
        print(f"{fid:<{width}}  {row['state']:<12}{row['count']:>7}  {engines}")
    print(f"\nexecutable moves: {summary['executable_moves']} · "
          f"descriptive units: {summary['descriptive_units']}")
    for name, families in summary["by_engine"].items():
        print(f"  {name}: {', '.join(families) or '—'}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="exit 1 on an unsupported claim (default)")
    parser.add_argument("--audit", action="store_true", help="print the per-family summary")
    parser.add_argument("--json", action="store_true", help="print the registry as-is")
    parser.add_argument("--registry", type=Path, default=REGISTRY, help="alternate registry path")
    args = parser.parse_args(argv)
    try:
        registry = load(args.registry)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot read moves registry: {exc}", file=sys.stderr)
        return 2
    errors = validate(registry)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(registry, ensure_ascii=False, indent=2))
    elif args.audit:
        _print_audit(audit(registry))
    else:
        summary = audit(registry)
        print(f"OK: {summary['executable_moves']} executable moves in "
              f"{sum(1 for row in summary['families'].values() if row['state'] == 'executable')} "
              f"families; {summary['descriptive_units']} descriptive units are not moves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
