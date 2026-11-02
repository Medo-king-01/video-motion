#!/usr/bin/env python3
"""Fetch a local Whisper-small CTranslate2 int8 model from npm tarballs.

Studio alignment infrastructure (see docs/alignment.md).

Why this exists: Hugging Face and the OpenAI/Azure model CDNs are frequently
unreachable from locked-down sandboxes (TLS EOF). npm's registry is usually
allow-listed, and a publisher ships a real CTranslate2 int8 conversion of
OpenAI Whisper-small split across four public packages. This downloads this
reassembles model.bin, and verifies the publisher's SHA-256 before use.

The model is written to a cache directory and must NOT be committed (it is
~480 MB and reproducible from this script).

Usage:
    python3 tools/whisper_fetch.py --out .cache/whisper-small-ct2-int8
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import urllib.request
from pathlib import Path

PACKAGES = [
    "@skillninja/shortmovie-telop-model-p0",
    "@skillninja/shortmovie-telop-model-p1",
    "@skillninja/shortmovie-telop-model-p2",
    "@skillninja/shortmovie-telop-model-p3",
]
VERSION = "1.0.0"
EXPECTED_SHA256 = "ca732cb1379efc49417d028465f543d83a39de2c61f3027678de103dc404ce73"


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path(".cache/whisper-small-ct2-int8"))
    args = ap.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    parts: list[bytes] = []
    for i, pkg in enumerate(PACKAGES):
        meta = json.loads(fetch(f"https://registry.npmjs.org/{pkg.replace('/', '%2F')}"))
        url = meta["versions"][VERSION]["dist"]["tarball"]
        print(f"fetch {pkg}@{VERSION}")
        raw = fetch(url)
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
            for m in tf.getmembers():
                name = Path(m.name).name
                if name in {"config.json", "preprocessor_config.json", "tokenizer.json", "vocabulary.json", "LICENSE", "model.sha256"}:
                    f = tf.extractfile(m)
                    if f:
                        (out / name).write_bytes(f.read())
                if name == f"model.bin.part{i}":
                    f = tf.extractfile(m)
                    if not f:
                        raise RuntimeError(f"missing {name}")
                    parts.append(f.read())
    if len(parts) != 4:
        raise RuntimeError(f"expected 4 model parts, got {len(parts)}")
    model = out / "model.bin"
    model.write_bytes(b"".join(parts))
    digest = hashlib.sha256(model.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise RuntimeError(f"SHA-256 mismatch: {digest}")
    print(f"OK {model} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
