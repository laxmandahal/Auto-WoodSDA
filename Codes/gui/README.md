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

**New Archetype** -- author a brand-new grid-plan layout from scratch: pick the number of
grid lines per direction (a slider) and walls per line (independently per line), and it
builds and saves a valid archetype with a sensibly-defaulted skeleton -- geometry, an
auto-derived leaning-column grid, and flat placeholder materials/loads/design constraints
seeded from a real archetype (s1_48x32) -- then registers it in `Buildings_input_info.csv`
and `Databases/Baseline_archetype_info_w_periods.json`. No eigen analysis: the fundamental
period is estimated with ASCE 7's low-rise `T = 0.1 x NumStories` shortcut (only that value
and mode 3 are ever actually read, by `utils_opensees.py`'s Rayleigh damping). Review and
correct every placeholder value in the Archetype Editor before running a real design.

Ground-motion sets are **not** handled here. The pipeline assumes you supply your own
site-specific records under `BuildingModels/GM_sets/<name>/<level>/`, in the layout
`Codes/structuralModule/openseespy_dynamic/ground_motion.py` reads (documented in that
module's docstring). A GM-set assembler with automatic ASCE 7 scaling was prototyped and
dropped -- robustly parsing/scaling arbitrary real PEER records turned out to need more
hardening than it was worth, given researchers in this space generally already have their
records selected and scaled.

## Known limitations (deliberate)

- **Archetype Editor**: story count is fixed once an archetype is loaded (changing it would
  resize every per-story matrix in the config) -- clone a different-story-count archetype
  (or author a new one) instead of trying to change this in place. The Geometry tab's
  wall-line "grid line" labels (e.g. `gridA`, `grid1`) are inferred from matching the count
  of distinct panel coordinates against the count of named wall lines -- if you add/remove
  a panel row on this tab without a matching edit on the Wall Lines tab, labels fall back to
  `line 1`, `line 2`, ... and a warning is shown; `Save & Validate` will still correctly
  reject the resulting shape mismatch either way.
- **New Archetype**: every wall on a grid line gets the same length (footprint / wall
  count) and every wall line gets the same flat placeholder materials/loads -- refine
  per-wall-line/per-story values afterward in the Archetype Editor. Periods are an ASCE 7
  shortcut estimate, not a real eigen analysis (see Scope above) -- if you need real
  periods, run one manually and edit `Databases/Baseline_archetype_info_w_periods.json`'s
  entry for the new layout. `design_outputs` is seeded with nominal (not yet designed)
  panel sizes so the design module can run at all on a from-scratch archetype --
  `python Codes/run_designModule.py --buildingID <id>` overwrites it with the real design.

## Layout

```
Codes/gui/
    app.py                        # landing page
    pages/
        1_Archetype_Editor.py     # edit an existing archetype
        2_New_Archetype.py        # author a brand-new layout's wall-line skeleton
    lib/
        config_io.py              # thin wrapper over Codes/schema/loader.py
        new_archetype.py          # build/save a from-scratch BuildingConfig + catalog entries
        geometry_preview.py       # 2D plan-view + 3D wireframe (Plotly, no openseespy needed)
        widgets.py                # st.data_editor helpers for vector/matrix schema fields
```
