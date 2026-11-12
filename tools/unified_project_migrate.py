#!/usr/bin/env python3
"""Migrate a unified project forward to the current schema version, non-destructively.

Two rules shape this tool:

* **Forward only.** Opening a *newer* project is refused with `M02`; guessing what a newer
  field means is how data gets lost quietly.
* **Nothing is dropped.** The migration only adds the fields the newer version requires
  (empty `transitions` on tracks before 1.2, nothing for 1.3), and the report names every
  element it touched. Validation runs before and after, so a project that was invalid
  stays invalid instead of being blessed by the migration.

Usage:
  python3 tools/unified_project_migrate.py project.json            # report only
  python3 tools/unified_project_migrate.py project.json --write    # write in place
  python3 tools/unified_project_migrate.py project.json --check    # exit 1 if not current
"""
from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402

CURRENT = "1.5"
KNOWN = ("1.0", "1.1", "1.2", "1.3", "1.4", "1.5")


class MigrationError(ValueError):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _order(version):
    return KNOWN.index(version)


def migrate(project):
    """Return (migrated project, report). The input is never mutated."""
    version = project.get("schemaVersion")
    if version not in KNOWN:
        raise MigrationError("M02", f"unknown schemaVersion {version!r}; expected one of {', '.join(KNOWN)}")
    if _order(version) > _order(CURRENT):
        raise MigrationError("M02", f"project is newer ({version}) than this tool ({CURRENT}); open it with a newer build")
    errors = validate(project)
    if errors:
        raise MigrationError("M01", "project is invalid before migration: " + "; ".join(errors))
    migrated = deepcopy(project)
    steps = []
    if _order(version) < _order("1.2"):
        added = 0
        for track in migrated["tracks"]:
            if "transitions" not in track:
                track["transitions"] = []
                added += 1
        steps.append({"step": "1.2", "change": "add empty transitions[] to every track", "tracks": added})
    if _order(version) < _order("1.3"):
        steps.append({"step": "1.3", "change": "keep the project as-is; 1.3 fields are optional",
                      "note": "speed/streams/texts stay absent until an editor adds them"})
    if _order(version) < _order("1.4"):
        steps.append({"step": "1.4", "change": "keep the project as-is; wrap/animation/wipe are optional",
                      "note": "text wrapping, word animation and wipe transitions are opt-in"})
    if _order(version) < _order("1.5"):
        steps.append({"step": "1.5", "change": "keep the project as-is; runs and letter animation are optional",
                      "note": "styled runs and per-letter animation are opt-in"})
    migrated["schemaVersion"] = CURRENT
    errors = validate(migrated)
    if errors:
        raise MigrationError("M03", "migrated project does not validate: " + "; ".join(errors))
    report = {
        "from": version, "to": CURRENT, "changed": version != CURRENT,
        "steps": steps,
        "counts": {
            "tracks": len(migrated["tracks"]),
            "clips": sum(len(track["clips"]) for track in migrated["tracks"]),
            "transitions": sum(len(track.get("transitions") or []) for track in migrated["tracks"]),
            "texts": len(migrated.get("texts") or []),
        },
    }
    return migrated, report


def _write(path, project):
    path = Path(path)
    payload = (json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    tmp = path.with_name(path.name + ".migrating")
    tmp.write_bytes(payload)
    tmp.replace(path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", type=Path)
    parser.add_argument("--write", action="store_true", help="write the migrated project back")
    parser.add_argument("--check", action="store_true", help="exit 1 when the project is not current")
    parser.add_argument("--json", action="store_true", dest="as_json", help="print the report as JSON")
    args = parser.parse_args(argv)

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
        migrated, report = migrate(project)
    except MigrationError as exc:
        print(exc, file=sys.stderr)
        return 1
    except (OSError, json.JSONDecodeError) as exc:
        print(f"M00 unreadable project: {exc}", file=sys.stderr)
        return 2
    if args.check:
        print(f"{report['from']} (current is {CURRENT})")
        return 0 if not report["changed"] else 1
    if args.as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"{report['from']} -> {report['to']}: {'migrated' if report['changed'] else 'already current'}")
        for step in report["steps"]:
            print(f"  {step['step']}: {step['change']}")
    if args.write and report["changed"]:
        _write(args.project, migrated)
        print(f"written {args.project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
