"""Agent-authored text direction: the single source of truth for which motion
style EVERY visible text element uses — captions, titles, keywords, numbers,
CTAs, labels and UI text. Shared contract for P/K/R.

The agent decides per scene (no default, no random picker). This module only
validates and resolves those explicit choices; it never invents a style.
"""
from __future__ import annotations

import json
from pathlib import Path

from caption_motion import SPECIAL_STYLES, STYLE_ALIAS
from caption_styles import CAPTION_STYLE_IDS

TEXT_ROLES = ("hook", "title", "body", "keyword", "cta", "label", "number", "ui", "quote")
KNOWN_STYLES = frozenset((*SPECIAL_STYLES, *STYLE_ALIAS, *CAPTION_STYLE_IDS))
MIN_REASON = 12
VERSION = 2


def is_text_style(style) -> bool:
    return isinstance(style, str) and (style in KNOWN_STYLES or STYLE_ALIAS.get(style) in KNOWN_STYLES)


def _scene_index(scene, pos):
    return scene.get("index", pos + 1)


def _long(value) -> bool:
    return isinstance(value, str) and len(value.strip()) >= MIN_REASON


def validate(direction, beats=None, copy=None) -> dict:
    """Return {'errors': [...], 'warnings': [...]}. Errors block a render/lint.

    `copy` is the on-screen text inventory (plan/copy.json). When supplied, every
    fragment must point at an explicit, agent-chosen style — not just captions.
    """
    errors, warnings = [], []
    if not isinstance(direction, dict):
        return {"errors": ["plan/text-direction.json must be an object"], "warnings": []}
    if direction.get("version") != VERSION:
        errors.append(f"text-direction version must be {VERSION}")
    if direction.get("status") != "directed":
        errors.append('text-direction status must be "directed" (the agent has chosen the styles)')
    if direction.get("decidedBy") not in ("agent", "user"):
        errors.append('text-direction decidedBy must be "agent" or "user"')
    if not _long(direction.get("concept")):
        errors.append("text-direction concept must explain the reel's text-motion idea (>= 12 chars)")

    scenes = direction.get("scenes")
    if not isinstance(scenes, list):
        errors.append("text-direction scenes must be a list")
        return {"errors": errors, "warnings": warnings}

    by_index = {}
    for sc in scenes:
        if not isinstance(sc, dict) or not isinstance(sc.get("scene"), int):
            errors.append("each text-direction scene needs an integer 'scene' index")
            continue
        idx = sc["scene"]
        if idx in by_index:
            errors.append(f"duplicate text-direction scene {idx}")
        by_index[idx] = sc
        if not is_text_style(sc.get("captionStyle")):
            errors.append(f"scene {idx}: captionStyle must be an explicit caption-safe style")
        if not _long(sc.get("captionWhy")):
            errors.append(f"scene {idx}: captionWhy must justify the caption style (>= {MIN_REASON} chars)")
        ts = sc.get("textStyles")
        if not isinstance(ts, dict):
            errors.append(f"scene {idx}: textStyles must be an object keyed by text role")
        else:
            for role, style in ts.items():
                if role not in TEXT_ROLES:
                    errors.append(f"scene {idx}: unknown text role '{role}'")
                if not is_text_style(style):
                    errors.append(f"scene {idx}: textStyles.{role} must be an explicit caption-safe style")
            if ts and not _long(sc.get("textWhy")):
                errors.append(f"scene {idx}: textWhy must justify the on-screen text styles")
        elements = sc.get("textElements") or {}
        if not isinstance(elements, dict):
            errors.append(f"scene {idx}: textElements must be an object keyed by element id")
        else:
            for eid, el in elements.items():
                if not isinstance(el, dict):
                    errors.append(f"scene {idx}: textElements.{eid} must be an object")
                    continue
                if el.get("role") not in TEXT_ROLES:
                    errors.append(f"scene {idx}: textElements.{eid} has an unknown role")
                if not is_text_style(el.get("style")):
                    errors.append(f"scene {idx}: textElements.{eid}.style must be an explicit caption-safe style")
                if not _long(el.get("why")):
                    errors.append(f"scene {idx}: textElements.{eid}.why must justify this element's motion")

    if beats and isinstance(beats.get("scenes"), list):
        wanted = {_scene_index(s, i) for i, s in enumerate(beats["scenes"])}
        missing = sorted(wanted - set(by_index))
        extra = sorted(set(by_index) - wanted)
        if missing:
            errors.append(f"text-direction missing scenes: {missing}")
        if extra:
            errors.append(f"text-direction has scenes not in the timeline: {extra}")

    # Every visible non-caption fragment must resolve to an explicit choice.
    if copy and isinstance(copy.get("copy"), list):
        for i, item in enumerate(copy["copy"]):
            if not isinstance(item, dict):
                errors.append(f"copy[{i}] must be an object")
                continue
            scene = item.get("scene")
            role = item.get("role")
            label = item.get("id") or f"copy[{i}]"
            sc = by_index.get(scene)
            if sc is None:
                errors.append(f"{label}: scene {scene} has no text direction")
                continue
            if role not in TEXT_ROLES:
                errors.append(f"{label}: every on-screen text fragment needs a known role (got {role!r})")
                continue
            elements = sc.get("textElements") or {}
            eid = item.get("id")
            if eid and eid in elements:
                el = elements[eid]
                if el.get("role") != role:
                    errors.append(f"{label}: textElements role does not match the copy role")
                if not is_text_style(el.get("style")):
                    errors.append(f"{label}: no explicit style for this text element")
            elif not is_text_style((sc.get("textStyles") or {}).get(role)):
                errors.append(f"{label}: scene {scene} has no textStyles.{role} (or textElements.{eid}) for this text")

    # Variety is advisory: a repeated motif is allowed when it is explained.
    styles = [sc.get("captionStyle") for sc in scenes if is_text_style(sc.get("captionStyle"))]
    if len(styles) >= 3 and len(set(styles)) == 1 and not direction.get("motifReason"):
        warnings.append("every scene uses the same captionStyle — vary it per scene, or add motifReason to justify a deliberate motif")
    return {"errors": errors, "warnings": warnings}


