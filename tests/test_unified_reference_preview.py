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
                     "pixels": bytes([255, 0, 0, 255, 0, 128, 255, 255]), "texts": 0}
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
    # Opacity is drawable now, so the disabled effect simply does nothing.
    assert render_frame(p, tmp_path, 1)["pixels"] == bytes([255, 0, 0, 255, 0, 128, 255, 255])
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
    # audio is not pixels: the frame is identical with or without the audio track
    assert render_frame(p, tmp_path, 1)["pixels"] == bytes([255, 0, 0, 255, 0, 128, 255, 255])
    p["tracks"][-1]["kind"] = "graphics"
    p["tracks"][-1]["clips"] = []
    with pytest.raises(PreviewError, match="only video and text"):
        render_frame(p, tmp_path, 1)


def test_reject_pixel_limit_and_non_image(tmp_path):
    p = image_project(tmp_path)
    p["profile"].update(width=10000, height=10000)
    with pytest.raises(PreviewError, match="pixel limit"):
        render_frame(p, tmp_path, 0)
    p = image_project(tmp_path)
    junk = b"not a video at all" * 64
    (tmp_path / "image.ppm").write_bytes(junk)
    p["assets"][0].update(kind="video", duration=24000, sha256=hashlib.sha256(junk).hexdigest())
    with pytest.raises(PreviewError, match="V08"):
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


# ---------------------------------------------------------------- video: VFR and colour
def _tagged_video(path: Path, frames: list[tuple[int, int]], *, colorspace: int,
                  color_range: int = 1, width: int = 64, height: int = 64, rate: int = 10) -> bytes:
    """A lossless clip whose frames are solid colours at explicit timestamps (VFR when gaps differ)."""
    import av
    import numpy as np

    with av.open(str(path), "w") as container:
        stream = container.add_stream("ffv1", rate=rate)
        stream.width, stream.height, stream.pix_fmt = width, height, "yuv420p"
        stream.codec_context.colorspace = colorspace
        stream.codec_context.color_range = color_range
        for pts, luma in frames:
            frame = av.VideoFrame(width, height, "yuv420p")
            frame.planes[0].update(np.full((height, width), luma, dtype=np.uint8).tobytes())
            frame.planes[1].update(np.full((height // 2, width // 2), 128, dtype=np.uint8).tobytes())
            frame.planes[2].update(np.full((height // 2, width // 2), 128, dtype=np.uint8).tobytes())
            frame.pts = pts
            for packet in stream.encode(frame):
                container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return path.read_bytes()


def video_project(tmp_path: Path, payload: bytes, *, duration: int = 480_000, size=(8, 4)) -> dict:
    p = image_project(tmp_path)
    p["profile"].update(width=size[0], height=size[1])
    p["duration"] = duration
    (tmp_path / "clip.mkv").write_bytes(payload)
    p["assets"] = [{"id": "a1", "kind": "video", "uri": "clip.mkv", "duration": duration,
                    "sha256": hashlib.sha256(payload).hexdigest()}]
    clip = p["tracks"][0]["clips"][0]
    clip.update(start=0, duration=duration, sourceIn=0)
    return p


def luma_to_grey(value: int) -> bytes:
    """Limited-range luma with neutral chroma becomes a grey level; this is the expected maths."""
    level = round((value - 16) * 255 / 219)
    return bytes([level, level, level])


def test_a_vfr_clip_shows_the_frame_that_covers_the_instant(tmp_path):
    """Frames sit at 0 s, 0.1 s and 0.5 s: a tick inside a gap must show the frame that covers it."""
    payload = _tagged_video(tmp_path / "clip.mkv", [(0, 40), (1, 120), (5, 200)], colorspace=5)
    p = video_project(tmp_path, payload)
    frames_per_second = 30  # the project's frame rate decides what a frame index means

    def at(seconds):
        index = int(round(seconds * frames_per_second))
        return render_frame(p, tmp_path, index)["pixels"][:3]

    assert at(0.0) == luma_to_grey(40)
    assert at(0.1) == luma_to_grey(120), "0.1 s is frame 1"
    assert at(0.3) == luma_to_grey(120), "frame 1 holds until the next timestamp (0.5 s)"
    assert at(0.4) == luma_to_grey(120), "a CFR reading would have invented a frame here"
    assert at(0.5) == luma_to_grey(200), "0.5 s is frame 2"
    assert at(0.9) == luma_to_grey(200), "past the last timestamp the last frame holds"


def test_a_neutral_grey_is_the_same_under_both_matrices(tmp_path):
    """Grey has no chroma, so the matrix cannot matter — the difference is tested with chroma below."""
    tagged = {}
    for name, space in (("bt601", 5), ("bt709", 1)):
        payload = _tagged_video(tmp_path / f"{name}.mkv", [(0, 100)], colorspace=space)
        p = video_project(tmp_path, payload)
        tagged[name] = render_frame(p, tmp_path, 0)["pixels"][:3]
    assert tagged["bt601"] == tagged["bt709"] == luma_to_grey(100)


def test_chroma_is_converted_with_the_declared_matrix(tmp_path):
    """A saturated blue chroma plane converts differently under 601 and 709 — the tag is honoured."""
    import av
    import numpy as np

    results = {}
    for name, space in (("bt601", 5), ("bt709", 1)):
        path = tmp_path / f"{name}-chroma.mkv"
        with av.open(str(path), "w") as container:
            stream = container.add_stream("ffv1", rate=10)
            stream.width, stream.height, stream.pix_fmt = 64, 64, "yuv420p"
            stream.codec_context.colorspace = space
            stream.codec_context.color_range = 1
            frame = av.VideoFrame(64, 64, "yuv420p")
            frame.planes[0].update(np.full((64, 64), 120, dtype=np.uint8).tobytes())
            frame.planes[1].update(np.full((32, 32), 200, dtype=np.uint8).tobytes())
            frame.planes[2].update(np.full((32, 32), 60, dtype=np.uint8).tobytes())
            for packet in stream.encode(frame):
                container.mux(packet)
            for packet in stream.encode():
                container.mux(packet)
        payload = path.read_bytes()
        p = video_project(tmp_path, payload)
        results[name] = render_frame(p, tmp_path, 0)["pixels"][:3]
    assert results["bt601"] != results["bt709"], results
    red_601, green_601, blue_601 = results["bt601"]
    assert blue_601 > 200 and red_601 < 100, "blue chroma must land in blue, not in red"


def test_an_hdr_source_is_refused_with_v09(tmp_path):
    payload = _tagged_video(tmp_path / "hdr.mkv", [(0, 100)], colorspace=9, color_range=2)
    p = video_project(tmp_path, payload)
    with pytest.raises(PreviewError) as error:
        render_frame(p, tmp_path, 0)
    assert error.value.code == "V09"
    assert "bt2020" in error.value.message


def test_a_still_with_a_non_srgb_profile_is_refused(tmp_path):
    from PIL import Image

    p = image_project(tmp_path)
    image = Image.new("RGB", (2, 1), (255, 0, 0))
    buffer = tmp_path / "tagged.png"
    image.save(buffer, format="PNG", icc_profile=b"Adobe RGB (1998) profile data")
    payload = buffer.read_bytes()
    (tmp_path / "image.ppm").unlink()
    p["assets"][0].update(uri="tagged.png", kind="image", sha256=hashlib.sha256(payload).hexdigest())
    with pytest.raises(PreviewError) as error:
        render_frame(p, tmp_path, 1)
    assert error.value.code == "V10"
