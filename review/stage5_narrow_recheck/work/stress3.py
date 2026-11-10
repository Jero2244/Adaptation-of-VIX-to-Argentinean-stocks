"""Open dates only. The real pattern of blank forwards, moved along the closes, in 585-session windows. Rule A is the rule as coded. Rule B adds: the close is also far from both adjacent closes."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
from pathlib import Path
from common import make_copy
d = make_copy("st3"); sys.path.insert(0, str(d))
import run_tests_once as rt
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation\data")
close = pd.read_parquet(REAL / "alpaca_open_closes.parquet")
series = pd.read_parquet(REAL / "index_series.parquet", columns=["session_date", "near_forward"])
assert close["session_date"].min() >= pd.Timestamp("2018-05-01") and series["session_date"].min() >= pd.Timestamp("2018-05-01")
panel = close.merge(series, on="session_date", how="left").reset_index(drop=True)
blank = panel.near_forward.isna().to_numpy(); n = len(panel); N = 585
lc = np.log(panel.close)
spike = pd.concat([lc.diff().abs(), lc.diff(-1).abs()], axis=1).min(axis=1) > .15
print("sessions with a real close far from both adjacent closes (Rule B alone):", int(spike.sum()), "of", n)
a = b = t = 0
rng = np.random.default_rng(3)
for _ in range(600):
    shift, s, s2 = int(rng.integers(n)), int(rng.integers(n - N)), int(rng.integers(n - N))
    pattern = np.roll(blank, shift)[s2:s2 + N]
    w = panel.iloc[s:s + N].reset_index(drop=True)
    w = w.assign(near_forward=np.where(pattern, np.nan, w.close))
    g = rt.no_forward_gaps(w) > .15
    t += 1; a += bool(g.any()); b += bool((g & spike.iloc[s:s + N].reset_index(drop=True).reindex(g.index)).any())
print(f"585-session windows, real blank pattern ({pattern.mean():.0%} blank in the last draw): Rule A false stop {a/t:.1%}, Rule B false stop {b/t:.1%}")
w = panel.reset_index(drop=True); g = rt.no_forward_gaps(w)
print("actual alignment: max gap", round(g.max(), 4), "| sessions above .10:", int((g > .10).sum()), "| above .08:", int((g > .08).sum()))
