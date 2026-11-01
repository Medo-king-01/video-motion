#!/usr/bin/env python3
"""Download free Google Fonts families (OFL/Apache/UFL) with their licence into the project.

Usage (run from the project folder):
  python <skill>/scripts/get_fonts.py --list                      # catalog of tested Arabic + pairing fonts
  python <skill>/scripts/get_fonts.py --check "Kufam" "Alexandria" # verify availability, download nothing
  python <skill>/scripts/get_fonts.py "Kufam" "Readex Pro"         # download into assets/fonts/<Family>/

NOTE: the studio's curated 14-family type system lives in `assets/fonts/` and is managed by
`tools/fonts_install.py` (npm `@expo-google-fonts/*`, TTF + OFL). Use this script only for a family
outside that curated list — and register it in `assets/fonts/fonts.json` + `docs/fonts.md` afterwards.

Source: the official github.com/google/fonts repository only. Saves the licence file beside the fonts,
writes SOURCE.md, and appends an entry to manifest.json when it is a JSON list or {"assets": [...]}.
Never overwrites existing files. Optional GITHUB_TOKEN raises GitHub's rate limit (never printed).
"""
import argparse, json, os, pathlib, re, sys, urllib.request, urllib.error, urllib.parse
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass

API = 'https://api.github.com/repos/google/fonts/contents/{}/{}'
ALLOWED_HOSTS = {'api.github.com', 'raw.githubusercontent.com'}
LICENCE_DIRS = ('ofl', 'apache', 'ufl')
LICENCE_FILES = {'OFL.txt': 'SIL Open Font License 1.1', 'LICENSE.txt': 'Apache License 2.0', 'UFL.txt': 'Ubuntu Font Licence 1.0'}
MAX_BYTES = 25 * 1024 * 1024

# Arabic families (role, feel) and Latin pairing families. Descriptions live in reference/arabic-fonts.md.
CATALOG = {
    'arabic-display': ['Kufam', 'Reem Kufi', 'Reem Kufi Fun', 'Lalezar', 'Marhey', 'Rakkas', 'Jomhuria', 'Lemonada',
                       'Changa', 'Baloo Bhaijaan 2', 'Badeen Display', 'Blaka', 'Handjet', 'Aref Ruqaa', 'Qahiri', 'Katibeh'],
    'arabic-text': ['Alexandria', 'IBM Plex Sans Arabic', 'Readex Pro', 'Cairo', 'Tajawal', 'Almarai', 'Noto Kufi Arabic',
                    'Noto Sans Arabic', 'Noto Naskh Arabic', 'Rubik', 'Vazirmatn', 'Amiri', 'El Messiri', 'Markazi Text',
                    'Playpen Sans Arabic', 'Beiruti', 'Zain'],
    'latin-pairing': ['Archivo', 'Instrument Serif', 'JetBrains Mono', 'Space Mono', 'VT323', 'Press Start 2P', 'Inter', 'Anton'],
}

def _request(url):
    host = urllib.parse.urlparse(url).hostname
    if host not in ALLOWED_HOSTS:
        raise ValueError(f'refusing non-GitHub host: {host}')
    req = urllib.request.Request(url, headers={'User-Agent': 'khaam-motion-fonts', 'Accept': 'application/vnd.github+json'})
    token = os.environ.get('GITHUB_TOKEN')
    if token and host == 'api.github.com':
        req.add_header('Authorization', 'Bearer ' + token)
    return urllib.request.urlopen(req, timeout=30)

def family_dir(family):
    return re.sub(r'[^a-z0-9]', '', family.lower())

def lookup(family):
    """Return (licence_dir, listing) for a family, or (None, reason)."""
    slug = family_dir(family)
    for lic in LICENCE_DIRS:
        try:
            with _request(API.format(lic, slug)) as r:
                return lic, json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: continue
            if e.code == 403: return None, 'GitHub rate limit reached; wait an hour or set GITHUB_TOKEN'
            return None, f'HTTP {e.code}'
        except (urllib.error.URLError, TimeoutError) as e:
            return None, f'network error: {e}'
    return None, 'not found in google/fonts'

def font_files(listing):
    files = [f for f in listing if f.get('type') == 'file' and f['name'].lower().endswith(('.ttf', '.otf'))]
    lic = [f for f in listing if f.get('type') == 'file' and f['name'] in LICENCE_FILES]
    return files, lic

def download(entry, dest):
    target = dest / entry['name']
    if target.exists():
        return 'kept'
    with _request(entry['download_url']) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"{entry['name']} is larger than {MAX_BYTES // 1048576} MB")
    target.write_bytes(data)
    return 'downloaded'

def update_manifest(manifest, rel_dir, family, licence, source_url, licence_file):
    if not manifest.exists():
        manifest.write_text('[]\n', encoding='utf-8')
    data = json.loads(manifest.read_text(encoding='utf-8-sig') or '[]')
    items = data if isinstance(data, list) else data.get('assets') if isinstance(data, dict) else None
    if not isinstance(items, list):
        return 'manifest format not recognised; add the entry by hand'
    if any(isinstance(i, dict) and i.get('path') == rel_dir for i in items):
        return 'manifest already lists it'
    items.append({'path': rel_dir, 'type': 'font', 'name': family, 'source_url': source_url,
                  'author': 'see licence file', 'license': licence, 'license_file': licence_file, 'used_in': []})
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 'manifest updated'

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('families', nargs='*')
    ap.add_argument('--list', action='store_true', help='print the tested catalog')
    ap.add_argument('--check', action='store_true', help='verify availability only, download nothing')
    ap.add_argument('--dest', default='assets/fonts')
    ap.add_argument('--manifest', default='manifest.json')
    a = ap.parse_args()
    if a.list:
        for group, names in CATALOG.items():
            print(f'{group}: ' + ', '.join(names))
        print('Details and licences: reference/arabic-fonts.md')
        return
    if not a.families:
        ap.error('name at least one family, or use --list')
    failed = 0
    for family in a.families:
        lic_dir, listing = lookup(family)
        if lic_dir is None:
            print(f'✗ {family}: {listing}'); failed += 1; continue
        files, lic = font_files(listing)
        if not files:
            print(f'✗ {family}: no TTF/OTF files at the top level'); failed += 1; continue
        licence = LICENCE_FILES.get(lic[0]['name'], 'see licence file') if lic else 'licence file missing'
        source = f'https://github.com/google/fonts/tree/main/{lic_dir}/{family_dir(family)}'
        if a.check:
            print(f'✓ {family}: {len(files)} file(s), {licence} — {source}'); continue
        dest = pathlib.Path(a.dest) / family
        dest.mkdir(parents=True, exist_ok=True)
        results = [download(f, dest) for f in files + lic]
        (dest / 'SOURCE.md').exists() or (dest / 'SOURCE.md').write_text(
            f'# {family}\nSource: {source}\nLicence: {licence} ({lic[0]["name"] if lic else "missing"})\n', encoding='utf-8')
        note = update_manifest(pathlib.Path(a.manifest), dest.as_posix(), family, licence, source,
                               (dest / lic[0]['name']).as_posix() if lic else '')
        print(f'✓ {family}: {results.count("downloaded")} downloaded, {results.count("kept")} kept → {dest.as_posix()} · {licence} · {note}')
    sys.exit(1 if failed else 0)

if __name__ == '__main__':
    main()
