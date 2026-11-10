"""Replace the HAR inputs with RV built from intraday mids plus the squared overnight return. Same target, same rows."""
import sys, os
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
import inference as inf, forecasts as fc

HERE = os.path.dirname(sys.argv[0])
p = pd.read_parquet(PROJECT + r"\data\forecast_panel.parquet")
d = pd.read_parquet(os.path.join(HERE, "a3_intraday.parquet"))
print("sessions in intraday", len(d), "median bars", d.n.median(), "bars by year", d.groupby(d.session_date.dt.year).n.median().to_dict())
p = p.merge(d, on="session_date", how="left", validate="one_to_one")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"
pd.set_option("display.width", 250, "display.max_columns", 50)
print("missing intraday rows", p.rv_5m.isna().sum())
print("corr close-close var vs 5m+on var, logs:", np.corrcoef(np.log(p.return_total[1:]**2 + 1e-6), np.log(p.rv_5m[1:].fillna(p.rv_5m.median()) + p.return_overnight[1:]**2 + 1e-6))[0, 1])
print("mean daily var: cc", (p.return_total**2).mean(), "5m+on", (p.rv_5m + p.return_overnight**2).mean(), "30m+on", (p.rv_30m + p.return_overnight**2).mean())
for m in (5, 15, 30):
    daily = (p[f"rv_{m}m"] + p.return_overnight ** 2)
    daily = daily.where(daily.notna(), p.return_total ** 2)  # fall back to the close-to-close square on a missing quote day
    for L in (1, 5, 22):
        p[f"h{m}_{L}"] = np.log(252 * daily.rolling(L, min_periods=L).mean().clip(lower=1e-6))
    # forward target
    dates = p.session_date.to_numpy()
    last = np.searchsorted(dates, p.window_end.to_numpy(), side="right")
    run = np.concatenate([[0.0], np.cumsum(np.nan_to_num(daily.to_numpy()))])
    tot = run[last] - run[np.arange(len(p)) + 1]
    p[f"y{m}"] = np.where(p.rv30.notna(), np.log(365 / 30 * np.where(tot > 0, tot, np.nan)), np.nan)


def fit(frame, y_name, names, reps=1000, key=IV):
    frame = frame.dropna(subset=names + [y_name])
    y = frame[y_name].to_numpy(float)
    X = np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(float) for n in names])
    res = inf.ols(y, X)
    i = 1 + names.index(key)
    pos = frame.position.to_numpy()
    out = dict(n=len(frame), b=res["beta"][i], r2=res["r2"], others=np.round(res["beta"][1:i], 3).tolist())
    for bl in (21, 63):
        dr = inf.block_bootstrap(lambda idx: np.linalg.lstsq(X[idx], y[idx], rcond=None)[0][i:i + 1], pos, bl, reps, 20261104 + bl)
        out.update({f"t{bl}": res["beta"][i] / dr.std(ddof=1), f"lo{bl}": np.percentile(dr, 2.5), f"hi{bl}": np.percentile(dr, 97.5)})
    return out


s = p[p.primary]
rows = []
for ylab, yname in (("close-close target", "log_rv30"), ("5m+overnight target", "y5")):
    rows.append(dict(y=ylab, har="close-close (study)", period="all", **fit(s, yname, HAR + [IV])))
    rows.append(dict(y=ylab, har="close-close, no IV", period="all", **fit(s, yname, HAR, key="log_rv22")))
    for m in (5, 15, 30):
        names = [f"h{m}_{L}" for L in (1, 5, 22)]
        rows.append(dict(y=ylab, har=f"{m}m+overnight", period="all", **fit(s, yname, names + [IV])))
        rows.append(dict(y=ylab, har=f"{m}m+overnight, no IV", period="all", **fit(s, yname, names, key=names[-1])))
    names = [f"h5_{L}" for L in (1, 5, 22)]
    for lab, mask in (("2018-2023", s.year <= 2023), ("2024-2025", s.year.isin([2024, 2025])), ("2026", s.year == 2026)):
        rows.append(dict(y=ylab, har="5m+overnight", period=lab, **fit(s[mask], yname, names + [IV])))
        rows.append(dict(y=ylab, har="close-close (study)", period=lab, **fit(s[mask], yname, HAR + [IV])))
print(pd.DataFrame(rows).round(3).to_string())

# Race on the calibrated dates with the intraday HAR. No smearing, and with smearing. Training on common days.
primary = p.primary.to_numpy()
common = primary & p.log_garch.notna().to_numpy() & p.log_garch_t.notna().to_numpy() & p.log_ewma.notna().to_numpy()
mask = common & (p.session_date >= "2019-12-11").to_numpy()
y = p.rv30.to_numpy()[mask]; pos = p.position.to_numpy()[mask]


def boot(dv, block=21, reps=2000):
    dr = inf.block_bootstrap(lambda i: np.array([dv[i].mean()]), pos, block, reps, 7)
    return round(dv.mean(), 4), round(dv.mean() / dr.std(ddof=1), 2), round(np.percentile(dr, 2.5), 4), round(np.percentile(dr, 97.5), 4)


for m in (5, 30):
    names = [f"h{m}_{L}" for L in (1, 5, 22)]
    for tname, train in (("common", common), ("primary", primary)):
        for smear in (True, False):
            h = fc.expanding_forecasts(p, names, train, mask, smearing=smear)[mask]
            hi = fc.expanding_forecasts(p, names + [IV], train, mask, smearing=smear)[mask]
            h0 = fc.expanding_forecasts(p, HAR, train, mask, smearing=smear)[mask]
            dq = fc.qlike(y, hi) - fc.qlike(y, h)
            dl = (np.log(y) - np.log(hi)) ** 2 - (np.log(y) - np.log(h)) ** 2
            cw = dl + (np.log(hi) - np.log(h)) ** 2
            print(f"m={m} train={tname} smear={smear} q_har_intraday={fc.qlike(y, h).mean():.4f} q_har_cc={fc.qlike(y, h0).mean():.4f} q_har_iv={fc.qlike(y, hi).mean():.4f} dq {boot(dq)} dq63 {boot(dq, 63)} dlog {boot(dl)} cw {boot(cw)}")
