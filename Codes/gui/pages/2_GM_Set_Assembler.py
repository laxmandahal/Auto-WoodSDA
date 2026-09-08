# -*- coding: utf-8 -*-
"""
GM Set Assembler -- assembles a BuildingModels/GM_sets/<name>/<level>/ ground-
motion set from raw PEER NGA .AT2 records: parses them, scales each H1/H2
pair to an ASCE 7 MCER target spectrum (see lib/gm_scaling.py's docstring for
the exact, simplified method -- NOT a substitute for a qualified engineer's
ground-motion selection/scaling review), and writes the GroundMotionInfo/*.txt
+ histories/*.txt structure Codes/structuralModule/openseespy_dynamic/
ground_motion.py already reads.
"""

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

_LIB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'lib')
_STRUCT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'structuralModule')
_SCHEMA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'schema')
for _d in (_LIB_DIR, _STRUCT_DIR, _SCHEMA_DIR):
    if _d not in sys.path:
        sys.path.append(_d)

import config_io  # noqa: E402
import gm_scaling  # noqa: E402
from BuildingModelClass import BuildingModel  # noqa: E402

st.set_page_config(page_title="GM Set Assembler", layout="wide")
st.title("Ground Motion Set Assembler")

st.warning(
    "Scaling here uses a simplified, per-pair version of ASCE 7-16 Section 16.2.3.1's "
    "procedure (SRSS-combine each pair, match a period-range average against the MCER target "
    "spectrum) -- it is NOT a substitute for a qualified engineer's ground-motion selection "
    "and scaling review before using the result for real research."
)

# --- Step 1: site parameters / target spectrum -------------------------------
st.header("1. Target spectrum")

archetypes = config_io.list_archetypes()
df_inputs_path = os.path.join(config_io.ROOT_DIR, 'Buildings_input_info.csv')
df_inputs = pd.read_csv(df_inputs_path) if os.path.isfile(df_inputs_path) else pd.DataFrame()

col1, col2 = st.columns([1, 2])
with col1:
    use_archetype = st.checkbox("Populate from an archetype's site parameters", value=bool(archetypes))
    site_class, Ss, S1, T1 = "D", 1.0, 0.4, 0.5
    if use_archetype and archetypes and not df_inputs.empty:
        archetype = st.selectbox("Archetype", archetypes, key="gm_archetype")
        row = df_inputs[df_inputs["BuildingID"] == archetype]
        if not row.empty:
            row = row.iloc[0]
            site_class = str(row.get("Site Class", site_class)) or site_class
            Ss = float(row.get("Ss(g)", Ss)) if pd.notna(row.get("Ss(g)")) else Ss
            S1 = float(row.get("S1(g)", S1)) if pd.notna(row.get("S1(g)")) else S1
        import json
        periods_path = os.path.join(config_io.ROOT_DIR, 'Databases', 'Baseline_archetype_info_w_periods.json')
        if os.path.isfile(periods_path) and not row.empty:
            baseline = json.load(open(periods_path))
            layout_id = row.get("Layout Type")
            if layout_id in baseline:
                T1 = float(baseline[layout_id]["Periods"][0])

with col2:
    site_class = st.selectbox("Site Class", ["A", "B", "C", "D", "E"],
                               index=["A", "B", "C", "D", "E"].index(site_class))
    c1, c2, c3 = st.columns(3)
    Ss = c1.number_input("Ss (g)", value=float(Ss), format="%.3f")
    S1 = c2.number_input("S1 (g)", value=float(S1), format="%.3f")
    T1 = c3.number_input("Fundamental period T1 (s)", value=float(T1), format="%.3f",
                          help="Anchors the ASCE 7-16 16.2.3.1 period range [0.2*T1, 1.5*T1] "
                               "below -- override directly if scaling for a different/unusual range.")

sc = gm_scaling.site_coefficients(BuildingModel, site_class, Ss, S1)
st.caption(f"Fa={sc['Fa']:.3f}  Fv={sc['Fv']:.3f}  SMS={sc['SMS']:.3f}g  SM1={sc['SM1']:.3f}g")

