"""Round 2: (a) raw-date decomposition, (b) fixed-step samples and the PASO row, (c) event-drop fairness, (d) dates read."""
import sys, os, zipfile
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import forecasts as fc, inference as inf, events as ev
from config import EQUITY_BBO
from load_data import member_day, SIDECARS

HERE = os.path.dirname(sys.argv[0])
p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
d = pd.read_parquet(os.path.join(HERE, "a3_intraday.parquet"))
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
primary = p.primary.to_numpy(); pos_all = p.position.to_numpy()

# (d)
print("(d) a3 parquet dates", d.session_date.min().date(), d.session_date.max().date(), len(d), "before 2018-05-01:", int((d.session_date < "2018-05-01").sum()))
with zipfile.ZipFile(EQUITY_BBO) as z:  # names only, nothing decoded
    days = [member_day(n) for n in z.namelist() if n not in SIDECARS]
print("(d) zip member days", min(days), max(days), len(days), "before 2018-05-01:", sum(str(x) < "2018-05-01" for x in days))
print("(d) panel dates", p.session_date.min().date(), p.session_date.max().date())


def boot(dv, pos, block=21, reps=2000):
    dr = inf.block_bootstrap(lambda i: np.array([dv[i].mean()]), pos, block, reps, 11)
    return np.round([dv.mean(), dv.mean() / dr.std(ddof=1), np.percentile(dr, 2.5), np.percentile(dr, 97.5)], 4).tolist()


# (a)
rawmask = primary & (pos_all >= 252)
dates = p.session_date
paso = ((dates < "2019-08-12") & (p.window_end >= "2019-08-12")).to_numpy()
late = (dates >= "2019-12-11").to_numpy()
y_all = p.rv30.to_numpy()
fc_all = {}
for smear in (True, False):
    h = fc.expanding_forecasts(p, HAR, primary, rawmask, smearing=smear)
    hi = fc.expanding_forecasts(p, HAR + [IV], primary, rawmask, smearing=smear)
    fc_all[smear] = (h, hi)
    dq_full = fc.qlike(y_all, hi) - fc.qlike(y_all, h)
    print(f"(a) training from 2018-06, smear={smear}")
    groups = [("raw dates, all", rawmask), ("raw, no PASO windows", rawmask & ~paso), ("raw, PASO windows only", rawmask & paso),
              ("2019-05-02..2019-12-10, no PASO", rawmask & ~paso & ~late), ("from 2019-12-11", rawmask & late)]
    total = np.nansum(dq_full[rawmask])
    for lab, m in groups:
        print("   ", lab, "n", int(m.sum()), boot(dq_full[m], pos_all[m]), "share of raw-date sum", round(np.nansum(dq_full[m]) / total, 2) if abs(total) > 1e-9 else "total about 0", "sum", round(np.nansum(dq_full[m]), 2))
    # Forecast and target levels in the early rows.
    for lab, m in (("PASO only", rawmask & paso), ("early no PASO", rawmask & ~paso & ~late)):
        print("    levels", lab, "f_har", round(h[m].mean(), 3), "f_hi", round(hi[m].mean(), 3), "y", round(y_all[m].mean(), 3))

# Short-training test: a fixed coefficient rule from late data cannot be run ex ante. Use a longer burn-in instead.
# Score no-PASO early rows under min_rows variants is not possible, so compare early rows by training size.
print("(a) rows in training at 2019-05-02:", int((primary & (p.window_end.to_numpy() <= np.datetime64("2019-05-02"))).sum()))

# (b)
def b_of(c, names=HAR + [IV]):
    X = np.column_stack([np.ones(len(c))] + [c[n].to_numpy(float) for n in names])
    r = inf.ols(c.log_rv30.to_numpy(float), X)
    return r["beta"][-1], r["beta"][-1] / r["classical_se"][-1]


first = int(np.flatnonzero(primary)[0])
for step in (22, 23):
    rows = []
    for off in range(step):
        c = p.iloc[np.arange(first + off, len(p), step)]
        c = c[c.primary]
        m = (c.session_date < "2019-08-12") & (c.window_end >= "2019-08-12")
        b, t = b_of(c); b2, t2 = b_of(c[~m])
        rows.append(dict(offset=off, n=len(c), b=b, t=t, b_no_paso=b2, t_no_paso=t2, paso_rows=int(m.sum()), origin=c[m].session_date.dt.date.iloc[0] if m.any() else None, iv=c[m].atm30.iloc[0] if m.any() else np.nan))
    t = pd.DataFrame(rows)
    print(f"(b) step {step}\n", t.round(3).to_string())
    print("   mean b", round(t.b.mean(), 3), "median t", round(t.t.median(), 2), "range", round(t.b.min(), 3), round(t.b.max(), 3), "| no PASO row: mean b", round(t.b_no_paso.mean(), 3), "median t", round(t.t_no_paso.median(), 2), "range", round(t.b_no_paso.min(), 3), round(t.b_no_paso.max(), 3), "| corr(b, PASO IV)", round(t.b.corr(t.iv), 2), "| sd b", round(t.b.std(), 3), "sd no PASO", round(t.b_no_paso.std(), 3))

# (c)
w = p.merge(d[["session_date", "rv_5m"]], on="session_date", how="left", validate="one_to_one")
daily = w.rv_5m + w.return_overnight ** 2
for L in (1, 5, 22):
    w[f"h_{L}"] = np.log(252 * daily.rolling(L, min_periods=L).mean().clip(lower=1e-6))
