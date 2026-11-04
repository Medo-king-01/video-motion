#!/usr/bin/env python3
"""Create a reel project scaffold.

    python3 tools/new_project.py my-reel                 # scaffold only
    python3 tools/new_project.py my-reel --engine p      # + copy engine P into the project
    python3 tools/new_project.py my-reel --engine k      # + copy engine K into src/
    python3 tools/new_project.py my-reel --engine r      # + copy Remotion (React/TS) into the project
    python3 tools/new_project.py my-reel --engine hybrid # + install P, K and R sequential hybrid scaffold
    python3 tools/new_project.py my-reel --out ~/reels/my-reel  # scaffold outside the repo (recommended)

Layout follows medo-motion/reference/planning-and-tracking.md.
The scaffold asks for nothing: fill BRIEF.md with the four inputs (script, scene
direction, VO, poses). There is no logo, no series name and no episode number unless
the user asks for one — by design.

A project is a working folder, not studio memory: `projects/` is ignored by Git and a
scaffold written there carries its own ignore file, so finished videos never accumulate
in the toolkit. Use --out to keep the folder next to the video's own files.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"
sys.path.insert(0, str(SKILL / "scripts"))
from _safe_paths import checked_path  # noqa: E402

BRIEF = """# BRIEF — {slug}

> المصدر الوحيد للطلبات: العناصر الأربعة. أي حاجة تانية الوكيل بيقررها.
> The four inputs. Everything else is the agent's decision.

## 1) السكريبت — Script
<!-- الصق السكريبت هنا. الأفضل: beats مرقمة، ومع كل beat اللي يظهر على الشاشة. -->
```
(1) ...
(2) ...
```

## 2) توجيه المشاهد — Scene direction
<!-- إزاي عايز المشاهد تتقدم: الترتيب، الإحساس، كل مشهد فيه إيه. -->

## 3) صوت التعليق — VO
- file: `assets/vo/` (لسه؟ حط الملف هنا)
- measured duration: `—`

## 4) صور ميدو — Poses
- [x] `assets/poses/` — المكتبة كاملة (٤٩ وضعية) + `poses.json` بتتنسخ أوتوماتيك من الاستوديو
   (شوف `docs/presenter.md`; منها full: neutral, arms-crossed, explain, point, welcome, wave, clap,
   celebrate, like, thinking, sad, shocked, walk, run, seated-talk, laptop-work — ونصف جسم:
   listen, shrug, searching, angry, sigh, close-explain, close-thinking …)
- [ ] مشهد محتاج وضعية مش في المكتبة؟ اكتب هنا اسم الوضعية والمشهد اللي محتاجها → هتتدخل خط الإنتاج
   (`assets/poses/source/<id>.png` → `tools/lib/pose_catalog.py` → `make poses`), متضيفش صورة خام.

## 5) الخلفية — Background
- الخلفيات من الكتالوج: `medo-motion/motion/backgrounds.json` (١٢ نمط × فاتح/غامق، كلها بالپاليت)
- اختار لكل مشهد: id: `—` — ليه: `—` (شوف الشيت: `make backgrounds` · `docs/backgrounds.md`)

## مرجع بصري (اختياري) — Visual reference
- file/link: `assets/refs/` — حلّله كإلهام للحركة والتكوين فقط؛ ممنوع نسخ شعاراته أو أصوله.

---
## قرارات الوكيل — Agent decisions (auto-filled)
- engine: `—`            <!-- P = Pillow، K = Canvas/Playwright، R = Remotion، Hybrid = مقاطع متتابعة -->
- text motion: `plan/text-direction.json` — الوكيل بيختار ستايل حركة **كل نص ظاهر** (كابشن، عنوان، رقم، CTA، ليبل، UI) لكل مشهد ويبرّره (مفيش default)
- font: الوكيل بيختار من `assets/fonts/fonts.json` (٢١ عيلة OFL) لكل مشهد/عنصر — مفيش خط افتراضي مفروض
- music: `Am–F–C–G · 76 BPM · ducked` (locked) / none
- sfx source: `procedural` → Openverse → (ElevenLabs with approval)
- assumptions: `—`

## اللي ناقص — Missing / at risk
- `—`
"""

PROGRESS = """# PROGRESS — {slug}

| stage | state | note |
|---|---|---|
| intake (4 inputs) | ⬜ | |
| reference analysed / STYLE.md | ⬜ | optional — no reference is required |
| VO analysed / beats locked | ⬜ | |
| engine chosen | ⬜ | |
| text direction (every text element) | ⬜ | plan/text-direction.json — agent chooses a style for all on-screen text, no default |
| scene 1 prototype | ⬜ | |
| contact sheet (4–8 frames) | ⬜ | |
| full render (chunks) | ⬜ | |
| mix (−14.5 LUFS) | ⬜ | |
| master encode (CRF13 ≥2.5Mbps) | ⬜ | |
| QC + brand_check | ⬜ | |
| delivered | ⬜ | |