c1, c2 = st.columns(2)
t_low = c1.number_input("Period range low (s)", value=round(0.2 * T1, 3), format="%.3f")
t_high = c2.number_input("Period range high (s)", value=round(1.5 * T1, 3), format="%.3f")

periods = np.geomspace(0.02, 6.0, 80)
target_sa = gm_scaling.mcer_spectrum(periods, sc["SMS"], sc["SM1"])

# --- Step 2: upload records ---------------------------------------------------
st.header("2. Upload ground-motion records (PEER NGA .AT2)")
st.caption("Upload pairs of horizontal-component files. They're paired up in upload order "
           "(1st+2nd = pair 1, 3rd+4th = pair 2, ...) -- reorder the file list below if needed.")

uploaded = st.file_uploader("AT2 files", type=["AT2", "at2"], accept_multiple_files=True)

if uploaded and len(uploaded) % 2 != 0:
    st.error(f"{len(uploaded)} files uploaded -- need an even number (H1/H2 pairs).")
    st.stop()

# --- Step 3: compute scale factors --------------------------------------------
if uploaded:
    st.header("3. Computed scale factors")
    if st.button("Compute"):
        results = []
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=periods, y=target_sa, mode="lines",
                                  line=dict(color="black", width=2, dash="dash"), name="MCER target"))

        for i in range(0, len(uploaded), 2):
            f1, f2 = uploaded[i], uploaded[i + 1]
            try:
                accel_h1, dt_h1 = gm_scaling.parse_at2(f1)
                accel_h2, dt_h2 = gm_scaling.parse_at2(f2)
                sf, sa1, sa2, srss = gm_scaling.pair_scale_factor(
                    accel_h1, dt_h1, accel_h2, dt_h2, periods, target_sa, t_low, t_high)
            except ValueError as e:
                st.error(f"{f1.name} / {f2.name}: {e}")
                continue

            pair_idx = i // 2
            results.append({
                "pair": pair_idx, "name_h1": os.path.splitext(f1.name)[0],
                "name_h2": os.path.splitext(f2.name)[0],
                "accel_h1": accel_h1, "dt_h1": dt_h1, "npts_h1": len(accel_h1),
                "accel_h2": accel_h2, "dt_h2": dt_h2, "npts_h2": len(accel_h2),
                "scale_factor": sf,
            })
            fig.add_trace(go.Scatter(x=periods, y=srss * sf, mode="lines",
                                      name=f"pair {pair_idx} SRSS (scaled)", opacity=0.6))

        if results:
            st.session_state["gm_results"] = results
            fig.add_vrect(x0=t_low, x1=t_high, fillcolor="lightblue", opacity=0.3, line_width=0)
            fig.update_layout(xaxis_title="Period (s)", yaxis_title="Sa (g)",
                               xaxis_type="log", height=450,
                               title="Target spectrum vs. scaled record SRSS spectra "
                                     "(shaded = matching period range)")
            st.plotly_chart(fig, use_container_width=True)

            table = pd.DataFrame([
                {"Pair": r["pair"], "H1": r["name_h1"], "H2": r["name_h2"],
                 "Scale factor": round(r["scale_factor"], 4)}
                for r in results
            ])
            st.dataframe(table, use_container_width=True)

# --- Step 4: write to disk -----------------------------------------------------
if st.session_state.get("gm_results"):
    st.header("4. Write GM set to disk")
    c1, c2 = st.columns(2)
    gm_set_name = c1.text_input("GM set name", value="NewGMSet")
    hazard_level = c2.text_input("Hazard level (folder name, e.g. '1')", value="1")

    if st.button("Assemble GM set", type="primary"):
        gm_set_dir = os.path.join(config_io.ROOT_DIR, "BuildingModels", "GM_sets", gm_set_name)
        gm_scaling.write_gm_set_level(gm_set_dir, hazard_level, st.session_state["gm_results"])
        st.success(f"Wrote BuildingModels/GM_sets/{gm_set_name}/{hazard_level}/ "
                   f"({len(st.session_state['gm_results'])} pairs)")
