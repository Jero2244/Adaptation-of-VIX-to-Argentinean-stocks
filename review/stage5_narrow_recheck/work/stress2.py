"""How often does the no-forward branch fire on clean closes, by the share and run length of blank forwards? Open dates only. No locked data."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
from pathlib import Path
from common import make_copy
d = make_copy("st"); sys.path.insert(0, str(d))
import run_tests_once as rt
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation\data")
OPEN = pd.Timestamp("2018-05-01")
close = pd.read_parquet(REAL / "alpaca_open_closes.parquet")
series = pd.read_parquet(REAL / "index_series.parquet", columns=["session_date", "near_forward"])
assert close["session_date"].min() >= OPEN and series["session_date"].min() >= OPEN
panel = close.merge(series, on="session_date", how="left").reset_index(drop=True)
print("Daily sd of log close change, open data:", round(np.log(panel.close).diff().std(), 4))
rng = np.random.default_rng(7)
N = 585
# Use closes of all sessions, and the close itself as the forward, so the only change is the pattern of blanks.
def trial(share, mean_run, vol_scale):
    s = int(rng.integers(0, len(panel) - N - 1))
    lc = np.log(panel.close.to_numpy()[s:s + N])
    lc = lc[0] + np.r_[0, np.cumsum(np.diff(lc) * vol_scale)]
    c = np.exp(lc); mask = np.zeros(N, bool)
    while mask.mean() < share:
        a = int(rng.integers(0, N)); mask[a:a + int(rng.geometric(1 / mean_run))] = True
    w = pd.DataFrame(dict(session_date=panel.session_date.iloc[s:s + N].to_numpy(), close=c, near_forward=np.where(mask, np.nan, c)))
    return bool((rt.no_forward_gaps(w) > .15).any())
for scale in (1.0, 0.7):
    print(f"vol scale {scale}: share of 585-session windows with a false stop (rows: blank share; columns: mean run)")
    print("        " + "".join(f"run {m:<5d}" for m in (2, 3, 5, 8, 15)))
    for share in (.14, .25, .35, .49):
        print(f"  {share:.2f}  " + "".join(f"{np.mean([trial(share, m, scale) for _ in range(150)]):<9.1%}" for m in (2, 3, 5, 8, 15)))
# The real open pattern of blanks, moved in time along other closes: keeps real run lengths.
blank = panel.near_forward.isna().to_numpy()
fired = []
for shift in range(0, len(panel), 25):
    b = np.roll(blank, shift)
    w = panel.assign(near_forward=np.where(b, np.nan, panel.close))
    fired.append(((rt.no_forward_gaps(w) > .15).sum()))
print("Real blank pattern, shifted along the closes: full-sample shifts with any false stop:", int(np.sum(np.array(fired) > 0)), "of", len(fired), "| median sessions above limit", np.median(fired))
