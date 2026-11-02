#!/usr/bin/env bash
# medo-motion — one-shot environment setup (Linux/macOS).
# Idempotent: safe to re-run. Installs only what is missing.
#
#   bash tools/setup.sh            # install + verify
#   bash tools/setup.sh --check    # verify only, install nothing
#
# Windows: use WSL, or PowerShell with the same steps commented below.
set -u
cd "$(dirname "$0")/.." || exit 1
ROOT="$PWD"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1
say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
ok()  { printf '  \033[32mOK\033[0m   %s\n' "$*"; }
bad() { printf '  \033[31mMISS\033[0m %s\n' "$*"; }

PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "python3 not found"; exit 1; }

# ---------------------------------------------------------------- python deps
say "Python packages (tools/requirements.txt)"
REQ="$ROOT/tools/requirements.txt"
NEED=$($PY - <<'EOF'
import importlib
need=[]
for mod,pkg in [('PIL','pillow'),('numpy','numpy'),('scipy','scipy'),('cv2','opencv-python-headless'),
                ('imageio_ffmpeg','imageio-ffmpeg'),('av','av'),('uharfbuzz','uharfbuzz'),('freetype','freetype-py')]:
    try: importlib.import_module(mod)
    except Exception: need.append(pkg)
print(' '.join(need))
EOF
)
if [ -n "$NEED" ]; then
  if [ "$CHECK_ONLY" = "1" ]; then bad "missing: $NEED"; else
    echo "  installing: $NEED"
    FLAGS=""
    if [ -f "$REQ" ]; then TARGET="-r $REQ"; else TARGET="$NEED"; fi
    $PY -m pip install --quiet --no-input $TARGET 2>/dev/null \
      || $PY -m pip install --quiet --no-input --break-system-packages $TARGET \
      || echo "  pip failed — install manually: pip install -r tools/requirements.txt"
  fi
else ok "all python packages present"; fi

# ---------------------------------------------------------------- ffmpeg / ffprobe
say "FFmpeg"
mkdir -p tools/bin
if command -v ffmpeg >/dev/null 2>&1; then
  ok "ffmpeg on PATH ($(ffmpeg -version 2>/dev/null | head -1))"
elif [ "$CHECK_ONLY" = "0" ]; then
  FF=$($PY -c "import imageio_ffmpeg,sys;print(imageio_ffmpeg.get_ffmpeg_exe())" 2>/dev/null)
  if [ -n "${FF:-}" ] && [ -x "$FF" ]; then
    ln -sf "$FF" tools/bin/ffmpeg
    ok "ffmpeg linked at tools/bin/ffmpeg (imageio-ffmpeg)"
    mkdir -p "$HOME/.local/bin" && ln -sf "$ROOT/tools/bin/ffmpeg" "$HOME/.local/bin/ffmpeg" 2>/dev/null \
      && ok "also linked into ~/.local/bin"
  else bad "ffmpeg missing and imageio-ffmpeg unavailable"; fi
else bad "ffmpeg not on PATH"; fi

# ffprobe: many static builds ship ffmpeg only -> ffprobe-compatible shim
if command -v ffprobe >/dev/null 2>&1; then
  ok "ffprobe on PATH"
elif [ "$CHECK_ONLY" = "0" ]; then
  printf '#!/bin/sh\nexec %s %s/tools/ffprobe_shim.py "$@"\n' "$PY" "$ROOT" > tools/bin/ffprobe
  chmod +x tools/bin/ffprobe
  mkdir -p "$HOME/.local/bin" && ln -sf "$ROOT/tools/bin/ffprobe" "$HOME/.local/bin/ffprobe" 2>/dev/null
  ok "ffprobe shim installed (tools/bin/ffprobe)"
else bad "ffprobe missing (shim not installed in --check mode)"; fi

# ---------------------------------------------------------------- node toolkit
say "Node toolkit + Chromium"
if ! command -v npm >/dev/null 2>&1; then
  bad "npm not found (install Node 20.11+ — tools/toolkit/package-lock.json requires it)"
elif [ "$CHECK_ONLY" = "1" ]; then
  [ -d tools/toolkit/node_modules/playwright-core ] && ok "toolkit installed" || bad "toolkit not installed"
else
  ( cd tools/toolkit && npm install --silent )
  if [ -d tools/toolkit/node_modules/playwright-core ]; then ok "playwright-core + chromium package installed"; else bad "npm install failed"; fi
fi

# ---------------------------------------------------------------- fonts (21 free families, OFL)
say "Type system (14 families, SIL OFL 1.1)"
if [ -f assets/fonts/fonts.json ] && [ "$(ls -1 assets/fonts/*/*.ttf 2>/dev/null | wc -l)" -ge 20 ]; then
  ok "$(ls -1d assets/fonts/*/ | wc -l) families already in assets/fonts (docs/fonts.md)"
elif [ "$CHECK_ONLY" = "0" ]; then
  # Check the installer's OWN exit code — piping through tail without pipefail would
  # report tail's success even when the install failed.
  if FONTS_LOG=$(python3 tools/fonts_install.py 2>&1); then
    printf '%s\n' "$FONTS_LOG" | tail -1
    if [ -f assets/fonts/fonts.json ]; then
      ok "type system installed from the OFL npm packages (manifest verified)"
    else
      bad "fonts_install.py exited 0 but assets/fonts/fonts.json is missing"
    fi
  else
    printf '%s\n' "$FONTS_LOG" | tail -5
    bad "could not fetch the fonts (run: python3 tools/fonts_install.py)"
  fi
else bad "fonts missing in assets/fonts (run: make fonts)"; fi

# ---------------------------------------------------------------- verify
say "Verification"
$PY tools/doctor.py || true

cat <<EOS

  Add to your shell profile if the tools are not on PATH:
      export PATH="$ROOT/tools/bin:\$PATH"
  For the Canvas engine, export the bundled Chromium first:
      eval "\$(node $ROOT/tools/chromium.mjs --env)"
EOS
