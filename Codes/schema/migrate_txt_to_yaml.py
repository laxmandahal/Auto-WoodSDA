# -*- coding: utf-8 -*-
"""
One-time migration: reads an existing `BuildingInfo/<archetype>/` .txt tree
and emits a single `building_config.yaml` conforming to
`Codes/schema/building_config.BuildingConfig`.

The reader logic mirrors `ComputeSeismicForce.read_in_txt_inputs` (design
module) and `BuildingModel.read_in_txt_inputs` (structural module) -- between
them they cover every file in the inventory. This script does not import
those classes (they require extra runtime args and slice per-wall-line data
via os.chdir side effects); instead it re-reads the same files directly,
normalizing every per-story/per-floor quantity to a real nested list
(`list[list[...]]`) regardless of story count, which removes the
numpy 1-D/2-D reshape special-casing both original readers need for
single-story buildings.

Usage:
    python3 migrate_txt_to_yaml.py <archetype_name>

Writes BuildingInfo/<archetype_name>/building_config.yaml and prints a
round-trip validation report.
"""

import copy
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(__file__))
from building_config import BuildingConfig  # noqa: E402

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
CODE_DIR = os.path.dirname(THIS_DIR)
ROOT_DIR = os.path.dirname(CODE_DIR)
BUILDING_INFO_DIR = os.path.join(ROOT_DIR, "BuildingInfo")
PINCHING4_DIR = os.path.join(ROOT_DIR, "Databases", "Pinching4_parameters")


# ---------------------------------------------------------------------------
# Low-level readers. Each normalizes numpy's "1 row collapses to 1-D" and
# "1 value collapses to 0-D" behavior into the shape the field is documented
# to have in building_config.py, regardless of story/wall count.
# ---------------------------------------------------------------------------

def _read_raw(path):
    return np.genfromtxt(path)


def read_scalar(path):
    return float(np.atleast_1d(_read_raw(path))[0])


def read_int_scalar(path):
    return int(read_scalar(path))


def read_vector(path, expected_len):
    """A field that is conceptually 1-D (per-story or per-wall), stored as a flat list."""
    arr = np.atleast_1d(_read_raw(path))
    values = arr.tolist()
    if len(values) != expected_len:
        raise ValueError(f"{path}: expected {expected_len} values, got {len(values)}: {values}")
    return values


def read_vector_free(path):
    """A 1-D field whose length is NOT tied to story/wall count (currently only
    liveLoads.txt -- confirmed by grep that no consumer slices it by story
    index, and s1_48x32 (1 story) still has 4 values on disk, same as
    4-story MFD6B, so it is not story-indexed)."""
    return np.atleast_1d(_read_raw(path)).tolist()


def read_matrix(path, n_rows):
    """A field that is conceptually 2-D (rows = stories or floor levels), stored as
    list[list[...]] regardless of whether numpy collapsed a single row/column."""
    arr = np.atleast_1d(_read_raw(path))
    if arr.ndim == 1:
        if n_rows == 1:
            matrix = [arr.tolist()]
        else:
            # single column, one value per row
            matrix = [[v] for v in arr.tolist()]
    else:
        matrix = arr.tolist()
    if len(matrix) != n_rows:
        raise ValueError(f"{path}: expected {n_rows} rows, got {len(matrix)}")
    return matrix


def read_text(path):
    with open(path) as f:
        return f.read().strip()


def read_string_matrix(path, n_rows):
    """A field whose consumer (ShearWallDesignClass.py) reads it as a whole-file
    string then `.split()` + `.reshape(n_rows, n_cols)`'s it into a per-story x
    per-wall matrix of tokens (nail size, panel thickness) -- not the flat
    string ComputeDesignForce.py's dead, unused `self.nailSize` attribute
    would suggest."""
    with open(path) as f:
        tokens = f.read().split()
    if len(tokens) % n_rows != 0:
        raise ValueError(f"{path}: {len(tokens)} tokens not evenly divisible by {n_rows} rows")
    n_cols = len(tokens) // n_rows
    return [tokens[i * n_cols:(i + 1) * n_cols] for i in range(n_rows)]


def read_bool(path):
    return bool(round(read_scalar(path)))


# ---------------------------------------------------------------------------
# Section readers
# ---------------------------------------------------------------------------

