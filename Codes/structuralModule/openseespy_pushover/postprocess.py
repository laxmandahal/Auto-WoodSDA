# -*- coding: utf-8 -*-
"""
Reduces a raw (roof_drift_pct, base_shear) pushover curve down to the summary
quantities reported in archetype-comparison tables such as FEMA P-2139-2's
Table 2 (base strength Vmax/W, drift at 80% Vmax, ductility demand).

Ductility demand needs an idealized bilinear (elastic-perfectly-plastic) backbone
-- there's no single universal definition. This repo's own prior pipeline uses
the FEMA P-695 idealization (confirmed with the user 2026-09-07): elastic
stiffness Ke from the secant through the origin and the 60%-of-peak point on the
ascending branch, an elastic-perfectly-plastic plateau at Vy = Vmax (no
equal-energy adjustment), Dy = Vmax/Ke, and Du at 80%-of-peak on the descending
branch -- ductility = Du/Dy. ASTM E2126's Equivalent Energy Elastic-Plastic
(EEEP) procedure (elastic stiffness from the 10%/40%-of-peak secant, yield force
solved so the idealized curve's area matches the actual curve's area out to Du)
is also provided below for reference/comparison, but is not what's reported by
`summarize_pushover`.
"""

import numpy as np


def _interp_disp_at_force(drift, force, target_force):
    """First crossing of `target_force` on the ascending (pre-peak) branch."""
    peak_idx = int(np.argmax(force))
    d, f = drift[:peak_idx + 1], force[:peak_idx + 1]
    idx = np.searchsorted(f, target_force)
    if idx == 0:
        return d[0]
    if idx >= len(f):
        return d[-1]
    f0, f1 = f[idx - 1], f[idx]
    d0, d1 = d[idx - 1], d[idx]
    if f1 == f0:
        return d1
    return d0 + (target_force - f0) * (d1 - d0) / (f1 - f0)


def _ultimate_drift(drift, force):
    """Drift at 80% of peak force on the descending (post-peak) branch -- the
    unambiguous part, read directly off the actual curve, no idealization."""
    peak_idx = int(np.argmax(force))
    vmax = force[peak_idx]
    target = 0.8 * vmax
    post = force[peak_idx:]
    below = np.where(post <= target)[0]
    if len(below) == 0:
        # Curve never drops to 80% of peak within the run -- ultimate point is
        # the last analyzed step.
        return drift[-1], vmax
    j = peak_idx + below[0]
    if j == peak_idx:
        return drift[j], vmax
    f0, f1 = force[j - 1], force[j]
    d0, d1 = drift[j - 1], drift[j]
    if f1 == f0:
        return d1, vmax
    du = d0 + (target - f0) * (d1 - d0) / (f1 - f0)
    return du, vmax


def eeep_idealize(drift, force):
    """ASTM E2126 EEEP idealization. Returns (ke, dy, vy, du, vmax, ductility)
    with drift in the same units passed in (this module is unit-agnostic --
    pass roof drift ratio (%) for a ductility ratio, or displacement (in) if a
    displacement-based ke/dy is wanted instead)."""
    drift = np.asarray(drift, dtype=float)
    force = np.asarray(force, dtype=float)

    du, vmax = _ultimate_drift(drift, force)

    d10 = _interp_disp_at_force(drift, force, 0.1 * vmax)
    d40 = _interp_disp_at_force(drift, force, 0.4 * vmax)
    ke = (0.4 * vmax - 0.1 * vmax) / (d40 - d10)

    # Actual area under the curve from 0 to du (trapezoidal), then solve for Vy
    # such that the idealized elastic-perfectly-plastic curve (0,0)-(dy,Vy)-(du,Vy)
    # encloses the same area: Vy*du - 0.5*Vy^2/ke = A_actual.
    mask = drift <= du
    d_trim = np.append(drift[mask], du)
    f_trim = np.append(force[mask], np.interp(du, drift, force))
    area = np.trapz(f_trim, d_trim)

    a = 0.5 / ke
    b = -du
    c = area
    disc = b ** 2 - 4 * a * c
    disc = max(disc, 0.0)
    vy = (-b - np.sqrt(disc)) / (2 * a)  # smaller (physically valid) root
    dy = vy / ke
    ductility = du / dy if dy > 0 else float('nan')

    return {
        'ke': ke, 'dy': dy, 'vy': vy, 'du': du, 'vmax': vmax,
        'ductility': ductility,
    }


def fema_p695_idealize(drift, force):
    """FEMA P-695 idealization: Ke = secant through the origin and the point on
    the ascending branch at 60% of peak force; plateau at Vy = Vmax (no
    equal-energy adjustment); Dy = Vmax/Ke; Du at 80%-of-peak post-peak.
    Confirmed as this repo's own convention (not ASTM E2126 EEEP) with the user,
    2026-09-07 -- ~2.4 vs. Table 2's 1.74 for MFD6B X-direction was called
    reasonable agreement."""
    drift = np.asarray(drift, dtype=float)
    force = np.asarray(force, dtype=float)

    du, vmax = _ultimate_drift(drift, force)
    d60 = _interp_disp_at_force(drift, force, 0.6 * vmax)
    ke = (0.6 * vmax) / d60

    vy = vmax
    dy = vy / ke
    ductility = du / dy if dy > 0 else float('nan')

    return {
        'ke': ke, 'dy': dy, 'vy': vy, 'du': du, 'vmax': vmax,
        'ductility': ductility,
    }


def summarize_pushover(roof_drift_pct, base_shear, total_weight):
    """Returns the Table-2-style summary: base strength (Vmax/W), drift at 80%
    Vmax (%), and ductility demand (FEMA P-695 idealization, drift-ratio-based
    -- see fema_p695_idealize's docstring)."""
    idealized = fema_p695_idealize(roof_drift_pct, base_shear)
    return {
        'Vmax': idealized['vmax'],
        'base_strength_ratio': idealized['vmax'] / total_weight,
        'drift_at_80pct_vmax_pct': idealized['du'],
        'ductility_demand': idealized['ductility'],
        'fema_p695': idealized,
    }
