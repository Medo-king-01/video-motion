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


def _timing_errors(direction, beats, words) -> tuple[list[str], dict]:
    """Measured word anchors must be finite, ordered, inside their scene, and complete."""
    errors: list[str] = []
    expected = {s.get('index', i + 1): s for i, s in enumerate(beats.get('scenes') or [])}
    duration = beats.get('duration')
    if not numeric(duration) or duration <= 0 or not expected:
        return ['measure the VO and scene bounds first'], expected
    try:
        measured = measured_words(words)
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return [str(error)], expected
    for index, timings in measured.items():
        previous = expected.get(index, {}).get('start', 0)
        bound = expected.get(index, {}).get('end', -1)
        for word in timings:
            if (not isinstance(word.get('text'), str) or not word['text'].strip()
                    or not numeric(word.get('start')) or not numeric(word.get('end'))
                    or not previous <= word['start'] < word['end'] <= bound):
                return ['word timings must be finite, ordered and inside their measured scene'], expected
            previous = word['end']
    return errors, expected


def _dataset_errors(element: dict, project) -> list[str]:
    """A comparison/timeline/counter element must point at a valid, matching dataset."""
    errors: list[str] = []
    if element.get('evidence') not in {'user', 'source', 'illustrative'}:
        errors.append(f"{element['id']}: classify evidence as user/source/illustrative")
    try:
        if project is None:
            raise ValueError('project root required to validate dataset')
        name = element.get('dataset')
        if not isinstance(name, str) or Path(name).is_absolute():
            raise ValueError('dataset must be a project-relative path')
        path = checked_path(project / name, within=project)
        data = load(path)
        from data_recipe import validate as validate_data
        issues = validate_data(data)
        if issues:
            raise ValueError('; '.join(issues))
        if data['kind'] != element['kind']:
            raise ValueError('dataset kind does not match element kind')
    except (ValueError, OSError, TypeError, subprocess.SubprocessError) as error:
        errors.append(f"{element['id']}: {error}")
    return errors


def _anchor_errors(element: dict, beat: dict, measured: dict) -> tuple[list[str], dict | None]:
    """The element must be anchored to one measured word of its own scene."""
    anchor = element.get('anchor') or {}
    word_index = anchor.get('word') if isinstance(anchor, dict) else None
    words = measured.get(beat.get('index'), [])
    if not isinstance(word_index, int) or isinstance(word_index, bool) or not 0 <= word_index < len(words):
        return [f"{element['id']}: anchor must reference a measured word index"], None
    word = words[word_index]
    if anchor.get('text') != word['text']:
        return [f"{element['id']}: anchor text does not match the measured word"], None
    return [], word


def _element_timing_errors(element: dict, word: dict, beat: dict) -> list[str]:
    """lead / sync / reveal: structure may lead a word, information may never precede it."""
    start, end, mode = element.get('start'), element.get('end'), element.get('timing')
    if not numeric(start) or not numeric(end) or not beat['start'] <= start < end <= beat['end']:
        return [f"{element['id']}: element bounds must be finite and inside the scene"]
    if mode == 'lead':
        if (element.get('fact') is not False or element.get('kind') in DATA_KINDS
                or not 0 <= word['start'] - start <= 6 / 30 + 1e-8):
            return [f"{element['id']}: lead is structure-only, at most six locked-30fps frames before the word"]
    elif mode == 'sync':
        if abs(start - word['start']) > 1e-6:
            return [f"{element['id']}: sync must start at its measured word"]
    elif mode == 'reveal':
        if start < word['start']:
            return [f"{element['id']}: withheld information cannot appear before its revealing word"]
    else:
        return [f"{element['id']}: timing must be lead, sync or reveal"]
    if end < word['end']:
        return [f"{element['id']}: visual must survive its anchor word"]
    return []


def _element_errors(element, beat, measured, copies, element_ids, used_copy, project) -> list[str]:
    """One visual element: identity, kind, copy mapping, measured anchor and safe timing."""
    if not isinstance(element, dict):
        return ['element must be an object']
    errors: list[str] = []
    element_id = element.get('id')
    if not isinstance(element_id, str) or not element_id.strip() or element_id in element_ids:
        errors.append('visual elements need unique ids')
    element_ids.add(str(element_id))
    if element.get('kind') not in DATA_KINDS | {'illustration', 'text', 'diagram'}:
        errors.append(f'{element_id}: unknown visual kind')
    if not isinstance(element.get('why'), str) or len(element['why'].strip()) < 12:
        errors.append(f'{element_id}: explain why the visual supports the spoken line')
    index = beat['index']
    refs = element.get('copyIds')
    if not isinstance(refs, list) or any(not isinstance(r, str) or r not in copies or copies[r].get('scene') != index
                                        for r in refs):
        errors.append(f'{element_id}: copyIds must reference copy.json ids in this scene')
    else:
        for ref in refs:
            if ref in used_copy:
                errors.append(f'{element_id}: duplicate visual mapping for copy {ref}')
            used_copy.add(ref)
    anchor_errors, word = _anchor_errors(element, beat, measured)
    errors += anchor_errors
    if word is None:
        return errors
    errors += _element_timing_errors(element, word, beat)
    if element.get('kind') in DATA_KINDS:
        errors += _dataset_errors(element, project)
    return errors


def _validate(direction, beats, words=None, copy=None, project=None):
    if not isinstance(direction, dict) or direction.get('version') != 1 or direction.get('clock') != 'vo':
        return {'errors': ['visual-direction requires version=1 and clock=vo']}
    errors: list[str] = []
    if (direction.get('status') != 'ready' or not isinstance(direction.get('decidedBy'), str)
            or len(direction['decidedBy'].strip()) < 3):
        errors.append('visual direction is draft; an agent must choose and record decidedBy')
    timing_errors, expected = _timing_errors(direction, beats, words)
    errors += timing_errors
    try:
        measured = measured_words(words)
    except (ValueError, KeyError, TypeError, AttributeError):
        measured = {}
    scenes = direction.get('scenes')
    if not isinstance(scenes, list):
        return {'errors': errors + ['scenes must be a list']}
    copies = {item.get('id'): item for item in (copy or {}).get('copy', []) if item.get('id')}
    seen, element_ids, used_copy = set(), set(), set()
    for scene in scenes:
        if not isinstance(scene, dict):
            errors.append('scene must be an object')
            continue
        index = scene.get('scene')
        if not isinstance(index, int) or isinstance(index, bool) or index not in expected or index in seen:
            errors.append('visual scenes must cover measured scene indices exactly once')
            continue
        seen.add(index)
        beat = expected[index]
        if scene.get('start') != beat['start'] or scene.get('end') != beat['end']:
            errors.append(f'scene {index}: visual bounds must equal VO scene bounds')
        if scene.get('treatment') not in {'presenter', 'overlay', 'cover'}:
            errors.append(f'scene {index}: choose presenter, overlay or cover')
        if not isinstance(scene.get('why'), str) or len(scene['why'].strip()) < 12:
            errors.append(f'scene {index}: explain what this treatment clarifies')
        elements = scene.get('elements')
        if not isinstance(elements, list):
            errors.append(f'scene {index}: elements must be a list')
            continue
        if scene.get('treatment') == 'presenter' and elements:
            errors.append(f'scene {index}: presenter-only cannot declare graphics; choose overlay or cover')
        if scene.get('treatment') in {'overlay', 'cover'} and not elements:
            errors.append(f'scene {index}: overlay/cover needs an explicit visual element')
        for element in elements:
            errors += _element_errors(element, beat, measured, copies, element_ids, used_copy, project)
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
