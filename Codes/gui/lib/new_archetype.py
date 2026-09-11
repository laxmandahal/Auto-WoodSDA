# -*- coding: utf-8 -*-
"""
Builds a brand-new archetype's `BuildingConfig` from a wizard's simple inputs
(number of stories, footprint, and a per-direction wall-line skeleton --
number of grid lines and number of walls per line), plus the two catalog
entries every archetype needs beyond its own building_config.yaml:
`Buildings_input_info.csv` (site/seismic row) and `Databases/
Baseline_archetype_info_w_periods.json` (Directions/wall_line_names/
num_walls_per_wallLine/Periods).

Scope (confirmed with the user): no eigen analysis here. The fundamental
period is estimated with ASCE 7's low-rise shortcut T = 0.1 * NumStories --
only that value (mode 1) and mode 3 are ever actually read downstream
(utils_opensees.py::defineDamping3DModel's two-point Rayleigh damping);
modes 2/4 are stored only for catalog-format consistency with the other 12
entries and use a simple decreasing-ratio estimate.

Every value this module fills in beyond the wall-line skeleton itself
(materials, loads, design constraints) is a flat placeholder seeded from a
real, already-validated archetype (s1_48x32) -- not a computed engineering
value. The wizard page makes this explicit to the user; review each one in
the Archetype Editor before running a real design.
"""

import json
import os
import sys

import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_GUI_DIR = os.path.dirname(_THIS_DIR)
_CODES_DIR = os.path.dirname(_GUI_DIR)
ROOT_DIR = os.path.dirname(_CODES_DIR)
SCHEMA_DIR = os.path.join(_CODES_DIR, "schema")
BUILDING_INFO_DIR = os.path.join(ROOT_DIR, "BuildingInfo")
BUILDINGS_INPUT_INFO_CSV = os.path.join(ROOT_DIR, "Buildings_input_info.csv")
BASELINE_JSON_PATH = os.path.join(ROOT_DIR, "Databases", "Baseline_archetype_info_w_periods.json")

if SCHEMA_DIR not in sys.path:
    sys.path.append(SCHEMA_DIR)

from building_config import BuildingConfig  # noqa: E402

# Flat placeholder wall-line defaults, seeded from BuildingInfo/s1_48x32's gridA/grid1 --
# a real, already-designed, already-validated archetype. Not computed from the wizard's
# geometry; the wizard's own UI flags every one of these as "review before real design."
_WALL_LINE_MATERIAL_DEFAULTS = dict(
    initial_moisture_content=15.0,
    final_moisture_content=10.0,
    wood_modulus_of_elasticity=1700000.0,
    nail_spacing=3.0,
    nail_size="10d",
    panel_thickness="15/32in",
    take_up_deflection=0.03,
    chord_area=105.0,
    sheathing_material_type="",
    sheathing_type="",
)
_WALL_LINE_DESIGN_CONSTRAINT_DEFAULTS = dict(
    user_defined_drift_limit=0.02,
    user_defined_dc_ratio=0.9,
    user_defined_dc_ratio_flag_tiedown=False,
    user_defined_dc_ratio_tiedown=0.9,
    tie_down_system_flag=True,
)
_RIGID_DIAPHRAGM_DEFAULTS = dict(
    accidental_torsion_ex=90.0,
    torsional_irregularity_ax=1.25,
    redundancy_factor=1.3,
)
_TRIBUTARY_WIDTH_DEFAULT = 48.0  # in -- flat placeholder, see module docstring
_SHEAR_WALL_LOAD_DEFAULT = 8.0  # klf -- flat placeholder, matches s1_48x32's order of magnitude

_STATIC_ANALYSIS_DEFAULTS = dict(pushover_increment=0.001, pushover_x_drift=10.0, pushover_z_drift=10.0)
_DYNAMIC_ANALYSIS_DEFAULTS = dict(
    collapse_drift_limit=0.1, demolition_drift_limit=0.01, damping_model="TangentRayleigh", damping_ratio=0.05
)


