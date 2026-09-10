# -*- coding: utf-8 -*-
"""
OpenSeesPy counterpart of utils_opensees.py's Tcl-path analysis orchestration --
a thin layer over the openseespy_eigen / openseespy_pushover packages so
`run_designModule.py --engine openseespy` (and the demo notebook) can run
eigen + pushover in-process instead of writing .tcl files and shelling out to
an external OpenSees binary.

Scope note: this covers the two analyses that need no extra inputs (eigen,
pushover). NRHA/dynamic is per-ground-motion and stays a separate invocation
(Codes/structuralModule/openseespy_dynamic/run_dynamic_cli.py) -- full MSA
orchestration is a later, separate piece of work.

This module imports openseespy at module scope, which is fine because it is
only ever imported lazily (inside run_designModule.py's `engine == 'openseespy'`
branch, or explicitly by a notebook) -- never at the top of run_designModule.py,
whose Tcl path must keep working with no openseespy installed.
"""

import csv
import os
import sys

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))          # .../Codes/structuralModule
_CODES_DIR = os.path.dirname(_THIS_DIR)                          # .../Codes
_ROOT_DIR = os.path.dirname(_CODES_DIR)                          # repo root
_EIGEN_DIR = os.path.join(_THIS_DIR, 'openseespy_eigen')
_PUSHOVER_DIR = os.path.join(_THIS_DIR, 'openseespy_pushover')
_DYNAMIC_DIR = os.path.join(_THIS_DIR, 'openseespy_dynamic')
_SCHEMA_DIR = os.path.join(_CODES_DIR, 'schema')

for _d in (_THIS_DIR, _EIGEN_DIR, _PUSHOVER_DIR, _DYNAMIC_DIR, _SCHEMA_DIR):
    if _d not in sys.path:
        sys.path.append(_d)

try:
    import openseespy.opensees as _ops  # noqa: F401  (import-time availability check)
except Exception as exc:  # pragma: no cover - environment-dependent
    # openseespy's own __init__ raises RuntimeError (not ImportError) when the
    # platform wheel is wrong -- e.g. an x86_64 openseespymac on Apple Silicon,
    # the exact situation pre-3.8.0.0. Catch broadly and re-raise with a fix hint.
    raise ImportError(
        "engine='openseespy' needs a working openseespy>=3.8.0.0 (see requirements.txt "
        "-- on Apple Silicon a native arm64 wheel exists as of 3.8.0.0, Python>=3.10; "
        "older openseespymac wheels are x86_64-only and fail to import). "
        f"Original error: {exc!r}"
    ) from exc

import numpy as np  # noqa: E402

from eigen_runner import generateModalAnalysisModel_ops  # noqa: E402
from pushover_runner import generatePushoverAnalysisModel_ops  # noqa: E402

# openseespy_pushover/postprocess.py -- openseespy_dynamic/ also has a postprocess.py,
# but this module only needs the pushover one and openseespy_pushover is earlier on
# sys.path, so a plain import resolves correctly. (If dynamic orchestration is ever
# added here, switch both to importlib-by-path to dodge the name collision.)
from postprocess import summarize_pushover  # noqa: E402


def run_eigen(building_model, num_modes=4):
    """`building_model` must already have had read_in_txt_inputs() called.
    Returns a list of `num_modes` periods (seconds)."""
    return generateModalAnalysisModel_ops(building_model.ID, building_model, NumModes=num_modes)


def run_pushover(building_model, directions=("X", "Z"), total_weight=None):
    """Runs a full displacement-controlled pushover per direction. If
    `total_weight` is given (kips -- typically `float(sum(building_model.floorWeights))`),
    each direction's result also carries a `summary` dict from
    openseespy_pushover.postprocess.summarize_pushover (Vmax, Vmax/W,
    drift at 80% Vmax, ...). Returns {dir: {"curve": <run dict>, "summary": <dict|None>}}."""
    out = {}
    for direction in directions:
        curve = generatePushoverAnalysisModel_ops(building_model.ID, building_model, direction)
        summary = None
        if total_weight is not None:
            summary = summarize_pushover(curve["roof_drift_pct"], curve["base_shear"], total_weight)
        out[direction] = {"curve": curve, "summary": summary}
    return out


def run_static_analyses(building_model, do_eigen=True, do_pushover=True, num_modes=4,
                         pushover_directions=("X", "Z")):
    """Design-agnostic: `building_model` must already be populated via
    read_in_txt_inputs(). Returns {"periods": [...]|None, "pushover": {...}|None}."""
    results = {"periods": None, "pushover": None}
    if do_eigen:
        results["periods"] = run_eigen(building_model, num_modes=num_modes)
    if do_pushover:
        total_weight = float(sum(building_model.floorWeights))
        results["pushover"] = run_pushover(building_model, pushover_directions, total_weight)
    return results


def save_static_results(results, output_dir):
    """Writes results from run_static_analyses to disk (the openseespy path's
    analogue of the Tcl path leaving .tcl/.out files in
    BuildingModels/<ID>/<AnalysisType>/). Creates:
      - periods.txt          : one period per line (if eigen ran)
      - pushover_<dir>.csv    : roof_drift_pct, base_shear_kips  (per direction)
      - pushover_summary.csv  : direction, Vmax_kips, Vmax_over_W, drift_at_80pct_Vmax_pct
    """
    os.makedirs(output_dir, exist_ok=True)

    if results.get("periods") is not None:
        with open(os.path.join(output_dir, "periods.txt"), "w") as f:
            f.write("\n".join(f"{p:.6f}" for p in results["periods"]) + "\n")

    pushover = results.get("pushover")
    if pushover:
        summary_rows = []
        for direction, data in pushover.items():
            curve = data["curve"]
            np.savetxt(
                os.path.join(output_dir, f"pushover_{direction}.csv"),
                np.column_stack([curve["roof_drift_pct"], curve["base_shear"]]),
                delimiter=",", header="roof_drift_pct,base_shear_kips", comments="",
            )
            s = data["summary"]
            if s is not None:
                summary_rows.append((direction, s["Vmax"], s["base_strength_ratio"],
                                     s["drift_at_80pct_vmax_pct"]))
        if summary_rows:
            with open(os.path.join(output_dir, "pushover_summary.csv"), "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["direction", "Vmax_kips", "Vmax_over_W", "drift_at_80pct_Vmax_pct"])
                for row in summary_rows:
                    writer.writerow([row[0], f"{row[1]:.4f}", f"{row[2]:.5f}", f"{row[3]:.4f}"])
