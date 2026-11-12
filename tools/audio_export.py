#!/usr/bin/env python3
"""Audio export (B7أ): the project's audio tracks mixed to one 48 kHz PCM16 WAV.

Sources are decoded, trimmed by `sourceIn`, placed at `start`, multiplied by their `gain` effect (values are
in 1/10000, so 10000 = unity, and keyframes are evaluated per tick), summed, clamped and written as mono
16-bit PCM. The mix is deterministic: same project, same bytes.

    python3 tools/audio_export.py build project.json -o out/mix.wav
    python3 tools/audio_export.py check out/mix.wav.json

Exit codes: 0 ok · 1 project/audio refused (A-codes) · 2 unreadable file or missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402
from unified_project_effects import effect_value  # noqa: E402

VERSION = 1
CHANNELS = 1
SAMPLE_WIDTH = 2
ROOT_FIELDS = {"version", "source", "sampleRate", "channels", "samples", "durationTicks", "clips", "totals", "pcm"}
CLIP_FIELDS = {"clipId", "trackId", "assetId", "start", "duration", "gain", "fade"}


class AudioError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_wav(path: Path) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as handle:
        rate = handle.getframerate()
        channels = handle.getnchannels()
        width = handle.getsampwidth()
        raw = handle.readframes(handle.getnframes())
    if width != 2:
        raise AudioError("A03", f"{path.name}: only 16-bit PCM WAV is read directly (got {width * 8}-bit)")
    total = len(raw) // 2
    import array  # noqa: PLC0415

    values = array.array("h")
    values.frombytes(raw[: total * 2])
    if sys.byteorder == "big":
        values.byteswap()
    frames = len(values) // channels
    mono = [sum(values[i * channels:(i + 1) * channels]) / (channels * 32768.0) for i in range(frames)]
    return mono, rate


def _read_via_av(path: Path, sample_rate: int) -> list[float]:
    try:
        import av  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - the test venv has av
        raise AudioError("A03", f"{path.name}: format needs PyAV (pip install av)") from exc
    samples: list[float] = []
    try:
        with av.open(str(path)) as container:
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is None:
                raise AudioError("A03", f"{path.name}: no audio stream")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=sample_rate)
            for frame in container.decode(stream):
                for out in resampler.resample(frame):
                    data = out.to_ndarray().reshape(-1)
                    samples.extend(float(value) / 32768.0 for value in data)
            for out in resampler.resample(None):
                data = out.to_ndarray().reshape(-1)
                samples.extend(float(value) / 32768.0 for value in data)
    except (OSError, ValueError) as exc:
        raise AudioError("A03", f"{path.name}: {exc}") from exc
    return samples


def read_audio(path: Path, sample_rate: int) -> tuple[list[float], int]:
    """Decode one asset to mono floats at `sample_rate`; WAV stays dependency-free."""
    if path.suffix.lower() == ".wav":
        mono, rate = _read_wav(path)
    else:
        return _read_via_av(path, sample_rate), sample_rate
    if rate == sample_rate:
        return mono, rate
    if rate <= 0:
        raise AudioError("A03", f"{path.name}: invalid sample rate {rate}")
    ratio = sample_rate / rate
    length = int(round(len(mono) * ratio))
    return [mono[min(len(mono) - 1, int(i / ratio))] for i in range(length)], sample_rate


def _gain_at(entry: dict, clip: dict, sample_rate: int, index: int, sample_rate_out: int) -> float:
    """Evaluate the clip's gain effect at this sample's local tick (unity when there is none)."""
    timebase = entry["timebase"]
    local_tick = int(index * timebase / sample_rate_out)
    value = None
    for effect in clip.get("effects", []):
        if effect.get("type") == "gain" and effect.get("enabled", True):
            value = effect_value(entry["project"], clip["id"], effect["id"], min(local_tick, clip["duration"]))
            break
    return 1.0 if value is None else float(value)


def build(project: dict, root: Path, *, sample_rate: int | None = None) -> tuple[bytes, dict]:
    errors = validate(project)
    if errors:
        raise AudioError("A01", "project is invalid: " + "; ".join(errors))
    rate = int(sample_rate or project["profile"]["sampleRate"])
    if rate <= 0:
        raise AudioError("A01", f"sampleRate must be positive (got {rate})")
    assets = {asset["id"]: asset for asset in project.get("assets") or []}
    timebase = project["timebase"]
    total_samples = int(round(project["duration"] * rate / timebase))
    mix = [0.0] * total_samples
    contributions = []

    audio_tracks = [track for track in project["tracks"] if track["kind"] == "audio" and track["enabled"]]
    if not audio_tracks:
        raise AudioError("A02", "no enabled audio track — nothing to mix")
    written = 0
    for track in audio_tracks:
        # A crossfade on this track is a linear gain ramp over its window: the outgoing clip falls to zero
        # exactly as the incoming one rises, so the sum keeps the level of a single source.
        fades: dict[str, tuple[int, int, bool]] = {}
        for transition in track.get("transitions") or []:
            half = transition["duration"] // 2
            clips_by_id = {clip["id"]: clip for clip in track["clips"]}
            source = clips_by_id.get(transition["fromClipId"])
            target = clips_by_id.get(transition["toClipId"])
            if source is None or target is None:
                continue
            cut = target["start"]
            # Both sides of the window must exist in the media, or half the crossfade would be silence:
            # the outgoing clip needs `half` ticks of tail handle, the incoming one `half` of head handle.
            source_asset = assets[source["assetId"]]
            if source_asset.get("duration") is not None and \
                    source["sourceIn"] + source["duration"] + half > source_asset["duration"]:
                raise AudioError("A06", f"crossfade {transition['id']}: clip {source['id']} needs {half} "
                                        "ticks of tail handle the media does not have")
            if target["sourceIn"] < half:
                raise AudioError("A06", f"crossfade {transition['id']}: clip {target['id']} needs {half} "
                                        "ticks of head handle the media does not have")
            fades[source["id"]] = (cut - half, cut + half, False)
            fades[target["id"]] = (cut - half, cut + half, True)
        for clip in track["clips"]:
            asset = assets.get(clip["assetId"])
            if asset is None:
                raise AudioError("A03", f"clip {clip['id']}: unknown asset {clip['assetId']!r}")
            path = Path(root) / asset["uri"]
            if not path.is_file():
                raise AudioError("A03", f"clip {clip['id']}: missing media {asset['uri']}")
            end_tick = clip["start"] + clip["duration"]
            if end_tick > project["duration"]:
                raise AudioError("A04", f"clip {clip['id']}: ends at {end_tick} beyond {project['duration']}")
            speed = clip.get("speed") or {"num": 1, "den": 1}
            num, den = int(speed["num"]), int(speed["den"])
            if num < 1 or den < 1:
                raise AudioError("A01", f"clip {clip['id']}: speed must be a positive fraction")
            samples, _ = read_audio(path, rate)
            window = fades.get(clip["id"])
            span = window[1] - window[0] if window else 0
            # A crossfade reads past the clip's own edges: the outgoing clip needs its tail handle, the
            # incoming one starts `half` early on its head handle. Both were checked above.
            head = span // 2 if window and window[2] else 0
            tail = span // 2 if window and not window[2] else 0
            offset = int(round((clip["sourceIn"] - head) * rate / timebase))
            start = int(round((clip["start"] - head) * rate / timebase))
            length = int(round((clip["duration"] + head + tail) * rate / timebase))
            entry = {"timebase": timebase, "project": project}
            static_gain = _constant_gain(clip) if not clip.get("keyframes") else None
            for index in range(length):
                # Speed = how many source samples one output sample consumes: 2/1 skips every other
                # sample (the clip plays twice as fast, the pitch rises with it — this is a rate
                # change, not a time-stretch), 1/2 repeats each sample once.
                source_index = offset + index * num // den
                if source_index < 0 or source_index >= len(samples):
                    continue
                gain = static_gain if static_gain is not None else _gain_at(
                    entry, clip, rate, max(0, index - head), rate)
                if window:
                    tick = int((start + index) * timebase / rate)
                    if window[0] <= tick < window[1]:
                        numerator = tick - window[0] if window[2] else window[1] - tick
                        gain *= numerator / span
                mix[start + index] += samples[source_index] * gain
            written += 1
            contributions.append({"clipId": clip["id"], "trackId": track["id"], "assetId": asset["id"],
                                  "start": clip["start"], "duration": clip["duration"],
                                  "gain": _constant_gain(clip),
                                  "fade": None if not window else
                                  {"start": window[0], "end": window[1], "rising": window[2]}})
    if not written:
        raise AudioError("A02", "enabled audio tracks have no clips")

    peak = max((abs(value) for value in mix), default=0.0)
    pcm = bytearray()
    import array  # noqa: PLC0415

    values = array.array("h", (max(-32768, min(32767, int(round(value * 32767)))) for value in mix))
    if sys.byteorder == "big":
        values.byteswap()
    pcm_values = values.tobytes()
    pcm.extend(pcm_values)

    manifest = {
        "version": VERSION,
        "source": {"name": project.get("name") or project["id"],
                   "sha256": _sha(json.dumps(project, ensure_ascii=False, sort_keys=True).encode("utf-8"))},
        "sampleRate": rate,
        "channels": CHANNELS,
        "samples": total_samples,
        "durationTicks": project["duration"],
        "clips": contributions,
        "totals": {"seconds": round(total_samples / rate, 6), "peak": round(peak, 6),
                   "clipped": peak > 1.0},
        "pcm": {"sha256": _sha(bytes(pcm_values)), "bytes": len(pcm_values)},
    }
    return bytes(pcm), manifest


def _constant_gain(clip: dict) -> float:
    for effect in clip.get("effects", []):
        if effect.get("type") == "gain" and effect.get("enabled", True) and not clip.get("keyframes"):
            return effect["params"]["value"] / 10000.0
    return 1.0


def write_wav(path: Path, pcm: bytes, sample_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(CHANNELS)
        handle.setsampwidth(SAMPLE_WIDTH)
        handle.setframerate(sample_rate)
        handle.writeframes(pcm)


def validate_manifest(data: dict) -> list[str]:
    """A05: the sidecar must agree with itself and with the numbers an editor would read."""
    if not isinstance(data, dict) or data.get("version") != VERSION:
        return [f"A01 version: only version {VERSION} is accepted"]
    if set(data) != ROOT_FIELDS:
        return [f"A01 root: needs exactly {sorted(ROOT_FIELDS)}"]
    errors: list[str] = []
    if data["samples"] != int(round(data["durationTicks"] * data["sampleRate"] / 240_000)):
        errors.append("A05 samples: does not match durationTicks × sampleRate / timebase")
    expected = data["samples"] / data["sampleRate"] if data["sampleRate"] else 0
    if abs(data["totals"]["seconds"] - expected) > 1e-4:
        errors.append(f"A05 totals.seconds: says {data['totals']['seconds']} but samples give {expected}")
    for index, clip in enumerate(data["clips"]):
        if not isinstance(clip, dict) or set(clip) != CLIP_FIELDS:
            errors.append(f"A01 clips[{index}]: needs exactly {sorted(CLIP_FIELDS)}")
        elif clip["start"] < 0 or clip["duration"] <= 0:
            errors.append(f"A05 clips[{index}]: start must be ≥ 0 and duration > 0")
        elif clip["start"] + clip["duration"] > data["durationTicks"]:
            errors.append(f"A05 clips[{index}]: ends beyond durationTicks")
        elif clip["fade"] is not None:
            fade = clip["fade"]
            if set(fade) != {"start", "end", "rising"} or not isinstance(fade["rising"], bool) \
                    or fade["end"] <= fade["start"]:
                errors.append(f"A05 clips[{index}].fade: needs start < end and a boolean rising")
    if data["pcm"]["bytes"] != data["samples"] * data["channels"] * SAMPLE_WIDTH:
        errors.append("A05 pcm.bytes: does not match samples × channels × 2")
    if len(data["pcm"]["sha256"]) != 64:
        errors.append("A05 pcm.sha256: 64 hex characters required")
    return errors


def verify(manifest: dict, path: Path) -> list[str]:
    errors = validate_manifest(manifest)
    if errors:
        return errors
    if not Path(path).is_file():
        return errors + [f"A05 {path}: missing"]
    with wave.open(str(path), "rb") as handle:
        if handle.getnchannels() != manifest["channels"] or handle.getframerate() != manifest["sampleRate"]:
            errors.append(f"A05 {path}: header channel count or rate differs from the manifest")
        if _sha(handle.readframes(handle.getnframes())) != manifest["pcm"]["sha256"]:
            errors.append(f"A05 {path}: samples no longer match the manifest")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mix the project's audio tracks to a PCM16 WAV.")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="project.json → mix.wav + mix.wav.json")
    build_cmd.add_argument("project", type=Path)
    build_cmd.add_argument("-o", "--out", type=Path, required=True)
    build_cmd.add_argument("--sample-rate", type=int, default=None)
    build_cmd.add_argument("--manifest", type=Path, default=None)
    check = sub.add_parser("check", help="validate a mix manifest")
    check.add_argument("manifest", type=Path)
    check.add_argument("--file", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
            return 2
        target = args.file or (args.manifest.parent / args.manifest.name[:-5]
                               if args.manifest.name.endswith(".json") else None)
        errors = verify(data, target) if target and target.is_file() else validate_manifest(data)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid mix · {data['totals']['seconds']:.2f}s · {data['sampleRate']} Hz · "
              f"{data['channels']} ch · peak {data['totals']['peak']:.3f}")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    try:
        pcm, manifest = build(project, args.project.parent, sample_rate=args.sample_rate)
    except AudioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    write_wav(args.out, pcm, manifest["sampleRate"])
    sidecar = args.manifest or args.out.with_suffix(args.out.suffix + ".json")
    sidecar.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} · {manifest['totals']['seconds']:.2f}s · {manifest['sampleRate']} Hz · "
          f"peak {manifest['totals']['peak']:.3f} · {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
