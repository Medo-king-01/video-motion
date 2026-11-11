#!/usr/bin/env python3
"""Read-only report: which projects will be stopped by the 2026-11-11 hardening.

For every project folder it checks, without changing or running anything in it:

  scene ids     every id in `src/data.js` against the allowlist `render_scenes.py` now enforces
                (`[A-Za-z0-9][A-Za-z0-9_-]{0,63}`); an id outside it is rejected before rendering
  audio mix     `out/final_audio.wav` with no `out/final_audio.mix.json` record next to it; with a
                cue sheet the pipeline's mix step stops until `--keep-mix` or `--remix`
  cache links   a symlinked `cache/` or `cache/scenes/`, which the scene cache refuses

    python3 tools/audit_projects.py                 every folder under projects/
    python3 tools/audit_projects.py ~/reels/a ~/reels/b
    python3 tools/audit_projects.py --json
    python3 tools/audit_projects.py --node          ask Node for the ids (this RUNS src/data.js)

Scene ids are read from the text of `src/data.js` by default, so no project code is executed. That
reading can miss ids that are built at run time; the report says so when it finds none. `--node`
imports `data.js` exactly as the renderer does. Exit status is 0 unless `--fail-on-findings`.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from render_scenes import SCENE_ID  # noqa: E402  - the one allowlist, not a copy

SCENES_BLOCK = re.compile(r"\bscenes\s*=\s*\[(.*?)\]\s*;?", re.S)
ID_FIELD = re.compile(r"""(?<![\w$])["']?id["']?\s*:\s*(?:'((?:[^'\\\n]|\\.)*)'|"((?:[^"\\\n]|\\.)*)"|`([^`$]*)`)""")
COMMENT = re.compile(r"/\*.*?\*/|(?<![:'\"`\\])//[^\n]*", re.S)


def static_scene_ids(text: str) -> list[str] | None:
    """Ids of the literal `scenes = [...]` array, or None when the file has no such literal."""
    block = SCENES_BLOCK.search(COMMENT.sub("", text))
    if not block:
        return None
    return [next(group for group in match.groups() if group is not None) for match in ID_FIELD.finditer(block.group(1))]


def node_scene_ids(project: Path) -> tuple[list | None, str]:
    node = shutil.which("node")
    if not node:
        return None, "node is not installed"
    script = ("import('./src/data.js').then(m => console.log(JSON.stringify((m.scenes || []).map(s => s && s.id))))"
              ".catch(e => { console.error(e.message); process.exit(1); })")
    done = subprocess.run([node, "-e", script], cwd=str(project), capture_output=True, text=True, check=False,
                          timeout=60)
    if done.returncode:
        return None, f"node could not import src/data.js: {done.stderr.strip()[:200]}"
    try:
        return json.loads(done.stdout), ""
    except ValueError:
        return None, "src/data.js printed something that is not JSON"


def audit(project: Path, *, use_node: bool = False) -> dict:
    """What is true of one project. Reads only; never writes, never follows a fix."""
    report: dict = {"project": str(project), "findings": [], "notes": []}
    data = project / "src" / "data.js"
    if data.is_file():
        ids, how = None, "static"
        if use_node:
            ids, problem = node_scene_ids(project)
            how = "node"
            if ids is None:
                report["notes"].append(f"scene ids: {problem}; fell back to reading the text")
        if ids is None:
            how = "static"
            try:
                ids = static_scene_ids(data.read_text(encoding="utf-8", errors="replace"))
            except OSError as error:
                report["notes"].append(f"scene ids: cannot read src/data.js ({error})")
                ids = []
        if not ids:
            report["notes"].append("scene ids: none found in the text of src/data.js — they may be built at run time; "
                                   "re-run with --node to ask the renderer's own loader")
        ids = ids or []
        bad = [item for item in ids if not isinstance(item, str) or not SCENE_ID.fullmatch(item)]
        report["scene_ids"] = {"read_with": how, "count": len(ids), "rejected": bad}
        for item in bad:
            report["findings"].append(f"scene id {item!r} is outside the allowlist — render_scenes.py will refuse it")
    else:
        report["scene_ids"] = None
        report["notes"].append("no src/data.js — not an engine-K project, scene ids not applicable")

    mix, record = project / "out" / "final_audio.wav", project / "out" / "final_audio.mix.json"
    sheet = project / "plan" / "cues.json"
    report["mix"] = {"final_audio": mix.is_file(), "record": record.is_file(), "cue_sheet": sheet.is_file()}
    if mix.is_file() and not record.is_file():
        if sheet.is_file():
            report["findings"].append("out/final_audio.wav has no out/final_audio.mix.json — the pipeline's mix step "
                                      "will stop once; choose --keep-mix (accept it) or --remix (rebuild it)")
        else:
            report["notes"].append("out/final_audio.wav has no record and there is no plan/cues.json — the pipeline "
                                   "keeps such a mix without checking it")

    for name in ("cache", "cache/scenes"):
        if (project / name).is_symlink():
            report["findings"].append(f"{name} is a symlink — the scene cache refuses to write through it")
    return report


def projects_under(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(path for path in folder.iterdir() if path.is_dir() and not path.name.startswith("."))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only audit of projects against the scene-id allowlist "
                                                 "and the audio-mix record.")
    parser.add_argument("projects", nargs="*", type=Path, help="project folders (default: every folder in projects/)")
    parser.add_argument("--root", type=Path, default=ROOT / "projects", help="folder holding the projects")
    parser.add_argument("--node", action="store_true", help="read scene ids by importing src/data.js (runs project code)")
    parser.add_argument("--json", action="store_true", help="print the report as JSON")
    parser.add_argument("--fail-on-findings", action="store_true", help="exit 1 when any project has a finding")
    args = parser.parse_args(argv)

    targets = [path.expanduser() for path in args.projects] or projects_under(args.root)
    missing = [str(path) for path in targets if not path.is_dir()]
    if missing:
        print(f"audit_projects: not a folder: {', '.join(missing)}", file=sys.stderr)
        return 2
    reports = [audit(path, use_node=args.node) for path in targets]
    flagged = [report for report in reports if report["findings"]]
    if args.json:
        print(json.dumps({"projects": reports, "with_findings": len(flagged)}, ensure_ascii=False, indent=2))
    else:
        if not reports:
            print(f"no project folders under {args.root}")
        for report in reports:
            ids = report["scene_ids"]
            summary = "no data.js" if ids is None else f"{ids['count']} scene id(s), {len(ids['rejected'])} rejected"
            print(f"{'FLAG' if report['findings'] else 'OK  '} {report['project']} · {summary}")
            for finding in report["findings"]:
                print(f"       ! {finding}")
            for note in report["notes"]:
                print(f"       · {note}")
        print(f"{len(reports)} project(s) checked, {len(flagged)} with findings. Nothing was changed.")
    return 1 if flagged and args.fail_on_findings else 0


if __name__ == "__main__":
    sys.exit(main())
