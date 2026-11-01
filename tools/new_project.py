#!/usr/bin/env python3
"""Create a reel project scaffold.

    python3 tools/new_project.py my-reel                 # scaffold only
    python3 tools/new_project.py my-reel --engine p      # + copy engine P into the project
    python3 tools/new_project.py my-reel --engine k      # + copy engine K into src/

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

---
## قرارات الوكيل — Agent decisions (auto-filled)
- engine: `—`            <!-- P = procedural-reels، K = canvas/playwright -->
- font: `Cairo` (locked)
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
| VO analysed / beats locked | ⬜ | |
| engine chosen | ⬜ | |
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
    ap.add_argument("--engine", choices=["p", "k", "none"], default="none")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    slug = re.sub(r"[^a-z0-9\-_]+", "-", a.slug.lower()).strip("-")
    proj = ROOT / "projects" / slug
    if proj.exists() and not a.force:
        raise SystemExit(f"projects/{slug} already exists (use --force)")

    for d in ["plan", "assets/vo", "assets/poses", "assets/fonts/Cairo", "assets/sfx", "out", "cache"]:
        (proj / d).mkdir(parents=True, exist_ok=True)

    (proj / "BRIEF.md").write_text(BRIEF.format(slug=slug), encoding="utf-8")
    (proj / "PROGRESS.md").write_text(PROGRESS.format(slug=slug), encoding="utf-8")
    (proj / "plan" / "beats.json").write_text(json.dumps(
        {"duration": None, "scenes": [], "note": "fill it from the VO: python3 tools/vo_length.py <vo> --json plan/beats.json"}, indent=2), encoding="utf-8")
    (proj / "plan" / "script.md").write_text("# Script\n\n(paste the numbered beats here)\n", encoding="utf-8")

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
    # taste file (brand-prefilled template)
    taste = SKILL / "templates" / "TASTE.md"
    if taste.is_file():
        shutil.copy2(taste, proj / "TASTE.md")

    if a.engine == "p":
        for f in (SKILL / "templates" / "procedural-reels").iterdir():
            if f.is_file():
                shutil.copy2(f, proj / f.name)
    elif a.engine == "k":
        shutil.copytree(SKILL / "templates" / "render", proj / "src", dirs_exist_ok=True)
        (proj / "package.json").write_text('{"type":"module","private":true}\n', encoding="utf-8")

    print(f"created projects/{slug}  (engine={a.engine})")
    print("next: fill BRIEF.md with the 4 inputs, then read AGENTS.md §5")


if __name__ == "__main__":
    main()
