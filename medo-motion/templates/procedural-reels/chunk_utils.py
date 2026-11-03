"""Shared integrity helpers for restartable engine-P chunk rendering."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

_ASSET_SUFFIXES = {".png", ".ttf", ".otf", ".json"}


def expected_chunks(total_frames: int, chunk_frames: int) -> list[tuple[int, int]]:
    """Return the exact ordered half-open frame ranges for one render."""
    if total_frames < 0:
        raise ValueError("total_frames must be non-negative")
    if chunk_frames <= 0:
        raise ValueError("chunk_frames must be positive")
    return [
        (start, min(start + chunk_frames, total_frames))
        for start in range(0, total_frames, chunk_frames)
    ]


def _hash_file(hasher, path: Path, relative_name: str) -> None:
    hasher.update(relative_name.replace(os.sep, "/").encode("utf-8"))
    hasher.update(b"\\0")
    hasher.update(str(path.stat().st_size).encode("ascii"))
    hasher.update(b"\\0")
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    hasher.update(b"\\0")


def build_signature(
    source_dir: str | os.PathLike,
    assets_dir: str | os.PathLike,
    total_frames: int,
    chunk_frames: int,
    scene_bounds,
    fps: int,
    width: int,
    height: int,
    font_override: str | None = None,
    fallback_assets_dir: str | os.PathLike | None = None,
    motion_mode: str = "normal",
) -> str:
    """Hash render code, visual assets by content, and all frame/timing settings."""
    source_root = Path(source_dir)
    assets_root = Path(assets_dir)
    hasher = hashlib.sha256()
    if motion_mode not in ("normal", "reduced"):
        raise ValueError("invalid motion mode")
    hasher.update(b"engine-p-cache-v3\\0")
    hasher.update(motion_mode.encode("ascii"))
    hasher.update(b"\\0")
    hasher.update(
        repr((total_frames, chunk_frames, tuple(scene_bounds), fps, width, height)).encode("utf-8")
    )
    hasher.update(b"\\0")

    source_files = sorted(
        (path for path in source_root.iterdir() if path.is_file() and path.suffix.lower() == ".py"),
        key=lambda path: path.name,
    )
    for path in source_files:
        _hash_file(hasher, path, f"code/{path.name}")

    if assets_root.is_dir():
        asset_files = []
        for root, dirs, files in os.walk(assets_root):
            dirs.sort()
            for filename in sorted(files):
                path = Path(root) / filename
                if path.suffix.lower() in _ASSET_SUFFIXES and path.is_file():
                    asset_files.append(path)
        for path in asset_files:
            _hash_file(hasher, path, f"assets/{path.relative_to(assets_root).as_posix()}")

    # presenter.py also searches the studio-level assets/poses directory when a
    # project does not contain a requested pose. Hash that fallback source too:
    # otherwise changing a fallback PNG or manifest could leave stale chunks reusable.
    if fallback_assets_dir is not None:
        fallback_root = Path(fallback_assets_dir)
        if fallback_root.is_dir():
            fallback_files = []
            for root, dirs, files in os.walk(fallback_root):
                dirs.sort()
                for filename in sorted(files):
                    path = Path(root) / filename
                    if path.suffix.lower() in _ASSET_SUFFIXES and path.is_file():
                        fallback_files.append(path)
            for path in fallback_files:
                _hash_file(
                    hasher,
                    path,
                    f"fallback-assets/{path.relative_to(fallback_root).as_posix()}",
                )

    override = (font_override or "").strip()
    hasher.update(b"REEL_FONT\\0")
    hasher.update(override.encode("utf-8"))
    hasher.update(b"\\0")
    if override:
        font_path = Path(override).expanduser()
        if font_path.is_file():
            _hash_file(hasher, font_path, "external-font")
        else:
            hasher.update(b"missing-external-font\\0")

    return hasher.hexdigest()


def is_valid_chunk(
    path: str | os.PathLike,
    expected_frames: int,
    width: int,
    height: int,
) -> bool:
    """Accept only a video that PyAV can fully decode at the expected size and frame count."""
    chunk_path = Path(path)
    try:
        if expected_frames <= 0 or not chunk_path.is_file() or chunk_path.stat().st_size <= 0:
            return False
        import av  # noqa: PLC0415 - required by the studio setup and ffprobe shim

        with av.open(str(chunk_path)) as container:
            streams = [stream for stream in container.streams if stream.type == "video"]
            if len(streams) != 1:
                return False
            stream = streams[0]
            if stream.codec_context.width != width or stream.codec_context.height != height:
                return False
            decoded_frames = 0
            for frame in container.decode(stream):
                if frame.width != width or frame.height != height:
                    return False
                decoded_frames += 1
                if decoded_frames > expected_frames:
                    return False
            return decoded_frames == expected_frames
    except Exception:
        return False
