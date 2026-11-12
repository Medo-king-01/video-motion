#!/usr/bin/env python3
"""EDL export (B6b): hand a timeline to another editor as CMX3600, without pretending to render.

The owner's delivery decision was EDL first, because it is the least committal format: cuts, sources and
timecodes, no effects, no project files, no vendor lock. The exporter reads the unified project (the same
object `timeline_session` edits), emits one event per enabled clip, and writes a sidecar manifest so the
result can be re-checked later byte for byte.

    python3 tools/edl_export.py build project.json -o out/project.edl
    python3 tools/edl_export.py check out/project.edl.json

Exit codes: 0 ok · 1 project/EDL refused (E-codes) · 2 unreadable file.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from unified_project_check import validate  # noqa: E402

VERSION = 1
TIMEBASE = 240_000
MAX_EVENTS = 999
CHANNELS = {"video": "V", "audio": "A"}
EVENT_RE = re.compile(
    r"^(?P<n>\d{3})  (?P<reel>\S{1,8}) +(?P<ch>[VA]2?) +(?P<tr>C|D)(?: +(?P<frames>\d{1,5}))? +"
    r"(?P<si>\d{2}:\d{2}:\d{2}:\d{2}) (?P<so>\d{2}:\d{2}:\d{2}:\d{2}) "
    r"(?P<ri>\d{2}:\d{2}:\d{2}:\d{2}) (?P<ro>\d{2}:\d{2}:\d{2}:\d{2})$")
MANIFEST_FIELDS = {"version", "source", "fps", "frameTicks", "title", "events", "totals"}
EVENT_FIELDS = {"n", "clipId", "trackId", "assetId", "fileName", "reel", "channel", "still", "dissolve",
                "sourceIn", "sourceOut",
                "recordIn", "recordOut", "sourceInTc", "sourceOutTc", "recordInTc", "recordOutTc"}
# A dissolve is written the CMX way: the incoming event carries `D <frames>`, and both events are widened by
# half its length so the transition is centred on the cut the project declares.
DISSOLVE_FIELD = "{frames:5d}"


class EdlError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"{code} {message}")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _fps(project: dict) -> tuple[int, int]:
    profile = project.get("profile") or {}
    fps = profile.get("fps") or {}
    num, den = fps.get("num"), fps.get("den")
    if not _is_int(num) or not _is_int(den) or num <= 0 or den <= 0:
        raise EdlError("E02", "profile.fps needs positive integers")
    if den != 1:
        raise EdlError("E02", f"CMX3600 export is non-drop integer fps only (got {num}/{den})")
    return num, den


def reel_for(uri: str) -> str:
    """CMX reels are short tags: basename, uppercase, alphanumerics, max 8."""
    stem = Path(str(uri).replace("\\", "/")).stem.upper()
    tag = re.sub(r"[^A-Z0-9]", "_", stem).strip("_") or "AX"
    return tag[:8]


def timecode(ticks: int, fps: int, frame_ticks: int) -> str:
    frames = ticks // frame_ticks
    total_seconds, frame = divmod(frames, fps)
    minutes, second = divmod(total_seconds, 60)
    hour, minute = divmod(minutes, 60)
    return f"{hour:02d}:{minute:02d}:{second:02d}:{frame:02d}"


def build_edl(project: dict, *, title: str | None = None) -> tuple[str, dict]:
    """Project → (CMX3600 text, manifest). Refuses anything the format cannot express."""
    errors = validate(project)
    if errors:
        raise EdlError("E01", "project is invalid: " + "; ".join(errors))
    fps, _ = _fps(project)
    frame_ticks = project["timebase"] // fps
    if project["timebase"] % fps:
        raise EdlError("E02", f"timebase {project['timebase']} does not divide {fps} fps into whole frames")
    assets = {asset["id"]: asset for asset in project.get("assets") or []}
    if not assets:
        raise EdlError("E03", "project has no assets; an EDL needs a source per event")

    events: list[dict] = []
    by_clip: dict[str, dict] = {}
    audio_seen = 0
    for track in project["tracks"]:
        if not track["enabled"]:
            continue
        if track["kind"] not in CHANNELS:
            raise EdlError("E05", f"track {track['id']}: {track['kind']} cannot be expressed in CMX3600")
        if track["kind"] == "audio":
            audio_seen += 1
            channel = "A" if audio_seen == 1 else f"A{audio_seen}"
        else:
            channel = "V"
        for clip in track["clips"]:
            asset = assets.get(clip["assetId"])
            if asset is None:
                raise EdlError("E03", f"clip {clip['id']}: unknown asset {clip['assetId']!r}")
            still = asset["kind"] == "image" and track["kind"] == "video"
            if asset["kind"] != track["kind"] and not still:
                raise EdlError("E03", f"clip {clip['id']}: {asset['kind']} asset on a {track['kind']} track")
            if still:
                # A still has no source duration: it is held from 0 for exactly the clip length.
                source_in, source_out = 0, clip["duration"]
            else:
                source_in, source_out = clip["sourceIn"], clip["sourceIn"] + clip["duration"]
            record_in, record_out = clip["start"], clip["start"] + clip["duration"]
            for name, value in (("sourceIn", source_in), ("sourceOut", source_out),
                                ("recordIn", record_in), ("recordOut", record_out)):
                if value % frame_ticks:
                    raise EdlError("E04", f"clip {clip['id']}: {name} {value} is not on a {frame_ticks}-tick "
                                          "frame boundary — round it in the timeline first")
            if record_out > project["duration"]:
                raise EdlError("E04", f"clip {clip['id']}: ends at {record_out} beyond project duration "
                                      f"{project['duration']}")
            if not still and asset.get("duration") is not None and source_out > asset["duration"]:
                raise EdlError("E04", f"clip {clip['id']}: reads to {source_out} beyond asset duration "
                                      f"{asset['duration']}")
            if clip["duration"] <= 0:
                raise EdlError("E04", f"clip {clip['id']}: zero length")
            event = {
                "clipId": clip["id"], "trackId": track["id"], "assetId": asset["id"],
                "fileName": Path(str(asset["uri"]).replace("\\", "/")).name,
                "reel": reel_for(asset["uri"]), "channel": channel, "still": still, "dissolve": 0,
                "sourceIn": source_in, "sourceOut": source_out,
                "recordIn": record_in, "recordOut": record_out,
            }
            events.append(event)
            by_clip[clip["id"]] = event

    for track in project["tracks"]:
        if not track["enabled"]:
            continue
        for transition in track.get("transitions") or []:
            source, target = by_clip.get(transition["fromClipId"]), by_clip.get(transition["toClipId"])
            if source is None or target is None:
                raise EdlError("E10", f"transition {transition['id']}: both clips must be exported")
            half = transition["duration"] // 2
            if half % frame_ticks:
                raise EdlError("E04", f"transition {transition['id']}: half of {transition['duration']} ticks "
                                      f"is not on a {frame_ticks}-tick frame boundary")
            source_asset = assets[source["assetId"]]
            target_asset = assets[target["assetId"]]
            if not source["still"] and source_asset.get("duration") is not None and \
                    source["sourceOut"] + half > source_asset["duration"]:
                raise EdlError("E10", f"transition {transition['id']}: clip {source['clipId']} needs "
                                      f"{half} ticks of tail handle the media does not have")
            if not target["still"] and target["sourceIn"] - half < 0:
                raise EdlError("E10", f"transition {transition['id']}: clip {target['clipId']} needs "
                                      f"{half} ticks of head handle the media does not have")
            source["recordOut"] += half
            source["sourceOut"] += half
            target["recordIn"] -= half
            if not target["still"]:
                # A still is held from source zero, so only its record position can move earlier.
                target["sourceIn"] -= half
            target["dissolve"] = transition["duration"] // frame_ticks

    if not events:
        raise EdlError("E05", "no enabled clips — an empty EDL is not a deliverable")
    if len(events) > MAX_EVENTS:
        raise EdlError("E07", f"{len(events)} events exceed the CMX3600 limit of {MAX_EVENTS}")

    last_by_channel: dict[str, tuple[int, int]] = {}
    for event in events:
        previous = last_by_channel.get(event["channel"])
        if previous is not None:
            allowed = event["dissolve"] * frame_ticks
            overlap = previous[0] - event["recordIn"]
            if overlap > allowed:
                raise EdlError("E06", f"clip {event['clipId']}: overlaps another event on channel "
                                      f"{event['channel']} — CMX3600 cannot stack a channel")
        last_by_channel[event["channel"]] = (event["recordOut"], event["dissolve"])

    events.sort(key=lambda event: (event["channel"] != "V", event["recordIn"], event["trackId"],
                                   event["clipId"]))
    name, text = _render(title or project.get("name") or project["id"], events, fps, frame_ticks)
    return text, _manifest(project.get("name") or project["id"], project, events, fps, frame_ticks,
                           name, project["duration"])


def plan_events(plan: dict) -> tuple[list[dict], int, int]:
    """cut-plan → EDL events for the **kept** cuts, assembled gaplessly on one video channel.

    Seconds are floats in a plan, ticks are not, so each boundary is rounded to the nearest frame once
    (`frames = round(seconds × fps)`); a range that collapses to zero frames is refused, not nudged.
    """
    if not isinstance(plan, dict) or plan.get("version") != 1:
        raise EdlError("E01", "plan must be an object with version 1")
    if set(plan) != {"version", "source", "video", "settings", "cuts", "totals"}:
        raise EdlError("E01", "plan needs exactly version/source/video/settings/cuts/totals")
    source = plan["source"]
    fps = source.get("fps") if isinstance(source, dict) else None
    if isinstance(fps, float) and fps.is_integer():
        fps = int(fps)
    if not _is_int(fps) or fps <= 0:
        raise EdlError("E02", f"CMX3600 export needs integer fps (plan says {source.get('fps')!r})")
    frame_ticks = TIMEBASE // fps
    if TIMEBASE % fps:
        raise EdlError("E02", f"timebase {TIMEBASE} does not divide {fps} fps into whole frames")
    cuts = plan.get("cuts")
    if not isinstance(cuts, list) or not cuts:
        raise EdlError("E01", "plan needs a non-empty cuts[] list")

    kept, events, cursor = 0, [], 0
    for cut in cuts:
        if not isinstance(cut, dict) or not isinstance(cut.get("id"), str):
            raise EdlError("E01", "every cut needs an id")
        if not isinstance(cut.get("keep"), bool):
            raise EdlError("E01", f"cut {cut['id']}: keep must be a boolean")
        start, end = cut.get("in"), cut.get("out")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or end <= start:
            raise EdlError("E04", f"cut {cut['id']}: requires in < out")
        start_frame, end_frame = round(start * fps), round(end * fps)
        if end_frame <= start_frame:
            raise EdlError("E04", f"cut {cut['id']}: collapses to zero frames at {fps} fps")
        if not cut["keep"]:
            continue
        kept += 1
        length = (end_frame - start_frame) * frame_ticks
        events.append({
            "clipId": cut["id"], "trackId": "v1", "assetId": "source",
            "fileName": Path(str(source.get("name") or "source")).name,
            "reel": reel_for(source.get("name") or "source"), "channel": "V", "still": False,
            "dissolve": 0,
            "sourceIn": start_frame * frame_ticks, "sourceOut": end_frame * frame_ticks,
            "recordIn": cursor, "recordOut": cursor + length,
        })
        cursor += length

    if not events:
        raise EdlError("E05", "every cut is rejected — nothing to deliver")
    if len(events) > MAX_EVENTS:
        raise EdlError("E07", f"{len(events)} kept cuts exceed the CMX3600 limit of {MAX_EVENTS}")
    return events, fps, frame_ticks


def build_from_plan(plan: dict, *, title: str | None = None) -> tuple[str, dict]:
    """cut-plan → (EDL text, manifest). A rejected cut simply has no event."""
    events, fps, frame_ticks = plan_events(plan)
    total = events[-1]["recordOut"]
    name, text = _render(title or plan["source"].get("name") or "cut plan", events, fps, frame_ticks)
    return text, _manifest("cut-plan", plan, events, fps, frame_ticks, name, total)


def _render(raw_title, events: list[dict], fps: int, frame_ticks: int) -> tuple[str, str]:
    raw_name = " ".join(str(raw_title).split())
    name = re.sub(r"[^ -~]", "_", raw_name)[:48].rstrip() or "TIMELINE"
    lines = [f"TITLE: {name}", "FCM: NON-DROP FRAME"]
    if raw_name != name:
        lines.append(f"* PROJECT NAME: {raw_name}")
    for index, event in enumerate(events, 1):
        event["n"] = index
        for key in ("sourceIn", "sourceOut", "recordIn", "recordOut"):
            event[key + "Tc"] = timecode(event[key], fps, frame_ticks)
        transition = "C        " if not event["dissolve"] else "D " + DISSOLVE_FIELD.format(frames=event["dissolve"])
        lines.append(f"{index:03d}  {event['reel']:<8}  {event['channel']:<4} {transition} "
                     f"{event['sourceInTc']} {event['sourceOutTc']} "
                     f"{event['recordInTc']} {event['recordOutTc']}")
        lines.append(f"* FROM CLIP NAME: {event['fileName']}")
        if event["still"]:
            lines.append("* STILL: held for the clip length (source 0 → duration)")
        lines.append(f"* CLIP {event['clipId']} | TRACK {event['trackId']} | ASSET {event['assetId']}")
    return name, "\n".join(lines) + "\n"


def _manifest(source_name: str, payload: dict, events: list[dict], fps: int, frame_ticks: int,
              name: str, duration_ticks: int) -> dict:
    return {
        "version": VERSION,
        "source": {"name": source_name, "sha256": hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()},
        "fps": fps, "frameTicks": frame_ticks, "title": name,
        "events": events,
        "totals": {"events": len(events), "durationTc": timecode(duration_ticks, fps, frame_ticks)},
    }


def parse_edl(text: str) -> list[dict]:
    """E08: read an EDL the way another tool would — header, numbering, arrow directions."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) < 3 or not lines[0].startswith("TITLE: ") or lines[1] != "FCM: NON-DROP FRAME":
        raise EdlError("E08", "edl must start with TITLE: and FCM: NON-DROP FRAME")
    events: list[dict] = []
    for line in lines[2:]:
        if line.startswith("*"):
            continue
        match = EVENT_RE.match(line)
        if not match:
            raise EdlError("E08", f"unreadable event line: {line!r}")
        event = match.groupdict()
        for key in ("si", "so", "ri", "ro"):
            if not _tc_ordered(event[key]):
                raise EdlError("E08", f"event {event['n']}: timecode {event[key]} has invalid fields")
        if event["so"] <= event["si"] or event["ro"] <= event["ri"]:
            raise EdlError("E08", f"event {event['n']}: out must be after in")
        events.append(event)
    numbers = [int(event["n"]) for event in events]
    if numbers != list(range(1, len(events) + 1)):
        raise EdlError("E08", "events must be numbered 1..n without gaps")
    return events


