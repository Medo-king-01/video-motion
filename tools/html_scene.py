#!/usr/bin/env python3
"""Author one scene as HTML/CSS and render it with HyperFrames (optional, Apache-2.0).

An experimental side path for a scene that is easier to write as a web page than as engine
code. P/K/R stay the engines of record; this produces a clip that meets the same picture
contract (1080x1920, 30 fps, exact frame count), and nothing else in the studio depends on it.

    python3 tools/html_scene.py new projects/demo/html/intro --frames 90 --font Cairo
    python3 tools/html_scene.py check projects/demo/html/intro
    python3 tools/html_scene.py render projects/demo/html/intro --out projects/demo/out/intro.mp4

The scaffold is offline and brand-locked: fonts are copied from assets/fonts/, colours are CSS
variables generated from medo-motion/brand/brand.json, motion is plain CSS animation (no GSAP,
no CDN). `check` enforces that before every render:
  H01 no network URL in any scene file      H02 every colour is a brand.json colour
  H03 root is 1080x1920 and its duration is a whole number of frames, equal to scene.json
  H04 HyperFrames' own lint has no errors (skipped with --no-lint)
Named CSS colours other than transparent/currentColor/inherit are not detected — use the variables.

Needs `bash tools/setup_extras.sh hyperframes` (Node >= 22) and `bash tools/setup.sh`.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools" / "lib"))
from media_bin import ffprobe as find_ffprobe  # noqa: E402 - shared precedence rule

WIDTH, HEIGHT, FPS = 1080, 1920, 30
BRAND = ROOT / "medo-motion" / "brand" / "brand.json"
FONTS = ROOT / "assets" / "fonts"
WRAPPER = ROOT / "tools" / "hyperframes.sh"
CLI = ROOT / "tools" / "optional-hyperframes" / "node_modules" / ".bin" / "hyperframes"
SCENE_FILES = (".html", ".htm", ".css", ".js", ".mjs", ".svg")
ALLOWED_URLS = ("http://www.w3.org/",)  # XML namespaces, never fetched
WEIGHTS = {"thin": 100, "extralight": 200, "light": 300, "regular": 400, "medium": 500,
           "semibold": 600, "extrabold": 800, "bold": 700, "black": 900}

URL_RE = re.compile(r"""(?:https?:)?//[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s"'<>)]*""")
HEX_RE = re.compile(r"#([0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})(?![0-9A-Za-z_-])")
RGB_RE = re.compile(r"rgba?\(\s*(\d{1,3})[\s,]+(\d{1,3})[\s,]+(\d{1,3})")
OTHER_COLOUR_RE = re.compile(r"\b(hsla?|hwb|lab|lch|oklab|oklch|color)\(")


def brand_colours(brand: dict) -> dict[str, tuple[int, int, int]]:
    """Token -> rgb for every colour the brand lock allows (palette + declared derived)."""
    colours = {}
    for group in ("palette", "derived"):
        for token, entry in (brand.get(group) or {}).items():
            if isinstance(entry, dict) and isinstance(entry.get("hex"), str):
                colours[token] = hex_to_rgb(entry["hex"])
    return colours


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    digits = value.lstrip("#")
    if len(digits) in (3, 4):
        digits = "".join(c * 2 for c in digits)
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def font_faces(family: str) -> list[dict]:
    """The @font-face entries for one family of assets/fonts/, read from its file names."""
    folder = FONTS / family
    if not folder.is_dir():
        raise SystemExit(f"html_scene: font family not in assets/fonts/: {family!r} (see docs/fonts.md)")
    faces = []
    for path in sorted(folder.glob("*.ttf")):
        stem = path.stem
        style = "italic" if "italic" in stem.lower() else "normal"
        if "[" in stem:
            weight = "100 900" if "wght" in stem else "400"
        else:
            number = re.search(r"_(\d{3})", stem)
            label = re.sub(r"italic", "", stem.split("-")[-1].split("_")[-1].lower())
            label = re.sub(r"^\d{3}", "", label) or "regular"
            weight = number.group(1) if number else str(WEIGHTS.get(label, 400))
        faces.append({"family": family, "file": path.name, "weight": weight, "style": style, "source": path})
    if not faces:
        raise SystemExit(f"html_scene: no .ttf files in assets/fonts/{family}")
    return faces


