"""Read Databento batch zips through the date gate, without unpacking them to disk.

Copied from options-valuation-model/adr/databento_store.py (data_members, member_day, read_member, session_date,
bar_date, parse_occ, official_daily). The original is not edited. The date filter in iter_days is new.

Instrument ids are not stable, so join on symbol and session date. read_member returns float prices, and null
prices arrive as NaN.
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import date
from pathlib import Path
from typing import Iterator

import databento as db
import pandas as pd

from config import ALPACA_BARS, EQUITY_OHLCV, SCOPE_OPTIONS, SCOPE_OUTCOMES, DataFault, require_open

NY = "America/New_York"
SIDECARS = {"condition.json", "metadata.json", "manifest.json"}
OPENING_PRICE = int(db.StatType.OPENING_PRICE)
CLOSE_PRICE = int(db.StatType.CLOSE_PRICE)
_MEMBER_DAY = re.compile(r"-[a-z]+-(\d{8})\.[a-z0-9-]+\.dbn\.zst$")


def data_members(zip_path: str | Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return sorted(name for name in archive.namelist() if name not in SIDECARS)


def member_day(name: str) -> date | None:
    """UTC day in a per-day member name, or None for a multi-day file."""
    match = _MEMBER_DAY.search(name)
    return None if match is None else date.fromisoformat(f"{match[1][:4]}-{match[1][4:6]}-{match[1][6:]}")


def read_member(archive: zipfile.ZipFile, name: str, map_symbols: bool = True) -> pd.DataFrame:
    frame = db.DBNStore.from_bytes(io.BytesIO(archive.read(name))).to_df(map_symbols=map_symbols)
    return frame.reset_index().drop(columns="rtype", errors="ignore")


def iter_days(zip_path: str | Path, start, end, map_symbols: bool = True, marker: Path | None = None, scope: str = SCOPE_OPTIONS) -> Iterator[tuple[date, pd.DataFrame]]:
    """Yield (day, frame) for per-day members from start to end. The date gate runs before any member is read."""
    first, last = require_open(start, end, marker, scope)
    with zipfile.ZipFile(zip_path) as archive:
        for name in sorted(n for n in archive.namelist() if n not in SIDECARS):
            day = member_day(name)
            if day is None:
                raise ValueError(f"{name} is not a per-day member")
            if first.date() <= day <= last.date():
                yield day, read_member(archive, name, map_symbols)


def day_conditions(zip_path: str | Path) -> dict[str, str]:
    """Databento's condition of each day (available, degraded, or missing), from the zip's condition.json."""
    with zipfile.ZipFile(zip_path) as archive:
        return {row["date"]: row["condition"] for row in json.loads(archive.read("condition.json"))}


def load_equity_ohlcv(start, end) -> pd.DataFrame:
    """Nasdaq daily bars. This is one multi-day file, so the date filter runs after the read and before the return."""
    first, last = require_open(start, end)
    with zipfile.ZipFile(EQUITY_OHLCV) as archive:
        members = [n for n in archive.namelist() if n not in SIDECARS]
        if len(members) != 1:
            raise ValueError(f"expected one ohlcv member, found {len(members)}")
        frame = read_member(archive, members[0])
    frame["bar_date"] = bar_date(frame["ts_event"])
    return frame[frame["bar_date"].between(first, last)].reset_index(drop=True)


def load_alpaca_closes(start, end, marker: Path | None = None, path: str | Path = ALPACA_BARS) -> pd.DataFrame:
    """Daily closes from the Alpaca file, by New York date, from start to end. No other code reads its closes.

    alpaca_layout.py parses the file and prints only its layout. freeze.py hashes it, and build_inputs.py copies it.

    The gate runs before the file opens. The file is one JSON document, so the parse holds all rows in memory, and the
    filter runs right after it. So the blindness comes from this code path, and it is not physical. Errors hold no values.
    """
    first, last = require_open(start, end, marker, SCOPE_OUTCOMES)
    try:
        bars = [bar for page in json.loads(Path(path).read_text(encoding="utf-8"))["pages"] for bar in page["bars"]["GGAL"]]
        stamps = pd.to_datetime(pd.Series([bar["t"] for bar in bars], dtype="object"), utc=True, format="ISO8601")
        closes = pd.Series([bar["c"] for bar in bars], dtype=float)
    except (KeyError, TypeError, ValueError):
        raise ValueError("The Alpaca file does not have the expected layout") from None
    days = stamps.dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()
    keep = days.between(first, last).to_numpy()
    frame = pd.DataFrame(dict(session_date=days[keep].to_numpy(), close=closes[keep].to_numpy()))
    del bars, stamps, closes, days, keep
    if frame.empty:
        raise DataFault("The Alpaca file has no bar in the requested dates")
    frame = frame.sort_values("session_date", kind="stable").reset_index(drop=True)
    if frame["session_date"].min() < first or frame["session_date"].max() > last:
        raise ValueError("A bar is outside the requested dates")
    repeated = frame["session_date"].duplicated(keep=False)
    if repeated.any():
        raise DataFault("The Alpaca file has two bars on one New York date", frame.loc[repeated, "session_date"].drop_duplicates())
    usable = frame["close"] > 0
    if not usable.all():
        raise DataFault("A close is missing or not positive", frame.loc[~usable, "session_date"])
    return frame


def session_date(ts: pd.Series) -> pd.Series:
    """New York calendar date of UTC timestamps, as naive datetime64 at midnight."""
    return ts.dt.tz_convert(NY).dt.tz_localize(None).dt.normalize()


def bar_date(ts_event: pd.Series) -> pd.Series:
    """Date of an ohlcv-1d bar. Its ts_event is midnight UTC of the bar's date."""
    return ts_event.dt.tz_convert("UTC").dt.tz_localize(None).dt.normalize()


def parse_occ(symbol: str) -> tuple[str, date, str, float]:
    """OSI option symbol -> root, expiry, right, strike."""
    if len(symbol) != 21:
        raise ValueError(f"not a 21-character OSI symbol: {symbol!r}")
    yymmdd = symbol[6:12]
    return symbol[:6].strip(), date(2000 + int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:])), symbol[12], int(symbol[13:]) / 1000


def official_daily(stats: pd.DataFrame) -> pd.DataFrame:
    """Official open and close per session from equity statistics. The last update of the day wins; updates are counted."""
    rows = stats[stats["stat_type"].isin([OPENING_PRICE, CLOSE_PRICE])].sort_values("ts_recv", kind="stable")
    grouped = rows.groupby(["session_date", "stat_type"]).agg(price=("price", "last"), quantity=("quantity", "last"), updates=("price", "size"))
    wide = grouped.unstack("stat_type")
    out = pd.DataFrame(index=wide.index)
    for code, label in [(OPENING_PRICE, "open"), (CLOSE_PRICE, "close")]:
        for field in ["price", "quantity", "updates"]:
            out[f"official_{label}_{field}"] = wide[(field, code)] if (field, code) in wide.columns else pd.NA
    return out.reset_index()
