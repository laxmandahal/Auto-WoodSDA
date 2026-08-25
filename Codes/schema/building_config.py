# -*- coding: utf-8 -*-
"""
Unified schema for autoWoodSDA building input data.

Replaces the scattered `BuildingInfo/<archetype>/` tree of ad hoc, whitespace-
delimited .txt files with a single validated `BuildingConfig`, serialized as
one YAML file per archetype (`BuildingInfo/<archetype>/building_config.yaml`).
This is the single source of truth read by both the design module
(`Codes/designModule/`) and the structural/modeling module
(`Codes/structuralModule/`), which previously parsed the same underlying data
via two independent, hand-written `read_in_txt_inputs()` implementations.

Units are preserved exactly as in the original .txt inputs (inches, kips,
ksi, klf, psf) -- no unit conversion happens in this schema.

Two shapes of per-floor data exist in the source files:
  - "per story" quantities have `number_of_stories` rows (e.g. story
    heights, wood panel coordinates, wall lengths).
  - "per floor level" quantities have `number_of_stories + 1` rows, one for
    the ground level plus each story above it (floor areas, leaning column
    node coordinates/tags).
"""

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

Matrix = List[List[float]]
IntMatrix = List[List[int]]
StrMatrix = List[List[str]]


class Geometry(BaseModel):
    number_of_stories: int = Field(gt=0)
    story_heights: List[float]  # per story, inches
    floor_max_x_dimension: List[float]  # per floor level (number_of_stories + 1), inches
    floor_max_z_dimension: List[float]  # per floor level (number_of_stories + 1), inches
    floor_areas: List[float]  # per floor level (number_of_stories + 1)
    leaning_column_node_tags: IntMatrix  # per floor level x n_nodes
    leaning_column_node_x: Matrix  # per floor level x n_nodes
    leaning_column_node_z: Matrix  # per floor level x n_nodes
    n_x_panels: List[int]  # per story
    n_z_panels: List[int]  # per story
    x_panel_x_coords: Matrix  # per story x n_x_panels, inches
    x_panel_z_coords: Matrix
    z_panel_x_coords: Matrix  # per story x n_z_panels, inches
    z_panel_z_coords: Matrix


class Loads(BaseModel):
    floor_weights: List[float]  # per story, kips
    live_loads: List[float]  # ksi; NOT story-indexed (verified: never sliced by
    # story downstream, and s1_48x32's 1-story archetype still carries 4 values,
    # same length as the 4-story MFD6B archetype) -- length not validated against story count
    leaning_column_loads: Matrix  # per story x n_columns, kips
    interior_wall_weight: float  # psf


class StaticAnalysisParameters(BaseModel):
    pushover_increment: float
    pushover_x_drift: float
    pushover_z_drift: float


class DynamicAnalysisParameters(BaseModel):
    collapse_drift_limit: float
    demolition_drift_limit: float
    damping_model: str  # e.g. "TangentRayleigh"
    damping_ratio: float


class WallLineGeometry(BaseModel):
    wall_lengths: Matrix  # per story x n_walls, inches (pre-design nominal length)
    pinching4_index: IntMatrix  # per story x n_walls
    tributary_length: Matrix  # per story x n_walls
    tributary_width: Matrix  # per story x n_walls


class WallLineLoads(BaseModel):
    shear_wall_load: Matrix  # per story x n_walls, klf
    tributary_load_ratio: List[float]  # n_walls


class WallLineMaterialProperties(BaseModel):
    initial_moisture_content: float
    final_moisture_content: float
    wood_modulus_of_elasticity: float
    nail_spacing: Matrix  # per story x n_walls
    nail_size: StrMatrix  # per story x n_walls, e.g. "10d" (verified: ShearWallDesignClass.py
    # reshapes this file into a (story, wall) matrix, not a scalar, despite its singular name)
    panel_thickness: StrMatrix  # per story x n_walls, e.g. "15/32in" (same as nail_size)
    take_up_deflection: List[float]  # per story
    chord_area: List[float]  # per story
    sheathing_material_type: str
    sheathing_type: str


class WallLineDesignConstraints(BaseModel):
    user_defined_drift_limit: float
    user_defined_dc_ratio: float
    user_defined_dc_ratio_flag_tiedown: bool
    user_defined_dc_ratio_tiedown: float
    tie_down_system_flag: bool
    # Resolves the on-disk duplication of tieDownSystemFlag.txt under both
    # DesignConstraints/ and MaterialProperties/ -- single field here; the
    # migration script asserts both copies agree before collapsing them.


class RigidDiaphragmAssumption(BaseModel):
    accidental_torsion_ex: float  # scalar, inches
    torsional_irregularity_ax: float  # scalar
    redundancy_factor: float  # scalar
    moment_arm: List[float]  # per wall (n_walls), inches


class WallLine(BaseModel):
    name: str  # e.g. "gridA", "grid1"
    direction: Literal["X", "Y"]
    geometry: WallLineGeometry
    loads: WallLineLoads
    material_properties: WallLineMaterialProperties
    design_constraints: WallLineDesignConstraints
    rigid_diaphragm_assumption: RigidDiaphragmAssumption
    envelope_shear_wall_demand: Optional[Matrix] = None  # only when envelope-based design is used


