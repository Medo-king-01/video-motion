#!/usr/bin/env python3
"""EDL import (B6ج): an EDL back into a unified project — the reverse of `edl_export`.

An EDL carries reels and timecodes, not file paths or hashes, so the import refuses to invent them: it
requires `--media DIR`, matches each reel to a real file, hashes it, and probes its duration. Reels that
cannot be resolved are listed, not guessed.

    python3 tools/edl_import.py build out/reel.edl --media media/ -o project.json
    python3 tools/edl_import.py build reel.edl --media media/ --fps 30 -o project.json   # no sidecar

Exit codes: 0 ok · 1 EDL/media refused (I-codes) · 2 unreadable file or missing dependency.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import edl_export  # noqa: E402
import profiles  # noqa: E402
from unified_project_check import validate  # noqa: E402

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".ppm", ".pgm"}
CHANNELS = {"V": ("v1", "video"), "A": ("a1", "audio"), "A2": ("a2", "audio")}


class ImportError_(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def tc_ticks(value: str, fps: int, frame_ticks: int) -> int:
    hour, minute, second, frame = (int(part) for part in value.split(":"))
    if frame >= fps:
        raise ImportError_("I05", f"timecode {value} has frame {frame} at {fps} fps — wrong rate")
    return ((hour * 3600 + minute * 60 + second) * fps + frame) * frame_ticks


def find_media(folder: Path, reel: str) -> Path | None:
    """Reels are 8-char tags: match by stem, case-insensitive, first hit in sorted order."""
    wanted = reel.strip("_ ").upper()
    if not wanted or not folder.is_dir():
        return None
    for path in sorted(folder.iterdir()):
        if path.is_file() and edl_export.reel_for(path.name) == wanted:
            return path
    return None


def probe_media(path: Path) -> dict:
    """Kind and duration of one file. Images have no duration; media must report one."""
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return {"kind": "image", "duration": None}
    try:
        import av  # noqa: PLC0415
    except ImportError as exc:  # pragma: no cover - the test venv has av
        raise ImportError_("I06", "PyAV is required to probe media durations (pip install av)") from exc
    try:
        with av.open(str(path)) as container:
            streams = [s for s in container.streams if s.type in ("video", "audio")]
            if not streams:
                raise ImportError_("I03", f"{path.name}: no video or audio stream")
            stream = streams[0]
            duration = 0.0
            if stream.duration is not None and stream.time_base is not None:
                duration = float(stream.duration * stream.time_base)
            elif container.duration:
                duration = float(container.duration / av.time_base)
            if duration <= 0:
                raise ImportError_("I03", f"{path.name}: no positive duration")
            return {"kind": "video" if stream.type == "video" else "audio",
                    "duration": round(duration, 6)}
    except (OSError, ValueError) as exc:
        raise ImportError_("I03", f"{path.name}: {exc}") from exc


def read_rate(edl_path: Path, *, sidecar: Path | None, fps: int | None) -> tuple[int, dict]:
    """The rate comes from our own sidecar when present, otherwise from an explicit `--fps`."""
    path = sidecar if sidecar is not None else edl_path.with_suffix(edl_path.suffix + ".json")
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ImportError_("I01", f"cannot read sidecar {path}: {exc}") from exc
        errors = edl_export.validate_manifest(data)
        if errors:
            raise ImportError_("I01", "sidecar is not a valid EDL manifest: " + "; ".join(errors))
        if fps is not None and int(fps) != int(data["fps"]):
            raise ImportError_("I05", f"--fps {fps} contradicts the sidecar's {data['fps']}")
        return int(data["fps"]), data
    if fps is None:
        raise ImportError_("I02", "no sidecar next to the EDL — pass --fps (timecodes need a rate)")
    return int(fps), {}


def build_project(edl_path: Path, *, media: Path, fps: int | None = None, sidecar: Path | None = None,
                  profile_id: str = "reel-30", name: str | None = None) -> dict:
    try:
        text = edl_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ImportError_("I01", f"cannot read {edl_path}: {exc}") from exc
    try:
        events = edl_export.parse_edl(text)
    except edl_export.EdlError as exc:
        raise ImportError_("I01", str(exc)) from exc
    rate, manifest = read_rate(edl_path, sidecar=sidecar, fps=fps)
    if not media.is_dir():
        raise ImportError_("I03", f"--media {media} is not a directory")
    registry = profiles.load_registry()
    try:
        profile = profiles.find(registry, profile_id)
    except profiles.ProfileError as exc:
        raise ImportError_("I05", str(exc)) from exc
    if profile["fps"]["num"] != rate or profile["fps"]["den"] != 1:
        raise ImportError_("I05", f"EDL is {rate} fps but profile {profile_id} is "
                                  f"{profile['fps']['num']}/{profile['fps']['den']}")
    if "FCM: NON-DROP FRAME" not in text:
        raise ImportError_("I05", "only non-drop EDLs are imported")

    timebase = registry["timebase"]
    frame_ticks = timebase // rate
    assets: dict[str, dict] = {}
    tracks: dict[str, dict] = {}
    imported: list[dict] = []
    missing: set[str] = set()
    duration = 0

    for event in events:
        channel = event["ch"]
        if channel not in CHANNELS:
            raise ImportError_("I05", f"event {event['n']}: channel {channel} is not supported")
        track_id, track_kind = CHANNELS[channel]
        reel = event["reel"]
        key = reel.lower()
        if key not in assets:
            path = find_media(media, reel)
            if path is None:
                missing.add(reel)
                continue
            info = probe_media(path)
            asset = {"id": f"asset-{len(assets) + 1}", "kind": info["kind"],
                     "uri": path.relative_to(media).as_posix(),
                     "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            if info["kind"] != "image":
                asset["duration"] = int(round(info["duration"] * timebase))
            assets[key] = asset
        asset = assets[key]
        still = asset["kind"] == "image" and track_kind == "video"
        if asset["kind"] != track_kind and not still:
            raise ImportError_("I05", f"event {event['n']}: {asset['kind']} asset on the {track_kind} track")
        source_in = tc_ticks(event["si"], rate, frame_ticks)
        record_in = tc_ticks(event["ri"], rate, frame_ticks)
        record_out = tc_ticks(event["ro"], rate, frame_ticks)
        if asset["kind"] == "image" and source_in != 0:
            raise ImportError_("I05", f"event {event['n']}: a still must start at source 00:00:00:00")
        track = tracks.setdefault(track_id, {"id": track_id, "kind": track_kind, "enabled": True, "clips": []})
        clip_id = f"c{sum(len(t['clips']) for t in tracks.values()) + 1}"
        clip = {"id": clip_id, "kind": "media", "assetId": asset["id"],
                "start": record_in, "duration": record_out - record_in,
                "sourceIn": source_in, "effects": [], "keyframes": []}
        track["clips"].append(clip)
        imported.append({"channel": channel, "event": event, "clip": clip, "still": still,
                         "track": track})
        duration = max(duration, record_out)

    if missing:
        raise ImportError_("I03", "no file in --media matches reel(s): " + ", ".join(sorted(missing)))
    # A `D` event is a dissolve centred on the cut: the exporter widened both neighbours by half its length,
    # so the importer takes that half back and records the crossfade the project models.
    transitions: list[dict] = []
    last_on_channel: dict[str, dict] = {}
    for item in imported:
        event = item["event"]
        if event["tr"] != "D":
            last_on_channel[item["channel"]] = item
            continue
        frames = int(event["frames"] or 0)
        if frames <= 0 or frames % 2:
            raise ImportError_("I06", f"event {event['n']}: a dissolve needs a positive even frame count")
        previous = last_on_channel.get(item["channel"])
        if previous is None:
            raise ImportError_("I06", f"event {event['n']}: a dissolve cannot open a channel — "
                                      "there is nothing to dissolve from")
        half = frames // 2 * frame_ticks
        behind, ahead = previous["clip"], item["clip"]
        overlap = behind["start"] + behind["duration"] - ahead["start"]
        if overlap != frames * frame_ticks:
            raise ImportError_("I06", f"event {event['n']}: the {frames}-frame dissolve does not match the "
                                      f"{overlap}-tick event overlap, so the cut would be a guess")
        behind["duration"] -= half
        ahead["start"] += half
        ahead["duration"] -= half
        if not item["still"]:
            ahead["sourceIn"] += half
        transitions.append({"id": f"t{len(transitions) + 1}", "kind": "crossfade",
                            "fromClipId": behind["id"], "toClipId": ahead["id"],
                            "duration": frames * frame_ticks})
        item["track"].setdefault("transitions", []).append(transitions[-1])
        last_on_channel[item["channel"]] = item
    if not tracks:
        raise ImportError_("I01", "the EDL has no events to import")
    for track in tracks.values():
        track["clips"].sort(key=lambda clip: clip["start"])
        for previous, current in zip(track["clips"], track["clips"][1:]):
            if current["start"] < previous["start"] + previous["duration"]:
                raise ImportError_("I04", f"clips {previous['id']} and {current['id']} overlap on "
                                          f"{track['id']}")

    totals = manifest.get("totals") or {}
    if isinstance(totals, dict) and isinstance(totals.get("durationTc"), str):
        duration = max(duration, tc_ticks(totals["durationTc"], rate, frame_ticks))

    project = {
        "schemaVersion": "1.2" if transitions else "1.0",
        "id": "edl-" + hashlib.sha256(text.encode("utf-8")).hexdigest()[:12],
        "name": name or manifest.get("title") or edl_path.stem,
        "profile": {"width": profile["width"], "height": profile["height"],
                    "fps": dict(profile["fps"]), "sampleRate": profile["sampleRate"]},
        "timebase": timebase,
        "duration": duration,
        "seed": 0,
        "assets": list(assets.values()),
        "tracks": [tracks[key] for key in ("v1", "a1", "a2") if key in tracks],
    }
    errors = validate(project)
    if errors:
        raise ImportError_("I04", "imported project is invalid: " + "; ".join(errors))
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CMX3600 EDL → unified project (needs real media).")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="edl + media directory → project.json")
    build.add_argument("edl", type=Path)
    build.add_argument("--media", type=Path, required=True)
    build.add_argument("-o", "--out", type=Path, required=True)
    build.add_argument("--fps", type=int, default=None)
    build.add_argument("--sidecar", type=Path, default=None)
    build.add_argument("--profile", default="reel-30")
    build.add_argument("--name", default=None)
    args = parser.parse_args(argv)

    try:
        project = build_project(args.edl, media=args.media, fps=args.fps, sidecar=args.sidecar,
                                profile_id=args.profile, name=args.name)
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    clips = sum(len(track["clips"]) for track in project["tracks"])
    print(f"wrote {args.out} · {clips} clips · {len(project['assets'])} assets · "
          f"{project['profile']['fps']['num']} fps · duration {project['duration']} ticks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
