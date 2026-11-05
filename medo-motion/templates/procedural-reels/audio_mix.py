"""One cue sheet for everything audible in a reel — music, SFX, and voice-over.

Why a single timeline: the previous system had three disconnected notions of time. `mix.py` hard-coded
a bed and a list of SFX in Python; `sfx_kit.py --cues` mixed a cue sheet to the voice's length; and
nothing anywhere recorded *where the music changed*. A cut that moved therefore changed the picture
and left the sound behind. This module makes one JSON document the source of truth:

    {"version": 1, "duration": 24.0, "sr": 44100, "seed": 7, "voice": "vo.wav",
     "music": {"preset": "tech", "bpm": 112, "key": "A", "scale": "minor",
               "sections": [{"name": "intro", "start": 0.0, "end": 2.6}, ...],
               "changes": [{"t": 8.0, "preset": "cinematic", "bpm": 82, "bars": 2}],
               "duck": {"amount": 0.6, "attack": 0.008, "release": 0.32, "lookahead": 0.04}},
     "sfx": [{"t": 2.1, "sfx": "whoosh", "gain": 0.9, "pan": [-0.6, 0.6], "anchor": true,
              "why": "transition wipe"}],
     "duck": {"amount": 0.7, "attack": 0.01, "release": 0.18},
     "master": {"lufs": -14.5, "true_peak": -1.5}}

Everything is resolved on the **sample grid**, at the sheet's `sr`, so a cue at 2.1 s is sample 92610
at 44.1 kHz and 100800 at 48 kHz and no rounding drift accumulates down a list. The mixer never keeps a
second timeline: `resolve()` produces the definitive event list, and `mix()` renders it once.

Adapted (re-written) from `majedphotos/video-ad-editor/motion/audio.py` (MIT) — see `assets/CREDITS.md`
and `docs/audio-engine-audit.md`.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np

import audio_engine as ax
import music
import sfx

SHEET_VERSION = 1
DEFAULT_MASTER = {"lufs": -14.5, "true_peak": -1.5}      # brand: -14.5 ±0.3 LUFS, ≤ -1.5 dBTP


# --------------------------------------------------------------------------- reading / writing
def load_sheet(path) -> dict:
    """Read a cue sheet, normalising the keys a caller is allowed to omit."""
    sheet = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(sheet, list):                          # a bare cue list is still a valid sheet
        sheet = {"sfx": sheet}
    if isinstance(sheet, dict) and "cuts" in sheet and not sheet.get("sfx"):
        sheet["sfx"] = sfx.cues_for_transitions(sheet["cuts"])
    return validate_sheet(sheet)


def validate_sheet(sheet: dict) -> dict:
    """Fill defaults and fail early on anything that would render to silence or crash mid-mix."""
    if not isinstance(sheet, dict):
        raise TypeError("a cue sheet must be a JSON object (or a list of sfx cues)")
    out = dict(sheet)
    out.setdefault("version", SHEET_VERSION)
    out.setdefault("sr", ax.SR)
    out.setdefault("seed", 7)
    out.setdefault("duck", {"amount": 0.6, "attack": 0.008, "release": 0.32, "lookahead": 0.04})
    out.setdefault("master", dict(DEFAULT_MASTER))
    out.setdefault("sfx", [])
    out.setdefault("music", None)
    if "duration" not in out or out["duration"] is None:
        raise ValueError("a cue sheet needs 'duration' (seconds) — the timeline has to be authoritative")
    out["duration"] = float(out["duration"])
    if not math.isfinite(out["duration"]) or out["duration"] <= 0:
        raise ValueError("duration must be a positive number of seconds")
    out["sr"] = ax.check_rate(out["sr"])
    if out.get("music") is not None:
        music_cfg = dict(out["music"])
        music_cfg.setdefault("duration", out["duration"])
        music_cfg.setdefault("sr", out["sr"])
        music_cfg.setdefault("seed", out["seed"])
        non_config = {"changes", "level_db", "duck", "why", "name"}
        music.MusicConfig(**{k: v for k, v in music_cfg.items() if k not in non_config})   # validate now
        out["music"] = music_cfg
    for i, cue in enumerate(out["sfx"]):
        name = cue.get("sfx") or cue.get("name")
        if name not in sfx.BANK:
            raise KeyError(f"cue {i}: unknown sfx {name!r}")
        if float(cue.get("t", 0.0)) < 0:
            raise ValueError(f"cue {i}: negative time {cue['t']}")
    for i, change in enumerate((out.get("music") or {}).get("changes", [])):
        if float(change.get("t", -1)) < 0:
            raise ValueError(f"music change {i}: negative time")
    return out


def save_sheet(sheet: dict, path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(validate_sheet(sheet), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------- music arrangement
def music_plan(sheet: dict) -> dict:
    """The music the sheet asks for, segment by segment.

    A *change* at `t` restarts the arrangement: the new preset keeps its own key/feel and gets the time
    from `t` to the next change (or the end). Nothing is stretched to reach a bar line — the picture
    decides the cut, and `music.section_spans()` already snaps the *inside* of a segment to bars, so a
    change still lands on a musical boundary rather than mid-phrase.
    """
    m = dict(sheet.get("music") or {})
    total = float(sheet["duration"])
    if not m:
        return {"segments": [], "changes": []}
    sr = int(m.get("sr", sheet["sr"]))
    changes = sorted((dict(c) for c in m.get("changes", [])), key=lambda c: float(c.get("t", 0.0)))
    base = {k: v for k, v in m.items() if k != "changes"}
    cuts = [0.0] + [float(c["t"]) for c in changes if 0.0 < float(c["t"]) < total] + [total]
    segments = []
    for i in range(len(cuts) - 1):
        start, end = cuts[i], cuts[i + 1]
        cfg = {k: v for k, v in base.items() if k not in ("level_db", "duck")}
        if i > 0:
            cfg.update({k: v for k, v in changes[i - 1].items()
                        if k not in ("t", "level_db", "duck", "why", "bars")})
        cfg.update({"duration": round(end - start, 6), "sr": sr, "seed": int(cfg.get("seed", sheet["seed"])) + i})
        segments.append({"start": start, "end": end, "config": cfg,
                         "change": dict(changes[i - 1]) if i else None})
    return {"segments": segments, "changes": changes, "total": total, "sr": sr}


SEAM = 0.45          # seconds of cross-fade at a music change


def render_music_track(sheet: dict, seam: float = SEAM) -> tuple[np.ndarray, list[dict]]:
    """Render every music segment and **cross-fade** the seams; returns (audio, plan).

    Each segment fades in and out inside its own length (so a stinger resolves), which leaves a hole
    at a music change: two fades meeting at the same instant cancel to near-silence. So a change
    hands the outgoing bed an extra `seam` seconds and starts the incoming one `seam` early, and the
    two are cross-faded — the level stays continuous and the change lands on the beat. Measured
    before the fix: 10.0 s into a 20 s reel the bed dropped to -48.8 dBFS.
    """
    plan = music_plan(sheet)
    n = int(round(float(sheet["duration"]) * int(sheet["sr"])))
    out = np.zeros((n, 2), np.float32)
    report = []
    if not plan["segments"]:
        return out, report
    sr = int(sheet["sr"])
    last = len(plan["segments"]) - 1
    for idx, seg in enumerate(plan["segments"]):
        extra = seam if idx < last else 0.0
        length = round(seg["end"] - seg["start"] + extra, 6)
        # A change is a *cut*, not a re-introduction: the incoming bed must be at full level when the
        # change lands. Only the first segment keeps the preset's fade-in, and only the last one keeps
        # a fade-out (a mid-reel segment hands its tail to the cross-fade instead).
        cfg = music.MusicConfig(**dict(
            seg["config"], duration=length,
            fade_in=seg["config"].get("fade_in", 0.8) if idx == 0 else 0.0,
            # the incoming segment starts `seam` early, so its own headroom covers the cross-fade
            fade_out=seg["config"].get("fade_out", 1.2) if idx == last else extra))
        audio = music.render_music(cfg)
        start = seg["start"] - (seam if idx > 0 else 0.0)
        i = int(round(max(0.0, start) * sr))
        written = ax.mix_into(out, audio, i)
        report.append({"start": seg["start"], "end": seg["end"], "preset": cfg.preset,
                       "bpm": cfg.resolved()["bpm"], "samples": int(audio.shape[0]),
                       "written": int(written), "seam": round(extra, 3),
                       "truncated": int(audio.shape[0] - max(0, written))})
    return out, report


# --------------------------------------------------------------------------- voice
def load_voice(path, sr: int, length: int) -> tuple[np.ndarray, dict]:
    """Read a voice track as mono float32 at `sr`, padded or trimmed to exactly `length` samples."""
    from scipy.io import wavfile
    from scipy.signal import resample_poly

    rate, data = wavfile.read(str(path))
    v = np.asarray(data)
    if v.dtype.kind == "i":
        v = v.astype(np.float32) / float(np.iinfo(v.dtype).max)
    elif v.dtype.kind == "u":
        v = (v.astype(np.float32) - np.iinfo(v.dtype).max / 2) / (np.iinfo(v.dtype).max / 2)
    else:
        v = v.astype(np.float32)
    if v.ndim > 1:
        v = v.mean(axis=1)
    if rate != sr:
        g = math.gcd(int(rate), int(sr))
        v = resample_poly(v, int(sr) // g, int(rate) // g).astype(np.float32)
    pad = np.zeros(length, np.float32)
    m = min(length, len(v))
    pad[:m] = v[:m]
    try:                                        # keep project artifacts portable in the report
        shown = str(Path(path).resolve().relative_to(Path.cwd().resolve()))
    except (ValueError, OSError):
        shown = Path(path).name
    return pad, {"source": shown, "source_rate": int(rate), "source_samples": int(len(v)),
                 "kept": int(m), "trimmed": int(max(0, len(v) - length)), "padded": int(max(0, length - len(v)))}


# --------------------------------------------------------------------------- the mix
def resolve(sheet: dict) -> dict:
    """The definitive, sample-locked event list — the only place a cue time becomes a sample index."""
    sheet = validate_sheet(sheet)
    sr = int(sheet["sr"])
    total = float(sheet["duration"])
    n = int(round(total * sr))

    def sample_of(t: float) -> int:
        return int(round(max(0.0, float(t)) * sr))

    events = []
    for i, cue in enumerate(sheet["sfx"]):
        name = cue.get("sfx") or cue.get("name")
        events.append({
            "index": i, "sample": sample_of(cue.get("t", 0.0)), "t": float(cue.get("t", 0.0)),
            "sfx": name, "family": sfx.CATALOG.get(name, {}).get("family", ""),
            "gain": float(cue.get("gain", 1.0)), "pan": cue.get("pan", 0.0),
            "anchor": bool(cue.get("anchor", sheet.get("sfx_anchor", False))),
            "why": cue.get("why", ""),
        })
    plan = music_plan(sheet)
    music_events = []
    if plan["segments"]:
        first = plan["segments"][0]
        music_events.append({"t": float(first["start"]), "sample": sample_of(first["start"]),
                             "kind": "music", "preset": first["config"].get("preset"), "why": "start"})
    for change in plan["changes"]:
        music_events.append({"t": float(change["t"]), "sample": sample_of(change["t"]), "kind": "change",
                             "preset": change.get("preset", (sheet.get("music") or {}).get("preset")),
                             "why": change.get("why", "")})
    events.sort(key=lambda e: (e["sample"], e["index"]))
    return {"sr": sr, "samples": n, "duration": total, "sfx": events, "music": music_events,
            "musicSegments": plan["segments"], "duck": dict(sheet["duck"]), "master": dict(sheet["master"])}


def mix(sheet: dict, voice_path=None, *, master: bool = True, limit: bool = True) -> dict:
    """Render the sheet: music + SFX + voice, with ducking and a brand-compliant master.

    Returns a dict of arrays and a report — never writes unless `write_mix()` is used, so the caller
    controls where files land (the previous renderers wrote fixed names and clobbered each other).
    """
    sheet = validate_sheet(sheet)
    sr = int(sheet["sr"])
    n = int(round(float(sheet["duration"]) * sr))
    resolved = resolve(sheet)

    # --- music ---------------------------------------------------------------------------
    if sheet.get("music"):
        bed, music_report = render_music_track(sheet)
        music_gain = ax.db(float((sheet["music"] or {}).get("level_db", -3.0)))
    else:
        bed, music_report, music_gain = np.zeros((n, 2), np.float32), [], 0.0
    bed = bed[:n] * music_gain

    # --- sfx -----------------------------------------------------------------------------
    cue_list = []
    for event in resolved["sfx"]:
        cue_list.append({"t": event["t"], "sfx": event["sfx"], "gain": event["gain"],
                         "pan": event["pan"], "anchor": event["anchor"],
                         "seed": event["index"], "id": event["index"]})
    if cue_list:
        sfx_bus = sfx.bus(float(sheet["duration"]), cue_list, sr=sr, limit=limit)
        sfx_written, sfx_truncated = int(sfx.bus.last_written), int(sfx.bus.last_truncated)
        sfx_clipped = int(sfx.bus.last_clipped)
    else:                                     # `bus` was never called, so there is nothing to report
        sfx_bus, sfx_written, sfx_truncated, sfx_clipped = np.zeros((n, 2), np.float32), 0, 0, 0
    sfx_bus = sfx_bus[:n]

    # --- voice ---------------------------------------------------------------------------
    if voice_path:
        vo, vo_report = load_voice(voice_path, sr, n)
    else:
        vo, vo_report = np.zeros(n, np.float32), None

    # --- ducking: SFX under the voice, and the music under *both* --------------------------
    d = resolved["duck"]
    mduck = dict((sheet["music"] or {}).get("duck") or d)
    vo_sig = vo
    if voice_path:
        sfx_bus = sfx.duck(vo_sig, sfx_bus, depth=float(d.get("amount", 0.6)),
                           attack=float(d.get("attack", 0.008)),
                           release=None if d.get("release") is None else float(d["release"]),
                           lookahead=float(d.get("lookahead", 0.04)), sr=sr)
    if voice_path and mduck.get("amount", 0) > 0:
        gain = ax.duck_gain(vo_sig, sr, depth=float(mduck["amount"]),
                            attack=float(mduck.get("attack", 0.008)),
                            release=float(mduck.get("release", 0.32)),
                            lookahead=float(mduck.get("lookahead", 0.04)),
                            threshold_db=float(mduck.get("threshold_db", -50.0)))
        bed *= gain[:, None]

    # --- sum, then master ----------------------------------------------------------------
    bed_level = float(np.sqrt(np.mean(bed ** 2))) if bed.size else 0.0
    sfx_level = float(np.sqrt(np.mean(sfx_bus ** 2))) if sfx_bus.size else 0.0
    pre = bed + sfx_bus + np.stack([vo, vo], 1) if voice_path else bed + sfx_bus
    out = pre
    if limit:
        out = ax.limiter(out, ceiling=10 ** (float(sheet["master"].get("true_peak", -1.5)) / 20.0) * 0.9, sr=sr)
    if master:
        target = float(sheet["master"].get("lufs", -14.5))
        out = normalise_rms(out, sr, target_lufs=target, true_peak=float(sheet["master"].get("true_peak", -1.5)))
    report = {
        "sr": sr, "samples": n, "duration": float(sheet["duration"]),
        "music": {"present": bool(sheet.get("music")), "segments": music_report,
                  "gain_db": round(ax.to_db(music_gain) if music_gain else -120.0, 2),
                  "rms_dbfs": round(ax.to_db(bed_level), 2), "duck": mduck},
        "sfx": {"cues": len(resolved["sfx"]), "rms_dbfs": round(ax.to_db(sfx_level), 2),
                "truncated_samples": sfx_truncated, "written_samples": sfx_written,
                "early_clipped_samples": sfx_clipped},
        "voice": vo_report, "events": resolved["sfx"], "musicEvents": resolved["music"],
        "master": dict(sheet["master"]),
        "peak_dbfs": round(ax.to_db(float(np.max(np.abs(out))) if out.size else 0.0), 2),
        "true_peak_dbtp": round(ax.true_peak(out, sr), 2),
    }
    return {"audio": out, "music": bed, "sfx": sfx_bus, "voice": vo, "report": report}


def normalise_rms(audio: np.ndarray, sr: int, target_lufs: float = -14.5, true_peak: float = -1.5) -> np.ndarray:
    """Bring the mix to the brand loudness **without** ffmpeg, using the RMS/ITU-approximation.

    `loudnorm` in ffmpeg is the final word (see `tools/audio_mix.py`), but the library has to produce
    something sane on a machine with no ffmpeg, and tests must not shell out. A −14.5 LUFS target is
    approximated from the A-weighted RMS on the stereo sum, then the ceiling is enforced.
    """
    x = np.asarray(audio, np.float32)
    if x.size == 0:
        return x
    mono = x.mean(axis=1) if x.ndim == 2 else x
    # A-weighting-ish: high-pass at 40 Hz, shelf down the low end, slight presence lift
    try:
        shaped = ax.hp(ax.hp(x, 90, sr, order=2), 40, sr, order=1).mean(axis=1) if x.ndim == 2 else ax.hp(x, 90, sr)
    except Exception:                                   # pragma: no cover — never fail on a filter
        shaped = mono
    rms = float(np.sqrt(np.mean(shaped ** 2))) if shaped.size else 0.0
    gain = 10 ** ((target_lufs - ax.to_db(rms) - 3.0) / 20.0) if rms > 0 else 1.0
    out = x * gain
    ceiling = 10 ** (true_peak / 20.0) * 0.89
    out = ax.limiter(out, ceiling=ceiling, sr=sr)
    return np.ascontiguousarray(out, np.float32)


def write_mix(result: dict, path, sr: int | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    ax.write_wav(path, result["audio"], sr or result["report"]["sr"])
    return path


# --------------------------------------------------------------------------- cue-sheet helpers
def from_storyboard(storyboard: dict, *, preset: str = "tech", duration: float | None = None,
                    sr: int = ax.SR, seed: int = 7) -> dict:
    """Build a sheet from a storyboard/cut list: transitions supply the SFX, scenes move the music.

    storyboard: {"duration": 24.0, "scenes": [{"t": 0.0}, {"t": 6.4, "transition": "wipe"}], ...}
    A scene that declares `music` starts a new music segment there.
    """
    scenes = storyboard.get("scenes") or []
    total = float(duration or storyboard.get("duration") or (max((s.get("t", 0.0) for s in scenes), default=0.0) + 4.0))
    cuts = [{"t": s.get("t", 0.0), "name": s.get("transition", ""), "gain": s.get("gain", 1.0)}
            for s in scenes if s.get("transition")]
    sheet = {
        "version": SHEET_VERSION, "duration": total, "sr": sr, "seed": seed,
        "music": {"preset": preset, "duration": total, "sr": sr, "seed": seed,
                  "changes": [{"t": s["t"], "preset": s["music"]} for s in scenes if s.get("music")]},
        "sfx": sfx.cues_for_transitions(cuts, lead=storyboard.get("sfxLead", 0.0)),
        "duck": {"amount": 0.62, "attack": 0.008, "release": 0.32, "lookahead": 0.04},
        "master": dict(DEFAULT_MASTER),
    }
    return validate_sheet(sheet)


def ffmpeg_loudnorm(path_in, path_out, lufs: float = -14.5, true_peak: float = -1.5, sr: int | None = None) -> dict:
    """Two-pass `loudnorm` (the final master). Returns the measured values; no-op without ffmpeg."""
    from media_bin import ffmpeg as find_ffmpeg     # local import: the library must work standalone

    ff = find_ffmpeg() or "ffmpeg"
    p1 = subprocess.run([ff, "-hide_banner", "-i", str(path_in), "-af",
                         f"loudnorm=I={lufs}:TP={true_peak}:LRA=11:print_format=json", "-f", "null", "-"],
                        capture_output=True, text=True)
    try:
        j = json.loads(p1.stderr[p1.stderr.rindex("{"):p1.stderr.rindex("}") + 1])
    except (ValueError, json.JSONDecodeError):
        return {"ok": False, "reason": "loudnorm measurement failed", "stderr": p1.stderr[-400:]}
    af = (f"loudnorm=I={lufs}:TP={true_peak}:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    path_in, path_out = Path(path_in), Path(path_out)
    tmp = path_out.with_name(path_out.stem + ".loudnorm.wav")
    cmd = [ff, "-y", "-loglevel", "error", "-i", str(path_in), "-af", af]
    if sr:
        cmd += ["-ar", str(sr)]
    cmd.append(str(tmp))
    subprocess.run(cmd, check=True)
    if path_out.suffix.lower() == ".wav":
        tmp.replace(path_out)                    # never transcode in place: ffmpeg refuses it
    else:
        subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(tmp), str(path_out)], check=True)
        tmp.unlink(missing_ok=True)
    return {"ok": True, "input_i": float(j["input_i"]), "input_tp": float(j["input_tp"]),
            "input_lra": float(j["input_lra"]), "target_offset": float(j["target_offset"])}


def measure_loudness(path, ff=None) -> dict:
    """Integrated loudness / true peak / LRA measured by ffmpeg's **EBU R128** meter.

    `loudnorm` and `ebur128` do not agree to the last decimal on the same file (measured here:
    -14.51 LUFS vs -14.8 LUFS on one master). `loudnorm` is a normaliser; `ebur128` is the reference
    meter the platforms use, so this is what the report quotes and what the trim step aims at.
    """
    import re

    from media_bin import ffmpeg as find_ffmpeg
    ff = ff or find_ffmpeg() or "ffmpeg"
    r = subprocess.run([ff, "-hide_banner", "-nostats", "-i", str(path), "-af",
                        "ebur128=peak=true:framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    # ebur128 emits partial per-window readings before its final Summary block.
    # Parse only that block; searching the whole stderr returns an early transient
    # (often 0.0 LUFS during the opening window) instead of integrated loudness.
    summary_at = r.stderr.rfind("Summary:")
    summary = r.stderr[summary_at:] if summary_at >= 0 else ""
    out = {"ok": False, "reason": "EBU R128 summary missing or measurement failed",
           "returncode": r.returncode, "stderr": r.stderr[-400:]}
    m_i = re.search(r"I:\s*(-?\d+(?:\.\d+)?) LUFS", summary)
    m_tp = re.search(r"Peak:\s*(-?\d+(?:\.\d+)?) dBFS", summary)
    m_lra = re.search(r"LRA:\s*(-?\d+(?:\.\d+)?) LU", summary)
    if r.returncode == 0 and m_i:
        out = {"ok": True, "lufs": float(m_i.group(1)),
               "true_peak": float(m_tp.group(1)) if m_tp else None,
               "lra": float(m_lra.group(1)) if m_lra else None}
    return out


def master_to_target(path, lufs: float = -14.5, true_peak: float = -1.5, tolerance: float = 0.15,
                     max_trim: float = 2.0, ff=None) -> dict:
    """Two-pass loudnorm, then **verify with the reference meter and trim** the residue.

    The trim is bounded (±2 dB), yields to the true-peak ceiling, and is measured again afterwards —
    so the number in the report is the number a platform will compute, not the number we hoped for.
    """
    from media_bin import ffmpeg as find_ffmpeg
    ff = ff or find_ffmpeg()
    if not ff:
        return {"ok": False, "reason": "ffmpeg not available"}
    path = Path(path)
    norm = ffmpeg_loudnorm(path, path, lufs=lufs, true_peak=true_peak)
    if not norm.get("ok"):
        return norm
    before = measure_loudness(path, ff)
    report = {"ok": True, "loudnorm": norm, "measured_before_trim": before}
    if not before.get("ok"):
        # A successful loudnorm pass is not sufficient: the exported master is only
        # verified when the independent EBU R128 meter can read it.
        report.update({
            "ok": False,
            "reason": "EBU R128 verification failed after loudnorm",
            "measurement_error": before,
        })
        return report
    gain = max(-max_trim, min(max_trim, lufs - before["lufs"]))
    if abs(gain) <= tolerance:
        report["trim_db"] = 0.0
        report["measured"] = before
        return report
    tp = before.get("true_peak")
    if gain > 0 and tp is not None and tp + gain > true_peak - 0.1:
        gain = max(0.0, true_peak - 0.1 - tp)          # loudness yields to the ceiling
    if abs(gain) <= 0.01:
        report["trim_db"] = 0.0
        report["measured"] = before
        return report
    tmp = path.with_name(path.stem + ".trim.wav")
    subprocess.run([ff, "-y", "-loglevel", "error", "-i", str(path), "-af",
                    f"volume={gain:.2f}dB", str(tmp)], check=True)
    tmp.replace(path)
    after = measure_loudness(path, ff)
    report.update({"trim_db": round(gain, 2), "measured": after,
                   "final_lufs": after.get("lufs"), "final_true_peak": after.get("true_peak")})
    return report


def describe(sheet: dict) -> list[str]:
    """Human-readable summary of a sheet — what a reviewer reads before listening."""
    r = resolve(sheet)
    lines = [f"{r['duration']:.2f}s @ {r['sr']} Hz · {len(r['sfx'])} sfx cue(s) · "
             f"{len(r['musicSegments'])} music segment(s)"]
    for seg in r["musicSegments"]:
        cfg = music.MusicConfig(**seg["config"])
        info = music.music_info(cfg)
        lines.append(f"  music {seg['start']:6.2f}→{seg['end']:6.2f}s  {cfg.preset:<9} {info['bpm']:g} BPM "
                     f"{info['key']} {info['scale']} · {len(info['sections'])} sections")
    for e in r["sfx"]:
        lines.append(f"  sfx   {e['t']:6.2f}s  {e['sfx']:<9} {e['family']:<7} gain {e['gain']:.2f}"
                     + (f"  ({e['why']})" if e["why"] else ""))
    return lines
