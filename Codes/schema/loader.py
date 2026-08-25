# -*- coding: utf-8 -*-
"""
Shared loader for `BuildingConfig` (see building_config.py), used by both
`designModule/ComputeDesignForce.py` and `structuralModule/BuildingModelClass.py`
in place of their previous independent `np.genfromtxt(...)` reads of the
`BuildingInfo/<archetype>/` .txt tree.

`as_matrix`/`as_vector` intentionally reproduce the exact array shape
`np.genfromtxt` would have produced when reading the original .txt files --
including its automatic squeezing of a 2-D result down to 1-D or a 0-D
scalar whenever a row/column dimension is 1. Both consumer files have
existing `if self.numberOfStories == 1: ...reshape(...)` branches tuned to
that squeeze behavior; reproducing it here means those branches keep working
unmodified, and this change stays confined to *how the numbers get into the
numpy arrays*, not what shape they end up in.
"""

import os

import numpy as np
import yaml

from building_config import BuildingConfig

CONFIG_FILENAME = "building_config.yaml"


def config_path(base_directory):
    return os.path.join(base_directory, CONFIG_FILENAME)


def load_building_config(base_directory):
    with open(config_path(base_directory)) as f:
        data = yaml.safe_load(f)
    return BuildingConfig(**data)


def save_building_config(config, base_directory):
    # Pydantic doesn't re-validate on in-place attribute mutation by default, so a caller that
    # mutates a nested field (e.g. FinalShearWallDesign_allFloors.py writing back a new
    # design_outputs matrix) could otherwise persist a shape that violates the schema's
    # consistency checks without ever being told. Round-tripping through the constructor here
    # re-runs those checks right before anything hits disk.
    validated = BuildingConfig(**config.model_dump(mode="json"))
    with open(config_path(base_directory), "w") as f:
        yaml.safe_dump(validated.model_dump(mode="json"), f, sort_keys=False, default_flow_style=False)


def as_matrix(nested_list):
    """list[list[...]] -> ndarray, squeezed the way np.genfromtxt squeezes a
    2-D text block: a single row or single column collapses to 1-D, and a
    single row-and-column collapses to a 0-D array.

    The 0-D case uses .reshape(()) rather than plain arr[0, 0] indexing:
    the latter returns a numpy scalar (np.float64), which LOOKS
    interchangeable with a true 0-D ndarray (same .shape == (), same
    arithmetic) but isn't -- np.insert(np.float64(x), 0, 0) silently drops
    x instead of inserting into it, which is exactly the array
    np.genfromtxt('storyHeights.txt') would give a single-story archetype
    and exactly what ComputeDesignForce.py's self.floorHeights computation
    does with it. Confirmed via direct comparison: arr[0,0] broke
    single-story seismic force calculations silently (empty array, no
    exception); .reshape(()) reproduces genfromtxt's real 0-D ndarray."""
    arr = np.array(nested_list, dtype=float)
    if arr.shape[0] == 1 and arr.shape[1] == 1:
        return arr.reshape(())
    if arr.shape[0] == 1:
        return arr[0]
    if arr.shape[1] == 1:
        return arr[:, 0]
    return arr


def as_vector(flat_list):
    """list[...] -> ndarray, squeezed the way np.genfromtxt squeezes a
    single-column/single-line text block: a single value collapses to a
    0-D array. See as_matrix's docstring for why .reshape(()) is used
    instead of arr[0] here."""
    arr = np.array(flat_list, dtype=float)
    if arr.shape[0] == 1:
        return arr.reshape(())
    return arr