def read_geometry(base_dir):
    d = os.path.join(base_dir, "Geometry")
    n = read_int_scalar(os.path.join(d, "numberOfStories.txt"))
    n_floor = n + 1

    return n, {
        "number_of_stories": n,
        "story_heights": read_vector(os.path.join(d, "storyHeights.txt"), n),
        "floor_max_x_dimension": read_vector(os.path.join(d, "floorMaximumXDimension.txt"), n_floor),
        "floor_max_z_dimension": read_vector(os.path.join(d, "floorMaximumZDimension.txt"), n_floor),
        "floor_areas": read_vector(os.path.join(d, "floorAreas.txt"), n_floor),
        "leaning_column_node_tags": [
            [int(v) for v in row]
            for row in read_matrix(os.path.join(d, "leaningColumnNodesOpenSeesTags.txt"), n_floor)
        ],
        "leaning_column_node_x": read_matrix(os.path.join(d, "leaningColumnNodesXCoordinates.txt"), n_floor),
        "leaning_column_node_z": read_matrix(os.path.join(d, "leaningColumnNodesZCoordinates.txt"), n_floor),
        "n_x_panels": [int(v) for v in read_vector(os.path.join(d, "numberOfXDirectionWoodPanels.txt"), n)],
        "n_z_panels": [int(v) for v in read_vector(os.path.join(d, "numberOfZDirectionWoodPanels.txt"), n)],
        "x_panel_x_coords": read_matrix(os.path.join(d, "XDirectionWoodPanelsXCoordinates.txt"), n),
        "x_panel_z_coords": read_matrix(os.path.join(d, "XDirectionWoodPanelsZCoordinates.txt"), n),
        "z_panel_x_coords": read_matrix(os.path.join(d, "ZDirectionWoodPanelsXCoordinates.txt"), n),
        "z_panel_z_coords": read_matrix(os.path.join(d, "ZDirectionWoodPanelsZCoordinates.txt"), n),
    }


def read_loads(base_dir, n):
    d = os.path.join(base_dir, "Loads")
    return {
        "floor_weights": read_vector(os.path.join(d, "floorWeights.txt"), n),
        "live_loads": read_vector_free(os.path.join(d, "liveLoads.txt")),
        "leaning_column_loads": read_matrix(os.path.join(d, "leaningcolumnLoads.txt"), n),
        "interior_wall_weight": read_scalar(os.path.join(d, "interiorWallWeights.txt")),
    }


def read_static_analysis(base_dir):
    d = os.path.join(base_dir, "AnalysisParameters", "StaticAnalysis")
    return {
        "pushover_increment": read_scalar(os.path.join(d, "PushoverIncrementSize.txt")),
        "pushover_x_drift": read_scalar(os.path.join(d, "PushoverXDrift.txt")),
        "pushover_z_drift": read_scalar(os.path.join(d, "PushoverZDrift.txt")),
    }


def read_dynamic_analysis(base_dir):
    d = os.path.join(base_dir, "AnalysisParameters", "DynamicAnalysis")
    return {
        "collapse_drift_limit": read_scalar(os.path.join(d, "CollapseDriftLimit.txt")),
        "demolition_drift_limit": read_scalar(os.path.join(d, "DemolitionDriftLimit.txt")),
        "damping_model": read_text(os.path.join(d, "dampingModel.txt")),
        "damping_ratio": read_scalar(os.path.join(d, "dampingRatio.txt")),
    }


