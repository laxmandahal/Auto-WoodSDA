# -*- coding: utf-8 -*-
"""
autoWoodSDA input-authoring GUI -- local Streamlit app, no hosting required.

Run with:
    streamlit run Codes/gui/app.py

Uses Streamlit's classic `pages/` auto-discovery (numbered filenames control
sidebar order) rather than the newer `st.navigation`/`st.Page` API, for
broader compatibility across Streamlit versions researchers may already have
installed.
"""

import streamlit as st

st.set_page_config(page_title="autoWoodSDA Input Editor", layout="wide")

st.title("autoWoodSDA Input-Authoring GUI")

st.markdown(
    """
This is a local tool (runs entirely on your own machine -- nothing is hosted or uploaded
anywhere) for authoring an archetype's `building_config.yaml`, in place of hand-editing it
directly.

Open **Archetype Editor** in the sidebar to edit an existing archetype's full config
(geometry, loads, wall-line materials, analysis parameters) with a live 2D plan-view and
3D geometry preview.

Open **New Archetype** to author a brand-new grid-plan layout from scratch: define the
wall-line skeleton (grid-line counts per direction, walls per line), and it creates a
valid, on-disk archetype (`BuildingInfo/<id>/building_config.yaml`, a `Buildings_input_info
.csv` row, and a `Databases/Baseline_archetype_info_w_periods.json` catalog entry) with
flat placeholder defaults for everything else -- review and correct those in the Archetype
Editor before running a real design. Periods are estimated with ASCE 7's low-rise
`T = 0.1 x NumStories` shortcut, not a real eigen analysis.

Every save goes through the same `BuildingConfig` Pydantic model
(`Codes/schema/building_config.py`) every other part of the pipeline uses, so a config saved
here is validated exactly as strictly as one produced any other way.

Ground-motion inputs are out of scope for this tool -- the pipeline assumes you supply your
own site-specific records under `BuildingModels/GM_sets/<name>/<level>/` in the format
`Codes/structuralModule/openseespy_dynamic/ground_motion.py` reads (that module's docstring
documents the exact layout).
"""
)
