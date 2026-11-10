"""c4: operating table of candidate replacement rules, from the c1 pickles and c2 csv. No new data read, except the pool base b from the panel."""
import os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim_core import load_pool, arrays
pd.set_option("display.width", 200, "display.max_columns", 30)
for kind in ("all", "no2019paso"):
    v, X, y = arrays(load_pool(kind))
    print(kind, "pool b", round(np.linalg.lstsq(X[v], y[v], rcond=None)[0][-1], 3), "rows", int(v.sum()))
for name in ("c1_main_all_63", "c1_main_no2019paso_63", "c1_main_no2019paso_126"):
    d = pd.read_pickle(os.path.join(HERE, name + ".pkl"))
    print("\n==", name)
    print("sd of b / median bootstrap se:", round(d["0.0|b"].astype(float).std() / d.se.median(), 2), " sd", round(d["0.0|b"].astype(float).std(), 3))
    rows = []
    for t in (0.0, 0.25, 0.37, 0.62):
        g = lambda k: d[f"{t}|{k}"].astype(float)
        r1a, r3d, r3, r2 = g("r1a") > 0, g("r3d") > 0, g("r3") > 0, g("r2") > 0
        fz = g("cw_frozen_dm") > 1.65
        c = g("u90") < .37
        rows.append(dict(b=t, draft_S=(g("S") > 0).mean(), draft_NS=(g("NS") > 0).mean(), R1a=r1a.mean(), R1b_given_not_R1a=((g("r1b") > 0) & ~r1a).mean(), R1a_R2=(r1a & r2).mean(), R1a_frozen=(r1a & fz).mean(), phi_R1a_frozen=np.corrcoef(r1a, fz)[0, 1],
                         R1a_R3duan=(r1a & r3d).mean(), R1a_R3both=(r1a & r3).mean(), contradict95=(g("high") < .37).mean(), contradict90=c.mean(), R3duan_size=r3d.mean()))
    print(pd.DataFrame(rows).round(3).T.to_string())
    # R1a at the pooled pre-break b, by shift from b = .37. Sign and lower bound move by the same constant.
    for t in (0.525,):
        s = t - 0.37
        low = d["0.37|low"].astype(float) + s
        high = d["0.37|high"].astype(float) + s
        b = d["0.37|b"].astype(float) + s
        print(f"b {t}: lower bound > 0 {(low > 0).mean():.3f}, b <= 0 {(b <= 0).mean():.3f}, upper bound < .37 {(high < .37).mean():.3f}")
t = pd.read_csv(os.path.join(HERE, "c2_dryrun.csv"))
print("\nDry run: windows", len(t), "| R1a", int(t.R1a.sum()), "R1b", int(t.R1b.sum()), "R2", int(t.R2.sum()), "R3", int(t.R3.sum()), "S", int(t.S.sum()), "G", int(t.G.sum()), "NS", int(t.NS.sum()))
print("R3 Duan only:", int(((t.qd < 0) & (t.qd_u < 0)).sum()), "R3 none only:", int(((t.qn < 0) & (t.qn_u < 0)).sum()), "upper bound < .37:", int((t.high < .37).sum()), "min upper", t.high.min(), "max upper", t.high.max())
print("SD of b across windows", round(t.b.std(), 3), "range", t.b.min(), t.b.max(), "| median fixed-step t where interval excludes zero", t.fs_t[t.R1a].median(), "| fixed-step rows below 20:", int((t.fsn_med < 20).sum()), "| Supported and below 20:", int((t.S & (t.fsn_med < 20)).sum()))
print("Non-overlapping windows:")
print(t.iloc[[0, 13, 27]][["first", "last", "b", "low", "high", "fs_t", "cw", "qd", "qn", "R1a", "S", "NS"]].to_string())
print("coverage range", t.cover.min(), t.cover.max())
