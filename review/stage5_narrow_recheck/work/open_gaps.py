"""No-forward gaps on open dates only. Stored open parquet files. Asserts the date range before any calculation."""
import sys
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
from pathlib import Path
from common import make_copy
d = make_copy("og"); sys.path.insert(0, str(d))
import run_tests_once as rt
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation\data")
OPEN = pd.Timestamp("2018-05-01")
close = pd.read_parquet(REAL / "alpaca_open_closes.parquet")
series = pd.read_parquet(REAL / "index_series.parquet", columns=["session_date", "near_forward", "atm30"])
assert close["session_date"].min() >= OPEN and series["session_date"].min() >= OPEN
panel = close.merge(series, on="session_date", how="left")
print("rows", len(panel), "first", panel.session_date.min().date(), "last", panel.session_date.max().date())
gaps = rt.no_forward_gaps(panel)
print("no-forward sessions with close:", len(gaps), "max gap", round(gaps.max(), 4), "above .15:", int((gaps > .15).sum()))
print("min near_forward on open data:", round(panel.near_forward.min(), 3), "| not positive:", int((panel.near_forward <= 0).sum()))
blank = panel.near_forward.isna().to_numpy()
runs = []; n = 0
for b in blank:
    if b: n += 1
    elif n: runs.append(n); n = 0
if n: runs.append(n)
print("blank runs:", len(runs), "longest", max(runs), "top", sorted(runs)[-6:])
print("atm30 present share of rows:", round(panel.atm30.notna().mean(), 3), "near_forward present share:", round(panel.near_forward.notna().mean(), 3))
# Windows of 28 months, one month apart.
starts = pd.date_range("2018-05-01", "2024-07-01", freq="MS"); nw = stops = 0; worst = 0
for s in starts:
    e = s + pd.DateOffset(months=28) - pd.Timedelta(days=1)
    w = panel[panel.session_date.between(s, e)].reset_index(drop=True)
    if len(w) < 300: continue
    nw += 1; g = rt.no_forward_gaps(w); worst = max(worst, g.max() if len(g) else 0)
    try:
        rt.input_guard(w, 0, 0)
    except rt.InputGuardFailed as x:
        stops += 1; print("  stop in window", s.date(), str(x)[:50])
print("windows", nw, "stops", stops, "worst no-forward gap", round(worst, 4))
# Stress: how often does a clean close trip the new branch if option days are thinner than on open data?
rng = np.random.default_rng(5); full = panel.dropna(subset=["near_forward"]).reset_index(drop=True)
print("full rows with forward:", len(full))
for L in (5, 10, 20, 30, 40, 60):
    fired = 0; starts_ = range(1, len(full) - L - 1, 3)
    for i in starts_:
        w = full.iloc[max(0, i - 2): i + L + 2].copy()
        w.iloc[2:2 + L, w.columns.get_loc("near_forward")] = np.nan
        fired += bool((rt.no_forward_gaps(w) > .15).any())
    print(f"blank run of {L:3d} sessions, clean closes: stop in {fired/len(starts_):.1%} of placements")
for keep_share in (.8, .6, .5):
    fired = 0
    for trial in range(200):
        s = int(rng.integers(0, len(full) - 590)); w = full.iloc[s:s + 585].copy()
        # Random blank runs, mean length 8, until the share is met.
        mask = np.zeros(585, bool)
        while mask.mean() < 1 - keep_share:
            a = int(rng.integers(0, 585)); mask[a:a + int(rng.geometric(1/8))] = True
        w.loc[w.index[mask], "near_forward"] = np.nan
        fired += bool((rt.no_forward_gaps(w) > .15).any())
    print(f"28-month window, {1-keep_share:.0%} of forwards blank in runs (mean 8): stop in {fired/200:.1%} of trials")
