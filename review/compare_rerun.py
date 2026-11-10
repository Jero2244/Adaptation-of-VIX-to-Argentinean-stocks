"""Compare the Stage 3 outputs with the backup from before Stage 4. Prints differences only, with no market values."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKUP = ROOT / "review" / "pre_stage4_backup"
SKIP_COLUMNS = {"sample_id"}  # A salted hash that changes per process.


def compare(new: pd.DataFrame, old: pd.DataFrame, name: str) -> bool:
    if list(new.columns) != list(old.columns) or len(new) != len(old):
        print(f"{name}: shape or columns differ: {new.shape} {old.shape}")
        return False
    same = True
    for column in new.columns:
        if column in SKIP_COLUMNS:
            continue
        if pd.api.types.is_numeric_dtype(new[column]) and pd.api.types.is_numeric_dtype(old[column]):
            a, b = new[column].to_numpy(dtype=float), old[column].to_numpy(dtype=float)
            if not np.allclose(a, b, rtol=1e-9, atol=1e-12, equal_nan=True):
                print(f"{name}.{column}: numeric difference, largest {np.nanmax(np.abs(a - b))}")
                same = False
        elif not new[column].astype(str).equals(old[column].astype(str)):
            print(f"{name}.{column}: text difference")
            same = False
    return same


results = [compare(pd.read_parquet(ROOT / "data" / "forecast_panel.parquet"), pd.read_parquet(BACKUP / "data" / "forecast_panel.parquet"), "forecast_panel")]
for path in sorted((BACKUP / "reports").glob("*.csv")):
    results.append(compare(pd.read_csv(ROOT / "reports" / path.name), pd.read_csv(path), path.name))
print(f"{sum(results)} of {len(results)} outputs have no difference")
sys.exit(0 if all(results) else 1)
