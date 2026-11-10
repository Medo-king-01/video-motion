#!/usr/bin/env python3
"""Engine-K scene cache: edit one scene, re-render one scene.

    python3 tools/render_scenes.py projects/my-reel
    # → cache/scenes/<id>-<hash>.mp4 per scene, then out/master.mp4 (concat, audio muxed if present)

Why: `pipeline.py --steps render` re-encodes the whole reel whenever anything under `src/`
changes. Engine K already renders a *range*, so each scene can be cached on its own: the key of
scene `intro` is the shared code (main.js, render.js, lib/*) plus `intro.js` plus that scene's
timing line — editing `outro.js` leaves `intro`'s key untouched and its MP4 is reused.

Honesty rules:
- a cache hit must still decode: every reused segment is probed for size and frame count;
- the concatenation is a stream copy of segments encoded with the same settings (no re-encode);
- the output is never overwritten without `--force`;
- the manifest records, per scene, whether it was a hit and how long a miss took, so
  "the cache works" is a number in `cache/scenes/manifest.json`, not a claim.

Scope: engine K only. Engine P caches whole chunks (see `chunk.py`) and R/Remotion has no range
API; pretending otherwise here would produce segments that do not concatenate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "lib"))

import media_bin  # noqa: E402


def load_scenes(project: Path) -> list[dict]:
    """Ask Node for `data.js`'s scenes — the renderer's own source of truth, not a regex."""
    node = shutil.which("node")
    if not node:
        raise SystemExit("render_scenes: node is required (engine K renders in Chromium)")
    script = ("import('./src/data.js').then(m => console.log(JSON.stringify(m.scenes)))"
              ".catch(e => { console.error(e.message); process.exit(1); })")
    result = subprocess.run([node, "-e", script], cwd=str(project), capture_output=True, text=True, check=False)
    if result.returncode:
        raise SystemExit(f"render_scenes: cannot read src/data.js: {result.stderr.strip()}")
    scenes = json.loads(result.stdout)
    if not isinstance(scenes, list) or not scenes:
        raise SystemExit("render_scenes: src/data.js exports no scenes")
    for scene in scenes:
        if not isinstance(scene, dict) or not scene.get("id") or "start" not in scene or "end" not in scene:
            raise SystemExit(f"render_scenes: every scene needs id/start/end, got {scene!r}")
        if float(scene["end"]) <= float(scene["start"]):
            raise SystemExit(f"render_scenes: scene {scene['id']} ends before it starts")
    return scenes


def _hash_file(hasher: hashlib._Hash, path: Path, label: str) -> None:
    hasher.update(label.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(path.read_bytes())
    hasher.update(b"\0")


def shared_key(project: Path, *, fps: int, scale: float, crf: int) -> str:
    """Everything a scene inherits: the renderer, the libs, the data and the encode settings."""
    src = project / "src"
    hasher = hashlib.sha256()
    hasher.update(f"engine-k-scene-cache-v1|{fps}|{scale}|{crf}".encode("ascii"))
    files = [src / "data.js", src / "main.js", src / "render.js", src / "index.html"]
    files += sorted((src / "lib").rglob("*.js"))
    for path in files:
        if path.is_file():
            _hash_file(hasher, path, f"src/{path.relative_to(src).as_posix()}")
    return hasher.hexdigest()


def scene_key(shared: str, project: Path, scene: dict) -> str:
    """A scene's own module plus its timing — the only things an edit to it can touch."""
    hasher = hashlib.sha256(shared.encode("ascii"))
    module = project / "src" / "scenes" / f"{scene['id']}.js"
    if not module.is_file():
        raise SystemExit(f"render_scenes: scene module missing: {module.relative_to(project)}")
    _hash_file(hasher, module, f"scene/{scene['id']}")
    hasher.update(repr((float(scene["start"]), float(scene["end"]))).encode("utf-8"))
    return hasher.hexdigest()


