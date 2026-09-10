# -*- coding: utf-8 -*-
"""
Archetype Editor -- edit an existing archetype's building_config.yaml.

v1 scope (confirmed in planning): editing one of the archetype layouts already
in Databases/Baseline_archetype_info_w_periods.json. No new-layout authoring
here (that needs an eigen-analysis bootstrap step for that catalog's Periods
field -- a v2 addition).

Working state lives in st.session_state as a plain JSON-able dict (not a live
BuildingConfig instance) so every widget can read/write it directly without
fighting Pydantic's validate-on-construct model across Streamlit's rerun-the-
whole-script-per-interaction execution model. A BuildingConfig is only
reconstructed (which re-runs every schema validator) at Validate/Save time.
"""

import os
import sys

import pandas as pd
import streamlit as st

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
_SCHEMA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'schema')
for _d in (_LIB_DIR, _SCHEMA_DIR):
    if _d not in sys.path:
        sys.path.append(_d)

import config_io  # noqa: E402
import geometry_preview  # noqa: E402
import widgets as w  # noqa: E402
from building_config import BuildingConfig  # noqa: E402
from pydantic import ValidationError  # noqa: E402

st.set_page_config(page_title="Archetype Editor", layout="wide")
st.title("Archetype Editor")

# --- Sidebar: pick an archetype, load it into session state ---------------
archetypes = config_io.list_archetypes()
if not archetypes:
    st.error(f"No archetypes with a building_config.yaml found under {config_io.BUILDING_INFO_DIR}")
    st.stop()

chosen = st.sidebar.selectbox("Archetype", archetypes, key="archetype_select")

if st.session_state.get("_loaded_archetype") != chosen:
    cfg = config_io.load(chosen)
    st.session_state["config_dict"] = cfg.model_dump(mode="json")
    st.session_state["_loaded_archetype"] = chosen

cd = st.session_state["config_dict"]
geo = cd["geometry"]
n_stories = geo["number_of_stories"]

tabs = st.tabs(["Overview", "Geometry", "Loads", "Wall Lines", "Analysis Parameters", "Save & Validate"])

# --- Overview ---------------------------------------------------------------
with tabs[0]:
    st.text_input("Building ID", value=cd["building_id"], disabled=True,
                  help="Renaming would require a new BuildingInfo/<id>/ folder -- out of scope for editing.")
    st.number_input("Number of stories", value=n_stories, disabled=True,
                     help="Changing story count would resize every per-story matrix in this "
                          "config -- not supported by the editor; clone a different-story-count "
                          "archetype instead.")

    st.subheader("Story heights & footprint")
    geo["story_heights"] = w.edit_vector(
        "Story height (in)", geo["story_heights"], "story_heights", w.story_labels(n_stories))

    col1, col2 = st.columns(2)
    with col1:
        geo["floor_max_x_dimension"] = w.edit_vector(
            "Max X dimension (in)", geo["floor_max_x_dimension"], "floor_max_x",
            w.floor_labels(n_stories))
    with col2:
        geo["floor_max_z_dimension"] = w.edit_vector(
            "Max Z dimension (in)", geo["floor_max_z_dimension"], "floor_max_z",
            w.floor_labels(n_stories))

    geo["floor_areas"] = w.edit_vector(
        "Floor area", geo["floor_areas"], "floor_areas", w.floor_labels(n_stories))

