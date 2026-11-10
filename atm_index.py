"""ATM30: 30-day near-the-money Black implied volatility from a quote snapshot. Rules are in PROTOCOL.md.

constant_maturity follows options/volatility_index.py (total-variance interpolation, no extrapolation), and
parity_forward follows the forward step of single_term in the same file. The originals are not edited.
Black pricing is new here, because the option_analytics solver prices American lattices.
"""
from __future__ import annotations

from datetime import datetime, time
from math import erfc, exp, isfinite, log, sqrt
from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")
YEAR_MINUTES = 525600
TARGET_MINUTES = 30 * 1440
MAX_STRIKE_DISTANCE = 0.25
SNAPSHOT_TIME = time(15, 45)
EXPIRY_TIME = time(16, 0)


def expiry_minutes(expiration, session) -> int:
    """Minutes from the session's 15:45 New York snapshot to 16:00 New York on the expiration date."""
    end = datetime.combine(pd.Timestamp(expiration).date(), EXPIRY_TIME, NY)
    start = datetime.combine(pd.Timestamp(session).date(), SNAPSHOT_TIME, NY)
    return int((end.astimezone(ZoneInfo("UTC")) - start.astimezone(ZoneInfo("UTC"))).total_seconds() // 60)


def _norm_cdf(x: float) -> float:
    return 0.5 * erfc(-x / sqrt(2))


def black_call(forward: float, strike: float, total_vol: float) -> float:
    """Undiscounted Black call. total_vol is sigma * sqrt(T)."""
    if total_vol <= 0:
        return max(forward - strike, 0.0)
    d1 = log(forward / strike) / total_vol + total_vol / 2
    return forward * _norm_cdf(d1) - strike * _norm_cdf(d1 - total_vol)


def black_average(forward: float, strike: float, total_vol: float) -> float:
    """Undiscounted average of the Black call and put at one strike."""
    call = black_call(forward, strike, total_vol)
    return call + (strike - forward) / 2


def solve_total_vol(price: float, forward: float, strike: float, tolerance: float = 1e-10) -> float | None:
    """Total vol that gives an undiscounted call-put average. None if the price is at or below intrinsic value."""
    if not all(isfinite(v) for v in (price, forward, strike)) or forward <= 0 or strike <= 0:
        return None
    if price <= abs(forward - strike) / 2:
        return None
    low, high = 1e-8, 1.0
    while black_average(forward, strike, high) < price:
        high *= 2
        if high > 64:
            return None
    for _ in range(200):
        middle = (low + high) / 2
        if black_average(forward, strike, middle) < price:
            low = middle
        else:
            high = middle
        if high - low < tolerance:
            break
    return (low + high) / 2


def two_sided_pairs(chain: pd.DataFrame) -> pd.DataFrame:
    """Strikes where the call and the put both have 0 < bid <= ask. Columns: strike, call_mid, put_mid, age, spread."""
    valid = chain[(chain["bid"] > 0) & (chain["ask"] >= chain["bid"])]
    calls = valid[valid["right"] == "C"].set_index("strike")
    puts = valid[valid["right"] == "P"].set_index("strike")
    strikes = calls.index.intersection(puts.index).sort_values()
    if strikes.has_duplicates or calls.index.has_duplicates or puts.index.has_duplicates:
        raise ValueError("A strike appears twice for one expiry and right")
    call, put = calls.loc[strikes], puts.loc[strikes]
    mids = pd.DataFrame({"strike": strikes, "call_mid": ((call["bid"] + call["ask"]) / 2).values, "put_mid": ((put["bid"] + put["ask"]) / 2).values})
    mids["age"] = pd.concat([call["age"], put["age"]], axis=1).max(axis=1).values
    width = (call["ask"] - call["bid"]).values + (put["ask"] - put["bid"]).values
    mids["relative_spread"] = width / (mids["call_mid"] + mids["put_mid"]).values
    return mids


def parity_forward(pairs: pd.DataFrame, growth: float) -> float:
    """F = K + exp(rT) (C - P) at the strike with the smallest |C - P|."""
    best = pairs.loc[(pairs["call_mid"] - pairs["put_mid"]).abs().idxmin()]
    return float(best["strike"] + growth * (best["call_mid"] - best["put_mid"]))


def term_iv(chain: pd.DataFrame, minutes: int, rate: float) -> dict:
    """Near-forward IV of one expiry. Tier 1 has a forward bracketed by two strikes, or a strike at the forward. Tier 2 has one strike."""
    result = dict(minutes=minutes, forward=None, iv=None, tier=None, strike_low=None, strike_high=None, max_distance=None,
                  max_age=None, relative_spread=None, pairs=0, reason="")
    if minutes <= 0:
        return dict(result, reason="expired")
    pairs = two_sided_pairs(chain)
    result["pairs"] = len(pairs)
    if pairs.empty:
        return dict(result, reason="no two-sided pair")
    years = minutes / YEAR_MINUTES
    growth = exp(rate * years)
    forward = parity_forward(pairs, growth)
    result["forward"] = forward
    if forward <= 0:
        return dict(result, reason="non-positive forward")
    below = pairs[pairs["strike"] <= forward]
    above = pairs[pairs["strike"] >= forward]
    chosen = []
    if not below.empty:
        chosen.append(below.iloc[-1])
    if not above.empty and (not chosen or above.iloc[0]["strike"] != chosen[0]["strike"]):
        chosen.append(above.iloc[0])
    in_range = [row for row in chosen if abs(log(row["strike"] / forward)) <= MAX_STRIKE_DISTANCE]
    if not in_range:
        return dict(result, reason="no pair within the strike distance")
    solved = []
    for row in in_range:
        total_vol = solve_total_vol(growth * (row["call_mid"] + row["put_mid"]) / 2, forward, row["strike"])
        if total_vol is not None:
            solved.append((row, total_vol / sqrt(years)))
    if not solved:
        return dict(result, reason="no solution for IV")
    if len(solved) == 2:
        (low, iv_low), (high, iv_high) = solved
        weight = log(forward / low["strike"]) / log(high["strike"] / low["strike"])
        iv = iv_low + weight * (iv_high - iv_low)
        tier = 1
    else:
        iv = solved[0][1]
        tier = 1 if solved[0][0]["strike"] == forward else 2
    rows = [row for row, _ in solved]
    return dict(result, iv=iv, tier=tier, strike_low=min(r["strike"] for r in rows), strike_high=max(r["strike"] for r in rows),
                max_distance=max(abs(log(r["strike"] / forward)) for r in rows), max_age=max(r["age"] for r in rows),
                relative_spread=max(r["relative_spread"] for r in rows), reason="ok")


def bracket_terms(minutes_by_expiry: dict, target: int = TARGET_MINUTES, floor_minutes: int = 0) -> tuple | None:
    """Listed expiries that bracket the target: (near, far), or (exact, None). Expiries below the floor are not eligible."""
    eligible = sorted((m, e) for e, m in minutes_by_expiry.items() if m > floor_minutes)
    near = [e for m, e in eligible if m <= target]
    far = [e for m, e in eligible if m > target]
    if near and minutes_by_expiry[near[-1]] == target:
        return near[-1], None
    return (near[-1], far[0]) if near and far else None


def constant_maturity(near_minutes: int, near_variance: float, far_minutes: int, far_variance: float, target: int = TARGET_MINUTES) -> float:
    """Annualized variance at the target from linear interpolation of total variance."""
    weight_near = (far_minutes - target) / (far_minutes - near_minutes)
    weight_far = (target - near_minutes) / (far_minutes - near_minutes)
    return (weight_near * near_minutes * near_variance + weight_far * far_minutes * far_variance) / target
