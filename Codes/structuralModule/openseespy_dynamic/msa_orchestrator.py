# -*- coding: utf-8 -*-
"""
Multiple Stripe Analysis (MSA) orchestration: run generateDynamicAnalysisModel_ops
(dynamic_runner.py) for every ground-motion pair, at every hazard level, for one
archetype -- the piece run_dynamic_cli.py's own docstring flagged as "later, separate
work" when the single-GM port landed.

Pairing ID 2 (H1-in-Z/H2-in-X, the 90-degree-swapped orientation) is deliberately not
run here -- confirmed with the repo owner it's not worth the compute (every unit of
work below is pairing 1, H1-in-X/H2-in-Z, only). generateDynamicAnalysisModel_ops/
define_ground_motion_loading still support pairing=2 as a general single-GM
capability (unchanged, used directly if ever needed); this orchestrator just never
asks for it.

Replaces the two `for GM_ID in range(...): os.system('OpenSees ...')` loops in
Codes/woodSDA_driver_E2E.ipynb (cell 20) plus the EDP-extraction cell right after it
(cell 22, ExtractMaxEDP.ExtractSDR/ExtractRDR/ExtractPFA) and the collapse-fragility
fit (Codes/damageModule/MLEClass.py, driven from Codes/postProcessing/Plot_Results
.ipynb) with one call: no .tcl files, no external OpenSees binary, no hardcoded
GM_Num/Scale_Sa_GM strings (ground_motion.py already derives hazard levels/GM counts
from the GM_sets/<name>/ folder structure), and no separate post-hoc collapse-counting
pass (collapse_flag already comes out of the analysis itself, using the archetype's
own dynamic_analysis.collapse_drift_limit as the check threshold instead of the legacy
hardcoded 0.1). Writes the same Results/<id>/EDP_data/{SDR,RDR,PFA,CollapseCount,
CollapseFragility}.csv scheme the real, committed Results/MFD6B/EDP_data/ already has
example output for -- see save_msa_results/to_legacy_edp_frames. Each hazard level's
target Sa (needed for CollapseFragility.csv) is a plain user input -- there's nowhere
in the GM_sets/<name>/ folder structure to derive or store it (confirmed no such file
exists there, and the old pipeline always sourced it externally too) -- passed
straight through from run_msa_cli.py's --hazardLevelIM to save_msa_results.

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


PAIRING = 1  # H1-in-X/H2-in-Z only -- see module docstring for why pairing 2 is skipped


def enumerate_units_of_work(gm_set_dir, gm_limit=None):
    """Every hazard level x every GM index, derived entirely from the GM_sets/<name>/
    folder structure (ground_motion.list_hazard_levels/num_gm_pairs) -- no hardcoded
    hazard-level count or GM count anywhere. `gm_limit` caps the number of GM indices
    used per hazard level (for smoke tests; None = all). Returns a list of
    {"hazard_level", "gm_index"} dicts (always pairing 1 -- see PAIRING)."""
    from ground_motion import list_hazard_levels, num_gm_pairs

    units = []
    for level in list_hazard_levels(gm_set_dir):
        n_pairs = num_gm_pairs(gm_set_dir, level)
        if gm_limit is not None:
            n_pairs = min(n_pairs, gm_limit)
        for gm_index in range(n_pairs):
            units.append({"hazard_level": level, "gm_index": gm_index})
    return units


def _compute_pga_g(result):
    """Peak ground acceleration (g) on each physical axis, matching
    ExtractMaxEDP.ExtractPGA's math (peak abs raw-record value x MCE scale factor --
    ground_motion.py's own docstring confirms raw record values are already in g, so
    no further unit conversion is needed here). Pairing is always 1 (H1 drives X, H2
    drives Z -- see PAIRING), so result['ground_motion']['gm_x_file'/'gm_z_file']
    (resolve_gm's raw H1/H2 assignment) already are the physical X/Z drive files."""
    import numpy as np
    from ground_motion import GM_SCALE_G

    gm = result['ground_motion']
    mce_scale_factor = gm['scale_factor'] / GM_SCALE_G  # strip the g->in/s^2 conversion back out

    def peak_g(path):
        return float(np.max(np.abs(np.loadtxt(path)))) * mce_scale_factor

    return peak_g(gm['gm_x_file']), peak_g(gm['gm_z_file'])


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
        "ok": None, "error": None,
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
            building_id, bm, gm_set_dir, unit["hazard_level"], unit["gm_index"], PAIRING,
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
        row["pga_x_g"], row["pga_z_g"] = _compute_pga_g(result)
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


def run_msa(building_id, gm_set_name, num_workers=None, gm_limit=None,
            num_modes=4, max_run_time=3600):
    """Runs the full MSA for `building_id` against BuildingModels/GM_sets/<gm_set_name>/
    (pairing 1 only -- see module docstring), parallelized across `num_workers` OS
    processes (default os.cpu_count()). Uses the archetype's own dynamic_analysis
    .collapse_drift_limit/demolition_drift_limit (building_config.yaml) as the
    collapse/demolition thresholds, rather than a hardcoded literal. Returns one
    DataFrame row per (hazard_level, gm_index)."""
    from loader import load_building_config

    base_dir = os.path.join(_ROOT_DIR, 'BuildingInfo', building_id)
    gm_set_dir = os.path.join(_ROOT_DIR, 'BuildingModels', 'GM_sets', gm_set_name)

    config = load_building_config(base_dir)
    collapse_drift_limit = config.dynamic_analysis.collapse_drift_limit
    demolition_drift_limit = config.dynamic_analysis.demolition_drift_limit

    units = enumerate_units_of_work(gm_set_dir, gm_limit=gm_limit)
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
            print(f"[{i}/{len(units)}] hazard {unit['hazard_level']} GM {unit['gm_index']}: "
                  f"{status} ({row['wall_time_s']:.1f}s)")

    print(f"MSA for {building_id!r} against {gm_set_name!r}: {len(units)} runs in "
          f"{(time.time() - start) / 60:.1f} min across {num_workers} workers.")

    df = pd.DataFrame(rows)
    # hazard_level is the folder name (a string, e.g. "1", "10") -- sort numerically so
    # "10" doesn't land before "2".
    df = (df.assign(_hazard_level_sort=df["hazard_level"].astype(int))
            .sort_values(["_hazard_level_sort", "gm_index"])
            .drop(columns="_hazard_level_sort")
            .reset_index(drop=True))
    return df


def summarize_by_hazard_level(df):
    """One row per hazard level: n_gm, n_ok, n_failed, n_collapse, collapse_fraction,
    n_demolition, demolition_fraction. This is the source data fit_collapse_fragility
    fits a curve to (n_collapse/n_gm per level) -- see save_msa_results."""
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


def to_legacy_edp_frames(df, num_stories):
    """Reshapes the long-format per-run `df` (one row per (hazard_level, gm_index),
    as returned by run_msa) into the same headerless 4-file scheme Results/MFD6B/
    EDP_data/ already has real committed examples of (confirmed by reading them
    directly): SDR/RDR/PFA each have columns [HazardLevel, Direction, GM_number, ...],
    with a block of "Direction 1" (X) rows for every GM followed by a block of
    "Direction 2" (Z) rows at each hazard level (ExtractMaxEDP.ExtractSDR's layout)
    -- not interleaved per-GM. CollapseCount is one row per hazard level.

    "GM_number" is simply gm_index + 1 (pairing 2 isn't run -- see module docstring
    -- so there's no ambiguity here about whether/how a second pairing should be
    counted, unlike a from-scratch reimplementation of the legacy 2-pairing scheme
    would have needed to resolve).

    Rows with a recorded 'error' (a failed run) are excluded entirely -- there's no
    valid EDP to report for them.

    Returns (sdr_df, rdr_df, pfa_df, collapse_count_df), each ready for
    `to_csv(header=False, index=False)`.
    """
    ok = df[df["error"].isna()].copy()
    ok["hazard_level_int"] = ok["hazard_level"].astype(int)
    ok = ok.sort_values(["hazard_level_int", "gm_index"])
    ok["gm_number"] = ok["gm_index"] + 1

    sdr_rows, rdr_rows, pfa_rows, collapse_rows = [], [], [], []
    for level, group in ok.groupby("hazard_level_int"):
        n_collapse = int(group["collapse_flag"].fillna(False).sum())
        collapse_rows.append({"n_collapse": n_collapse})

        for _, r in group.iterrows():
            sdr_rows.append([level, 1, r["gm_number"]] + [r[f"sdr_x_story{s + 1}"] for s in range(num_stories)])
            rdr_rows.append([level, 1, r["gm_number"], r["residual_drift_x"]])
            pfa_rows.append([level, 1, r["gm_number"], r["pga_x_g"]]
                             + [r[f"pfa_x_g_floor{s + 1}"] for s in range(num_stories)])
        for _, r in group.iterrows():
            sdr_rows.append([level, 2, r["gm_number"]] + [r[f"sdr_z_story{s + 1}"] for s in range(num_stories)])
            rdr_rows.append([level, 2, r["gm_number"], r["residual_drift_z"]])
            pfa_rows.append([level, 2, r["gm_number"], r["pga_z_g"]]
                             + [r[f"pfa_z_g_floor{s + 1}"] for s in range(num_stories)])

    sdr_df = pd.DataFrame(sdr_rows)
    rdr_df = pd.DataFrame(rdr_rows)
    pfa_df = pd.DataFrame(pfa_rows)
    collapse_count_df = pd.DataFrame(collapse_rows)
    return sdr_df, rdr_df, pfa_df, collapse_count_df


def save_msa_results(df, building_id, num_stories, hazard_level_im=None):
    """Writes Results/<building_id>/EDP_data/ -- the same location and (for SDR/RDR/
    PFA/CollapseCount) the same headerless schema as the real, committed
    Results/MFD6B/EDP_data/ example. Also writes CollapseFragility.csv (median,
    dispersion -- one value per line, matching that real file's shape exactly) if
    `hazard_level_im` (a {"<level>": Sa_g} dict, a plain user input -- there's nowhere
    in the GM_sets/<name>/ folder structure to derive or store it) is given and covers
    every hazard level actually run; skips it with a printed warning otherwise (EDP
    extraction doesn't need it, only the fragility fit does).

    Additionally writes edp_results.csv (the full long-format per-run table -- errors,
    wall-clock time, etc., which the legacy 4-file scheme has no room for) and
    hazard_level_summary.csv (counts/fractions) alongside them -- genuinely new files,
    not part of the legacy scheme, but useful diagnostics kept in the same place.

    Returns a dict of the paths written."""
    out_dir = os.path.join(_ROOT_DIR, 'Results', building_id, 'EDP_data')
    os.makedirs(out_dir, exist_ok=True)
    paths = {}

    n_failed = int(df["error"].notna().sum())
    if n_failed:
        print(f"WARNING: {n_failed} of {len(df)} runs failed and are excluded from "
              f"SDR/RDR/PFA/CollapseCount.csv -- see edp_results.csv's 'error' column.")

    sdr_df, rdr_df, pfa_df, collapse_count_df = to_legacy_edp_frames(df, num_stories)
    for name, frame in [("SDR", sdr_df), ("RDR", rdr_df), ("PFA", pfa_df), ("CollapseCount", collapse_count_df)]:
        path = os.path.join(out_dir, f"{name}.csv")
        frame.to_csv(path, header=False, index=False)
        paths[name] = path

    paths["edp_results"] = os.path.join(out_dir, "edp_results.csv")
    df.to_csv(paths["edp_results"], index=False)

    summary_df = summarize_by_hazard_level(df)
    paths["hazard_level_summary"] = os.path.join(out_dir, "hazard_level_summary.csv")
    summary_df.to_csv(paths["hazard_level_summary"], index=False)

    if not hazard_level_im:
        print("No hazard-level Sa values given -- skipping CollapseFragility.csv "
              "(EDP data was still written).")
        return paths

    missing = [lvl for lvl in summary_df["hazard_level"] if lvl not in hazard_level_im]
    if missing:
        print(f"hazard_level_im is missing hazard level(s) {missing} -- skipping "
              f"CollapseFragility.csv.")
        return paths

    sys.path.append(os.path.join(_CODES_DIR, 'damageModule'))
    from fit_collapse_fragility import fit_lognormal_fragility

    im_values = [hazard_level_im[lvl] for lvl in summary_df["hazard_level"]]
    median, dispersion = fit_lognormal_fragility(im_values, summary_df["n_collapse"], summary_df["n_gm"])
    paths["CollapseFragility"] = os.path.join(out_dir, "CollapseFragility.csv")
    pd.DataFrame([median, dispersion]).to_csv(paths["CollapseFragility"], header=False, index=False)
    print(f"Collapse fragility: median Sa={median:.4f}, dispersion={dispersion:.4f}")

    return paths
