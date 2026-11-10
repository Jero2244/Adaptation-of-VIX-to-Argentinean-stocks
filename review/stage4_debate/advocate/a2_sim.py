"""Semi-synthetic size and power of the draft rules. Exploratory, open pre-2025-03 panel rows only.

The real inputs of a 28-month window stay. The target is rebuilt: y = a + HAR weights + b * log IV + e, with a true b.
e is 63-session circular blocks of the pooled pre-break HAR+IV residuals, so it keeps overlap dependence, 2019-08 tails, and fat tails.
HAR trains on the primary rows only here, because y has no value on other rows. Usage: a2_sim.py START REPS.
"""
import sys as _s
from rules import *

start, reps = _s.argv[1], int(_s.argv[2])
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=CALC)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
a = p[[IV, "log_rv30"] + HAR].notna().all(axis=1)
pool = p[a]
beta = np.linalg.lstsq(design(pool, FULL), pool.log_rv30.to_numpy(float), rcond=None)[0]
resid = pool.log_rv30.to_numpy(float) - design(pool, FULL) @ beta
print("pooled pre-break beta", beta.round(3), "resid sd", resid.std().round(3), flush=True)
s = pd.Period(start, "M")
w0 = p[(p.session_date >= s.to_timestamp()) & (p.session_date <= (s + 27).to_timestamp(how="end").normalize())].reset_index(drop=True).copy()
rng = np.random.default_rng(abs(hash(start)) % 2**31 if False else int(start.replace("-", "")))
rows = []


def one(true_b, thin):
    w = w0.copy()
    if thin:
        # Blank IV in random 21-session blocks until coverage of valid IV falls to about 70%.
        keep = np.ones(len(w), bool)
        while (keep & w[IV].notna().to_numpy()).sum() > .70 * len(w):
            q = rng.integers(0, len(w))
            keep[q:q + 21] = False
        w.loc[~keep, IV] = np.nan
    n = len(w)
    e = np.empty(0)
    while len(e) < n:
        q = rng.integers(0, len(resid))
        e = np.concatenate([e, np.take(resid, np.arange(q, q + 63), mode="wrap")])
    m = w[HAR + [IV]].notna().all(axis=1).to_numpy() & w0.log_rv30.notna().to_numpy()
    y = np.full(n, np.nan)
    y[m] = beta[0] + w.loc[m, HAR].to_numpy(float) @ beta[1:4] + true_b * w.loc[m, IV].to_numpy(float) + (beta[4] - true_b) * pool[IV].mean() + e[:n][m]
    w["log_rv30"] = y
    w["rv30"] = np.exp(y)
    return apply_rules(w, reps=499, seed=int(rng.integers(1, 2**31)), har_train_all=False, block63=True)


for thin, count in ((False, reps), (True, reps // 2)):
    for true_b in (0.0, .25, .37, .5, .62):
        for k in range(count):
            o = one(true_b, thin)
            rows.append(dict(start=start, thin=thin, true_b=true_b, **o))
        pd.DataFrame(rows).to_csv(f"a2_sim_{start}.csv", index=False)
        print(start, thin, true_b, "done", flush=True)
