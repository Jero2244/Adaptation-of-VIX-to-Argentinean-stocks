"""Audit step 4: independent rebuild of returns, RV30, HAR inputs, the primary regression, the Stage 5 number, and the calibration measures.

Reads data/*.parquet and reports/*.csv. Writes nothing in the project. statsmodels does the regressions here; the study uses its own numpy code.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss

ROOT = Path(__file__).resolve().parent.parent
D, R = ROOT / "data", ROOT / "reports"
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300)

panel = pd.read_parquet(D / "forecast_panel.parquet")
daily = pd.read_parquet(D / "equity_official_daily.parquet").sort_values("session_date").reset_index(drop=True)
cash = pd.read_csv(D / "adr_cash_events.csv", parse_dates=["ex_date"])
cash = cash[cash.ex_date >= "2018-05-01"]

print("=== 1. Returns and RV30 rebuilt from the official closes")
c = daily.set_index("session_date")["official_close_price"]
div = cash.groupby("ex_date")["usd_per_ads"].sum().reindex(c.index).fillna(0.0)
print("ex-dates that are not sessions:", [str(d.date()) for d in cash.ex_date if d not in c.index])
ret = np.log((c + div) / c.shift(1))
dates = c.index.to_numpy()
rv = np.full(len(c), np.nan)
nsess = np.zeros(len(c), dtype=int)
for i, d in enumerate(dates):
    end = d + np.timedelta64(30, "D")
    if end > dates[-1]:
        continue
    mask = (dates > d) & (dates <= end)
    rv[i] = 365 / 30 * float((ret.to_numpy()[mask] ** 2).sum())
    nsess[i] = mask.sum()
p = panel.set_index("session_date")
print("max |return_total diff|:", float(np.nanmax(np.abs(ret.to_numpy() - p["return_total"].to_numpy()))))
print("max |rv30 diff|:", float(np.nanmax(np.abs(rv - p["rv30"].to_numpy()))), " rows with rv30:", int(np.isfinite(rv).sum()), "panel:", int(p.rv30.notna().sum()), " presence mismatch:", int((np.isfinite(rv) != p.rv30.notna().to_numpy()).sum()))
print("sessions in a 30-calendar-day window: ", pd.Series(nsess[np.isfinite(rv)]).value_counts().sort_index().to_dict())
last = pd.Series(dates).map(lambda d: 0)
# actual calendar length to the last session in the window
span = [(dates[(dates > d) & (dates <= d + np.timedelta64(30, 'D'))][-1] - d) / np.timedelta64(1, 'D') for d, ok in zip(dates, np.isfinite(rv)) if ok]
print("calendar days from origin to the last session in the window: mean %.2f, min %d, share <30: %.3f" % (np.mean(span), np.min(span), np.mean(np.array(span) < 30)))
lr22 = np.log(252 * (ret ** 2).rolling(22).mean().clip(lower=1e-6))
lr5 = np.log(252 * (ret ** 2).rolling(5).mean().clip(lower=1e-6))
lr1 = np.log(252 * (ret ** 2).clip(lower=1e-6))
for name, mine in (("log_rv1", lr1), ("log_rv5", lr5), ("log_rv22", lr22)):
    print(f"max |{name} diff|:", float(np.nanmax(np.abs(mine.to_numpy() - p[name].to_numpy()))))
big = ret.abs().sort_values(ascending=False).head(8)
print("largest |daily total log returns|:\n", pd.DataFrame({"ret": ret[big.index], "close": c[big.index], "prev": c.shift(1)[big.index]}).round(4).to_string())
print("zero returns:", int((ret == 0).sum()), " |ret|<0.1% (floor binds on log_rv1):", int((ret.abs() < 1e-3).sum()), "of", len(ret))
al = pd.read_parquet(D / "alpaca_open_closes.parquet")
j = al.merge(daily, on="session_date")
gap = np.log(j["close"] / j["official_close_price"]).abs()
print("Alpaca vs official close: n", len(j), " differ:", int((gap > 1e-9).sum()), " max bp:", round(float(gap.max() * 1e4), 2))
print("dividend yield per event (cash / prior close), top 5:\n", (div[div > 0] / c.shift(1)[div > 0]).sort_values(ascending=False).head(5).round(4).to_string())

print("\n=== 2. Primary regression (statsmodels)")
s = panel[panel.primary].copy()
y = s["log_rv30"]
Xh = sm.add_constant(s[["log_rv1", "log_rv5", "log_rv22"]])
Xf = sm.add_constant(s[["log_rv1", "log_rv5", "log_rv22", "log_iv2"]])
mh, mf = sm.OLS(y, Xh).fit(), sm.OLS(y, Xf).fit()
print("n", len(s), " R2 HAR %.3f, HAR+IV %.3f" % (mh.rsquared, mf.rsquared))
print("coefficients HAR+IV:", mf.params.round(3).to_dict())
for lags in (21, 42, 63):
    h = mf.get_robustcov_results(cov_type="HAC", maxlags=lags, use_correction=False)
    print(f"  HAC({lags}) se of b {h.bse[-1]:.3f}, t {h.tvalues[-1]:.2f}")
print("  OLS (iid) t of b: %.2f  <- what one gets if the overlap is ignored" % mf.tvalues.iloc[-1])
# my own circular block bootstrap on the session grid (independent code)
rng = np.random.default_rng(7)
pos = s["position"].to_numpy()
Xa, ya = Xf.to_numpy(), y.to_numpy()
grid_n = pos[-1] - pos[0] + 1
where = {int(q): i for i, q in enumerate(pos - pos[0])}
for block in (21, 63):
    draws = []
    for _ in range(1000):
        starts = rng.integers(0, grid_n, size=int(np.ceil(grid_n / block)))
        idx = [where[(st + k) % grid_n] for st in starts for k in range(block) if (st + k) % grid_n in where]
        draws.append(np.linalg.lstsq(Xa[idx], ya[idx], rcond=None)[0][-1])
    print(f"  my block bootstrap, block {block}: se {np.std(draws):.3f}, 95% percentile interval {np.percentile(draws, 2.5):.3f} to {np.percentile(draws, 97.5):.3f}")
print("stored study values: b .622, 21-block interval .337 to .916, 63-block .309 to .946")

print("\n=== 3. Mincer-Zarnowitz, logs and levels, with a joint test of a=0, b=1 (HAC 21)")
for label, yy, xx in (("logs", s["log_rv30"], s["log_iv2"]), ("levels (variance)", s["rv30"], s["atm30"] ** 2), ("levels (vol)", np.sqrt(s["rv30"]), s["atm30"])):
    m = sm.OLS(yy, sm.add_constant(xx)).fit(cov_type="HAC", cov_kwds=dict(maxlags=21))
    w = m.wald_test((np.eye(2), np.array([0.0, 1.0])), scalar=True)
    print(f"  {label}: a {m.params.iloc[0]:.3f} (se {m.bse.iloc[0]:.3f}), b {m.params.iloc[1]:.3f} (se {m.bse.iloc[1]:.3f}), R2 {m.rsquared:.3f}, Wald p(a=0,b=1) {float(w.pvalue):.4f}")
nop = s[~((s.session_date < "2019-08-12") & (s.window_end >= "2019-08-12"))]
m = sm.OLS(nop["rv30"], sm.add_constant(nop["atm30"] ** 2)).fit()
print("  level b without 2019-08-12 windows: %.3f (n %d)" % (m.params.iloc[1], len(nop)))

print("\n=== 4. Variance risk premium as the study defines it (ATM30^2 - RV30)")
v = s["atm30"] ** 2 - s["rv30"]
print("  mean %.3f, median %.3f, share IV2>RV %.3f" % (v.mean(), v.median(), (v > 0).mean()))
vv = s["atm30"] - np.sqrt(s["rv30"])
print("  in vol points: mean %.3f, median %.3f" % (vv.mean(), vv.median()))
mfp = panel.dropna(subset=["mf30", "atm30"])
print("  MF30^2 / ATM30^2 median where both exist (2024+ mostly): %.3f on %d days -> ATM30^2 understates model-free variance by about %.0f%%" % ((mfp.mf30 ** 2 / mfp.atm30 ** 2).median(), len(mfp), 100 * (1 - 1 / (mfp.mf30 ** 2 / mfp.atm30 ** 2).median())))

print("\n=== 5. Persistence and unit roots (valid rows treated as consecutive)")
for name in ("log_iv2", "log_rv30"):
    x = s[name].to_numpy()
    a = adfuller(x, autolag="AIC")
    print(f"  {name}: AR(1) {np.corrcoef(x[1:], x[:-1])[0, 1]:.3f}, ADF stat {a[0]:.2f}, p {a[1]:.4f}")
x = panel["log_iv2"].dropna().to_numpy()
print("  residual AR(1) of the primary regression: %.3f ; at lag 21: %.3f ; at lag 30: %.3f" % tuple(np.corrcoef(mf.resid.to_numpy()[k:], mf.resid.to_numpy()[:-k])[0, 1] for k in (1, 21, 30)))

print("\n=== 6. Stage 5 number from the saved test panel (no rerun of the test)")
t = pd.read_parquet(D / "test" / "test_panel.parquet")
tp = t[t.primary]
mt = sm.OLS(tp["log_rv30"], sm.add_constant(tp[["log_rv1", "log_rv5", "log_rv22", "log_iv2"]])).fit()
h = mt.get_robustcov_results(cov_type="HAC", maxlags=21)
print("  n %d, b %.4f (stored .2810), HAC(21) se %.3f, R2 %.3f; R2 HAR alone %.3f" % (len(tp), mt.params.iloc[-1], h.bse[-1], mt.rsquared, sm.OLS(tp["log_rv30"], sm.add_constant(tp[["log_rv1", "log_rv5", "log_rv22"]])).fit().rsquared))
print("  test ATM30 range %.3f to %.3f, median %.3f; sd of log_iv2: test %.3f vs open %.3f" % (t.atm30.min(), t.atm30.max(), t.atm30.median(), tp.log_iv2.std(), s.log_iv2.std()))
print("  test sessions %d, first %s, last %s" % (len(t), t.session_date.min().date(), t.session_date.max().date()))

print("\n=== 7. Calibration (implied move) rebuilt")
cal = pd.read_parquet(D / "calibration_panel.parquet")
T = 30 / 365
tot = np.concatenate([[0.0], np.nancumsum(ret.to_numpy())])
Rm = np.full(len(c), np.nan)
for i, d in enumerate(dates):
    end = d + np.timedelta64(30, "D")
    if end > dates[-1]:
        continue
    k = np.searchsorted(dates, end, side="right")
    Rm[i] = tot[k] - tot[i + 1]
ser = pd.read_parquet(D / "index_series.parquet").set_index("session_date")
atm = ser["atm30"].where(~ser["flag_half_day"]).to_numpy()
r = cal["r"].to_numpy()
sgm = atm * np.sqrt(T)
z = (Rm - (r * T - sgm ** 2 / 2)) / sgm
ok = np.isfinite(z)
print("  rows %d (stored valid %d); max |z diff| %.2e" % (ok.sum(), int(cal.valid.sum()), float(np.nanmax(np.abs(z - cal.z.to_numpy())))))
zz = z[ok]
inner, outer = np.mean(np.abs(zz) < 1), np.mean(np.abs(zz) < 2)
print("  inner %.4f (nominal %.4f), outer %.4f (nominal %.4f), mean z %.3f, sd z %.3f, mean z2 %.3f, down %.4f, up %.4f" % (inner, stats.norm.cdf(1) - stats.norm.cdf(-1), outer, stats.norm.cdf(2) - stats.norm.cdf(-2), zz.mean(), zz.std(ddof=1), (zz ** 2).mean(), np.mean(zz < -2), np.mean(zz > 2)))
neff = ok.sum() / 21
for name, ph in (("inner", inner), ("outer", outer)):
    se = np.sqrt(ph * (1 - ph) / neff)
    print(f"  rough check, {name}: binomial se with n_eff = rows/21 = {neff:.0f}: {se:.3f} -> 95% about {ph - 1.96 * se:.3f} to {ph + 1.96 * se:.3f}")
simple_band = np.abs(np.exp(Rm[ok]) - 1) < sgm[ok]
print("  alternative textbook rule |S_T/S_0 - 1| < sigma*sqrt(T): hit rate %.4f" % simple_band.mean())

print("\n=== 8. Numbers quoted in the write-up against the CSV reports")
print(pd.read_csv(R / "stage3_mf30.csv").round(3).to_string())
ev = pd.read_csv(R / "stage3_events.csv")
print(ev[["event", "first_return", "near_vol", "forward_vol", "ratio", "realized_vol_between", "share_placebos_below", "near_days", "gap_days"]].round(3).to_string())
print(pd.read_csv(R / "stage3_vrp.csv").round(3).to_string())
print(pd.read_csv(R / "stage3_split.csv").round(3).to_string())
print(pd.read_csv(R / "stage3_level.csv").round(3).to_string())
