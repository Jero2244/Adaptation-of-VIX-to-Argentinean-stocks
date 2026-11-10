"""Stage 3: regressions and inference. The block bootstrap and the non-overlapping samples are primary. Newey-West is for comparison only."""
from __future__ import annotations

from typing import Callable

import numpy as np
import pandas as pd


def ols(y: np.ndarray, X: np.ndarray) -> dict:
    """OLS with an intercept in X. Returns the coefficients, the residuals, R2, and the classical standard errors."""
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta
    total = float(np.sum((y - y.mean()) ** 2))
    sigma2 = float(residuals @ residuals) / max(len(y) - X.shape[1], 1)
    classical = np.sqrt(np.diag(sigma2 * np.linalg.pinv(X.T @ X)))
    return dict(beta=beta, residuals=residuals, r2=1 - float(residuals @ residuals) / total if total > 0 else np.nan, classical_se=classical)


def newey_west_se(X: np.ndarray, residuals: np.ndarray, lags: int) -> np.ndarray:
    """Newey-West standard errors with a Bartlett kernel. Rows are treated as consecutive, so missing days are ignored."""
    scores = X * residuals[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        weight = 1 - lag / (lags + 1)
        cross = scores[lag:].T @ scores[:-lag]
        meat += weight * (cross + cross.T)
    bread = np.linalg.pinv(X.T @ X)
    return np.sqrt(np.diag(bread @ meat @ bread))


def two_stage(y: np.ndarray, exogenous: np.ndarray, endogenous: np.ndarray, instrument: np.ndarray) -> dict:
    """2SLS with one endogenous input, placed last in beta. exogenous includes the intercept."""
    Z = np.column_stack([exogenous, instrument])
    first = ols(endogenous, Z)
    fitted = Z @ first["beta"]
    beta = np.linalg.lstsq(np.column_stack([exogenous, fitted]), y, rcond=None)[0]
    restricted = ols(endogenous, exogenous)
    rss_r = float(restricted["residuals"] @ restricted["residuals"])
    rss_u = float(first["residuals"] @ first["residuals"])
    return dict(beta=beta, first_stage_f=(rss_r - rss_u) / (rss_u / max(len(y) - Z.shape[1], 1)))


def block_sample(positions: np.ndarray, block: int, rng: np.random.Generator) -> np.ndarray:
    """Row indices of one circular block resample, with the original row count.

    A block covers consecutive sessions on the full session grid, including missing days. So a block holds fewer rows
    when days are missing, and the time span of the dependence stays correct.
    """
    n = len(positions)
    first = int(positions[0])
    span = int(positions[-1]) - first + 1
    block = min(block, span)
    offsets = positions - first
    parts, total = [], 0
    while total < n:
        start = int(rng.integers(0, span))
        end = start + block
        low, high = np.searchsorted(offsets, [start, min(end, span)])
        part = np.arange(low, high)
        if end > span:
            part = np.concatenate([part, np.arange(0, np.searchsorted(offsets, end - span))])
        parts.append(part)
        total += len(part)
    return np.concatenate(parts)[:n]


def block_bootstrap(estimator: Callable[[np.ndarray], np.ndarray], positions: np.ndarray, block: int, reps: int, seed: int) -> np.ndarray:
    """One row of estimates per resample."""
    rng = np.random.default_rng(seed)
    return np.array([estimator(block_sample(positions, block, rng)) for _ in range(reps)])


def bootstrap_summary(estimate: np.ndarray, draws: np.ndarray) -> dict:
    """Standard error, t, and the 95% percentile interval, per coefficient."""
    se = draws.std(axis=0, ddof=1)
    return dict(se=se, t=np.asarray(estimate) / se, low=np.percentile(draws, 2.5, axis=0), high=np.percentile(draws, 97.5, axis=0))


def non_overlapping_samples(dates: np.ndarray, valid: np.ndarray, window_days: int = 30, offsets: int = 21) -> list[np.ndarray]:
    """Session positions of one sample per offset. No two 30-calendar-day target windows in a sample share a return.

    Offsets count sessions from the first valid session, because early sessions can have no inputs. The next origin is the
    first valid session on or after the end of the current window. A step of exactly 21 sessions can be only 29 calendar
    days, so a fixed step would overlap. Two offsets can merge after a missing day, so the samples are not always distinct.
    """
    step = np.timedelta64(window_days, "D")
    valid_positions = np.flatnonzero(valid)
    samples = []
    for offset in range(offsets):
        chosen, position = [], int(valid_positions[0]) + offset
        while True:
            index = np.searchsorted(valid_positions, position)
            if index == len(valid_positions):
                break
            current = int(valid_positions[index])
            chosen.append(current)
            position = int(np.searchsorted(dates, dates[current] + step))
        samples.append(np.array(chosen, dtype=int))
    return samples


def non_overlapping_table(frame: pd.DataFrame, y_name: str, x_names: list[str], key: str, valid: np.ndarray) -> pd.DataFrame:
    """OLS on each non-overlapping sample. The classical standard error fits these rows, because the windows do not share returns."""
    rows = []
    for offset, sample in enumerate(non_overlapping_samples(frame["session_date"].to_numpy(), valid)):
        chosen = frame.iloc[sample]
        X = np.column_stack([np.ones(len(chosen))] + [chosen[name].to_numpy(dtype=float) for name in x_names])
        result = ols(chosen[y_name].to_numpy(dtype=float), X)
        where = 1 + x_names.index(key)
        rows.append(dict(offset=offset, sample_id=hash(sample.tobytes()), n=len(chosen), coefficient=result["beta"][where], classical_t=result["beta"][where] / result["classical_se"][where], r2=result["r2"]))
    return pd.DataFrame(rows)


def fixed_step_samples(valid: np.ndarray, step: int) -> list[np.ndarray]:
    """One sample per offset. Each sample takes every step-th session on the grid, from the first valid session plus the offset.

    The next origin does not depend on which days are valid, so the paths cannot merge. Steps of 22 and 23 sessions
    are at least 30 calendar days, so the target windows in a sample do not share a return.
    """
    valid = np.asarray(valid, dtype=bool)
    first = int(np.flatnonzero(valid)[0])
    samples = []
    for offset in range(step):
        positions = np.arange(first + offset, len(valid), step)
        samples.append(positions[valid[positions]])
    return samples


def fixed_step_table(frame: pd.DataFrame, y_name: str, x_names: list[str], key: str, valid: np.ndarray, steps: tuple[int, ...] = (22, 23), min_rows: int = 7) -> pd.DataFrame:
    """OLS on each fixed-step sample. A sample with fewer than min_rows rows has no estimate. frame needs one row per session."""
    rows = []
    for step in steps:
        for offset, sample in enumerate(fixed_step_samples(valid, step)):
            chosen = frame.iloc[sample]
            row = dict(step=step, offset=offset, n=len(chosen), coefficient=np.nan, classical_t=np.nan)
            if len(chosen) >= min_rows:
                X = np.column_stack([np.ones(len(chosen))] + [chosen[name].to_numpy(dtype=float) for name in x_names])
                result = ols(chosen[y_name].to_numpy(dtype=float), X)
                where = 1 + x_names.index(key)
                row.update(coefficient=result["beta"][where], classical_t=result["beta"][where] / result["classical_se"][where])
            rows.append(row)
    return pd.DataFrame(rows)


def clark_west(target: np.ndarray, small: np.ndarray, big: np.ndarray) -> np.ndarray:
    """Clark-West adjusted loss difference per row for nested forecasts, on one scale. A positive mean favors the big model."""
    return (target - small) ** 2 - ((target - big) ** 2 - (small - big) ** 2)
