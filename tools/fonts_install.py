#!/usr/bin/env python3
"""Fetch the studio's ORIGINAL type system into `assets/fonts/` — free licences only.

This script manages the original 21 npm-pinned families (see `tools/font-packages.lock.json`,
SIL OFL 1.1). The manifest in `assets/fonts/fonts.json` is BIGGER than this script: the Alansari
integration added 104 more families (mostly OFL; Permanent Marker is Apache-2.0 and Ubuntu is
UFL-1.0) which are already on disk and are preserved on every run — this script never deletes or
narrows the manifest, it only adds/updates the families listed in `FAMILIES`.

Every family managed here is on Google Fonts; we pull the actual `.ttf` files from the
`@expo-google-fonts/*` npm packages (same binaries Google serves, plus the OFL text), because npm is
a host we can reach from a sandbox and it keeps the provenance reproducible.
The lock file (`tools/font-packages.lock.json`) pins the npm coordinates (version + SHA-512
integrity) of the 21 managed families AND of the 100 Alansari-added families that
`@expo-google-fonts` publishes (pinned 2026-11-09 from the registry's `dist.integrity`).
The four Alansari families in `LOCK_EXCEPTIONS` have no npm package — see the constant's comment.

    python3 tools/fonts_install.py                 # all managed families that are missing
    python3 tools/fonts_install.py --only tajawal   # one family
    python3 tools/fonts_install.py --force          # re-fetch the managed families
    python3 tools/fonts_install.py --list           # what is in the manifest
    python3 tools/fonts_install.py --check          # read-only validation of the WHOLE manifest
    python3 tools/fonts_install.py --verify-lock    # read-only audit of tools/font-packages.lock.json

The result is `assets/fonts/<Family>/<File>.ttf` + `OFL.txt` per managed family, and
`assets/fonts/fonts.json` — the single source of truth both engines read
(`lib.font(size, family)` / `lib/fonts.js`).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
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
LOCK = ROOT / "tools" / "font-packages.lock.json"

# Alansari-added families with NO @expo-google-fonts package (HTTP 404 on the registry,
# 2026-11-09) — variable fonts that are only published via fonts.google.com specimens.
# They ship in the repo with their specimen source and OFL licence (see the manifest's
# `source` and `licence_file`). This set is not a waiver for licence review: adding a
# lock entry for any of them later is a deliberate act — update this constant in the
# same commit.
LOCK_EXCEPTIONS = ("firjar", "thabit", "noto-naskh-arabic-ui", "noto-sans-arabic-ui")

# Curated, not exhaustive: each family has one job. `pairs` is the Arabic↔Latin pairing that shares
# proportions, so a mixed line looks designed rather than assembled.
FAMILIES = [
    # ---------------- Arabic ----------------
    {
        "family": "Cairo", "npm": "cairo", "script": "arabic", "weights": [400, 700, 800, 900],
        "role": "available option / system-chrome fallback — captions, body, lower thirds (not a forced creative default)",
        "pairs": "Inter", "tags": ["brand", "sans", "neutral", "fallback"],
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
        "role": "available option / system-chrome fallback — UI, data, mixed Arabic+Latin lines",
        "pairs": "Cairo", "tags": ["brand", "sans", "ui", "fallback"],
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
    segments, links and special files are all rejected.
    """
    dest = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if target != dest and dest not in target.parents:
            raise SystemExit(f"refusing unsafe archive member (escapes the target dir): {member.name!r}")
        # Packages contain only directories and regular files. Reject links and
        # special files entirely, including link chains on the Python 3.10 fallback.
        if not member.isfile() and not member.isdir():
            raise SystemExit(f"refusing unsafe archive link/special file: {member.name!r}")
    try:
        tar.extractall(dest, filter="data")    # py>=3.12
    except TypeError:                          # py3.10/3.11: safe because members were validated above
        tar.extractall(dest)


