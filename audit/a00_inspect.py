"""Audit step 0: look at the derived tables. Read-only. Writes nothing in the project."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 200)

for name in ["index_series", "atm_terms", "forecast_panel", "option_snapshot_1545", "option_listed", "session_diagnostics", "equity_official_daily", "calibration_panel"]:
    f = pd.read_parquet(D / f"{name}.parquet")
    print(f"\n=== {name}: {f.shape}")
    print(f.dtypes.to_string())
    print(f.head(3).to_string())

s = pd.read_parquet(D / "index_series.parquet")
print("\nATM30 describe\n", s["atm30"].describe())
print("\nstatus counts\n", s["status"].value_counts())
print("\nnear_weight describe\n", s["near_weight"].describe())
print("\nnear_days when ok\n", s.loc[s.atm30.notna(), "near_days"].describe())
print("\nfar_days when ok\n", s.loc[s.atm30.notna(), "far_days"].describe())
d = pd.read_parquet(D / "session_diagnostics.parquet")
print("\ndiagnostics describe\n", d.describe().T.to_string())
print(d["first_bar"].value_counts().head(8), d["last_bar"].value_counts().head(8))
e = pd.read_parquet(D / "equity_official_daily.parquet")
print("\nofficial daily describe\n", e.describe().T.to_string())
print(e[e.isna().any(axis=1)].to_string())
