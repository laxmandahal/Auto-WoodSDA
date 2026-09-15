# -*- coding: utf-8 -*-
"""
Multiple Stripe Analysis (MSA) orchestration: run generateDynamicAnalysisModel_ops
(dynamic_runner.py) for every ground-motion pair, at every hazard level, in both
pairings, for one archetype -- the piece run_dynamic_cli.py's own docstring flagged
as "later, separate work" when the single-GM port landed.

Replaces the two `for GM_ID in range(...): os.system('OpenSees ...')` loops in
Codes/woodSDA_driver_E2E.ipynb (cell 20) plus the EDP-extraction cell right after it
(cell 22, ExtractMaxEDP.ExtractSDR/ExtractRDR/ExtractPFA) with one call: no .tcl
files, no external OpenSees binary, no hardcoded GM_Num/Scale_Sa_GM strings (ground_
motion.py already derives hazard levels/GM counts from the GM_sets/<name>/ folder
structure), and no separate post-hoc collapse-counting pass (collapse_flag already
comes out of the analysis itself, using the archetype's own dynamic_analysis
.collapse_drift_limit as the check threshold instead of the legacy hardcoded 0.1).

Parallel by OS process, not thread: model_builders.build_model() calls ops.wipe()
first thing, and generateDynamicAnalysisModel_ops() calls build_model() as its very
first step, so every run fully resets OpenSeesPy's global C-extension state -- safe
to loop sequentially within one process, but that state isn't thread-safe/shareable
across Python threads in one process. concurrent.futures.ProcessPoolExecutor gives
one OS process per worker for free (stdlib, no new dependency); each worker loops
over its assigned units of work sequentially via _run_one_unit.
"""

import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))                 # .../openseespy_dynamic
_STRUCTURAL_MODULE_DIR = os.path.dirname(_THIS_DIR)                    # .../structuralModule
_CODES_DIR = os.path.dirname(_STRUCTURAL_MODULE_DIR)                   # .../Codes
_ROOT_DIR = os.path.dirname(_CODES_DIR)                                # repo root
_EIGEN_DIR = os.path.join(_STRUCTURAL_MODULE_DIR, 'openseespy_eigen')
_SCHEMA_DIR = os.path.join(_CODES_DIR, 'schema')

for _d in (_THIS_DIR, _EIGEN_DIR, _STRUCTURAL_MODULE_DIR, _SCHEMA_DIR):
    if _d not in sys.path:
        sys.path.append(_d)


def enumerate_units_of_work(gm_set_dir, pairings=(1, 2), gm_limit=None):
    """Cross product of every hazard level x every GM index x every pairing, derived
    entirely from the GM_sets/<name>/ folder structure (ground_motion.list_hazard_levels
    / num_gm_pairs) -- no hardcoded hazard-level count or GM count anywhere. `gm_limit`
    caps the number of GM indices used per hazard level (for smoke tests; None = all).
    Returns a list of {"hazard_level", "gm_index", "pairing"} dicts."""
    from ground_motion import list_hazard_levels, num_gm_pairs

    units = []
    for level in list_hazard_levels(gm_set_dir):
        n_pairs = num_gm_pairs(gm_set_dir, level)
        if gm_limit is not None:
            n_pairs = min(n_pairs, gm_limit)
        for gm_index in range(n_pairs):
            for pairing in pairings:
                units.append({"hazard_level": level, "gm_index": gm_index, "pairing": pairing})
    return units


def _run_one_unit(building_id, base_dir, gm_set_dir, unit, collapse_drift_limit,
                   demolition_drift_limit, num_modes, max_run_time):
    """The unit of work dispatched to each worker process. Module-level (not a
    closure/method) so it's picklable for ProcessPoolExecutor. Rebuilds its own
    BuildingModel from scratch -- same 3-line pattern run_dynamic_cli.py uses --
    since OpenSeesPy model state can't cross a process boundary anyway. Never raises:
    a failed run becomes one row with ok=None and an 'error' message, so one bad GM
    doesn't abort the whole batch."""
    row = {
        "hazard_level": unit["hazard_level"], "gm_index": unit["gm_index"],
        "pairing": unit["pairing"], "ok": None, "error": None,
    }
    start = time.time()
    try:
        from dynamic_runner import generateDynamicAnalysisModel_ops
        from postprocess import summarize_dynamic
        from run_dynamic_cli import _load_df_inputs
        from BuildingModelClass import BuildingModel

        df_inputs = _load_df_inputs(building_id)
        bm = BuildingModel(building_id)
        bm.read_in_txt_inputs(building_id, base_dir, df_inputs=df_inputs)

        result = generateDynamicAnalysisModel_ops(
            building_id, bm, gm_set_dir, unit["hazard_level"], unit["gm_index"], unit["pairing"],
            num_modes=num_modes, drift_limit=collapse_drift_limit, max_run_time=max_run_time,
        )
        summary = summarize_dynamic(result, bm.storyHeights)

        row["ok"] = summary["ok"]
        row["collapse_flag"] = summary["collapse_flag"]
        row["collapse_dof"] = summary["collapse_dof"]
        row["demolition_flag"] = (
            max(summary["residual_drift_x"], summary["residual_drift_z"]) >= demolition_drift_limit
        )
        row["residual_drift_x"] = summary["residual_drift_x"]
        row["residual_drift_z"] = summary["residual_drift_z"]
        row["final_time"] = summary["final_time"]
        row["gm_time"] = summary["gm_time"]
        for i, v in enumerate(summary["peak_sdr_x"]):
            row[f"sdr_x_story{i + 1}"] = v
        for i, v in enumerate(summary["peak_sdr_z"]):
            row[f"sdr_z_story{i + 1}"] = v
        for i, v in enumerate(summary["peak_pfa_x_g"]):
            row[f"pfa_x_g_floor{i + 1}"] = v
        for i, v in enumerate(summary["peak_pfa_z_g"]):
            row[f"pfa_z_g_floor{i + 1}"] = v
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, see docstring
        row["error"] = f"{type(exc).__name__}: {exc}"

    row["wall_time_s"] = time.time() - start
    return row


