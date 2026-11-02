#!/usr/bin/env python3
"""Create a reel project scaffold.

    python3 tools/new_project.py my-reel                 # scaffold only
    python3 tools/new_project.py my-reel --engine p      # + copy engine P into the project
    python3 tools/new_project.py my-reel --engine k      # + copy engine K into src/
    python3 tools/new_project.py my-reel --engine r      # + copy Remotion (React/TS) into the project
    python3 tools/new_project.py my-reel --engine hybrid # + install P, K and R sequential hybrid scaffold

Layout follows medo-motion/reference/planning-and-tracking.md.
The scaffold asks for nothing: fill BRIEF.md with the four inputs (script, scene
direction, VO, poses). There is no logo and no series name — by design.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "medo-motion"

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
- [x] `assets/poses/` — صور ميدو (١٤ وضعية) + `poses.json` بتتنسخ أوتوماتيك من الاستوديو
   (شوف `docs/presenter.md`; الوضعيات: neutral, explain, point, welcome, wave, clap, like,
   thinking, thinking-deep, puzzled, sad, shocked, walk, run)

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="short project name, e.g. laptop-ep1")
    ap.add_argument("--engine", choices=["p", "k", "r", "hybrid", "none"], default="none")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    slug = re.sub(r"[^a-z0-9\-_]+", "-", a.slug.lower()).strip("-")
    if not slug:
        raise SystemExit(f"invalid project name {a.slug!r}: after normalisation the slug is empty "
                         f"— use at least one letter or digit, e.g. my-reel")
    proj = ROOT / "projects" / slug
    # belt and braces: even with --force the target must be a named subfolder of projects/,
    # never projects/ itself or anything outside it
    if proj == ROOT / "projects" or ROOT / "projects" not in proj.parents:
        raise SystemExit(f"refusing to scaffold into {proj} — the target must be a named "
                         f"subfolder of projects/")
    if proj.exists() and not a.force:
        raise SystemExit(f"projects/{slug} already exists (use --force)")

    for d in ["plan", "assets/vo", "assets/poses", "assets/refs", "assets/fonts/Cairo", "assets/sfx", "out", "cache"]:
        (proj / d).mkdir(parents=True, exist_ok=True)

    (proj / "BRIEF.md").write_text(BRIEF.format(slug=slug), encoding="utf-8")
    (proj / "PROGRESS.md").write_text(PROGRESS.format(slug=slug), encoding="utf-8")
    (proj / "plan" / "beats.json").write_text(json.dumps(
        {"duration": None, "scenes": [], "note": "fill it from the VO: python3 tools/vo_length.py <vo> --json plan/beats.json"}, indent=2), encoding="utf-8")
    (proj / "plan" / "script.md").write_text("# Script\n\n(paste the numbered beats here)\n", encoding="utf-8")
    # Text motion is an explicit agent decision per scene — never a default look.
    # After the VO beats exist, run: python3 tools/text_direction.py projects/<slug> --init
    (proj / "plan" / "text-direction.json").write_text(json.dumps({
        "version": 3, "status": "draft", "decidedBy": None, "concept": None, "scenes": [],
        "note": "the agent chooses a motion style AND a font for EVERY on-screen text element (captions, titles, numbers, CTAs, labels, UI) and explains why; no creative default",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # What appears on screen, and the moves drawn for this reel (docs/craft.md §3 and §4).
    (proj / "plan" / "copy.json").write_text(json.dumps({
        "pace": "calm", "bpm": 100, "copy": [],
        "note": "one entry per on-screen fragment: {scene, text, start, end, mode: build|replace}",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # brand font
    poses_src = ROOT / "assets" / "poses"
    if poses_src.exists():
        for f in poses_src.glob("*.png"):
            shutil.copy2(f, proj / "assets" / "poses" / f.name)
        if (poses_src / "poses.json").exists():
            shutil.copy2(poses_src / "poses.json", proj / "assets" / "poses" / "poses.json")
    # the whole free type system (docs/fonts.md) — engine K resolves it through lib/fonts.js
    for fam_dir in sorted(p for p in (ROOT / "assets" / "fonts").iterdir() if p.is_dir()):
        dst = proj / "assets" / "fonts" / fam_dir.name
        dst.mkdir(parents=True, exist_ok=True)
        for f in fam_dir.iterdir():
            if f.is_file():
                shutil.copy2(f, dst / f.name)
    if (ROOT / "assets" / "fonts" / "fonts.json").is_file():
        shutil.copy2(ROOT / "assets" / "fonts" / "fonts.json", proj / "assets" / "fonts" / "fonts.json")
    # Project memory (brand-prefilled) and the optional reference-to-style recipe.
    taste = SKILL / "templates" / "TASTE.md"
    if taste.is_file():
        shutil.copy2(taste, proj / "TASTE.md")
    style = SKILL / "templates" / "STYLE.md"
    if style.is_file():
        shutil.copy2(style, proj / "STYLE.md")

    if a.engine == "p":
        for f in (SKILL / "templates" / "procedural-reels").iterdir():
            if f.is_file():
                shutil.copy2(f, proj / f.name)
    elif a.engine == "k":
        shutil.copytree(SKILL / "templates" / "render", proj / "src", dirs_exist_ok=True)
        (proj / "package.json").write_text('{"type":"module","private":true}\n', encoding="utf-8")
    elif a.engine in {"r", "hybrid"}:
        shutil.copytree(SKILL / "templates" / "remotion", proj, dirs_exist_ok=True)
        # Remotion serves local media from public/. The agent may choose any manifest
        # face, so expose the whole free type system (family subfolders + manifest).
        public_fonts = proj / "public" / "fonts"
        public_fonts.mkdir(parents=True, exist_ok=True)
        for fam_dir in sorted(p for p in (ROOT / "assets" / "fonts").iterdir() if p.is_dir()):
            dst = public_fonts / fam_dir.name
            dst.mkdir(parents=True, exist_ok=True)
            for f in fam_dir.iterdir():
                if f.is_file() and (f.suffix == ".ttf" or f.name == "OFL.txt"):
                    shutil.copy2(f, dst / f.name)
        if (ROOT / "assets" / "fonts" / "fonts.json").is_file():
            shutil.copy2(ROOT / "assets" / "fonts" / "fonts.json", public_fonts / "fonts.json")
        # Keep Medo's existing pose library addressable through Remotion's staticFile().
        public_poses = proj / "public" / "assets" / "poses"
        public_poses.mkdir(parents=True, exist_ok=True)
        for image in (proj / "assets" / "poses").glob("*.png"):
            shutil.copy2(image, public_poses / image.name)
        pose_manifest = proj / "assets" / "poses" / "poses.json"
        if pose_manifest.is_file():
            shutil.copy2(pose_manifest, public_poses / pose_manifest.name)

        if a.engine == "hybrid":
            # Keep P, K and R as separate, inspectable engines. The hybrid runner
            # renders a sequential timeline and then normalizes/assembles the clips.
            for source in (SKILL / "templates" / "procedural-reels").iterdir():
                if source.is_file():
                    shutil.copy2(source, proj / source.name)
            shutil.copytree(SKILL / "templates" / "render", proj / "src", dirs_exist_ok=True)
            (proj / "HYBRID.md").write_text((SKILL / "templates" / "HYBRID.md").read_text(encoding="utf-8"), encoding="utf-8")
            (proj / "plan" / "hybrid.json").write_text(json.dumps({
                "version": 1, "fps": 30, "width": 1080, "height": 1920,
                "duration_frames": None, "segments": [], "audio": None,
            }, indent=2) + "\n", encoding="utf-8")

    print(f"created projects/{slug}  (engine={a.engine})")
    print("next: fill BRIEF.md with the 4 inputs, then read AGENTS.md §5")


if __name__ == "__main__":
    main()
