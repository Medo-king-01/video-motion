"""Agent-authored text direction: the single source of truth for which motion
style each scene's captions and on-screen text use. Shared contract for P/K/R.

The agent decides per scene (no default, no random picker). This module only
validates and resolves those explicit choices; it never invents a style.
"""
from __future__ import annotations

import json
from pathlib import Path

from caption_motion import SPECIAL_STYLES, STYLE_ALIAS
from caption_styles import CAPTION_STYLE_IDS

TEXT_ROLES = ("hook", "title", "body", "keyword", "cta", "label")
KNOWN_STYLES = frozenset((*SPECIAL_STYLES, *STYLE_ALIAS, *CAPTION_STYLE_IDS))
MIN_REASON = 12


def is_text_style(style) -> bool:
    return isinstance(style, str) and (style in KNOWN_STYLES or STYLE_ALIAS.get(style) in KNOWN_STYLES)


def _scene_index(scene, pos):
    return scene.get("index", pos + 1)


def validate(direction, beats=None) -> dict:
    """Return {'errors': [...], 'warnings': [...]}. Errors block a render/lint."""
    errors, warnings = [], []
    if not isinstance(direction, dict):
        return {"errors": ["plan/text-direction.json must be an object"], "warnings": []}
    if direction.get("version") != 1:
        errors.append("text-direction version must be 1")
    if direction.get("status") != "directed":
        errors.append('text-direction status must be "directed" (the agent has chosen the styles)')
    if direction.get("decidedBy") not in ("agent", "user"):
        errors.append('text-direction decidedBy must be "agent" or "user"')
    concept = direction.get("concept")
    if not isinstance(concept, str) or len(concept.strip()) < MIN_REASON:
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
        why = sc.get("captionWhy")
        if not isinstance(why, str) or len(why.strip()) < MIN_REASON:
            errors.append(f"scene {idx}: captionWhy must justify the caption style (>= {MIN_REASON} chars)")
        ts = sc.get("textStyles") or {}
        if not isinstance(ts, dict):
            errors.append(f"scene {idx}: textStyles must be an object keyed by role")
        else:
            for role, style in ts.items():
                if role not in TEXT_ROLES:
                    errors.append(f"scene {idx}: unknown text role '{role}'")
                if not is_text_style(style):
                    errors.append(f"scene {idx}: textStyles.{role} must be an explicit caption-safe style")
            if ts:
                tw = sc.get("textWhy")
                if not isinstance(tw, str) or len(tw.strip()) < MIN_REASON:
                    errors.append(f"scene {idx}: textWhy must justify the on-screen text styles")

    if beats and isinstance(beats.get("scenes"), list):
        wanted = {_scene_index(s, i) for i, s in enumerate(beats["scenes"])}
        missing = sorted(wanted - set(by_index))
        extra = sorted(set(by_index) - wanted)
        if missing:
            errors.append(f"text-direction missing scenes: {missing}")
        if extra:
            errors.append(f"text-direction has scenes not in the timeline: {extra}")

    # Variety is advisory: a repeated motif is allowed when it is explained.
    styles = [sc.get("captionStyle") for sc in scenes if is_text_style(sc.get("captionStyle"))]
    if len(styles) >= 3 and len(set(styles)) == 1 and not direction.get("motifReason"):
        warnings.append("every scene uses the same captionStyle — vary it per scene, or add motifReason to justify a deliberate motif")
    return {"errors": errors, "warnings": warnings}


def load(project) -> dict:
    p = Path(project) / "plan" / "text-direction.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else {}


def init_draft(beats) -> dict:
    """A draft skeleton mirroring the timeline. The agent fills every choice."""
    scenes = []
    for i, s in enumerate(beats.get("scenes") or []):
        scenes.append({"scene": _scene_index(s, i), "captionStyle": None, "captionWhy": None,
                       "textStyles": {}, "textWhy": None})
    return {"version": 1, "status": "draft", "decidedBy": None, "concept": None, "scenes": scenes}


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


def text_style_for(direction, scene, role) -> str:
    style = (_find(direction, scene).get("textStyles") or {}).get(role)
    if not is_text_style(style):
        raise ValueError(f"Scene {scene} has no explicit textStyles.{role}.")
    return style
