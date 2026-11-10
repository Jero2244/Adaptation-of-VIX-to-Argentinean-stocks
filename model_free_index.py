"""MF30: descriptive model-free variance of one expiry. PCHIP on total vol in log-moneyness, flat wings, dense grid."""
from __future__ import annotations

from math import exp, sqrt

import numpy as np
import pandas as pd
from scipy.interpolate import PchipInterpolator
from scipy.special import erfc

from atm_index import YEAR_MINUTES, solve_total_vol

MIN_WING_QUOTES = 2
GRID_POINTS = 4001
GRID_STDEVS = 12.0


def _black_otm(forward: float, strikes: np.ndarray, total_vol: np.ndarray) -> np.ndarray:
    """Undiscounted out-of-the-money Black price at each strike."""
    d1 = np.log(forward / strikes) / total_vol + total_vol / 2
    d2 = d1 - total_vol
    call = forward * 0.5 * erfc(-d1 / sqrt(2)) - strikes * 0.5 * erfc(-d2 / sqrt(2))
    put = call - forward + strikes
    return np.where(strikes >= forward, call, put)


def term_variance(chain: pd.DataFrame, minutes: int, rate: float, forward: float) -> dict:
    """Annualized model-free variance, with the share of variance outside the quoted log-moneyness range."""
    result = dict(variance=None, extrapolated_share=None, put_quotes=0, call_quotes=0, reason="")
    if forward is None or minutes <= 0:
        return dict(result, reason="no forward")
    years = minutes / YEAR_MINUTES
    growth = exp(rate * years)
    valid = chain[(chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    puts = valid[(valid["right"] == "P") & (valid["strike"] < forward)]
    calls = valid[(valid["right"] == "C") & (valid["strike"] > forward)]
    result.update(put_quotes=len(puts), call_quotes=len(calls))
    if len(puts) < MIN_WING_QUOTES or len(calls) < MIN_WING_QUOTES:
        return dict(result, reason="fewer than two quotes on a wing")
    points = []
    for row in pd.concat([puts, calls]).sort_values("strike").itertuples():
        mid_undiscounted = growth * (row.bid + row.ask) / 2
        # solve_total_vol prices the call-put average, which equals the OTM price plus half the intrinsic value.
        total_vol = solve_total_vol(mid_undiscounted + abs(forward - row.strike) / 2, forward, row.strike)
        if total_vol is not None:
            points.append((np.log(row.strike / forward), total_vol))
    if len(points) < 2 * MIN_WING_QUOTES:
        return dict(result, reason="too few solved quotes")
    log_money, vols = (np.array(values) for values in zip(*points))
    if not (np.any(log_money < 0) and np.any(log_money > 0)):
        return dict(result, reason="no quotes on one side")
    smile = PchipInterpolator(log_money, vols, extrapolate=False)
    reference = float(np.median(vols))
    half_width = max(GRID_STDEVS * max(reference, float(vols.max())), abs(log_money).max() + 0.01)
    grid = np.linspace(-half_width, half_width, GRID_POINTS)
    grid_vol = np.where(grid < log_money[0], vols[0], np.where(grid > log_money[-1], vols[-1], smile(np.clip(grid, log_money[0], log_money[-1]))))
    strikes = forward * np.exp(grid)
    integrand = _black_otm(forward, strikes, grid_vol) * np.exp(-grid) / forward
    step = grid[1] - grid[0]
    total = float(np.sum(integrand) * step)
    outside = (grid < log_money[0]) | (grid > log_money[-1])
    variance = 2 * total / years
    if not np.isfinite(variance) or variance <= 0:
        return dict(result, reason="non-positive variance")
    return dict(result, variance=variance, extrapolated_share=float(np.sum(integrand[outside]) * step / total), reason="ok")
