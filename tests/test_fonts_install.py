"""fonts_install must never extract an archive member outside the target directory."""
from __future__ import annotations

import importlib.util
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fonts_install", ROOT / "tools" / "fonts_install.py")
fonts_install = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fonts_install)


def _tar_with(tmp_path: Path, members: dict) -> Path:
    tgz = tmp_path / "evil.tgz"
    with tarfile.open(tgz, "w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            if data is None:  # symlink
                info.type = tarfile.SYMTYPE
                info.linkname = members[name] if isinstance(members[name], str) else ""
                tar.addfile(info)
            else:
                info.size = len(data)
                tar.addfile(info, __import__("io").BytesIO(data))
    return tgz


def test_safe_extract_rejects_parent_traversal(tmp_path):
    tgz = _tar_with(tmp_path, {"package/ok.txt": b"fine", "../evil.txt": b"bad"})
    with tarfile.open(tgz) as tar:
        with pytest.raises(SystemExit):
            fonts_install._safe_extract(tar, tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_safe_extract_rejects_absolute_paths(tmp_path):
    tgz = _tar_with(tmp_path, {"/tmp/evil-abs.txt": b"bad"})
    with tarfile.open(tgz) as tar:
        with pytest.raises(SystemExit):
            fonts_install._safe_extract(tar, tmp_path / "out")


def test_safe_extract_rejects_escaping_symlink(tmp_path):
    tgz = tmp_path / "link.tgz"
    with tarfile.open(tgz, "w:gz") as tar:
        info = tarfile.TarInfo("package/link")
        info.type = tarfile.SYMTYPE
        info.linkname = "../../outside"
        tar.addfile(info)
    with tarfile.open(tgz) as tar:
        with pytest.raises(SystemExit):
            fonts_install._safe_extract(tar, tmp_path / "out")


def test_safe_extract_accepts_a_clean_package(tmp_path):
    tgz = _tar_with(tmp_path, {"package/package.json": b"{}", "package/font.ttf": b"ttf"})
    out = tmp_path / "out"
    with tarfile.open(tgz) as tar:
        fonts_install._safe_extract(tar, out)
    assert (out / "package" / "package.json").is_file()


def test_pack_rejects_bad_checksum_before_extract(tmp_path, monkeypatch):
    import json
    root = tmp_path / 'root'
    (root / 'tools').mkdir(parents=True)
    (root / 'tools' / 'font-packages.lock.json').write_text(json.dumps({
        '@expo-google-fonts/inter': {'version': '1.2.3', 'integrity': 'sha512-wrong'}}))
    cache = tmp_path / 'cache'
    cache.mkdir()
    (cache / 'inter-1.2.3.tgz').write_bytes(b'not a tarball')
    monkeypatch.setattr(fonts_install, 'ROOT', root)
    monkeypatch.setattr(fonts_install, 'LOCK', root / 'tools' / 'font-packages.lock.json')
    with pytest.raises(SystemExit, match='checksum mismatch'):
        fonts_install.pack('inter', cache)
    assert not (cache / 'inter-1.2.3').exists()


def test_pack_uses_pinned_version_and_validates_integrity(tmp_path, monkeypatch):
    import base64
    import hashlib
    import json
    import types
    tgz = _tar_with(tmp_path, {'package/package.json': b'{}', 'package/font.ttf': b'font'})
    data = tgz.read_bytes()
    integrity = 'sha512-' + base64.b64encode(hashlib.sha512(data).digest()).decode()
    root = tmp_path / 'root'
    (root / 'tools').mkdir(parents=True)
    (root / 'tools' / 'font-packages.lock.json').write_text(json.dumps({
        '@expo-google-fonts/inter': {'version': '1.2.3', 'integrity': integrity}}))
    monkeypatch.setattr(fonts_install, 'ROOT', root)
    monkeypatch.setattr(fonts_install, 'LOCK', root / 'tools' / 'font-packages.lock.json')
    cache = tmp_path / 'cache'
    def run(command, **kwargs):
        assert '@expo-google-fonts/inter@1.2.3' in command
        (cache / 'expo-google-fonts-inter-1.2.3.tgz').write_bytes(data)
        return types.SimpleNamespace(returncode=0)
    monkeypatch.setattr(fonts_install.subprocess, 'run', run)
    out = fonts_install.pack('inter', cache)
    assert (out / 'font.ttf').read_bytes() == b'font'
    assert out.parent.name == 'inter-1.2.3'


def test_font_lock_covers_exact_expected_families():
    import json
    lock = json.loads((ROOT / 'tools' / 'font-packages.lock.json').read_text())
    managed = {f"@expo-google-fonts/{spec['npm']}" for spec in fonts_install.FAMILIES}
    assert managed <= set(lock), "every managed family must be pinned in the lock"
    exceptions = {f"@expo-google-fonts/{slug}" for slug in fonts_install.LOCK_EXCEPTIONS}
    assert not (exceptions & set(lock)), "documented exceptions must not be pinned"
    # lock = managed + every Alansari family @expo-google-fonts publishes
    manifest = json.loads((ROOT / 'assets' / 'fonts' / 'fonts.json').read_text(encoding='utf-8'))['families']
    alansari = set(manifest) - {spec['family'] for spec in fonts_install.FAMILIES}
    published = {f"@expo-google-fonts/{fonts_install._slugify(name)}" for name in alansari} - exceptions
    assert set(lock) == managed | published
    assert all(item['version'] and item['integrity'].startswith('sha512-') for item in lock.values())
