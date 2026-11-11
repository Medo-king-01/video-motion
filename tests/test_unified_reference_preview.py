"""End-to-end reference preview: validated project -> graph -> RGBA frame."""
import copy
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from unified_reference_preview import PreviewError, render_frame  # noqa: E402


def image_project(tmp_path):
    p = json.loads((ROOT / "tests/fixtures/unified_project/basic.json").read_text(encoding="utf-8"))
    p["profile"].update(width=2, height=1)
    p["duration"] = 24000
    data = b"P6\n2 1\n255\n" + bytes([255, 0, 0, 0, 128, 255])
    (tmp_path / "image.ppm").write_bytes(data)
    p["assets"][0] = {"id": "a1", "kind": "image", "uri": "image.ppm",
                      "sha256": hashlib.sha256(data).hexdigest()}
    p["tracks"][0]["clips"][0].update(start=8000, duration=8000)
    return p


def test_image_preview_gap_boundaries_and_determinism(tmp_path):
    p = image_project(tmp_path)
    before = copy.deepcopy(p)
    assert render_frame(p, tmp_path, 0)["pixels"] == b"\x00" * 8
    frame = render_frame(p, tmp_path, 1)
    assert frame == {"width": 2, "height": 1, "frameIndex": 1, "tick": 8000, "format": "RGBA8",
                     "pixels": bytes([255, 0, 0, 255, 0, 128, 255, 255])}
    assert render_frame(p, tmp_path, 1) == frame
    assert render_frame(p, tmp_path, 2)["pixels"] == b"\x00" * 8
    assert p == before
    for invalid in (-1, 3, True, 1.0):
        with pytest.raises(PreviewError, match="V01"):
            render_frame(p, tmp_path, invalid)


def test_inactive_assets_are_verified_and_track_disable(tmp_path):
    p = image_project(tmp_path)
    (tmp_path / "image.ppm").write_bytes(b"changed")
    with pytest.raises(PreviewError, match="V03"):
        render_frame(p, tmp_path, 0)
    p["tracks"][0]["enabled"] = False
    assert render_frame(p, tmp_path, 1)["pixels"] == b"\0" * 8


def test_reject_bad_images_even_with_matching_hash(tmp_path):
    p = image_project(tmp_path)
    for data in (b"P6\n1 1\n255\n\0\0\0", b"P6\n2 1\n255\n" + b"\0" * 7):
        (tmp_path / "image.ppm").write_bytes(data)
        p["assets"][0]["sha256"] = hashlib.sha256(data).hexdigest()
        with pytest.raises(PreviewError, match="V0[34]"):
            render_frame(p, tmp_path, 1)


def test_reject_unsupported_content_even_outside_frame(tmp_path):
    p = image_project(tmp_path)
    clip = p["tracks"][0]["clips"][0]
    p["schemaVersion"] = "1.1"
    clip["effects"] = [{"id": "fx", "type": "opacity", "version": 1,
                        "enabled": False, "params": {"value": 5000}}]
    with pytest.raises(PreviewError, match="effects"):
        render_frame(p, tmp_path, 0)
    clip["effects"] = []
    p["tracks"].append({"id": "v2", "kind": "video", "enabled": True, "clips": []})
    with pytest.raises(PreviewError, match="multiple"):
        render_frame(p, tmp_path, 0)
    p["tracks"].pop()
    p["assets"].append({"id": "audio", "kind": "audio", "uri": "a.wav", "sha256": "0" * 64,
                        "duration": 24000})
    p["tracks"].append({"id": "a", "kind": "audio", "enabled": True, "clips": [
        {"id": "ac", "kind": "media", "assetId": "audio", "start": 8000, "duration": 8000,
         "sourceIn": 0, "effects": [], "keyframes": []}]})
    with pytest.raises(PreviewError, match="only video-track"):
        render_frame(p, tmp_path, 0)


def test_reject_pixel_limit_and_non_image(tmp_path):
    p = image_project(tmp_path)
    p["profile"].update(width=10000, height=10000)
    with pytest.raises(PreviewError, match="pixel limit"):
        render_frame(p, tmp_path, 0)
    p = image_project(tmp_path)
    p["assets"][0].update(kind="video", duration=24000)
    with pytest.raises(PreviewError, match="still images"):
        render_frame(p, tmp_path, 0)


def test_symlink_is_rejected(tmp_path):
    p = image_project(tmp_path)
    target = tmp_path / "image.ppm"
    target.rename(tmp_path / "real.ppm")
    try:
        target.symlink_to("real.ppm")
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(PreviewError, match="V03"):
        render_frame(p, tmp_path, 1)