def scaffold_html(frames: int, colours: dict[str, tuple[int, int, int]], faces: list[dict]) -> str:
    seconds = f"{frames / FPS:.6f}".rstrip("0").rstrip(".")
    variables = "\n".join(f"        --{token.replace('_', '-')}: #{r:02X}{g:02X}{b:02X};"
                          for token, (r, g, b) in colours.items())
    font_css = "\n".join(
        f'      @font-face {{ font-family: "{f["family"]}"; src: url("fonts/{f["file"]}"); '
        f'font-weight: {f["weight"]}; font-style: {f["style"]}; }}' for f in faces)
    family = faces[0]["family"]
    return f"""<!doctype html>
<html lang="ar" dir="rtl" data-resolution="portrait">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={WIDTH}, height={HEIGHT}" />
    <style>
{font_css}
      /* Every colour of medo-motion/brand/brand.json. Use these variables only (check H02). */
      :root {{
{variables}
      }}
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ width: {WIDTH}px; height: {HEIGHT}px; overflow: hidden; background: var(--paper); }}
      #root {{
        width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
        font-family: "{family}"; color: var(--ink);
      }}
      /* Frame 0 is the thumbnail: the title is already on screen and only settles. */
      #title {{ font-size: 120px; font-weight: 800; animation: settle 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; }}
      @keyframes settle {{ from {{ transform: translateY(40px); }} to {{ transform: none; }} }}
    </style>
  </head>
  <body>
    <!-- data-duration = frames / {FPS}; keep it equal to scene.json (check H03). -->
    <div id="root" data-composition-id="main" data-no-timeline data-start="0" data-duration="{seconds}"
         data-width="{WIDTH}" data-height="{HEIGHT}">
      <h1 id="title" class="clip" data-start="0" data-duration="{seconds}" data-track-index="0">العنوان هنا</h1>
    </div>
  </body>
</html>
"""


def cmd_new(args: argparse.Namespace) -> int:
    scene: Path = args.scene
    if scene.exists() and any(scene.iterdir()):
        print(f"html_scene: {scene} already exists and is not empty", file=sys.stderr)
        return 2
    if args.frames < 1:
        print("html_scene: --frames must be >= 1", file=sys.stderr)
        return 2
    colours = brand_colours(json.loads(BRAND.read_text(encoding="utf-8")))
    faces = [face for family in (args.font or ["Cairo"]) for face in font_faces(family)]
    (scene / "fonts").mkdir(parents=True, exist_ok=True)
    for face in faces:
        shutil.copy2(face["source"], scene / "fonts" / face["file"])
        licence = face["source"].parent / "OFL.txt"
        if licence.is_file():
            shutil.copy2(licence, scene / "fonts" / f"{face['family']} - OFL.txt")
    (scene / "index.html").write_text(scaffold_html(args.frames, colours, faces), encoding="utf-8")
    meta = {"frames": args.frames, "fps": FPS, "width": WIDTH, "height": HEIGHT,
            "fonts": sorted({face["family"] for face in faces}), "engine": "hyperframes (experimental side path)"}
    (scene / "scene.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Scaffolded {scene} · {args.frames} frames ({args.frames / FPS:.3f}s) · fonts: {', '.join(meta['fonts'])}")
    print(f"Next: edit index.html, then  python3 tools/html_scene.py render {scene} --out <clip.mp4>")
    return 0


