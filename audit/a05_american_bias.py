"""Audit step 5: how large is the error from treating American GGAL options as European in the ATM30 recipe?

Synthetic only. A CRR tree prices American calls and puts on a stock with one discrete cash dividend (escrowed-dividend model)
at a known flat volatility. The study's own term recipe (atm_index.term_iv: parity forward at the smallest |C-P|, Black
inversion of the call-put average, log-strike interpolation) then runs on those prices. Output: recovered IV / true vol - 1,
and recovered forward / true forward - 1. No project data is read.
"""
import sys
from math import exp, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
from atm_index import term_iv  # noqa: E402  (read-only import of the study's function)

pd.set_option("display.width", 200)


def american(S, K, T, r, sigma, div, t_div, right, n=600):
    """CRR American price with one cash dividend at t_div (escrowed). European price is returned too."""
    dt = T / n
    u = exp(sigma * sqrt(dt)); d = 1 / u
    q = (exp(r * dt) - d) / (u - d)
    disc = exp(-r * dt)
    pv = div * exp(-r * t_div) if 0 < t_div < T else 0.0
    s0 = S - pv
    j = np.arange(n + 1)
    st = s0 * u ** j * d ** (n - j)
    pay = (lambda s: np.maximum(s - K, 0)) if right == "C" else (lambda s: np.maximum(K - s, 0))
    am = pay(st); eu = am.copy()
    for i in range(n - 1, -1, -1):
        j = np.arange(i + 1)
        node = s0 * u ** j * d ** (i - j)
        t = i * dt
        cum = node + (div * exp(-r * (t_div - t)) if (0 < t_div < T and t < t_div) else 0.0)
        cont = disc * (q * am[1:i + 2] + (1 - q) * am[:i + 1])
        am = np.maximum(cont, pay(cum))
        eu = disc * (q * eu[1:i + 2] + (1 - q) * eu[:i + 1])
    return float(am[0]), float(eu[0])


rows = []
for S, step in ((30.0, 1.0), (10.0, 2.5), (60.0, 5.0)):
    for sigma in (0.45, 0.65, 1.0):
        for days in (10, 20, 30, 45):
            for r in (0.02, 0.05):
                for dy in (0.0, 0.02, 0.035):
                    T = days / 365
                    div, t_div = dy * S, T / 2
                    F_true = (S - div * exp(-r * t_div)) * exp(r * T)
                    strikes = [k for k in np.arange(step, 3 * S, step) if abs(np.log(k / S)) < 0.35]
                    chain = []
                    for K in strikes:
                        for right in "CP":
                            a, e = american(S, K, T, r, sigma, div, t_div, right)
                            chain.append(dict(strike=K, right=right, bid=a * 0.9999, ask=a * 1.0001, age=0.0, eu=e))
                    chain = pd.DataFrame(chain)
                    got = term_iv(chain, int(days * 1440), r)
                    eur = chain.assign(bid=chain.eu * 0.9999, ask=chain.eu * 1.0001)
                    base = term_iv(eur, int(days * 1440), r)
                    rows.append(dict(S=S, step=step, sigma=sigma, days=days, r=r, div_yield=dy, iv_err=got["iv"] / sigma - 1, fwd_err=got["forward"] / F_true - 1,
                                     iv_err_european=base["iv"] / sigma - 1, tier=got["tier"]))
out = pd.DataFrame(rows)
out.to_csv(Path(__file__).resolve().parent / "a05_american_bias.csv", index=False)
print("European prices through the same recipe (tree and interpolation error only): iv_err mean %.4f, min %.4f, max %.4f" % (out.iv_err_european.mean(), out.iv_err_european.min(), out.iv_err_european.max()))
print("\nAmerican prices, relative IV error of the term (recovered / true - 1), mean by dividend yield and days:")
print(out.pivot_table(index="div_yield", columns="days", values="iv_err", aggfunc="mean").round(4).to_string())
print("\nworst case by dividend yield and days:")
print(out.pivot_table(index="div_yield", columns="days", values="iv_err", aggfunc=lambda s: s.loc[s.abs().idxmax()]).round(4).to_string())
print("\nby rate (no dividend):")
print(out[out.div_yield == 0].pivot_table(index="r", columns="days", values="iv_err", aggfunc="mean").round(4).to_string())
print("\nforward error (recovered / true - 1), mean by dividend yield and days:")
print(out.pivot_table(index="div_yield", columns="days", values="fwd_err", aggfunc="mean").round(4).to_string())
print("\nby strike grid (S, step): mean and worst iv_err")
print(out.groupby(["S", "step"])["iv_err"].agg(["mean", "min", "max"]).round(4).to_string())