def archetype_id_conflicts(archetype_id):
    """Returns a list of human-readable reasons `archetype_id` can't be used, or
    [] if it's free. Checked against all three places a new archetype needs a
    unique, consistent name: BuildingInfo/, Buildings_input_info.csv, and the
    Baseline JSON catalog (kept identical across all three -- see PR #14, which
    fixed the exact bug that comes from letting BuildingID and Layout Type
    diverge)."""
    reasons = []
    if not archetype_id or not archetype_id.strip():
        reasons.append("Archetype ID can't be empty.")
        return reasons
    if any(c in archetype_id for c in r'/\:*?"<>| '):
        reasons.append("Archetype ID can't contain spaces or path characters (/ \\ : * ? \" < > |).")
    if os.path.isdir(os.path.join(BUILDING_INFO_DIR, archetype_id)):
        reasons.append(f"BuildingInfo/{archetype_id}/ already exists.")
    if os.path.isfile(BUILDINGS_INPUT_INFO_CSV):
        df = pd.read_csv(BUILDINGS_INPUT_INFO_CSV)
        if (df["BuildingID"] == archetype_id).any() or (df["Layout Type"] == archetype_id).any():
            reasons.append(f"{archetype_id!r} is already used as a BuildingID or Layout Type in Buildings_input_info.csv.")
    if os.path.isfile(BASELINE_JSON_PATH):
        with open(BASELINE_JSON_PATH) as f:
            if archetype_id in json.load(f):
                reasons.append(f"{archetype_id!r} is already a key in Baseline_archetype_info_w_periods.json.")
    return reasons


def compute_periods(number_of_stories):
    """T1 = 0.1 * N (ASCE 7's low-rise approximate-period shortcut, per the
    user's own simplification -- no eigen analysis). Modes 2/4 are never read
    downstream (only indices 0 and 2 are -- see module docstring); a simple
    decreasing-ratio estimate (T1/3, T1/5, T1/7) keeps the stored shape
    consistent with the other 12 catalog entries."""
    t1 = 0.1 * number_of_stories
    return [t1, t1 / 3, t1 / 5, t1 / 7]


def line_names(direction, count):
    if direction == "X":
        return [f"grid{chr(ord('A') + i)}" for i in range(count)]
    return [f"grid{i + 1}" for i in range(count)]


def _evenly_spaced(span, count):
    """count fixed coordinates spread across [0, span], edges included (a
    single line defaults to mid-span)."""
    if count == 1:
        return [span / 2]
    return [span * i / (count - 1) for i in range(count)]


def build_skeleton(footprint_x, footprint_z, x_line_count, x_wall_counts, z_line_count, z_wall_counts):
    """Wall-line skeleton only: names, fixed coordinates, per-wall positions.
    `x_wall_counts`/`z_wall_counts` are per-line lists (one wall count per grid
    line -- lines don't have to match each other). X-direction lines are
    pinned to a fixed Z coordinate and span the X footprint; Z-direction lines
    are pinned to a fixed X coordinate and span the Z footprint (confirmed
    against BuildingInfo/MFD6B and s1_48x32's real panel-coordinate data).

    Returns a dict with enough information for both `build_config` (below) and
    the Baseline JSON catalog entry (Directions/wall_line_names/
    num_walls_per_wallLine, X lines first then Z/"Y" lines, matching every
    existing catalog entry's ordering)."""
    x_names = line_names("X", x_line_count)
    x_fixed_z = _evenly_spaced(footprint_z, x_line_count)
    z_names = line_names("Z", z_line_count)
    z_fixed_x = _evenly_spaced(footprint_x, z_line_count)

    x_lines = []
    for name, fixed_z, n_walls in zip(x_names, x_fixed_z, x_wall_counts):
        wall_length = footprint_x / n_walls
        positions = [wall_length * (i + 0.5) for i in range(n_walls)]  # wall centers
        x_lines.append(dict(name=name, fixed_coord=fixed_z, n_walls=n_walls,
                             wall_length=wall_length, positions=positions))

    z_lines = []
    for name, fixed_x, n_walls in zip(z_names, z_fixed_x, z_wall_counts):
        wall_length = footprint_z / n_walls
        positions = [wall_length * (i + 0.5) for i in range(n_walls)]
        z_lines.append(dict(name=name, fixed_coord=fixed_x, n_walls=n_walls,
                             wall_length=wall_length, positions=positions))

    return dict(x_lines=x_lines, z_lines=z_lines)


