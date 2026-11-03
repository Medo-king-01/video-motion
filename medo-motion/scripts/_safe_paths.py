"""Conservative path checks for local, single-user file-writing commands.

Reject existing symlink components, including dangling links. These preflight
checks do not provide a sandbox against concurrent hostile filesystem changes.
"""
from pathlib import Path
import os


def checked_path(path, *, within=None, tree=False):
    path = Path(os.path.abspath(path))
    for part in (*reversed(path.parents), path):
        if part.is_symlink():
            raise ValueError(f'refusing symlink path: {part}')
    resolved = path.resolve()
    if within is not None and not resolved.is_relative_to(Path(within).resolve()):
        raise ValueError(f'path escapes destination: {path}')
    if tree and path.is_dir():
        for parent, dirs, files in os.walk(path, followlinks=False):
            for name in dirs + files:
                entry = Path(parent) / name
                if entry.is_symlink():
                    raise ValueError(f'refusing symlink path: {entry}')
    return path
