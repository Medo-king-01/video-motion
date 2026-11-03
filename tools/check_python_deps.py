#!/usr/bin/env python3
"""Read-only check of the reviewed render/development dependency baseline."""
from __future__ import annotations

import importlib.metadata
import sys
from pathlib import Path

try:
    from packaging.requirements import Requirement
except ModuleNotFoundError as error:
    raise SystemExit("Missing packaging; run setup without --check inside a venv") from error

RUNTIME = {'pillow', 'numpy', 'scipy', 'opencv-python-headless', 'imageio-ffmpeg',
           'av', 'uharfbuzz', 'freetype-py', 'packaging'}


def main():
    wanted = RUNTIME | ({'pytest', 'ruff'} if '--dev' in sys.argv else set())
    errors = []
    for line in Path(__file__).with_name('constraints.txt').read_text().splitlines():
        if '==' not in line:
            continue
        requirement = Requirement(line)
        if requirement.marker and not requirement.marker.evaluate():
            continue
        name = requirement.name
        version = next(iter(requirement.specifier)).version
        if name not in wanted:
            continue
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = 'missing'
        if actual != version:
            errors.append(f'{name}: {actual}; expected {version}')
    print('\n'.join(errors) if errors else 'Python baseline OK')
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
