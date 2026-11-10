"""Daily intraday RV from Nasdaq bbo-1m mids on open dates only (the gate runs in iter_days). Output stays in the scratchpad."""
import sys
PROJECT = r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation"
sys.path.insert(0, PROJECT)
import numpy as np, pandas as pd
from config import DEVELOPMENT_START, DATA_END, EQUITY_BBO
from load_data import iter_days, NY

OUT = sys.argv[0].replace(".py", ".parquet")
rows = []
for k, (day, f) in enumerate(iter_days(EQUITY_BBO, DEVELOPMENT_START, DATA_END, map_symbols=False)):
    if k == 0:
        print(f.columns.tolist())
    ts = f["ts_recv"].dt.tz_convert(NY)
    bid, ask = f["bid_px_00"], f["ask_px_00"]
    good = (bid > 0) & (ask >= bid)
    s = pd.Series(((bid + ask) / 2)[good].to_numpy(), index=ts[good]).sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s = s.between_time("09:30", "16:00")
    row = dict(session_date=pd.Timestamp(day), n=len(s))
    if len(s) > 10:
        for m in (5, 15, 30):
            g = s.resample(f"{m}min", label="right", closed="right").last().dropna()
            r = np.log(g).diff().dropna()
            row[f"rv_{m}m"] = float((r ** 2).sum())
            row[f"oc_{m}m_first"] = float(g.iloc[0])
            row[f"last"] = float(g.iloc[-1])
    rows.append(row)
out = pd.DataFrame(rows)
out.to_parquet(OUT, index=False)
print(out.describe().T.to_string())
