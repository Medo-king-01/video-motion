#!/usr/bin/env python3
"""Fetch the studio's type system into `assets/fonts/` — free (SIL OFL 1.1) only.

Every family here is on Google Fonts under the SIL Open Font License: free for commercial use,
redistribution allowed, no attribution required on screen. We pull the actual `.ttf` files from the
`@expo-google-fonts/*` npm packages (same binaries Google serves, plus the OFL text), because npm is
a host we can reach from a sandbox and it keeps the provenance reproducible.

    python3 tools/fonts_install.py                 # all families that are missing
    python3 tools/fonts_install.py --only tajawal   # one family
    python3 tools/fonts_install.py --force          # re-fetch everything
    python3 tools/fonts_install.py --list           # what is in the manifest

The result is `assets/fonts/<Family>/<File>.ttf` + `OFL.txt` per family, and `assets/fonts/fonts.json`
— the single source of truth both engines read (`lib.font(size, family)` / `lib/fonts.js`).
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "fonts"
MANIFEST = OUT / "fonts.json"
CACHE = ROOT / "cache" / "fonts-pack"

# Curated, not exhaustive: each family has one job. `pairs` is the Arabic↔Latin pairing that shares
# proportions, so a mixed line looks designed rather than assembled.
FAMILIES = [
    # ---------------- Arabic ----------------
    {
        "family": "Cairo", "npm": "cairo", "script": "arabic", "weights": [400, 700, 800, 900],
        "role": "brand default — captions, body, lower thirds (the locked brand face)",
        "pairs": "Inter", "tags": ["brand", "sans", "neutral", "default"],
    },
    {
        "family": "Tajawal", "npm": "tajawal", "script": "arabic", "weights": [400, 500, 700, 800],
        "role": "geometric headlines and numbers — short, confident lines",
        "pairs": "Inter", "tags": ["display", "geometric", "headline"],
    },
    {
        "family": "IBM Plex Sans Arabic", "npm": "ibm-plex-sans-arabic", "script": "arabic",
        "weights": [400, 600],
        "role": "technical / UI / telemetry — label pairs, stat rows, device screens",
        "pairs": "IBM Plex Mono", "tags": ["technical", "ui", "superfamily"],
    },
    {
        "family": "Almarai", "npm": "almarai", "script": "arabic", "weights": [400, 700],
        "role": "small captions and long body where legibility beats personality",
        "pairs": "Inter", "tags": ["legible", "caption", "body"],
    },
    {
        "family": "Alexandria", "npm": "alexandria", "script": "arabic", "weights": [700, 800],
        "role": "big display Arabic (hook word, key number) — wide, modern, high impact",
        "pairs": "Space Grotesk", "tags": ["display", "impact", "hook"],
    },
    {
        "family": "Kufam", "npm": "kufam", "script": "arabic", "weights": [500, 700],
        "role": "kufic-geometric statement — chapter cards, poster-like frames, big numbers",
        "pairs": "Anton", "tags": ["kufic", "display", "poster"],
    },
    {
        "family": "El Messiri", "npm": "el-messiri", "script": "arabic", "weights": [500, 700],
        "role": "Egyptian-flavoured modern display — titles with character, warm not corporate",
        "pairs": "Inter", "tags": ["display", "egyptian", "warm"],
    },
    {
        "family": "Amiri", "npm": "amiri", "script": "arabic", "weights": [400, 700],
        "role": "naskh serif — quotes, citations, a serious editorial beat",
        "pairs": "Instrument Serif", "tags": ["serif", "naskh", "quote"],
    },
    {
        "family": "Rubik", "npm": "rubik", "script": "arabic", "weights": [400, 500, 700, 800, 900],
        "role": "rounded modern Arabic+Latin — friendly hooks, social captions, bold numbers",
        "pairs": "Sora", "tags": ["display", "rounded", "social", "hook"],
    },
    {
        "family": "Changa", "npm": "changa", "script": "arabic", "weights": [400, 600, 700, 800],
        "role": "condensed Arabic display — punchy headlines, tight kinetic type, countdowns",
        "pairs": "Archivo Black", "tags": ["display", "condensed", "impact"],
    },
    {
        "family": "Readex Pro", "npm": "readex-pro", "script": "arabic", "weights": [400, 600, 700],
        "role": "clean contemporary Arabic+Latin — readable body/UI with a modern edge",
        "pairs": "Sora", "tags": ["modern", "ui", "body", "legible"],
    },
    {
        "family": "Lalezar", "npm": "lalezar", "script": "arabic", "weights": [400],
        "role": "bold display statement — poster frames, chapter cards, big Arabic keywords",
        "pairs": "Bebas Neue", "tags": ["display", "poster", "impact", "heavy"],
    },
    # ---------------- Latin ----------------
    {
        "family": "Inter", "npm": "inter", "script": "latin", "weights": [400, 600, 800],
        "role": "Latin default — UI, data, mixed Arabic+Latin lines",
        "pairs": "Cairo", "tags": ["brand", "sans", "ui", "default"],
    },
    {
        "family": "Space Grotesk", "npm": "space-grotesk", "script": "latin", "weights": [500, 700],
        "role": "technical display — product names, headers with an engineered edge",
        "pairs": "Alexandria", "tags": ["display", "technical", "geometric"],
    },
    {
        "family": "IBM Plex Sans", "npm": "ibm-plex-sans", "script": "latin", "weights": [400, 600],
        "role": "Latin half of the Plex superfamily — pairs 1:1 with IBM Plex Sans Arabic",
        "pairs": "IBM Plex Sans Arabic", "tags": ["technical", "superfamily", "ui"],
    },
    {
        "family": "IBM Plex Mono", "npm": "ibm-plex-mono", "script": "latin", "weights": [400, 600],
        "role": "code, specs, numbers that must line up — terminal / telemetry looks",
        "pairs": "IBM Plex Sans Arabic", "tags": ["mono", "code", "telemetry"],
    },
    {
        "family": "Anton", "npm": "anton", "script": "latin", "weights": [400],
        "role": "one heavy display weight — hooks, single big numbers, CTA",
        "pairs": "Reem Kufi", "tags": ["display", "heavy", "hook"],
    },
    {
        "family": "Instrument Serif", "npm": "instrument-serif", "script": "latin", "weights": [400],
        "role": "editorial serif — quotes and pull-outs against the sans default",
        "pairs": "Amiri", "tags": ["serif", "editorial", "quote"],
    },
    {
        "family": "Archivo Black", "npm": "archivo-black", "script": "latin", "weights": [400],
        "role": "heavy grotesque — loud hooks, single big numbers, stamp-like CTAs",
        "pairs": "Changa", "tags": ["display", "heavy", "hook", "impact"],
    },
    {
        "family": "Bebas Neue", "npm": "bebas-neue", "script": "latin", "weights": [400],
        "role": "tall condensed caps — trailer-style titles, countdowns, kinetic labels",
        "pairs": "Noto Kufi Arabic", "tags": ["display", "condensed", "trailer", "caps"],
    },
    {
        "family": "Sora", "npm": "sora", "script": "latin", "weights": [400, 700, 800],
        "role": "geometric modern Latin — product/UI headers paired with rounded Arabic",
        "pairs": "Rubik", "tags": ["geometric", "modern", "ui", "display"],
    },
]

SUFFIX = {100: "Thin", 200: "ExtraLight", 300: "Light", 400: "Regular", 500: "Medium",
          600: "SemiBold", 700: "Bold", 800: "ExtraBold", 900: "Black"}
FILE_RE = re.compile(r"^(?P<family>.+)_(?P<weight>\d{3})(?P<rest>[A-Za-z]*)\.ttf$")


def _norm(name: str) -> str:
    """'IBM Plex Sans Arabic' == 'IBMPlexSansArabic' — Google's file names drop the spaces."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract only members that stay inside `dest` — never trust the archive's paths.

    `filter="data"` (py>=3.12) already does this, but the project supports 3.10+, so every
    member is validated explicitly here regardless of Python version: absolute paths, `..`
    segments, and symlinks/hardlinks pointing outside the destination are all rejected.
    """
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if target != dest and dest not in target.parents:
            raise SystemExit(f"refusing unsafe archive member (escapes the target dir): {member.name!r}")
        if member.issym() or member.islnk():
            link = Path(member.linkname)
            if link.is_absolute():
                raise SystemExit(f"refusing unsafe archive link (absolute): {member.name!r} -> {member.linkname!r}")
            resolved = (dest / link).resolve()
            if resolved != dest and dest not in resolved.parents:
                raise SystemExit(f"refusing unsafe archive link (escapes the target dir): "
                                 f"{member.name!r} -> {member.linkname!r}")
    try:
        tar.extractall(dest, filter="data")    # py>=3.12
    except TypeError:                          # py3.10/3.11: safe because members were validated above
        tar.extractall(dest)


def pack(npm_name: str, dest: Path) -> Path:
    """`npm pack` one family and extract it; returns the extracted package dir."""
    dest.mkdir(parents=True, exist_ok=True)
    tgz = dest / f"{npm_name}.tgz"
    if not tgz.is_file():
        r = subprocess.run(["npm", "pack", f"@expo-google-fonts/{npm_name}", "--silent",
                            "--pack-destination", str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"npm pack @expo-google-fonts/{npm_name} failed:\n{r.stderr}")
        produced = sorted(dest.glob(f"expo-google-fonts-{npm_name}-*.tgz"))
        if not produced:
            raise SystemExit(f"npm pack produced nothing for {npm_name}")
        produced[-1].replace(tgz)
    out = dest / npm_name
    if not (out / "package" / "package.json").is_file():     # also recovers a half-extracted dir
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=dest) as tmp:
            with tarfile.open(tgz) as tar:
                _safe_extract(tar, Path(tmp))
            shutil.copytree(Path(tmp) / "package", out / "package", dirs_exist_ok=True)
    return out / "package"


def install(spec: dict, force: bool = False) -> dict:
    fam = spec["family"]
    target = OUT / fam
    have = sorted(target.glob("*.ttf")) if target.is_dir() else []
    if have and not force:
        # the TTFs are already there; only the licence text may be missing (older checkouts)
        if not (target / "OFL.txt").is_file():
            src = pack(spec["npm"], CACHE)
            if (src / "LICENSE_FONT").is_file():
                shutil.copy2(src / "LICENSE_FONT", target / "OFL.txt")
        return {"family": fam, "skipped": True, "files": [f.name for f in have]}

    src = pack(spec["npm"], CACHE)
    wanted = set(spec["weights"])
    picked = {}
    for f in sorted(src.rglob("*.ttf")):
        m = FILE_RE.match(f.name)
        if not m or _norm(m.group("family")) != _norm(fam):
            continue
        weight, rest = int(m.group("weight")), m.group("rest")
        if weight not in wanted or "Italic" in rest:
            continue
        picked[weight] = f
    missing = wanted - set(picked)
    if missing:
        raise SystemExit(f"{fam}: missing weights {sorted(missing)} (package has "
                         f"{sorted({int(FILE_RE.match(f.name).group('weight')) for f in src.rglob('*.ttf') if FILE_RE.match(f.name)})})")

    if force and target.is_dir():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    weights = []
    for weight in sorted(picked):
        shutil.copy2(picked[weight], target / picked[weight].name)
        weights.append({"weight": weight, "style": "normal", "file": picked[weight].name})
    licence = src / "LICENSE_FONT"
    if licence.is_file():
        shutil.copy2(licence, target / "OFL.txt")
    return {"family": fam, "skipped": False, "weights": weights,
            "files": [w["file"] for w in weights]}


def build_manifest() -> dict:
    """The manifest describes what is actually on disk — never a wish list."""
    families = {}
    for spec in FAMILIES:
        target = OUT / spec["family"]
        weights = []
        for f in sorted(target.glob("*.ttf")):
            m = FILE_RE.match(f.name)
            if not m or "Italic" in m.group("rest"):
                continue
            weights.append({"weight": int(m.group("weight")), "style": "normal", "file": f.name})
        if not weights:
            continue
        families[spec["family"]] = {
            "script": spec["script"],
            "role": spec["role"],
            "pairs": spec["pairs"],
            "tags": spec["tags"],
            "weights": sorted(weights, key=lambda w: w["weight"]),
            "licence": "OFL-1.1",
            "licence_file": f"{spec['family']}/OFL.txt" if (target / "OFL.txt").is_file() else None,
            "source": f"https://fonts.google.com/specimen/{spec['family'].replace(' ', '+')}",
            "npm": f"@expo-google-fonts/{spec['npm']}",
        }
    return {
        "note": "Free type system (SIL OFL 1.1) — the only fonts allowed on screen. The agent chooses "
                "the most fitting face per scene/element (plan/text-direction.json); there is no "
                "creative default. `fallback` is a last-resort safety net for system chrome only.",
        "fallback": {"arabic": "Cairo", "latin": "Inter"},
        "families": families,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", help="family name (repeatable)")
    ap.add_argument("--force", action="store_true", help="re-fetch even if the files exist")
    ap.add_argument("--list", action="store_true", help="print the manifest and exit")
    a = ap.parse_args()

    if a.list:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else build_manifest()
        for name, meta in manifest["families"].items():
            weights = "/".join(str(w["weight"]) for w in meta["weights"])
            print(f"  {name:<22} {meta['script']:<7} {weights:<16} {meta['role']}")
        return 0

    specs = FAMILIES
    if a.only:
        wanted = {n.lower() for n in a.only}
        specs = [s for s in FAMILIES if s["family"].lower() in wanted]
        if not specs:
            raise SystemExit(f"unknown family: {', '.join(a.only)}")

    for spec in specs:
        res = install(spec, force=a.force)
        state = "kept" if res["skipped"] else "added"
        print(f"{state:<6} {res['family']:<22} {', '.join(res['files'])}")

    manifest = build_manifest()
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(f.stat().st_size for f in OUT.rglob("*.ttf"))
    print(f"manifest -> {MANIFEST.relative_to(ROOT)}  ({len(manifest['families'])} families, "
          f"{total / 1e6:.1f} MB of TTF)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
