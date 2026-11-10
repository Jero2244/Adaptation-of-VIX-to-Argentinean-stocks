"""Shared helpers for the fixes folder. DEVELOPMENT work on open data (2018-05-01 onward). Nothing here replaces the pre-registered result.

Frozen modules are imported read-only. No frozen file is edited. Run every script from this folder with the py4fi Python.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (ROOT, ROOT / "audit"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import inference as inf  # noqa: E402
import realized as rz  # noqa: E402
import stage4_rules as rules  # noqa: E402

LABEL = "DEVELOPMENT work on open data, 2018-05-01 to 2026-10-29. Not the pre-registered result. Does not replace Stage 5."
DATA = ROOT / "data"
FDATA = HERE / "data"
FDATA.mkdir(exist_ok=True)
HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
SEED = rules.SEED
REPS = rules.REPS
NW_LAGS = 21
pd.set_option("display.width", 250, "display.max_columns", 80, "display.max_rows", 400)


def make_panel(series: pd.DataFrame, realized: pd.DataFrame | None = None, atm_col: str = "atm30") -> pd.DataFrame:
    """Realized frame (full session grid, with 'position') merged with a series that has session_date and atm_col."""
    realized = rz.build_realized() if realized is None else realized
    s = series[["session_date", atm_col]].rename(columns={atm_col: "atm30"})
    panel = realized.merge(s, on="session_date", how="left", validate="one_to_one")
    return rules.add_inputs(panel)


def fit_b(frame: pd.DataFrame, names=None, key: str = IV, y_name: str = "log_rv30", reps: int = REPS, blocks=(21, 63)) -> dict:
    """Same estimator as run_development.regression_rows: OLS, Newey-West(21) t, circular block bootstrap with SEED + block."""
    names = HAR + [IV] if names is None else names
    y = frame[y_name].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(dtype=float) for n in names])
    fit = inf.ols(y, X)
    k = 1 + names.index(key)
    se = inf.newey_west_se(X, fit["residuals"], NW_LAGS)
    out = dict(n=len(frame), b=float(fit["beta"][k]), nw_se=float(se[k]), nw_t=float(fit["beta"][k] / se[k]), r2=float(fit["r2"]))
    positions = frame["position"].to_numpy()
    span = int(positions[-1] - positions[0] + 1)

    def est(idx):
        return np.linalg.lstsq(X[idx], y[idx], rcond=None)[0]

    for block in blocks:
        if reps <= 0 or block * 3 > span:
            continue
        s = inf.bootstrap_summary(fit["beta"], inf.block_bootstrap(est, positions, block, reps, SEED + block))
        out[f"boot{block}_t"] = float(s["t"][k]); out[f"boot{block}_low"] = float(s["low"][k]); out[f"boot{block}_high"] = float(s["high"][k])
    return out


def har_r2(frame: pd.DataFrame, y_name: str = "log_rv30") -> float:
    y = frame[y_name].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(frame))] + [frame[n].to_numpy(dtype=float) for n in HAR])
    return float(inf.ols(y, X)["r2"])
