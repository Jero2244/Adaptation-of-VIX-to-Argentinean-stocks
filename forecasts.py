"""Stage 3: forecasts of 30-day realized variance. Rules are in PROTOCOL.md.

ewma_variance, fit_garch, next_variance, and the recursion in horizon_total follow
options-valuation-model/adr/estimators_v2.py. The originals are not edited. horizon_total takes the session count of each
window, because a 30-calendar-day window has no fixed length in sessions. fit_har is not used, because it forces
non-negative weights. The HAR regression here is plain OLS in logs.

A training row at origin t must have a target window that ends on or before t. So no fit sees a return after t.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from arch import arch_model

from realized import CALENDAR_ANNUAL

EWMA_LAMBDA = 0.94
RETURN_SCALE = 100
GARCH_MAXITER = 1000
GARCH_REFIT_SESSIONS = 21
START_SESSIONS = 252
MIN_TRAINING_ROWS = 126
NUMERIC_ERRORS = (ValueError, ArithmeticError, np.linalg.LinAlgError)


class FitFailure(Exception):
    """A registered reason that one fit gave no parameters."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def ewma_variance(returns: np.ndarray, lam: float = EWMA_LAMBDA) -> np.ndarray:
    """s2(t) = sum(lam^i * r(t-i)^2) / sum(lam^i), for all returns through t. Blank at position 0, which has no return."""
    returns = np.asarray(returns, dtype=float)
    if len(returns) < 2 or np.isfinite(returns[0]) or not np.isfinite(returns[1:]).all():
        raise ValueError("Position 0 must have no return, and no other return can be blank")
    out = np.full(len(returns), np.nan)
    numerator, denominator = 0.0, 0.0
    for position in range(1, len(returns)):
        numerator = returns[position] ** 2 + lam * numerator
        denominator = 1 + lam * denominator
        out[position] = numerator / denominator
    return out


def fit_garch(fit_returns: np.ndarray, dist: str = "normal") -> dict:
    """One zero-mean GARCH(1,1) fit on returns in percent. dist is normal or t."""
    fit_returns = np.asarray(fit_returns, dtype=float)
    try:
        with np.errstate(all="ignore"):
            result = arch_model(RETURN_SCALE * fit_returns, mean="Zero", vol="GARCH", p=1, o=0, q=1, dist=dist, rescale=False).fit(disp="off", show_warning=False, options=dict(maxiter=GARCH_MAXITER))
    except NUMERIC_ERRORS as error:
        raise FitFailure("numerical_failure") from error
    if result.convergence_flag != 0:
        raise FitFailure("nonconvergence")
    omega, alpha, beta = (float(result.params[name]) for name in ("omega", "alpha[1]", "beta[1]"))
    last = float(np.asarray(result.conditional_volatility)[-1] ** 2)
    if not np.isfinite([omega, alpha, beta, last]).all():
        raise FitFailure("nonfinite_result")
    return dict(omega=omega, alpha=alpha, beta=beta, persistence=alpha + beta, last_variance=last, fit_rows=len(fit_returns))


def next_variance(fit: dict, previous: float, return_value: float) -> float:
    """h(k+1) from h(k) and the return at k, in percent squared. return_value is not scaled."""
    return fit["omega"] + fit["alpha"] * (RETURN_SCALE * return_value) ** 2 + fit["beta"] * previous


def horizon_total(fit: dict, first_step: float, sessions: int) -> float:
    """Sum h(t+1) to h(t+sessions) with h(k+1) = w + p * h(k), in raw return units."""
    total, current = first_step, first_step
    for _ in range(sessions - 1):
        current = fit["omega"] + fit["persistence"] * current
        total += current
    return total / RETURN_SCALE ** 2