def read_wall_line(base_dir, direction, name, n):
    d = os.path.join(base_dir, f"{direction}_direction_wall", name)

    wall_lengths = read_matrix(os.path.join(d, "Geometry", "wallLengths.txt"), n)
    n_walls = len(wall_lengths[0])

    geometry = {
        "wall_lengths": wall_lengths,
        "pinching4_index": [
            [int(v) for v in row]
            for row in read_matrix(os.path.join(d, "Geometry", "pinching4Index.txt"), n)
        ],
        "tributary_length": read_matrix(os.path.join(d, "Geometry", "tribuitaryLength.txt"), n),
        "tributary_width": read_matrix(os.path.join(d, "Geometry", "tribuitaryWidth.txt"), n),
    }

    loads = {
        "shear_wall_load": read_matrix(os.path.join(d, "Loads", "shearWall_load.txt"), n),
        "tributary_load_ratio": read_vector(os.path.join(d, "Loads", "tribuitaryLoadRatio.txt"), n_walls),
    }

    mp_dir = os.path.join(d, "MaterialProperties")
    material_properties = {
        "initial_moisture_content": read_scalar(os.path.join(mp_dir, "initial_moisture_content.txt")),
        "final_moisture_content": read_scalar(os.path.join(mp_dir, "final_moisture_content.txt")),
        "wood_modulus_of_elasticity": read_scalar(os.path.join(mp_dir, "wood_modulusOfElasticity.txt")),
        "nail_spacing": read_matrix(os.path.join(mp_dir, "preferred_nail_spacing.txt"), n),
        "nail_size": read_string_matrix(os.path.join(mp_dir, "preferred_nail_size.txt"), n),
        "panel_thickness": read_string_matrix(os.path.join(mp_dir, "preferred_panel_thickness.txt"), n),
        "take_up_deflection": read_vector(os.path.join(mp_dir, "takeUpDeflection.txt"), n),
        "chord_area": read_vector(os.path.join(mp_dir, "chordArea.txt"), n),
        "sheathing_material_type": read_text(os.path.join(mp_dir, "sheathingMaterialType.txt")),
        "sheathing_type": read_text(os.path.join(mp_dir, "sheathingType.txt")),
    }

    dc_dir = os.path.join(d, "DesignConstraints")
    tie_down_dc = read_bool(os.path.join(dc_dir, "tieDownSystemFlag.txt"))
    tie_down_mp = read_bool(os.path.join(mp_dir, "tieDownSystemFlag.txt"))
    if tie_down_dc != tie_down_mp:
        raise ValueError(
            f"{name}: tieDownSystemFlag.txt disagrees between DesignConstraints/ ({tie_down_dc}) "
            f"and MaterialProperties/ ({tie_down_mp}) -- cannot collapse to one field"
        )
    design_constraints = {
        "user_defined_drift_limit": read_scalar(os.path.join(dc_dir, "userDefinedDriftLimit.txt")),
        "user_defined_dc_ratio": read_scalar(os.path.join(dc_dir, "userDefinedDCRatio.txt")),
        "user_defined_dc_ratio_flag_tiedown": read_bool(os.path.join(dc_dir, "userDefinedDCRatioFlag_TieDown.txt")),
        "user_defined_dc_ratio_tiedown": read_scalar(os.path.join(dc_dir, "userDefinedDCRatio_TieDown.txt")),
        "tie_down_system_flag": tie_down_dc,
    }

    rd_dir = os.path.join(d, "RigidDiaphragmAssumption")
    rigid_diaphragm_assumption = {
        "accidental_torsion_ex": read_scalar(os.path.join(rd_dir, "AccidentalTorsion(ex).txt")),
        "torsional_irregularity_ax": read_scalar(os.path.join(rd_dir, "TorsionalIrregularity(Ax).txt")),
        "redundancy_factor": read_scalar(os.path.join(rd_dir, "RedundancyFactor.txt")),
        "moment_arm": read_vector(os.path.join(rd_dir, "MomentArm.txt"), n_walls),
    }

    envelope_path = os.path.join(d, "envelopeShearWallDemand.txt")
    envelope_demand = read_matrix(envelope_path, n) if os.path.isfile(envelope_path) else None

    return {
        "name": name,
        "direction": direction,
        "geometry": geometry,
        "loads": loads,
        "material_properties": material_properties,
        "design_constraints": design_constraints,
        "rigid_diaphragm_assumption": rigid_diaphragm_assumption,
        "envelope_shear_wall_demand": envelope_demand,
    }


def read_wall_lines(base_dir, direction, n):
    parent = os.path.join(base_dir, f"{direction}_direction_wall")
    names = sorted(
        name for name in os.listdir(parent)
        if os.path.isdir(os.path.join(parent, name)) and not name.startswith(".")
    )
    return [read_wall_line(base_dir, direction, name, n) for name in names]


def read_panel_design_outputs(base_dir, direction, n):
    subdir = "XWoodPanels" if direction == "X" else "YWoodPanels"
    d = os.path.join(base_dir, "StructuralProperties", subdir)

    length_path = os.path.join(d, "length.txt")
    height_path = os.path.join(d, "height.txt")
    length = read_matrix(length_path, n) if os.path.isfile(length_path) else None
    height = read_matrix(height_path, n) if os.path.isfile(height_path) else None

    material_number = {}
    if os.path.isdir(d):
        for fname in sorted(os.listdir(d)):
            if not fname.startswith("Pinching4MaterialNumber") or not fname.endswith(".txt"):
                continue
            stem = fname[: -len(".txt")]
            key = "default" if stem == "Pinching4MaterialNumber" else stem[len("Pinching4MaterialNumber_"):]
            # 2 rows per story: [outer, inner] material assignment (see
            # structuralModule/utils_opensees.py XPanelMaterial[2*i, j] / [2*i+1, j])
            matrix = read_matrix(os.path.join(d, fname), 2 * n)
            material_number[key] = [[int(v) for v in row] for row in matrix]

    return {
        "length": length,
        "height": height,
        "material_number": material_number or None,
    }


