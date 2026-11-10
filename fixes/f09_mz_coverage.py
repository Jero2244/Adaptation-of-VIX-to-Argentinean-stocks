"""Fix step 5 (F13, F14): Mincer-Zarnowitz joint test and measured coverage of the nominal 95% intervals. DEVELOPMENT work on open data.

Part A, Mincer-Zarnowitz: regress the realized value on the forecast, test a = 0 and b = 1 jointly (Wald, HAC with 21 lags, statsmodels), on the primary
sample. Three scales: logs (log RV30 on log ATM30^2), variance levels (RV30 on ATM30^2), volatility levels (sqrt RV30 on ATM30). Also run on the
all-four-fixes series if it exists. Note: a != 0, b != 1 is expected in part because of the variance risk premium; the test is not a test of the study claim.

Part B, coverage: Monte Carlo with the observed regressors held FIXED. True model y = X b_hat + e. The error e is Gaussian with the empirical
autocovariance of the primary-regression residuals on the session grid (lags 0 to 90, Bartlett taper, so the matrix is positive semi-definite).
For each draw, the study's estimator is refit and two nominal 95% intervals are formed for the IV coefficient: the percentile block-bootstrap interval
(blocks 21 and 63, 399 resamples, the study's code) and b +- 1.96 Newey-West(21). Coverage = share of draws whose interval holds the true b_hat.
Limits: X is fixed; the real regressors are random and persistent, so real coverage can differ. The study's own earlier simulation (80% to 91%) is
quoted in reports/stage4_descriptive.md and was not rerun.
"""
from multiprocessing import Pool

import statsmodels.api as sm
from scipy.linalg import toeplitz

from common import *  # noqa

NSIM, NBOOT, MAXLAG = 400, 399, 90


def mz(panel: pd.DataFrame, label: str):
    s = panel[panel.primary]
    rows = []
    for scale, y, x in (("logs", s.log_rv30, s.log_iv2), ("variance levels", s.rv30, s.atm30 ** 2), ("volatility levels", np.sqrt(s.rv30), s.atm30)):
        m = sm.OLS(y, sm.add_constant(x)).fit(cov_type="HAC", cov_kwds=dict(maxlags=21))
        w = m.wald_test((np.eye(2), np.array([0.0, 1.0])), scalar=True)
        rows.append(dict(iv_series=label, scale=scale, n=len(s), a=m.params.iloc[0], a_se=m.bse.iloc[0], b=m.params.iloc[1], b_se=m.bse.iloc[1], r2=m.rsquared, wald_chi2=float(w.statistic), p_joint=float(w.pvalue)))
    return rows


def one_chunk(args):
    seed, n_sims, X, beta, L, positions, grid_n, k = args
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n_sims):
        e = (L @ rng.standard_normal(grid_n))[positions - positions[0]]
        y = X @ beta + e
        fit = inf.ols(y, X)
        se = inf.newey_west_se(X, fit["residuals"], NW_LAGS)
        row = dict(b=fit["beta"][k], nw_low=fit["beta"][k] - 1.96 * se[k], nw_high=fit["beta"][k] + 1.96 * se[k], nw_se=se[k])

        def est(idx):
            return np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]

        for block in (21, 63):
            d = inf.block_bootstrap(est, positions, block, NBOOT, int(rng.integers(1, 2 ** 31)))
            s = inf.bootstrap_summary(fit["beta"], d)
            row.update({f"boot{block}_low": s["low"][k], f"boot{block}_high": s["high"][k], f"boot{block}_se": s["se"][k]})
        out.append(row)
    return out


def coverage(panel: pd.DataFrame, label: str):
    s = panel[panel.primary]
    names = HAR + [IV]
    X = np.column_stack([np.ones(len(s))] + [s[n].to_numpy() for n in names])
    y = s.log_rv30.to_numpy()
    fit = inf.ols(y, X)
    beta, e = fit["beta"], fit["residuals"]
    positions = s.position.to_numpy()
    grid_n = int(positions[-1] - positions[0] + 1)
    full = np.full(grid_n, np.nan)
    full[positions - positions[0]] = e
    acov = np.array([np.nanmean(full[: grid_n - h] * full[h:]) for h in range(MAXLAG + 1)])
    taper = 1 - np.arange(MAXLAG + 1) / (MAXLAG + 1)
    gam = np.zeros(grid_n)
    gam[: MAXLAG + 1] = acov * taper
    cov = toeplitz(gam)
    w, v = np.linalg.eigh(cov)
    L = v * np.sqrt(np.clip(w, 0, None))
    k = len(names)
    chunks = [(1000 + i, NSIM // 8, X, beta, L, positions, grid_n, k) for i in range(8)]
    with Pool(4) as pool:
        res = [r for part in pool.map(one_chunk, chunks) for r in part]
    r = pd.DataFrame(res)
    truth = beta[k]
    rows = []
    for name, lo, hi in (("bootstrap, 21-session blocks", "boot21_low", "boot21_high"), ("bootstrap, 63-session blocks", "boot63_low", "boot63_high"), ("b +- 1.96 Newey-West(21)", "nw_low", "nw_high")):
        rows.append(dict(iv_series=label, interval=name, draws=len(r), nominal=0.95, measured_coverage=float(((r[lo] <= truth) & (truth <= r[hi])).mean()),
                         mean_width=float((r[hi] - r[lo]).mean()), sd_of_b_over_mean_width_implied_se=float(r.b.std(ddof=1) / ((r[hi] - r[lo]).mean() / 3.92))))
    print(f"[{label}] true b = {truth:.3f}; SD of b across draws {r.b.std(ddof=1):.3f}; median NW se {r.nw_se.median():.3f}; median boot21 se {r.boot21_se.median():.3f}; median boot63 se {r.boot63_se.median():.3f}")
    return rows


if __name__ == "__main__":
    print(LABEL)
    real = rz.build_realized()
    sets = [("stored ATM30", "base", "atm30")]
    if (FDATA / "series_core.parquet").exists():
        sets.append(("all four fixes", "core", "atm30_floor7"))
    mzrows, covrows = [], []
    for label, name, col in sets:
        panel = make_panel(pd.read_parquet(FDATA / f"series_{name}.parquet"), real, col)
        mzrows += mz(panel, label)
        covrows += coverage(panel, label)
    pd.set_option("display.float_format", lambda x: f"{x:.4f}")
    t1, t2 = pd.DataFrame(mzrows), pd.DataFrame(covrows)
    t1.to_csv(HERE / "f09_mincer_zarnowitz.csv", index=False)
    t2.to_csv(HERE / "f09_coverage.csv", index=False)
    print("\nMincer-Zarnowitz (HAC 21). Joint test a=0, b=1")
    print(t1.to_string(index=False))
    print("\nMeasured coverage of nominal 95% intervals (fixed-X Monte Carlo)")
    print(t2.to_string(index=False))