# --- Geometry (the flagship screen) -----------------------------------------
with tabs[1]:
    story_choice = st.radio("Story", list(range(1, n_stories + 1)), horizontal=True, key="geom_story")
    story_idx = story_choice - 1

    plot_col, edit_col = st.columns([3, 2])

    with edit_col:
        st.markdown(f"**Story {story_choice} panel coordinates**")
        st.caption("X-direction panels (resist force along X)")
        x_df = pd.DataFrame({
            "x (in)": geo["x_panel_x_coords"][story_idx],
            "z (in)": geo["x_panel_z_coords"][story_idx],
        })
        x_edited = st.data_editor(x_df, key=f"x_panels_{story_idx}", use_container_width=True,
                                   num_rows="dynamic")
        geo["x_panel_x_coords"][story_idx] = x_edited["x (in)"].tolist()
        geo["x_panel_z_coords"][story_idx] = x_edited["z (in)"].tolist()
        geo["n_x_panels"][story_idx] = len(x_edited)

        st.caption("Z-direction panels (resist force along Z)")
        z_df = pd.DataFrame({
            "x (in)": geo["z_panel_x_coords"][story_idx],
            "z (in)": geo["z_panel_z_coords"][story_idx],
        })
        z_edited = st.data_editor(z_df, key=f"z_panels_{story_idx}", use_container_width=True,
                                   num_rows="dynamic")
        geo["z_panel_x_coords"][story_idx] = z_edited["x (in)"].tolist()
        geo["z_panel_z_coords"][story_idx] = z_edited["z (in)"].tolist()
        geo["n_z_panels"][story_idx] = len(z_edited)

        st.info("Adding/removing a panel row here changes n_x_panels/n_z_panels for this story "
                "only -- the matching WallLine's wall_lengths etc. on the Wall Lines tab must be "
                "updated to match, or Save & Validate will reject the shape mismatch.")

    with plot_col:
        class _Geo:
            pass
        g = _Geo()
        for k, v in geo.items():
            setattr(g, k, v)
        fig, x_matched, z_matched = geometry_preview.plan_view_figure(
            g, story_idx, cd["x_wall_lines"], cd["y_wall_lines"])
        st.plotly_chart(fig, use_container_width=True)
        if not (x_matched and z_matched):
            st.caption("Note: number of distinct wall-line coordinates doesn't match the "
                       "number of named wall lines on the Wall Lines tab -- lines are shown "
                       "numbered above rather than by name until that's reconciled.")

    with st.expander("3D geometry preview (whole building, wireframe only -- no analysis)"):
        fig3d = geometry_preview.wireframe_3d_figure(g)
        st.plotly_chart(fig3d, use_container_width=True)

# --- Loads -------------------------------------------------------------------
with tabs[2]:
    loads = cd["loads"]
    loads["floor_weights"] = w.edit_vector(
        "Floor weight (kips)", loads["floor_weights"], "floor_weights", w.story_labels(n_stories))
    loads["live_loads"] = w.edit_vector(
        "Live load (ksi)", loads["live_loads"], "live_loads",
        help="Not story-indexed in the schema (see building_config.py's Loads model comment) -- "
             "length doesn't have to equal number_of_stories.")
    loads["leaning_column_loads"] = w.edit_matrix(
        "Leaning column loads (kips)", loads["leaning_column_loads"], "lc_loads",
        w.story_labels(n_stories))
    loads["interior_wall_weight"] = st.number_input(
        "Interior wall weight (psf)", value=float(loads["interior_wall_weight"]))

