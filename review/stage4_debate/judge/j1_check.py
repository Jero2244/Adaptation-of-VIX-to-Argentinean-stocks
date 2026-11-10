"""Judge check of the Stage 4 debate. Exploratory. Open pre-2025-03 panel rows only. No locked data, no Alpaca file.

Part 1 recomputes the disputed rule comparison from the advocate's stored simulations.
Part 2 is a separate simulation that uses other base windows, a 42-session residual block, and the study's own
block_bootstrap, so it shares no simulation code with either agent.
Part 3 reproduces the development reference values.
"""
import glob
import sys
import numpy as np
import pandas as pd

ROOT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
HERE = r"C:\Users\HPLAPT~1\AppData\Local\Temp\claude\e4b19ea5a582ebf6\5265b482-23f7-4be4-a036-a8320fa41846\scratchpad"
sys.path.insert(0, ROOT)
from inference import block_sample  # noqa: E402

# Part 1
s = pd.concat(pd.read_csv(f) for f in glob.glob(HERE + r"\advocate\a2_sim_*.csv"))
s = s[~s.thin]
rules = {
    "21 interval": s.lo > 0,
    "21 and 63 intervals": (s.lo > 0) & (s.lo63 > 0),
    "21 interval + CW gate": (s.lo > 0) & (s.cw_t > 1.65),
    "21 and 63 + CW gate": (s.lo > 0) & (s.lo63 > 0) & (s.cw_t > 1.65),
    "b <= 0": s.b <= 0,
    "upper21 and upper63 < .37": (s.hi < .37) & (s.hi63 < .37),
}
table = pd.DataFrame({k: v.groupby(s.true_b).mean() for k, v in rules.items()}).T
table["LR .37 vs 0"] = table[.37] / table[0.0]
table["LR .62 vs 0"] = table[.62] / table[0.0]
print("PART 1, advocate stored simulations, rows per true b:", int((s.true_b == 0).sum()))
print(table.round(3).to_string())
g = (s.lo > 0) & (s.lo63 > 0)
print("CW passes given both intervals pass:", ((s.cw_t > 1.65)[g]).groupby(s.true_b[g]).mean().round(3).to_dict())

# Part 3
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=["session_date", "position", "primary", "log_rv30", "log_rv1", "log_rv5", "log_rv22", "log_iv2"])
pre = p[p.primary & (p.session_date < "2025-03-01")].reset_index(drop=True)
X_names = ["log_rv1", "log_rv5", "log_rv22", "log_iv2"]


def design(frame):
    return np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(float) for n in X_names])


full = np.linalg.lstsq(design(pre), pre.log_rv30.to_numpy(float), rcond=None)[0]
print("\nPART 3, pre-break primary rows", len(pre), "b", round(full[4], 3))
allb = np.linalg.lstsq(design(p[p.primary]), p[p.primary].log_rv30.to_numpy(float), rcond=None)[0]
print("all primary rows", int(p.primary.sum()), "b", round(allb[4], 3))

# Part 2
resid = pre.log_rv30.to_numpy(float) - design(pre) @ full
rng = np.random.default_rng(20261104)
REPS, BOOTS, RESID_BLOCK = 240, 299, 42
windows = ["2018-11", "2020-03", "2021-08", "2022-06"]
rows = []
for start in windows:
    s0 = pd.Period(start, "M")
    w = pre[(pre.session_date >= s0.to_timestamp()) & (pre.session_date <= (s0 + 27).to_timestamp(how="end").normalize())].reset_index(drop=True)
    X = design(w)
    positions = w.position.to_numpy(int)
    pinv = None
    for true_b in (0.0, .37, .62):
        for rep in range(REPS // len(windows)):
            noise = np.empty(0)
            while len(noise) < len(w):
                q = rng.integers(0, len(resid))
                noise = np.concatenate([noise, np.take(resid, np.arange(q, q + RESID_BLOCK), mode="wrap")])
            coefficients = full.copy()
            coefficients[4] = true_b
            y = X @ coefficients + noise[:len(w)]
            estimate = np.linalg.lstsq(X, y, rcond=None)[0][4]
            bounds = {}
            for block in (21, 63):
                draws = np.empty(BOOTS)
                for k in range(BOOTS):
                    index = block_sample(positions, block, rng)
                    draws[k] = np.linalg.lstsq(X[index], y[index], rcond=None)[0][4]
                bounds[block] = np.percentile(draws, [2.5, 97.5])
            rows.append(dict(start=start, n=len(w), true_b=true_b, b=estimate, lo21=bounds[21][0], hi21=bounds[21][1], lo63=bounds[63][0], hi63=bounds[63][1]))
d = pd.DataFrame(rows)
d.to_csv(HERE + r"\judge\j1_sim.csv", index=False)
d["sup21"] = d.lo21 > 0
d["sup_both"] = (d.lo21 > 0) & (d.lo63 > 0)
d["below"] = (d.hi21 < .37) & (d.hi63 < .37)
d["nonpos"] = d.b <= 0
print("\nPART 2, separate simulation, rows per true b:", int((d.true_b == 0).sum()), "window rows", d.groupby("start").n.first().to_dict())
print(d.groupby("true_b")[["sup21", "sup_both", "below", "nonpos"]].mean().round(3).to_string())
print("SD of b by true b:", d.groupby("true_b").b.std().round(3).to_dict())
print("by window, sup_both:")
print(d.groupby(["start", "true_b"]).sup_both.mean().unstack().round(3).to_string())
