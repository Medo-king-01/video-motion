#!/usr/bin/env python3
"""Draft/check beat-by-beat visual treatments against measured VO words and copy."""
from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'medo-motion/scripts'))
from _safe_paths import checked_path  # noqa: E402

DATA_KINDS = {'comparison', 'timeline', 'counter'}


def numeric(n):
    return isinstance(n, (int, float)) and not isinstance(n, bool) and math.isfinite(n)


def load(path, default=None):
    return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else default


def init_draft(beats):
    return {'version': 1, 'status': 'draft', 'decidedBy': None, 'clock': 'vo',
            'note': 'Choose presenter/overlay/cover and justify each beat. Anchors must come from measured VO words, never guessed.',
            'scenes': [{'scene': s.get('index', i + 1), 'start': s['start'], 'end': s['end'],
                        'treatment': None, 'why': '', 'elements': []} for i, s in enumerate(beats.get('scenes') or [])]}


def measured_words(document):
    """Canonical absolute words or caption_align measurement list (local final -> VO)."""
    if document is None:
        return {}
    local = isinstance(document, list)
    scenes = document if local else document.get('scenes', [])
    if not local and document.get('clock') != 'vo':
        raise ValueError('word timings must declare clock=vo')
    out = {}
    for i, sc in enumerate(scenes):
        index = sc.get('index', i + 1) if local else sc['scene']
        if index in out:
            raise ValueError('duplicate word-timing scene')
        offset = sc['start'] if local else 0
        out[index] = [{**word, 'start': word['start'] + offset, 'end': word['end'] + offset}
                      for word in (sc.get('final', []) if local else sc.get('words', []))]
    return out


def _validate(direction, beats, words=None, copy=None, project=None):
    errors = []
    if not isinstance(direction, dict) or direction.get('version') != 1 or direction.get('clock') != 'vo':
        return {'errors': ['visual-direction requires version=1 and clock=vo']}
    if direction.get('status') != 'ready' or not isinstance(direction.get('decidedBy'), str) or len(direction['decidedBy'].strip()) < 3:
        errors.append('visual direction is draft; an agent must choose and record decidedBy')
    expected = {s.get('index', i + 1): s for i, s in enumerate(beats.get('scenes') or [])}
    duration = beats.get('duration')
    if not numeric(duration) or duration <= 0 or not expected:
        errors.append('measure the VO and scene bounds first')
    try:
        measured = measured_words(words)
        for index, timings in measured.items():
            previous = expected.get(index, {}).get('start', 0)
            bound = expected.get(index, {}).get('end', -1)
            for w in timings:
                if not isinstance(w.get('text'), str) or not w['text'].strip() or not numeric(w['start']) or not numeric(w['end']) or not previous <= w['start'] < w['end'] <= bound:
                    raise ValueError('word timings must be finite, ordered and inside their measured scene')
                previous = w['end']
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        errors.append(str(error)); measured = {}
    scenes = direction.get('scenes')
    if not isinstance(scenes, list):
        return {'errors': errors + ['scenes must be a list']}
    copies = {item.get('id'): item for item in (copy or {}).get('copy', []) if item.get('id')}
    seen, element_ids, used_copy = set(), set(), set()
    for sc in scenes:
        if not isinstance(sc, dict):
            errors.append('scene must be an object'); continue
        index = sc.get('scene')
        if not isinstance(index, int) or isinstance(index, bool) or index not in expected or index in seen:
            errors.append('visual scenes must cover measured scene indices exactly once'); continue
        seen.add(index)
        beat = expected[index]
        if sc.get('start') != beat['start'] or sc.get('end') != beat['end']:
            errors.append(f'scene {index}: visual bounds must equal VO scene bounds')
        if sc.get('treatment') not in {'presenter', 'overlay', 'cover'}:
            errors.append(f'scene {index}: choose presenter, overlay or cover')
        if not isinstance(sc.get('why'), str) or len(sc['why'].strip()) < 12:
            errors.append(f'scene {index}: explain what this treatment clarifies')
        elements = sc.get('elements')
        if not isinstance(elements, list):
            errors.append(f'scene {index}: elements must be a list'); continue
        if sc.get('treatment') == 'presenter' and elements:
            errors.append(f'scene {index}: presenter-only cannot declare graphics; choose overlay or cover')
        if sc.get('treatment') in {'overlay', 'cover'} and not elements:
            errors.append(f'scene {index}: overlay/cover needs an explicit visual element')
        for e in elements:
            if not isinstance(e, dict):
                errors.append('element must be an object'); continue
            eid = e.get('id')
            if not isinstance(eid, str) or not eid.strip() or eid in element_ids:
                errors.append('visual elements need unique ids')
            element_ids.add(str(eid))
            if e.get('kind') not in DATA_KINDS | {'illustration', 'text', 'diagram'}:
                errors.append(f'{eid}: unknown visual kind')
            if not isinstance(e.get('why'), str) or len(e['why'].strip()) < 12:
                errors.append(f'{eid}: explain why the visual supports the spoken line')
            refs = e.get('copyIds')
            if not isinstance(refs, list) or any(not isinstance(r, str) or r not in copies or copies[r].get('scene') != index for r in refs):
                errors.append(f'{eid}: copyIds must reference copy.json ids in this scene')
            else:
                for ref in refs:
                    if ref in used_copy:
                        errors.append(f'{eid}: duplicate visual mapping for copy {ref}')
                    used_copy.add(ref)
            a = e.get('anchor') or {}
            wi = a.get('word') if isinstance(a, dict) else None
            ws = measured.get(index, [])
            if not isinstance(wi, int) or isinstance(wi, bool) or not 0 <= wi < len(ws):
                errors.append(f'{eid}: anchor must reference a measured word index'); continue
            word = ws[wi]
            if a.get('text') != word['text']:
                errors.append(f'{eid}: anchor text does not match the measured word')
            start, end, mode = e.get('start'), e.get('end'), e.get('timing')
            if not numeric(start) or not numeric(end) or not beat['start'] <= start < end <= beat['end']:
                errors.append(f'{eid}: element bounds must be finite and inside the scene'); continue
            if mode == 'lead':
                if e.get('fact') is not False or e.get('kind') in DATA_KINDS or not 0 <= word['start'] - start <= 6 / 30 + 1e-8:
                    errors.append(f'{eid}: lead is structure-only, at most six locked-30fps frames before the word')
            elif mode == 'sync':
                if abs(start - word['start']) > 1e-6:
                    errors.append(f'{eid}: sync must start at its measured word')
            elif mode == 'reveal':
                if start < word['start']:
                    errors.append(f'{eid}: withheld information cannot appear before its revealing word')
            else:
                errors.append(f'{eid}: timing must be lead, sync or reveal')
            if end < word['end']:
                errors.append(f'{eid}: visual must survive its anchor word')
            if e.get('kind') in DATA_KINDS:
                if e.get('evidence') not in {'user', 'source', 'illustrative'}:
                    errors.append(f'{eid}: classify evidence as user/source/illustrative')
                try:
                    if project is None:
                        raise ValueError('project root required to validate dataset')
                    name = e.get('dataset')
                    if not isinstance(name, str) or Path(name).is_absolute():
                        raise ValueError('dataset must be a project-relative path')
                    path = checked_path(project / name, within=project)
                    data = load(path)
                    from data_recipe import validate as validate_data
                    issues = validate_data(data)
                    if issues:
                        raise ValueError('; '.join(issues))
                    if data['kind'] != e['kind']:
                        raise ValueError('dataset kind does not match element kind')
                except (ValueError, OSError, TypeError, subprocess.SubprocessError) as error:
                    errors.append(f'{eid}: {error}')
    if seen != set(expected):
        errors.append('visual direction is missing measured scenes')
    return {'errors': errors}


