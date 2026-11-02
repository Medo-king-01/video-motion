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