## Log
- {slug} scaffolded by tools/new_project.py
"""


READ_ONLY_DIRS = ("medo-motion", "tools", "tests", "assets")
STANDARD_DIRS = ("plan", "assets/vo", "assets/poses", "assets/refs", "assets/fonts/Cairo",
                 "assets/sfx", "out", "cache")
# This studio is a tool, not a video archive: a project folder stays out of Git history.
PROJECT_IGNORE = ("# A video project is a working folder, not studio memory.\n"
                  "# Keep it out of the studio's Git history (AGENTS.md §2 rule 12).\n"
                  "*\n")


def slugify(raw: str) -> str:
    """A filesystem-safe project name; an empty result means the input had no usable characters."""
    slug = re.sub(r"[^a-z0-9\-_]+", "-", raw.lower()).strip("-")
    if not slug:
        raise SystemExit(f"invalid project name {raw!r}: after normalisation the slug is empty "
                         f"— use at least one letter or digit, e.g. my-reel")
    return slug


def resolve_target(raw_slug: str, out: str | None) -> Path:
    """Where the project folder goes, refusing the toolkit and the repo root.

    A custom --out is allowed (the video may live outside the repo) but never inside a
    read-only kit directory; without --out the target must be a named subfolder of projects/.
    """
    default_root = ROOT / "projects"
    target = Path(out).expanduser().resolve() if out else default_root / slugify(raw_slug)
    if target == target.parent or target == ROOT:
        raise SystemExit(f"refusing to scaffold into {target} — the target must be a named folder")
    if out:
        for read_only in (ROOT / name for name in READ_ONLY_DIRS):
            if target == read_only or read_only in target.parents:
                raise SystemExit(f"refusing to scaffold into {target} — {read_only.name}/ is read-only")
    elif target == default_root or default_root not in target.parents:
        raise SystemExit(f"refusing to scaffold into {target} — the target must be a named "
                         f"subfolder of projects/")
    try:
        # Symlink safety only in the --out case; the parent directory is the user's choice.
        checked_path(target, tree=True) if out else checked_path(target, within=default_root, tree=True)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    return target


def write_plan_files(project: Path) -> None:
    """Every plan file the lint/render gates expect, each starting as an explicit draft."""
    plans = {
        "beats.json": {"duration": None, "scenes": [],
                       "note": "fill it from the VO: python3 tools/vo_length.py <vo> --json plan/beats.json"},
        "text-direction.json": {
            "version": 3, "status": "draft", "decidedBy": None, "concept": None, "scenes": [],
            "note": "the agent chooses a motion style AND a font for EVERY on-screen text element "
                    "(captions, titles, numbers, CTAs, labels, UI) and explains why; no creative default"},
        "visual-direction.json": {
            "version": 1, "clock": "vo", "status": "draft", "decidedBy": None, "scenes": [],
            "note": "after measured VO beats exist, run tools/visual_direction.py <project> "
                    "--init --force; choose treatments and measured word anchors"},
        "copy.json": {"pace": "calm", "bpm": 100, "copy": [],
                      "note": "one entry per on-screen fragment: "
                              "{scene, text, start, end, mode: build|replace}"},
        "stage.json": {
            "version": 1,
            "enabled": False,
            "clock": "vo",
            "mode": "fullscreen",
            "theme": "dark",
            "defaultFramedBox": {"x": 56, "y": 224, "w": 968, "h": 1096, "r": 36},
            "note": "optional Fixed Stage: set enabled=true and configure timeline/under/over (see docs/fixed-stage.md)",
        },
    }
    for name, document in plans.items():
        (project / "plan" / name).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (project / "plan" / "script.md").write_text("# Script\n\n(paste the numbered beats here)\n",
                                                encoding="utf-8")


def copy_assets(project: Path) -> None:
    """Poses, the whole free type system, and the project-memory templates."""
    poses = ROOT / "assets" / "poses"
    if poses.is_dir():
        for image in poses.glob("*.png"):
            shutil.copy2(image, project / "assets" / "poses" / image.name)
        if (poses / "poses.json").is_file():
            shutil.copy2(poses / "poses.json", project / "assets" / "poses" / "poses.json")

    fonts = ROOT / "assets" / "fonts"
    for family_dir in sorted(d for d in fonts.iterdir() if d.is_dir()):
        destination = project / "assets" / "fonts" / family_dir.name
        destination.mkdir(parents=True, exist_ok=True)
        for font_file in family_dir.iterdir():
            if font_file.is_file():
                shutil.copy2(font_file, destination / font_file.name)
    if (fonts / "fonts.json").is_file():
        shutil.copy2(fonts / "fonts.json", project / "assets" / "fonts" / "fonts.json")

    for name in ("TASTE.md", "STYLE.md"):
        template = SKILL / "templates" / name
        if template.is_file():
            shutil.copy2(template, project / name)


def _copy_flat(source: Path, destination: Path) -> None:
    for item in source.iterdir():
        if item.is_file():
            shutil.copy2(item, destination / item.name)


def _public_fonts(project: Path) -> None:
    """Remotion serves local media from public/; expose every manifest face the agent may pick."""
    fonts = ROOT / "assets" / "fonts"
    public_fonts = project / "public" / "fonts"
    public_fonts.mkdir(parents=True, exist_ok=True)
    for family_dir in sorted(d for d in fonts.iterdir() if d.is_dir()):
        destination = public_fonts / family_dir.name
        destination.mkdir(parents=True, exist_ok=True)
        for font_file in family_dir.iterdir():
            if font_file.is_file() and (font_file.suffix == ".ttf" or font_file.name == "OFL.txt"):
                shutil.copy2(font_file, destination / font_file.name)
    if (fonts / "fonts.json").is_file():
        shutil.copy2(fonts / "fonts.json", public_fonts / "fonts.json")


def _public_poses(project: Path) -> None:
    """Keep the pose library addressable through Remotion's staticFile()."""
    public_poses = project / "public" / "assets" / "poses"
    public_poses.mkdir(parents=True, exist_ok=True)
    for image in (project / "assets" / "poses").glob("*.png"):
        shutil.copy2(image, public_poses / image.name)
    manifest = project / "assets" / "poses" / "poses.json"
    if manifest.is_file():
        shutil.copy2(manifest, public_poses / manifest.name)