def run_msa(building_id, gm_set_name, pairings=(1, 2), num_workers=None, gm_limit=None,
            num_modes=4, max_run_time=3600):
    """Runs the full MSA for `building_id` against BuildingModels/GM_sets/<gm_set_name>/,
    parallelized across `num_workers` OS processes (default os.cpu_count()). Uses the
    archetype's own dynamic_analysis.collapse_drift_limit/demolition_drift_limit
    (building_config.yaml) as the collapse/demolition thresholds, rather than a
    hardcoded literal. Returns one DataFrame row per (hazard_level, gm_index, pairing)."""
    from loader import load_building_config

    base_dir = os.path.join(_ROOT_DIR, 'BuildingInfo', building_id)
    gm_set_dir = os.path.join(_ROOT_DIR, 'BuildingModels', 'GM_sets', gm_set_name)

    config = load_building_config(base_dir)
    collapse_drift_limit = config.dynamic_analysis.collapse_drift_limit
    demolition_drift_limit = config.dynamic_analysis.demolition_drift_limit

    units = enumerate_units_of_work(gm_set_dir, pairings=pairings, gm_limit=gm_limit)
    if not units:
        raise ValueError(f"No ground motions found under {gm_set_dir}")

    num_workers = num_workers or os.cpu_count() or 1
    rows = []
    start = time.time()
    with ProcessPoolExecutor(max_workers=num_workers) as pool:
        futures = {
            pool.submit(_run_one_unit, building_id, base_dir, gm_set_dir, unit,
                        collapse_drift_limit, demolition_drift_limit, num_modes, max_run_time): unit
            for unit in units
        }
        for i, future in enumerate(as_completed(futures), 1):
            unit = futures[future]
            row = future.result()
            rows.append(row)
            status = row["error"] or ("collapse" if row.get("collapse_flag") else "ok")
            print(f"[{i}/{len(units)}] hazard {unit['hazard_level']} GM {unit['gm_index']} "
                  f"pairing {unit['pairing']}: {status} ({row['wall_time_s']:.1f}s)")

    print(f"MSA for {building_id!r} against {gm_set_name!r}: {len(units)} runs in "
          f"{(time.time() - start) / 60:.1f} min across {num_workers} workers.")

    df = pd.DataFrame(rows)
    # hazard_level is the folder name (a string, e.g. "1", "10") -- sort numerically so
    # "10" doesn't land before "2".
    df = (df.assign(_hazard_level_sort=df["hazard_level"].astype(int))
            .sort_values(["_hazard_level_sort", "gm_index", "pairing"])
            .drop(columns="_hazard_level_sort")
            .reset_index(drop=True))
    return df


def summarize_by_hazard_level(df):
    """One row per hazard level: n_gm, n_ok, n_failed, n_collapse, collapse_fraction,
    n_demolition, demolition_fraction. Raw counts/fractions only -- fitting a fragility
    curve to these is a separate, later step (not this module's job)."""
    rows = []
    for level in sorted(df["hazard_level"].unique(), key=int):
        group = df[df["hazard_level"] == level]
        n = len(group)
        n_ok = int((group["ok"] == 0).sum())
        n_failed = int(group["error"].notna().sum())
        n_collapse = int(group["collapse_flag"].fillna(False).sum())
        n_demolition = int(group["demolition_flag"].fillna(False).sum())
        rows.append({
            "hazard_level": level, "n_gm": n, "n_ok": n_ok, "n_failed": n_failed,
            "n_collapse": n_collapse, "collapse_fraction": n_collapse / n if n else 0.0,
            "n_demolition": n_demolition, "demolition_fraction": n_demolition / n if n else 0.0,
        })
    return pd.DataFrame(rows)


def save_msa_results(df, building_id, gm_set_name):
    """Writes BuildingModels/<building_id>/OpenSeesPyResults/MSA/<gm_set_name>/
    edp_results.csv (the full per-run table) and hazard_level_summary.csv (per-hazard-
    level counts/fractions) -- following the OpenSeesPyResults/ convention the
    eigen/pushover port already established, not the legacy Results/<id>/EDP_data/
    path (tied to the Tcl-recorder pipeline and its currently-broken Pelicun consumer).
    Returns (edp_csv_path, summary_csv_path)."""
    out_dir = os.path.join(_ROOT_DIR, 'BuildingModels', building_id, 'OpenSeesPyResults', 'MSA', gm_set_name)
    os.makedirs(out_dir, exist_ok=True)

    edp_csv_path = os.path.join(out_dir, 'edp_results.csv')
    summary_csv_path = os.path.join(out_dir, 'hazard_level_summary.csv')

    df.to_csv(edp_csv_path, index=False)
    summarize_by_hazard_level(df).to_csv(summary_csv_path, index=False)

    return edp_csv_path, summary_csv_path
