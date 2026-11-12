#!/usr/bin/env python3
"""OTIO import (B7ج): a Medo timeline back into the unified project — or a refusal, never a guess.

`otio_export.py` writes the exact tick values, effects and keyframes into `metadata.medo`. Import reads only
those, checks them against the OTIO structure, and refuses a file that disagrees with itself or that came from
another tool: reconstructing a project out of visual clip placement would be inventing an edit.

    python3 tools/otio_import.py build timeline.otio -o project.json
    python3 tools/otio_import.py check project.json
    python3 tools/otio_import.py roundtrip timeline.otio      # import → export, compare the two files

Exit codes: 0 ok · 1 timeline refused or inconsistent (N-codes) · 2 unreadable file.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import otio_export  # noqa: E402
from unified_project_check import validate  # noqa: E402

SUPPORTED = 1
TRACK_KINDS = {"Video": "video", "Audio": "audio"}
DEFAULT_TIMEBASE = 240_000


class ImportError_(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _ticks(value: float, rate: float, timebase: int, where: str) -> int:
    exact = value * timebase / rate
    if abs(exact - round(exact)) > 1e-6:
        raise ImportError_("N03", f"{where}: {value} frames at {rate:g} fps is not a whole tick "
                                  f"(would need {exact:.6f})")
    return int(round(exact))


def build(payload: dict) -> dict:
    errors = otio_export.validate_timeline(payload)
    if errors:
        raise ImportError_("N01", "; ".join(errors))
    meta = payload.get("metadata", {}).get("medo")
    if not isinstance(meta, dict):
        raise ImportError_("N02", "not a Medo timeline: metadata.medo is missing, and guessing an edit from "
                                  "clip placement is not an import")
    if meta.get("version") != SUPPORTED:
        raise ImportError_("N02", f"timeline version {meta.get('version')!r} is not supported "
                                  f"(only {SUPPORTED})")
    timebase = meta.get("timebase", DEFAULT_TIMEBASE)
    if not isinstance(timebase, int) or timebase <= 0:
        raise ImportError_("N03", f"timebase {timebase!r} is unusable")
    rate = payload["global_start_time"]["rate"]
    if not float(rate).is_integer() or rate <= 0:
        raise ImportError_("N03", f"timeline rate {rate!r} is not an integer")
    fps = int(rate)

    assets: list[dict] = []
    seen_assets: set[str] = set()
    tracks: list[dict] = []
    seen_tracks: set[str] = set()
    seen_clips: set[str] = set()

    for track_index, track in enumerate(payload["tracks"]["children"]):
        tmeta = track.get("metadata", {}).get("medo") or {}
        track_id = tmeta.get("trackId")
        if not isinstance(track_id, str) or not track_id:
            raise ImportError_("N04", f"tracks[{track_index}]: metadata.medo.trackId is missing")
        if track_id in seen_tracks:
            raise ImportError_("N04", f"tracks[{track_index}]: duplicate track id {track_id!r}")
        seen_tracks.add(track_id)
        kind = tmeta.get("trackKind") or TRACK_KINDS.get(track["kind"])
        if kind not in ("video", "audio", "text", "graphics"):
            raise ImportError_("N04", f"track {track_id}: unknown track kind {kind!r}")
        if track["kind"] != otio_export.KINDS[kind]:
            raise ImportError_("N04", f"track {track_id}: OTIO kind {track['kind']} disagrees with "
                                      f"trackKind {kind!r}")
        enabled = tmeta.get("enabled", True)
        if not isinstance(enabled, bool):
            raise ImportError_("N04", f"track {track_id}: enabled must be a boolean")
        clips = []
        transitions = []
        for clip_index, clip in enumerate(track["children"]):
            where = f"tracks.{track_id}.children[{clip_index}]"
            if clip.get("OTIO_SCHEMA") == "Transition.1":
                tmeta = (clip.get("metadata") or {}).get("medo") or {}
                if clip.get("transition_type") != "SMPTE_Dissolve":
                    raise ImportError_("N05", f"{where}: {clip.get('transition_type')!r} would have to be "
                                              "invented as a crossfade")
                if tmeta.get("kind") != "crossfade":
                    raise ImportError_("N05", f"{where}: only a crossfade can be reconstructed, "
                                              f"not {tmeta.get('kind')!r}")
                length = tmeta.get("duration")
                if not isinstance(length, int) or length <= 0:
                    raise ImportError_("N04", f"{where}: metadata.medo.duration is missing")
                half = _ticks(clip["in_offset"]["value"], rate, timebase, f"{where}.in_offset")
                if half * 2 != length or _ticks(clip["out_offset"]["value"], rate, timebase,
                                                f"{where}.out_offset") != half:
                    raise ImportError_("N04", f"{where}: in/out offsets disagree with duration {length}")
                for key in ("transitionId", "fromClipId", "toClipId"):
                    if not isinstance(tmeta.get(key), str) or not tmeta[key]:
                        raise ImportError_("N04", f"{where}: metadata.medo.{key} is missing")
                transitions.append({"id": tmeta["transitionId"], "kind": "crossfade",
                                    "fromClipId": tmeta["fromClipId"], "toClipId": tmeta["toClipId"],
                                    "duration": length})
                continue
            cmeta = clip.get("metadata", {}).get("medo") or {}
            clip_id = cmeta.get("clipId")
            if not isinstance(clip_id, str) or not clip_id:
                raise ImportError_("N04", f"{where}: metadata.medo.clipId is missing")
            if clip_id != clip.get("name"):
                raise ImportError_("N04", f"{where}: name {clip.get('name')!r} disagrees with clipId {clip_id!r}")
            if clip_id in seen_clips:
                raise ImportError_("N04", f"{where}: duplicate clip id {clip_id!r}")
            seen_clips.add(clip_id)
            if cmeta.get("trackId") not in (None, track_id):
                raise ImportError_("N04", f"{where}: metadata names track {cmeta.get('trackId')!r}, "
                                          f"but the clip sits on {track_id!r}")
            # OTIO's source_range describes the media window (sourceIn + duration); placement on the track
            # lives only in the metadata, because OTIO expresses position through gaps, not per-clip starts.
            source_in = _ticks(clip["source_range"]["start_time"]["value"], rate, timebase, f"{where}.start_time")
            length = _ticks(clip["source_range"]["duration"]["value"], rate, timebase, f"{where}.duration")
            if cmeta.get("sourceIn") != source_in or cmeta.get("duration") != length:
                raise ImportError_("N04", f"{where}: metadata (sourceIn {cmeta.get('sourceIn')}, duration "
                                          f"{cmeta.get('duration')}) disagree with the range "
                                          f"({source_in}, {length})")
            if not isinstance(cmeta.get("start"), int) or cmeta["start"] < 0:
                raise ImportError_("N04", f"{where}: metadata.medo.start is missing")
            media = clip["media_reference"]
            mmeta = media.get("metadata", {}).get("medo") or {}
            asset_id = mmeta.get("assetId")
            if not isinstance(asset_id, str) or not asset_id:
                raise ImportError_("N04", f"{where}.media_reference: metadata.medo.assetId is missing")
            digest = mmeta.get("sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise ImportError_("N04", f"{where}.media_reference: a 64-character sha256 is required, "
                                          f"the project format verifies media by hash")
            asset_kind = mmeta.get("kind")
            if asset_kind not in ("image", "video", "audio", "text", "graphics"):
                raise ImportError_("N04", f"{where}.media_reference: unknown asset kind {asset_kind!r}")
            if cmeta.get("assetId") not in (None, asset_id):
                raise ImportError_("N04", f"{where}: clip metadata names asset {cmeta.get('assetId')!r} "
                                          f"but its reference is {asset_id!r}")
            if asset_id not in seen_assets:
                asset = {"id": asset_id, "kind": asset_kind, "uri": media["target_url"], "sha256": digest}
                available = media.get("available_range")
                if available is not None:
                    asset["duration"] = _ticks(available["duration"]["value"], rate, timebase,
                                               f"{where}.available_range")
                assets.append(asset)
                seen_assets.add(asset_id)
            clips.append({
                "id": clip_id, "kind": cmeta.get("kind", "media"), "assetId": asset_id,
                "start": cmeta["start"], "duration": length, "sourceIn": source_in,
                "effects": cmeta.get("effects") or [], "keyframes": cmeta.get("keyframes") or [],
            })
        if transitions:
            clips_by_id = {clip["id"] for clip in clips}
            for transition in transitions:
                if transition["fromClipId"] not in clips_by_id or transition["toClipId"] not in clips_by_id:
                    raise ImportError_("N05", f"transition {transition['id']}: names a clip that is not on "
                                              f"track {track_id!r}")
            entry = {"id": track_id, "kind": kind, "enabled": enabled, "clips": clips,
                     "transitions": transitions}
        else:
            entry = {"id": track_id, "kind": kind, "enabled": enabled, "clips": clips}
        tracks.append(entry)

    if not assets:
        raise ImportError_("N04", "the timeline carries no assets")
    duration = meta.get("durationTicks")
    if not isinstance(duration, int) or duration <= 0:
        raise ImportError_("N03", "metadata.medo.durationTicks is missing")
    seed = meta.get("seed")
    if not isinstance(seed, int):
        raise ImportError_("N03", "metadata.medo.seed is missing; the render seed changes the output")
    project = {
        "schemaVersion": "1.2" if any(track.get("transitions") for track in tracks) else "1.1",
        "id": str(meta.get("project") or "imported"),
        "name": payload.get("name") or "Imported timeline",
        "profile": meta.get("profile"),
        "timebase": timebase,
        "duration": duration,
        "seed": seed,
        "assets": assets,
        "tracks": tracks,
    }
    if not isinstance(project["profile"], dict):
        raise ImportError_("N03", "metadata.medo.profile is missing")
    problems = validate(project)
    if problems:
        raise ImportError_("N06", "the reconstructed project would be invalid: " + "; ".join(problems))
    return project


def roundtrip(payload: dict) -> tuple[dict, dict]:
    """Import then export again: the two timelines should say the same thing."""
    project = build(payload)
    return project, otio_export.build(project, name=payload.get("name"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenTimelineIO JSON → unified project.")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="timeline.otio → project.json")
    build_cmd.add_argument("timeline", type=Path)
    build_cmd.add_argument("-o", "--out", type=Path, required=True)
    check = sub.add_parser("check", help="validate a unified project file")
    check.add_argument("project", type=Path)
    trip = sub.add_parser("roundtrip", help="import a timeline and export it again")
    trip.add_argument("timeline", type=Path)
    trip.add_argument("-o", "--out", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            project = json.loads(args.project.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
            return 2
        errors = validate(project)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        clips = sum(len(track["clips"]) for track in project["tracks"])
        print(f"Valid project · {clips} clips · {len(project['tracks'])} tracks · {project['duration']} ticks")
        return 0

    try:
        payload = json.loads(args.timeline.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.timeline}: {exc}", file=sys.stderr)
        return 2
    try:
        if args.command == "roundtrip":
            project, again = roundtrip(payload)
            clips = sum(len(track["clips"]) for track in project["tracks"])
            print(f"Round trip · {clips} clips · {len(project['tracks'])} tracks · "
                  f"{project['duration']} ticks · {len(json.dumps(again))} bytes re-exported")
            if args.out:
                args.out.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return 0
        project = build(payload)
    except ImportError_ as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(project, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} · {sum(len(t['clips']) for t in project['tracks'])} clips · "
          f"{len(project['tracks'])} tracks · {project['duration']} ticks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
