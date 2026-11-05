#!/usr/bin/env bash
# Regenerate everything in docs/audition/ from the engine.
#
# Requires: python3 with numpy/scipy (see tools/requirements-dev.txt) and ffmpeg on PATH.
# Usage:   bash docs/audition/make.sh
#
# Deterministic: same source, same seed 7, same bytes in the audio (MP3 encoder aside).
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(cd "$here/../.." && pwd)"
cd "$root"

command -v ffmpeg >/dev/null || { echo "ffmpeg not on PATH" >&2; exit 1; }

py="python3"
[ -x .venv/bin/python ] && py=".venv/bin/python"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

echo "==> rendering"
"$py" - "$tmp" <<'PY'
import json
import os
import sys

sys.path.insert(0, "medo-motion/templates/procedural-reels")
sys.path.insert(0, os.path.abspath("tools/lib"))

import numpy as np

import audio_engine as ax
import audio_mix as am
import music as M
import sfx

out = sys.argv[1]
SR = 44100


def save(name, buf):
    ax.write_wav(os.path.join(out, name + ".wav"), buf, SR)


# --- 01: the six presets, 16 s each, 2 s apart ------------------------------------------
names = M.preset_names()
seg, gap = 16.0, 2.0
buf = np.zeros((int(len(names) * (seg + gap) * SR), 2), np.float32)
for i, name in enumerate(names):
    bed = M.render_music(M.MusicConfig(preset=name, duration=seg, seed=7))
    ax.mix_into(buf, bed, int(round(i * (seg + gap) * SR)), 1.0)
save("01-six-presets", buf)

# --- A/B helper: match two renders on LUFS, not raw RMS ---------------------------------
def to_lufs(x, target=-18.0, tp=-1.5):
    y = x.astype(np.float32) * 0.5  # headroom
    ax.write_wav(os.path.join(out, "_probe.wav"), y, SR)
    m = am.measure_loudness(os.path.join(out, "_probe.wav"))
    y = y * (10 ** ((target - m["lufs"]) / 20))
    pk = ax.to_db(float(np.abs(y).max()))
    if pk > tp:
        y = y * (10 ** ((tp - pk) / 20))
    return y


def ab(name, preset, layers, seg=16.0):
    a = M.render_music(M.MusicConfig(preset=preset, duration=seg, seed=7))
    kw = {"preset": preset, "duration": seg, "seed": 7}
    if layers is not None:
        kw["layers"] = layers
    b = M.render_music(M.MusicConfig(**kw))
    a2, b2 = to_lufs(a), to_lufs(b)
    both = np.zeros((int(2 * (seg + 1.5) * SR), 2), np.float32)
    ax.mix_into(both, a2, 0, 1.0)
    ax.mix_into(both, b2, int((seg + 1.5) * SR), 1.0)
    save(name, both)


plan = {}
if os.path.exists("docs/audition/plan_b_layers.json"):
    with open("docs/audition/plan_b_layers.json") as fh:
        plan = json.load(fh)

ab("05-AB-tech-levelmatched", "tech", plan.get("tech"))
ab("06-AB-energetic", "energetic", plan.get("energetic"))

# --- 07: music + SFX + VO + ducking, current vs plan B ---------------------------------
DUR = 20.0
# `load_voice` reads WAV only, so decode the committed MP3 into the temp dir first.
vo_mp3 = "docs/audition/vo-ar.mp3"
vo = os.path.join(out, "vo-ar.wav")
if not os.path.exists(vo):
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", vo_mp3,
                    "-ar", "44100", "-ac", "1", vo], check=True)

def sheet(layers):
    m = {"preset": "tech", "seed": 7, "level_db": -3.0}
    if layers:
        m["layers"] = layers
    return {
        "sr": SR,
        "duration": DUR,
        "music": m,
        "sfx": [
            {"t": 0.0, "sfx": "riser", "gain": -14},
            {"t": 3.0, "sfx": "whoosh", "gain": -12},
            {"t": 7.0, "sfx": "swipe", "gain": -12},
            {"t": 11.0, "sfx": "impact", "gain": -10},
            {"t": 15.0, "sfx": "chime", "gain": -11},
            {"t": 19.0, "sfx": "pop", "gain": -13},
        ],
        "voice": {"path": vo, "start": 1.2, "gain_db": 0.0},
        "duck": {"amount": 0.45, "attack": 0.08, "release": 0.32, "lookahead": 0.04},
    }


mixes = []
for layers in (None, plan.get("tech")):
    res = am.mix(sheet(layers), voice_path=vo)
    path = os.path.join(out, "_mix.wav")
    am.write_mix(res, path)
    x, _ = ax.read_wav_mono(path)
    mixes.append(to_lufs(np.stack([x, x], 1), target=-14.5))

both = np.zeros((int(2 * (DUR + 1.5) * SR), 2), np.float32)
ax.mix_into(both, mixes[0], 0, 1.0)
ax.mix_into(both, mixes[1], int((DUR + 1.5) * SR), 1.0)
save("07-VO-mix-AB", both)


# --- 08: music level A/B (-3 dB vs -5 dB), everything else identical -------------------
def level_sheet(level_db):
    return {
        "sr": SR,
        "duration": 20.0,
        "music": {"preset": "tech", "seed": 7, "level_db": level_db},
        "sfx": [
            {"t": 0.0, "sfx": "riser", "gain": -14},
            {"t": 3.0, "sfx": "whoosh", "gain": -12},
            {"t": 7.0, "sfx": "swipe", "gain": -12},
            {"t": 11.0, "sfx": "impact", "gain": -10},
            {"t": 15.0, "sfx": "chime", "gain": -11},
            {"t": 19.0, "sfx": "pop", "gain": -13},
        ],
        "voice": {"path": vo, "start": 1.2, "gain_db": 0.0},
        "duck": {"amount": 0.45, "attack": 0.08, "release": 0.32, "lookahead": 0.04},
    }


halves = []
for level in (-3.0, -5.0):
    res = am.mix(level_sheet(level), voice_path=vo)
    path = os.path.join(out, "_lvl.wav")
    am.write_mix(res, path)
    x, _ = ax.read_wav_mono(path)
    halves.append(to_lufs(np.stack([x, x], 1), target=-14.5))

both = np.zeros((int(2 * (20.0 + 1.5) * SR), 2), np.float32)
ax.mix_into(both, halves[0], 0, 1.0)
ax.mix_into(both, halves[1], int(21.5 * SR), 1.0)
save("08-music-level-AB", both)

# --- vo-ar: already committed; copy through the temp dir so the encoder step finds it --
for stale in ("_probe.wav", "_mix.wav", "_lvl.wav", "vo-ar.wav"):
    p = os.path.join(out, stale)
    if os.path.exists(p):
        os.remove(p)

print("rendered", sorted(f for f in os.listdir(out) if f.endswith(".wav")))
PY

echo "==> encoding 192 kbit/s mp3"
for wav in "$tmp"/*.wav; do
  base="$(basename "$wav" .wav)"
  ffmpeg -y -loglevel error -i "$wav" -c:a libmp3lame -b:a 192k "$here/$base.mp3"
  echo "    $base.mp3"
done

echo "==> done. vo-ar.mp3 is a recorded input, not regenerated here."
