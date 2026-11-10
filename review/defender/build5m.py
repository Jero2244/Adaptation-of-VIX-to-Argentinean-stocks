import sys
sys.path.insert(0, r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
from config import EQUITY_BBO, DEVELOPMENT_START, DATA_END
from load_data import iter_days, NY

OUT = __import__("os").path.join(__import__("os").path.dirname(__import__("os").path.abspath(__file__)), "rv5m.csv")
rows = []
for day, f in iter_days(EQUITY_BBO, DEVELOPMENT_START, DATA_END, map_symbols=False):
    if f.empty:
        continue
    g = f[(f.bid_px_00 > 0) & (f.ask_px_00 >= f.bid_px_00)].copy()
    t = g.ts_recv.dt.tz_convert(NY).dt.tz_localize(None)
    g.index = t
    d = t.iloc[0].normalize() if len(t) else None
    if d is None:
        continue
    g = g.between_time("09:30", "16:00")
    if len(g) < 2:
        continue
    mid = np.log((g.bid_px_00 + g.ask_px_00) / 2).sort_index()
    five = mid.resample("5min", label="right", closed="right").last().ffill().dropna()
    rows.append(dict(session_date=d, rv5=float((five.diff().dropna() ** 2).sum()), first=float(five.iloc[0]), last=float(five.iloc[-1]), bars=len(five), ids=f.instrument_id.nunique()))
pd.DataFrame(rows).to_csv(OUT, index=False)
print(len(rows), rows[0], rows[-1])
