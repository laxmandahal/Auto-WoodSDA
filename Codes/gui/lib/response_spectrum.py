# -*- coding: utf-8 -*-
"""
Pseudo-acceleration response spectrum of a ground-motion record, via Newmark-
beta (constant average acceleration: gamma=1/2, beta=1/4 -- unconditionally
stable) time-stepping of the SDOF equation of motion
    m*a + c*v + k*u = -m*ag(t)
at each requested period, following the standard formulation in Chopra's
"Dynamics of Structures" (Table 5.4.1/5.4.2 -- widely reproduced, not specific
to this repo). Vectorized across periods (all periods share the same time
loop; only the per-step scalar coefficients differ per period), not across
records -- call once per component.

Units: whatever `ground_accel` is in (e.g. g, or in/s^2) -- damping/stiffness/
mass all cancel out consistently for a linear-elastic SDOF, so the returned
Sa is in the same units as `ground_accel`, unitless "PGA-equivalent" scale.
"""

import numpy as np

# np.trapz was removed in numpy>=2.0 in favor of np.trapezoid (deprecated
# alias first, then gone entirely by 2.4) -- this repo's requirements.txt
# already targets numpy>=2.0 (see its pandas>=2.2 note), so prefer the new
# name but fall back for anyone on an older numpy.
_trapz = getattr(np, "trapezoid", None) or np.trapz


def sdof_response_spectrum(ground_accel, dt, periods, damping_ratio=0.05):
    """Returns pseudo-spectral acceleration Sa(T) = omega^2 * max|u(t)| for
    each period in `periods` (array-like, seconds). `ground_accel`: 1-D array
    of ground acceleration values, uniform time step `dt`."""
    ag = np.asarray(ground_accel, dtype=float)
    periods = np.atleast_1d(np.asarray(periods, dtype=float))
    n_steps = len(ag)

    omega = 2.0 * np.pi / periods
    m = 1.0
    k = m * omega ** 2
    c = 2.0 * damping_ratio * omega * m

    gamma = 0.5
    beta = 0.25
    a1 = 1.0 / (beta * dt ** 2) * m + gamma / (beta * dt) * c
    a2 = 1.0 / (beta * dt) * m + (gamma / beta - 1.0) * c
    a3 = (1.0 / (2.0 * beta) - 1.0) * m + dt * (gamma / (2.0 * beta) - 1.0) * c
    k_hat = k + a1

    u = np.zeros_like(periods)
    v = np.zeros_like(periods)
    a = -ag[0] - (c * v + k * u) / m  # initial acceleration (u0=v0=0 -> a0 = -ag0)

    u_max = np.abs(u).copy()

    for i in range(n_steps - 1):
        d_p = -(ag[i + 1] - ag[i]) * m
        d_p_hat = d_p + a2 * v + a3 * a
        d_u = d_p_hat / k_hat
        d_v = gamma / (beta * dt) * d_u - gamma / beta * v + dt * (1.0 - gamma / (2.0 * beta)) * a
        d_a = 1.0 / (beta * dt ** 2) * d_u - 1.0 / (beta * dt) * v - 1.0 / (2.0 * beta) * a

        u = u + d_u
        v = v + d_v
        a = a + d_a
        np.maximum(u_max, np.abs(u), out=u_max)

    return omega ** 2 * u_max


def average_spectral_acceleration(periods, spectrum, t_low, t_high, n_samples=50):
    """Average of `spectrum` (already computed at `periods`, and interpolated
    -- linearly in Sa, at log-spaced sample periods) over [t_low, t_high],
    via trapezoidal integration IN LOG-PERIOD SPACE divided by the log-period
    range. Log-period averaging (not a plain arithmetic mean over whatever
    discrete periods happen to fall in range) is the standard convention for
    period-range spectral matching -- periods are naturally log-distributed
    in engineering practice. Always resamples at `n_samples` log-spaced
    points regardless of how `periods` was sampled, so the result isn't
    sensitive to that input spacing."""
    periods = np.asarray(periods, dtype=float)
    spectrum = np.asarray(spectrum, dtype=float)
    log_p = np.linspace(np.log(t_low), np.log(t_high), n_samples)
    sample_periods = np.exp(log_p)
    sample_sa = np.interp(sample_periods, periods, spectrum)
    return float(_trapz(sample_sa, log_p) / (log_p[-1] - log_p[0]))
