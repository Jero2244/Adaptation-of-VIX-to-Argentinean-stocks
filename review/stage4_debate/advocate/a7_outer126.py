"""Short check of Rule 1 options with longer residual dependence (126-session outer blocks), and at coverage near the 300-origin floor.
Open pre-2025-03 panel rows only. Exploratory."""
import sys as _s
from rules import *
REPS, DRAWS = 80, 399
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=CALC)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
pool = p[p[[IV, "log_rv30"] + HAR].notna().all(axis=1)]
beta = np.linalg.lstsq(design(pool, FULL), pool.log_rv30.to_numpy(float), rcond=None)[0]
resid = pool.log_rv30.to_numpy(float) - design(pool, FULL) @ beta
rng = np.random.default_rng(int(_s.argv[1].replace("-", "")))
rows = []
for start in (_s.argv[1],):
    s = pd.Period(start, "M")
    w0 = p[(p.session_date >= s.to_timestamp()) & (p.session_date <= (s + 27).to_timestamp(how="end").normalize())].reset_index(drop=True)
    w0.loc[w0.index < 22, HAR] = np.nan
    n = len(w0)
    for cover, outer in ((None, 126), (None, 63), (.53, 126)):
        for true_b in (0.0, .37, .62):
            for _ in range(REPS):
                iv = w0[IV].to_numpy(float).copy()
                if cover:
                    keep = np.ones(n, bool)
                    while (keep & np.isfinite(iv)).sum() > cover * n:
                        q = rng.integers(0, n)
                        keep[q:q + 21] = False
                    iv[~keep] = np.nan
                e = np.empty(0)
                while len(e) < n:
                    q = rng.integers(0, len(resid))
                    e = np.concatenate([e, np.take(resid, np.arange(q, q + outer), mode="wrap")])
                m = np.isfinite(iv) & w0[HAR].notna().all(axis=1).to_numpy() & w0.log_rv30.notna().to_numpy()
                X = np.column_stack([np.ones(m.sum()), w0.loc[m, HAR].to_numpy(float), iv[m]])
                y = beta[0] + X[:, 1:4] @ beta[1:4] + true_b * iv[m] + (beta[4] - true_b) * pool[IV].mean() + e[:n][m]
                pos = np.flatnonzero(m)
                bh = np.linalg.lstsq(X, y, rcond=None)[0][4]
                f = lambda idx: np.array([np.linalg.lstsq(X[idx], y[idx], rcond=None)[0][4]])
                seed = int(rng.integers(1, 2**31))
                d21 = inf.block_bootstrap(f, pos, 21, DRAWS, seed)[:, 0]
                d63 = inf.block_bootstrap(f, pos, 63, DRAWS, seed + 1)[:, 0]
                rows.append(dict(start=start, cover=cover or 0, outer=outer, true_b=true_b, n=len(y), b=bh, se21=d21.std(ddof=1), se63=d63.std(ddof=1), lo21=np.percentile(d21, 2.5), hi21=np.percentile(d21, 97.5), lo63=np.percentile(d63, 2.5), hi63=np.percentile(d63, 97.5)))
    pd.DataFrame(rows).to_csv(f"a7_{start}.csv", index=False)
    print(start, "done", flush=True)