def _wall_line_dict(line, direction, n_stories, column_offset):
    """`column_offset` is this line's starting column in the archetype-wide
    x_panels/z_panels matrices (design_outputs) -- i.e. the total wall count
    of every X-or-Z-direction line before this one, in the same concatenation
    order build_config uses for x_panel_x_coords/z_panel_x_coords. Required
    for `pinching4_index` to be correct: FinalShearWallDesign_allFloors.py
    uses it as `col = pinching4_index[story][wall]` to index directly into
    those archetype-wide matrices (not this wall line's own local wall
    index) -- confirmed the hard way: a naive per-line-local index (0, 1, ...
    repeated for every line) silently let each line overwrite column 0's
    design instead of its own."""
    n_walls = line["n_walls"]
    wall_lengths_row = [line["wall_length"]] * n_walls
    moment_arm = [abs(p - line["wall_length"] * n_walls / 2) for p in line["positions"]]
    tributary_load_ratio = [1.0 / n_walls] * n_walls
    pinching4_row = [column_offset + j for j in range(n_walls)]
    return dict(
        name=line["name"],
        direction=direction,
        geometry=dict(
            wall_lengths=[wall_lengths_row[:] for _ in range(n_stories)],
            pinching4_index=[pinching4_row[:] for _ in range(n_stories)],
            tributary_length=[wall_lengths_row[:] for _ in range(n_stories)],
            tributary_width=[[_TRIBUTARY_WIDTH_DEFAULT] * n_walls for _ in range(n_stories)],
        ),
        loads=dict(
            shear_wall_load=[[_SHEAR_WALL_LOAD_DEFAULT] * n_walls for _ in range(n_stories)],
            tributary_load_ratio=tributary_load_ratio,
        ),
        material_properties=dict(
            nail_spacing=[[_WALL_LINE_MATERIAL_DEFAULTS["nail_spacing"]] * n_walls for _ in range(n_stories)],
            nail_size=[[_WALL_LINE_MATERIAL_DEFAULTS["nail_size"]] * n_walls for _ in range(n_stories)],
            panel_thickness=[[_WALL_LINE_MATERIAL_DEFAULTS["panel_thickness"]] * n_walls for _ in range(n_stories)],
            take_up_deflection=[_WALL_LINE_MATERIAL_DEFAULTS["take_up_deflection"]] * n_stories,
            chord_area=[_WALL_LINE_MATERIAL_DEFAULTS["chord_area"]] * n_stories,
            initial_moisture_content=_WALL_LINE_MATERIAL_DEFAULTS["initial_moisture_content"],
            final_moisture_content=_WALL_LINE_MATERIAL_DEFAULTS["final_moisture_content"],
            wood_modulus_of_elasticity=_WALL_LINE_MATERIAL_DEFAULTS["wood_modulus_of_elasticity"],
            sheathing_material_type=_WALL_LINE_MATERIAL_DEFAULTS["sheathing_material_type"],
            sheathing_type=_WALL_LINE_MATERIAL_DEFAULTS["sheathing_type"],
        ),
        design_constraints=dict(_WALL_LINE_DESIGN_CONSTRAINT_DEFAULTS),
        rigid_diaphragm_assumption=dict(
            moment_arm=moment_arm,
            **_RIGID_DIAPHRAGM_DEFAULTS,
        ),
    )


