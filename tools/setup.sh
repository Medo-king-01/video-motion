#!/usr/bin/env bash
# Linux/macOS/WSL. Python >=3.10 and Node >=20.11 are prerequisites.
# --check performs read-only inventory (no installs, mkdir, browser, or doctor).
# --dev also installs/checks pytest + Ruff. Use a virtual environment.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
export PATH="$ROOT/tools/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
CHECK_ONLY=0
DEV=0
for arg in "$@"; do
  case "$arg" in
    --check) CHECK_ONLY=1 ;;
    --dev) DEV=1 ;;
    *) echo "Usage: bash tools/setup.sh [--check] [--dev]" >&2; exit 2 ;;
  esac
done
PY=${PY:-python3}
command -v "$PY" >/dev/null || { echo 'Install Python >=3.10: https://www.python.org/downloads/' >&2; exit 1; }
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else "Python >=3.10 required")'
command -v node >/dev/null && command -v npm >/dev/null || {
  echo 'Install Node >=20.11 (includes npm): https://nodejs.org/en/download' >&2; exit 1;
}
node -e 'const [a,b]=process.versions.node.split(".").map(Number); if(a<20 || (a===20 && b<11)) process.exit(1)' || {
  echo 'Node >=20.11 required' >&2; exit 1;
}
REQ=tools/requirements.txt
EXTRA=()
if [ "$DEV" = 1 ]; then REQ=tools/requirements-dev.txt; EXTRA=(--dev); fi
if [ "$CHECK_ONLY" = 1 ]; then
  STATUS=0
  "$PY" tools/check_python_deps.py "${EXTRA[@]}" || STATUS=1
  "$PY" -m pip check || STATUS=1
  command -v ffmpeg >/dev/null || { echo 'Missing ffmpeg'; STATUS=1; }
  command -v ffprobe >/dev/null || { echo 'Missing ffprobe'; STATUS=1; }
  [ -d tools/toolkit/node_modules/playwright-core ] && [ -d tools/toolkit/node_modules/@sparticuz/chromium ] || {
    echo 'Missing Node toolkit (run setup without --check)'; STATUS=1;
  }
  "$PY" tools/fonts_install.py --check || STATUS=1
  echo 'Inventory only; run python3 tools/doctor.py for functional readiness (browser/audio smoke checks).'
  exit "$STATUS"
fi
# Fail honestly: never suppress pip/npm/font/doctor errors or mutate system Python.
"$PY" -m pip install --no-input -r "$REQ"
"$PY" -m pip check
(cd tools/toolkit && npm ci --no-audit --no-fund)
mkdir -p tools/bin
if ! command -v ffmpeg >/dev/null; then
  FF=$("$PY" -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')
  ln -sf "$FF" tools/bin/ffmpeg
fi
if ! command -v ffprobe >/dev/null; then
  printf '#!/bin/sh\nexec "%s" "%s/tools/ffprobe_shim.py" "$@"\n' "$(command -v "$PY")" "$ROOT" > tools/bin/ffprobe
  chmod +x tools/bin/ffprobe
fi
"$PY" tools/fonts_install.py --check || "$PY" tools/fonts_install.py
"$PY" tools/doctor.py
printf '\nFor future shells: export PATH="%s/tools/bin:$PATH"\n' "$ROOT"