def _tc_ordered(value: str) -> bool:
    hour, minute, second, frame = (int(part) for part in value.split(":"))
    return minute < 60 and second < 60 and frame < 100


def validate_manifest(data: dict) -> list[str]:
    """E01 shape · E04 timing · E09 totals/manifest drift."""
    if not isinstance(data, dict):
        return ["E01 root: manifest must be an object"]
    if data.get("version") != VERSION:
        return [f"E01 version: only version {VERSION} is accepted"]
    if set(data) != MANIFEST_FIELDS:
        return [f"E01 root: needs exactly {sorted(MANIFEST_FIELDS)}"]
    events = data.get("events")
    if not isinstance(events, list) or not events:
        return ["E01 events: non-empty list required"]
    errors: list[str] = []
    fps = data.get("fps")
    if not _is_int(fps) or fps <= 0:
        errors.append("E02 fps: positive integer required")
    for index, event in enumerate(events):
        where = f"events[{index}]"
        if not isinstance(event, dict) or set(event) != EVENT_FIELDS:
            errors.append(f"E01 {where}: needs exactly {sorted(EVENT_FIELDS)}")
            continue
        if event["n"] != index + 1:
            errors.append(f"E04 {where}: event number {event['n']} should be {index + 1}")
        if not _is_int(event["sourceIn"]) or not _is_int(event["sourceOut"]) or \
                not _is_int(event["recordIn"]) or not _is_int(event["recordOut"]):
            errors.append(f"E04 {where}: ticks must be integers")
        elif event["sourceOut"] <= event["sourceIn"] or event["recordOut"] <= event["recordIn"]:
            errors.append(f"E04 {where}: out must be after in")
        if not _is_int(event.get("dissolve")) or event["dissolve"] < 0 or event["dissolve"] % 2:
            errors.append(f"E01 {where}.dissolve: zero, or a positive even frame count")
        frame_ticks = data.get("frameTicks")
        if _is_int(frame_ticks) and frame_ticks > 0 and _is_int(event["sourceIn"]):
            for key in ("sourceIn", "sourceOut", "recordIn", "recordOut"):
                if event[key] % frame_ticks:
                    errors.append(f"E04 {where}.{key}: not on a frame boundary")
    totals = data.get("totals")
    if not isinstance(totals, dict) or set(totals) != {"events", "durationTc"}:
        errors.append("E09 totals: needs exactly ['durationTc', 'events']")
    elif totals["events"] != len(events):
        errors.append(f"E09 totals.events: says {totals['events']} but there are {len(events)}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CMX3600 EDL export from a unified project.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="project.json → .edl + .edl.json")
    build.add_argument("project", type=Path)
    build.add_argument("-o", "--out", type=Path, required=True)
    build.add_argument("--manifest", type=Path, default=None)
    build.add_argument("--title", default=None)
    check = sub.add_parser("check", help="validate an exported manifest (and its EDL text)")
    check.add_argument("manifest", type=Path)
    check.add_argument("--edl", type=Path, default=None)
    args = parser.parse_args(argv)

    if args.command == "check":
        try:
            data = json.loads(args.manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"error: cannot read {args.manifest}: {exc}", file=sys.stderr)
            return 2
        errors = validate_manifest(data)
        if args.edl is not None:
            try:
                events = parse_edl(args.edl.read_text(encoding="utf-8"))
            except (OSError, EdlError) as exc:
                print(f"error: {exc}", file=sys.stderr)
                return 2 if isinstance(exc, OSError) else 1
            if len(events) != len(data.get("events", [])):
                errors.append(f"E09 edl: {len(events)} events but the manifest lists "
                              f"{len(data.get('events', []))}")
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print(f"Valid EDL · {len(data['events'])} events · {data['fps']} fps · duration {data['totals']['durationTc']}")
        return 0

    try:
        project = json.loads(args.project.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read {args.project}: {exc}", file=sys.stderr)
        return 2
    try:
        text, manifest = build_edl(project, title=args.title)
    except EdlError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(text, encoding="utf-8")
    sidecar = args.manifest or args.out.with_suffix(args.out.suffix + ".json")
    sidecar.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out} · {len(manifest['events'])} events · {manifest['fps']} fps · "
          f"duration {manifest['totals']['durationTc']} · {sidecar}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