def build_config(
    archetype_id,
    number_of_stories,
    story_height,
    footprint_x,
    footprint_z,
    skeleton,
    floor_weight,
    leaning_column_load,
    interior_wall_weight,
    wall_material,
):
    """Assembles the full BuildingConfig dict and returns a validated
    `BuildingConfig` instance -- construction runs the real shape-consistency
    validator, so a mistake anywhere surfaces as the same `ValidationError`
    every other path through this schema raises. `design_outputs.x_panels`/
    `z_panels` length/height are seeded with nominal pre-design values (see
    below) -- `ComputeDesignForce.py` requires them non-None even for the
    first design run; `FinalShearWallDesign_allFloors.py` overwrites them with
    the real designed values once `run_designModule.py` runs for this id."""
    n = number_of_stories
    n_floor = n + 1

    x_lines = skeleton["x_lines"]
    z_lines = skeleton["z_lines"]

    # Leaning column grid: one node per (X-line fixed-Z) x (Z-line fixed-X) intersection,
    # replicated at every floor level -- matches how s1_48x32/MFD6B's real leaning-column
    # grids are laid out (confirmed by reading their geometry.leaning_column_node_x/z).
    tags, xs, zs = [], [], []
    for fi in range(n_floor):
        row_tags, row_xs, row_zs = [], [], []
        for zline in z_lines:
            for xline in x_lines:
                row_tags.append((fi + 1) * 1000 + len(row_tags) * 100)
                row_xs.append(zline["fixed_coord"])
                row_zs.append(xline["fixed_coord"])
        tags.append(row_tags)
        xs.append(row_xs)
        zs.append(row_zs)
    n_columns = len(tags[0])

    x_panel_x_coords, x_panel_z_coords, n_x_panels = [], [], []
    x_panel_length_row, x_panel_height_row = [], []
    for xline in x_lines:
        x_panel_length_row.extend([xline["wall_length"]] * xline["n_walls"])
        x_panel_height_row.extend([story_height] * xline["n_walls"])
    for _ in range(n):
        row_x, row_z = [], []
        for xline in x_lines:
            row_x.extend(xline["positions"])
            row_z.extend([xline["fixed_coord"]] * xline["n_walls"])
        x_panel_x_coords.append(row_x)
        x_panel_z_coords.append(row_z)
        n_x_panels.append(len(row_x))

    z_panel_x_coords, z_panel_z_coords, n_z_panels = [], [], []
    z_panel_length_row, z_panel_height_row = [], []
    for zline in z_lines:
        z_panel_length_row.extend([zline["wall_length"]] * zline["n_walls"])
        z_panel_height_row.extend([story_height] * zline["n_walls"])
    for _ in range(n):
        row_x, row_z = [], []
        for zline in z_lines:
            row_x.extend([zline["fixed_coord"]] * zline["n_walls"])
            row_z.extend(zline["positions"])
        z_panel_x_coords.append(row_x)
        z_panel_z_coords.append(row_z)
        n_z_panels.append(len(row_x))

    _x_wall_lines, _offset = [], 0
    for xline in x_lines:
        _x_wall_lines.append(_wall_line_dict(xline, "X", n, _offset))
        _offset += xline["n_walls"]

    _y_wall_lines, _offset = [], 0
    for zline in z_lines:
        _y_wall_lines.append(_wall_line_dict(zline, "Y", n, _offset))
        _offset += zline["n_walls"]

    data = dict(
        building_id=archetype_id,
        geometry=dict(
            number_of_stories=n,
            story_heights=[story_height] * n,
            floor_max_x_dimension=[footprint_x] * n_floor,
            floor_max_z_dimension=[footprint_z] * n_floor,
            floor_areas=[footprint_x * footprint_z] * n_floor,
            leaning_column_node_tags=tags,
            leaning_column_node_x=xs,
            leaning_column_node_z=zs,
            n_x_panels=n_x_panels,
            n_z_panels=n_z_panels,
            x_panel_x_coords=x_panel_x_coords,
            x_panel_z_coords=x_panel_z_coords,
            z_panel_x_coords=z_panel_x_coords,
            z_panel_z_coords=z_panel_z_coords,
        ),
        loads=dict(
            floor_weights=[floor_weight] * n,
            live_loads=[0.000345] * 4,  # flat placeholder; schema-decoupled from story count
            leaning_column_loads=[[leaning_column_load] * n_columns for _ in range(n)],
            interior_wall_weight=interior_wall_weight,
        ),
        static_analysis=dict(_STATIC_ANALYSIS_DEFAULTS),
        dynamic_analysis=dict(_DYNAMIC_ANALYSIS_DEFAULTS),
        x_wall_lines=_x_wall_lines,
        y_wall_lines=_y_wall_lines,
        # ComputeDesignForce.py::read_in_txt_inputs (the DESIGN module itself, not just the
        # structural module) raises ValueError if design_outputs.x_panels/z_panels.length is
        # None -- confirmed the hard way: a from-scratch archetype with no prior design has
        # nothing else to supply this. MFD6B/s1_48x32 never hit this because
        # migrate_txt_to_yaml.py carried over a real prior (legacy-Tcl-era) design; a
        # genuinely new layout has none. Seed nominal pre-design panel length/height (each
        # wall's own skeleton length, story height) in the same per-story panel ordering as
        # x_panel_x_coords/z_panel_x_coords above -- this is exactly what a real, un-designed
        # archetype's "nominal" panel size would be before FinalShearWallDesign_allFloors.py
        # overwrites it with the actual designed values.
        #
        # material_number needs a `wall_material`-keyed (+ "default") entry too --
        # FinalShearWallDesign_allFloors.py requires it present (any placeholder int; every
        # column belonging to an actual wall gets overwritten in place during the real design,
        # cell by cell, indexed by each wall line's pinching4_index -- see _wall_line_dict).
        design_outputs=dict(
            x_panels=dict(length=[x_panel_length_row[:] for _ in range(n)],
                          height=[x_panel_height_row[:] for _ in range(n)],
                          material_number={
                              wall_material: [[1] * len(x_panel_length_row) for _ in range(2 * n)],
                              "default": [[1] * len(x_panel_length_row) for _ in range(2 * n)],
                          }),
            z_panels=dict(length=[z_panel_length_row[:] for _ in range(n)],
                          height=[z_panel_height_row[:] for _ in range(n)],
                          material_number={
                              wall_material: [[1] * len(z_panel_length_row) for _ in range(2 * n)],
                              "default": [[1] * len(z_panel_length_row) for _ in range(2 * n)],
                          }),
        ),
    )
    return BuildingConfig(**data)


