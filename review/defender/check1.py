import sys
sys.path.insert(0, r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import inference as inf, forecasts as fc

p = pd.read_parquet(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation\data\forecast_panel.parquet")
print("cols", list(p.columns))
print("dates", p.session_date.min(), p.session_date.max(), len(p))
HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
s = p[p.primary].copy()
print("n primary", len(s))


def X(fr, names):
    return np.column_stack([np.ones(len(fr))] + [fr[c].to_numpy(float) for c in names])


def bt(fr, names, blocks=(21, 63, 126, 252), reps=1000, y="log_rv30"):
    yy = fr[y].to_numpy(float); XX = X(fr, names)
    b = inf.ols(yy, XX)
    pos = fr.position.to_numpy()
    k = 1 + names.index(IV)
    out = {"n": len(fr), "b": round(b["beta"][k], 3), "r2": round(b["r2"], 3)}
    for bl in blocks:
        d = inf.block_bootstrap(lambda i: np.linalg.lstsq(XX[i], yy[i], rcond=None)[0][k:k + 1], pos, bl, reps, 11 + bl)
        out[bl] = (round(b["beta"][k] / d.std(ddof=1), 2), round(np.percentile(d, 2.5), 3), round(np.percentile(d, 97.5), 3))
    return out


print("\n== A primary with long blocks", bt(s, HAR + [IV]))

# B stronger baseline
print("\n== B stronger baseline")
ss = s.dropna(subset=["log_ewma", "log_garch_t", "log_garch"]).copy()
r2 = ss["return_total"]
full = p.copy()
full["log_rv63"] = np.log((252 * (full.return_total ** 2).rolling(63, min_periods=63).mean()).clip(lower=252e-6))
full["log_ov22"] = np.log((252 * (full.return_overnight ** 2).rolling(22, min_periods=22).mean()).clip(lower=252e-6))
full["log_id22"] = np.log((252 * (full.return_intraday ** 2).rolling(22, min_periods=22).mean()).clip(lower=252e-6))
ss = ss.join(full[["log_rv63", "log_ov22", "log_id22"]])
print("HAR+IV same rows", bt(ss, HAR + [IV]))
print("+ewma", bt(ss, HAR + ["log_ewma", IV]))
print("+garch_t", bt(ss, HAR + ["log_garch_t", IV]))
print("+ewma+garch_t+rv63", bt(ss.dropna(subset=["log_rv63"]), HAR + ["log_ewma", "log_garch_t", "log_rv63", IV]))
print("+overnight,intraday22", bt(ss, HAR + ["log_ov22", "log_id22", IV]))
print("no rv1", bt(s, ["log_rv5", "log_rv22", IV], blocks=(21,)))

# floor
print("\n== floor")
for L in (1, 5, 22):
    d = (p.return_total ** 2).rolling(L, min_periods=L).mean()
    print(L, "floor binds on primary", int((d[p.primary] < 1e-6).sum()))
print("window_sessions", s.window_sessions.value_counts().sort_index().to_dict(), "mean annual factor", (s.window_sessions * 365 / 30).mean())

# by year Fama-MacBeth
print("\n== year FM")
bs = []
for y, g in s.groupby("year"):
    bs.append(inf.ols(g.log_rv30.to_numpy(), X(g, HAR + [IV]))["beta"][-1])
bs = np.array(bs); print(np.round(bs, 3), "mean", bs.mean(), "t", bs.mean() / (bs.std(ddof=1) / np.sqrt(len(bs))), "pos", (bs > 0).sum())

# C non-overlap
print("\n== C non overlap")
dates = p.session_date.to_numpy(); valid = p.primary.to_numpy()
samples = inf.non_overlapping_samples(dates, valid)
tab = inf.non_overlapping_table(p, "log_rv30", HAR + [IV], IV, valid)
print(tab[["offset", "n", "coefficient", "classical_t"]].round(3).to_string())
sets = [set(x.tolist()) for x in samples]
J = np.array([[len(a & b) / len(a | b) for b in sets] for a in sets])
iu = np.triu_indices(21, 1)
print("Jaccard median, mean, share pairs >.8", np.median(J[iu]), J[iu].mean(), (J[iu] > .8).mean())
# last-half coalescence: distinct positions by origin at each step late in sample
late = [tuple(x[x > np.quantile(np.flatnonzero(valid), .5)].tolist()) for x in samples]
print("distinct second-half paths", len(set(late)))
tail = [tuple(x[-20:].tolist()) for x in samples]
print("distinct last-20 paths", len(set(tail)))
print("unique rows used across all samples", len(set().union(*sets)), "of", valid.sum())
wk = pd.Series(np.concatenate(samples)); print("weekday share of sample origins", pd.to_datetime(p.session_date.iloc[wk]).dt.dayofweek.value_counts(normalize=True).sort_index().round(3).to_dict())
print("weekday share of all primary", s.session_date.dt.dayofweek.value_counts(normalize=True).sort_index().round(3).to_dict())

# fixed-step alternative that cannot merge: step on session grid of 22 and a calendar check
print("\n fixed session step, no coalescence")
for step in (22, 23):
    res = []
    for off in range(step):
        idx = np.arange(off + np.flatnonzero(valid)[0], len(p), step)
        idx = idx[valid[idx]]
        g = p.iloc[idx]
        overlap = (g.window_end.to_numpy()[:-1] > g.session_date.to_numpy()[1:]).sum()
        f = inf.ols(g.log_rv30.to_numpy(float), X(g, HAR + [IV]))
        res.append((len(g), f["beta"][-1], f["beta"][-1] / f["classical_se"][-1], overlap))
    r = pd.DataFrame(res, columns=["n", "b", "t", "overlaps"])
    print(step, "n med", r.n.median(), "b mean", round(r.b.mean(), 3), "b med", round(r.b.median(), 3), "min", round(r.b.min(), 3), "max", round(r.b.max(), 3), "t med", round(r.t.median(), 2), "share t>2", round((r.t > 2).mean(), 2), "overlap rows", int(r.overlaps.sum()))
# rows-weighted: pool of report samples
pooled = np.concatenate(samples)
g = p.iloc[pooled]; print("pooled stack of report samples b", inf.ols(g.log_rv30.to_numpy(float), X(g, HAR + [IV]))["beta"][-1])
# excluding Monday-Wed-Fri artifact: full sample by weekday
for d, g in s.groupby(s.session_date.dt.dayofweek):
    print("weekday", d, "n", len(g), "b", round(inf.ols(g.log_rv30.to_numpy(float), X(g, HAR + [IV]))["beta"][-1], 3))

# D instruments
print("\n== D noise")
ivs = p[IV]
dv = ivs.diff()
c1 = pd.concat([dv, dv.shift(1)], axis=1).dropna().cov().iloc[0, 1]
print("var dlogiv2", dv.var(), "autocov1", c1, "ac1", dv.autocorr(1))
same = s.dropna(subset=["log_iv2_lag1", "log_iv2_lag5"])
noise = -c1
res_var = inf.ols(same[IV].to_numpy(float), X(same, HAR))["residuals"].var()
print("Roll noise var", noise, "partial var iv", res_var, "reliability", 1 - noise / res_var, "implied b if unattenuated", .685 / (1 - noise / res_var))
Xb = X(same, HAR); y = same.log_rv30.to_numpy(float); e = same[IV].to_numpy(float)
z1 = same.log_iv2_lag1.to_numpy(float); z5 = same.log_iv2_lag5.to_numpy(float)
def est(i):
    o = np.linalg.lstsq(np.column_stack([Xb[i], e[i]]), y[i], rcond=None)[0][-1]
    a = inf.two_stage(y[i], Xb[i], e[i], z1[i])["beta"][-1]
    b = inf.two_stage(y[i], Xb[i], e[i], z5[i])["beta"][-1]
    return np.array([a - o, b - o])
base = est(np.arange(len(same)))
for bl in (21, 63):
    d = inf.block_bootstrap(est, same.position.to_numpy(), bl, 500, 5)
    print("diff IV1-OLS, IV5-OLS", base.round(3), "block", bl, "low", np.percentile(d, 2.5, axis=0).round(3), "high", np.percentile(d, 97.5, axis=0).round(3))
# stale check: exact repeats
print("share day-to-day |dlogiv2|<1e-6", float((dv.abs() < 1e-6).mean()))

# G 15:45
print("\n== G close IV", bt(p.assign(log_s=np.log(p.atm30_session_last ** 2)).dropna(subset=["log_s", "log_rv30"] + HAR).assign(**{}).rename(columns={IV: "old", "log_s": IV}), HAR + [IV], blocks=(21,), reps=300))
