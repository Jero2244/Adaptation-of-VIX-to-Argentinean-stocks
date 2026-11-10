"""c2: apply the draft rules, unchanged, to contiguous 585-session windows of real pre-2025-03 panel rows. Also the row and window counts.
No forced b. The windows overlap, so about three are independent. Reads data/forecast_panel.parquet only."""
import sys, os
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sim_core import load_pool, arrays, evaluate_rules, L_GRID
pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 200)
g = load_pool("all")
v0, X0, y0 = arrays(g)
X0, y0 = np.nan_to_num(X0), np.nan_to_num(y0)
rng = np.random.default_rng(7)
rows = []
for start in range(0, len(g) - L_GRID + 1, 42):
    grid = np.arange(start, start + L_GRID)
    v = v0[grid]
    gr = np.flatnonzero(v)
    r = evaluate_rules(X0[grid][v], y0[grid][v], v, gr, 500, rng, 0.0, (None,))
    d = g.session_date.iloc[grid]
    tier2 = float((g.tier.iloc[grid][v] == 2).mean())
    rows.append(dict(first=d.iloc[0].date(), last=d.iloc[-1].date(), n=r["n"], cover=round(v.mean(), 3), tier2=round(tier2, 3), scored=r["scored"], span=round(r["scored_span"], 1),
                     fsn_med=r["fs_n_med"], fsn_min=r["fs_n_min"], b=round(r["None|b"], 3), low=round(r["None|low"], 3), high=round(r["None|high"], 3), se=round(r["se"], 3),
                     fs_mean=round(r["None|fs_mean"], 3), fs_t=round(r["None|fs_medt"], 2), cw=round(r["None|cw_t"], 2), qd=round(r["None|qd"], 3), qd_u=round(r["None|qd_u"], 3), qn=round(r["None|qn"], 3), qn_u=round(r["None|qn_u"], 3),
                     R1a=r["None|r1a"], R1b=r["None|r1b"], R2=r["None|r2"], R3=r["None|r3"], S=r["None|S"], G=r["None|G"], NS=r["None|NS"]))
t = pd.DataFrame(rows)
print(t.to_string())
t.to_csv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "c2_dryrun.csv"), index=False)
print(t[["R1a", "R1b", "R2", "R3", "S", "G", "NS"]].mean().round(3))
print("Outcome share", dict(S=round(t.S.mean(), 3), NS=round(t.NS.mean(), 3), Inconclusive=round((~t.S & ~t.NS).mean(), 3)))
print("median width", round((t.high - t.low).median(), 3), "median se", t.se.median())
print("corr(b, tier2)", round(t.b.corr(t.tier2), 2), "corr(b, cover)", round(t.b.corr(t.cover), 2))