def install_engine(project: Path, engine: str) -> None:
    """Copy the chosen read-only template(s) into the project. The toolkit is never edited."""
    procedural = SKILL / "templates" / "procedural-reels"
    render = SKILL / "templates" / "render"
    remotion = SKILL / "templates" / "remotion"

    if engine == "p":
        _copy_flat(procedural, project)
    elif engine == "k":
        shutil.copytree(render, project / "src", dirs_exist_ok=True)
        (project / "package.json").write_text('{"type":"module","private":true}\n', encoding="utf-8")
    elif engine in {"r", "hybrid"}:
        shutil.copytree(remotion, project, dirs_exist_ok=True)
        _public_fonts(project)
        _public_poses(project)
        if engine == "hybrid":
            # Keep P, K and R as separate, inspectable engines: the hybrid runner renders
            # sequential full-frame segments and then normalizes/assembles them.
            _copy_flat(procedural, project)
            shutil.copytree(render, project / "src", dirs_exist_ok=True)
            shutil.copy2(SKILL / "templates" / "HYBRID.md", project / "HYBRID.md")
            (project / "plan" / "hybrid.json").write_text(json.dumps({
                "version": 1, "fps": 30, "width": 1080, "height": 1920,
                "duration_frames": None, "segments": [], "audio": None,
            }, indent=2) + "\n", encoding="utf-8")


def scaffold(slug: str, engine: str, out: str | None = None, force: bool = False) -> Path:
    project = resolve_target(slug, out)
    if project.exists() and not force:
        raise SystemExit(f"{project} already exists (use --force)")

    for directory in STANDARD_DIRS:
        (project / directory).mkdir(parents=True, exist_ok=True)
    (project / ".gitignore").write_text(PROJECT_IGNORE, encoding="utf-8")
    (project / "BRIEF.md").write_text(BRIEF.format(slug=slug), encoding="utf-8")
    (project / "PROGRESS.md").write_text(PROGRESS.format(slug=slug), encoding="utf-8")
    write_plan_files(project)
    copy_assets(project)
    install_engine(project, engine)
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="short project name, e.g. laptop-ep1")
    parser.add_argument("--engine", choices=["p", "k", "r", "hybrid", "none"], default="none")
    parser.add_argument("--out", help="where to create the project (default: projects/<slug> in the repo, "
                                      "which Git ignores). Pass a path outside the repo to keep the video elsewhere.")
    parser.add_argument("--force", action="store_true")
    options = parser.parse_args(argv)

    slug = slugify(options.slug)
    project = scaffold(slug, options.engine, options.out, options.force)
    shown = project.relative_to(ROOT) if ROOT in project.parents else project
    print(f"created {shown}  (engine={options.engine})")
    print("next: fill BRIEF.md with the 4 inputs, then read AGENTS.md §5")
    return 0


if __name__ == "__main__":
    main()
