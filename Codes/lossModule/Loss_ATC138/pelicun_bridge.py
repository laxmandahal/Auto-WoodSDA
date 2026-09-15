import json
import os
import shutil
import zipfile
from pathlib import Path


# atc138.input_builder.convert_pelicun() expects these as plain, uncompressed
# CSVs sitting next to each other in one directory. The real pelicun package
# zip-compresses its "Sample" outputs by default (archive name == the plain
# filename), so those need extracting; DL_summary.csv is already plain.
_ZIP_SAMPLE_FILES = {
    "DMG_sample.csv": "DMG_sample.zip",
    "DV_repair_sample.csv": "DV_repair_sample.zip",
}


def _extract_zip_member(zip_path, member_name, dest_path):
    with zipfile.ZipFile(zip_path) as zf:
        with zf.open(member_name) as src, open(dest_path, "wb") as dst:
            shutil.copyfileobj(src, dst)


def bridge_pelicun_output(pelicun_output_dir, model_dir, cmp_marginals_fp):
    """Populate `model_dir` with exactly what atc138.input_builder.convert_pelicun
    needs, sourced from a completed pelicun run in `pelicun_output_dir`.
    """
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    for plain_name, zip_name in _ZIP_SAMPLE_FILES.items():
        zip_path = os.path.join(pelicun_output_dir, zip_name)
        dest_path = os.path.join(model_dir, plain_name)
        if os.path.exists(zip_path):
            _extract_zip_member(zip_path, plain_name, dest_path)
            continue
        # Fall back to an already-plain file (e.g. an older pelicun/fork
        # output, or DV_bldg_repair_sample.* instead of DV_repair_sample.*).
        plain_src = os.path.join(pelicun_output_dir, plain_name)
        if os.path.exists(plain_src):
            shutil.copyfile(plain_src, dest_path)
            continue
        if plain_name == "DV_repair_sample.csv":
            legacy_zip = os.path.join(pelicun_output_dir, "DV_bldg_repair_sample.zip")
            legacy_csv = os.path.join(pelicun_output_dir, "DV_bldg_repair_sample.csv")
            if os.path.exists(legacy_zip):
                _extract_zip_member(legacy_zip, "DV_bldg_repair_sample.csv", dest_path)
                continue
            if os.path.exists(legacy_csv):
                shutil.copyfile(legacy_csv, dest_path)
                continue
        raise FileNotFoundError(
            f"Could not find {plain_name} (or its zip-compressed form) in {pelicun_output_dir}"
        )

    dl_summary_src = os.path.join(pelicun_output_dir, "DL_summary.csv")
    shutil.copyfile(dl_summary_src, os.path.join(model_dir, "DL_summary.csv"))

    # Our own ComponentAssignmentFile already has every column
    # atc138.input_builder.convert_pelicun reads off "CMP_QNT.csv" (ID in dotted
    # FEMA form, Units, Location, Direction, Theta_0) -- no separate generator
    # needed. Pelicun itself only writes a CMP_QNT.csv when an auto-population
    # script assembles components, which this project's pipeline doesn't use.
    shutil.copyfile(cmp_marginals_fp, os.path.join(model_dir, "CMP_QNT.csv"))


def write_general_inputs(
    model_dir,
    num_stories,
    plan_area_ft2,
    story_height_ft,
    length_side_1_ft,
    length_side_2_ft,
    replacement_cost,
    num_entry_doors=2,
    num_elevators=1,
    stairs_per_story=2,
    peak_occ_rate=3.1 / 1000,
    struct_bay_area_ft=100,
):
    """Write general_inputs.json -- the one input file atc138.input_builder
    .convert_pelicun() needs that this project's pelicun/schema pipeline
    doesn't already produce in an atc138-compatible shape.
    """
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    # Matches driverPelicun_E2E.py's own existing single-story convention.
    if num_stories == 1:
        num_entry_doors = 1

    general_inputs = {
        "number_of_stories": num_stories,
        "replacement_cost_median": replacement_cost,
        "plan_area_ft2": plan_area_ft2,
        "typ_story_ht_ft": story_height_ft,
        "length_side_1_ft": length_side_1_ft,
        "length_side_2_ft": length_side_2_ft,
        # A real structural-bay length isn't tracked anywhere in this project's
        # schema -- this is the same 100 sf placeholder driverPelicun_E2E.py
        # already used, kept as "area" (not "length") so atc138 takes the same
        # documented fallback-with-warning path it already has for this case.
        "typ_struct_bay_area_ft": struct_bay_area_ft,
        "num_entry_doors": num_entry_doors,
        "num_elevators": num_elevators,
        "stairs_per_story": [stairs_per_story] * num_stories,
        "peak_occ_rate": peak_occ_rate,
    }

    with open(os.path.join(model_dir, "general_inputs.json"), "w") as f:
        json.dump(general_inputs, f, indent=2)


def write_optional_inputs(model_dir, num_story):
    """Write optional_inputs.json, overriding only the two fields where this
    project's established defaults (driverPelicun_E2E.py's old
    create_optional_inputs_updated() call) differ from atc138's own bundled
    data/default_inputs.json -- confirmed field-by-field identical otherwise.
    """
    Path(model_dir).mkdir(parents=True, exist_ok=True)

    optional_inputs = {
        "impedance_options": {"mitigation": {"capital_available_ratio": 0.1}},
        "functionality_options": {"water_pressure_max_story": num_story},
    }

    with open(os.path.join(model_dir, "optional_inputs.json"), "w") as f:
        json.dump(optional_inputs, f, indent=2)
