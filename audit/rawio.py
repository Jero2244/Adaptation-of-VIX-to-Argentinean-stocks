"""Audit helper: read one day of a Databento batch zip. Independent of the study's load_data.py. Open dates only (>= 2018-05-01)."""
import io
import zipfile
from pathlib import Path

import databento as db
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARCH = ROOT / "databento_ggal_20261031"
ZIPS = {"cbbo": ARCH / "options" / "OPRA-cbbo_1m.zip", "defs": ARCH / "options" / "OPRA-Definition.zip", "eq": ARCH / "equity" / "XNAS-bbo.zip",
        "eqstat": ARCH / "equity" / "XNAS-statistics.zip", "tcbbo": ARCH / "options" / "OPRA-TCBBO.zip", "ohlc": ARCH / "equity" / "XNAS-ohlc.zip"}
_cache = {}


def _names(kind):
    if kind not in _cache:
        with zipfile.ZipFile(ZIPS[kind]) as z:
            _cache[kind] = z.namelist()
    return _cache[kind]


def read_day(kind: str, day: str) -> pd.DataFrame:
    if pd.Timestamp(day) < pd.Timestamp("2018-05-01"):
        raise ValueError("The audit reads open dates only")
    tag = "-" + day.replace("-", "") + "."
    hits = [n for n in _names(kind) if tag in n and n.endswith(".dbn.zst")]
    if len(hits) != 1:
        raise ValueError(f"{kind} {day}: {len(hits)} members")
    with zipfile.ZipFile(ZIPS[kind]) as z:
        store = db.DBNStore.from_bytes(io.BytesIO(z.read(hits[0])))
    return store.to_df(map_symbols=False).reset_index()


def parse_osi(sym: str):
    root = sym[:6].strip()
    exp = pd.Timestamp("20" + sym[6:12])
    return root, exp, sym[12], int(sym[13:21]) / 1000.0
