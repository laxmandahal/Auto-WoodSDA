# -*- coding: utf-8 -*-
"""
Ground-motion-set assembly: target (MCER) spectrum construction, PEER NGA
.AT2 record parsing, per-pair scale-factor computation, and writing the
GM_sets/<name>/<level>/{GroundMotionInfo,histories} structure
Codes/structuralModule/openseespy_dynamic/ground_motion.py already reads.

Scaling method: ASCE 7-16 Section 16.2.3.1's general idea (SRSS-combine the
two horizontal components, match against the target spectrum over a period
range anchored to the structure's fundamental period), simplified to ONE
scale factor per pair computed independently (not jointly optimized across
an entire suite the way the full Ch. 16 procedure allows) -- each pair's own
SRSS spectrum's period-range average is scaled to equal the target
spectrum's period-range average over the same range. This is a real,
simplified-but-standard structural engineering computation; it is NOT a
substitute for a qualified engineer's ground-motion selection and scaling
review before using the result for real research.
"""

import os
import re

import numpy as np

from response_spectrum import sdof_response_spectrum, average_spectral_acceleration


# --- Target spectrum ---------------------------------------------------------

def site_coefficients(building_model_cls, site_class, Ss, S1):
    """Fa, Fv, SMS, SM1, SDS, SD1 via BuildingModelClass.py's own ASCE 7-10
    Table 11.4-1/11.4-2/Section 11.4 methods -- reused directly (a throwaway
    instance, since these methods don't touch any other instance state) so
    this doesn't re-derive the site-coefficient tables."""
    bm = building_model_cls("_gm_scaling_scratch")
    Fa = bm.determine_Fa_coefficient(site_class, Ss)
    Fv = bm.determine_Fv_coefficient(site_class, S1)
    SMS, SM1, SDS, SD1 = bm.calculate_DBE_acceleration(Ss, S1, Fa, Fv)
    return {"Fa": Fa, "Fv": Fv, "SMS": SMS, "SM1": SM1, "SDS": SDS, "SD1": SD1}


def mcer_spectrum(periods, SMS, SM1, TL=8.0):
    """ASCE 7 Section 11.4.6 / Figure 11.4-1 general response spectrum shape,
    evaluated at the MCER level (SMS/SM1 anchors, not the 2/3-reduced design
    SDS/SD1 -- ground-motion scaling for NRHA targets MCER, matching this
    repo's own existing 'MCE scale factor' / BiDirectionMCEScaleFactors.txt
    convention)."""
    periods = np.asarray(periods, dtype=float)
    T0 = 0.2 * SM1 / SMS
    Ts = SM1 / SMS
    return np.where(
        periods < T0, SMS * (0.4 + 0.6 * periods / T0),
        np.where(periods <= Ts, SMS,
                 np.where(periods <= TL, SM1 / periods, SM1 * TL / periods ** 2)))


# --- PEER NGA .AT2 parsing ---------------------------------------------------

_NPTS_DT_RE = re.compile(r"NPTS\s*=?\s*(\d+)\D+DT\s*=?\s*([\d.]+)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?")


def parse_at2(file_path_or_buffer):
    """Parses a PEER NGA .AT2 file: 3 free-text header lines, a 4th line with
    NPTS/DT (format varies slightly across NGA-West1/West2 exports, hence the
    permissive regex), then acceleration values (units: g) at N-per-line,
    N varying by export. Returns (accel_array, dt)."""
    if hasattr(file_path_or_buffer, "read"):
        text = file_path_or_buffer.read()
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
    else:
        with open(file_path_or_buffer) as f:
            text = f.read()

    lines = text.splitlines()
    if len(lines) < 5:
        raise ValueError("File too short to be a PEER NGA .AT2 record (need >=3 header lines, "
                          "an NPTS/DT line, and data).")

    header_line = None
    for line in lines[:6]:
        if "NPTS" in line.upper() and "DT" in line.upper():
            header_line = line
            break
    if header_line is None:
        raise ValueError("Could not find an 'NPTS=... DT=...' header line in the first 6 lines "
                          "-- is this really a PEER NGA .AT2 file?")
    m = _NPTS_DT_RE.search(header_line)
    if not m:
        raise ValueError(f"Found a header line but couldn't parse NPTS/DT from it: {header_line!r}")
    npts = int(m.group(1))
    dt = float(m.group(2))

    data_start = lines.index(header_line) + 1
    values = []
    for line in lines[data_start:]:
        # PEER's fixed-width data columns don't always have a separating space
        # before a negative value (the '-' sign eats the padding instead) --
        # e.g. "5.6354122E-02-2.3177310E-02" is two numbers, not one. A plain
        # .split() silently mis-tokenizes that; match each number directly.
        values.extend(float(x) for x in _NUMBER_RE.findall(line))
    accel = np.array(values, dtype=float)

    if len(accel) < npts:
        raise ValueError(f"Header declares NPTS={npts} but only {len(accel)} values were read.")
    accel = accel[:npts]
    return accel, dt


