"""Shared helpers for the Video Motion scripts (Windows, macOS, Linux; Python >= 3.9, stdlib only)."""
import json, os, shutil, subprocess, sys
from video_motion_paths import executable
for _s in (sys.stdout, sys.stderr):  # Windows consoles (cp1252) can't print ✅/❌ -> force UTF-8
    try: _s.reconfigure(encoding='utf-8', errors='replace')
    except Exception: pass
KEYS = ['PIXABAY_API_KEY', 'FREESOUND_CLIENT_ID', 'FREESOUND_API_KEY', 'UNSPLASH_APPLICATION_ID', 'UNSPLASH_ACCESS_KEY',
        'UNSPLASH_SECRET_KEY', 'FIRECRAWL_API_KEY', 'ELEVENLABS_API_KEY']
def load_env(path='.env'):
    """read NAME=value lines into a dict (values are never printed)"""
    env = {}
    if os.path.exists(path):
        for ln in open(path, encoding='utf-8-sig'):
            ln = ln.strip()
            if ln and not ln.startswith('#') and '=' in ln:
                k, v = ln.split('=', 1); env[k.strip()] = v.strip().strip('"').strip("'")
    return env
def which(*names):
    for n in names:
        p = shutil.which(n)
        if p: return p
    return None
def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)
def ffmpeg(): return executable('ffmpeg') or sys.exit('ffmpeg not found on PATH (install: winget install Gyan.FFmpeg / brew install ffmpeg / sudo apt install ffmpeg)')
def ffprobe(): return executable('ffprobe') or sys.exit('ffprobe not found on PATH (comes with ffmpeg)')


def append_asset_entry(manifest, entry, *, key='path'):
    """Record an external asset in a manifest.json that is either a list or {"assets": [...]}.

    Both downloaders (fonts, sound) have to append without duplicating and without
    rewriting an unrecognised file. Returns a short human status for the CLI to print.
    """
    if not manifest.exists():
        manifest.write_text('[]\n', encoding='utf-8')
    data = json.loads(manifest.read_text(encoding='utf-8-sig') or '[]')
    items = data if isinstance(data, list) else data.get('assets') if isinstance(data, dict) else None
    if not isinstance(items, list):
        return 'manifest format not recognised; add the entry by hand'
    if any(isinstance(i, dict) and i.get(key) == entry[key] for i in items):
        return 'manifest already lists it'
    items.append(entry)
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 'manifest updated'
