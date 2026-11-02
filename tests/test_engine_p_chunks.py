from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


def test_expected_chunks_are_exact_ordered_half_open_ranges():
    from chunk_utils import expected_chunks

    assert expected_chunks(10, 4) == [(0, 4), (4, 8), (8, 10)]
    assert expected_chunks(0, 4) == []


@pytest.mark.parametrize(
    "total, chunk",
    [(-1, 4), (10, 0), (10, -2)],
)
def test_expected_chunks_reject_invalid_ranges(total, chunk):
    from chunk_utils import expected_chunks

    with pytest.raises(ValueError):
        expected_chunks(total, chunk)


def test_signature_changes_when_python_renderer_changes(tmp_path):
    from chunk_utils import build_signature

    source = tmp_path / "source"
    assets = tmp_path / "assets"
    source.mkdir()
    assets.mkdir()
    code = source / "render.py"
    code.write_text("VALUE = 1\n", encoding="utf-8")
    args = (source, assets, 120, 30, [0, 4], 30, 1080, 1920)
    first = build_signature(*args)
    code.write_text("VALUE = 2\n", encoding="utf-8")
    assert build_signature(*args) != first


def test_signature_hashes_asset_contents_not_only_file_size(tmp_path):
    from chunk_utils import build_signature

    source = tmp_path / "source"
    assets = tmp_path / "assets"
    source.mkdir()
    assets.mkdir()
    (source / "render.py").write_text("pass\n", encoding="utf-8")
    asset = assets / "same-size.png"
    asset.write_bytes(b"AAAA")
    args = (source, assets, 120, 30, [0, 4], 30, 1080, 1920)
    first = build_signature(*args)
    asset.write_bytes(b"BBBB")
    assert asset.stat().st_size == 4
    assert build_signature(*args) != first


def test_signature_includes_nested_pose_assets_and_font_manifest(tmp_path):
    from chunk_utils import build_signature

    source = tmp_path / "source"
    assets = tmp_path / "assets"
    (assets / "poses").mkdir(parents=True)
    source.mkdir()
    (source / "render.py").write_text("pass\n", encoding="utf-8")
    pose = assets / "poses" / "poses.json"
    pose.write_text('{"pose":"neutral"}', encoding="utf-8")
    args = (source, assets, 120, 30, [0, 4], 30, 1080, 1920)
    first = build_signature(*args)
    pose.write_text('{"pose":"wave"}', encoding="utf-8")
    assert build_signature(*args) != first


def _fake_av_module(width=1080, height=1920, frames=4):
    class Frame:
        def __init__(self):
            self.width = width
            self.height = height

    class Stream:
        type = "video"
        codec_context = SimpleNamespace(width=width, height=height)

    class Container:
        streams = [Stream()]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def decode(self, stream):
            return iter(Frame() for _ in range(frames))

    return SimpleNamespace(open=lambda path: Container())


def test_chunk_validator_requires_exact_dimensions_and_decoded_frame_count(tmp_path, monkeypatch):
    from chunk_utils import is_valid_chunk

    video = tmp_path / "chunk.mp4"
    video.write_bytes(b"non-empty fixture")
    monkeypatch.setitem(sys.modules, "av", _fake_av_module())
    assert is_valid_chunk(video, 4, 1080, 1920)
    assert not is_valid_chunk(video, 5, 1080, 1920)
    assert not is_valid_chunk(video, 4, 720, 1280)


def test_chunk_validator_rejects_decode_errors_and_wrong_frame_dimensions(tmp_path, monkeypatch):
    from chunk_utils import is_valid_chunk

    video = tmp_path / "chunk.mp4"
    video.write_bytes(b"non-empty fixture")

    class BrokenContainer:
        streams = [SimpleNamespace(type="video", codec_context=SimpleNamespace(width=1080, height=1920))]

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def decode(self, stream):
            raise RuntimeError("decode failed")

    monkeypatch.setitem(sys.modules, "av", SimpleNamespace(open=lambda path: BrokenContainer()))
    assert not is_valid_chunk(video, 4, 1080, 1920)

    monkeypatch.setitem(sys.modules, "av", _fake_av_module(width=720, height=1280))
    assert not is_valid_chunk(video, 4, 1080, 1920)


def test_chunk_validator_rejects_missing_and_empty_files(tmp_path):
    from chunk_utils import is_valid_chunk

    assert not is_valid_chunk(tmp_path / "missing.mp4", 4, 1080, 1920)
    empty = tmp_path / "empty.mp4"
    empty.touch()
    assert not is_valid_chunk(empty, 4, 1080, 1920)

def test_signature_changes_when_presenter_fallback_pose_changes(tmp_path):
    from chunk_utils import build_signature

    source = tmp_path / "source"
    project_assets = tmp_path / "project-assets"
    fallback = tmp_path / "studio-assets" / "poses"
    source.mkdir()
    project_assets.mkdir()
    fallback.mkdir(parents=True)
    (source / "render.py").write_text("pass\n", encoding="utf-8")
    pose = fallback / "neutral.png"
    pose.write_bytes(b"POSE-A")
    args = (source, project_assets, 120, 30, [0, 4], 30, 1080, 1920)
    first = build_signature(*args, fallback_assets_dir=fallback)
    pose.write_bytes(b"POSE-B")
    assert build_signature(*args, fallback_assets_dir=fallback) != first


def test_chunk_validator_decodes_a_real_mp4_with_pyav(tmp_path):
    av = pytest.importorskip("av")
    np = pytest.importorskip("numpy")
    from chunk_utils import is_valid_chunk

    video = tmp_path / "real.mp4"
    with av.open(str(video), mode="w") as output:
        stream = output.add_stream("mpeg4", rate=30)
        stream.width = 16
        stream.height = 16
        stream.pix_fmt = "yuv420p"
        for _ in range(3):
            frame = av.VideoFrame.from_ndarray(
                np.zeros((16, 16, 3), dtype=np.uint8), format="rgb24"
            )
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)

    assert is_valid_chunk(video, 3, 16, 16)
    assert not is_valid_chunk(video, 4, 16, 16)
