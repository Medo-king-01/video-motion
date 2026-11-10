"""Standalone media resolution for the P engine.

The P engine is a self-contained template: it is copied flat into projects/<slug>
and also runs from a throwaway temp dir in tools/selftest.py. Its runtime modules
must therefore never import the repository's tools/lib by a fixed relative depth.

Precedence (same order as tools/lib/media_bin.py): $<NAME>_BIN -> the nearest
tools/bin/<name> shim discovered by walking up from `start` -> PATH.
Never raises: unresolvable binaries come back as None.
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path


def find_media(name: str, start: Path | None = None) -> str | None:
    env = os.environ.get(f"{name.upper()}_BIN")
    candidates: list[str] = []
    if env:
        candidates.append(env)
    here = (start if start is not None else Path(__file__)).resolve()
    for parent in here.parents:
        candidates.append(str(parent / "tools" / "bin" / name))
    candidates.append(name)  # PATH
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
        path = Path(candidate)
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None
