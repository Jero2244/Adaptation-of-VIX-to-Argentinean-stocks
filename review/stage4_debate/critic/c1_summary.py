"""Summarize the c1 runs. Floor A = median fixed-step rows >= 20. Reads only the pickles from c1_power.py."""
import glob, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 200)
T = (0.0, 0.25, 0.37, 0.62)
for path in sorted(glob.glob(os.path.join(HERE, "c1_main_*.pkl"))):
    d = pd.read_pickle(path)
    print("\n==", os.path.basename(path), "sims", len(d))
    print("rows median", d.n.median(), "p10", d.n.quantile(.1), "| scored median", d.scored.median(), "scored early median", d.scored_early.median(), "| span", round(d.scored_span.median(), 1), "| se median", round(d.se.median(), 3), "| fixed-step rows median", d.fs_n_med.median(), "| P(fixed-step median < 20)", round((d.fs_n_med < 20).mean(), 3), "| P(n<300)", round((d.n < 300).mean(), 3))
    rows = []
    for t in T:
        g = lambda k: d[f"{t}|{k}"].astype(float)
        r1a, r1b, r2, r3, r1 = (g(k).astype(bool) for k in ("r1a", "r1b", "r2", "r3", "R1"))
        S, G, NS = (g(k).astype(bool) for k in ("S", "G", "NS"))
        row = dict(b=t, R1a=r1a.mean(), R1b=r1b.mean(), R1=r1.mean(), R2=r2.mean(), R2_early=g("r2_early").astype(bool).mean(), R3duan=g("r3d").astype(bool).mean(), R3none=g("r3n").astype(bool).mean(), R3=r3.mean(),
                   S=S.mean(), G=G.mean(), NS=NS.mean(), NS_b=g("NS_b").astype(bool).mean(), NS_u=g("NS_u").astype(bool).mean(), Inc=(~S & ~NS).mean(), S_NS=g("S_and_NS").astype(bool).mean(), R1_NS=g("R1_and_NS").astype(bool).mean(),
                   anyrule=(r1a | r1b | r2).mean())
        row["S_floor"] = (S & (d.fs_n_med >= 20)).mean()
        row["phi_R1a_R1b"] = np.corrcoef(r1a, r1b)[0, 1]
        row["phi_R1_R2"] = np.corrcoef(r1, r2)[0, 1]
        rows.append(row)
    print(pd.DataFrame(rows).round(3).T.to_string())
    rows = []
    for t in T:
        g = lambda k: d[f"{t}|{k}"].astype(float)
        rows.append(dict(b=t, b_mean=g("b").mean(), b_sd=g("b").std(), width=(g("high") - g("low")).median(), high_min=g("high").min(), low90_pos=(g("l90") > 0).mean(), low95_pos=(g("low") > 0).mean(), high90_lt37=(g("u90") < .37).mean(), high95_lt37=(g("high") < .37).mean(), high90_lt25=(g("u90") < .25).mean(),
                         fs_t_med=g("fs_medt").median(), cw_med=g("cw_t").median(), cw165=(g("cw_t") > 1.65).mean(), cw_early=(g("cw_early") > 1.65).mean(), frozen165=(g("cw_frozen") > 1.65).mean(), frozen_dm165=(g("cw_frozen_dm") > 1.65).mean(),
                         fs_t_gt_165=(g("fs_medt") > 1.65).mean(), bias_none=g("bias_n").median(), bias_duan=g("bias_d").median(), qd_lt0=(g("qd") < 0).mean(), qn_lt0=(g("qn") < 0).mean(),
                         conflict_d_not_n=(g("r3d").astype(bool) & ~g("r3n").astype(bool)).mean(), conflict_n_not_d=(g("r3n").astype(bool) & ~g("r3d").astype(bool)).mean()))
    print(pd.DataFrame(rows).round(3).T.to_string())
    # Candidate replacement rule: interval plus a falsifier at .37, 90% two-sided.
    rows = []
    for t in T:
        g = lambda k: d[f"{t}|{k}"].astype(float)
        sup = g("low") > 0
        ns = g("u90") < 0.37
        sup90 = g("l90") > 0
        rows.append(dict(b=t, Sup95=sup.mean(), Sup90=sup90.mean(), Contradicts=ns.mean(), Inconclusive_95=(~sup & ~ns).mean(), Inconclusive_90=(~sup90 & ~ns).mean()))
    print(pd.DataFrame(rows).round(3).T.to_string())
