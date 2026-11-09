"""The npm download lock for the type system: size, shape, coverage, and exceptions.

tools/font-packages.lock.json pins the @expo-google-fonts packages the studio downloads
(SHA-512 + version). The 21 managed families are consumed by tools/fonts_install.py pack();
the Alansari additions (pinned 2026-11-09) are pinned for reproducible re-fetch and are
excepted only for the four families that have no npm package. This file is the cheap gate;
`python3 tools/fonts_install.py --verify-lock` is the full read-only audit.
"""
from __future__ import annotations

import base64
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "tools" / "font-packages.lock.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((ROOT / "assets" / "fonts" / "fonts.json").read_text(encoding="utf-8"))["families"]
SPEC = importlib.util.spec_from_file_location("fonts_install", ROOT / "tools" / "fonts_install.py")
fonts_install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fonts_install)

SHA512_RE = re.compile(r"^sha512-[A-Za-z0-9+/]{86}={0,2}$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$")
FREE_LICENCES = {"OFL-1.1", "Apache-2.0", "UFL-1.0"}


def test_lock_shape_and_integrity():
    assert isinstance(LOCK, dict) and LOCK, "lock must be a non-empty object"
    for key, spec in LOCK.items():
        assert key.startswith("@expo-google-fonts/"), key
        assert set(spec) == {"integrity", "version"}, key
        assert SHA512_RE.match(spec["integrity"]), key
        assert len(base64.b64decode(spec["integrity"][len("sha512-"):])) == 64, key
        assert SEMVER_RE.match(spec["version"]), key


def test_lock_covers_managed_and_published_alansari():
    managed = {f"@expo-google-fonts/{spec['npm']}" for spec in fonts_install.FAMILIES}
    assert managed <= set(LOCK), "every managed family must be pinned"
    alansari = set(MANIFEST) - {spec["family"] for spec in fonts_install.FAMILIES}
    for name in sorted(alansari):
        slug = fonts_install._slugify(name)
        if slug in fonts_install.LOCK_EXCEPTIONS:
            continue
        assert f"@expo-google-fonts/{slug}" in LOCK, f"{name} unpinned"


def test_lock_exceptions_are_real_and_unpinned():
    manifest_slugs = {fonts_install._slugify(n) for n in MANIFEST}
    for slug in fonts_install.LOCK_EXCEPTIONS:
        assert slug in manifest_slugs, f"exception {slug} matches no family"
        assert f"@expo-google-fonts/{slug}" not in LOCK, f"exception {slug} is pinned"
    assert len(fonts_install.LOCK_EXCEPTIONS) == 4


def test_exceptions_carry_declared_free_licences_and_files():
    by_slug = {fonts_install._slugify(n): n for n in MANIFEST}
    for slug in fonts_install.LOCK_EXCEPTIONS:
        family = by_slug[slug]
        meta = MANIFEST[family]
        assert meta["licence"] in FREE_LICENCES, family
        licence_file = ROOT / "assets" / "fonts" / meta["licence_file"]
        assert licence_file.is_file() and licence_file.stat().st_size > 0, family


def test_every_locked_alansari_family_declares_a_free_licence():
    managed = {spec["family"] for spec in fonts_install.FAMILIES}
    for name, meta in MANIFEST.items():
        if name in managed:
            continue
        slug = fonts_install._slugify(name)
        if slug in fonts_install.LOCK_EXCEPTIONS:
            continue
        assert f"@expo-google-fonts/{slug}" in LOCK
        assert meta["licence"] in FREE_LICENCES, name


def test_verify_lock_passes_on_the_repo_state():
    assert fonts_install.verify_lock() == []


def test_unlock_drift_is_caught(tmp_path, monkeypatch):
    """A family whose pin disappears must be reported, not silently tolerated."""
    original = dict(LOCK)
    monkeypatch.setattr(fonts_install, "LOCK", tmp_path / "lock.json")
    (tmp_path / "lock.json").write_text(json.dumps(
        {k: v for k, v in original.items() if k != "@expo-google-fonts/baloo-bhaijaan-2"}),
        encoding="utf-8")
    problems = fonts_install.verify_lock()
    assert any("baloo-bhaijaan-2" in p for p in problems)