# --- Wall Lines ---------------------------------------------------------------
with tabs[3]:
    direction = st.radio("Direction", ["X", "Y"], horizontal=True, key="wl_direction",
                          help="'Y' here means Z-running wall lines, matching the schema's own "
                               "Literal['X','Y'] naming.")
    key_list = "x_wall_lines" if direction == "X" else "y_wall_lines"
    wall_lines = cd[key_list]
    names = [wl["name"] for wl in wall_lines]
    if not names:
        st.warning(f"No {direction}-direction wall lines defined.")
    else:
        wl_name = st.selectbox("Wall line", names, key=f"wl_select_{direction}")
        wl = next(wl for wl in wall_lines if wl["name"] == wl_name)
        n_walls = len(wl["geometry"]["wall_lengths"][0]) if wl["geometry"]["wall_lengths"] else 0
        wall_labels = [f"Wall {j+1}" for j in range(n_walls)]

        sub = st.tabs(["Geometry", "Loads", "Materials", "Design constraints", "Rigid diaphragm"])

        with sub[0]:
            g_ = wl["geometry"]
            g_["wall_lengths"] = w.edit_matrix("Wall length (in)", g_["wall_lengths"], f"{wl_name}_len",
                                                w.story_labels(n_stories), wall_labels)
            g_["pinching4_index"] = w.edit_int_matrix("Pinching4 index", g_["pinching4_index"],
                                                       f"{wl_name}_p4", w.story_labels(n_stories), wall_labels)
            g_["tributary_length"] = w.edit_matrix("Tributary length (in)", g_["tributary_length"],
                                                    f"{wl_name}_tl", w.story_labels(n_stories), wall_labels)
            g_["tributary_width"] = w.edit_matrix("Tributary width (in)", g_["tributary_width"],
                                                   f"{wl_name}_tw", w.story_labels(n_stories), wall_labels)

        with sub[1]:
            l_ = wl["loads"]
            l_["shear_wall_load"] = w.edit_matrix("Shear wall load (klf)", l_["shear_wall_load"],
                                                   f"{wl_name}_swl", w.story_labels(n_stories), wall_labels)
            l_["tributary_load_ratio"] = w.edit_vector("Tributary load ratio", l_["tributary_load_ratio"],
                                                        f"{wl_name}_tlr", wall_labels)

        with sub[2]:
            m_ = wl["material_properties"]
            c1, c2, c3 = st.columns(3)
            m_["initial_moisture_content"] = c1.number_input(
                "Initial moisture content", value=float(m_["initial_moisture_content"]), key=f"{wl_name}_imc")
            m_["final_moisture_content"] = c2.number_input(
                "Final moisture content", value=float(m_["final_moisture_content"]), key=f"{wl_name}_fmc")
            m_["wood_modulus_of_elasticity"] = c3.number_input(
                "Wood modulus of elasticity (psi)", value=float(m_["wood_modulus_of_elasticity"]),
                key=f"{wl_name}_moe")
            m_["nail_spacing"] = w.edit_matrix("Nail spacing (in)", m_["nail_spacing"], f"{wl_name}_ns",
                                                w.story_labels(n_stories), wall_labels)
            m_["nail_size"] = w.edit_str_matrix("Nail size", m_["nail_size"], f"{wl_name}_nsz",
                                                 w.story_labels(n_stories), wall_labels)
            m_["panel_thickness"] = w.edit_str_matrix("Panel thickness", m_["panel_thickness"], f"{wl_name}_pt",
                                                       w.story_labels(n_stories), wall_labels)
            m_["take_up_deflection"] = w.edit_vector("Take-up deflection", m_["take_up_deflection"],
                                                      f"{wl_name}_tud", w.story_labels(n_stories))
            m_["chord_area"] = w.edit_vector("Chord area", m_["chord_area"], f"{wl_name}_ca",
                                              w.story_labels(n_stories))
            m_["sheathing_material_type"] = st.text_input(
                "Sheathing material type", value=m_["sheathing_material_type"], key=f"{wl_name}_smt")
            m_["sheathing_type"] = st.text_input(
                "Sheathing type", value=m_["sheathing_type"], key=f"{wl_name}_st")

        with sub[3]:
            dc = wl["design_constraints"]
            c1, c2 = st.columns(2)
            dc["user_defined_drift_limit"] = c1.number_input(
                "User-defined drift limit", value=float(dc["user_defined_drift_limit"]), key=f"{wl_name}_udl")
            dc["user_defined_dc_ratio"] = c2.number_input(
                "User-defined D/C ratio", value=float(dc["user_defined_dc_ratio"]), key=f"{wl_name}_udcr")
            dc["tie_down_system_flag"] = st.checkbox(
                "Tie-down system", value=dc["tie_down_system_flag"], key=f"{wl_name}_tdsf")
            dc["user_defined_dc_ratio_flag_tiedown"] = st.checkbox(
                "User-defined D/C ratio (tiedown)", value=dc["user_defined_dc_ratio_flag_tiedown"],
                key=f"{wl_name}_udcrft")
            dc["user_defined_dc_ratio_tiedown"] = st.number_input(
                "User-defined D/C ratio value (tiedown)", value=float(dc["user_defined_dc_ratio_tiedown"]),
                key=f"{wl_name}_udcrt")

        with sub[4]:
            rd = wl["rigid_diaphragm_assumption"]
            c1, c2, c3 = st.columns(3)
            rd["accidental_torsion_ex"] = c1.number_input(
                "Accidental torsion ex (in)", value=float(rd["accidental_torsion_ex"]), key=f"{wl_name}_ex")
            rd["torsional_irregularity_ax"] = c2.number_input(
                "Torsional irregularity Ax", value=float(rd["torsional_irregularity_ax"]), key=f"{wl_name}_ax")
            rd["redundancy_factor"] = c3.number_input(
                "Redundancy factor", value=float(rd["redundancy_factor"]), key=f"{wl_name}_rho")
            rd["moment_arm"] = w.edit_vector("Moment arm (in)", rd["moment_arm"], f"{wl_name}_ma", wall_labels)

