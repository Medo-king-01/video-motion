#!/usr/bin/env python3
"""Engine-K scene cache: edit one scene, re-render one scene.

    python3 tools/render_scenes.py projects/my-reel
    # → cache/scenes/<id>-<hash>.mp4 per scene, then out/master.mp4 (concat, audio muxed if present)

Why: `pipeline.py --steps render` re-encodes the whole reel whenever anything under `src/`
changes. Engine K already renders a *range*, so each scene can be cached on its own: the key of
scene `intro` is every shared visual input (`shared_inputs`: src/, the served plans, the assets,
the package files) plus `intro.js` plus that scene's timing — editing `outro.js` leaves `intro`'s
key untouched and its MP4 is reused; editing a plan or an asset re-renders every scene.

Honesty rules:
- a cache hit must still decode: every reused segment is probed for size and frame count;
- the concatenation is a stream copy of segments encoded with the same settings (no re-encode);
- the output is never overwritten without `--force`;
- the manifest records, per scene, whether it was a hit and how long a miss took, so
  "the cache works" is a number in `cache/scenes/manifest.json`, not a claim.

Scope: engine K only. Engine P caches whole chunks (see `chunk.py`). Engine R *does* render a range
(`scripts/render.mjs --from-frame --to-frame`, validated against the locked 30 fps timeline, and
`render_hybrid.py` has always used it) — what R lacks is **per-scene modules**: one composition
(`RemotionRoot.tsx` + `src/lib/*`, 46 files at last count) reads `plan/beats.json` and draws every
scene, so a key built from "that scene's own code" would be the whole project and any edit would
invalidate every segment. A cache that never hits is worse than no cache, so `--scene-cache` stays
K-only and `pipeline.py` says that reason instead of the old, false one.
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


# --- what a frame can read: the one manifest the cache key is built from --------------------
#
# render.js serves the browser exactly three things — everything under `src/`, everything under
# the assets root, and the plans in ALLOWED_PLANS — plus the project's node_modules. main.js hands
# the whole direction/copy documents to every scene and initialises every scene on every render,
# and a scene may fetch any served URL at run time, so none of these can be proven to belong to
# one scene: they are *shared* inputs and a change re-renders every scene. The only inputs that
# are provably one scene's own are its module (`src/scenes/<id>.js`) and its timing.
#
# A new kind of input is added here, in this table, and nowhere else.
KEY_VERSION = "engine-k-scene-cache-v2"  # bump when the key's meaning changes: old segments must miss
PLAN_FILES = ("text-direction.json", "beats.json", "stage.json", "slide-wall.json", "one-take.json",
              "copy.json", "word-timings.json")  # render.js ALLOWED_PLANS (a test pins the two together)
PACKAGE_FILES = ("node_modules/.package-lock.json", "package.json", "package-lock.json",
                 "pnpm-lock.yaml", "yarn.lock")  # stands in for node_modules; the tree is never walked
AUDIO_SUFFIXES = frozenset({".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg"})  # sound, not picture
ASSETS_ENV = ("MEDO_ASSETS_DIR", "KHAAM_ASSETS_DIR")  # render.js: setting('ASSETS_DIR')
MOTION_MODES = ("normal", "reduced")
_CHUNK = 1 << 20


def assets_root(project: Path) -> Path:
    """The directory render.js serves as /assets/: the env override if set, else <project>/assets."""
    for name in ASSETS_ENV:
        value = os.environ.get(name)
        if value:
            return (project / value).resolve()  # render.js resolves against its cwd, the project
    return (project / "assets").resolve()


def resolve_motion_mode(cli: str | None = None) -> str:
    """The mode render.js will draw in: --motion-mode, then MEDO_MOTION_MODE, then normal."""
    mode = cli or os.environ.get("MEDO_MOTION_MODE") or "normal"
    if mode not in MOTION_MODES:
        raise SystemExit(f"render_scenes: motion mode must be one of {', '.join(MOTION_MODES)}, got {mode!r}")
    return mode


def _servable_tree(root: Path, what: str) -> list[tuple[str, Path]]:
    """Every file under `root` the loopback server would hand out, as (posix relative path, file).

    Dot-names are skipped because the server refuses them. A symlink is followed only while it
    stays inside `root`: the server would serve an escaping link, so ignoring it would leave a
    visual input out of the key — the run stops instead.
    """
    if not root.is_dir():
        return []
    real_root = root.resolve()
    found: list[tuple[str, Path]] = []
    visited: set[Path] = set()

    def walk(directory: Path, prefix: str) -> None:
        real = directory.resolve()
        if real in visited:  # a link back to an ancestor: already covered, and it would never end
            return
        visited.add(real)
        for entry in sorted(directory.iterdir(), key=lambda item: item.name):
            if entry.name.startswith("."):
                continue
            relative = f"{prefix}{entry.name}"
            if entry.is_symlink():
                target = entry.resolve()
                if target != real_root and real_root not in target.parents:
                    raise SystemExit(f"render_scenes: {what}/{relative} is a symlink that leaves {real_root} "
                                     f"(-> {target}); copy the file in, or point MEDO_ASSETS_DIR at the real folder")
            if entry.is_dir():
                walk(entry, relative + "/")
            elif entry.is_file():
                found.append((relative, entry))

    walk(real_root, "")
    return found


def shared_inputs(project: Path, scene_ids: list[str] | tuple[str, ...],
                  extra: tuple[Path, ...] = ()) -> list[tuple[str, Path]]:
    """(label, file) for every shared visual input, sorted by label. The label is hashed too, so
    adding, removing or renaming a file changes the key even when no byte changed."""
    own_modules = {f"scenes/{scene_id}.js" for scene_id in scene_ids}
    inputs = [(f"src/{relative}", path) for relative, path in _servable_tree(project / "src", "src")
              if relative not in own_modules]  # helpers beside the scene modules are shared
    inputs += [(f"plan/{name}", project / "plan" / name) for name in PLAN_FILES
               if (project / "plan" / name).is_file()]
    inputs += [(f"assets/{relative}", path) for relative, path in _servable_tree(assets_root(project), "assets")
               if path.suffix.lower() not in AUDIO_SUFFIXES]
    inputs += [(f"package/{name}", project / name) for name in PACKAGE_FILES if (project / name).is_file()]
    for path in extra:
        resolved = (project / path).resolve()
        if not resolved.is_file():
            raise SystemExit(f"render_scenes: --hash-audio file not found: {path}")
        inputs.append((f"extra/{resolved.as_posix()}", resolved))
    return sorted(set(inputs), key=lambda item: item[0])


def _hash_file(hasher: hashlib._Hash, path: Path, label: str) -> None:
    content = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_CHUNK):
            content.update(chunk)
    hasher.update(label.encode("utf-8"))
    hasher.update(b"\0")
    hasher.update(content.digest())
    hasher.update(b"\0")


def shared_key(project: Path, *, fps: int, scale: float, crf: int, scene_ids: list[str] | tuple[str, ...],
               motion_mode: str | None = None, extra: tuple[Path, ...] = ()) -> str:
    """Everything every scene inherits: `shared_inputs`, the encode settings and the motion mode."""
    hasher = hashlib.sha256()
    hasher.update(f"{KEY_VERSION}|{fps}|{scale}|{crf}|{resolve_motion_mode(motion_mode)}".encode("ascii"))
    for label, path in shared_inputs(project, scene_ids, extra):
        _hash_file(hasher, path, label)
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


def render_segment(project: Path, scene: dict, target: Path, *, fps: int, crf: int, log: Path,
                   motion_mode: str = "normal") -> bool:
    """Render one scene range into the cache directory (render.js owns the encoding)."""
    target.parent.mkdir(parents=True, exist_ok=True)
    name = target.stem
    cmd = (f'eval "$(node {ROOT}/tools/chromium.mjs --env)" && '
           f'node src/render.js --from {float(scene["start"]):.6f} --to {float(scene["end"]):.6f} '
           f'--fps {fps} --scale 1 --crf {crf} --motion-mode {motion_mode} --out {target.parent.relative_to(project)} --name {name}')
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
        log: Path, motion_mode: str | None = None, hash_audio: tuple[Path, ...] = ()) -> dict:
    scenes = load_scenes(project)
    cache = project / "cache" / "scenes"
    motion_mode = resolve_motion_mode(motion_mode)
    shared = shared_key(project, fps=fps, scale=1.0, crf=crf, scene_ids=[scene["id"] for scene in scenes],
                        motion_mode=motion_mode, extra=hash_audio)
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
            if not render_segment(project, scene, target, fps=fps, crf=crf, log=log, motion_mode=motion_mode):
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
        "engine": "k", "fps": fps, "crf": crf, "motion_mode": motion_mode, "key_version": KEY_VERSION,
        "shared_key": shared[:12],
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
    parser.add_argument("--motion-mode", choices=MOTION_MODES, default=None,
                        help="default: $MEDO_MOTION_MODE, else normal (part of the cache key)")
    parser.add_argument("--hash-audio", type=Path, action="append", default=[], metavar="FILE",
                        help="an audio file a scene DRAWS from (e.g. a waveform): add it to the shared key. "
                             "Audio is otherwise left out of the key. Repeatable; relative to the project")
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
                       force=args.force, log=log, motion_mode=args.motion_mode,
                       hash_audio=tuple(args.hash_audio))
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
