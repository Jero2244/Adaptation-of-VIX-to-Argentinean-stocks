"""c3: sensitivity of b to close noise and to chain quality, on pre-2025-03 panel rows. Reads data/forecast_panel.parquet only.
Alpaca closes are not read. The noise sizes are assumptions, so this shows only how much mismatch would matter."""
import sys
import numpy as np, pandas as pd
ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, ROOT)
import realized as rz
pd.set_option("display.width", 200, "display.max_columns", 30)
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet")
HAR = ["log_rv1", "log_rv5", "log_rv22"]; IV = "log_iv2"


def fit(f, names=HAR + [IV]):
    X = np.column_stack([np.ones(len(f))] + [f[n].to_numpy(float) for n in names])
    return np.linalg.lstsq(X, f.log_rv30.to_numpy(float), rcond=None)[0][-1]


def rebuild(close):
    f = p[["session_date", "open", "close", "dividend_cash", "rights_cash"]].copy()
    f["close"] = close
    f = rz.trailing_realized(rz.forward_realized(rz.total_returns(f)))
    return f


base = p[p.primary & (p.session_date < "2025-03-01")]
print("rows", len(base), "b", round(fit(base), 3))
print("identity check against panel: max rv30 gap", float(np.nanmax(np.abs(rebuild(p.close.to_numpy()).rv30 - p.rv30))))
r = p.return_total.dropna()
print("median daily |return|", round(float(r.abs().median()), 4), "daily sd", round(float(r.std()), 4), "2018-05 to 2018-12 sd", round(float(p.return_total[p.session_date < "2019-01-01"].std()), 4))
rng = np.random.default_rng(11)
for sd_bp in (5, 10, 25, 50, 100):
    out = []
    for _ in range(20):
        noisy = p.close.to_numpy() * np.exp(rng.normal(0, sd_bp / 1e4, len(p)))
        f = rebuild(noisy)
        m = p[[IV, "primary", "session_date"]].join(f[["log_rv1", "log_rv5", "log_rv22", "rv30"]])
        m["log_rv30"] = np.log(m.rv30)
        m = m[m.primary & (m.session_date < "2025-03-01")]
        out.append((fit(m), np.corrcoef(m.log_rv1, base.log_rv1)[0, 1], np.mean(np.abs(np.log(m.rv30 / base.rv30)))))
    o = np.array(out).mean(axis=0)
    print(f"close noise {sd_bp} bp: b {o[0]:.3f}, corr log_rv1 {o[1]:.3f}, mean |log rv30 change| {o[2]:.3f}")
# One bad close per 100 sessions, size 2%.
out = []
for _ in range(20):
    bump = np.where(rng.random(len(p)) < 0.01, rng.choice([-0.02, 0.02], len(p)), 0.0)
    f = rebuild(p.close.to_numpy() * np.exp(bump))
    m = p[[IV, "primary", "session_date"]].join(f[["log_rv1", "log_rv5", "log_rv22", "rv30"]])
    m["log_rv30"] = np.log(m.rv30)
    m = m[m.primary & (m.session_date < "2025-03-01")]
    out.append(fit(m))
print("1% of closes off by 2%: b", round(float(np.mean(out)), 3))

print("\nChain quality, pre-2025-03, HAR+IV")
print("tier 1 b", round(fit(base[base.tier == 1]), 3), "n", int((base.tier == 1).sum()), "| tier 2 b", round(fit(base[base.tier == 2]), 3), "n", int((base.tier == 2).sum()))
calm = base[~((base.session_date < "2019-08-12") & (base.window_end >= "2019-08-12"))]
print("no 2019 PASO: tier 1 b", round(fit(calm[calm.tier == 1]), 3), "| tier 2 b", round(fit(calm[calm.tier == 2]), 3))
base2 = base.assign(flag=(base.tier == 2).astype(float))
base2["iv_t2"] = base2[IV] * base2.flag
X = np.column_stack([np.ones(len(base2)), base2[HAR].to_numpy(float), base2[IV], base2.flag, base2.iv_t2])
print("interaction: b tier 1, shift for tier 2", np.round(np.linalg.lstsq(X, base2.log_rv30.to_numpy(float), rcond=None)[0][[4, 6]], 3))
b1, b2 = fit(base[base.tier == 1]), fit(base[base.tier == 2])
for share in (0.1, 0.25, 0.5, 0.75):
    print(f"tier 2 share {share}: simple mixed b {b1 * (1 - share) + b2 * share:.3f}")
print("relative_spread median by year, primary rows")
print(p[p.primary].groupby("year").relative_spread.median().round(3).to_string())
print("near_pairs median by year, primary rows")
print(p[p.primary].groupby("year").near_pairs.median().to_string())

print("\nCount of grid rows in a 585-session window")
sessions = 585
for cov in (0.92, 0.85, 0.81, 0.75, 0.72):
    grid = sessions - 21 - 22
    print(f"coverage {cov}: origins {grid * cov:.0f}, fixed step 22 rows {grid / 22 * cov:.1f}, fixed step 23 rows {grid / 23 * cov:.1f}, 21-session spans of the whole grid {grid / 21:.1f}, scored rows {312 * cov:.0f}")
