#!/usr/bin/env python3
"""Inspect local unified-project assets without modifying files or executing a renderer.

The project directory and media must be trusted: ffprobe is a native decoder and this
module is not a sandbox, nor protection against concurrent malicious filesystem changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

from unified_project_edit import _checked
from unified_project_store import load


def _local_file(root, uri):
    """Resolve a previously validated URI without following symlink components."""
    base = Path(root).resolve(strict=True)
    if not base.is_dir():
        raise ValueError("Project root is not a directory")
    path = base
    for component in uri.split("/"):
        path = path / component
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise ValueError("Asset paths may not contain symlinks")
    if not stat.S_ISREG(path.stat().st_mode):
        raise ValueError("Asset is not a regular file")
    return path


def _hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def inspect_assets(project, root, *, probe=False, ffprobe="ffprobe", timeout=30):
    """Return one report per asset in project order; never mutate project or its files.

    By default only check existence, path and content hash. Probe only matching files.
    An ffprobe error is per-asset and prevents the report from claiming success.
    """
    _checked(project)
    reports = []
    for asset in project["assets"]:
        result = {"id": asset["id"], "uri": asset["uri"], "status": "ok"}
        reports.append(result)
        try:
            path = _local_file(root, asset["uri"])
            result["sha256"] = _hash_file(path)
        except FileNotFoundError:
            result.update(status="missing", error="Asset or project directory not found")
            continue
        except (OSError, ValueError) as exc:
            result.update(status="error", error=str(exc))
            continue
        if result["sha256"] != asset["sha256"]:
            result.update(status="changed", error="SHA-256 does not match the project")
            continue
        if not probe:
            continue
        try:
            response = subprocess.run(
                [os.fspath(ffprobe), "-v", "error", "-show_format", "-show_streams", "-of", "json", os.fspath(path)],
                capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, check=False,
            )
            if response.returncode:
                raise ValueError(f"ffprobe exited {response.returncode}: {response.stderr.strip()[:500]}")
            metadata = json.loads(response.stdout)
            if not isinstance(metadata, dict) or not isinstance(metadata.get("streams"), list):
                raise ValueError("ffprobe output has no stream list")
            # Do not claim stream selection or reconcile duration; expose raw metadata for review.
            result["probe"] = metadata
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            result.update(status="probe_error", error=str(exc))
    return reports


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="path to project JSON; assets resolve relative to its parent")
    parser.add_argument("--probe", action="store_true", help="also inspect verified assets with ffprobe")
    parser.add_argument("--ffprobe", default="ffprobe", help="local ffprobe executable")
    args = parser.parse_args(argv)
    try:
        project, _ = load(args.project)
        reports = inspect_assets(project, args.project.parent, probe=args.probe, ffprobe=args.ffprobe)
    except (OSError, ValueError, UnicodeError) as exc:
        print(f"Cannot inspect project: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"assets": reports}, ensure_ascii=False, indent=2))
    return 0 if all(item["status"] == "ok" for item in reports) else 1


def import_asset(project, root, source, *, asset_id, kind, uri, duration=None):
    """Copy a trusted source to a new project-relative path and return a new project.

    The destination parent must exist. Never overwrite files or reuse an asset URI.
    Temporal duration is supplied by the caller in project ticks, not inferred here.
    Project persistence is separate: a crash or failed save can leave an orphan copy.
    """
    import tempfile
    from copy import deepcopy

    _checked(project)
    asset = {"id": asset_id, "kind": kind, "uri": uri, "sha256": "0" * 64}
    if duration is not None:
        asset["duration"] = duration
    result = deepcopy(project)
    if any(a["uri"] == uri for a in result["assets"]):
        raise ValueError("Asset URI is already registered")
    result["assets"].append(asset)
    _checked(result)  # validates ID, URI and kind before any destination writes
    root = Path(root).resolve(strict=True)
    parent = root
    components = uri.split("/")
    for component in components[:-1]:
        parent = parent / component
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
            raise ValueError("Asset parent must be a directory without symlinks")
    destination = parent / components[-1]
    src = Path(source)
    info = src.lstat()
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise ValueError("Source must be a regular file, not a symlink")
    temporary = None
    try:
        digest = hashlib.sha256()
        with src.open("rb") as input_file, tempfile.NamedTemporaryFile(
            mode="wb", dir=parent, prefix=".import-", delete=False
        ) as output_file:
            temporary = output_file.name
            for block in iter(lambda: input_file.read(1024 * 1024), b""):
                digest.update(block)
                output_file.write(block)
            output_file.flush()
            os.fsync(output_file.fileno())
        asset["sha256"] = digest.hexdigest()
        _checked(result)
        # A hard link creates the final name atomically and fails if anything exists there.
        # Some filesystems do not support hard links; report the error rather than overwrite.
        os.link(temporary, destination)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)
    return result


if __name__ == "__main__":
    raise SystemExit(main())
