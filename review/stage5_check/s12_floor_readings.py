"""The floor text. PROTOCOL.md says "at least 20 consecutive 21-session spans hold 10 or more". STAGE4_PLAN.md and the code count any 20 spans.
How often do the two readings differ on open 28-month windows, with the frozen frame rules? Open rows only."""
import _common
from _common import ROOT
import numpy as np, pandas as pd
import stage4_rules as rules

p = pd.read_parquet(ROOT / "data/forecast_panel.parquet", columns=["session_date", "window_end", "log_iv2", "log_rv30", "log_rv1", "log_rv5", "log_rv22"])
p = p[p.session_date < "2025-03-01"]
rows = []
for start in pd.period_range("2018-05", "2022-11", freq="M"):
    w = p[(p.session_date >= start.to_timestamp()) & (p.session_date <= (start + 27).to_timestamp(how="end").normalize())].reset_index(drop=True)
    v = w[["log_iv2", "log_rv30", "log_rv1", "log_rv5", "log_rv22"]].notna().all(axis=1).to_numpy() & (np.arange(len(w)) >= 22) & (w.window_end <= w.session_date.iloc[-1]).to_numpy()
    floor = rules.data_floor(v)
    first = int(np.flatnonzero(v)[0])
    filled = [int(v[s:s + 21].sum()) >= 10 for s in range(first, len(v), 21)]
    run = best = 0
    for f in filled:
        run = run + 1 if f else 0
        best = max(best, run)
    rows.append(dict(start=str(start), origins=floor["origins"], spans=len(filled), filled=floor["filled_spans"], longest_adjacent=best, code=floor["passed"], adjacent_reading=floor["origins"] >= 300 and best >= 20))
d = pd.DataFrame(rows)
print("windows", len(d), "pass by code", int(d.code.sum()), "pass by adjacent reading", int(d.adjacent_reading.sum()), "differ", int((d.code != d.adjacent_reading).sum()))
print(d[d.code != d.adjacent_reading].to_string(index=False))
print("origins min, median", d.origins.min(), d.origins.median())
