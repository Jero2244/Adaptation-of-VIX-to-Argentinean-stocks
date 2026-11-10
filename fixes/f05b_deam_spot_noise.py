"""Fix step 4 (F2): how much does an error in the spot move the de-Americanized term IV? Synthetic only. DEVELOPMENT work.

The tree recipe takes the spot from the Nasdaq mid, because parity does not hold for American options. So a spot error enters the forward and the IV.
Setup: S = 30, strike step 1, true vol .65, rate .05, 2% dividend at mid-term, tight quotes. The recipe gets S*(1+eps) instead of S.
"""
from common import *  # noqa
import deam

S, step, sigma, r, dy = 30.0, 1.0, 0.65, 0.05, 0.02
rows = []
for days in (10, 20, 30, 45):
    T = days / 365
    divs = [(T / 2, dy * S)]
    ch = pd.DataFrame([dict(strike=K, right=rt, mid=deam.crr_american(S, K, T, r, sigma, divs, rt, 1000)) for K in np.arange(step, 3 * S, step) if abs(np.log(K / S)) < 0.25 for rt in "CP"])
    q = ch.assign(bid=ch.mid * 0.9999, ask=ch.mid * 1.0001, age=0.0)
    for eps in (-0.005, -0.003, -0.001, 0.0, 0.001, 0.003, 0.005):
        new = deam.term_iv_american(q, int(days * 1440), r, S * (1 + eps), divs)
        rows.append(dict(days=days, spot_error=eps, iv_error=new["iv"] / sigma - 1))
t = pd.DataFrame(rows).pivot(index="spot_error", columns="days", values="iv_error")
print(LABEL)
print("Relative error of the tree-based term IV for a given relative error of the spot (rows) and days to expiry (columns):")
print(t.round(4).to_string())
