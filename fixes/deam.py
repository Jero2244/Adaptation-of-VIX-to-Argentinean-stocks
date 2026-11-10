"""De-Americanization of the term IV (F2). DEVELOPMENT work on open data. Not part of the frozen pipeline.

For a term with a known cash dividend inside it, the out-of-the-money option at each chosen strike is inverted with a CRR
American tree (escrowed discrete dividend, as in audit/a05_american_bias.py). The forward comes from the spot and the dividend,
not from put-call parity, because parity does not hold for American options with a dividend.
"""
from math import exp, log, sqrt

import numpy as np
from scipy.optimize import brentq

import atm_index as atm

TREE_STEPS = 400


def crr_american(S, K, T, r, sigma, divs, right, n=TREE_STEPS):
    """American price on a CRR tree. divs = list of (t_div_years, cash). Escrowed model: the tree runs on S minus the PV of dividends."""
    dt = T / n
    u = exp(sigma * sqrt(dt))
    d = 1 / u
    q = (exp(r * dt) - d) / (u - d)
    disc = exp(-r * dt)
    divs = [(t, c) for t, c in divs if 0 < t < T]
    s0 = S - sum(c * exp(-r * t) for t, c in divs)
    j = np.arange(n + 1)
    st = s0 * u ** j * d ** (n - j)
    pay = (lambda s: np.maximum(s - K, 0)) if right == "C" else (lambda s: np.maximum(K - s, 0))
    am = pay(st)
    for i in range(n - 1, -1, -1):
        t = i * dt
        jj = np.arange(i + 1)
        node = s0 * u ** jj * d ** (i - jj)
        cum = node + sum(c * exp(-r * (td - t)) for td, c in divs if t < td)
        am = np.maximum(disc * (q * am[1:i + 2] + (1 - q) * am[:i + 1]), pay(cum))
    return float(am[0])


def implied_vol(price, S, K, T, r, divs, right, n=TREE_STEPS):
    f = lambda s: crr_american(S, K, T, r, s, divs, right, n) - price
    lo, hi = 0.02, 4.0
    try:
        if f(lo) > 0 or f(hi) < 0:
            return None
        return brentq(f, lo, hi, xtol=1e-6)
    except ValueError:
        return None


def model_forward(S, T, r, divs):
    return (S - sum(c * exp(-r * t) for t, c in divs if 0 < t < T)) * exp(r * T)


def term_iv_american(chain, minutes, rate, S, divs, n=TREE_STEPS):
    """Same output keys as atm_index.term_iv. Strikes come from the two-sided pairs; the OTM option's mid is inverted at each of the two strikes next to the model forward."""
    result = dict(minutes=minutes, forward=None, iv=None, tier=None, strike_low=None, strike_high=None, max_distance=None, max_age=None,
                  relative_spread=None, pairs=0, reason="")
    years = minutes / atm.YEAR_MINUTES
    pairs = atm.two_sided_pairs(chain)
    result["pairs"] = len(pairs)
    if pairs.empty:
        return dict(result, reason="no two-sided pair")
    F = model_forward(S, years, rate, divs)
    result["forward"] = F
    below, above = pairs[pairs.strike <= F], pairs[pairs.strike >= F]
    chosen = []
    if not below.empty:
        chosen.append(below.iloc[-1])
    if not above.empty and (not chosen or above.iloc[0]["strike"] != chosen[0]["strike"]):
        chosen.append(above.iloc[0])
    chosen = [row for row in chosen if abs(log(row["strike"] / F)) <= atm.MAX_STRIKE_DISTANCE]
    if not chosen:
        return dict(result, reason="no pair within the strike distance")
    solved = []
    for row in chosen:
        K = row["strike"]
        right = "C" if K >= F else "P"
        mid = row["call_mid"] if right == "C" else row["put_mid"]
        sig = implied_vol(mid, S, K, years, rate, divs, right, n)
        if sig is not None:
            solved.append((row, sig))
    if not solved:
        return dict(result, reason="no solution for IV")
    if len(solved) == 2:
        (lo, iv_lo), (hi, iv_hi) = solved
        w = log(F / lo["strike"]) / log(hi["strike"] / lo["strike"])
        iv, tier = iv_lo + w * (iv_hi - iv_lo), 1
    else:
        iv = solved[0][1]
        tier = 1 if solved[0][0]["strike"] == F else 2
    rows = [r for r, _ in solved]
    return dict(result, iv=iv, tier=tier, strike_low=min(r["strike"] for r in rows), strike_high=max(r["strike"] for r in rows),
                max_distance=max(abs(log(r["strike"] / F)) for r in rows), max_age=max(r["age"] for r in rows),
                relative_spread=max(r["relative_spread"] for r in rows), reason="ok")
