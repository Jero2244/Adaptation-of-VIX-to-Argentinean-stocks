"""Stage 3: forward variance between the two expiries that straddle each listed Argentina event.

These are case studies with placebo dates and no p-values. A rise in 30-day IV alone is mechanical, so the measure is the
forward variance. The 2017 events belong to the locked 2016-01 to 2018-04 test, and they are not in this list.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from atm_index import YEAR_MINUTES

EVENTS = (
    ("2019 PASO", "2019-08-11"), ("2019 general", "2019-10-27"),
    ("2021 PASO", "2021-09-12"), ("2021 midterm", "2021-11-14"),
    ("2023 PASO", "2023-08-13"), ("2023 general", "2023-10-22"), ("2023 runoff", "2023-11-19"),
    ("2025 PBA", "2025-09-07"), ("2025 midterm", "2025-10-26"),
)
# The events of the one-time test. Use these only with the test's own session grid.
TEST_EVENTS = (("2017 PASO", "2017-08-13"), ("2017 midterm", "2017-10-22"))
MIN_NEAR_DAYS = 7
SEARCH_DAYS = 60
PLACEBO_STEP_DAYS = 28
PLACEBO_STEPS = 12
SAME_TERM_DAYS = 7


def first_session(date, sessions: np.ndarray) -> pd.Timestamp:
    """The first session on or after a date. All listed elections are on Sundays."""
    return pd.Timestamp(sessions[np.searchsorted(sessions, np.datetime64(pd.Timestamp(date)))])


def forward_variance(near_iv: float, near_minutes: float, far_iv: float, far_minutes: float) -> float:
    """Annualized variance implied between two expiries. It can be negative when the term structure falls fast."""
    return (far_iv ** 2 * far_minutes - near_iv ** 2 * near_minutes) / (far_minutes - near_minutes)


def event_within(start, end, event_sessions: list[pd.Timestamp]) -> bool:
    return any(pd.Timestamp(start) <= day <= pd.Timestamp(end) for day in event_sessions)


def straddle(terms: pd.DataFrame, event_session: pd.Timestamp, sessions: np.ndarray) -> dict | None:
    """Forward variance on the last session with a usable pair. The near expiry is before the event session and at least 7 days away."""
    earliest = event_session - pd.Timedelta(days=SEARCH_DAYS)
    candidates = sessions[(sessions < np.datetime64(event_session)) & (sessions >= np.datetime64(earliest))]
    by_session = {day: group for day, group in terms[terms["session_date"].isin(candidates)].groupby("session_date")}
    for observed in candidates[::-1]:
        observed = pd.Timestamp(observed)
        group = by_session.get(observed)
        if group is None:
            continue
        usable = group[group["iv"].notna()]
        near = usable[(usable["expiry"] < event_session) & (usable["minutes"] >= MIN_NEAR_DAYS * 1440)]
        far = usable[usable["expiry"] >= event_session]
        if near.empty or far.empty:
            continue
        near_row, far_row = near.sort_values("expiry").iloc[-1], far.sort_values("expiry").iloc[0]
        variance = forward_variance(near_row["iv"], near_row["minutes"], far_row["iv"], far_row["minutes"])
        return dict(observed=observed, near_expiry=near_row["expiry"], far_expiry=far_row["expiry"], near_days=near_row["minutes"] / 1440, gap_days=(far_row["expiry"] - near_row["expiry"]).days,
                    near_vol=near_row["iv"], far_vol=far_row["iv"], forward_variance=variance, forward_vol=np.sqrt(variance) if variance > 0 else np.nan, ratio=np.sqrt(variance) / near_row["iv"] if variance > 0 else np.nan, tier=max(near_row["tier"], far_row["tier"]))
    return None


def realized_between(returns: pd.DataFrame, start, end) -> float:
    """Annualized realized vol of total returns on sessions in (start, end], with the same calendar basis as the IV."""
    chosen = returns[(returns["session_date"] > pd.Timestamp(start)) & (returns["session_date"] <= pd.Timestamp(end))]
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    return float(np.sqrt((chosen["return_total"] ** 2).sum() * 365 / days)) if days > 0 and len(chosen) else np.nan


def event_table(terms: pd.DataFrame, returns: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """One row per event, and one row per placebo date. A placebo pair cannot contain any listed event."""
    sessions = returns["session_date"].to_numpy()
    event_sessions = [first_session(date, sessions) for _, date in EVENTS]
    event_rows, placebo_rows = [], []
    for (name, date), event_session in zip(EVENTS, event_sessions):
        found = straddle(terms, event_session, sessions)
        if found is None:
            event_rows.append(dict(event=name, election=date, event_session=event_session))
            continue
        row = dict(event=name, election=date, event_session=event_session, first_return=float(returns.loc[returns["session_date"] == event_session, "return_total"].iloc[0]), realized_vol_between=realized_between(returns, found["near_expiry"], found["far_expiry"]), **found)
        placebos = []
        for step in [s for s in range(-PLACEBO_STEPS, PLACEBO_STEPS + 1) if s]:
            shifted = pd.Timestamp(date) + pd.Timedelta(days=step * PLACEBO_STEP_DAYS)
            if not sessions[0] <= np.datetime64(shifted) <= sessions[-1]:
                continue
            placebo_session = first_session(shifted, sessions)
            candidate = straddle(terms, placebo_session, sessions)
            if candidate is None or abs(candidate["gap_days"] - found["gap_days"]) > SAME_TERM_DAYS:
                continue
            if event_within(candidate["observed"], candidate["far_expiry"], event_sessions):
                continue
            placebos.append(dict(event=name, step=step, placebo_session=placebo_session, **candidate))
        ratios = np.array([p["ratio"] for p in placebos if np.isfinite(p["ratio"])])
        row.update(placebo_count=len(ratios), placebo_median_ratio=float(np.median(ratios)) if len(ratios) else np.nan, share_placebos_below=float(np.mean(ratios < row["ratio"])) if len(ratios) and np.isfinite(row["ratio"]) else np.nan)
        event_rows.append(row)
        placebo_rows += placebos
    return pd.DataFrame(event_rows), pd.DataFrame(placebo_rows)
