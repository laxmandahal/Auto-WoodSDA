# Legacy per-archetype `.txt` input trees

These are the pre-schema `BuildingInfo/<archetype>/` input files (`Geometry`, `Loads`,
`AnalysisParameters`, `StructuralProperties`, `DynamicProperties`, `X_direction_wall`,
`Y_direction_wall`, and -- for `s1_48x32` -- `SeismicDesignParameters`), archived here
once the pipeline fully moved to the single validated `building_config.yaml` per
archetype (see `Codes/schema/`).

Nothing in the current pipeline reads these anymore. They're kept only as a reference
for the original input format and for `Codes/designModule/migrate_txt_to_yaml.py`, the
one-time tool that consumed a tree exactly like this to produce the `building_config.yaml`
files that live archetypes use today.
