"""Semi-synthetic size and power with the FROZEN rows and functions: frames that blank each window ending after the frame end, rules.intervals, rules.data_floor, rules.decide.
Open pre-2025-03 rows only. Same residual method as advocate/a2_sim.py (63-session blocks of pooled residuals). 399 draws per bootstrap, as a speed choice."""
import _common
from _common import ROOT
import numpy as np, pandas as pd
import stage4_rules as rules

REPS, DRAWS = 200, 399
HAR, IV = rules.HAR, rules.IV
p = pd.read_parquet(ROOT / "data/forecast_panel.parquet", columns=["session_date", "window_end", "rv30", "log_rv30", "log_iv2"] + HAR)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
pool = p[p[[IV, "log_rv30"] + HAR].notna().all(axis=1)]


def design(frame):
    return np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(float) for n in rules.FULL])


beta = np.linalg.lstsq(design(pool), pool.log_rv30.to_numpy(float), rcond=None)[0]
resid = pool.log_rv30.to_numpy(float) - design(pool) @ beta
rng = np.random.default_rng(20261105)
out = []
for start in ("2018-05", "2020-09", "2022-11"):
    s = pd.Period(start, "M")
    w0 = p[(p.session_date >= s.to_timestamp()) & (p.session_date <= (s + 27).to_timestamp(how="end").normalize())].reset_index(drop=True).copy()
    w0["position"] = np.arange(len(w0))
    w0.loc[w0.position < 22, HAR] = np.nan
    complete = (w0.window_end <= w0.session_date.iloc[-1]).to_numpy()
    usable = w0[HAR + [IV]].notna().all(axis=1).to_numpy() & w0.log_rv30.notna().to_numpy()
    strict = usable & complete
    floor = rules.data_floor(strict)
    print(start, "sessions", len(w0), "rows frozen", int(strict.sum()), "rows a2_sim", int(usable.sum()), "floor", floor, flush=True)
    for true_b in (0.0, .37, .62):
        for _ in range(REPS):
            n = len(w0)
            e = np.empty(0)
            while len(e) < n:
                q = rng.integers(0, len(resid))
                e = np.concatenate([e, np.take(resid, np.arange(q, q + 63), mode="wrap")])
            y = beta[0] + w0[HAR].to_numpy(float) @ beta[1:4] + true_b * w0[IV].to_numpy(float) + (beta[4] - true_b) * pool[IV].mean() + e[:n]
            r = rules.intervals(w0[strict].assign(log_rv30=y[strict]), DRAWS)
            d = rules.decide(floor, r, {})
            out.append(dict(start=start, true_b=true_b, outcome=d["outcome"]))
    print(pd.DataFrame(out).query("start==@start").groupby("true_b").outcome.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string(), flush=True)
o = pd.DataFrame(out)
print("pooled")
print(o.groupby("true_b").outcome.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())
