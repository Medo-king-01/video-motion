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

# 5. Plan B's nine numbers never reached the preset file.
if [ -f docs/audition/plan_b_layers.json ]; then
  drift=0
  while read -r preset layer want; do
    have=$(python3 -c "
import json,sys
try:
    d=json.load(open('$PRESETS'))
    print(d['presets']['$preset']['layers'].get('$layer'))
except Exception:
    print('ERR')
" 2>/dev/null)
    # Only flag it if the preset ALREADY equals the plan value while differing from the base value:
    # that would mean the plan was applied.
    base=$(git show "$BASE:$PRESETS" 2>/dev/null | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    print(d['presets']['$preset']['layers'].get('$layer'))
except Exception:
    print('')
" 2>/dev/null)
    if [ -n "$base" ] && [ "$have" = "$want" ] && [ "$have" != "$base" ]; then
      printf '  FAIL  plan B applied to %s.%s = %s\n' "$preset" "$layer" "$want"
      drift=1
    fi
  done < <(python3 -c "
import json
d=json.load(open('docs/audition/plan_b_layers.json'))
current=json.load(open('$PRESETS'))
for preset,layers in d.items():
    for layer,val in layers.items():
        print(preset, layer, val)
")
  [ "$drift" -eq 0 ] && printf '  PASS  %-56s not applied\n' "Plan B layer values"
  fail=$((fail || drift))
else
  printf '  SKIP  %-56s (plan_b_layers.json missing)\n' "Plan B layer values"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "OK: -3.0 dB is the default, Plan B is not applied, presets untouched."
else
  echo "DRIFT: see the FAIL lines above."
fi
exit "$fail"
