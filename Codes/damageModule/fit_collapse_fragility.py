# -*- coding: utf-8 -*-
"""
Lightweight lognormal collapse-fragility MLE fit: given each hazard level's target
intensity (Sa), collapse count, and number of GM runs, returns (median, dispersion)
-- exactly the two numbers Results/<id>/EDP_data/CollapseFragility.csv holds.

This is a dependency-minimal equivalent of MLEClass.py's MaximumLikelihoodMethod
class -- same lognormfit()/neg_loglik() math (binomial likelihood of a lognormal-CDF
fragility model, Nelder-Mead), same [2, 3] initial guess -- but only the core fit.
MLEClass additionally computes variance estimates (Taylor series, Sandwich/Huber-White
via sympy+numdifftools), a GLM probit comparison fit, and Mean Annual Frequency of
Collapse (MAFC, via a Riemann sum over an external seismic hazard curve). That extra
machinery needs a full site hazard curve (collapseRate: mean annual frequency of
exceedance vs. IM) that MSA orchestration doesn't produce and has no principled way to
fabricate -- confirmed by reading Codes/postProcessing/Plot_Results.ipynb, where even
the original research code sources it from "some dummy return periods" picked by hand,
not derived from anything in this repo. Fitting the two fragility parameters
(median/dispersion) needs none of that -- only IM, collapse count, and GM count per
hazard level, all of which msa_orchestrator.py already has.
"""

import numpy as np
from scipy.optimize import minimize
from scipy.stats import binom, norm


def fit_lognormal_fragility(im_values, collapse_counts, num_gm):
    """im_values, collapse_counts, num_gm: one entry per hazard level (arrays or
    lists, same order). Returns (median, dispersion) of the fitted lognormal
    fragility curve P(collapse | IM) = Phi((ln(IM) - ln(median)) / dispersion)."""
    im_values = np.asarray(im_values, dtype=float)
    collapse_counts = np.asarray(collapse_counts, dtype=float)
    num_gm = np.asarray(num_gm, dtype=float)

    def neg_loglik(theta):
        p_pred = norm.cdf(np.log(im_values), loc=np.log(theta[0]), scale=theta[1])
        likelihood = binom.pmf(collapse_counts, num_gm, p_pred)
        return -np.sum(np.log(likelihood))

    theta_start = [2, 3]  # matches MLEClass.py's lognormfit -- avoids log(0)/log(1) blowups
    res = minimize(neg_loglik, theta_start, method='Nelder-Mead', options={'disp': False})
    median, dispersion = float(res.x[0]), float(res.x[1])
    return median, dispersion