def probe_video(path: Path) -> dict | None:
    ffprobe = media_bin.ffprobe()
    if not ffprobe or not path.is_file():
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0",
         "-show_entries", "stream=width,height,nb_frames,r_frame_rate,duration", "-of", "json", str(path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode:
        return None
    streams = json.loads(result.stdout).get("streams") or []
    if not streams:
        return None
    info = streams[0]
    try:
        numerator, _, denominator = str(info.get("r_frame_rate", "0/1")).partition("/")
        fps = float(numerator) / float(denominator or 1)
        frames = int(info["nb_frames"]) if str(info.get("nb_frames", "")).isdigit() else None
        if frames is None and info.get("duration"):
            frames = round(float(info["duration"]) * fps)
        return {"width": int(info["width"]), "height": int(info["height"]),
                "frames": frames, "fps": info.get("r_frame_rate")}
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def expected_frames(scene: dict, fps: int) -> int:
    return max(1, round((float(scene["end"]) - float(scene["start"])) * fps))


def render_segment(project: Path, scene: dict, target: Path, *, fps: int, crf: int, log: Path) -> bool:
    """Render one scene range into the cache directory (render.js owns the encoding)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    name = target.stem
    cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
           f'node src/render.js --from {float(scene["start"]):.6f} --to {float(scene["end"]):.6f} '
           f'--fps {fps} --scale 1 --crf {crf} --out {target.parent.relative_to(project)} --name {name}')
    with log.open("a", encoding="utf-8") as handle:
        handle.write("\n$ " + cmd + "\n")
        handle.flush()
        return subprocess.run(["bash", "-c", cmd], cwd=str(project or Path.cwd()), env=os.environ.copy(),
                              stdout=handle, stderr=subprocess.STDOUT, check=False).returncode == 0


def concat(segments: list[Path], target: Path, log: Path) -> bool:
    ffmpeg = media_bin.ffmpeg()
    if not ffmpeg:
        return False
    listing = target.with_name("scenes.txt")
    include = [seg.resolve() for seg in segments if seg.is_file()]
    listing.write_text("".join(f"file '{seg}'\n" for seg in include), encoding="utf-8")
    tmp = target.with_name(target.stem + ".tmp" + target.suffix)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
           "-c", "copy", str(tmp)]
    with log.open("a", encoding="utf-8") as handle:
        if subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=False).returncode:
            return False
    os.replace(tmp, target)
    listing.unlink(missing_ok=True)
    return True


def mux_audio(picture: Path, audio: Path, target: Path, log: Path) -> bool:
    ffmpeg = media_bin.ffmpeg()
    if not ffmpeg:
        return False
    tmp = target.with_name(target.stem + ".tmp" + target.suffix)
    cmd = [ffmpeg, "-y", "-loglevel", "error", "-i", str(picture), "-i", str(audio),
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
           "-shortest", "-movflags", "+faststart", str(tmp)]
    with log.open("a", encoding="utf-8") as handle:
        if subprocess.run(cmd, stdout=handle, stderr=subprocess.STDOUT, check=False).returncode:
            return False
    os.replace(tmp, target)
    return True


def run(project: Path, *, fps: int, crf: int, output: Path, audio: Path | None, force: bool,
        log: Path) -> dict:
    scenes = load_scenes(project)
    cache = project / "cache" / "scenes"
    shared = shared_key(project, fps=fps, scale=1.0, crf=crf)
    entries: list[dict] = []
    segments: list[Path] = []
    cache_hits = 0
    for scene in scenes:
        key = scene_key(shared, project, scene)[:12]
        target = cache / f"{scene['id']}-{key}.mp4"
        want = expected_frames(scene, fps)
        started = time.perf_counter()
        info = probe_video(target)
        hit = bool(info and info["frames"] == want and (info["width"], info["height"]) == (1080, 1920))
        if not hit:
            if target.exists():
                target.unlink()
            if not render_segment(project, scene, target, fps=fps, crf=crf, log=log):
                raise SystemExit(f"render_scenes: render failed for scene '{scene['id']}' — see {log}")
            info = probe_video(target)
            if not info or info["frames"] != want:
                raise SystemExit(f"render_scenes: scene '{scene['id']}' produced {info and info['frames']} "
                                 f"frames, expected {want}")
        else:
            cache_hits += 1
        entries.append({"id": scene["id"], "cache": "hit" if hit else "miss",
                        "frames": info["frames"], "segment": str(target.relative_to(project)),
                        "seconds": round(time.perf_counter() - started, 3)})
        segments.append(target)

    if output.exists() and not force:
        raise SystemExit(f"render_scenes: refusing to overwrite {output} (use --force)")
    output.parent.mkdir(parents=True, exist_ok=True)
    picture = output
    if audio is not None:
        picture = cache / "picture.mp4"
        if not concat(segments, picture, log):
            raise SystemExit(f"render_scenes: concat failed — see {log}")
        if not mux_audio(picture, audio, output, log):
            raise SystemExit(f"render_scenes: audio mux failed — see {log}")
    elif not concat(segments, output, log):
        raise SystemExit(f"render_scenes: concat failed — see {log}")

    manifest = {
        "engine": "k", "fps": fps, "crf": crf, "shared_key": shared[:12],
        "scenes": entries, "hits": cache_hits, "misses": len(entries) - cache_hits,
        "output": str(output.relative_to(project)), "audio": str(audio) if audio else None,
    }
    cache.mkdir(parents=True, exist_ok=True)
    (cache / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("project", type=Path)
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--crf", type=int, default=13)
    parser.add_argument("--out", type=Path, default=None, help="default: <project>/out/master.mp4")
    parser.add_argument("--audio", type=Path, default=None, help="default: out/final_audio.wav if present")
    parser.add_argument("--force", action="store_true", help="overwrite an existing output")
    parser.add_argument("--json", action="store_true", help="print the manifest as JSON")
    args = parser.parse_args(argv)

    project = args.project.resolve()
    if not project.is_dir():
        print(f"render_scenes: project not a directory: {project}", file=sys.stderr)
        return 2
    if not (project / "src" / "render.js").is_file():
        print("render_scenes: not an engine-K project (src/render.js missing)", file=sys.stderr)
        return 2
    output = (args.out or project / "out" / "master.mp4").resolve()
    audio = args.audio
    if audio is None:
        candidate = project / "out" / "final_audio.wav"
        audio = candidate if candidate.is_file() else None
    if audio is not None and not audio.is_file():
        print(f"render_scenes: audio not found: {audio}", file=sys.stderr)
        return 2
    log = project / "cache" / "scenes.log"
    log.parent.mkdir(parents=True, exist_ok=True)

    try:
        manifest = run(project, fps=args.fps, crf=args.crf, output=output, audio=audio,
                       force=args.force, log=log)
    except SystemExit as error:
        print(str(error), file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    else:
        print(f"SCENE CACHE hits={manifest['hits']} misses={manifest['misses']}")
        for entry in manifest["scenes"]:
            print(f"  {entry['id']:<20} {entry['cache']:<5} {entry['frames']:>4}f "
                  f"{entry['seconds']:>6.2f}s  {entry['segment']}")
        print(f"SCENES -> {manifest['output']}" + (" (with audio)" if audio else " (silent)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
