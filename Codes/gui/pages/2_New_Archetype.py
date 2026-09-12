# -*- coding: utf-8 -*-
"""
New Archetype -- author a brand-new grid-plan layout from scratch.

v2 (this page): define the wall-line skeleton (grid-line counts per direction,
wall count per line -- the one thing v1's Archetype Editor can't do at all),
seed everything else with flat placeholder defaults, and register the result
in all three places a new archetype needs to exist: BuildingInfo/<id>/
building_config.yaml, Buildings_input_info.csv, and Databases/
Baseline_archetype_info_w_periods.json.

No eigen analysis here (confirmed with the user) -- the fundamental period is
estimated with ASCE 7's low-rise shortcut T = 0.1 * NumStories
(new_archetype.compute_periods). This page's whole job is to get to a valid,
on-disk skeleton fast; once created, the archetype immediately shows up in
the Archetype Editor's picker for reviewing/refining every placeholder value
before running a real design.
"""

import os
import sys

import streamlit as st

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
if _LIB_DIR not in sys.path:
    sys.path.append(_LIB_DIR)

import new_archetype as na  # noqa: E402
from pydantic import ValidationError  # noqa: E402

st.set_page_config(page_title="New Archetype", layout="wide")
st.title("New Archetype")

st.info(
    "This wizard gets you to a valid, on-disk archetype fast by defining the wall-line "
    "skeleton (something the Archetype Editor can't do) and filling everything else -- "
    "materials, loads, design constraints -- with flat placeholder defaults. **Review and "
    "correct every placeholder value in the Archetype Editor before running a real "
    "design.** Periods are estimated with ASCE 7's T = 0.1 x NumStories shortcut, not a "
    "real eigen analysis."
)

tabs = st.tabs(["Identity & Stories", "Wall-Line Skeleton", "Loads", "Site & Seismic", "Create"])

# --- Identity & Stories -------------------------------------------------------
with tabs[0]:
    archetype_id = st.text_input("Archetype ID", key="na_id",
                                  help="Used as BuildingInfo/<id>/, and kept identical for "
                                       "both BuildingID and Layout Type in Buildings_input_info.csv "
                                       "(avoids the mismatch fixed in PR #14).")
    c1, c2 = st.columns(2)
    n_stories = c1.number_input("Number of stories", min_value=1, max_value=12, value=1, step=1, key="na_stories")
    story_height = c2.number_input("Story height (in)", min_value=1.0, value=120.0, step=1.0, key="na_story_height")

    c1, c2 = st.columns(2)
    footprint_x = c1.number_input("Footprint X dimension (in)", min_value=1.0, value=480.0, step=1.0, key="na_fx")
    footprint_z = c2.number_input("Footprint Z dimension (in)", min_value=1.0, value=384.0, step=1.0, key="na_fz")

# --- Wall-Line Skeleton --------------------------------------------------------
with tabs[1]:
    st.caption("'Y' here means Z-running wall lines, matching the schema's own "
               "Literal['X','Y'] naming (same convention as the Archetype Editor).")

    col_x, col_z = st.columns(2)
    with col_x:
        st.subheader("X-direction wall lines")
        st.caption("Each pinned to a fixed Z coordinate, spanning the full X footprint.")
        n_x_lines = st.slider("Number of X-direction grid lines", 1, 10, 2, key="na_n_x_lines")
        x_wall_counts = []
        for i, name in enumerate(na.line_names("X", n_x_lines)):
            x_wall_counts.append(
                st.number_input(f"Walls on {name}", min_value=1, max_value=20, value=2, step=1,
                                 key=f"na_x_walls_{i}"))

    with col_z:
        st.subheader("Y-direction wall lines")
        st.caption("Each pinned to a fixed X coordinate, spanning the full Z footprint.")
        n_z_lines = st.slider("Number of Y-direction grid lines", 1, 10, 2, key="na_n_z_lines")
        z_wall_counts = []
        for i, name in enumerate(na.line_names("Z", n_z_lines)):
            z_wall_counts.append(
                st.number_input(f"Walls on {name}", min_value=1, max_value=20, value=2, step=1,
                                 key=f"na_z_walls_{i}"))

    skeleton = na.build_skeleton(footprint_x, footprint_z, n_x_lines, x_wall_counts, n_z_lines, z_wall_counts)

    st.divider()
    st.markdown("**Preview**")
    for line in skeleton["x_lines"]:
        st.text(f"{line['name']} (X, fixed Z={line['fixed_coord']:.1f}in): "
                 f"{line['n_walls']} walls x {line['wall_length']:.1f}in")
    for line in skeleton["z_lines"]:
        st.text(f"{line['name']} (Y, fixed X={line['fixed_coord']:.1f}in): "
                 f"{line['n_walls']} walls x {line['wall_length']:.1f}in")

