"""Atomic authoring of experimental version 1.1 effects and curves."""
from __future__ import annotations

from copy import deepcopy

from unified_project_edit import _checked, _find_clip


def enable_effects_contract(project):
    """Explicitly upgrade the supported 1.0 project to 1.1; never downgrade."""
    _checked(project)
    result = deepcopy(project)
    result["schemaVersion"] = "1.1"
    _checked(result)
    return result


def add_effect(project, clip_id, effect):
    """Append a fully specified effect; no implicit contract migration."""
    _checked(project)
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    clip["effects"].append(deepcopy(effect))
    _checked(result)
    return result


def replace_effect(project, clip_id, effect_id, effect):
    """Replace settings in place, retaining its stable ID and any valid curve."""
    _checked(project)
    if not isinstance(effect, dict) or effect.get("id") != effect_id:
        raise ValueError("replacement must retain the effect ID")
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    for index, old in enumerate(clip["effects"]):
        if old["id"] == effect_id:
            clip["effects"][index] = deepcopy(effect)
            _checked(result)
            return result
    raise ValueError(f"Unknown effect: {effect_id!r}")


def set_curve(project, clip_id, curve):
    """Replace or create the value curve for an effect, preserving other curves."""
    _checked(project)
    if not isinstance(curve, dict) or not isinstance(curve.get("effectId"), str):
        raise ValueError("curve must be an object with an effectId")
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    for index, old in enumerate(clip["keyframes"]):
        if old["effectId"] == curve["effectId"]:
            clip["keyframes"][index] = deepcopy(curve)
            break
    else:
        clip["keyframes"].append(deepcopy(curve))
    _checked(result)
    return result


def remove_curve(project, clip_id, effect_id):
    _checked(project)
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    for index, curve in enumerate(clip["keyframes"]):
        if curve["effectId"] == effect_id:
            clip["keyframes"].pop(index)
            _checked(result)
            return result
    raise ValueError(f"Unknown curve for effect: {effect_id!r}")


def remove_effect(project, clip_id, effect_id):
    """Remove an effect only after its curve has been explicitly removed."""
    _checked(project)
    result = deepcopy(project)
    _, _, clip = _find_clip(result, clip_id)
    if any(curve["effectId"] == effect_id for curve in clip["keyframes"]):
        raise ValueError("Remove the effect's curve first")
    for index, effect in enumerate(clip["effects"]):
        if effect["id"] == effect_id:
            clip["effects"].pop(index)
            _checked(result)
            return result
    raise ValueError(f"Unknown effect: {effect_id!r}")
