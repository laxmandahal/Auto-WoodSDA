# -*- coding: utf-8 -*-
"""
Thin wrapper around Codes/schema/loader.py for the GUI. Deliberately does not
re-implement load/save/validation -- `save_building_config` already
round-trips a real archetype byte-for-byte (confirmed against
BuildingInfo/MFD6B/building_config.yaml) and re-validates through
`BuildingConfig`'s own `model_validator` before writing, so the GUI gets that
validation for free by going through the same function every other consumer
of this schema uses.
"""

import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_GUI_DIR = os.path.dirname(_THIS_DIR)
_CODES_DIR = os.path.dirname(_GUI_DIR)
ROOT_DIR = os.path.dirname(_CODES_DIR)
SCHEMA_DIR = os.path.join(_CODES_DIR, 'schema')
BUILDING_INFO_DIR = os.path.join(ROOT_DIR, 'BuildingInfo')

if SCHEMA_DIR not in sys.path:
    sys.path.append(SCHEMA_DIR)

from loader import load_building_config, save_building_config, config_path  # noqa: E402
from building_config import BuildingConfig  # noqa: E402


def list_archetypes():
    """Archetype names = subdirectories of BuildingInfo/ that have a
    building_config.yaml. Only these are editable by the GUI (v1 -- see plan's
    'editing existing layouts only' scope decision)."""
    if not os.path.isdir(BUILDING_INFO_DIR):
        return []
    names = []
    for entry in sorted(os.listdir(BUILDING_INFO_DIR)):
        base_dir = os.path.join(BUILDING_INFO_DIR, entry)
        if os.path.isdir(base_dir) and os.path.isfile(config_path(base_dir)):
            names.append(entry)
    return names


def load(archetype):
    base_dir = os.path.join(BUILDING_INFO_DIR, archetype)
    return load_building_config(base_dir)


def save(config, archetype):
    """Raises pydantic.ValidationError if `config` fails BuildingConfig's own
    validators -- callers should catch this and surface it in the UI rather
    than letting a broken config silently reach disk."""
    base_dir = os.path.join(BUILDING_INFO_DIR, archetype)
    save_building_config(config, base_dir)


def new_from_template(archetype_name, template_archetype):
    """Loads `template_archetype`'s config as a starting point for a new
    archetype named `archetype_name`, WITHOUT writing anything to disk --
    caller edits the in-memory copy and calls save() explicitly. This is v1's
    only path to a "new" archetype: cloning an existing one's full config
    (all shape-consistent by construction) rather than building one from a
    blank slate, which the plan defers to v2 (it needs the eigen-analysis
    bootstrap step for Baseline_archetype_info_w_periods.json's Periods
    field)."""
    config = load(template_archetype)
    data = config.model_dump(mode="json")
    data["building_id"] = archetype_name
    return BuildingConfig(**data)
