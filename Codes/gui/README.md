# autoWoodSDA Input-Authoring GUI

A local Streamlit app for editing an archetype's `building_config.yaml`, in
place of hand-editing that (large) file directly. Runs entirely on your own
machine -- nothing is hosted or uploaded anywhere, so there's no hosting cost.

## Run it

```bash
pip install -r requirements.txt   # adds streamlit + plotly, see that file's notes
streamlit run Codes/gui/app.py
```

Needs Python>=3.10 (same reason as `openseespy` -- see `requirements.txt`).

## Scope

**Archetype Editor** -- edit an existing archetype's full `building_config.yaml`: geometry
(with a live 2D plan-view and 3D wireframe preview), loads, per-wall-line materials/design
constraints, and analysis parameters. Every save goes through the real `BuildingConfig`
Pydantic model (`Codes/schema/building_config.py`), so validation is exactly as strict as
any other path that touches this schema.

Ground-motion sets are **not** handled here. The pipeline assumes you supply your own
site-specific records under `BuildingModels/GM_sets/<name>/<level>/`, in the layout
`Codes/structuralModule/openseespy_dynamic/ground_motion.py` reads (documented in that
module's docstring). A GM-set assembler with automatic ASCE 7 scaling was prototyped and
dropped -- robustly parsing/scaling arbitrary real PEER records turned out to need more
hardening than it was worth, given researchers in this space generally already have their
records selected and scaled.

## Known limitations (deliberate)

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

## Layout

```
Codes/gui/
    app.py                        # landing page
    pages/1_Archetype_Editor.py   # main editor
    lib/
        config_io.py              # thin wrapper over Codes/schema/loader.py
        geometry_preview.py       # 2D plan-view + 3D wireframe (Plotly, no openseespy needed)
        widgets.py                # st.data_editor helpers for vector/matrix schema fields
```
