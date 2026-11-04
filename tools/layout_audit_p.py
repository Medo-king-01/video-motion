#!/usr/bin/env python3
"""Screen-space layout and reverse-seek determinism audit for engine P.

    python3 tools/layout_audit_p.py --project projects/my-reel --out cache/layout-p-v1
    python3 tools/layout_audit_p.py --project projects/my-reel --out cache/layout-p-replay --replay

Mirrors `tools/layout_audit.mjs` (engine K) using engine P's native sprite geometry (`layout_p.py`):
- `L00`: invalid/missing registered box (including an unmeasured presenter `face_box`) or unknown zone
- `L01`: text ink outside its brand safe zone (`content` y200..1350, `caption` y1350..1500, `hud` y0..200, margin 40px)
- `L02`: overlapping text / protected `keep` boxes (>= 2 px on both axes)
- `L03`: text overlapping a measured presenter `face` box
- `R01` / `R02` (with `--replay`): full-frame RGB SHA-256 or layout snapshot changed on reverse-order re-evaluation
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
TEMPLATE_P = SKILL / "templates" / "procedural-reels"
sys.path.insert(0, str(SKILL / "scripts"))
from _safe_paths import checked_path  # noqa: E402

RED_RGB = (203, 39, 27)
FPS_LOCKED = 30


def _draw_issue_boxes(rgb, boxes: list[dict[str, Any]], offending_ids: set[str]):
    import cv2  # noqa: PLC0415

    canvas = rgb.copy()
    for box in boxes:
        if box.get("id") not in offending_ids:
            continue
        vals = [box.get(k) for k in ("x", "y", "w", "h")]
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v)) for v in vals):
            continue
        x, y, w, h = (float(v) for v in vals)
        if w <= 0 or h <= 0:
            continue
        p0 = (int(round(x)), int(round(y)))
        p1 = (int(round(x + w)), int(round(y + h)))
        cv2.rectangle(canvas, p0, p1, RED_RGB, 4)
    return canvas


def _save_png(path: Path, rgb) -> None:
    from PIL import Image  # noqa: PLC0415

    Image.fromarray(rgb, "RGB").save(path)


def _timeline_duration(project: Path, scenes_module: Any) -> float:
    beats_path = project / "plan" / "beats.json"
    if beats_path.is_file():
        beats = json.loads(beats_path.read_text(encoding="utf-8"))
        dur = beats.get("duration")
        if isinstance(dur, (int, float)) and not isinstance(dur, bool) and float(dur) > 0:
            return float(dur)
    bounds = getattr(scenes_module, "B", None)
    if isinstance(bounds, (list, tuple)) and bounds and float(bounds[-1]) > 0:
        return float(bounds[-1])
    raise RuntimeError("Could not determine engine-P timeline duration from plan/beats.json or scenes.B")


def _safe_abs(path: Path, *, tree: bool = False) -> Path:
    checked_path(Path(os.path.abspath(path)), tree=tree)
    return checked_path(path.resolve(), tree=tree)


def _run_in_project(args: argparse.Namespace) -> int:
    project = _safe_abs(args.project, tree=True)
    out = _safe_abs(args.out)
    if not project.is_dir() or not (project / "scenes.py").is_file():
        raise RuntimeError(f"{project} is not an engine-P project (scenes.py missing)")
    if out.exists():
        raise RuntimeError(f"Audit output exists; choose a fresh directory: {out}")
    if args.replay_only_flag_error:
        raise RuntimeError("Invalid flags")
    if args.fps != FPS_LOCKED:
        raise RuntimeError("Audit requires native 30 fps")
    if args.every < 1:
        raise RuntimeError("--every must be a positive frame stride")

    old_sys_path = list(sys.path)
    sys.path.insert(0, str(TEMPLATE_P))
    sys.path.insert(0, str(project))
    sys.modules.pop("scenes", None)
    old_cwd = Path.cwd()
    os.environ["REEL_DIR"] = str(project)
    os.environ["MEDO_MOTION_MODE"] = args.motion_mode

    try:
        os.chdir(project)
        import layout_p  # noqa: PLC0415
        import scenes  # noqa: PLC0415
        import text_direction as td  # noqa: PLC0415
        from resource_scope import ResourceScope  # noqa: PLC0415

        if args.motion_mode == "reduced" and getattr(scenes, "SUPPORTS_REDUCED_MOTION", False) is not True:
            raise RuntimeError("Reduced motion requires an explicit SUPPORTS_REDUCED_MOTION=True in scenes.py")

        beats_path = project / "plan" / "beats.json"
        if beats_path.is_file():
            beats = json.loads(beats_path.read_text(encoding="utf-8"))
            if beats.get("duration") is not None:
                report = td.validate(td.load(project), beats, td.load_copy(project), td.load_fonts(project) or None)
                if report["errors"]:
                    raise RuntimeError(
                        "Text direction incomplete — the agent must choose styles per scene:\n"
                        + "\n".join(report["errors"])
                    )

        duration = _timeline_duration(project, scenes)
        from_s = float(args.from_s)
        to_s = float(duration if args.to_s is None else args.to_s)
        if not (math.isfinite(from_s) and math.isfinite(to_s)) or from_s < 0 or to_s <= from_s:
            raise RuntimeError("Invalid --from / --to range")
        if to_s > duration + 1e-8:
            raise RuntimeError(f"Audit range end ({to_s:.3f}s) exceeds timeline duration ({duration:.3f}s)")

        render_frame = getattr(scenes, "render_frame", None)
        if not callable(render_frame):
            raise RuntimeError("scenes.py does not define a callable render_frame(t)")

        count = math.ceil((to_s - from_s) * args.fps - 1e-8)
        out.mkdir(parents=True, exist_ok=False)

        audit_frames: list[dict[str, Any]] = []
        fingerprints: list[dict[str, Any]] = []
        captured_text = 0
        screenshots = 0
        replay_failures = 0

        with ResourceScope() as resources:
            initializer = getattr(scenes, "init_resources", None)
            if initializer is not None:
                if not callable(initializer):
                    raise TypeError("init_resources must be callable")
                initializer(resources)

            for i in range(count):
                if i % args.every != 0 and i != count - 1:
                    continue
                t = from_s + i / args.fps
                layout_p.begin_frame()
                try:
                    image = render_frame(t)
                except BaseException:
                    layout_p.end_frame()
                    raise
                boxes = layout_p.end_frame()
                dtype_name = getattr(getattr(image, "dtype", None), "name", None)
                if getattr(image, "shape", None) != (1920, 1080, 3) or dtype_name != "uint8":
                    raise RuntimeError(f"engine P returned an invalid frame at index {i}: {getattr(image, 'shape', None)}")

                captured_text += sum(1 for b in boxes if b.get("kind") == "text")
                if args.replay:
                    fingerprints.append({
                        "index": i,
                        "hash": hashlib.sha256(image.tobytes()).hexdigest(),
                        "layout": json.dumps(boxes, sort_keys=True, ensure_ascii=False),
                    })
                issues = layout_p.audit_layout(boxes, check_platform_ui=args.platform_ui)
                if issues:
                    image_name = f"frame-{i}.png" if screenshots < 12 else None
                    audit_frames.append({
                        "frame": round(from_s * args.fps) + i,
                        "time": round(t, 6),
                        "issues": issues,
                        "boxes": boxes,
                        "image": image_name,
                    })
                    if image_name is not None:
                        annotated = _draw_issue_boxes(image, boxes, {bid for item in issues for bid in item["ids"]})
                        _save_png(out / image_name, annotated)
                        screenshots += 1

            if args.replay:
                replay_screenshots = 0
                for original in reversed(fingerprints):
                    idx = original["index"]
                    t = from_s + idx / args.fps
                    layout_p.begin_frame()
                    try:
                        image = render_frame(t)
                    except BaseException:
                        layout_p.end_frame()
                        raise
                    boxes = layout_p.end_frame()
                    digest = hashlib.sha256(image.tobytes()).hexdigest()
                    layout_ser = json.dumps(boxes, sort_keys=True, ensure_ascii=False)
                    r_issues: list[dict[str, Any]] = []
                    if digest != original["hash"]:
                        r_issues.append({
                            "code": "R01",
                            "ids": ["frame"],
                            "message": "Pixels changed when re-evaluating the same time in reverse order",
                            "expected": original["hash"],
                            "actual": digest,
                        })
                    if layout_ser != original["layout"]:
                        r_issues.append({
                            "code": "R02",
                            "ids": ["layout"],
                            "message": "Layout capture changed when re-evaluating the same time in reverse order",
                        })
                    if r_issues:
                        replay_failures += 1
                        image_name = f"replay-frame-{idx}.png" if replay_screenshots < 6 else None
                        audit_frames.append({
                            "frame": round(from_s * args.fps) + idx,
                            "time": round(t, 6),
                            "issues": r_issues,
                            "boxes": boxes,
                            "image": image_name,
                        })
                        if image_name is not None:
                            _save_png(out / image_name, image)
                            replay_screenshots += 1

        audit_frames.sort(key=lambda item: item["frame"])
        status = "incomplete" if captured_text == 0 else ("fail" if audit_frames else "pass")
        replay_status = (
            "not-requested"
            if not args.replay
            else ("fail" if replay_failures else ("pass" if fingerprints else "incomplete"))
        )
        report_doc = {
            "version": 1,
            "engine": "P",
            "status": status,
            "fps": args.fps,
            "from": from_s,
            "to": to_s,
            "every": args.every,
            "motionMode": args.motion_mode,
            "sampling": "all frames" if args.every == 1 else "sampled; brief collisions can be missed",
            "capturedText": captured_text,
            "replay": {
                "status": replay_status,
                "checkedFrames": len(fingerprints),
                "failedFrames": replay_failures,
                "order": "reverse of inspected frames",
                "hash": "SHA-256 of 1080x1920 RGB24",
            },
            "limitations": (
                "Conservative sprite ink AABBs from draw_directed_text/draw_word_caption and measured "
                "presenter face_box; raw raster text (T04) or uninstrumented custom sprites are not captured, "
                "and AABBs do not prove Arabic shaping or visual readability."
            ),
            "frames": audit_frames,
        }
        report_path = out / "report.json"
        with report_path.open("x", encoding="utf-8") as stream:
            json.dump(report_doc, stream, indent=2, ensure_ascii=False)
            stream.write("\n")

        if status != "pass" or replay_status == "fail":
            print(f"Layout audit P {status.upper()} (replay: {replay_status}); see {report_path}", file=sys.stderr)
            return 1
        print(f"Layout audit P PASS · {count} frame range · {captured_text} text box(es)")
        return 0
    finally:
        sys.modules.pop("scenes", None)
        sys.path[:] = old_sys_path
        os.chdir(old_cwd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", required=True, type=Path, help="engine-P project directory containing scenes.py")
    parser.add_argument("--out", required=True, type=Path, help="fresh directory for report.json and violation PNGs")
    parser.add_argument("--from", dest="from_s", type=float, default=0.0)
    parser.add_argument("--to", dest="to_s", type=float, default=None)
    parser.add_argument("--fps", type=int, default=FPS_LOCKED)
    parser.add_argument("--every", type=int, default=1)
    parser.add_argument("--replay", action="store_true", help="re-evaluate inspected frames in reverse order")
    parser.add_argument(
        "--platform-ui",
        action="store_true",
        help="also flag L04 intrusions into the Reels/TikTok right-rail action zone (x940..1080 y1100..1500)",
    )
    parser.add_argument(
        "--motion-mode",
        choices=("normal", "reduced"),
        default=os.environ.get("MEDO_MOTION_MODE", "normal"),
    )
    parser.set_defaults(replay_only_flag_error=False)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return _run_in_project(args)
    except BaseException as error:  # noqa: BLE001
        if isinstance(error, SystemExit):
            raise
        print(f"Layout audit P blocked: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
