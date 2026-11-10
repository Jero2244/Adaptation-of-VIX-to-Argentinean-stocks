"""Open dates only. Run the real input_guard functions on the two tests behind question A, and on bad closes in adjacent pairs.

Prints counts and rates, with no market value."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True
import run_tests_once as rt  # noqa: E402

LIMIT = rt.GUARD_NO_FORWARD
closes = pd.read_parquet(ROOT / "data" / "alpaca_open_closes.parquet")
series = pd.read_parquet(ROOT / "data" / "index_series.parquet", columns=["session_date", "near_forward"])
assert closes["session_date"].min() >= pd.Timestamp("2018-05-01") and series["session_date"].min() >= pd.Timestamp("2018-05-01")
panel = closes.merge(series, on="session_date", how="left").sort_values("session_date").reset_index(drop=True)[["session_date", "close", "near_forward"]]


def old_rule(frame):
    return bool((rt.no_forward_gaps(frame) > LIMIT).any())


def new_rule(frame):
    far = rt.no_forward_gaps(frame) > LIMIT
    return bool((far & (rt.adjacent_close_gaps(frame).reindex(far.index) > LIMIT)).any())


blank = np.flatnonzero(panel["near_forward"].isna().to_numpy())
print("sessions", len(panel), "no forward", len(blank))
print("real panel: old rule stops", old_rule(panel), "new rule stops", new_rule(panel))
print("real closes above the limit from both adjacent closes", int((rt.adjacent_close_gaps(panel) > LIMIT).sum()))

print("one bad close: factor, old rule share, new rule share")
for factor in (0.5, 0.7, 0.8, 0.85, 1.15, 1.2, 1.25, 1.5, 2.0):
    old = new = 0
    for i in blank:
        changed = panel.copy()
        changed.loc[i, "close"] *= factor
        old += old_rule(changed)
        new += new_rule(changed)
    print(factor, f"{old / len(blank):.1%}", f"{new / len(blank):.1%}")

pairs = blank[np.isin(blank + 1, blank)]
print("two adjacent bad closes with the same factor, on", len(pairs), "adjacent blank pairs: factor, old rule share, new rule share")
for factor in (0.5, 0.7, 0.8, 1.25, 1.5, 2.0):
    old = new = 0
    for i in pairs:
        changed = panel.copy()
        changed.loc[[i, i + 1], "close"] *= factor
        old += old_rule(changed)
        new += new_rule(changed)
    print(factor, f"{old / len(pairs):.1%}", f"{new / len(pairs):.1%}")

rng = np.random.default_rng(3)
pattern_all = panel["near_forward"].isna().to_numpy()
N, tries, old, new = 585, 600, 0, 0
for _ in range(tries):
    shift, start, start2 = int(rng.integers(len(panel))), int(rng.integers(len(panel) - N)), int(rng.integers(len(panel) - N))
    pattern = np.roll(pattern_all, shift)[start2:start2 + N]
    window = panel.iloc[start:start + N].reset_index(drop=True)
    window = window.assign(near_forward=np.where(pattern, np.nan, window["close"]))
    old += old_rule(window)
    new += new_rule(window)
print(f"blank pattern moved at random, {tries} windows of {N}: old rule false stop {old / tries:.1%}, new rule false stop {new / tries:.1%}")
