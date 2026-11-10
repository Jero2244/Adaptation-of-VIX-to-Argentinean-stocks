"""Round 2 tables from a2_sim_*.csv, a1_dryrun.csv, a5_amended.csv. Panel read only for span counts (pre-2025-03 rows). Exploratory."""
import glob
from rules import *
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
s = pd.concat(pd.read_csv(f) for f in glob.glob("a2_sim_*.csv")).reset_index(drop=True)
u = s[~s.thin].copy()

print("1. SE check. Fixed real inputs per base window, so the spread of b is sampling only.")
g = u.groupby(["start", "true_b"]).agg(sd_b=("b", "std"), se21=("se", "median"), n=("b", "size"))
g["ratio"] = g.sd_b / g.se21
print(g.round(3).to_string())
print("by window, mean ratio", g.groupby("start").ratio.mean().round(3).to_dict(), "all", round(g.ratio.mean(), 3))
u["half63"] = (u.hi63 - u.lo63) / 3.92
print("median se63 approx", round(u.half63.median(), 3), "ratio sd/se63 by window", (u.groupby(["start", "true_b"]).b.std() / u.groupby(["start", "true_b"]).half63.median()).groupby("start").mean().round(3).to_dict())

print("\nInterval coverage of the true b, each tail (nominal 2.5%)")
u["miss_low"] = u.hi < u.true_b
u["miss_high"] = u.lo > u.true_b
u["miss_low63"] = u.hi63 < u.true_b
u["miss_high63"] = u.lo63 > u.true_b
u["skew"] = (u.lo + u.hi) / 2 - u.b
print(u.groupby("true_b")[["miss_low", "miss_high", "miss_low63", "miss_high63", "skew"]].mean().round(3).to_string())

print("\nOption table, share passing, all windows, no floor")
u["i21"] = u.lo > 0
u["i63"] = u.lo63 > 0
u["i2163"] = u.i21 & u.i63
u["fs13"] = u.i21 & (u.fs_mean > 0) & (u.fs_medt > 1.30)
u["fs165"] = u.i21 & (u.fs_mean > 0) & (u.fs_medt > 1.65)
u["r2"] = u.cw_t > 1.65
u["i_r2"] = u.i21 & u.r2
u["i2163_r2"] = u.i2163 & u.r2
u["fs13_r2"] = u.fs13 & u.r2
u["fs165_r2"] = u.fs165 & u.r2
cols = ["i21", "i63", "i2163", "fs165", "fs13", "r2", "i_r2", "i2163_r2", "fs13_r2", "fs165_r2"]
t = u.groupby("true_b")[cols].mean().round(3)
print(t.to_string())
print("by window at b=0 and .62")
print(u[u.true_b.isin([0, .62])].groupby(["start", "true_b"])[cols].mean().round(3).to_string())
print("Rule 2 given interval, b=0, .37, .62:", u.groupby("true_b").apply(lambda d: round(d.r2[d.i21].mean(), 3), include_groups=False).to_dict())

print("\nLabels: upper bound below .37, b at or below zero, upper below .25")
u["hi37"] = u.hi < .37
u["hi3763"] = u.hi63 < .37
u["b0"] = u.b <= 0
u["hi25"] = u.hi < .25
u["i21_hi37"] = u.i21 & u.hi37
print(u.groupby("true_b")[["hi37", "hi3763", "b0", "hi25", "i21_hi37"]].mean().round(3).to_string())

print("\nRule 3, gated by the interval")
u["duan"] = (u.q_duan < 0) & (u.q_duan_hi < 0)
u["none"] = (u.q_none < 0) & (u.q_none_hi < 0)
u["sign_differs"] = (u.q_duan < 0) & (u.q_none >= 0)
u["g_duan"] = u.i21 & u.duan
u["g_both"] = u.i21 & u.duan & u.none
u["g_i2163_duan"] = u.i2163 & u.duan
print(u.groupby("true_b")[["duan", "none", "g_duan", "g_both", "g_i2163_duan"]].mean().round(3).to_string())
print("sign differs given g_duan", u[u.g_duan].groupby("true_b").sign_differs.mean().round(3).to_dict())

print("\nFinal outcome tables on the simulation")
for name, gate in (("interval 21 only", u.i21), ("interval 21 and 63", u.i2163)):
    o = np.where(gate & u.duan, "Sup+gain", np.where(gate, "Sup", np.where(u.hi < .37, "Below", "Inc")))
    print(name)
    print(u.assign(o=o).groupby("true_b").o.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())

print("\nThinned to about 70%: pass rates")
v = s[s.thin].copy()
v["i21"] = v.lo > 0
v["i63"] = v.lo63 > 0
v["both"] = v.i21 & v.i63
print(v.groupby("true_b")[["i21", "i63", "both"]].mean().round(3).to_string(), "\nmedian origins", v.origins.median())

print("\n5. Floors on 55 rolling real windows (strict ends)")
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=CALC)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
a5 = pd.read_csv("a5_amended.csv")
rows = []
for m in pd.period_range("2018-05", "2022-11", freq="M"):
    a, e = m.to_timestamp(), (m + 27).to_timestamp(how="end").normalize()
    w = p[(p.session_date >= a) & (p.session_date <= e)].reset_index(drop=True).copy()
    w.loc[w.index < 22, HAR] = np.nan
    w.loc[w.window_end > e, "log_rv30"] = np.nan
    prim = w[[IV, "log_rv30"] + HAR].notna().all(axis=1).to_numpy()
    q = np.flatnonzero(prim)
    span = (q[-1] - q[0]) / 21
    counts = [prim[i:i + 21].sum() for i in range(q[0], q[-1] + 1, 21)]
    rows.append(dict(start=str(m), origins=prim.sum(), span=span, spans_ge10=sum(c >= 10 for c in counts), maxgap=np.diff(q).max()))
f = pd.DataFrame(rows).merge(a5[["start", "fs_n", "scored", "r1a", "cw_t"]], on="start")
print(f.describe().loc[["min", "50%", "max"]].round(2).to_string())
print("fail: fixed-step median<20", int((f.fs_n < 20).sum()), "<17", int((f.fs_n < 17).sum()), "span<20", int((f.span < 20).sum()), "spans_ge10<20", int((f.spans_ge10 < 20).sum()), "of those with r1a pass and median<20", int(((f.fs_n < 20) & f.r1a).sum()), "r1a pass", int(f.r1a.sum()))
print("Dry run, amended rows: interval only", round(a5.r1a.mean(), 3), "interval 21 and 63", round((a5.r1a & (a5.lo63 > 0)).mean(), 3), "Below .37", int((a5.hi < .37).sum()), "and also interval pass", int(((a5.hi < .37) & a5.r1a).sum()))