def save_new_archetype(config, archetype_id):
    """config_io.save() assumes BuildingInfo/<archetype>/ already exists (it
    only ever overwrote an existing archetype in v1) -- create it first."""
    from loader import save_building_config  # local import: SCHEMA_DIR is appended above

    base_dir = os.path.join(BUILDING_INFO_DIR, archetype_id)
    os.makedirs(base_dir, exist_ok=True)
    save_building_config(config, base_dir)


def append_csv_row(archetype_id, site_class, latitude, longitude, wall_material, seismic_weight,
                    allowable_drift=0.02, design_year=2020):
    """Appends one row to Buildings_input_info.csv. BuildingID and Layout Type
    are kept identical to `archetype_id` (see archetype_id_conflicts' docstring
    -- avoids the exact BuildingID-vs-Layout-Type mismatch fixed in PR #14).
    Risk Category/R/Cd/Ie/Ss(g)/S1(g) are left blank, matching every existing
    row -- check_and_complete_inputs() auto-fills them (Ss/S1 via the USGS API
    from Latitude/Longitude) the first time the design module runs.

    Reads the whole CSV and rewrites it with the new row via pandas, rather
    than a raw file append -- the file doesn't reliably end with a trailing
    newline (confirmed: appending a raw line the first time this ran landed
    on the same line as the previous row), and the table is small enough that
    a full rewrite is simplest and avoids that class of bug entirely."""
    fieldnames = [
        "BuildingID", "Layout Type", "SiteID", "Latitude", "Longitude", "Site Class",
        "Risk Category", "R", "Cd", "Ie", "Allowable Drift", "Design Year", "Ss(g)", "S1(g)",
        "wallMaterial", "seismicWeight",
    ]
    row = {
        "BuildingID": archetype_id, "Layout Type": archetype_id, "SiteID": 1,
        "Latitude": latitude, "Longitude": longitude, "Site Class": site_class,
        "Risk Category": "", "R": "", "Cd": "", "Ie": "",
        "Allowable Drift": allowable_drift, "Design Year": design_year,
        "Ss(g)": "", "S1(g)": "", "wallMaterial": wall_material, "seismicWeight": seismic_weight,
    }
    if os.path.isfile(BUILDINGS_INPUT_INFO_CSV):
        df = pd.read_csv(BUILDINGS_INPUT_INFO_CSV)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row], columns=fieldnames)
    df.to_csv(BUILDINGS_INPUT_INFO_CSV, index=False)


def append_baseline_json_entry(archetype_id, skeleton, number_of_stories):
    """Appends one key to Databases/Baseline_archetype_info_w_periods.json,
    in the same shape as the other 12 entries: X lines first, then Z/"Y"
    lines (matching Codes/run_designModule.py's baseline_building_info[
    layoutID] lookup)."""
    directions = ["X"] * len(skeleton["x_lines"]) + ["Y"] * len(skeleton["z_lines"])
    wall_line_names = [ln["name"] for ln in skeleton["x_lines"]] + [ln["name"] for ln in skeleton["z_lines"]]
    num_walls_per_wall_line = ([ln["n_walls"] for ln in skeleton["x_lines"]]
                                + [ln["n_walls"] for ln in skeleton["z_lines"]])

    with open(BASELINE_JSON_PATH) as f:
        catalog = json.load(f)
    catalog[archetype_id] = {
        "Num Story": number_of_stories,
        "Directions": directions,
        "wall_line_names": wall_line_names,
        "num_walls_per_wallLine": num_walls_per_wall_line,
        "Periods": compute_periods(number_of_stories),
    }
    with open(BASELINE_JSON_PATH, "w") as f:
        json.dump(catalog, f, indent=2)
        f.write("\n")
