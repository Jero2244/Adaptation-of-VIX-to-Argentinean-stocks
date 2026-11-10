"""Open dates only. Test the proposed condition for a close on a session with no near forward: stop only if the close is above .15 from the forwards on both sides, and also above .15 from both adjacent closes.

For each real no-forward session, multiply that one close by a factor, and count how often each rule stops. Also count the real closes that meet each part with no fault. Prints counts and rates, with no market value."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
LIMIT = 0.15
closes = pd.read_parquet(ROOT / "data" / "alpaca_open_closes.parquet")
assert closes["session_date"].min() >= pd.Timestamp("2018-05-01")
series = pd.read_parquet(ROOT / "data" / "index_series.parquet")[["session_date", "near_forward"]]
panel = closes.merge(series, on="session_date", how="left").sort_values("session_date").reset_index(drop=True)
close = panel["close"].to_numpy(float)
forward = panel["near_forward"]
before = forward.ffill().shift(1).to_numpy(float)
after = forward.bfill().shift(-1).to_numpy(float)
blank = np.flatnonzero(forward.isna().to_numpy())


def smaller(value, left, right):
    gaps = [abs(np.log(value / side)) for side in (left, right) if np.isfinite(side)]
    return min(gaps) if gaps else np.nan


def forward_rule(i, value):
    return smaller(value, before[i], after[i]) > LIMIT


def close_rule(i, value):
    left = close[i - 1] if i > 0 else np.nan
    right = close[i + 1] if i < len(close) - 1 else np.nan
    return smaller(value, left, right) > LIMIT


print("sessions", len(close), "no forward", len(blank))
real_close_rule = [close_rule(i, close[i]) for i in range(len(close))]
print("real closes above .15 from both adjacent closes, all sessions", int(np.nansum(real_close_rule)))
print("no fault, forward rule stops", sum(forward_rule(i, close[i]) for i in blank), "both rules stop", sum(forward_rule(i, close[i]) and close_rule(i, close[i]) for i in blank))
print("factor, share stopped by the forward rule, share stopped by both rules")
for factor in (0.5, 0.7, 0.8, 0.85, 1.15, 1.2, 1.25, 1.5, 2.0):
    first = np.mean([forward_rule(i, close[i] * factor) for i in blank])
    both = np.mean([forward_rule(i, close[i] * factor) and close_rule(i, close[i] * factor) for i in blank])
    print(factor, round(float(first), 3), round(float(both), 3))
