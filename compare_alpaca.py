"""Stage 4, step 5: compare Alpaca closes with official closes, on open dates only.

Run from this folder: conda run --no-capture-output -n py4fi python compare_alpaca.py
Output: data/alpaca_open_closes.parquet (written once), reports/stage4_alpaca_comparison.md and .csv
The comparison reads only the filtered parquet file after that file exists. Limits are in STAGE4_PLAN.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import realized as rz
import stage4_rules as rules
from config import DATA, DATA_END, DEVELOPMENT_START, REPORTS, load_cash_events
from load_data import load_alpaca_closes

OPEN_CLOSES = DATA / "alpaca_open_closes.parquet"
EARLY_END = pd.Timestamp("2019-07-31")
BREAK = pd.Timestamp("2025-03-01")
LIMITS = dict(B1=3, B2=5.0, B3=10.0, B4=100.0, B5=0.05, B6=0.03)
ACTIONS = dict(B1="Find the cause, fix the reader, rerun, log", B2="Find the cause, fix the reader, rerun, log", B3="Stage 4 stops, and the user decides", B4="Stage 4 stops, and the user decides", B5="Stage 4 stops, and the user decides", B6="No verdict with Alpaca RV. The user drops Stage 5, or reports the test as descriptive only")


def open_closes() -> pd.DataFrame:
    """The filtered open rows. The source file is read once, and later runs use the parquet file."""
    if not OPEN_CLOSES.exists():
        load_alpaca_closes(DEVELOPMENT_START, DATA_END).to_parquet(OPEN_CLOSES, index=False)
    return pd.read_parquet(OPEN_CLOSES)


def close_measures(joined: pd.DataFrame) -> dict:
    """Signed and absolute log differences of closes, in basis points."""
    gap = 1e4 * np.log(joined["close_alpaca"] / joined["close_official"])
    return dict(sessions=len(joined), B2=float(gap.median()), B3=float(gap.abs().median()), B4=float(gap.abs().quantile(0.99)))


def rv_measure(alpaca: pd.DataFrame, official: pd.DataFrame) -> dict:
    """Median absolute log ratio of RV30, on origins with a value in both sources."""
    joined = alpaca[["session_date", "rv30"]].merge(official[["session_date", "rv30"]], on="session_date", suffixes=("_alpaca", "_official")).dropna()
    joined = joined[(joined["rv30_alpaca"] > 0) & (joined["rv30_official"] > 0)]
    return dict(origins=len(joined), B5=float(np.log(joined["rv30_alpaca"] / joined["rv30_official"]).abs().median()))


def pre_break_b(realized: pd.DataFrame, series: pd.DataFrame) -> dict:
    panel = rules.add_inputs(realized.merge(series[["session_date", "atm30"]], on="session_date", how="left", validate="one_to_one"))
    rows = panel[panel["primary"] & (panel["session_date"] < BREAK)]
    X = np.column_stack([np.ones(len(rows))] + [rows[name].to_numpy(dtype=float) for name in rules.FULL])
    return dict(n=len(rows), b=float(np.linalg.lstsq(X, rows["log_rv30"].to_numpy(dtype=float), rcond=None)[0][-1]))


def comparison(closes: pd.DataFrame, official_daily: pd.DataFrame, series: pd.DataFrame, events: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """All limits on all overlap dates, and on 2018-05 to 2019-07 for the close and RV limits. Returns a table and counts."""
    official_closes = official_daily[["session_date", "close"]]
    first, last = max(closes["session_date"].min(), official_closes["session_date"].min()), min(closes["session_date"].max(), official_closes["session_date"].max())
    a = closes[closes["session_date"].between(first, last)].reset_index(drop=True)
    o = official_closes[official_closes["session_date"].between(first, last)].reset_index(drop=True)
    only_alpaca = sorted(set(a["session_date"]) - set(o["session_date"]))
    only_official = sorted(set(o["session_date"]) - set(a["session_date"]))
    joined = a.merge(o, on="session_date", suffixes=("_alpaca", "_official"))
    chosen = events[events["ex_date"].between(first, last)]
    realized_official = rz.realized_from_closes(o, chosen)
    # Cash on a session that Alpaca lacks cannot enter its returns, and that case already fails B1.
    realized_alpaca = rz.realized_from_closes(a, chosen[chosen["ex_date"].isin(a["session_date"])])
    all_close, early_close = close_measures(joined), close_measures(joined[joined["session_date"] <= EARLY_END])
    all_rv = rv_measure(realized_alpaca, realized_official)
    early = realized_alpaca[realized_alpaca["session_date"] <= EARLY_END]
    early_rv = rv_measure(early, realized_official[realized_official["session_date"] <= EARLY_END])
    b_alpaca, b_official = pre_break_b(realized_alpaca, series), pre_break_b(realized_official, series)
    rows = [dict(id="B1", measure="Sessions in one source only", sample="all overlap", value=float(len(only_alpaca) + len(only_official)), limit=LIMITS["B1"])]
    for key, label in (("B2", "Signed median log(Alpaca / official), bp"), ("B3", "Absolute median, bp"), ("B4", "Absolute 99th percentile, bp")):
        rows.append(dict(id=key, measure=label, sample="all overlap", value=abs(all_close[key]) if key == "B2" else all_close[key], limit=LIMITS[key]))
        rows.append(dict(id=key, measure=label, sample="2018-05 to 2019-07", value=abs(early_close[key]) if key == "B2" else early_close[key], limit=LIMITS[key]))
    rows.append(dict(id="B5", measure="Median absolute log(RV30 ratio)", sample="all overlap", value=all_rv["B5"], limit=LIMITS["B5"]))
    rows.append(dict(id="B5", measure="Median absolute log(RV30 ratio)", sample="2018-05 to 2019-07", value=early_rv["B5"], limit=LIMITS["B5"]))
    rows.append(dict(id="B6", measure="Change in b, pre-break primary rows, Alpaca RV and HAR", sample="before 2025-03", value=abs(b_alpaca["b"] - b_official["b"]), limit=LIMITS["B6"]))
    table = pd.DataFrame(rows)
    table["passed"] = table["value"] <= table["limit"]
    table["if_it_fails"] = table["id"].map(ACTIONS)
    counts = dict(first=first.date(), last=last.date(), alpaca_sessions=len(a), official_sessions=len(o), only_alpaca=[str(d.date()) for d in only_alpaca], only_official=[str(d.date()) for d in only_official], signed_median_bp=all_close["B2"], signed_median_early_bp=early_close["B2"], b_alpaca=b_alpaca, b_official=b_official, rv_origins=all_rv["origins"])
    return table, counts


def main() -> None:
    closes = open_closes()
    official = pd.read_parquet(DATA / "equity_official_daily.parquet").rename(columns={"official_close_price": "close"})
    official["session_date"] = pd.to_datetime(official["session_date"])
    series = pd.read_parquet(DATA / "index_series.parquet")
    table, counts = comparison(closes, official, series, load_cash_events(DEVELOPMENT_START, DATA_END))
    table.to_csv(REPORTS / "stage4_alpaca_comparison.csv", index=False)
    lines = ["| " + " | ".join(table.columns) + " |", "|" + "---|" * len(table.columns)]
    for row in table.itertuples(index=False):
        lines.append("| " + " | ".join(f"{v:.4f}" if isinstance(v, float) else str(v) for v in row) + " |")
    text = "\n".join(["# Stage 4: Alpaca against official closes, open dates only", "", f"Overlap: {counts['first']} to {counts['last']}. Alpaca sessions: {counts['alpaca_sessions']}. Official sessions: {counts['official_sessions']}.", f"Only in Alpaca: {counts['only_alpaca']}. Only in the official table: {counts['only_official']}.", f"Signed median, bp: {counts['signed_median_bp']:.3f} on all dates, {counts['signed_median_early_bp']:.3f} on 2018-05 to 2019-07.", f"Pre-break b: {counts['b_alpaca']['b']:.4f} with Alpaca on {counts['b_alpaca']['n']} rows, {counts['b_official']['b']:.4f} with official closes on {counts['b_official']['n']} rows. Official closes here use the same close-only path, and the study value is .525.", "", *lines, "", "A pass on open dates does not prove the same fit in 2016-2017. The limits use assumed noise sizes, because nobody had read the Alpaca file.", ""])
    (REPORTS / "stage4_alpaca_comparison.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
