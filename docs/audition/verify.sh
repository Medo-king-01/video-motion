#!/usr/bin/env bash
# Verify that the audition decisions were actually left un-applied.
#
# Run from the repo root:  bash docs/audition/verify.sh
# Exit 0 = the engine and presets are untouched; exit 1 = something drifted.
#
# This exists because "we decided not to change it" is a claim that rots: the next person cannot tell
# a deliberate -3.0 from a leftover. These five checks make the claim executable.
set -uo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../.." || exit 1

ENGINE="medo-motion/templates/procedural-reels"
PRESETS="medo-motion/motion/music-presets.json"
BASE="${BASE_COMMIT:-82d8c3e}"     # the commit that delivered the audio engine
fail=0

check() {  # check <label> <expected> <actual>
  if [ "$2" = "$3" ]; then
    printf '  PASS  %-56s %s\n' "$1" "$3"
  else
    printf '  FAIL  %-56s got %s, wanted %s\n' "$1" "$3" "$2"
    fail=1
  fi
}

echo "verify: audition decisions not applied (base $BASE)"
echo

# 1. The default bed level is still -3.0 dB.
got=$(grep -c 'level_db", -3\.0' "$ENGINE/audio_mix.py")
check "audio_mix.py default level_db is -3.0" "1" "$got"

# 2. No -5 dB level leaked into the engine, presets or tools.
got=$(grep -rl 'level_db"[[:space:]]*:[[:space:]]*-5' "$ENGINE" medo-motion/motion tools 2>/dev/null | wc -l | tr -d ' ')
check "no 'level_db: -5' anywhere in engine/presets/tools" "0" "$got"

# 3. from_storyboard() does not set level_db (generated sheets inherit the default).
got=$(sed -n '/def from_storyboard/,/^def /p' "$ENGINE/audio_mix.py" | grep -c 'level_db')
check "from_storyboard() does not set level_db" "0" "$got"

# 4. The presets are byte-identical to the delivered engine.
if git diff --quiet "$BASE" -- "$PRESETS"; then got=identical; else got=CHANGED; fi
check "music-presets.json identical to $BASE" "identical" "$got"

# 5. Plan B's layer values never reached the preset file (numeric compare, see check_plan_b.py).
if ! python3 docs/audition/check_plan_b.py; then fail=1; fi

echo
if [ "$fail" -eq 0 ]; then
  echo "OK: -3.0 dB is the default, Plan B is not applied, presets untouched."
else
  echo "DRIFT: see the FAIL lines above."
fi
exit "$fail"