# --- Analysis Parameters -------------------------------------------------------
with tabs[4]:
    st.subheader("Static (pushover) analysis")
    sa = cd["static_analysis"]
    c1, c2, c3 = st.columns(3)
    sa["pushover_increment"] = c1.number_input("Displacement increment (in)", value=float(sa["pushover_increment"]),
                                                format="%.5f")
    sa["pushover_x_drift"] = c2.number_input("Target X roof drift (%)", value=float(sa["pushover_x_drift"]))
    sa["pushover_z_drift"] = c3.number_input("Target Z roof drift (%)", value=float(sa["pushover_z_drift"]))

    st.subheader("Dynamic analysis")
    da = cd["dynamic_analysis"]
    c1, c2 = st.columns(2)
    da["collapse_drift_limit"] = c1.number_input("Collapse drift limit", value=float(da["collapse_drift_limit"]))
    da["demolition_drift_limit"] = c2.number_input("Demolition drift limit",
                                                    value=float(da["demolition_drift_limit"]))
    da["damping_model"] = st.selectbox("Damping model", ["TangentRayleigh", "InitialRayleigh", "CommittedRayleigh"],
                                        index=["TangentRayleigh", "InitialRayleigh", "CommittedRayleigh"]
                                        .index(da["damping_model"]) if da["damping_model"] in
                                        ["TangentRayleigh", "InitialRayleigh", "CommittedRayleigh"] else 0)
    da["damping_ratio"] = st.number_input("Damping ratio", value=float(da["damping_ratio"]), format="%.3f")

# --- Save & Validate -----------------------------------------------------------
with tabs[5]:
    st.markdown("Validation runs the exact same `BuildingConfig` Pydantic model (and its "
                "`model_validator` shape checks) every other consumer of this schema uses.")

    if st.button("Validate (no save)"):
        try:
            BuildingConfig(**st.session_state["config_dict"])
            st.success("Valid -- matches BuildingConfig's schema and shape-consistency checks.")
        except ValidationError as e:
            st.error("Validation failed:")
            st.code(str(e))

    st.divider()
    st.warning(f"Saving overwrites BuildingInfo/{chosen}/building_config.yaml on disk.")
    if st.button("Save to building_config.yaml", type="primary"):
        try:
            validated = BuildingConfig(**st.session_state["config_dict"])
            config_io.save(validated, chosen)
            st.success(f"Saved BuildingInfo/{chosen}/building_config.yaml")
        except ValidationError as e:
            st.error("Not saved -- validation failed:")
            st.code(str(e))
