"""c5: compare candidate verdict rules on the critic pickles, on the advocate simulation CSVs (read-only), and with a short 63-block check.
Also the first_session check, in memory only. Reads data/forecast_panel.parquet (session_date and needed columns) and the two simulation outputs."""
import os, sys, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sim_core import load_pool, arrays, L_GRID, ROOT
import inference as inf
import events as ev
pd.set_option("display.width", 220, "display.max_columns", 40, "display.max_rows", 200)
ADV = os.path.join(HERE, "..", "advocate")
T = (0.0, 0.25, 0.37, 0.62)


def table(get, label):
    rows = {}
    for t in T:
        b, lo, hi, se, fs, cw, qd_hi, qd, qn_hi, qn = get(t)
        r1a = lo > 0
        r2 = cw > 1.65
        duan = (qd < 0) & (qd_hi < 0)
        both = duan & (qn < 0) & (qn_hi < 0)
        c = {
            "A interval": r1a,
            "B advocate: interval+t1.30+R2": r1a & (fs > 1.30) & r2,
            "B2 draft: interval+t1.65+R2": r1a & (fs > 1.65) & r2,
            "C interval+R2": r1a & r2,
            "H interval+t1.30": r1a & (fs > 1.30),
        }
        for k in (1.25, 1.35, 1.5):
            c[f"D k={k}"] = b - 1.96 * k * se > 0
            c[f"G k={k}+R2"] = (b - 1.96 * k * se > 0) & r2
        c["Duan|A"] = r1a & duan
        c["Duan|C"] = r1a & r2 & duan
        c["Both|C"] = r1a & r2 & both
        c["Duan|B"] = r1a & (fs > 1.30) & r2 & duan
        c["Both|B"] = r1a & (fs > 1.30) & r2 & both
        c["NS b<=0"] = b <= 0
        for th in (.37, .459, .525, .622):
            c[f"NS hi<{th}"] = hi < th
        c["hi<.37 not b<=0"] = (hi < .37) & (b > 0)
        c["b<=0 not hi<.37"] = (b <= 0) & (hi >= .37)
        rows[t] = {k: float(np.mean(v)) for k, v in c.items()}
    print("\n==", label)
    print(pd.DataFrame(rows).round(3).to_string())
    return rows


for name in ("c1_main_all_63", "c1_main_no2019paso_63", "c1_main_no2019paso_126"):
    d = pd.read_pickle(os.path.join(HERE, name + ".pkl"))
    def get(t, d=d):
        g = lambda k: d[f"{t}|{k}"].astype(float).to_numpy()
        return g("b"), g("low"), g("high"), d.se.to_numpy(float), g("fs_medt"), g("cw_t"), g("qd_u"), g("qd"), g("qn_u"), g("qn")
    table(get, name)
    b0 = d["0.0|b"].astype(float).to_numpy()
    se = d.se.to_numpy(float)
    print("calibrated k: false-pass 2.5%", round(float(np.percentile(b0 / (1.96 * se), 97.5)), 2), "| 5%", round(float(np.percentile(b0 / (1.96 * se), 95)), 2))

adv = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(ADV, "a2_sim_*.csv")))], ignore_index=True)
adv = adv[(~adv.thin) & (adv.fs_n >= 17)]
print("\nadvocate rows", len(adv), "| columns ok")
def get_adv(t):
    a = adv[adv.true_b == t]
    return tuple(a[c].to_numpy(float) for c in ("b", "lo", "hi", "se", "fs_medt", "cw_t", "q_duan_hi", "q_duan", "q_none_hi", "q_none"))
table(get_adv, "advocate simulation, constant b, floor 17")
a0 = adv[adv.true_b == 0]
print("advocate sim: SD of b at b=0", round(a0.b.std(), 3), "median se", round(a0.se.median(), 3), "ratio", round(a0.b.std() / a0.se.median(), 2), "| by window", a0.groupby("start").apply(lambda g: round(g.b.std() / g.se.median(), 2)).to_dict())
print("calibrated k, advocate sim: 2.5%", round(float(np.percentile(a0.b / (1.96 * a0.se), 97.5)), 2), "| 5%", round(float(np.percentile(a0.b / (1.96 * a0.se), 95)), 2))
for t in T:
    a = adv[adv.true_b == t]
    print(f"b {t}: 63-block lower>0 {(a.lo63 > 0).mean():.3f}, 21 and 63 both {((a.lo > 0) & (a.lo63 > 0)).mean():.3f}, both +R2 {((a.lo > 0) & (a.lo63 > 0) & (a.cw_t > 1.65)).mean():.3f}, hi63<.37 {(a.hi63 < .37).mean():.3f}")