# --- Scale factor computation -------------------------------------------------

def pair_scale_factor(accel_h1, dt_h1, accel_h2, dt_h2, target_periods, target_sa, t_low, t_high,
                       damping_ratio=0.05):
    """One scale factor for a bi-directional pair: SRSS-combine the two
    components' response spectra (resampled onto a common period grid --
    the two components can have different dt, hence different natural period
    grids if computed independently), then scale so the SRSS spectrum's
    period-range average equals the target spectrum's period-range average
    over [t_low, t_high]. The SAME scale factor applies to both components
    (standard practice -- component scale factors must match)."""
    sa1 = sdof_response_spectrum(accel_h1, dt_h1, target_periods, damping_ratio)
    sa2 = sdof_response_spectrum(accel_h2, dt_h2, target_periods, damping_ratio)
    srss = np.sqrt(sa1 ** 2 + sa2 ** 2)

    avg_target = average_spectral_acceleration(target_periods, target_sa, t_low, t_high)
    avg_record = average_spectral_acceleration(target_periods, srss, t_low, t_high)
    if avg_record <= 0:
        raise ValueError("Record's SRSS spectrum has zero average over the target period range "
                          "-- cannot compute a scale factor (check the record and period range).")
    return avg_target / avg_record, sa1, sa2, srss


# --- Output: GM_sets/<name>/<level>/ ------------------------------------------

def write_gm_set_level(gm_set_dir, hazard_level, pairs):
    """`pairs`: list of dicts, one per GM pair, each with keys
    {name_h1, name_h2, accel_h1, dt_h1, npts_h1, accel_h2, dt_h2, npts_h2, scale_factor}.
    Writes GroundMotionInfo/{GMFileNames,GMNumPoints,GMTimeSteps,
    BiDirectionMCEScaleFactors}.txt and histories/<name>.txt, in exactly the
    layout/line-indexing openseespy_dynamic/ground_motion.py's resolve_gm()
    expects: one line per COMPONENT (H1/H2 consecutive) for names/numPoints/
    timeSteps, one line per PAIR for the scale factor."""
    level_dir = os.path.join(gm_set_dir, str(hazard_level))
    info_dir = os.path.join(level_dir, "GroundMotionInfo")
    hist_dir = os.path.join(level_dir, "histories")
    os.makedirs(info_dir, exist_ok=True)
    os.makedirs(hist_dir, exist_ok=True)

    names, num_points, time_steps, scale_factors = [], [], [], []
    for p in pairs:
        names.extend([p["name_h1"], p["name_h2"]])
        num_points.extend([p["npts_h1"], p["npts_h2"]])
        time_steps.extend([p["dt_h1"], p["dt_h2"]])
        scale_factors.append(p["scale_factor"])

        np.savetxt(os.path.join(hist_dir, p["name_h1"] + ".txt"), p["accel_h1"], fmt="%.8f")
        np.savetxt(os.path.join(hist_dir, p["name_h2"] + ".txt"), p["accel_h2"], fmt="%.8f")

    with open(os.path.join(info_dir, "GMFileNames.txt"), "w") as f:
        f.write("\n".join(names) + "\n")
    np.savetxt(os.path.join(info_dir, "GMNumPoints.txt"), np.array(num_points, dtype=int), fmt="%d")
    np.savetxt(os.path.join(info_dir, "GMTimeSteps.txt"), np.array(time_steps, dtype=float), fmt="%.5f")
    np.savetxt(os.path.join(info_dir, "BiDirectionMCEScaleFactors.txt"),
               np.array(scale_factors, dtype=float), fmt="%.4f")
