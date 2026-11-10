"""Audit step 1: what do the raw cbbo-1m and bbo-1m records look like? Open dates only."""
import sys

import numpy as np
import pandas as pd

from rawio import parse_osi, read_day

pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 200)
NY = "America/New_York"

for day in sys.argv[1:] or ["2019-08-09", "2022-03-15", "2024-06-03", "2025-06-02", "2026-09-15"]:
    q = read_day("cbbo", day)
    d = read_day("defs", day)
    print(f"\n================ {day}: cbbo rows {len(q)}, cols {list(q.columns)}")
    print(q.head(3).to_string())
    print("defs cols", list(d.columns)[:60])
    t = q["ts_recv"].dt.tz_convert(NY)
    print("ts_recv range", t.min(), t.max())
    if "ts_event" in q:
        te = q["ts_event"]
        print("ts_event null share", te.isna().mean())
        lag = (q["ts_recv"] - te).dt.total_seconds()
        print("ts_recv - ts_event seconds:", lag.describe().to_string())
    per = q.groupby("instrument_id").size()
    print("rows per instrument:", per.describe().to_string())
    print("seconds part of ts_recv:", t.dt.second.value_counts().head(3).to_dict())
    print("flags:", q["flags"].value_counts().head(5).to_dict())
    print("bid null", q["bid_px_00"].isna().mean(), "ask null", q["ask_px_00"].isna().mean())
    both = q.dropna(subset=["bid_px_00", "ask_px_00"])
    print("crossed share", (both.bid_px_00 > both.ask_px_00).mean(), "locked share", (both.bid_px_00 == both.ask_px_00).mean(), "zero bid share", (both.bid_px_00 == 0).mean())
    print("max price", both.ask_px_00.max(), "min ask", both.ask_px_00.min())
    # does the quote change between minutes? share of minute rows identical to the previous row of the same instrument
    s = q.sort_values(["instrument_id", "ts_recv"])
    same = (s.groupby("instrument_id")[["bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"]].diff().abs().sum(axis=1) == 0)
    print("share of rows equal to previous minute (px and size):", float(same.mean()))
    # definition fields of interest
    d = d.sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    for col in ["contract_multiplier", "unit_of_measure_qty", "underlying", "exercise_style", "security_type", "instrument_class", "min_price_increment", "strike_price_currency", "expiration"]:
        if col in d:
            vc = d[col].astype(str).value_counts().head(4).to_dict()
            print(f"  def {col}: {vc}")
    roots = d["raw_symbol"].map(lambda x: parse_osi(x)[0]).value_counts().to_dict()
    print("  roots:", roots)
    exps = sorted(set(d["raw_symbol"].map(lambda x: parse_osi(x)[1].date())))
    print("  expiries:", [str(e) for e in exps])
    # expiration time in definitions vs study's 16:00 NY
    if "expiration" in d:
        ex = pd.to_datetime(d["expiration"], utc=True).dt.tz_convert(NY)
        print("  def expiration local times:", ex.dt.strftime("%a %H:%M").value_counts().head(4).to_dict())
    e = read_day("eq", day)
    te = e["ts_recv"].dt.tz_convert(NY)
    print("equity bbo rows", len(e), "range", te.min(), te.max(), "instrument ids", e["instrument_id"].nunique(), "cols", list(e.columns))
    w = e[(te >= pd.Timestamp(f"{day} 15:40", tz=NY)) & (te <= pd.Timestamp(f"{day} 15:46", tz=NY))]
    print(w[["ts_recv", "ts_event", "bid_px_00", "ask_px_00", "price"]].assign(ts_recv=w.ts_recv.dt.tz_convert(NY)).to_string() if "price" in w else w.to_string())