def garch_forecasts(returns: np.ndarray, sessions: np.ndarray, start: int = START_SESSIONS, refit: int = GARCH_REFIT_SESSIONS, dist: str = "normal") -> tuple[np.ndarray, pd.DataFrame]:
    """Annualized 30-day GARCH forecast at each origin from start.

    Each refit uses returns through the prior origin. Between refits, the parameters stay fixed, and the recursion uses
    each new return. A failed fit keeps the prior parameters, and the fit table records the failure. A blank target
    window has a blank forecast.
    """
    returns = np.asarray(returns, dtype=float)
    out = np.full(len(returns), np.nan)
    fit, variance, rows = None, None, []
    for origin in range(start, len(returns)):
        if (origin - start) % refit == 0:
            try:
                candidate = fit_garch(returns[1:origin], dist)
                fit, variance = candidate, candidate["last_variance"]
                # last_variance is h(origin - 1), and it has not used the return at origin - 1.
                variance = next_variance(fit, variance, returns[origin - 1])
                rows.append(dict(origin=origin, reason="", **{k: candidate[k] for k in ("omega", "alpha", "beta", "persistence", "fit_rows")}))
            except FitFailure as failure:
                rows.append(dict(origin=origin, reason=failure.reason))
        if fit is None:
            continue
        # variance is h(origin) here. Use the return at the origin to get h(origin + 1).
        variance = next_variance(fit, variance, returns[origin])
        if sessions[origin] > 0:
            out[origin] = CALENDAR_ANNUAL * horizon_total(fit, variance, int(sessions[origin]))
    return out, pd.DataFrame(rows)


def ewma_forecasts(returns: np.ndarray, sessions: np.ndarray, lam: float = EWMA_LAMBDA) -> np.ndarray:
    """Annualized 30-day EWMA forecast: the daily variance at the origin, times the sessions in the window."""
    return CALENDAR_ANNUAL * ewma_variance(returns, lam) * np.where(sessions > 0, sessions, np.nan)


def fit_log_ols(design: np.ndarray, log_target: np.ndarray) -> tuple[np.ndarray, float]:
    """OLS in logs, plus the Duan smearing factor that returns a forecast of the variance level."""
    beta = np.linalg.lstsq(design, log_target, rcond=None)[0]
    return beta, float(np.mean(np.exp(log_target - design @ beta)))


def expanding_forecasts(frame: pd.DataFrame, inputs: list[str], train_mask: np.ndarray, score_mask: np.ndarray, start: int = START_SESSIONS, min_rows: int = MIN_TRAINING_ROWS, smearing: bool = True) -> np.ndarray:
    """Forecast rv30 with a log regression on inputs, refit at each origin. The inputs are logs.

    A training row needs train_mask and a target window that ends on or before the origin date. An origin needs
    score_mask, at least min_rows training rows, and a position of at least start. Without smearing, the forecast is the
    exponential of the log forecast, which is closer to a median than to a mean.
    """
    design = np.column_stack([np.ones(len(frame))] + [frame[name].to_numpy(dtype=float) for name in inputs])
    target = frame["rv30"].to_numpy(dtype=float)
    dates = frame["session_date"].to_numpy()
    window_end = frame["window_end"].to_numpy()
    out = np.full(len(frame), np.nan)
    for origin in np.flatnonzero(score_mask):
        if origin < start:
            continue
        train = train_mask & (window_end <= dates[origin]) & (np.arange(len(frame)) < origin)
        if train.sum() < min_rows:
            continue
        beta, smear = fit_log_ols(design[train], np.log(target[train]))
        out[origin] = float(np.exp(design[origin] @ beta) * (smear if smearing else 1.0))
    return out


def qlike(target: np.ndarray, forecast: np.ndarray) -> np.ndarray:
    """QLIKE loss per row. It is zero when the forecast equals the target."""
    ratio = np.asarray(target, dtype=float) / np.asarray(forecast, dtype=float)
    return ratio - np.log(ratio) - 1


def squared_error(target: np.ndarray, forecast: np.ndarray) -> np.ndarray:
    return (np.asarray(target, dtype=float) - np.asarray(forecast, dtype=float)) ** 2