def validate(direction, beats, words=None, copy=None, project=None):
    try:
        return _validate(direction, beats, words, copy, project)
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        return {'errors': [f'Malformed visual direction/input: {error}']}


def _check_project(project, words_path=None):
    direction = load(project / 'plan/visual-direction.json', {})
    if not isinstance(direction, dict):
        return {'errors': ['visual direction must be an object']}
    if words_path is None:
        name = direction.get('wordTimings', 'plan/word-timings.json')
        if not isinstance(name, str) or Path(name).is_absolute():
            return {'errors': ['wordTimings must be a project-relative path']}
        try:
            words_path = checked_path(project / name, within=project)
        except ValueError as error:
            return {'errors': [str(error)]}
    return validate(direction, load(project / 'plan/beats.json', {}), load(words_path),
                    load(project / 'plan/copy.json', {}), project)


def check_project(project, words_path=None):
    try:
        return _check_project(project, words_path)
    except (ValueError, TypeError, KeyError, AttributeError, OSError) as error:
        return {'errors': [f'Cannot verify visual direction: {error}']}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('project', type=Path)
    ap.add_argument('--init', action='store_true')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--words', type=Path, help='canonical VO word timings or caption_align measurements')
    args = ap.parse_args()
    project = checked_path(args.project)
    if args.init:
        target = checked_path(project / 'plan/visual-direction.json', within=project)
        draft = init_draft(load(project / 'plan/beats.json', {}))
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('w' if args.force else 'x', encoding='utf-8') as stream:
            json.dump(draft, stream, ensure_ascii=False, indent=2)
        print('Draft created: choose treatments and measured anchors; no timing was invented')
        return 0
    report = check_project(project, args.words)
    for error in report['errors']:
        print('!!', error)
    if not report['errors']:
        print('Visual direction OK')
    return int(bool(report['errors']))


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'Visual direction blocked: {error}', file=sys.stderr)
        raise SystemExit(1) from error