# Short 63-block check on the critic pools.
for kind in ("all", "no2019paso"):
    v0, X0, y0 = arrays(load_pool(kind))
    base = np.linalg.lstsq(X0[v0], y0[v0], rcond=None)[0][-1]
    X0n, y0n = np.nan_to_num(X0), np.nan_to_num(y0)
    rng = np.random.default_rng(55)
    rows = []
    for s in range(200):
        G = len(v0)
        starts = rng.integers(0, G, size=L_GRID // 63 + 2)
        grid = np.concatenate([(q + np.arange(63)) % G for q in starts])[:L_GRID]
        v = v0[grid]
        gr = np.flatnonzero(v)
        X, y = X0n[grid][v], y0n[grid][v]
        bh = np.linalg.lstsq(X, y, rcond=None)[0][-1]
        low = {}
        for block in (21, 63):
            dr = np.array([np.linalg.lstsq(X[i], y[i], rcond=None)[0][-1] for i in (inf.block_sample(gr, block, rng) for _ in range(150))])
            low[block] = (np.percentile(dr, 2.5), dr.std(ddof=1))
        rows.append((bh, low[21][0], low[63][0], low[21][1], low[63][1]))
    r = np.array(rows)
    out = {t: (float(np.mean(r[:, 1] + t - base > 0)), float(np.mean(r[:, 2] + t - base > 0)), float(np.mean((r[:, 1] + t - base > 0) & (r[:, 2] + t - base > 0)))) for t in T}
    print(kind, "lower>0 for (21, 63, both):", {k: tuple(round(x, 3) for x in v) for k, v in out.items()}, "| median se 21", round(float(np.median(r[:, 3])), 3), "se 63", round(float(np.median(r[:, 4])), 3))

# first_session check, in memory only.
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=["session_date", "window_end", "primary", "log_rv30", "log_rv1", "log_rv5", "log_rv22", "log_iv2"])
sessions = p.session_date.to_numpy()
print("\nfirst_session of 2017-08-13:", ev.first_session("2017-08-13", sessions).date(), "| of 2017-10-22:", ev.first_session("2017-10-22", sessions).date())
a = p[p.primary]
def bb(f):
    X = np.column_stack([np.ones(len(f)), f.log_rv1, f.log_rv5, f.log_rv22, f.log_iv2])
    return np.linalg.lstsq(X, f.log_rv30.to_numpy(float), rcond=None)[0][-1]
def inside(events):
    m = np.zeros(len(a), bool)
    for _, date in events:
        day = ev.first_session(date, sessions)
        m |= ((a.session_date < day) & (a.window_end >= day)).to_numpy()
    return m
extra = (("2017 PASO", "2017-08-13"), ("2017 midterm", "2017-10-22"))
print("no-event b, 9 events", round(bb(a[~inside(ev.EVENTS)]), 3), "| with 2017 dates added", round(bb(a[~inside(tuple(ev.EVENTS) + extra)]), 3))
for n in (len(ev.EVENTS), len(ev.EVENTS) + 2):
    rng = np.random.default_rng(1)
    draws = []
    for _ in range(300):
        pick = rng.choice(len(sessions) - 1, size=n, replace=False)
        m = np.zeros(len(a), bool)
        for q in pick:
            m |= ((a.session_date < sessions[q]) & (a.window_end >= sessions[q])).to_numpy()
        draws.append(bb(a[~m]))
    print("random drops, count", n, np.round(np.percentile(draws, [2.5, 50, 97.5]), 3))

t = pd.read_csv(os.path.join(HERE, "c2_dryrun.csv"))
t["r2"] = t.cw > 1.65
print("\nDry run, 28 windows: interval", int(t.R1a.sum()), "| interval+R2", int((t.R1a & t.R2).sum()), "| interval+t1.30+R2", int((t.R1a & t.R2 & (t.fs_t > 1.30)).sum()), "| with Duan gain on interval+R2", int((t.R1a & t.R2 & (t.qd < 0) & (t.qd_u < 0)).sum()), "| both", int((t.R1a & t.R2 & t.R3).sum()))
print("corrected k=1.35 in dry run", int(((t.b - 1.96 * 1.35 * t.se) > 0).sum()), "| k=1.35+R2", int((((t.b - 1.96 * 1.35 * t.se) > 0) & t.R2).sum()))
print("fixed-step median rows min", t.fsn_med.min(), "| windows with fewer than 17", int((t.fsn_med < 17).sum()), "| scored min", t.scored.min(), "| n min", t.n.min())
print("Corr of cw and b across windows", round(t.cw.corr(t.b), 2))
