#!/usr/bin/env python3
"""Check the declared execution capabilities of P/K/R/Hybrid against the repository.

The manifest at `medo-motion/schema/backend-capabilities.json` is a statement about the code that
exists today, not a roadmap. This tool enforces the rules that make such a statement trustworthy:

* every backend answers **every** feature (no silent gap: a missing entry is an error),
* a state is one of `supported`, `conditional`, `unsupported`, `unknown`,
* `conditional` carries at least one human-readable condition,
* `supported`/`conditional` carries evidence, and every evidence path exists in the repo,
* no backend may claim to read the unified project or execute a graph until an adapter exists
  (that is the phase-0 gate in docs/editor-architecture.md; the guard is meant to be removed
  together with the adapter, not before).

This says nothing about whether a feature works. It says whether the project is honest about it.

Exit codes: 0 manifest is consistent, 1 it contradicts itself or the tree, 2 unreadable/invalid JSON.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "medo-motion" / "schema" / "backend-capabilities.json"
BACKENDS = ("P", "K", "R", "Hybrid")
STATES = ("supported", "conditional", "unsupported", "unknown")
FEATURE_ID = re.compile(r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$")
# Features nothing can do before the render-backend contract is implemented.
UNBACKED = ("project.read", "graph.execute")


def _no_duplicates(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f"duplicate JSON key {key!r}")
        obj[key] = value
    return obj


def load(path: Path = MANIFEST):
    text = path.read_text(encoding="utf-8")
    return json.loads(text, object_pairs_hook=_no_duplicates,
                      parse_constant=lambda value: (_ for _ in ()).throw(
                          ValueError(f"invalid constant {value}")))


def _evidence_ok(value: str) -> bool:
    candidate = Path(value)
    if candidate.is_absolute() or ".." in candidate.parts or "\\" in value:
        return False
    return (ROOT / candidate).is_file()


def validate(manifest, root: Path = ROOT) -> list[str]:
    """Return diagnostics; an empty list means the manifest and the tree agree."""
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["M00 $: expected an object"]
    expected = {"manifestVersion", "note", "features", "backends"}
    for key in sorted(set(manifest) - expected):
        errors.append(f"M00 $.{key}: unknown top-level field")
    for key in sorted(expected - {"note"} - set(manifest)):
        errors.append(f"M00 $.{key}: required")
    if errors:
        return errors
    if manifest["manifestVersion"] != 1:
        errors.append("M00 $.manifestVersion: only version 1 is defined")
    if not isinstance(manifest.get("note"), str) or not manifest["note"].strip():
        errors.append("M00 $.note: nonempty string required")

    features = manifest["features"]
    if not isinstance(features, dict) or not features:
        return errors + ["M01 $.features: nonempty object of id -> title"]
    for fid, title in features.items():
        if not FEATURE_ID.match(fid):
            errors.append(f"M01 $.features[{fid!r}]: invalid feature id")
        if not isinstance(title, str) or not title.strip():
            errors.append(f"M01 $.features[{fid!r}]: nonempty title required")

    backends = manifest["backends"]
    if not isinstance(backends, dict):
        return errors + ["M02 $.backends: object expected"]
    if set(backends) != set(BACKENDS):
        errors.append(f"M02 $.backends: expected exactly {list(BACKENDS)}, got {sorted(backends)}")

    for backend, body in backends.items():
        where = f"$.backends.{backend}"
        if not isinstance(body, dict) or set(body) != {"features"}:
            errors.append(f"M02 {where}: expected only a `features` object")
            continue
        declared = body["features"]
        if not isinstance(declared, dict):
            errors.append(f"M03 {where}.features: object expected")
            continue
        missing = sorted(set(features) - set(declared))
        extra = sorted(set(declared) - set(features))
        if missing:
            errors.append(f"M03 {where}: no state for {missing} (a gap is not 'unknown', say it)")
        if extra:
            errors.append(f"M03 {where}: states for undeclared features {extra}")
        for fid, entry in declared.items():
            loc = f"{where}.features.{fid}"
            if not isinstance(entry, dict):
                errors.append(f"M04 {loc}: object expected")
                continue
            unknown = set(entry) - {"version", "state", "conditions", "evidence"}
            if unknown:
                errors.append(f"M04 {loc}: unknown fields {sorted(unknown)}")
            version = entry.get("version")
            if isinstance(version, bool) or not isinstance(version, int) or version < 1:
                errors.append(f"M04 {loc}.version: positive integer required")
            state = entry.get("state")
            if state not in STATES:
                errors.append(f"M04 {loc}.state: expected one of {list(STATES)}")
                continue
            conditions = entry.get("conditions", [])
            if not isinstance(conditions, list) or any(
                    not isinstance(item, str) or not item.strip() for item in conditions):
                errors.append(f"M04 {loc}.conditions: list of nonempty strings expected")
                conditions = []
            evidence = entry.get("evidence", [])
            if not isinstance(evidence, list) or any(
                    not isinstance(item, str) or not item.strip() for item in evidence):
                errors.append(f"M04 {loc}.evidence: list of nonempty paths expected")
                evidence = []
            if state == "conditional" and not conditions:
                errors.append(f"M04 {loc}.conditions: conditional needs at least one condition")
            if state in ("supported", "conditional") and not evidence:
                errors.append(f"M04 {loc}.evidence: {state} needs evidence")
            if state in ("unsupported", "unknown") and conditions:
                errors.append(f"M04 {loc}.conditions: only conditional entries carry conditions")
            for item in evidence:
                if not _evidence_ok(item):
                    errors.append(f"M05 {loc}.evidence: {item!r} is not an existing repo-relative file")
            if fid in UNBACKED and state in ("supported", "conditional"):
                errors.append(
                    f"M06 {loc}: {fid} cannot be claimed before an adapter exists "
                    "(docs/editor-architecture.md §11); implement it or lower the state")
    return errors


def matrix(manifest) -> dict[str, dict[str, str]]:
    """Backend -> feature -> state, for callers that only need the summary."""
    return {backend: {fid: entry["state"] for fid, entry in body["features"].items()}
            for backend, body in manifest["backends"].items()}


def _print_matrix(manifest) -> None:
    features = list(manifest["features"])
    width = max(len(name) for name in features)
    print(f"{'feature':<{width}}  " + "  ".join(f"{b:^12}" for b in BACKENDS))
    for fid in features:
        row = "  ".join(f"{manifest['backends'][b]['features'][fid]['state']:^12}" for b in BACKENDS)
        print(f"{fid:<{width}}  {row}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the manifest contradicts itself or the tree (default)")
    parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
    parser.add_argument("--matrix", action="store_true", help="print only the state table")
    parser.add_argument("--manifest", type=Path, default=MANIFEST, help="alternate manifest path")
    args = parser.parse_args(argv)
    try:
        manifest = load(args.manifest)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Cannot read capabilities manifest: {exc}", file=sys.stderr)
        return 2
    errors = validate(manifest)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    elif args.matrix:
        _print_matrix(manifest)
    else:
        print(f"OK: {len(manifest['features'])} features declared for "
              f"{', '.join(BACKENDS)}; every claim has evidence in the tree.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
