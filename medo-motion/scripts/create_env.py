#!/usr/bin/env python3
"""Create private empty key slots; preserve existing values and never print them."""
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import KEYS
from _safe_paths import checked_path


def create_env(project):
    project = checked_path(project)
    project.mkdir(parents=True, exist_ok=True)
    envp = checked_path(project / '.env', within=project)
    gi = checked_path(project / '.gitignore', within=project)
    cur = envp.read_text(encoding='utf-8-sig') if envp.exists() else ''
    head = ('# API keys for Video Motion. Fill locally, then SAVE.\n'
            '# Leave unused keys empty. Never share this file.\n')
    lines = cur.splitlines()
    if not any(line.startswith('# API keys for ') for line in lines):
        lines = head.rstrip('\n').split('\n') + lines
    have = {line.split('=', 1)[0].strip() for line in lines if '=' in line and not line.lstrip().startswith('#')}
    lines += ['%s=' % key for key in KEYS if key not in have]
    # mkstemp creates 0600 regardless of umask. Replace atomically, never open the
    # destination for writing (so existing links/hardlinks cannot be truncated).
    fd, name = tempfile.mkstemp(prefix='.env.', dir=project)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write('\n'.join(lines).rstrip('\n') + '\n')
        checked_path(envp, within=project)
        os.replace(name, envp)
    finally:
        Path(name).unlink(missing_ok=True)
    g = gi.read_text(encoding='utf-8').splitlines() if gi.exists() else []
    for pattern in ('.env', '*.env', '.env.*', '.env-*', 'node_modules/', 'cache/', 'models/'):
        if pattern not in g:
            g.append(pattern)
    gi.write_text('\n'.join(g) + '\n', encoding='utf-8')
    return envp


def main():
    try:
        path = create_env(sys.argv[1] if len(sys.argv) > 1 else '.')
    except (OSError, ValueError) as error:
        raise SystemExit(f'Could not create private .env: {error}') from error
    print('Created/updated private key slots:', path)


if __name__ == '__main__':
    main()