w["log_rv63"] = np.log(252 * (w.return_total ** 2).rolling(63, min_periods=63).mean())
w["log_ewma_c"] = w.log_ewma
INTRA = ["h_1", "h_5", "h_22"]
STRONG = HAR + ["log_ewma_c", "log_garch_t", "log_rv63"]
STRONG_I = INTRA + ["log_ewma_c", "log_garch_t", "log_rv63"]
s = w[w.primary].copy()
sessions = p.session_date.to_numpy()
event_days = [ev.first_session(date, sessions) for _, date in ev.EVENTS]
inside = np.zeros(len(s), bool)
for day in event_days:
    inside |= ((s.session_date < day) & (s.window_end >= day)).to_numpy()


def fit(f, names, blocks=(21, 63, 252), reps=1000):
    f = f.dropna(subset=names)
    y = f.log_rv30.to_numpy(float); X = np.column_stack([np.ones(len(f))] + [f[n].to_numpy(float) for n in names])
    r = inf.ols(y, X); out = dict(n=len(f), b=round(r["beta"][-1], 3))
    for bl in blocks:
        if bl * 3 > f.position.iloc[-1] - f.position.iloc[0] + 1:
            continue
        dr = inf.block_bootstrap(lambda i: np.linalg.lstsq(X[i], y[i], rcond=None)[0][-1:], f.position.to_numpy(), bl, reps, 20261104 + bl)
        out.update({f"t{bl}": round(r["beta"][-1] / dr.std(ddof=1), 2), f"lo{bl}": round(np.percentile(dr, 2.5), 3), f"hi{bl}": round(np.percentile(dr, 97.5), 3)})
    return out


for lab, names in (("study HAR", HAR), ("intraday HAR", INTRA), ("strong", STRONG), ("strong intraday", STRONG_I)):
    print("(c)", lab, "all", fit(s, names + [IV]))
    print("(c)", lab, "no events", fit(s[~inside], names + [IV]))
    print("(c)", lab, "events only", fit(s[inside], names + [IV], blocks=(21,)))
    r = s[s.session_date < "2025-03-01"]
    print("(c)", lab, "before 2025-03, no events", fit(r[~inside[s.session_date < "2025-03-01"]], names + [IV]))
    print("(c)", lab, "from 2025-03", fit(s[s.session_date >= "2025-03-01"], names + [IV], blocks=(21, 63)))
# Yearly mean b with events out.
for lab, names in (("study HAR", HAR), ("intraday HAR", INTRA)):
    for evlab, f in (("all", s), ("no events", s[~inside])):
        bs = [b_of(c, names + [IV])[0] for _, c in f.groupby("year")]
        print("(c) yearly", lab, evlab, np.round(bs, 2).tolist(), "mean", round(np.mean(bs), 3), "positive", sum(x > 0 for x in bs))

# Leave one event out, intraday HAR.
for (name, _), day in zip(ev.EVENTS, event_days):
    m = ((s.session_date < day) & (s.window_end >= day)).to_numpy()
    print("(c) intraday HAR, drop", name, int(m.sum()), round(b_of(s[~m], INTRA + [IV])[0], 3))
# Keep PASO 2019 in, drop other eight; drop only PASO 2019.
m19 = ((s.session_date < event_days[0]) & (s.window_end >= event_days[0])).to_numpy()
print("(c) intraday, only PASO out", fit(s[~m19], INTRA + [IV], blocks=(21, 63)))
print("(c) intraday, eight others out", fit(s[~(inside & ~m19)], INTRA + [IV], blocks=(21, 63)))

# Placebo for the event drop: nine random clusters of origins with the same row count pattern. Is .278 special?
rng = np.random.default_rng(5)
X_cols = {lab: np.column_stack([np.ones(len(s))] + [s[n].to_numpy(float) for n in names + [IV]]) for lab, names in (("study", HAR), ("intraday", INTRA))}
y = s.log_rv30.to_numpy(float); pos = s.position.to_numpy()
sizes = [int(((s.session_date < day) & (s.window_end >= day)).sum()) for day in event_days]
res = {k: [] for k in X_cols}
forbidden = inside
for rep in range(2000):
    drop = np.zeros(len(s), bool)
    for size in sizes:
        start = rng.integers(0, len(s) - size)
        drop[start:start + size] = True
    for k, X in X_cols.items():
        res[k].append(np.linalg.lstsq(X[~drop], y[~drop], rcond=None)[0][-1])
for k, v in res.items():
    v = np.array(v)
    obs = np.linalg.lstsq(X_cols[k][~inside], y[~inside], rcond=None)[0][-1]
    print(f"(c) placebo drop {k}: observed {obs:.3f}, placebo mean {v.mean():.3f}, 2.5% {np.percentile(v, 2.5):.3f}, 97.5% {np.percentile(v, 97.5):.3f}, share below observed {np.mean(v < obs):.3f}")
# Same placebo, with the PASO windows always kept out, so the question is the other eight events.
keep = ~m19
for k, X in X_cols.items():
    obs = np.linalg.lstsq(X[keep & ~inside], y[keep & ~inside], rcond=None)[0][-1]
    vals = []
    for rep in range(2000):
        drop = ~keep
        for size in sizes[1:]:
            start = rng.integers(0, len(s) - size)
            drop = drop.copy(); drop[start:start + size] = True
        vals.append(np.linalg.lstsq(X[~drop], y[~drop], rcond=None)[0][-1])
    v = np.array(vals)
    print(f"(c) placebo drop, PASO out in all, {k}: b with PASO out only {np.linalg.lstsq(X[keep], y[keep], rcond=None)[0][-1]:.3f}, observed all out {obs:.3f}, placebo mean {v.mean():.3f}, 2.5% {np.percentile(v, 2.5):.3f}, 97.5% {np.percentile(v, 97.5):.3f}, share below observed {np.mean(v < obs):.3f}")
print("done7")
