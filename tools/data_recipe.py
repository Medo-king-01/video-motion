#!/usr/bin/env python3
"""Validate JSON or convert CSV to a sourced data recipe dataset (no rendering/network)."""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'medo-motion' / 'scripts'))
from _safe_paths import checked_path  # noqa: E402


def validate(data):
    module = (ROOT / 'medo-motion/templates/render/lib/data-recipes.js').as_uri()
    script = f'import {{validateDataset}} from {json.dumps(module)}; let s=""; for await(const c of process.stdin)s+=c; console.log(JSON.stringify(validateDataset(JSON.parse(s))));'
    result = subprocess.run(['node', '--input-type=module', '-e', script], input=json.dumps(data, allow_nan=False),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('input', type=Path)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--kind', choices=['comparison', 'timeline', 'counter'])
    ap.add_argument('--source')
    ap.add_argument('--unit')
    ap.add_argument('--locale', default='ar-EG', choices=['ar-EG', 'en-US'])
    ap.add_argument('--decimals', type=int, default=0)
    args = ap.parse_args()
    if args.input.suffix.lower() == '.csv':
        if not all((args.kind, args.source, args.unit)):
            ap.error('CSV requires --kind, --source and --unit')
        with args.input.open(encoding='utf-8-sig', newline='') as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            row['value'] = float(row['value'])
            if args.kind == 'timeline':
                row['at'] = float(row['at'])
        data = dict(version=1, kind=args.kind, source=args.source, unit=args.unit,
                    locale=args.locale, decimals=args.decimals, rows=rows)
    else:
        data = json.loads(args.input.read_text(encoding='utf-8'))
    errors = validate(data)
    if errors:
        raise ValueError('; '.join(errors))
    if args.out:
        target = checked_path(args.out)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + '\n')
    print('Data recipe dataset OK')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f'Data recipe blocked: {error}', file=sys.stderr)
        raise SystemExit(1) from error