def load(project) -> dict:
    p = Path(project) / "plan" / "text-direction.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def load_copy(project) -> dict:
    p = Path(project) / "plan" / "copy.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def init_draft(beats) -> dict:
    """A draft skeleton mirroring the timeline. The agent fills every choice."""
    scenes = []
    for i, s in enumerate(beats.get("scenes") or []):
        scenes.append({"scene": _scene_index(s, i), "captionStyle": None, "captionWhy": None,
                       "textStyles": {}, "textWhy": None, "textElements": {}})
    return {"version": VERSION, "status": "draft", "decidedBy": None, "concept": None, "scenes": scenes}


def _find(direction, scene):
    for sc in direction.get("scenes") or []:
        if sc.get("scene") == scene:
            return sc
    raise ValueError(f"No text direction for scene {scene}; the agent must choose its styles.")


def caption_style_for(direction, scene) -> str:
    style = _find(direction, scene).get("captionStyle")
    if not is_text_style(style):
        raise ValueError(f"Scene {scene} has no explicit captionStyle.")
    return style


def text_style_for(direction, scene, role, element_id=None) -> str:
    """Resolve the agent's choice for ANY visible text: element override first,
    then the scene's role style. Never falls back to a default."""
    sc = _find(direction, scene)
    if element_id:
        el = (sc.get("textElements") or {}).get(element_id)
        if el and is_text_style(el.get("style")):
            if el.get("role") not in (None, role):
                raise ValueError(f"Scene {scene} textElements.{element_id} role does not match '{role}'.")
            return el["style"]
    style = (sc.get("textStyles") or {}).get(role)
    if not is_text_style(style):
        raise ValueError(f"Scene {scene} has no explicit text style for role '{role}'"
                         + (f" (element '{element_id}')" if element_id else "") + ".")
    return style
