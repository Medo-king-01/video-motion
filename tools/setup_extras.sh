#!/usr/bin/env bash
# Optional free tools on top of `bash tools/setup.sh` (which already provides FFmpeg).
# Nothing here is needed by engines P/K/R; install only what you will use.
#
#   bash tools/setup_extras.sh whisper       # faster-whisper + local Whisper-small model (~480 MB)
#   bash tools/setup_extras.sh demucs        # Demucs stem separation (pulls PyTorch, several GB)
#   bash tools/setup_extras.sh hyperframes   # HyperFrames CLI 0.9.9, isolated (Node >= 22)
#   bash tools/setup_extras.sh all
#   bash tools/setup_extras.sh --check       # read-only: report what is installed
#
# Use the same virtual environment as tools/setup.sh (PY=/path/to/venv/bin/python).
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
export PATH="$ROOT/tools/bin:$PATH"
export PYTHONDONTWRITEBYTECODE=1
PY=${PY:-python3}
MODEL=${WHISPER_MODEL_DIR:-.cache/whisper-small-ct2-int8}
HF_DIR=tools/optional-hyperframes

usage() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//' >&2; exit 2; }

has_py() { "$PY" -c "import $1" >/dev/null 2>&1; }

check() {
  local status=0
  if command -v ffmpeg >/dev/null; then echo "ffmpeg       OK       $(ffmpeg -version | head -n1 | cut -d' ' -f1-3)"
  else echo 'ffmpeg       MISSING  bash tools/setup.sh'; status=1; fi
  if has_py faster_whisper && [ -f "$MODEL/model.bin" ]; then echo "whisper      OK       faster-whisper + $MODEL"
  elif has_py faster_whisper; then echo "whisper      PARTIAL  model missing: $PY tools/whisper_fetch.py --out $MODEL"; status=1
  else echo 'whisper      MISSING  bash tools/setup_extras.sh whisper'; status=1; fi
  if has_py demucs && has_py soundfile; then echo "demucs       OK       $("$PY" -c 'import demucs; print(demucs.__version__)') (weights download on first use)"
  else echo 'demucs       MISSING  bash tools/setup_extras.sh demucs'; status=1; fi
  if [ -x "$HF_DIR/node_modules/.bin/hyperframes" ]; then echo "hyperframes  OK       $("$HF_DIR/node_modules/.bin/hyperframes" --version)"
  else echo 'hyperframes  MISSING  bash tools/setup_extras.sh hyperframes'; status=1; fi
  return "$status"
}

install_whisper() {
  "$PY" -m pip install --no-input -r tools/requirements-align.txt
  [ -f "$MODEL/model.bin" ] || "$PY" tools/whisper_fetch.py --out "$MODEL"
}

install_demucs() {
  "$PY" -m pip install --no-input -r tools/requirements-stems.txt
}

install_hyperframes() {
  node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 22 ? 0 : 1)' || {
    echo 'HyperFrames needs Node >= 22 (the studio itself only needs >= 20.11).' >&2; exit 1;
  }
  # --ignore-scripts: no package install hooks run; the lockfile pins all 78 packages.
  npm ci --prefix "$HF_DIR" --ignore-scripts --no-audit --no-fund
}

[ "$#" -ge 1 ] || usage
for arg in "$@"; do
  case "$arg" in
    --check) check; exit $? ;;
    whisper) install_whisper ;;
    demucs) install_demucs ;;
    hyperframes) install_hyperframes ;;
    all) install_whisper; install_demucs; install_hyperframes ;;
    *) usage ;;
  esac
done
"$PY" -m pip check
check
