"""Implied move calibration: pure functions. Rules are in CALIBRATION_PLAN.md. All results on seen data are exploratory.

This folder is outside the study's freeze manifest. It imports study code and does not change it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import special, stats

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import inference as inf  # noqa: E402
from atm_index import TARGET_MINUTES  # noqa: E402
from build_series import rate_for  # noqa: E402

WINDOW_DAYS = 30
T = WINDOW_DAYS / 365
INNER = float(stats.norm.cdf(1) - stats.norm.cdf(-1))
OUTER = float(stats.norm.cdf(2) - stats.norm.cdf(-2))
TAIL = float(stats.norm.cdf(-2))
MEAN_ABS = float(np.sqrt(2 / np.pi))
BLOCKS = (21, 63)
REPS = 2000
SEED = 20261104
FIXED_STEPS = (22, 23)
THRESHOLDS = (0.10, 0.20)
RELIABILITY_GROUPS = 5
PIT_BINS = 10
START_POSITION = 252
MIN_PAST_ROWS = 126
NU_GRID = np.array([2.5, 3, 3.5, 4, 5, 6, 7, 8, 10, 12, 15, 20, 30, 50, 100, 1000], dtype=float)
MEASURES = ("inner", "outer", "down_tail", "up_tail", "mean_z2", "mean_abs_z")
FORWARD_START = pd.Timestamp("2026-10-30")
FORWARD_LOOK_END = pd.Timestamp("2027-10-29")
MISCALIBRATED = "Miscalibrated"
NOT_SHOWN = "No miscalibration shown"
TOO_FEW = "Too few rows"


def outcome_returns(frame: pd.DataFrame) -> pd.DataFrame:
    """Total log return in (t, t + 30 calendar days]. The window ends at the last session inside it, as in realized.forward_realized.

    No value is imputed. A blank daily return after the first session stops the run. A window past the last session stays blank.
    """
    dates = frame["session_date"].to_numpy()
    returns = frame["return_total"].to_numpy(dtype=float)
    if not pd.Series(dates).is_monotonic_increasing or not pd.Series(dates).is_unique:
        raise ValueError("Sessions are not unique and in order")
    if np.isnan(returns[1:]).any():
        raise ValueError("A daily return is blank after the first session")
    target = dates + np.timedelta64(WINDOW_DAYS, "D")
    last = np.searchsorted(dates, target, side="right")
    index = np.arange(len(dates))
    running = np.concatenate([[0.0], np.cumsum(np.nan_to_num(returns))])
    sessions = last - index - 1
    complete = (target <= dates[-1]) & (sessions > 0)
    return pd.DataFrame({"R": np.where(complete, running[last] - running[index + 1], np.nan), "outcome_sessions": np.where(complete, sessions, 0), "outcome_end": dates[np.clip(last - 1, 0, len(dates) - 1)]}, index=frame.index)


def rate_30d(frame_dates: pd.Series, rates: pd.DataFrame) -> np.ndarray:
    """Continuous rate at 30 days, from study.session_rates output indexed by session."""
    return np.array([rate_for(rates.loc[day], TARGET_MINUTES) for day in frame_dates], dtype=float)


def build_calibration(frame: pd.DataFrame, r: np.ndarray, outcome_builder=outcome_returns) -> pd.DataFrame:
    """Add r, s, m, R, and z. A half day, a blank ATM30, a blank rate, or an open window gives a blank z."""
    out = frame.copy()
    out = out.join(outcome_builder(out))
    out["r"] = r
    atm = out["atm30"].to_numpy(dtype=float)
    atm = np.where(out["flag_half_day"].to_numpy(dtype=bool), np.nan, atm)
    out["s"] = atm * np.sqrt(T)
    out["m"] = out["r"] * T - out["s"] ** 2 / 2
    out["z"] = (out["R"] - out["m"]) / out["s"]
    out["valid"] = out["z"].notna()
    return out


def alignment_failures(builder=outcome_returns) -> list[str]:
    """Plant one jump and check which origins see it. A builder with a shifted outcome or window fails this check."""
    dates = pd.bdate_range("2021-01-04", periods=80)
    jump_at = 40
    returns = np.zeros(len(dates))
    returns[0] = np.nan
    returns[jump_at] = 0.5
    frame = pd.DataFrame({"session_date": dates, "return_total": returns})
    got = builder(frame)["R"].to_numpy()
    failures = []
    if got[jump_at - 1] != 0.5:
        failures.append("the origin before the jump does not see it")
    if got[jump_at] != 0.0:
        failures.append("the origin at the jump sees it")
    target = dates[jump_at] - pd.Timedelta(days=WINDOW_DAYS)
    first = int(np.searchsorted(dates, target))
    if got[first] != 0.5:
        failures.append("the earliest origin in range does not see it")
    if first > 0 and got[first - 1] != 0.0:
        failures.append("an origin out of range sees it")
    return failures


def measures_from_z(z: np.ndarray) -> np.ndarray:
    """Inner, outer, down tail, up tail, mean z squared, and mean absolute z, in the order of MEASURES."""
    return np.array([np.mean(np.abs(z) < 1), np.mean(np.abs(z) < 2), np.mean(z < -2), np.mean(z > 2), np.mean(z ** 2), np.mean(np.abs(z))])


def pit_shares(u: np.ndarray, bins: int = PIT_BINS) -> np.ndarray:
    return np.histogram(u, bins=np.linspace(0, 1, bins + 1))[0] / len(u)


def intervals_for(values_by_index, positions: np.ndarray, reps: int = REPS) -> dict:
    """Percentile intervals per block. values_by_index takes row indices and returns one vector. A block above a third of the span stays blank."""
    positions = np.asarray(positions)
    span = int(positions[-1] - positions[0] + 1) if len(positions) else 0
    out = {}
    for block in BLOCKS:
        if len(positions) == 0 or block * 3 > span:
            out[block] = None
            continue
        draws = inf.block_bootstrap(values_by_index, positions, block, reps, SEED + block)
        out[block] = dict(low=np.percentile(draws, 2.5, axis=0), high=np.percentile(draws, 97.5, axis=0), se=draws.std(axis=0, ddof=1))
    return out


def measure_table(z: np.ndarray, positions: np.ndarray, reps: int = REPS) -> dict:
    """All primary measures on one set of rows, with intervals for each block."""
    estimate = measures_from_z(z)
    found = intervals_for(lambda index: measures_from_z(z[index]), positions, reps)
    out = dict(n=int(len(z)))
    for where, name in enumerate(MEASURES):
        row = dict(value=float(estimate[where]))
        for block, part in found.items():
            row[f"low{block}"] = None if part is None else float(part["low"][where])
            row[f"high{block}"] = None if part is None else float(part["high"][where])
        out[name] = row
    return out


def fixed_step_table(frame: pd.DataFrame, z_name: str = "z", valid_name: str = "valid") -> list[dict]:
    """Primary measures on each fixed-step sample, summarized by step. frame has one row per session."""
    valid = frame[valid_name].to_numpy(dtype=bool)
    z = frame[z_name].to_numpy(dtype=float)
    rows = []
    for step in FIXED_STEPS:
        samples = [sample for sample in inf.fixed_step_samples(valid, step) if len(sample)]
        values = np.array([measures_from_z(z[sample]) for sample in samples])
        row = dict(step=step, samples=len(samples), median_n=float(np.median([len(sample) for sample in samples])))
        for where, name in enumerate(MEASURES):
            row[name] = dict(mean=float(values[:, where].mean()), min=float(values[:, where].min()), max=float(values[:, where].max()))
        rows.append(row)
    return rows


def past_end_positions(frame: pd.DataFrame) -> np.ndarray:
    """For each origin: the count of leading rows whose window ends on or before the origin date. Those rows are the past rows."""
    dates = frame["session_date"].to_numpy()
    ends = dates + np.timedelta64(WINDOW_DAYS, "D")
    return np.minimum(np.searchsorted(ends, dates, side="right"), np.arange(len(dates)))


def eligible_origin(frame: pd.DataFrame, past_counts: np.ndarray) -> np.ndarray:
    return (frame["position"].to_numpy() >= START_POSITION) & (past_counts >= MIN_PAST_ROWS)


def expanding_scale(frame: pd.DataFrame) -> np.ndarray:
    """k at each origin: the root of the past mean of z squared. It needs position 252 and 126 past rows, and it reads past rows only."""
    valid = frame["valid"].to_numpy(dtype=bool)
    z2 = np.where(valid, frame["z"].to_numpy(dtype=float) ** 2, 0.0)
    total = np.concatenate([[0.0], np.cumsum(z2)])
    count = np.concatenate([[0], np.cumsum(valid)])
    ends = past_end_positions(frame)
    past = count[ends]
    out = np.full(len(frame), np.nan)
    use = eligible_origin(frame, past) & valid
    out[use] = np.sqrt(total[ends[use]] / past[use])
    return out


def unit_t_scale(nu) -> np.ndarray:
    """Scale that gives a Student-t a variance of one."""
    return np.sqrt((np.asarray(nu, dtype=float) - 2) / np.asarray(nu, dtype=float))


def unit_t_logpdf(z: np.ndarray, nu: float) -> np.ndarray:
    scale = unit_t_scale(nu)
    return stats.t.logpdf(z / scale, nu) - np.log(scale)


def expanding_nu(frame: pd.DataFrame, grid: np.ndarray = NU_GRID) -> np.ndarray:
    """Degrees of freedom at each origin from a grid likelihood of past z. It reads past rows only."""
    valid = frame["valid"].to_numpy(dtype=bool)
    z = np.where(valid, frame["z"].to_numpy(dtype=float), 0.0)
    columns = [np.where(valid, unit_t_logpdf(z, nu), 0.0) for nu in grid]
    running = np.vstack([np.zeros(len(grid)), np.cumsum(np.column_stack(columns), axis=0)])
    count = np.concatenate([[0], np.cumsum(valid)])
    ends = past_end_positions(frame)
    out = np.full(len(frame), np.nan)
    use = np.flatnonzero(eligible_origin(frame, count[ends]) & valid)
    out[use] = grid[np.argmax(running[ends[use]], axis=1)]
    return out


def normal_crps(y, loc, scale) -> np.ndarray:
    """CRPS of a normal distribution, closed form (Gneiting and Raftery, 2007)."""
    x = (np.asarray(y) - loc) / scale
    return scale * (x * (2 * stats.norm.cdf(x) - 1) + 2 * stats.norm.pdf(x) - 1 / np.sqrt(np.pi))


def t_crps(y, loc, scale, nu) -> np.ndarray:
    """CRPS of a location-scale Student-t with nu above 1, closed form (Jordan, Kruger and Lerch, 2019)."""
    nu = np.asarray(nu, dtype=float)
    x = (np.asarray(y) - loc) / scale
    constant = 2 * np.sqrt(nu) * np.exp(special.betaln(0.5, nu - 0.5) - 2 * special.betaln(0.5, nu / 2)) / (nu - 1)
    return scale * (x * (2 * stats.t.cdf(x, nu) - 1) + 2 * stats.t.pdf(x, nu) * (nu + x ** 2) / (nu - 1) - constant)


def interval_score(y, low, high, alpha: float) -> np.ndarray:
    """Interval score of a central interval with coverage 1 - alpha. Lower is better."""
    y, low, high = np.asarray(y), np.asarray(low), np.asarray(high)
    return (high - low) + 2 / alpha * np.maximum(low - y, 0) + 2 / alpha * np.maximum(y - high, 0)


class Predictive:
    """One predictive distribution per row: normal if nu is None, otherwise Student-t with a variance of s squared."""

    def __init__(self, loc: np.ndarray, s: np.ndarray, nu: np.ndarray | None = None):
        self.loc, self.s, self.nu = np.asarray(loc, dtype=float), np.asarray(s, dtype=float), None if nu is None else np.asarray(nu, dtype=float)

    def take(self, rows: np.ndarray) -> "Predictive":
        return Predictive(self.loc[rows], self.s[rows], None if self.nu is None else self.nu[rows])

    def cdf(self, y: np.ndarray) -> np.ndarray:
        x = (np.asarray(y) - self.loc) / self.s
        return stats.norm.cdf(x) if self.nu is None else stats.t.cdf(x / unit_t_scale(self.nu), self.nu)

    def half_width(self, coverage: float) -> np.ndarray:
        p = 0.5 + coverage / 2
        return self.s * stats.norm.ppf(p) if self.nu is None else self.s * stats.t.ppf(p, self.nu) * unit_t_scale(self.nu)

    def crps(self, y: np.ndarray) -> np.ndarray:
        return normal_crps(y, self.loc, self.s) if self.nu is None else t_crps(y, self.loc, self.s * unit_t_scale(self.nu), self.nu)

    def move_probability(self, threshold: float) -> np.ndarray:
        return self.cdf(np.full_like(self.loc, np.log(1 - threshold))) + 1 - self.cdf(np.full_like(self.loc, np.log(1 + threshold)))


def normal_band(r: np.ndarray, s: np.ndarray) -> Predictive:
    """The centre rule of the plan: m = rT - s^2/2."""
    return Predictive(np.asarray(r) * T - np.asarray(s) ** 2 / 2, s)


def row_scores(pred: Predictive, R: np.ndarray) -> dict[str, np.ndarray]:
    out = {"crps": pred.crps(R)}
    for name, coverage in (("interval_inner", INNER), ("interval_outer", OUTER)):
        half = pred.half_width(coverage)
        out[name] = interval_score(R, pred.loc - half, pred.loc + half, 1 - coverage)
    return out


def hit_rows(pred: Predictive, R: np.ndarray) -> dict[str, np.ndarray]:
    inner, outer = pred.half_width(INNER), pred.half_width(OUTER)
    distance = R - pred.loc
    return dict(inner=np.abs(distance) < inner, outer=np.abs(distance) < outer, down_tail=distance < -outer, up_tail=distance > outer)


def move_happened(R: np.ndarray, threshold: float) -> np.ndarray:
    return np.abs(np.exp(R) - 1) > threshold


def reliability_groups(probability: np.ndarray, happened: np.ndarray, groups: int = RELIABILITY_GROUPS) -> list[dict]:
    """Equal-count groups by forecast probability, with the mean forecast and the observed share."""
    order = np.argsort(probability, kind="stable")
    rows = []
    for part in np.array_split(order, groups):
        rows.append(dict(n=int(len(part)), mean_probability=float(probability[part].mean()), observed=float(happened[part].mean()), low_probability=float(probability[part].min()), high_probability=float(probability[part].max())))
    return rows


def brier(probability: np.ndarray, happened: np.ndarray) -> np.ndarray:
    return (probability - happened.astype(float)) ** 2


def forward_verdict(z: np.ndarray, positions: np.ndarray, horizon: str | None, last_origin, reps: int = REPS) -> dict:
    """The frozen forward rule. It refuses a run without a horizon fixed in advance, or before that horizon."""
    if horizon is None:
        raise RuntimeError("The owner has not fixed the verdict horizon")
    if pd.Timestamp(last_origin) < pd.Timestamp(horizon):
        raise RuntimeError("The verdict horizon has not been reached")
    hits = (np.abs(z) < 1).astype(float)
    found = intervals_for(lambda index: np.array([hits[index].mean()]), positions, reps)
    out = dict(n=int(len(z)), inner=float(hits.mean()) if len(z) else None)
    if any(part is None for part in found.values()):
        return dict(out, verdict=TOO_FEW)
    for block, part in found.items():
        out[f"low{block}"], out[f"high{block}"] = float(part["low"][0]), float(part["high"][0])
    outside = all(out[f"low{block}"] > INNER or out[f"high{block}"] < INNER for block in BLOCKS)
    return dict(out, verdict=MISCALIBRATED if outside else NOT_SHOWN)
