# autoWoodSDA Input-Authoring GUI

A local Streamlit app for authoring the inputs autoWoodSDA needs, in place of
hand-editing `building_config.yaml` (or the old scattered `.txt` tree)
directly. Runs entirely on your own machine -- nothing is hosted or uploaded
anywhere, so there's no hosting cost.

## Run it

```bash
pip install -r requirements.txt   # adds streamlit + plotly, see that file's notes
streamlit run Codes/gui/app.py
```

Needs Python>=3.10 (same reason as `openseespy` -- see `requirements.txt`).

## Pages

- **Archetype Editor** -- edit an existing archetype's full `building_config.yaml`:
  geometry (with a live 2D plan-view and 3D wireframe preview), loads, per-wall-line
  materials/design constraints, and analysis parameters. Every save goes through the real
  `BuildingConfig` Pydantic model (`Codes/schema/building_config.py`), so validation is
  exactly as strict as any other path that touches this schema.
- **GM Set Assembler** -- assemble a `BuildingModels/GM_sets/<name>/<level>/` ground-motion
  set from raw PEER NGA `.AT2` records: parses them, computes a per-pair scale factor against
  an ASCE 7 MCER target spectrum (a simplified, per-pair version of ASCE 7-16 Section
  16.2.3.1's procedure -- **not** a substitute for a qualified engineer's ground-motion
  selection/scaling review), and writes the exact file structure
  `Codes/structuralModule/openseespy_dynamic/ground_motion.py` already reads.

## v1 scope (deliberate, see the session's plan)

- Editing one of the archetype layouts already listed in
  `Databases/Baseline_archetype_info_w_periods.json`. Authoring a brand-new layout from
  scratch is a planned v2 -- it needs an eigen-analysis bootstrap step to populate that
  catalog's required `Periods` field, which this editor doesn't attempt.
- Story count is fixed once an archetype is loaded (changing it would resize every
  per-story matrix in the config) -- clone a different-story-count archetype instead of
  trying to change this in place.
- The Geometry tab's wall-line "grid line" labels (e.g. `gridA`, `grid1`) are inferred from
  matching the count of distinct panel coordinates against the count of named wall lines --
  if you add/remove a panel row on this tab without a matching edit on the Wall Lines tab,
  labels fall back to `line 1`, `line 2`, ... and a warning is shown; `Save & Validate` will
  still correctly reject the resulting shape mismatch either way.

Ground-motion scaling needs an SDOF pseudo-acceleration response spectrum of each uploaded
record, computed via Newmark-beta integration -- validated against the T->0 rigid-oscillator
limit (Sa should converge to PGA), not against a reference implementation (none was available
to compare against). Treat scale factors as a starting point to sanity-check, not a final
answer to use unreviewed.

## Layout

```
Codes/gui/
    app.py                          # landing page
    pages/
        1_Archetype_Editor.py       # building_config.yaml editor
        2_GM_Set_Assembler.py       # ground-motion set assembly
    lib/
        config_io.py                # thin wrapper over Codes/schema/loader.py
        geometry_preview.py         # 2D plan-view + 3D wireframe (Plotly, no openseespy needed)
        widgets.py                  # st.data_editor helpers for vector/matrix schema fields
        response_spectrum.py        # SDOF pseudo-acceleration spectrum (Newmark-beta)
        gm_scaling.py                # ASCE 7 target spectrum, .AT2 parsing, scale factors,
                                     # GM_sets/ output writer
```
