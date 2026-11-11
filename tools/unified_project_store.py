"""Explicit local project storage with cooperative conflict detection.

Callers keep revisions from load/create/save. Files with unsupported data are never
rewritten. This is not an autosave service and does not secure an untrusted directory.
"""
from __future__ import annotations

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
