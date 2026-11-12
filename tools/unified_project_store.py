"""Explicit local project storage with cooperative conflict detection and recovery.

Callers keep revisions from load/create/save. Files with unsupported data are never
rewritten. Autosave writes a *sibling* `<project>.autosave.json` that records the
revision it was based on; `recover()` reports whether that base is still current, so a
crash never silently overwrites work. Nothing here secures an untrusted directory.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path

from unified_project_check import _unique_pairs
from unified_project_edit import _checked


class ConflictError(ValueError):
    """File changed or a cooperative writer currently holds the lock."""


def _revision(data):
    return hashlib.sha256(data).hexdigest()


def _read(path):
    if path.is_symlink():
        raise ValueError("Project file must not be a symlink")
    return path.read_bytes()


def _decode(data):
    def reject_constant(value):
        raise ValueError(f"Invalid JSON constant: {value}")

    project = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs, parse_constant=reject_constant)
    _checked(project)
    return project


def load(path):
    """Load a validated snapshot and the SHA-256 revision of its exact bytes."""
    data = _read(Path(path))
    return _decode(data), _revision(data)


@contextmanager
def _lock(path):
    lock_path = path.with_name(path.name + ".lock")
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise ConflictError("Project is locked by another writer; check stale lock manually") from exc
    try:
        os.close(fd)
        yield
    finally:
        lock_path.unlink()


def save(path, project, expected_revision=None):
    """Atomically create or replace after a revision check under a cooperative lock.

    None means create-only. For an existing file pass the exact revision from load/save;
    missing, changed or symlink targets fail without replacing them. Temp files live in
    the same directory. A crash can leave a lock; it requires manual inspection/removal.
    """
    _checked(project)
    path = Path(path)
    payload = (json.dumps(project, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    with _lock(path):
        if path.is_symlink():
            raise ValueError("Project file must not be a symlink")
        if expected_revision is None:
            if path.exists():
                raise ConflictError("Project already exists; load before overwriting")
        else:
            try:
                current = _read(path)
            except FileNotFoundError as exc:
                raise ConflictError("Project no longer exists") from exc
            if _revision(current) != expected_revision:
                raise ConflictError("Project changed since it was loaded")
            _decode(current)  # Never overwrite an unknown or malformed version, even with its hash.
        tmp_name = None
        try:
            with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".unified-", delete=False) as tmp:
                tmp_name = tmp.name
                tmp.write(payload)
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_name, path)
            tmp_name = None
        finally:
            if tmp_name is not None:
                Path(tmp_name).unlink(missing_ok=True)
    return _revision(payload)


AUTOSAVE_SUFFIX = ".autosave.json"


def _autosave_path(path):
    path = Path(path)
    return path.with_name(path.name + AUTOSAVE_SUFFIX)


def _write_atomic(path, payload):
    tmp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, prefix=".autosave-", delete=False) as tmp:
            tmp_name = tmp.name
            tmp.write(payload)
            tmp.flush()
            os.fsync(tmp.fileno())
        os.replace(tmp_name, path)
        tmp_name = None
    finally:
        if tmp_name is not None:
            Path(tmp_name).unlink(missing_ok=True)


def autosave(path, project, *, base_revision=None, now=None):
    """Write the sibling autosave file; return the record written.

    The record keeps the project untouched and remembers which on-disk revision it grew
    from, so `recover()` can say whether the file is still the work it belongs to.
    """
    _checked(project)
    path = Path(path)
    stamp = (now or _dt.datetime.now(_dt.timezone.utc)).replace(microsecond=0).isoformat()
    record = {"savedAt": stamp, "baseRevision": base_revision, "project": project}
    payload = (json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    target = _autosave_path(path)
    if target.is_symlink():
        raise ValueError("Autosave target must not be a symlink")
    _write_atomic(target, payload)
    return record


def recover(path):
    """Return the autosave candidate, or None when there is nothing to recover.

    `stale` is True when the project on disk changed since the autosave was written: the
    candidate is still shown (never deleted) but must not overwrite the newer file.
    """
    path = Path(path)
    target = _autosave_path(path)
    if not target.exists():
        return None
    if target.is_symlink():
        raise ValueError("Autosave file must not be a symlink")
    raw = target.read_bytes()
    try:
        record = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except ValueError as exc:
        raise ValueError(f"Unreadable autosave: {exc}") from exc
    _checked(record["project"])
    current = None
    try:
        current = _revision(_read(path))
    except FileNotFoundError:
        current = None
    return {"savedAt": record["savedAt"], "baseRevision": record.get("baseRevision"),
            "project": record["project"], "bytes": len(raw),
            "stale": current is not None and record.get("baseRevision") != current,
            "projectMissing": current is None}


def discard_autosave(path):
    """Delete the autosave file (only after the work is safely saved)."""
    target = _autosave_path(path)
    existed = target.exists()
    target.unlink(missing_ok=True)
    return existed


def main(argv=None):
    import argparse

    parser = argparse.ArgumentParser(description="Autosave a unified project, or inspect/recover one.")
    parser.add_argument("project", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("autosave", help="write <project>.autosave.json from the current file")
    sub.add_parser("show", help="print the autosave record without touching the project")
    sub.add_parser("recover", help="write the autosave back over the project when it is not stale")
    sub.add_parser("discard", help="delete the autosave file")
    args = parser.parse_args(argv)

    if args.command == "autosave":
        project, revision = load(args.project)
        record = autosave(args.project, project, base_revision=revision)
        print(f"autosaved {record['savedAt']} -> {_autosave_path(args.project)}")
        return 0
    candidate = recover(args.project)
    if candidate is None:
        print("no autosave")
        return 1
    if args.command == "show":
        print(json.dumps({k: v for k, v in candidate.items() if k != "project"}, ensure_ascii=False))
        return 0
    if args.command == "discard":
        discard_autosave(args.project)
        print("autosave discarded")
        return 0
    if candidate["stale"]:
        print("refused: the project changed since this autosave; inspect both copies")
        return 1
    revision = None if candidate["projectMissing"] else _revision(_read(args.project))
    save(args.project, candidate["project"], expected_revision=revision)
    discard_autosave(args.project)
    print("recovered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
