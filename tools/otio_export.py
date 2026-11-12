#!/usr/bin/env python3
"""OTIO export (B6ه): the project as an OpenTimelineIO timeline — effects and keyframes included.

EDL carries cuts only. OTIO is JSON, so it can also carry what the unified project already models: per-clip
effects, keyframe curves, disabled tracks and the exact tick values. Transitions do not exist in the model,
so the file never claims them; what is not modelled is named in the report, not invented.

    python3 tools/otio_export.py build project.json -o out/timeline.otio
    python3 tools/otio_export.py check out/timeline.otio

Exit codes: 0 ok · 1 project/OTIO refused (O-codes) · 2 unreadable file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402

VERSION = 1
KINDS = {"video": "Video", "audio": "Audio", "text": "Video", "graphics": "Video"}
TRACK_FIELDS = {"OTIO_SCHEMA", "name", "kind", "children", "metadata"}
TRANSITION_FIELDS = {"OTIO_SCHEMA", "name", "transition_type", "in_offset", "out_offset", "metadata"}
CLIP_FIELDS = {"OTIO_SCHEMA", "name", "source_range", "media_reference", "metadata"}
RANGE_FIELDS = {"OTIO_SCHEMA", "start_time", "duration"}
TIME_FIELDS = {"OTIO_SCHEMA", "rate", "value"}


class OtioError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _time(value: float, rate: int) -> dict:
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": float(rate), "value": round(value, 6)}


def _frames(ticks: int, timebase: int, fps: int) -> float:
    """Ticks → frames at the timeline rate; exact when the tick is on a frame boundary."""
    exact = ticks * fps / timebase
    return exact


def build(project: dict, *, name: str | None = None) -> dict:
    errors = validate(project)
    if errors:
        raise OtioError("O01", "project is invalid: " + "; ".join(errors))
    fps = project["profile"]["fps"]
    if fps["den"] != 1:
        raise OtioError("O02", f"OTIO export needs an integer rate (got {fps['num']}/{fps['den']})")
    rate = fps["num"]
    timebase = project["timebase"]
    assets = {asset["id"]: asset for asset in project.get("assets") or []}
    if not assets:
        raise OtioError("O03", "project has no assets; every clip needs a media reference")

    children = []
    for track in project["tracks"]:
        clips = []
        for clip in track["clips"]:
            asset = assets.get(clip["assetId"])
            if asset is None:
                raise OtioError("O03", f"clip {clip['id']}: unknown asset {clip['assetId']!r}")
            if clip["duration"] <= 0:
                raise OtioError("O04", f"clip {clip['id']}: zero length")
            if asset.get("duration") is not None and clip["sourceIn"] + clip["duration"] > asset["duration"]:
                raise OtioError("O04", f"clip {clip['id']}: reads beyond the asset's duration")
            start = _frames(clip["sourceIn"], timebase, rate)
            length = _frames(clip["duration"], timebase, rate)
            available = asset.get("duration")
            media = {"OTIO_SCHEMA": "ExternalReference.1", "target_url": asset["uri"],
                     "metadata": {"medo": {"assetId": asset["id"], "kind": asset["kind"],
                                           "sha256": asset["sha256"]}}}
            if available is not None:
                media["available_range"] = {"OTIO_SCHEMA": "TimeRange.1", "start_time": _time(0, rate),
                                            "duration": _time(_frames(available, timebase, rate), rate)}
            clips.append({
                "OTIO_SCHEMA": "Clip.1", "name": clip["id"],
                "source_range": {"OTIO_SCHEMA": "TimeRange.1", "start_time": _time(start, rate),
                                 "duration": _time(length, rate)},
                "media_reference": media,
                "metadata": {"medo": {"clipId": clip["id"], "assetId": asset["id"],
                                      "trackId": track["id"], "kind": clip["kind"],
                                      "start": clip["start"], "duration": clip["duration"],
                                      "sourceIn": clip["sourceIn"],
                                      "effects": clip.get("effects", []),
                                      "keyframes": clip.get("keyframes", [])}},
            })
        clips.sort(key=lambda item: item["metadata"]["medo"]["start"])
        for transition in track.get("transitions") or []:
            # OTIO places a transition at the cut: half its length eats into each neighbour.
            half = _frames(transition["duration"] // 2, timebase, rate)
            item = {"OTIO_SCHEMA": "Transition.1", "name": transition["id"],
                    "transition_type": "SMPTE_Dissolve",
                    "in_offset": _time(half, rate), "out_offset": _time(half, rate),
                    "metadata": {"medo": {"transitionId": transition["id"], "kind": transition["kind"],
                                          "fromClipId": transition["fromClipId"],
                                          "toClipId": transition["toClipId"],
                                          "duration": transition["duration"]}}}
            position = next((index for index, clip in enumerate(clips)
                             if clip["name"] == transition["fromClipId"]), len(clips) - 1)
            clips.insert(position + 1, item)
        children.append({
            "OTIO_SCHEMA": "Track.1", "name": track["id"], "kind": KINDS[track["kind"]],
            "children": clips,
            "metadata": {"medo": {"trackId": track["id"], "trackKind": track["kind"],
                                  "enabled": track["enabled"]}},
        })

    if not any(track["children"] for track in children):
        raise OtioError("O04", "the timeline has no clips to deliver")

    payload = {
        "OTIO_SCHEMA": "Timeline.1",
        "name": name or project.get("name") or project["id"],
        "global_start_time": _time(0, rate),
        "metadata": {"medo": {"version": VERSION, "project": project["id"], "timebase": timebase,
                              "seed": project.get("seed", 0),
                              "durationTicks": project["duration"],
                              "durationFrames": round(project["duration"] * rate / timebase, 6),
                              "profile": project["profile"],
                              "effects": sum(len(c.get("effects", [])) for t in project["tracks"] for c in t["clips"]),
                              "keyframes": sum(len(c.get("keyframes", [])) for t in project["tracks"] for c in t["clips"]),
                              "transitions": sum(len(t.get("transitions") or []) for t in project["tracks"]),
                              "transitionKinds": sorted({transition["kind"] for t in project["tracks"]
                                                         for transition in (t.get("transitions") or [])})}},
        "tracks": {"OTIO_SCHEMA": "Stack.1", "name": "tracks", "children": children,
                   "metadata": {"medo": {"sha256": _sha(json.dumps(project, ensure_ascii=False, sort_keys=True).encode("utf-8"))}}},
    }
    return payload


def validate_timeline(payload: dict) -> list[str]:
    """O05: structure another tool would rely on — schema names, ranges, rates, references."""
    if not isinstance(payload, dict) or payload.get("OTIO_SCHEMA") != "Timeline.1":
        return ["O01 OTIO_SCHEMA: Timeline.1 required"]
    if set(payload) != {"OTIO_SCHEMA", "name", "global_start_time", "metadata", "tracks"}:
        return ["O01 root: unexpected fields"]
    errors: list[str] = []
    rate = payload["global_start_time"].get("rate")
    tracks = payload.get("tracks") or {}
    if tracks.get("OTIO_SCHEMA") != "Stack.1":
        errors.append("O05 tracks: Stack.1 required")
    children = tracks.get("children")
    if not isinstance(children, list) or not children:
        return errors + ["O05 tracks.children: non-empty list required"]
    for index, track in enumerate(children):
        where = f"tracks[{index}]"
        if not isinstance(track, dict) or set(track) != TRACK_FIELDS:
            errors.append(f"O05 {where}: needs exactly {sorted(TRACK_FIELDS)}")
            continue
        if track["OTIO_SCHEMA"] != "Track.1" or track["kind"] not in ("Video", "Audio"):
            errors.append(f"O05 {where}: must be a Track.1 of kind Video/Audio")
        for clip_index, clip in enumerate(track["children"]):
            cwhere = f"{where}.children[{clip_index}]"
            if isinstance(clip, dict) and clip.get("OTIO_SCHEMA") == "Transition.1":
                if set(clip) != TRANSITION_FIELDS:
                    errors.append(f"O05 {cwhere}: a transition needs exactly {sorted(TRANSITION_FIELDS)}")
                    continue
                if clip["transition_type"] != "SMPTE_Dissolve":
                    errors.append(f"O05 {cwhere}.transition_type: only SMPTE_Dissolve is written")
                for key in ("in_offset", "out_offset"):
                    time = clip[key]
                    if not isinstance(time, dict) or set(time) != TIME_FIELDS:
                        errors.append(f"O05 {cwhere}.{key}: malformed RationalTime")
                    elif time["rate"] != rate:
                        errors.append(f"O05 {cwhere}.{key}: rate {time['rate']} != timeline {rate}")
                    elif not time["value"] > 0:
                        errors.append(f"O05 {cwhere}.{key}: must be positive")
                if clip_index == 0:
                    errors.append(f"O05 {cwhere}: a transition cannot open a track")
                continue
            if not isinstance(clip, dict) or set(clip) != CLIP_FIELDS:
                errors.append(f"O05 {cwhere}: needs exactly {sorted(CLIP_FIELDS)}")
                continue
            if clip["OTIO_SCHEMA"] != "Clip.1":
                errors.append(f"O05 {cwhere}: Clip.1 required")
            source = clip["source_range"]
            if not isinstance(source, dict) or set(source) != RANGE_FIELDS:
                errors.append(f"O05 {cwhere}.source_range: needs exactly {sorted(RANGE_FIELDS)}")
                continue
            for key in ("start_time", "duration"):
                time = source[key]
                if not isinstance(time, dict) or set(time) != TIME_FIELDS:
                    errors.append(f"O05 {cwhere}.source_range.{key}: malformed RationalTime")
                elif time["rate"] != rate:
                    errors.append(f"O05 {cwhere}.source_range.{key}: rate {time['rate']} != timeline {rate}")
                elif key == "duration" and not time["value"] > 0:
                    errors.append(f"O05 {cwhere}.source_range.duration: must be positive")
            media = clip.get("media_reference") or {}
            if media.get("OTIO_SCHEMA") != "ExternalReference.1" or not media.get("target_url"):
                errors.append(f"O05 {cwhere}.media_reference: external target_url required")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unified project → OpenTimelineIO JSON.")
    sub = parser.add_subparsers(dest="command", required=True)
    build_cmd = sub.add_parser("build", help="project.json → timeline.otio")
    build_cmd.add_argument("project", type=Path)
    build_cmd.add_argument("-o", "--out", type=Path, required=True)
    build_cmd.add_argument("--name", default=None)
    check = sub.add_parser("check", help="validate an exported .otio")
    check.add_argument("timeline", type=Path)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            payload = json.loads(args.timeline.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.timeline}: {exc}", file=sys.stderr)
            return 2
        errors = validate_timeline(payload)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        clips = sum(len(track["children"]) for track in payload["tracks"]["children"])
        print(f"Valid OTIO · {clips} clips · {len(payload['tracks']['children'])} tracks · "
              f"{payload['global_start_time']['rate']:g} fps")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    try:
        payload = build(project, name=args.name)
    except OtioError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    errors = validate_timeline(payload)
    if errors:
        print("error: built timeline failed its own check: " + "; ".join(errors), file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    meta = payload["metadata"]["medo"]
    clips = sum(len(track["children"]) for track in payload["tracks"]["children"])
    print(f"wrote {args.out} · {clips} clips · {payload['global_start_time']['rate']:g} fps · "
          f"{meta['effects']} effects · {meta['keyframes']} keyframe curves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
