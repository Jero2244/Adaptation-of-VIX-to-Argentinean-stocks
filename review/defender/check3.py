import sys
sys.path.insert(0, r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
import inference as inf, forecasts as fc, events as ev

ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
D = __import__("os").path.dirname(__import__("os").path.abspath(__file__))
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
r5 = pd.read_csv(D + r"\rv5m.csv", parse_dates=["session_date"])
print("5m days", len(r5), "ids max", r5.ids.max(), "bars med", r5.bars.median())
p = p.merge(r5[["session_date", "rv5", "first"]], on="session_date", how="left")
p["on2"] = np.log((np.exp(p["first"]) + p.dividend_cash + p.rights_cash) / p.close.shift(1)) ** 2
p["dv5"] = p.rv5 + p.on2
for L in (1, 5, 22):
    p[f"h5_{L}"] = np.log((252 * p.dv5.rolling(L, min_periods=L).mean()).clip(lower=252e-6))
H5 = ["h5_1", "h5_5", "h5_22"]
s = p[p.primary].dropna(subset=H5).copy()
print("rows with 5m HAR", len(s))
print("mean dv5 / mean r2", p.dv5.mean() / (p.return_total ** 2).mean())


def X(fr, names):
    return np.column_stack([np.ones(len(fr))] + [fr[c].to_numpy(float) for c in names])


def bt(fr, names, key=IV, blocks=(21, 63), reps=800, y="log_rv30"):
    yy = fr[y].to_numpy(float); XX = X(fr, names); k = 1 + names.index(key)
    f = inf.ols(yy, XX); pos = fr.position.to_numpy(); o = dict(n=len(fr), b=round(f["beta"][k], 3))
    for bl in blocks:
        if bl * 3 > pos[-1] - pos[0] + 1:
            continue
        d = inf.block_bootstrap(lambda i: np.linalg.lstsq(XX[i], yy[i], rcond=None)[0][k:k + 1], pos, bl, reps, 7 + bl)
        o[bl] = (round(f["beta"][k] / d.std(ddof=1), 2), round(np.percentile(d, 2.5), 3), round(np.percentile(d, 97.5), 3))
    return o


sessions = p.session_date.to_numpy()
evd = [ev.first_session(d, sessions) for _, d in ev.EVENTS]
def inside(fr, days):
    m = np.zeros(len(fr), bool)
    for x in days:
        m |= ((fr.session_date < x) & (fr.window_end >= x)).to_numpy()
    return m
s["ev"] = inside(s, evd)
print("\n== (a)")
print("study HAR all", bt(s, HAR + [IV]))
print("5m HAR all", bt(s, H5 + [IV]))
ne = s[~s.ev]
print("5m HAR no events", bt(ne, H5 + [IV]))
print("5m HAR no events 18-23", bt(ne[ne.session_date < "2024"], H5 + [IV]))
print("5m HAR no events pre 2025-03", bt(ne[ne.session_date < "2025-03-01"], H5 + [IV]))
print("5m HAR no events post 2025-03", bt(ne[ne.session_date >= "2025-03-01"], H5 + [IV], blocks=(21,)))
print("study HAR no events", bt(ne, HAR + [IV]))
print("study HAR no events pre 2025-03", bt(ne[ne.session_date < "2025-03-01"], HAR + [IV]))
print("study HAR no events post", bt(ne[ne.session_date >= "2025-03-01"], HAR + [IV], blocks=(21,)))
print("study HAR pre 2025-03 with events", bt(s[s.session_date < "2025-03-01"], HAR + [IV]))
print("5m HAR pre 2025-03 with events", bt(s[s.session_date < "2025-03-01"], H5 + [IV]))
print("5m HAR post 2025-03 with events", bt(s[s.session_date >= "2025-03-01"], H5 + [IV], blocks=(21,)))
print("5m HAR 18-23 with events", bt(s[s.session_date < "2024"], H5 + [IV]))
print("study HAR 2024-01..2025-02", bt(s[(s.session_date >= "2024") & (s.session_date < "2025-03-01")], HAR + [IV], blocks=(21,)))

# placebo drop: same count of pseudo events at random sessions
rng = np.random.default_rng(9)
pool = p.session_date[(p.session_date >= "2018-06-01") & (p.session_date <= "2026-09-01")].to_numpy()
for name, H in (("study", HAR), ("5m", H5)):
    b = []
    for _ in range(2000):
        days = [pd.Timestamp(x) for x in rng.choice(pool, 9, replace=False)]
        k = s[~inside(s, days)]
        b.append(inf.ols(k.log_rv30.to_numpy(float), X(k, H + [IV]))["beta"][-1])
    b = np.array(b); act = inf.ols(ne.log_rv30.to_numpy(float), X(ne, H + [IV]))["beta"][-1]
    print(name, "random-9 drop: median", round(np.median(b), 3), "p2.5", round(np.percentile(b, 2.5), 3), "p97.5", round(np.percentile(b, 97.5), 3), "event-drop", round(act, 3), "share random below", round((b < act).mean(), 4))

# Drop same count of high-vol windows chosen on ex ante IV (non-event)
# SSE gain decomposition
for name, H in (("study", HAR), ("5m", H5)):
    y = s.log_rv30.to_numpy(float)
    e0 = inf.ols(y, X(s, H))["residuals"]; e1 = inf.ols(y, X(s, H + [IV]))["residuals"]
    g = e0 ** 2 - e1 ** 2
    post = (s.session_date >= "2025-03-01").to_numpy(); evm = s.ev.to_numpy()
    paso = inside(s, [pd.Timestamp("2019-08-12")])
    print(name, "dR2", round(g.sum() / ((y - y.mean()) ** 2).sum(), 3), "SSE-gain share: event rows", round(g[evm].sum() / g.sum(), 3), "(rows", round(evm.mean(), 3), ") PASO rows", round(g[paso].sum() / g.sum(), 3), "post-break non-event", round(g[post & ~evm].sum() / g.sum(), 3), "(rows", round((post & ~evm).mean(), 3), ") pre-break non-event", round(g[~post & ~evm].sum() / g.sum(), 3), "(rows", round((~post & ~evm).mean(), 3), ")")

print("\n== (b)")
sall = p[p.primary]
paso_day = pd.Timestamp("2019-08-12")
vp = p.primary.to_numpy()
def fit_b(g, H=HAR):
    return inf.ols(g.log_rv30.to_numpy(float), X(g, H + [IV]))
rep = inf.non_overlapping_samples(p.session_date.to_numpy(), vp)
a = []
for sm in rep:
    g = p.iloc[sm]; m = inside(g, [paso_day])
    a.append((fit_b(g)["beta"][-1], fit_b(g[~m])["beta"][-1], g.session_date[m].dt.date.astype(str).tolist()))
print("report samples with/without PASO row")
for i, x in enumerate(a):
    print(i, round(x[0], 3), round(x[1], 3), x[2])
print("without: min", min(x[1] for x in a), "max", max(x[1] for x in a), "median", np.median([x[1] for x in a]))
for step in (22, 23):
    res = []
    for off in range(step):
        idx = np.arange(off + np.flatnonzero(vp)[0], len(p), step); idx = idx[vp[idx]]
        g = p.iloc[idx]; m = inside(g, [paso_day]); ev_m = inside(g, evd)
        f0 = fit_b(g); f1 = fit_b(g[~m]); f2 = fit_b(g[~ev_m])
        res.append(dict(off=off, n=len(g), paso=int(m.sum()), row=g.session_date[m].dt.strftime("%m-%d").tolist(), b=f0["beta"][-1], t=f0["beta"][-1] / f0["classical_se"][-1], b_nopaso=f1["beta"][-1], t_nopaso=f1["beta"][-1] / f1["classical_se"][-1], b_noev=f2["beta"][-1], t_noev=f2["beta"][-1] / f2["classical_se"][-1]))
    r = pd.DataFrame(res)
    print("step", step); print(r.round(3).to_string())
    print("means b, nopaso, noev", r.b.mean(), r.b_nopaso.mean(), r.b_noev.mean(), "range nopaso", r.b_nopaso.min(), r.b_nopaso.max(), "med t nopaso", r.t_nopaso.median(), "share t>2", (r.t_nopaso > 2).mean(), "noev med t", r.t_noev.median(), "share", (r.t_noev > 2).mean(), "with PASO row share", (r.paso > 0).mean())
    print("offsets with PASO row: b mean", r.b[r.paso > 0].mean(), "without", r.b_nopaso[r.paso > 0].mean(), "; offsets where missing: b mean", r.b[r.paso == 0].mean() if (r.paso == 0).any() else None)
full_np = s[~inside(s, [paso_day])]
print("pooled no PASO rows", fit_b(sall[~inside(sall, [paso_day])])["beta"][-1])

print("\n== (c)")
# lags on identical days
lags = (1, 2, 3, 5, 10, 21, 42, 63, 126)
q = p.copy()
for L in lags:
    q[f"z{L}"] = q[IV].shift(L)
same = q[q.primary].dropna(subset=[f"z{L}" for L in lags])
print("identical days", len(same))
print("OLS", round(fit_b(same)["beta"][-1], 3))
for L in lags:
    t = inf.two_stage(same.log_rv30.to_numpy(float), X(same, HAR), same[IV].to_numpy(float), same[f"z{L}"].to_numpy(float))
    print("lag", L, "2SLS", round(t["beta"][-1], 3), "F", round(t["first_stage_f"], 1))
# with fewer lags on larger sample
same2 = q[q.primary].dropna(subset=["z1", "z5", "z21"])
print("n", len(same2), "OLS", round(fit_b(same2)["beta"][-1], 3))
for L in (1, 5, 21):
    print("lag", L, round(inf.two_stage(same2.log_rv30.to_numpy(float), X(same2, HAR), same2[IV].to_numpy(float), same2[f"z{L}"].to_numpy(float))["beta"][-1], 3))
# decomposition fast vs slow
q["iv_slow"] = q[IV].shift(1).rolling(21, min_periods=15).mean()
q["iv_fast"] = q[IV] - q["iv_slow"]
sf = q[q.primary].dropna(subset=["iv_slow"])
print("slow/fast", bt(sf, HAR + ["iv_slow", "iv_fast"], key="iv_fast", blocks=(21,)), bt(sf, HAR + ["iv_slow", "iv_fast"], key="iv_slow", blocks=(21,)))

# same-day instrument: session last, and near vs far term
sl = q[q.primary].copy()
sl["iv_last"] = np.log(sl.atm30_session_last ** 2)
sl = sl.dropna(subset=["iv_last"])
print("corr iv, last", np.corrcoef(sl[IV], sl.iv_last)[0, 1], "share identical", float((np.abs(sl[IV] - sl.iv_last) < 1e-10).mean()), "sd diff", (sl[IV] - sl.iv_last).std())
diffs = sl[np.abs(sl[IV] - sl.iv_last) > 1e-10]
print("rows differing", len(diffs))
s2 = q[q.primary].copy()
s2["ly"] = s2.groupby("year").relative_spread.rank(pct=True)
s2["terc"] = pd.cut(s2.ly, [0, 1 / 3, 2 / 3, 1], labels=["low", "mid", "high"])
s2["log_near"] = np.log(s2.near_iv ** 2); s2["log_far"] = np.log(s2.far_iv ** 2)
print("near/far: corr", s2[["log_near", "log_far"]].corr().iloc[0, 1])

def tsls(g, end, z):
    g = g.dropna(subset=[end, z])
    return inf.two_stage(g.log_rv30.to_numpy(float), X(g, HAR), g[end].to_numpy(float), g[z].to_numpy(float))["beta"][-1], len(g)

dv = q[IV].diff()
print("\nwithin-year spread terciles")
for name in ("low", "mid", "high"):
    g = s2[s2.terc == name]
    o = fit_b(g)["beta"][-1]
    resv = inf.ols(g[IV].to_numpy(float), X(g, HAR))["residuals"].var()
    # Roll by tercile: autocov of dv at t, t-1 when t is in tercile
    idx = g.index
    d0 = dv.reindex(idx); d1 = dv.shift(-1).reindex(idx)
    noise = -np.nanmean((d0 - dv.mean()) * (d1 - dv.mean()))
    near_far = fit_b(g.assign(**{IV: g.log_far}).dropna(subset=[IV]))["beta"][-1]
    g2 = g.dropna(subset=["log_near", "log_far"])
    nf = tsls(g2, "log_far", "log_near")
    fn = tsls(g2, "log_near", "log_far")
    l1 = tsls(q.loc[idx], IV, "z1")
    gl = g.assign(iv_last=np.log(g.atm30_session_last ** 2))
    sl1 = tsls(gl, IV, "iv_last")
    evm = inside(g, evd)
    print(name, "n", len(g), "OLS", round(o, 3), "noevents", round(fit_b(g[~evm])["beta"][-1], 3), "| noise var", round(noise, 4), "resid IV var", round(resv, 3), "reliab", round(1 - noise / resv, 3), "implied unatten", round(o / (1 - noise / resv), 3), "| 2SLS lag1", round(l1[0], 3), "2SLS far by near", round(nf[0], 3), "near by far", round(fn[0], 3), "last", round(sl1[0], 3), "| mean logIV", round(g[IV].mean(), 3), "near_days", round(g.near_days.mean(), 1), "post-break", round((g.session_date >= "2025-03-01").mean(), 3), "tier2", round((g.tier == 2).mean(), 3), "event rows", round(evm.mean(), 3))
    b_ = bt(g, HAR + [IV], blocks=(21,), reps=500); print("    ", b_)
print("overall 2SLS far by near", tsls(s2, "log_far", "log_near"), "near by far", tsls(s2, "log_near", "log_far"), "OLS on these", round(fit_b(s2.dropna(subset=["log_near", "log_far"]))["beta"][-1], 3), "last", tsls(s2.assign(iv_last=np.log(s2.atm30_session_last ** 2)), IV, "iv_last"))

# interactions
s3 = s2.dropna(subset=["terc"]).copy()
s3["high"] = (s3.terc == "high").astype(float); s3["low"] = (s3.terc == "low").astype(float)
s3["iv_high"] = s3[IV] * s3.high; s3["iv_low"] = s3[IV] * s3.low
yd = pd.get_dummies(s3.year, prefix="y", drop_first=True, dtype=float)
s3 = pd.concat([s3, yd], axis=1); yc = list(yd.columns)
s3["ivc"] = s3[IV] - s3[IV].mean(); s3["iv_sq"] = s3.ivc ** 2
for lab, names in (("base", HAR + yc + ["high", "low", IV, "iv_high", "iv_low"]),
                   ("+IV^2", HAR + yc + ["high", "low", IV, "iv_sq", "iv_high", "iv_low"]),):
    print(lab, "high-minus-mid", bt(s3, names, key="iv_high", blocks=(21,), reps=500), "low-minus-mid", bt(s3, names, key="iv_low", blocks=(21,), reps=500))
# gradient without events and by era
for lab, g0 in (("no events", s3[~inside(s3, evd)]), ("pre-break", s3[s3.session_date < "2025-03-01"]), ("post-break", s3[s3.session_date >= "2025-03-01"]), ("no 2019", s3[s3.year != 2019])):
    print(lab, {t: round(fit_b(g0[g0.terc == t])["beta"][-1], 3) for t in ("low", "mid", "high")})
print("spread vs |return next window| corr, spread vs log_iv", round(s2.relative_spread.corr(s2[IV]), 3), "within-year rank vs IV", round(s2.ly.corr(s2[IV]), 3), "rank vs logrv30", round(s2.ly.corr(s2.log_rv30), 3), "rank vs near_days", round(s2.ly.corr(s2.near_days), 3))

print("\n== (d)")
Q = fc.qlike
sc = q.dropna(subset=["c_har", "c_har_atm", "m_har", "m_har_atm", "rv30"]).copy()
def scale_free(g, a, b, reps=800):
    tg = g.rv30.to_numpy(); fa = g[a].to_numpy(); fb = g[b].to_numpy(); pos = g.position.to_numpy()
    def stat(i):
        A, B = fa[i], fb[i]; T = tg[i]
        return np.array([(Q(T, A * np.mean(T / A)) - Q(T, B * np.mean(T / B))).mean()])
    v = stat(np.arange(len(g)))[0]
    d = inf.block_bootstrap(stat, pos, 21, reps, 13)
    return round(v, 4), round(v / d.std(ddof=1), 2), round(np.percentile(d, 2.5), 4), round(np.percentile(d, 97.5), 4)
for lab, g in (("all", sc), ("18-23", sc[sc.session_date < "2024"]), ("24-25", sc[(sc.session_date >= "2024") & (sc.session_date < "2026")]), ("26", sc[sc.session_date >= "2026"])):
    print(lab, "means c", round(g.c_har.mean(), 3), round(g.c_har_atm.mean(), 3), "m", round(g.m_har.mean(), 3), round(g.m_har_atm.mean(), 3), "tgt", round(g.rv30.mean(), 3))
    print("   scale-free m", scale_free(g, "m_har_atm", "m_har"), "scale-free c", scale_free(g, "c_har_atm", "c_har"))
    print("   raw qlike m", round((Q(g.rv30, g.m_har_atm) - Q(g.rv30, g.m_har)).mean(), 4), "c", round((Q(g.rv30, g.c_har_atm) - Q(g.rv30, g.c_har)).mean(), 4))
# ex ante intercept-correction: rolling scale of past mature rows (past 252 rows mean T/F per model)
def adapt(col):
    r = (q.rv30 / q[col])
    out = np.full(len(q), np.nan); d = q.session_date.to_numpy(); w = q.window_end.to_numpy(); f = q[col].to_numpy(); rr = r.to_numpy()
    for o in sc.index:
        ok = np.flatnonzero((w <= d[o]) & np.isfinite(rr) & (np.arange(len(q)) < o))
        if len(ok) >= 126:
            out[o] = f[o] * rr[ok[-252:]].mean()
    return pd.Series(out, index=q.index)[sc.index]
aa, bb = adapt("m_har_atm"), adapt("m_har")
tg = sc.rv30.to_numpy(); vv = np.isfinite(aa.to_numpy()) & np.isfinite(bb.to_numpy())
dq = (Q(tg, aa) - Q(tg, bb))
pos = sc.position.to_numpy()
draw = inf.block_bootstrap(lambda i: np.array([dq[vv][i].mean()]), pos[vv], 21, 1000, 2)
print("ex ante trailing-252 scale on no-smear forecasts: n", vv.sum(), "mean f", round(aa[vv].mean(), 3), round(bb[vv].mean(), 3), "diff", round(dq[vv].mean(), 4), "t", round(dq[vv].mean() / draw.std(ddof=1), 2), "ci", np.percentile(draw, [2.5, 97.5]).round(4))
for lab, m in (("18-23", sc.session_date < "2024"), ("24-25", (sc.session_date >= "2024") & (sc.session_date < "2026")), ("26", sc.session_date >= "2026")):
    mm = m.to_numpy() & vv; print(lab, round(dq[mm].mean(), 4), "mean f", round(aa[mm].mean(), 3), round(bb[mm].mean(), 3))

# raw dates log loss with and without PASO rows
vp2 = q.primary.to_numpy(); mk = q.f_har.notna().to_numpy()
q["nf_har"] = fc.expanding_forecasts(q, HAR, vp2, mk, smearing=False)
q["nf_har_atm"] = fc.expanding_forecasts(q, HAR + [IV], vp2, mk, smearing=False)
r = q.dropna(subset=["nf_har", "nf_har_atm", "rv30"])
ly = r.log_rv30.to_numpy(); ea = ly - np.log(r.nf_har_atm.to_numpy()); eh = ly - np.log(r.nf_har.to_numpy()); df = ea ** 2 - eh ** 2
pm = inside(r, [paso_day])
print("raw dates log MSE diff all", round(df.mean(), 4), "n", len(r), "PASO rows", pm.sum(), "mean in PASO rows", round(df[pm].mean(), 4), "excluding PASO", round(df[~pm].mean(), 4))
pp = r.position.to_numpy()
for lab, mm in (("all", np.ones(len(r), bool)), ("no paso", ~pm), ("before 2019-12-11", (r.session_date < "2019-12-11").to_numpy()), ("from 2019-12-11", (r.session_date >= "2019-12-11").to_numpy())):
    dr = inf.block_bootstrap(lambda i: np.array([df[mm][i].mean()]), pp[mm], 21, 1000, 4)
    print(lab, "n", mm.sum(), "diff", round(df[mm].mean(), 4), "t", round(df[mm].mean() / dr.std(ddof=1), 2), "ci", np.percentile(dr, [2.5, 97.5]).round(4))
