"""In-sample: stronger controls, non-overlap diagnostics, instrument profile, spread within year, session gaps."""
import sys
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import inference as inf

p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
pd.set_option("display.width", 250, "display.max_columns", 50)

# Session gaps.
gaps = p.session_date.diff().dt.days
print("gaps>4 days:", p.loc[gaps > 4, "session_date"].dt.date.tolist(), gaps[gaps > 4].tolist())
bd = pd.bdate_range(p.session_date.min(), p.session_date.max())
print("sessions", len(p), "weekdays", len(bd))
miss = sorted(set(bd) - set(p.session_date))
print("missing weekdays by year", pd.Series([d.year for d in miss]).value_counts().sort_index().to_dict())
print([d.date().isoformat() for d in miss if d.year in (2018, 2019, 2022, 2025)])
print("window sessions dist", p.loc[p.window_sessions > 0, "window_sessions"].value_counts().sort_index().to_dict())
r = p.return_total
print("share |r|<0.1% (floor binds log_rv1):", (r.abs() < 1e-3).mean(), "zero:", (r == 0).sum())


def fit(frame, names, reps=1000, key=IV):
    frame = frame.dropna(subset=names + ["log_rv30"])
    y = frame.log_rv30.to_numpy(float)
    X = np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(float) for n in names])
    res = inf.ols(y, X)
    i = 1 + names.index(key)
    pos = frame.position.to_numpy()
    out = dict(n=len(frame), b=res["beta"][i], r2=res["r2"])
    for bl in (21, 63):
        d = inf.block_bootstrap(lambda idx: np.linalg.lstsq(X[idx], y[idx], rcond=None)[0][i:i + 1], pos, bl, reps, 20261104 + bl)
        out.update({f"t{bl}": res["beta"][i] / d.std(ddof=1), f"lo{bl}": np.percentile(d, 2.5), f"hi{bl}": np.percentile(d, 97.5)})
    return out


w = p.copy()
sq = w.return_total ** 2
for L in (66, 126):
    w[f"log_rv{L}"] = np.log(252 * sq.rolling(L, min_periods=L).mean())
ab = w.return_total.abs()
for L in (1, 5, 22, 66):
    w[f"log_ab{L}"] = np.log(ab.rolling(L, min_periods=L).mean().clip(lower=1e-3))
w["log_ewma_c"] = np.log(w.f_ewma_raw)
s = w[w.primary]

specs = {
    "primary HAR+IV": HAR + [IV],
    "HAR + rv66 + IV": HAR + ["log_rv66", IV],
    "HAR + rv66 + rv126 + IV": HAR + ["log_rv66", "log_rv126", IV],
    "abs-return HAR + IV": ["log_ab1", "log_ab5", "log_ab22", IV],
    "abs HAR + ab66 + IV": ["log_ab1", "log_ab5", "log_ab22", "log_ab66", IV],
    "HAR + log GARCH t + IV": HAR + ["log_garch_t", IV],
    "HAR + log EWMA + IV": HAR + ["log_ewma_c", IV],
}
base = s.dropna(subset=["log_rv126", "log_ab66"])
print("on identical rows with rv126:", len(base))
rows = []
for name, names in specs.items():
    rows.append(dict(spec=name, sample="own rows", **fit(s, names)))
    rows.append(dict(spec=name, sample="rows with rv126", **fit(base, names)))
print(pd.DataFrame(rows).round(3).to_string())

# Robust subset runs.
inside = np.zeros(len(s), bool)
import events as ev
sessions = p.session_date.to_numpy()
for _, date in ev.EVENTS:
    day = ev.first_session(date, sessions)
    inside |= ((s.session_date < day) & (s.window_end >= day)).to_numpy()
print("drop all events", fit(s[~inside], HAR + [IV]))
print("drop all events, HAR+rv66", fit(s[~inside], HAR + ["log_rv66", IV]))
print("drop 2025", fit(s[s.year != 2025], HAR + [IV]))
print("drop 2021 and 2025", fit(s[~s.year.isin([2021, 2025])], HAR + [IV]))
print("drop events and 2025", fit(s[(~inside) & (s.year != 2025)], HAR + [IV]))
print("drop events and 2024-25", fit(s[(~inside) & (~s.year.isin([2024, 2025]))], HAR + [IV]))
print("2018-2023 drop events", fit(s[(~inside) & (s.year <= 2023)], HAR + [IV]))
print("after format break", fit(s[s.session_date >= "2025-03-01"], HAR + [IV], reps=500))
print("2024-01..2025-02", fit(s[(s.session_date >= "2024-01-01") & (s.session_date < "2025-03-01")], HAR + [IV], reps=500))

