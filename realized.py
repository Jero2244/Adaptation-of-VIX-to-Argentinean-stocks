"""Stage 3: total returns and realized variance from official closes. Rules are in PROTOCOL.md.

total_returns follows session_returns in options-valuation-model/adr/returns_v1.py. The original is not edited.
The overnight and open-to-close split is new here.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import EQUITY_OFFICIAL_DAILY, DataFault, load_cash_events, require_open

WINDOW_DAYS = 30
CALENDAR_ANNUAL = 365 / WINDOW_DAYS
SENSITIVITY_SESSIONS = 21
SESSIONS_PER_YEAR = 252
HAR_LENGTHS = (1, 5, 22)
DAILY_VARIANCE_FLOOR = 1e-6  # An absolute daily return of 0.1%. 17 sessions have a zero return, and log(0) is undefined.


def load_sessions() -> pd.DataFrame:
    """One row per session: open, close, and the cash that goes ex on that session. The gate runs before the return."""
    daily = pd.read_parquet(EQUITY_OFFICIAL_DAILY).sort_values("session_date").reset_index(drop=True)
    first, last = require_open(daily["session_date"].iloc[0], daily["session_date"].iloc[-1])
    events = load_cash_events(first, last)
    return attach_cash(daily.rename(columns={"official_open_price": "open", "official_close_price": "close"})[["session_date", "open", "close"]], events)


def attach_cash(frame: pd.DataFrame, events: pd.DataFrame) -> pd.DataFrame:
    """Add cash columns. An ex-date that is not a session stops the run, because its cash would be lost."""
    missing = events.loc[~events["ex_date"].isin(frame["session_date"]), "ex_date"]
    if len(missing):
        raise DataFault("An ex-date is not a session", missing)
    out = frame.copy()
    for column, kind in (("dividend_cash", "dividend"), ("rights_cash", "rights")):
        amounts = events[events["kind"] == kind].groupby("ex_date")["usd_per_ads"].sum()
        out[column] = out["session_date"].map(amounts).fillna(0.0).astype(float)
    return out


def total_returns(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the total, price, overnight, and open-to-close log returns. The first session has no return.

    Cash goes in the overnight part, because the stock goes ex at the open. With cash, overnight plus open-to-close
    differs slightly from the total return, because the log of a sum is not additive.
    """
    dates = frame["session_date"]
    if not (dates.is_unique and dates.is_monotonic_increasing):
        raise ValueError("Sessions are not unique and in order")
    if frame[["open", "close", "dividend_cash", "rights_cash"]].isna().any().any():
        raise ValueError("A price or a cash value is missing")
    if not ((frame["close"] > 0).all() and (frame["open"] > 0).all()):
        raise ValueError("A price is not positive")
    if (frame[["dividend_cash", "rights_cash"]] < 0).any().any():
        raise ValueError("A cash value is negative")
    out = frame.reset_index(drop=True).copy()
    out.insert(0, "position", np.arange(len(out), dtype="int64"))
    previous = out["close"].shift(1)
    cash = out["dividend_cash"] + out["rights_cash"]
    out["return_price"] = np.log(out["close"] / previous)
    out["return_total"] = np.log((out["close"] + cash) / previous)
    out["return_overnight"] = np.log((out["open"] + cash) / previous)
    out["return_intraday"] = np.log(out["close"] / out["open"])
    return out


def forward_realized(frame: pd.DataFrame) -> pd.DataFrame:
    """Add the realized variance after each origin close. A window with no full data stays blank.

    rv30 sums squared total returns on sessions in (origin, origin + 30 calendar days], annualized with 365/30.
    rv21 is the sensitivity target: the next 21 sessions, annualized with 252/21.
    """
    out = frame.copy()
    dates = out["session_date"].to_numpy()
    window_end = dates + np.timedelta64(WINDOW_DAYS, "D")
    last = np.searchsorted(dates, window_end, side="right")
    complete = window_end <= dates[-1]
    out["window_end"] = window_end
    out["window_sessions"] = np.where(complete, last - np.arange(len(dates)) - 1, -1)

    def window_sum(returns: np.ndarray) -> np.ndarray:
        running = np.concatenate([[0.0], np.cumsum(np.nan_to_num(returns) ** 2)])
        total = running[last] - running[np.arange(len(dates)) + 1]
        return np.where(complete, total, np.nan)

    out["rv30"] = CALENDAR_ANNUAL * window_sum(out["return_total"].to_numpy())
    out["rv30_overnight"] = CALENDAR_ANNUAL * window_sum(out["return_overnight"].to_numpy())
    out["rv30_intraday"] = CALENDAR_ANNUAL * window_sum(out["return_intraday"].to_numpy())
    running = np.concatenate([[0.0], np.cumsum(np.nan_to_num(out["return_total"].to_numpy()) ** 2)])
    future = np.full(len(dates), np.nan)
    count = len(dates) - SENSITIVITY_SESSIONS
    future[:count] = running[SENSITIVITY_SESSIONS + 1:] - running[1:count + 1]
    out["rv21"] = SESSIONS_PER_YEAR / SENSITIVITY_SESSIONS * future
    return out


def trailing_realized(frame: pd.DataFrame, floor: float = DAILY_VARIANCE_FLOOR) -> pd.DataFrame:
    """Add log annualized RV over 1, 5, and 22 sessions through the origin close. The window ends at the origin."""
    out = frame.copy()
    squares = out["return_total"] ** 2
    for length in HAR_LENGTHS:
        daily = squares.rolling(length, min_periods=length).mean()
        out[f"log_rv{length}"] = np.log(SESSIONS_PER_YEAR * daily.clip(lower=floor))
    return out


def realized_from_closes(closes: pd.DataFrame, events: pd.DataFrame, floor: float = DAILY_VARIANCE_FLOOR) -> pd.DataFrame:
    """Total returns, targets, and HAR inputs from closes only. A close-only source has no overnight split, so those columns are dropped."""
    frame = attach_cash(closes.assign(open=closes["close"])[["session_date", "open", "close"]], events)
    out = trailing_realized(forward_realized(total_returns(frame)), floor)
    return out.drop(columns=["open", "return_overnight", "return_intraday", "rv30_overnight", "rv30_intraday"])


def build_realized(floor: float = DAILY_VARIANCE_FLOOR) -> pd.DataFrame:
    return trailing_realized(forward_realized(total_returns(load_sessions())), floor)
