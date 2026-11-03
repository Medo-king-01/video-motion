#!/usr/bin/env python3
"""Free sound effects from Openverse (openly licensed audio, no API key needed).

Usage (run from the project folder):
  python <skill>/scripts/openverse_sfx.py search "whoosh" [--n 10] [--cc0-only] [--max-seconds 4]
  python <skill>/scripts/openverse_sfx.py get <id> [--name whoosh-soft-01] [--dest assets/sfx]

Licences: CC0, Public Domain Mark and CC BY only by default (safe for commercial video when BY is credited).
NC, ND and SA licences are excluded: they forbid commercial use, editing, or force the video's licence.
`get` saves the file, a <name>.source.json sidecar, a line in <dest>/ATTRIBUTION.md, and a manifest.json entry.
Anonymous Openverse use is rate limited; search sparingly. Always audition before using a sound.
"""
import argparse, json, pathlib, re, sys, urllib.parse, urllib.request, urllib.error
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

API = 'https://api.openverse.org/v1/audio/'
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from _common import append_asset_entry  # noqa: E402

SAFE = {'cc0', 'pdm', 'by'}
MAX_BYTES = 50 * 1024 * 1024

def fetch_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'video-motion-sfx'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 429:
            sys.exit('Openverse rate limit reached. Wait a few minutes and try again.')
        sys.exit(f'Openverse error: HTTP {e.code}')
    except (urllib.error.URLError, TimeoutError) as e:
        sys.exit(f'Network error: {e}')

def licence_label(r):
    return f"CC {r['license'].upper()} {r.get('license_version') or ''}".strip() if r['license'] not in ('cc0', 'pdm') \
        else ('CC0 1.0' if r['license'] == 'cc0' else 'Public Domain Mark')

def search(a):
    licences = 'cc0' if a.cc0_only else 'cc0,pdm,by'
    # Openverse's own `length=short` means minutes, not seconds, so duration is filtered here instead.
    results = []
    for page in (1, 2, 3):   # anonymous requests allow at most 20 results per page
        q = urllib.parse.urlencode({'q': a.query, 'license': licences, 'page_size': 20, 'page': page})
        data = fetch_json(API + '?' + q)
        results += data.get('results', [])
        short = [r for r in results if (r.get('duration') or 0) / 1000 <= a.max_seconds]
        if len(short) >= a.n or page >= (data.get('page_count') or 1):
            break
    shown = 0
    for r in results:
        if r.get('mature') or r['license'] not in SAFE:
            continue
        secs = (r.get('duration') or 0) / 1000
        if secs and secs > a.max_seconds:
            continue
        shown += 1
        print(f"{shown:>2}. {r['title'][:60]}  ·  {secs:.1f}s  ·  {licence_label(r)}  ·  {r.get('creator') or 'unknown'}")
        print(f"    id: {r['id']}  ·  {r.get('foreign_landing_url')}")
        if shown >= a.n:
            break
    if not shown:
        print('No matching sounds. Try a simpler English word (whoosh, click, pop, impact, swoosh, ding).')

def slug(text):
    s = re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')
    return (s or 'sound')[:50]

def update_manifest(manifest, entry):
    return append_asset_entry(manifest, entry)


def get(a):
    if not re.fullmatch(r'[0-9a-fA-F-]{36}', a.id):
        sys.exit('Use the id printed by `search`.')
    r = fetch_json(API + a.id + '/')
    if r.get('license') not in SAFE:
        sys.exit(f"Refused: licence {r.get('license')} is not CC0/PDM/BY.")
    url = r.get('url') or ''
    if urllib.parse.urlparse(url).scheme != 'https':
        sys.exit('Refused: the file URL is not HTTPS.')
    ext = (r.get('filetype') or pathlib.PurePosixPath(urllib.parse.urlparse(url).path).suffix.lstrip('.') or 'mp3').lower()
    if ext not in ('mp3', 'wav', 'ogg', 'flac', 'aiff', 'm4a'):
        sys.exit(f'Refused: unexpected file type {ext}.')
    dest = pathlib.Path(a.dest); dest.mkdir(parents=True, exist_ok=True)
    name = slug(a.name or r['title'])
    target = dest / f'{name}.{ext}'
    if target.exists():
        sys.exit(f'{target.as_posix()} already exists; choose another --name.')
    req = urllib.request.Request(url, headers={'User-Agent': 'video-motion-sfx'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        ctype = resp.headers.get('Content-Type', '')
        if ctype and not (ctype.startswith('audio/') or ctype == 'application/octet-stream'):
            sys.exit(f'Refused: server sent {ctype}, not audio.')
        data = resp.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        sys.exit('Refused: file larger than 50 MB.')
    target.write_bytes(data)
    record = {k: r.get(k) for k in ('id', 'title', 'creator', 'creator_url', 'license', 'license_version', 'license_url',
                                     'provider', 'foreign_landing_url', 'url', 'attribution', 'duration', 'filetype')}
    record['note'] = 'Preview files from some providers are lossy MP3; label them honestly.'
    (dest / f'{name}.source.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    credit = r.get('attribution') or f"\"{r['title']}\" by {r.get('creator')} ({licence_label(r)})"
    if r['license'] == 'by':
        with open(dest / 'ATTRIBUTION.md', 'a', encoding='utf-8') as f:
            f.write(f'- {target.name}: {credit}\n')
    note = update_manifest(pathlib.Path(a.manifest), {
        'path': target.as_posix(), 'type': 'sfx', 'source_url': r.get('foreign_landing_url'), 'author': r.get('creator'),
        'license': licence_label(r), 'license_file': f'{name}.source.json', 'used_in': []})
    need = 'credit REQUIRED (see ATTRIBUTION.md)' if r['license'] == 'by' else 'no credit required'
    print(f'✓ saved {target.as_posix()} ({len(data) // 1024} KB) · {licence_label(r)} · {need} · {note}')

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    s = sub.add_parser('search'); s.add_argument('query'); s.add_argument('--n', type=int, default=8)
    s.add_argument('--cc0-only', action='store_true'); s.add_argument('--max-seconds', type=float, default=6)
    g = sub.add_parser('get'); g.add_argument('id'); g.add_argument('--name'); g.add_argument('--dest', default='assets/sfx')
    g.add_argument('--manifest', default='manifest.json')
    a = ap.parse_args()
    search(a) if a.cmd == 'search' else get(a)

if __name__ == '__main__':
    main()