class PanelDesignOutputs(BaseModel):
    """Populated by the design module (FinalShearWallDesign_allFloors.py) once a
    design has run for this archetype; consumed by the structural module.
    Length/height/material_number are written together through one path so
    they cannot drift apart the way they could when they were separate .txt
    files with no shared write step.
    """

    length: Optional[Matrix] = None  # per story x n_panels, inches
    height: Optional[Matrix] = None  # per story x n_panels, inches
    material_number: Optional[Dict[str, IntMatrix]] = None
    # dict key = finish variant, e.g. "default", "Stucco_GWB", "HWS_GWB", "Stucco_Plaster".
    # Each matrix has 2 * number_of_stories rows: rows [2*i, 2*i+1] are the
    # "outer"/"inner" material assignment for story i (see
    # structuralModule/utils_opensees.py's XPanelMaterial[2*i, j] / [2*i+1, j] usage).


class DesignOutputs(BaseModel):
    x_panels: PanelDesignOutputs = Field(default_factory=PanelDesignOutputs)
    z_panels: PanelDesignOutputs = Field(default_factory=PanelDesignOutputs)


class BuildingConfig(BaseModel):
    building_id: str
    geometry: Geometry
    loads: Loads
    static_analysis: StaticAnalysisParameters
    dynamic_analysis: DynamicAnalysisParameters
    x_wall_lines: List[WallLine]
    y_wall_lines: List[WallLine]
    design_outputs: DesignOutputs = Field(default_factory=DesignOutputs)

    @model_validator(mode="after")
    def _check_shape_consistency(self) -> "BuildingConfig":
        n = self.geometry.number_of_stories
        n_floor = n + 1
        g = self.geometry
        errors: List[str] = []

        def require_len(label: str, seq, expected: int) -> None:
            if len(seq) != expected:
                errors.append(f"{label}: expected {expected} entries, got {len(seq)}")

        require_len("geometry.story_heights", g.story_heights, n)
        require_len("geometry.floor_max_x_dimension", g.floor_max_x_dimension, n_floor)
        require_len("geometry.floor_max_z_dimension", g.floor_max_z_dimension, n_floor)
        require_len("geometry.floor_areas", g.floor_areas, n_floor)
        require_len("geometry.leaning_column_node_tags", g.leaning_column_node_tags, n_floor)
        require_len("geometry.leaning_column_node_x", g.leaning_column_node_x, n_floor)
        require_len("geometry.leaning_column_node_z", g.leaning_column_node_z, n_floor)
        require_len("geometry.n_x_panels", g.n_x_panels, n)
        require_len("geometry.n_z_panels", g.n_z_panels, n)
        require_len("geometry.x_panel_x_coords", g.x_panel_x_coords, n)
        require_len("geometry.x_panel_z_coords", g.x_panel_z_coords, n)
        require_len("geometry.z_panel_x_coords", g.z_panel_x_coords, n)
        require_len("geometry.z_panel_z_coords", g.z_panel_z_coords, n)

        require_len("loads.floor_weights", self.loads.floor_weights, n)
        # loads.live_loads is intentionally not story-indexed -- see Loads model comment
        require_len("loads.leaning_column_loads", self.loads.leaning_column_loads, n)

        for wall_lines, direction in ((self.x_wall_lines, "X"), (self.y_wall_lines, "Y")):
            for wl in wall_lines:
                if wl.direction != direction:
                    errors.append(
                        f"wall line {wl.name}: direction={wl.direction!r} does not match "
                        f"its containing list ({direction}_wall_lines)"
                    )
                require_len(f"{wl.name}.geometry.wall_lengths", wl.geometry.wall_lengths, n)
                require_len(f"{wl.name}.geometry.pinching4_index", wl.geometry.pinching4_index, n)
                require_len(f"{wl.name}.geometry.tributary_length", wl.geometry.tributary_length, n)
                require_len(f"{wl.name}.geometry.tributary_width", wl.geometry.tributary_width, n)
                require_len(f"{wl.name}.loads.shear_wall_load", wl.loads.shear_wall_load, n)
                require_len(f"{wl.name}.material_properties.nail_spacing", wl.material_properties.nail_spacing, n)
                require_len(f"{wl.name}.material_properties.nail_size", wl.material_properties.nail_size, n)
                require_len(
                    f"{wl.name}.material_properties.panel_thickness", wl.material_properties.panel_thickness, n
                )

                n_walls = len(wl.geometry.wall_lengths[0]) if wl.geometry.wall_lengths else 0
                require_len(f"{wl.name}.loads.tributary_load_ratio", wl.loads.tributary_load_ratio, n_walls)
                require_len(
                    f"{wl.name}.rigid_diaphragm_assumption.moment_arm",
                    wl.rigid_diaphragm_assumption.moment_arm,
                    n_walls,
                )

        for panels, label in ((self.design_outputs.x_panels, "x_panels"), (self.design_outputs.z_panels, "z_panels")):
            if panels.length is not None:
                require_len(f"design_outputs.{label}.length", panels.length, n)
            if panels.height is not None:
                require_len(f"design_outputs.{label}.height", panels.height, n)
            if panels.material_number is not None:
                for finish, mat in panels.material_number.items():
                    require_len(f"design_outputs.{label}.material_number[{finish}]", mat, 2 * n)

        if errors:
            raise ValueError("BuildingConfig shape validation failed:\n  " + "\n  ".join(errors))
        return self
