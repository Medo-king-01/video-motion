from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import cover_generator as covers  # noqa: E402


def test_style_profiles_use_registered_font_families():
    registry = json.loads((ROOT / "assets/fonts/fonts.json").read_text(encoding="utf-8"))["families"]
    for style in covers.STYLES.values():
        assert style["font_ar"] in registry
        assert style["font_latin"] in registry


@pytest.mark.parametrize(("size", "expected"), [((1080, 1920), (1080, 1920)), ((1280, 720), (1280, 720))])
def test_render_outputs_exact_dimensions(size, expected):
    result = covers.render_artwork(size=size, title="A practical AI workflow")
    assert result.size == expected
    assert result.mode == "RGB"


def test_arabic_and_mixed_latin_title_renders():
    result = covers.render_artwork(size=(1080, 1920), title="جرّب Claude Code النهاردة",
                                   subtitle="شرح عملي للمطورين", eyebrow="فكرة تقنية")
    assert result.size == (1080, 1920)


def test_optional_pose_is_kept_inside_canvas():
    pose = Image.new("RGBA", (400, 1200), (203, 39, 27, 180))
    result = covers.render_artwork(size=(1080, 1920), title="شرح الأداة", pose=pose)
    assert result.size == (1080, 1920)
    assert result.getpixel((900, 1700))[0] > 60


def test_title_is_required_and_style_is_valid():
    with pytest.raises(ValueError, match="title"):
        covers.render_artwork(size=(1080, 1920), title=" ")
    with pytest.raises(ValueError, match="style"):
        covers.render_artwork(size=(1080, 1920), title="Title", style_name="unknown")


def test_pose_manifest_resolves_known_slug_and_rejects_unknown():
    pose = covers._pose_image("neutral", None)
    assert pose is not None and pose.mode == "RGBA"
    with pytest.raises(ValueError, match="Unknown pose"):
        covers._pose_image("not-a-pose", None)


def test_existing_output_symlink_is_rejected(tmp_path):
    target = tmp_path / "real.png"
    target.write_bytes(b"not an image")
    link = tmp_path / "cover-9x16.png"
    try:
        link.symlink_to(target)
    except (NotImplementedError, OSError):
        pytest.skip("Symlink creation is not available on this platform")
    with pytest.raises(ValueError, match="symlink output file"):
        covers._reject_output_symlinks((link,))


def test_source_frame_cover_crop_is_exact():
    source = Image.new("RGB", (1920, 1080), (20, 30, 40))
    result = covers._cover_crop(source, (1080, 1920))
    assert result.size == (1080, 1920)
