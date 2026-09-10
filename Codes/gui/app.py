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
3D geometry preview. v1 scope: editing one of the archetype layouts already defined in
`Databases/Baseline_archetype_info_w_periods.json` -- authoring a brand-new layout from
scratch is a planned follow-up (it needs an eigen-analysis bootstrap step this page
doesn't attempt).

Every save goes through the same `BuildingConfig` Pydantic model
(`Codes/schema/building_config.py`) every other part of the pipeline uses, so a config saved
here is validated exactly as strictly as one produced any other way.

Ground-motion inputs are out of scope for this tool -- the pipeline assumes you supply your
own site-specific records under `BuildingModels/GM_sets/<name>/<level>/` in the format
`Codes/structuralModule/openseespy_dynamic/ground_motion.py` reads (that module's docstring
documents the exact layout).
"""
)
