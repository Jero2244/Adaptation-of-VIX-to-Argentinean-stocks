"""Check the input stop on open 28-month windows. A false stop would end a run with no fault. Open dates only. Prints counts, with no market value."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import run_tests_once as rt  # noqa: E402

closes = pd.read_parquet(ROOT / "data" / "alpaca_open_closes.parquet")
series = pd.read_parquet(ROOT / "data" / "index_series.parquet")[["session_date", "near_forward"]]
panel = closes.merge(series, on="session_date", how="left")
results = []
for start in pd.period_range("2018-05", "2024-05", freq="M"):
    window = panel[panel["session_date"].between(start.to_timestamp(), (start + 27).to_timestamp(how="end"))]
    try:
        rt.input_guard(window, 0, 0)
        results.append(True)
    except rt.InputGuardFailed as error:
        print(start, error)
        results.append(False)
print(f"windows {len(results)}, passed {sum(results)}")
