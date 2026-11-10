"""Stage 2, part 1: decode the 15:45 New York snapshot for each session, and fetch the Treasury rates.

Run from this folder: conda run -n py4fi python build_snapshot.py
Output: data/option_snapshot_1545.parquet, data/option_listed.parquet, data/session_diagnostics.parquet,
data/source/fred_rates.csv. The snapshot keeps the last regular-session quote at or before 15:45 with its age.
The age filter is applied later, in build_series.py.
"""
from __future__ import annotations

import io
import time as clock
import urllib.request
from pathlib import Path

import pandas as pd

from config import (DATA, DATA_END, DEVELOPMENT_START, EQUITY_BBO, OPTION_CBBO, OPTION_DEFINITIONS, OPTION_ROOT, SCOPE_OPTIONS, SOURCE)
from load_data import NY, iter_days, parse_occ

FRED_SERIES = ["DGS1MO", "DGS3MO"]
FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd=2018-01-01&coed=2026-10-30"


def fetch_rates() -> None:
    frames = []
    for series in FRED_SERIES:
        with urllib.request.urlopen(FRED_URL.format(series=series), timeout=60) as response:
            frame = pd.read_csv(io.BytesIO(response.read()))
        frames.append(frame.set_index("observation_date")[series])
    pd.concat(frames, axis=1).to_csv(SOURCE / "fred_rates.csv")


def last_quotes(frame: pd.DataFrame, day) -> pd.DataFrame:
    """Last non-null value of each column per instrument from 09:30 to 15:45 New York, with quote age in minutes. See PROTOCOL.md, "Quote snapshot"."""
    opening = pd.Timestamp(f"{day} 09:30", tz=NY)
    cutoff = pd.Timestamp(f"{day} 15:45", tz=NY)
    inside = frame[(frame["ts_recv"] >= opening) & (frame["ts_recv"] <= cutoff)]
    last = inside.sort_values("ts_recv", kind="stable").groupby("instrument_id", as_index=False).last()
    last["age"] = (cutoff - last["ts_recv"]).dt.total_seconds() / 60
    return last


def last_row_null_bids(frame: pd.DataFrame, day) -> int:
    """Instruments whose last row in the snapshot window has a null bid. last_quotes keeps an older bid for these, so this count shows how often that applies."""
    opening = pd.Timestamp(f"{day} 09:30", tz=NY)
    cutoff = pd.Timestamp(f"{day} 15:45", tz=NY)
    inside = frame[(frame["ts_recv"] >= opening) & (frame["ts_recv"] <= cutoff)]
    return int(inside.sort_values("ts_recv", kind="stable").drop_duplicates("instrument_id", keep="last")["bid_px_00"].isna().sum())


def snapshot_tables(start, end, marker: Path | None = None, use_equity: bool = True, progress: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Snapshot, listed expiries, and diagnostics per session, in memory. The date gate runs in iter_days.

    The Nasdaq equity quotes start in 2018-05. So a read without equity has no stock mid, and it never joins equity data.
    """
    definitions = iter_days(OPTION_DEFINITIONS, start, end, map_symbols=False, marker=marker, scope=SCOPE_OPTIONS)
    quotes = iter_days(OPTION_CBBO, start, end, map_symbols=False, marker=marker, scope=SCOPE_OPTIONS)
    equity = iter_days(EQUITY_BBO, start, end, map_symbols=False, marker=marker, scope=SCOPE_OPTIONS) if use_equity else None

    snapshots, listed, diagnostics = [], [], []
    started = clock.time()
    for count, ((day_d, defs), (day_q, cbbo)) in enumerate(zip(definitions, quotes, strict=True), start=1):
        day_e, bbo = next(equity) if use_equity else (day_q, None)
        if not day_d == day_q == day_e:
            raise ValueError("The files are out of step")
        session = pd.Timestamp(day_q)

        defs = defs.sort_values("ts_recv", kind="stable").drop_duplicates("instrument_id", keep="last")
        parsed = pd.DataFrame([parse_occ(symbol) for symbol in defs["raw_symbol"]], columns=["root", "expiry", "right", "strike"], index=defs.index)
        contracts = pd.concat([defs[["instrument_id", "raw_symbol"]], parsed], axis=1)
        other_roots = int((contracts["root"] != OPTION_ROOT).sum())
        contracts = contracts[contracts["root"] == OPTION_ROOT]
        listed.append(contracts.groupby("expiry", as_index=False).size().assign(session_date=session))

        last = last_quotes(cbbo, day_q)
        joined = last.merge(contracts, on="instrument_id", how="left")
        unmatched = int(joined["raw_symbol"].isna().sum())
        joined = joined.dropna(subset=["raw_symbol"])
        snapshots.append(pd.DataFrame({
            "session_date": session, "symbol": joined["raw_symbol"], "expiry": pd.to_datetime(joined["expiry"]), "right": joined["right"],
            "strike": joined["strike"], "bid": joined["bid_px_00"], "ask": joined["ask_px_00"], "bid_size": joined["bid_sz_00"],
            "ask_size": joined["ask_sz_00"], "age": joined["age"]}))

        stock = last_quotes(bbo, day_q) if use_equity else None
        has_stock = stock is not None and len(stock) > 0
        stock_mid = (stock["bid_px_00"].iloc[-1] + stock["ask_px_00"].iloc[-1]) / 2 if has_stock else float("nan")
        times = cbbo["ts_recv"].dt.tz_convert(NY)
        diagnostics.append(dict(
            session_date=session, cbbo_rows=len(cbbo), cbbo_instruments=cbbo["instrument_id"].nunique(), definitions=len(defs), other_roots=other_roots,
            unmatched_quotes=unmatched, last_row_null_bids=last_row_null_bids(cbbo, day_q), flag_mode=int(cbbo["flags"].mode().iloc[0]) if len(cbbo) else -1,
            null_bid_share=float(cbbo["bid_px_00"].isna().mean()) if len(cbbo) else float("nan"),
            first_bar=times.min().strftime("%H:%M") if len(cbbo) else None, last_bar=times.max().strftime("%H:%M") if len(cbbo) else None,
            stock_mid=stock_mid, stock_age=float(stock["age"].iloc[-1]) if has_stock else float("nan")))
        if progress and count % 100 == 0:
            print(f"{count} sessions, {clock.time() - started:.0f}s", flush=True)
    return pd.concat(snapshots, ignore_index=True), pd.concat(listed, ignore_index=True), pd.DataFrame(diagnostics)


def main() -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    fetch_rates()
    snapshot, listed, diagnostics = snapshot_tables(DEVELOPMENT_START, DATA_END)
    snapshot.to_parquet(DATA / "option_snapshot_1545.parquet", index=False)
    listed.to_parquet(DATA / "option_listed.parquet", index=False)
    diagnostics.to_parquet(DATA / "session_diagnostics.parquet", index=False)
    print(f"done: {len(diagnostics)} sessions")


if __name__ == "__main__":
    main()