def pack(npm_name: str, dest: Path) -> Path:
    """`npm pack` one family and extract it; returns the extracted package dir."""
    dest.mkdir(parents=True, exist_ok=True)
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    spec = lock[f"@expo-google-fonts/{npm_name}"]
    version = spec["version"]
    tgz = dest / f"{npm_name}-{version}.tgz"
    if not tgz.is_file():
        r = subprocess.run(["npm", "pack", f"@expo-google-fonts/{npm_name}@{version}", "--silent",
                            "--pack-destination", str(dest)], capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit(f"npm pack @expo-google-fonts/{npm_name} failed:\n{r.stderr}")
        produced = sorted(dest.glob(f"expo-google-fonts-{npm_name}-{version}.tgz"))
        if not produced:
            raise SystemExit(f"npm pack produced nothing for {npm_name}")
        produced[-1].replace(tgz)
    integrity = "sha512-" + base64.b64encode(hashlib.sha512(tgz.read_bytes()).digest()).decode()
    if not hmac.compare_digest(integrity, spec["integrity"]):
        raise SystemExit(f"font archive checksum mismatch: {tgz}; remove it and retry")
    out = dest / f"{npm_name}-{version}"
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
    """The manifest describes what is actually on disk — never a wish list.

    Merges with the existing manifest: families not managed by this script (the Alansari
    additions) are preserved untouched, including their `status`/licence fields. Managed
    families get their weights re-detected from disk; `status`, `licence` and `licence_file`
    are preserved from the existing entry when present.
    """
    existing = {}
    try:
        existing = json.loads(MANIFEST.read_text(encoding="utf-8")).get("families", {})
    except (OSError, ValueError):
        existing = {}
    families = dict(existing)
    families.update(_build_managed_families())
    try:
        note = json.loads(MANIFEST.read_text(encoding="utf-8")).get("note")
    except (OSError, ValueError):
        note = None
    if not note:
        note = (
            "Free type system — the only fonts allowed on screen. See each family's "
            "licence/licence_file in this manifest for licence details. `status`: ok = passes "
            "the shaping/collision gate (tests/test_fonts.py); review = measured >= 0.20 on "
            "2026-11-09 (see docs/fonts.md)."
        )
    return {"note": note, "fallback": {"arabic": "Cairo", "latin": "Inter"}, "families": families}


def _build_managed_families() -> dict:
    families = {}
    existing = {}
    try:
        existing = json.loads(MANIFEST.read_text(encoding="utf-8")).get("families", {})
    except (OSError, ValueError):
        existing = {}
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
        prev = existing.get(spec["family"], {})
        entry = {
            "script": spec["script"],
            "role": spec["role"],
            "pairs": spec["pairs"],
            "tags": spec["tags"],
            "weights": sorted(weights, key=lambda w: w["weight"]),
            "licence": prev.get("licence", "OFL-1.1"),
            "licence_file": f"{spec['family']}/OFL.txt" if (target / "OFL.txt").is_file() else prev.get("licence_file"),
            "source": prev.get("source", f"https://fonts.google.com/specimen/{spec['family'].replace(' ', '+')}"),
            "npm": f"@expo-google-fonts/{spec['npm']}",
        }
        # Preserve the curation fields from the curated manifest — regenerating must never erase them.
        for key in ("status", "status_note"):
            if key in prev:
                entry[key] = prev[key]
        families[spec["family"]] = entry
    return families


def check_type_system(base: Path = OUT) -> list[str]:
    """Validate every family in the manifest, its files, and each declared licence."""
    problems = []
    try:
        families = json.loads((base / "fonts.json").read_text(encoding="utf-8"))["families"]
        for family, meta in families.items():
            weights = meta.get("weights", [])
            if not weights:
                problems.append(f"{family}: no weights in manifest")
            paths = [base / family / w["file"] for w in weights]
            licence_file = meta.get("licence_file")
            paths.append(base / licence_file if licence_file else base / family / "OFL.txt")
            for path in paths:
                if not path.resolve().is_relative_to(base.resolve()) or not path.is_file() or path.stat().st_size == 0:
                    problems.append(f"{family}: missing/unsafe/empty file {path.name}")
            if meta.get("status") not in {"ok", "review"}:
                problems.append(f"{family}: status must be 'ok' or 'review' (got {meta.get('status')!r})")
        # The 21 npm-managed families must keep at least their pinned weights —
        # and every declared file (TTFs + OFL.txt) must exist.
        for spec in FAMILIES:
            family = spec["family"]
            meta = families.get(family, {})
            weights = meta.get("weights", [])
            if not set(spec["weights"]).issubset({w["weight"] for w in weights}):
                problems.append(f"{family}: missing manifest weights")
            paths = [base / family / w["file"] for w in weights]
            paths.append(base / family / "OFL.txt")
            for path in paths:
                if not path.resolve().is_relative_to(base.resolve()) or not path.is_file() or path.stat().st_size == 0:
                    problems.append(f"{family}: missing/unsafe/empty file {path.name}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        problems.append(f"invalid type system: {error}")
    return problems


_SHA512_RE = re.compile(r"^sha512-[A-Za-z0-9+/]{86}={0,2}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
FREE_LICENCES = {"OFL-1.1", "Apache-2.0", "UFL-1.0"}


def _slugify(name: str) -> str:
    """The @expo-google-fonts slug for a family name (lowercase, hyphenated)."""
    s = name.lower().replace(" ", "-")
    s = re.sub(r"[^a-z0-9-]", "", s)
    return re.sub(r"-+", "-", s).strip("-")


def verify_lock(base: Path = OUT) -> list[str]:
    """Read-only audit of tools/font-packages.lock.json against the manifest and disk.

    The lock must cover the 21 managed families (pack() consumes it) and exactly the
    Alansari families that @expo-google-fonts publishes — no missing pins, no stale ones,
    no silent exceptions. Every locked Alansari family must carry a declared free licence
    and its licence file on disk (the mechanical half of the OFL review).
    """
    problems: list[str] = []
    try:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        return [f"cannot read {LOCK.relative_to(ROOT)}: {error}"]
    if not isinstance(lock, dict):
        return [f"{LOCK.relative_to(ROOT)} must be a JSON object of package -> pin"]
    for key, spec in sorted(lock.items()):
        if not key.startswith("@expo-google-fonts/"):
            problems.append(f"{key}: lock keys must be @expo-google-fonts/<slug>")
            continue
        if not isinstance(spec, dict) or set(spec) != {"integrity", "version"}:
            problems.append(f"{key}: entry must be exactly {{integrity, version}}")
            continue
        integrity, version = spec["integrity"], spec["version"]
        if not isinstance(integrity, str) or not _SHA512_RE.match(integrity):
            problems.append(f"{key}: integrity must be sha512-<base64 of 64 bytes>")
        else:
            try:
                if len(base64.b64decode(integrity[len("sha512-"):])) != 64:
                    problems.append(f"{key}: integrity payload is not 64 bytes")
            except Exception:  # noqa: BLE001 - any decode failure is a bad pin
                problems.append(f"{key}: integrity is not valid base64")
        if not isinstance(version, str) or not _SEMVER_RE.match(version):
            problems.append(f"{key}: version {version!r} is not semver")

    try:
        manifest = json.loads((base / "fonts.json").read_text(encoding="utf-8"))["families"]
    except (OSError, ValueError) as error:
        return problems + [f"cannot read the manifest: {error}"]

    managed_names = {spec["family"] for spec in FAMILIES}
    managed_slugs = {f"@expo-google-fonts/{spec['npm']}" for spec in FAMILIES}
    for key in sorted(managed_slugs - set(lock)):
        problems.append(f"{key}: managed family missing from the lock")

    alansari = {name: meta for name, meta in manifest.items() if name not in managed_names}
    slug_of = {name: _slugify(name) for name in alansari}
    for name, slug in sorted(slug_of.items()):
        key = f"@expo-google-fonts/{slug}"
        if slug in LOCK_EXCEPTIONS:
            if key in lock:
                problems.append(f"{name}: pinned in the lock but listed in LOCK_EXCEPTIONS — pick one")
            continue
        if key not in lock:
            problems.append(f"{name}: {key} missing from the lock "
                            f"(pin it, or add {slug!r} to LOCK_EXCEPTIONS with its specimen source)")
            continue
        meta = manifest[name]
        if meta.get("licence") not in FREE_LICENCES:
            problems.append(f"{name}: licence {meta.get('licence')!r} is not one of {sorted(FREE_LICENCES)}")
        licence_file = meta.get("licence_file")
        if not licence_file or not (base / licence_file).is_file() or (base / licence_file).stat().st_size == 0:
            problems.append(f"{name}: declared licence file {licence_file!r} missing/empty on disk")

    covered = set(managed_slugs) | {f"@expo-google-fonts/{slug_of[n]}" for n in alansari
                                     if slug_of[n] not in LOCK_EXCEPTIONS}
    for key in sorted(set(lock) - covered):
        problems.append(f"{key}: lock entry matches no family in the manifest (stale pin?)")
    for slug in LOCK_EXCEPTIONS:
        if slug not in set(slug_of.values()):
            problems.append(f"LOCK_EXCEPTIONS lists {slug!r} but no Alansari family slugifies to it")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="read-only check of every family and file")
    ap.add_argument("--only", action="append", help="family name (repeatable)")
    ap.add_argument("--force", action="store_true", help="re-fetch even if the files exist")
    ap.add_argument("--list", action="store_true", help="print the manifest and exit")
    ap.add_argument("--verify-lock", action="store_true",
                    help="read-only audit of tools/font-packages.lock.json against the manifest and disk")
    a = ap.parse_args()

    if a.verify_lock:
        problems = verify_lock()
        try:
            pinned = len(json.loads(LOCK.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pinned = 0
        print("\n".join(problems) if problems
              else f"Font packages lock OK ({pinned} pinned packages, "
                   f"{len(LOCK_EXCEPTIONS)} documented exceptions, licence files verified)")
        return int(bool(problems))

    if a.check:
        problems = check_type_system()
        try:
            n = len(json.loads(MANIFEST.read_text(encoding="utf-8"))["families"])
        except (OSError, ValueError):
            n = len(FAMILIES)
        print("\n".join(problems) if problems else f"Type system OK ({n} families in manifest, files verified)")
        return int(bool(problems))

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
