"""Stage 4: the rules of the one-time test, as pure functions. Rules are in STAGE4_PLAN.md and PROTOCOL.md.

The open-data report, the rehearsal, and run_tests_once.py all use these functions. So the test cannot run other rules.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import forecasts as fc
import inference as inf

HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
FULL = HAR + [IV]
SEED = 20261104  # Each bootstrap uses SEED + block, as run_development.py does.
REPS = 2000
BLOCKS = (21, 63)
FIXED_STEPS = (22, 23)
LIMIT_NO_EVENTS = 0.37
LIMIT_WITH_EVENTS = 0.525
FLOOR_ORIGINS = 300
FLOOR_SPANS = 20
SPAN_SESSIONS = 21
FLOOR_ROWS_PER_SPAN = 10
MIN_SCORED = 180
CW_LIMIT = 1.65

SUPPORTED = "Supported"
SMALLER = "Smaller than .37"
INCONCLUSIVE = "Inconclusive"
NO_FLOOR = "Inconclusive, data floor"


def add_inputs(panel: pd.DataFrame) -> pd.DataFrame:
    """Add the log inputs and the primary flag to a frame of realized measures and index series, with one row per session."""
    out = panel.copy()
    out[IV] = np.log(out["atm30"] ** 2)
    out["log_rv30"] = np.log(out["rv30"])
    out["log_rv21"] = np.log(out["rv21"])
    out["log_iv2_lag1"] = out[IV].shift(1)
    out["log_iv2_lag5"] = out[IV].shift(5)
    out["primary"] = out[[IV, "log_rv30"] + HAR].notna().all(axis=1)
    return out


def data_floor(valid: np.ndarray) -> dict:
    """At least 300 valid origins, and at least 20 of the 21-session spans hold 10 or more valid origins each. These 20 spans do not need to be adjacent.

    The spans start at the first valid origin, on the session grid. The last span can be short, and it still counts if it holds 10.
    """
    valid = np.asarray(valid, dtype=bool)
    origins = int(valid.sum())
    if origins == 0:
        return dict(origins=0, filled_spans=0, passed=False)
    first = int(np.flatnonzero(valid)[0])
    counts = [int(valid[start:start + SPAN_SESSIONS].sum()) for start in range(first, len(valid), SPAN_SESSIONS)]
    filled = sum(count >= FLOOR_ROWS_PER_SPAN for count in counts)
    return dict(origins=origins, filled_spans=filled, passed=origins >= FLOOR_ORIGINS and filled >= FLOOR_SPANS)


def intervals(rows: pd.DataFrame, reps: int = REPS, names: list[str] | None = None, key: str = IV) -> dict:
    """Estimate of the coefficient on key, with a percentile interval per block. A block with fewer than three fits stays blank."""
    names = FULL if names is None else names
    y = rows["log_rv30"].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(rows))] + [rows[name].to_numpy(dtype=float) for name in names])
    where = 1 + names.index(key)
    positions = rows["position"].to_numpy()
    span = int(positions[-1] - positions[0] + 1)
    out = dict(n=len(rows), b=float(inf.ols(y, X)["beta"][where]))

    def estimator(index: np.ndarray) -> np.ndarray:
        return np.linalg.lstsq(X[index], y[index], rcond=None)[0][where:where + 1]

    for block in BLOCKS:
        out[f"low{block}"], out[f"high{block}"], out[f"se{block}"] = np.nan, np.nan, np.nan
        if block * 3 <= span:
            draws = inf.block_bootstrap(estimator, positions, block, reps, SEED + block)[:, 0]
            out[f"low{block}"], out[f"high{block}"] = (float(v) for v in np.percentile(draws, [2.5, 97.5]))
            out[f"se{block}"] = float(draws.std(ddof=1))
    return out


def fixed_step_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """Mean b, range, and median t of the fixed-step samples, per step. Reported only. panel has one row per session."""
    table = inf.fixed_step_table(panel, "log_rv30", FULL, IV, panel["primary"].to_numpy(), FIXED_STEPS)
    return table.groupby("step").agg(samples=("n", "size"), median_n=("n", "median"), mean_b=("coefficient", "mean"), min_b=("coefficient", "min"), max_b=("coefficient", "max"), median_t=("classical_t", "median")).reset_index()


def mean_interval(values: np.ndarray, positions: np.ndarray, block: int, reps: int) -> dict:
    """Mean of a row-level series, with its bootstrap t and percentile interval."""
    draws = inf.block_bootstrap(lambda index: np.array([values[index].mean()]), positions, block, reps, SEED + block)
    summary = inf.bootstrap_summary(np.array([values.mean()]), draws)
    return dict(mean=float(values.mean()), t=float(summary["t"][0]), low=float(summary["low"][0]), high=float(summary["high"][0]))


def same_row_race(panel: pd.DataFrame, reps: int = REPS) -> dict:
    """HAR against HAR+ATM30 on the same rows, with and without the Duan factor.

    Both models train on all primary rows with a target window that ends on or before the origin. No row needs a GARCH
    or EWMA value. Scoring starts at position 252, and each origin needs 126 training rows. panel has one row per session.
    """
    primary = panel["primary"].to_numpy()
    score = primary & (panel["position"].to_numpy() >= fc.START_SESSIONS)
    small = fc.expanding_forecasts(panel, HAR, primary, score, smearing=False)
    big = fc.expanding_forecasts(panel, FULL, primary, score, smearing=False)
    small_duan = fc.expanding_forecasts(panel, HAR, primary, score, smearing=True)
    big_duan = fc.expanding_forecasts(panel, FULL, primary, score, smearing=True)
    scored = np.isfinite(small) & np.isfinite(big)
    out = dict(scored=int(scored.sum()), first_scored=panel["session_date"][scored].min() if scored.any() else None)
    if scored.sum() < 2 * BLOCKS[0]:
        return out
    target = panel["rv30"].to_numpy(dtype=float)[scored]
    positions = panel["position"].to_numpy()[scored]
    log_target, log_small, log_big = np.log(target), np.log(small[scored]), np.log(big[scored])
    adjusted = inf.clark_west(log_target, log_small, log_big)
    out["clark_west"] = mean_interval(adjusted, positions, BLOCKS[0], reps)
    out["clark_west_block63"] = mean_interval(adjusted, positions, BLOCKS[1], reps)
    out["qlike_duan"] = mean_interval(fc.qlike(target, big_duan[scored]) - fc.qlike(target, small_duan[scored]), positions, BLOCKS[0], reps)
    out["qlike_no_factor"] = mean_interval(fc.qlike(target, big[scored]) - fc.qlike(target, small[scored]), positions, BLOCKS[0], reps)
    out["mean_target"] = float(target.mean())
    out["mean_forecast"] = dict(duan_har=float(small_duan[scored].mean()), duan_har_atm=float(big_duan[scored].mean()), no_factor_har=float(small[scored].mean()), no_factor_har_atm=float(big[scored].mean()))
    return out


def without_events(rows: pd.DataFrame, event_sessions: list[pd.Timestamp]) -> pd.DataFrame:
    """Drop each origin with an event session in its target window."""
    inside = np.zeros(len(rows), dtype=bool)
    for day in event_sessions:
        inside |= ((rows["session_date"] < day) & (rows["window_end"] >= day)).to_numpy()
    return rows[~inside]


def decide(floor: dict, rule1: dict, race: dict) -> dict:
    """Apply the outcome rules in order. The first match is the outcome. The labels apply only to "Supported"."""
    lows = [rule1.get(f"low{block}", np.nan) for block in BLOCKS]
    highs = [rule1.get(f"high{block}", np.nan) for block in BLOCKS]
    has_scores = race.get("scored", 0) >= MIN_SCORED and "clark_west" in race
    rule2 = bool(has_scores and race["clark_west"]["t"] > CW_LIMIT)
    rule3 = bool(has_scores and race["qlike_duan"]["high"] < 0)
    passed1 = bool(np.isfinite(lows).all() and min(lows) > 0)
    if not floor["passed"]:
        return dict(outcome=NO_FLOOR, rule1=False, also_out_of_sample=False, usable_gain=False)
    if passed1:
        return dict(outcome=SUPPORTED, rule1=True, also_out_of_sample=rule2, usable_gain=rule3)
    if np.isfinite(highs).all() and max(highs) < LIMIT_NO_EVENTS:
        return dict(outcome=SMALLER, rule1=False, also_out_of_sample=False, usable_gain=False)
    return dict(outcome=INCONCLUSIVE, rule1=False, also_out_of_sample=False, usable_gain=False)


def interval_excludes_zero(result: dict | None) -> bool:
    if result is None:
        return False
    lows = [result.get(f"low{block}", np.nan) for block in BLOCKS]
    return bool(np.isfinite(lows).all() and min(lows) > 0)


def verdict_line(decision: dict, rule1: dict, no_events: dict | None, race: dict, period: str = "2016-01 to 2018-04 only") -> str:
    """The required statements of each verdict line."""
    parts = [decision["outcome"]]
    if decision["also_out_of_sample"]:
        parts.append("also out-of-sample")
    if decision["usable_gain"]:
        parts.append("with usable gain")
    line = [", ".join(parts) + ".", f"{period}.", 'The "95%" intervals really cover about 80% to 91% in simulation.']
    if decision["outcome"] == INCONCLUSIVE:
        line.append(f"The sign of b is {'positive' if rule1['b'] > 0 else 'not positive'}.")
    if decision["outcome"] == SMALLER:
        line.append("This does not say that b is zero.")
    if decision["outcome"] == SUPPORTED:
        if not interval_excludes_zero(no_events):
            line.append("With events only; the ordinary-day question stays open.")
        if "qlike_no_factor" in race and np.sign(race["qlike_duan"]["mean"]) != np.sign(race["qlike_no_factor"]["mean"]):
            line.append("The QLIKE difference has opposite signs with and without the Duan factor.")
    return " ".join(line)


def evaluate(panel: pd.DataFrame, event_sessions: list[pd.Timestamp], reps: int = REPS, period: str = "2016-01 to 2018-04 only") -> dict:
    """All rule results on one panel, with one row per session. The outcome depends only on the floor and the rules above."""
    floor = data_floor(panel["primary"].to_numpy())
    rows = panel[panel["primary"]]
    result = dict(floor=floor, sessions=len(panel))
    if rows.empty:
        decision = decide(floor, {}, {})
        return dict(result, decision=decision, line=f"{decision['outcome']}. {period}.")
    rule1 = intervals(rows, reps)
    minimum = len(FULL) + 2
    calm = without_events(rows, event_sessions)
    no_events = intervals(calm, reps) if len(calm) >= minimum else None
    race = same_row_race(panel, reps)
    decision = decide(floor, rule1, race)
    tier1 = rows[rows["tier"] == 1]
    result.update(rule1=rule1, no_events=no_events, race=race, decision=decision, line=verdict_line(decision, rule1, no_events, race, period),
                  fixed_steps=fixed_step_summary(panel).to_dict("records"), tier1=intervals(tier1, reps) if len(tier1) >= minimum else None,
                  upper_against=dict(limit_no_events=LIMIT_NO_EVENTS, limit_with_events=LIMIT_WITH_EVENTS, max_upper=max(rule1["high21"], rule1["high63"])),
                  each_event_dropped={str(day.date()): intervals(without_events(rows, [day]), reps) for day in event_sessions})
    return result
