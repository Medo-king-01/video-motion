#!/usr/bin/env python3
"""ffprobe-compatible shim (subset) built on PyAV.

Why: FFmpeg static builds often ship `ffmpeg` only, without a matching
`ffprobe` binary. The skill's helpers call a small, predictable subset of
ffprobe, so this shim answers exactly that subset and returns ffprobe-shaped
JSON.

Supported:
  ffprobe [-v error] [-select_streams a:0|v:0] [-show_streams] [-show_format]
          [-show_entries format=duration,bit_rate:stream=codec_name,channels,sample_rate]
          [-of|-print_format json] FILE

Read-only. Never writes, never calls the network.
"""
from __future__ import annotations

import json
import os
import sys


def _parse_entries(spec: str):
    """'format=duration,bit_rate:stream=codec_name,channels' -> {'format': {...}}"""
    out = {}
    for part in spec.split(':'):
        part = part.strip()
        if '=' not in part:
            continue
        section, keys = part.split('=', 1)
        section = section.strip()
        keys = {k.strip() for k in keys.split(',') if k.strip()}
        if keys:
            out.setdefault(section, set()).update(keys)
        else:
            out.setdefault(section, set())
    return out


def _filter(obj: dict, keys) -> dict:
    if not keys:
        return obj
    return {k: v for k, v in obj.items() if k in keys}


def main(argv):
    args = argv[1:]
    show_streams = '-show_streams' in args
    show_format = '-show_format' in args
    want = {}
    select = None
    path = None
    i = 0
    while i < len(args):
        a = args[i]
        if a in ('-v', '-loglevel'):
            i += 2
            continue
        if a == '-select_streams':
            select = args[i + 1]
            i += 2
            continue
        if a in ('-show_entries',):
            want = _parse_entries(args[i + 1])
            i += 2
            continue
        if a in ('-of', '-print_format'):
            i += 2
            continue
        if a.startswith('-'):
            i += 1
            continue
        path = a
        i += 1

    if not path or not os.path.exists(path):
        sys.stderr.write(f'ffprobe shim: file not found: {path}\n')
        return 1

    try:
        import av
        container = av.open(path)
    except Exception as e:                                        # pragma: no cover
        sys.stderr.write(f'ffprobe shim: cannot open {path}: {e}\n')
        return 1

    streams = []
    for idx, s in enumerate(container.streams):
        cc = s.codec_context
        d = {
            'index': idx,
            'codec_name': cc.name,
            'codec_type': s.type,
            'codec_long_name': cc.name,
            'profile': str(getattr(cc, 'profile', '') or ''),
        }
        for key in ('width', 'height', 'channels', 'sample_rate', 'bit_rate',
                    'sample_aspect_ratio', 'display_aspect_ratio', 'pix_fmt'):
            try:
                v = getattr(cc, key, None)
                if v is not None:
                    d[key] = str(v) if key in ('sample_aspect_ratio', 'display_aspect_ratio', 'pix_fmt') else int(v)
            except Exception:
                pass
        try:
            if s.type == 'video' and s.average_rate:
                d['r_frame_rate'] = f'{s.average_rate.numerator}/{s.average_rate.denominator}'
                d['avg_frame_rate'] = d['r_frame_rate']
        except Exception:
            pass
        try:
            if s.duration is not None:
                # A stream's duration is in the *stream's own* time base (1/48000 for a WAV,
                # 1/15360 for typical H.264). Dividing by 1e6 — the code's old assumption —
                # reported 0.384 s for an 8 s file and silently broke every length check.
                d['duration'] = f'{float(s.duration) * float(s.time_base):.6f}'
        except Exception:
            pass
        try:
            if s.frames:
                d['nb_frames'] = str(s.frames)
        except Exception:
            pass
        streams.append(d)

    sel_type, sel_idx = None, 0
    if select:
        bits = select.split(':')
        sel_type = {'a': 'audio', 'v': 'video', 's': 'subtitle', 'd': 'data'}.get(bits[0][:1], bits[0])
        try:
            sel_idx = int(bits[1]) if len(bits) > 1 else 0
        except ValueError:
            sel_idx = 0
        streams = [s for s in streams if s['codec_type'] == sel_type]
        streams = streams[sel_idx:sel_idx + 1]

    fmt = {
        'filename': path,
        'nb_streams': len(container.streams),
        'format_name': ','.join(sorted(container.format.name.split(','))),
        'size': str(os.path.getsize(path)),
    }
    try:
        if container.duration:
            fmt['duration'] = f'{container.duration / 1_000_000:.6f}'
    except Exception:
        pass
    try:
        if container.bit_rate:
            fmt['bit_rate'] = str(int(container.bit_rate))
    except Exception:
        pass

    want_stream = want.get('stream', set()) if want else set()
    want_format = want.get('format', set()) if want else set()
    if want:
        streams = [_filter(s, want_stream) for s in streams]
        fmt = _filter(fmt, want_format)

    out = {}
    if show_streams or want_stream or (not show_format and not want):
        out['streams'] = streams
    if show_format or want_format or (not show_streams and not want):
        out['format'] = fmt

    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