class RootFinder(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.roots: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        found = dict(attrs)
        if "data-composition-id" in found:
            self.roots.append(found)


def scene_files(scene: Path) -> list[Path]:
    skip = {"node_modules", "renders", ".hyperframes", ".debug"}
    return sorted(p for p in scene.rglob("*") if p.is_file() and p.suffix.lower() in SCENE_FILES
                  and not skip.intersection(p.relative_to(scene).parts))


def static_findings(scene: Path, colours: dict[str, tuple[int, int, int]]) -> list[tuple[str, str]]:
    """H01-H03: (rule, message) for every violation found without launching anything."""
    findings: list[tuple[str, str]] = []
    index = scene / "index.html"
    meta_path = scene / "scene.json"
    if not index.is_file() or not meta_path.is_file():
        return [("H03", f"{scene} is not an HTML scene (index.html + scene.json) — create one with `new`")]
    allowed = set(colours.values())
    for path in scene_files(scene):
        text = path.read_text(encoding="utf-8", errors="replace")
        name = path.relative_to(scene)
        for number, line in enumerate(text.splitlines(), 1):
            for match in URL_RE.finditer(line):
                url = match.group(0)
                if not any(url.startswith(ok) for ok in ALLOWED_URLS):
                    findings.append(("H01", f"{name}:{number}: network URL {url} — copy the file into the scene"))
            for match in HEX_RE.finditer(line):
                before = re.split(r"[{};]", line[:match.start()])[-1]
                if ":" not in before and "=" not in before:
                    continue  # an id selector such as `#face {`, not a value
                if hex_to_rgb(match.group(0)) not in allowed:
                    findings.append(("H02", f"{name}:{number}: {match.group(0)} is not a brand.json colour"))
            for match in RGB_RE.finditer(line):
                if tuple(int(v) for v in match.groups()) not in allowed:
                    findings.append(("H02", f"{name}:{number}: {match.group(0)}…) is not a brand.json colour"))
            for match in OTHER_COLOUR_RE.finditer(line):
                findings.append(("H02", f"{name}:{number}: {match.group(1)}() cannot be checked against "
                                        "brand.json — use a palette variable, hex or rgb()"))
    try:
        frames = int(json.loads(meta_path.read_text(encoding="utf-8"))["frames"])
    except (ValueError, KeyError, TypeError):
        return findings + [("H03", "scene.json has no integer `frames`")]
    finder = RootFinder()
    finder.feed(index.read_text(encoding="utf-8", errors="replace"))
    if len(finder.roots) != 1:
        return findings + [("H03", f"index.html must have exactly one data-composition-id root (found {len(finder.roots)})")]
    root = finder.roots[0]
    if (root.get("data-width"), root.get("data-height")) != (str(WIDTH), str(HEIGHT)):
        findings.append(("H03", f"root must be data-width={WIDTH} data-height={HEIGHT}"))
    try:
        duration = float(root.get("data-duration") or "")
    except ValueError:
        return findings + [("H03", "root has no numeric data-duration")]
    if frames < 1 or abs(duration * FPS - frames) > 1e-3:
        findings.append(("H03", f"root data-duration={duration:g}s is {duration * FPS:g} frames at {FPS} fps, "
                                f"but scene.json says {frames} — both must be the same whole number"))
    return findings


def hyperframes_ready() -> str | None:
    if not CLI.exists():
        return "HyperFrames is not installed — bash tools/setup_extras.sh hyperframes (Node >= 22)"
    if shutil.which("bash") is None:
        return "bash is required to run tools/hyperframes.sh"
    return None


def run_check(scene: Path, lint: bool) -> int:
    colours = brand_colours(json.loads(BRAND.read_text(encoding="utf-8")))
    findings = static_findings(scene, colours)
    for rule, message in findings:
        print(f"ERROR {rule} {message}")
    if findings:
        print(f"{len(findings)} error(s) — fix them before rendering")
        return 1
    print("OK    H01 no network URLs · H02 brand colours only · H03 1080x1920, whole frames")
    if not lint:
        print("SKIP  H04 HyperFrames lint (--no-lint)")
        return 0
    problem = hyperframes_ready()
    if problem:
        print(f"html_scene: {problem}", file=sys.stderr)
        return 1
    result = subprocess.run(["bash", str(WRAPPER), "lint"], cwd=scene, capture_output=True, text=True)
    if result.returncode:
        print("ERROR H04 HyperFrames lint:\n" + (result.stdout + result.stderr).strip())
        return 1
    print("OK    H04 HyperFrames lint")
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    return run_check(args.scene, not args.no_lint)


def cmd_render(args: argparse.Namespace) -> int:
    scene: Path = args.scene
    status = run_check(scene, True)
    if status:
        return status
    ffprobe = find_ffprobe()
    if not ffprobe:
        print("html_scene: ffprobe not found — bash tools/setup.sh", file=sys.stderr)
        return 1
    frames = int(json.loads((scene / "scene.json").read_text(encoding="utf-8"))["frames"])
    out = args.out.resolve()
    if out.suffix.lower() != ".mp4":
        print("html_scene: --out must end in .mp4", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    temp = out.with_name(out.stem + ".partial.mp4")
    temp.unlink(missing_ok=True)
    result = subprocess.run(["bash", str(WRAPPER), "render", "-o", str(temp), "--fps", str(FPS),
                             "--workers", "1", "--strict", "--quiet"],
                            cwd=scene, capture_output=True, text=True)
    if result.returncode or not temp.is_file():
        tail = "\n".join((result.stdout + result.stderr).strip().splitlines()[-12:])
        print(f"html_scene: HyperFrames render failed (exit {result.returncode}):\n{tail}", file=sys.stderr)
        temp.unlink(missing_ok=True)
        return 1
    probe = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height,r_frame_rate,nb_frames", "-of", "json", str(temp)],
                           capture_output=True, text=True)
    try:
        stream = json.loads(probe.stdout)["streams"][0]
        got = (int(stream["width"]), int(stream["height"]), stream["r_frame_rate"], int(stream["nb_frames"]))
    except (ValueError, KeyError, IndexError, TypeError):
        temp.unlink(missing_ok=True)
        print(f"html_scene: could not read the rendered clip: {probe.stderr.strip()}", file=sys.stderr)
        return 1
    if got != (WIDTH, HEIGHT, f"{FPS}/1", frames):
        temp.unlink(missing_ok=True)
        print(f"html_scene: clip violates the picture contract: {got}; expected "
              f"{WIDTH}x{HEIGHT}, {FPS}/1 fps, {frames} frames", file=sys.stderr)
        return 1
    temp.replace(out)
    print(f"Rendered {out} · {WIDTH}x{HEIGHT} · {FPS} fps · {frames} frames")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="command", required=True)
    new = sub.add_parser("new", help="scaffold an offline, brand-locked HTML scene")
    new.add_argument("scene", type=Path)
    new.add_argument("--frames", type=int, required=True, help=f"scene length in frames at {FPS} fps")
    new.add_argument("--font", action="append", help="family from assets/fonts/ (repeatable; default Cairo)")
    new.set_defaults(func=cmd_new)
    check = sub.add_parser("check", help="H01-H04 guards")
    check.add_argument("scene", type=Path)
    check.add_argument("--no-lint", action="store_true", help="static guards only; do not run HyperFrames")
    check.set_defaults(func=cmd_check)
    render = sub.add_parser("render", help="check, render, and verify the clip contract")
    render.add_argument("scene", type=Path)
    render.add_argument("--out", type=Path, required=True, help="output .mp4")
    render.set_defaults(func=cmd_render)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