# Non-overlap samples.
samples = inf.non_overlapping_samples(p.session_date.to_numpy(), p.primary.to_numpy())
seen = {}
rows = []
for off, smp in enumerate(samples):
    c = p.iloc[smp]
    X = np.column_stack([np.ones(len(c))] + [c[n].to_numpy(float) for n in HAR + [IV]])
    y = c.log_rv30.to_numpy(float)
    res = inf.ols(y, X)
    e = res["residuals"]
    nw = inf.newey_west_se(X, e, 3)
    # HC1
    bread = np.linalg.pinv(X.T @ X); sc = X * e[:, None]; hc = np.sqrt(np.diag(bread @ (sc.T @ sc) @ bread) * len(y) / (len(y) - X.shape[1]))
    has_paso = ((c.session_date < "2019-08-12") & (c.window_end >= "2019-08-12")).any()
    pc = c[(c.session_date < "2019-08-12") & (c.window_end >= "2019-08-12")]
    key = smp.tobytes()
    rows.append(dict(offset=off, dup=key in seen, n=len(c), b=res["beta"][-1], t_cl=res["beta"][-1] / res["classical_se"][-1], t_hc=res["beta"][-1] / hc[-1], t_nw3=res["beta"][-1] / nw[-1], ac1=np.corrcoef(e[1:], e[:-1])[0, 1], paso_origin=pc.session_date.dt.date.iloc[0] if len(pc) else None, paso_iv=pc.atm30.iloc[0] if len(pc) else np.nan))
    seen[key] = off
t = pd.DataFrame(rows)
print(t.round(3).to_string())
u = t[~t.dup]
print("distinct: n", len(u), "b mean", u.b.mean(), "median", u.b.median(), "share t_cl>2", (u.t_cl > 2).mean(), "share t_hc>2", (u.t_hc > 2).mean(), "share nw3>2", (u.t_nw3 > 2).mean(), "median t_hc", u.t_hc.median(), "median ac1", u.ac1.median())
print("all 21: b mean", t.b.mean(), "median", t.b.median())

# 2024 non-overlap range quoted in findings without a table.
s24 = p[p.primary & (p.year == 2024)]
v = (p.primary & (p.year == 2024)).to_numpy()
bs = []
for smp in inf.non_overlapping_samples(p.session_date.to_numpy(), v):
    c = p.iloc[smp]
    bs.append((len(c), inf.ols(c.log_rv30.to_numpy(float), np.column_stack([np.ones(len(c)), c[IV].to_numpy(float)]))["beta"][1]))
print("2024 MZ non-overlap n,b range", min(b for _, b in bs), max(b for _, b in bs), sorted(set(n for n, _ in bs)))

# Instrument profile by lag on identical days.
w2 = p.copy()
for L in (1, 2, 3, 5, 10, 15, 21, 42):
    w2[f"z{L}"] = w2[IV].shift(L)
zs = [f"z{L}" for L in (1, 2, 3, 5, 10, 15, 21, 42)]
same = w2[w2.primary].dropna(subset=zs)
y = same.log_rv30.to_numpy(float)
ex = np.column_stack([np.ones(len(same))] + [same[n].to_numpy(float) for n in HAR])
en = same[IV].to_numpy(float)
print("identical days n", len(same), "OLS b", inf.ols(y, np.column_stack([ex, en]))["beta"][-1])
for z in zs:
    res = inf.two_stage(y, ex, en, same[z].to_numpy(float))
    print(z, "b", round(res["beta"][-1], 3), "F", round(res["first_stage_f"], 1))
# Noise diagnostics. Autocorrelation of IV changes. Classical noise gives lag1 AC of changes near -noise/(2 noise + signal).
d = p[IV].diff()
dd = pd.DataFrame(dict(d=d, l=d.shift(1), l2=d.shift(2))).dropna()
print("AC1 of daily change in log IV2:", dd.d.corr(dd.l), "AC2", dd.d.corr(dd.l2), "var d", dd.d.var(), "implied noise var (=-cov1)", -dd.d.cov(dd.l))
print("var log iv2", p.loc[p.primary, IV].var())
for lab, mask in (("low spread", p.relative_spread <= p.relative_spread.quantile(1 / 3)), ("high spread", p.relative_spread > p.relative_spread.quantile(2 / 3))):
    x = dd[mask.reindex(dd.index).fillna(False)]
    print(lab, "AC1", x.d.corr(x.l), "noise var", -x.d.cov(x.l), "n", len(x))
# Noise share within HAR residualized IV.
sp = p[p.primary]
Xh = np.column_stack([np.ones(len(sp))] + [sp[n].to_numpy(float) for n in HAR])
ivres = inf.ols(sp[IV].to_numpy(float), Xh)["residuals"]
print("var IV residual on HAR", ivres.var(), "R2 of IV on HAR", 1 - ivres.var() / sp[IV].var())

# Spread terciles within year.
rows = []
sp = sp.copy()
for yr, c in sp.groupby("year"):
    rows.append(dict(year=yr, med_spread=c.relative_spread.median(), n=len(c)))
print(pd.DataFrame(rows).round(3).to_string())
sp["within"] = sp.groupby("year").relative_spread.transform(lambda x: pd.qcut(x, 3, labels=False))
dm = pd.get_dummies(sp.year, prefix="y", drop_first=True, dtype=float)
sp2 = pd.concat([sp, dm], axis=1)
for g in (0, 1, 2):
    print("within-year spread tercile", g, fit(sp2[sp2.within == g], HAR + list(dm.columns) + [IV]))
overall = pd.qcut(sp.relative_spread, 3, labels=False)
for yrs, lab in (((2018, 2019, 2020, 2021, 2022, 2023), "2018-23"), ((2024, 2025), "2024-25"), ((2026,), "2026")):
    print(lab, "share by overall tercile", overall[sp.year.isin(yrs)].value_counts(normalize=True).sort_index().round(2).to_dict())
