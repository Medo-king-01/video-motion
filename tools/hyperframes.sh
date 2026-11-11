#!/usr/bin/env bash
# Run the isolated HyperFrames CLI (tools/optional-hyperframes) with the studio's own
# Chromium and FFmpeg, telemetry off. Experimental HTML-to-video path only — it is not
# a fourth engine; P/K/R stay the engines of record (docs/hyperframes-fit.md).
#
#   bash tools/setup_extras.sh hyperframes        # once
#   bash /path/to/repo/tools/hyperframes.sh init demo --example blank --resolution portrait --non-interactive
#   cd demo && bash /path/to/repo/tools/hyperframes.sh render -o out.mp4 --workers 1
#
# Runs in the caller's directory. Compositions must load GSAP and fonts from local files
# when the CDN is unreachable, and must take colours from medo-motion/brand/brand.json.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/tools/optional-hyperframes/node_modules/.bin/hyperframes"
[ -x "$BIN" ] || { echo 'HyperFrames is not installed: bash tools/setup_extras.sh hyperframes' >&2; exit 1; }
export PATH="$ROOT/tools/bin:$PATH"
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null || {
  echo 'ffmpeg/ffprobe missing: bash tools/setup.sh' >&2; exit 1;
}
# Studio Chromium (same one engine K uses) plus the shared libraries it needs.
eval "$(node "$ROOT/tools/chromium.mjs" --env)"
export HYPERFRAMES_BROWSER_PATH="${HYPERFRAMES_BROWSER_PATH:-$MEDO_CHROMIUM}"
FFMPEG_BIN="$(command -v ffmpeg)"
export HYPERFRAMES_FFMPEG_PATH="${HYPERFRAMES_FFMPEG_PATH:-$(readlink -f "$FFMPEG_BIN" 2>/dev/null || echo "$FFMPEG_BIN")}"
export HYPERFRAMES_FFPROBE_PATH="${HYPERFRAMES_FFPROBE_PATH:-$(command -v ffprobe)}"
# No usage telemetry and no auto-installed third-party agent skills.
export HYPERFRAMES_NO_TELEMETRY=1 DO_NOT_TRACK=1 HYPERFRAMES_SKIP_SKILLS=1
exec "$BIN" "$@"
