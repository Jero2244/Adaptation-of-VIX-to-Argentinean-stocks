"""Check for F16 (called 'contract_multiplier' in the task text): what the OPRA definitions say about the deliverable, against config.CONTRACT_MULTIPLIER = 100.

Assert-style: if a definition row carries a DEFINED multiplier, it must equal 100, or the script fails. If the field is the undefined sentinel
(INT_MAX), the script reports that the standard 100-share deliverable CANNOT be verified from this file. It does not reopen the GGAL1 question.
Reads definitions on open dates only (rawio refuses earlier dates). DEVELOPMENT work. Writes only to stdout.
"""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "audit"))
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

import config  # noqa: E402
from rawio import parse_osi, read_day  # noqa: E402

DAYS = ["2018-05-01", "2018-12-24", "2019-08-12", "2020-03-16", "2021-06-15", "2022-07-08", "2023-05-30", "2024-06-18", "2025-01-21", "2025-01-22", "2025-06-02", "2026-09-15"]
INT_MAX = 2 ** 31 - 1

print("config.CONTRACT_MULTIPLIER =", config.CONTRACT_MULTIPLIER)
assert config.CONTRACT_MULTIPLIER == 100
undefined_days, defined_bad = [], []
for day in DAYS:
    d = read_day("defs", day)
    d = d.drop_duplicates("instrument_id", keep="last")
    roots = d.raw_symbol.map(lambda s: parse_osi(s)[0])
    g = d[roots == "GGAL"]
    cols = [c for c in ("contract_multiplier", "unit_of_measure_qty", "min_price_increment", "security_type") if c in g.columns]
    mult = g["contract_multiplier"] if "contract_multiplier" in g.columns else pd.Series(dtype=float)
    defined = mult[(mult != INT_MAX) & mult.notna() & (mult > 0)]
    print(day, "GGAL rows", len(g), "| other roots:", sorted(set(roots) - {"GGAL"}), "| multiplier values:", sorted(mult.dropna().unique().tolist())[:5],
          "| unit_of_measure_qty values:", sorted(g["unit_of_measure_qty"].dropna().unique().tolist())[:3] if "unit_of_measure_qty" in g.columns else "n/a")
    if len(defined):
        bad = defined[defined != config.CONTRACT_MULTIPLIER]
        if len(bad):
            defined_bad.append(day)
    else:
        undefined_days.append(day)
assert not defined_bad, f"A defined multiplier differs from {config.CONTRACT_MULTIPLIER} on {defined_bad}"
print()
print(f"Multiplier undefined (sentinel) on {len(undefined_days)} of {len(DAYS)} sample days; no defined value differs from 100.")
if len(undefined_days) == len(DAYS):
    print("RESULT: the 100-share deliverable is ASSUMED, not verified. The definitions cannot detect a non-standard deliverable (audit F16).")
diag = pd.read_parquet(ROOT / "data" / "session_diagnostics.parquet")
print("session_diagnostics.other_roots: sessions with any other root:", int((diag.other_roots > 0).sum()), "of", len(diag), "; max per session", int(diag.other_roots.max()))