def read_building_config(archetype):
    base_dir = os.path.join(BUILDING_INFO_DIR, archetype)
    n, geometry = read_geometry(base_dir)

    config_dict = {
        "building_id": archetype,
        "geometry": geometry,
        "loads": read_loads(base_dir, n),
        "static_analysis": read_static_analysis(base_dir),
        "dynamic_analysis": read_dynamic_analysis(base_dir),
        "x_wall_lines": read_wall_lines(base_dir, "X", n),
        "y_wall_lines": read_wall_lines(base_dir, "Y", n),
        "design_outputs": {
            "x_panels": read_panel_design_outputs(base_dir, "X", n),
            "z_panels": read_panel_design_outputs(base_dir, "Y", n),
        },
    }
    return BuildingConfig(**config_dict)


# ---------------------------------------------------------------------------
# Migration entry point
# ---------------------------------------------------------------------------

def migrate(archetype):
    base_dir = os.path.join(BUILDING_INFO_DIR, archetype)
    out_path = os.path.join(base_dir, "building_config.yaml")

    print(f"Reading BuildingInfo/{archetype}/ ...")
    config = read_building_config(archetype)
    dumped = config.model_dump(mode="json")

    with open(out_path, "w") as f:
        yaml.safe_dump(dumped, f, sort_keys=False, default_flow_style=False)
    print(f"Wrote {out_path}")

    # Round-trip check 1: YAML serialization fidelity.
    with open(out_path) as f:
        reloaded_dict = yaml.safe_load(f)
    reloaded = BuildingConfig(**reloaded_dict)
    if reloaded.model_dump(mode="json") != dumped:
        raise AssertionError("YAML round-trip produced a different BuildingConfig than the original read")
    print("Round-trip check 1/2 OK: YAML reload == in-memory config")

    # Round-trip check 2: independently re-read a sample of raw files directly
    # and confirm the values landed in the config unchanged (catches
    # transcription bugs in this script's readers, independent of the YAML
    # layer above).
    spot_checks = [
        ("geometry.number_of_stories", config.geometry.number_of_stories,
         read_int_scalar(os.path.join(base_dir, "Geometry", "numberOfStories.txt"))),
        ("geometry.story_heights", config.geometry.story_heights,
         read_vector(os.path.join(base_dir, "Geometry", "storyHeights.txt"), config.geometry.number_of_stories)),
        ("loads.floor_weights", config.loads.floor_weights,
         read_vector(os.path.join(base_dir, "Loads", "floorWeights.txt"), config.geometry.number_of_stories)),
    ]
    if config.x_wall_lines:
        wl = config.x_wall_lines[0]
        raw_wall_lengths = read_matrix(
            os.path.join(base_dir, "X_direction_wall", wl.name, "Geometry", "wallLengths.txt"),
            config.geometry.number_of_stories,
        )
        spot_checks.append((f"x_wall_lines[0]({wl.name}).geometry.wall_lengths", wl.geometry.wall_lengths, raw_wall_lengths))

    mismatches = []
    for label, from_config, from_disk in spot_checks:
        if not np.allclose(np.array(from_config, dtype=float), np.array(from_disk, dtype=float)):
            mismatches.append(f"{label}: config={from_config} disk={from_disk}")

    if mismatches:
        raise AssertionError("Round-trip check 2/2 FAILED:\n" + "\n".join(mismatches))
    print("Round-trip check 2/2 OK: spot-checked fields match independent re-read of source files")

    print(f"\nMigration successful for '{archetype}'.")
    print(f"  Stories: {config.geometry.number_of_stories}")
    print(f"  X wall lines: {[w.name for w in config.x_wall_lines]}")
    print(f"  Y wall lines: {[w.name for w in config.y_wall_lines]}")
    print(f"  Design outputs present: x_panels.length={config.design_outputs.x_panels.length is not None}, "
          f"z_panels.length={config.design_outputs.z_panels.length is not None}")
    return config


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python3 {os.path.basename(__file__)} <archetype_name>")
        sys.exit(1)
    migrate(sys.argv[1])
