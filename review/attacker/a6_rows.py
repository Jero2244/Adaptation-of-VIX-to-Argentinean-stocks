"""One-row leverage in the non-overlapping samples. Intraday HAR with events dropped. Outlier share of the QLIKE gain."""
import sys, os
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import inference as inf, events as ev

p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
samples = inf.non_overlapping_samples(p.session_date.to_numpy(), p.primary.to_numpy())


def b_of(c):
    X = np.column_stack([np.ones(len(c))] + [c[n].to_numpy(float) for n in HAR + [IV]])
    return inf.ols(c.log_rv30.to_numpy(float), X)["beta"][-1]


rows = []
for off, smp in enumerate(samples):
    c = p.iloc[smp]
    pasomask = (c.session_date < "2019-08-12") & (c.window_end >= "2019-08-12")
    rows.append(dict(offset=off, b=b_of(c), b_no_paso_row=b_of(c[~pasomask]), origin=c[pasomask].session_date.dt.date.iloc[0]))
t = pd.DataFrame(rows)
print(t.round(3).to_string())
print("b no PASO row: min", t.b_no_paso_row.min(), "max", t.b_no_paso_row.max(), "median", t.b_no_paso_row.median())
s = p[p.primary]
inpaso = (s.session_date < "2019-08-12") & (s.window_end >= "2019-08-12")
print("PASO-window rows", s[inpaso].session_date.dt.date.min(), s[inpaso].session_date.dt.date.max(), inpaso.sum(), "mean IV by row", s[inpaso].atm30.round(2).tolist())
print("pooled b", b_of(s), "drop PASO rows", b_of(s[~inpaso]))

d = pd.read_parquet(os.path.join(os.path.dirname(sys.argv[0]), "a3_intraday.parquet"))
w = p.merge(d, on="session_date", how="left", validate="one_to_one")
daily = w.rv_5m + w.return_overnight ** 2
for L in (1, 5, 22):
    w[f"h_{L}"] = np.log(252 * daily.rolling(L, min_periods=L).mean().clip(lower=1e-6))
names = ["h_1", "h_5", "h_22", IV]
s = w[w.primary]
inside = np.zeros(len(s), bool)
sessions = p.session_date.to_numpy()
for _, date in ev.EVENTS:
    day = ev.first_session(date, sessions)
    inside |= ((s.session_date < day) & (s.window_end >= day)).to_numpy()


def fit(f, names, reps=1000):
    f = f.dropna(subset=names)
    y = f.log_rv30.to_numpy(float); X = np.column_stack([np.ones(len(f))] + [f[n].to_numpy(float) for n in names])
    r = inf.ols(y, X); out = dict(n=len(f), b=round(r["beta"][-1], 3))
    for bl in (21, 63):
        dr = inf.block_bootstrap(lambda i: np.linalg.lstsq(X[i], y[i], rcond=None)[0][-1:], f.position.to_numpy(), bl, reps, 20261104 + bl)
        out.update({f"t{bl}": round(r["beta"][-1] / dr.std(ddof=1), 2), f"lo{bl}": round(np.percentile(dr, 2.5), 3), f"hi{bl}": round(np.percentile(dr, 97.5), 3)})
    return out


print("intraday HAR all", fit(s, names))
print("intraday HAR drop events", fit(s[~inside], names))
print("intraday HAR drop events 2018-2023", fit(s[(~inside) & (s.year <= 2023)], names))
print("intraday HAR before 2025-03", fit(s[s.session_date < "2025-03-01"], names))
print("study HAR before 2025-03", fit(s[s.session_date < "2025-03-01"], HAR + [IV]))
print("study HAR before 2025-03 drop events", fit(s[(s.session_date < "2025-03-01") & (~inside)], HAR + [IV]))
print("done6")