# --- Loads ----------------------------------------------------------------------
with tabs[2]:
    st.caption("One global value each, broadcast to every story/column -- refine per-floor "
               "afterward in the Archetype Editor's Loads tab.")
    c1, c2, c3 = st.columns(3)
    floor_weight = c1.number_input("Floor weight (kips)", min_value=0.0, value=50.0, key="na_floor_weight")
    leaning_column_load = c2.number_input("Leaning column load per node (kips)", min_value=0.0, value=5.0,
                                           key="na_lc_load")
    interior_wall_weight = c3.number_input("Interior wall weight (psf)", min_value=0.0, value=10.0,
                                            key="na_interior_wall_weight")

# --- Site & Seismic ---------------------------------------------------------------
with tabs[3]:
    st.caption("Feeds Buildings_input_info.csv. Risk Category/R/Cd/Ie/Ss(g)/S1(g) are left "
               "blank and auto-filled (Ss/S1 via the USGS API from Latitude/Longitude) the "
               "first time the design module runs.")
    c1, c2, c3 = st.columns(3)
    site_class = c1.selectbox("Site Class", ["A", "B", "C", "D", "E", "F"], index=3, key="na_site_class")
    wall_material = c2.text_input("Wall material", value="Stucco_GWB", key="na_wall_material")
    seismic_weight = c3.selectbox("Seismic weight", ["Light", "Normal", "Heavy"], index=1, key="na_seismic_weight")
    c1, c2 = st.columns(2)
    latitude = c1.number_input("Latitude", value=33.9721, format="%.4f", key="na_lat")
    longitude = c2.number_input("Longitude", value=-118.42177, format="%.5f", key="na_lon")

# --- Create -----------------------------------------------------------------------
with tabs[4]:
    conflicts = na.archetype_id_conflicts(archetype_id) if archetype_id else ["Enter an Archetype ID first."]
    if conflicts:
        for reason in conflicts:
            st.warning(reason)

    periods = na.compute_periods(n_stories)
    st.markdown(f"**Estimated periods** (T = 0.1 x {n_stories} stories): "
                f"`{[round(p, 4) for p in periods]}` -- only the 1st and 3rd values are ever "
                f"actually used (Rayleigh damping); the others are stored for catalog-format "
                f"consistency only.")

    if st.button("Create Archetype", type="primary", disabled=bool(conflicts)):
        try:
            config = na.build_config(
                archetype_id, n_stories, story_height, footprint_x, footprint_z, skeleton,
                floor_weight, leaning_column_load, interior_wall_weight, wall_material,
            )
            na.save_new_archetype(config, archetype_id)
            na.append_csv_row(archetype_id, site_class, latitude, longitude, wall_material, seismic_weight)
            na.append_baseline_json_entry(archetype_id, skeleton, n_stories)
            st.success(
                f"Created BuildingInfo/{archetype_id}/building_config.yaml, added it to "
                f"Buildings_input_info.csv and Baseline_archetype_info_w_periods.json. "
                f"Open **Archetype Editor** to review and correct every placeholder value "
                f"before running `python Codes/run_designModule.py --buildingID {archetype_id}`."
            )
        except ValidationError as e:
            st.error("Not created -- validation failed:")
            st.code(str(e))
