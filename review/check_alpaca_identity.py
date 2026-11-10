"""Check that the Alpaca and official close tables are separate sources. Open dates only."""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
a = pd.read_parquet(ROOT / "data" / "alpaca_open_closes.parquet")
o = pd.read_parquet(ROOT / "data" / "equity_official_daily.parquet").rename(columns={"official_close_price": "official"})
o["session_date"] = pd.to_datetime(o["session_date"])
j = a.merge(o[["session_date", "official"]], on="session_date")
gap = 1e4 * np.log(j["close"] / j["official"])
differ = gap.abs() > 1e-6
print("sessions", len(j), "with a different close", int(differ.sum()), "largest absolute gap, bp", round(float(gap.abs().max()), 2))
print("different closes by year:", j[differ].groupby(j["session_date"].dt.year).size().to_dict())
