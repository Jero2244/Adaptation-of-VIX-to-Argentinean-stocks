"""Stage 1 inputs: copy the source files, rebuild the official daily table, and build the ADS cash event table.

Run from this folder: conda run -n py4fi python build_inputs.py
The Alpaca bars are only copied here. They are read later through the date gate.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone

import pandas as pd

from config import (ADR_CASH_EVENTS, DATA, DATA_END, DEVELOPMENT_START, EQUITY_OFFICIAL_DAILY, EQUITY_STATISTICS, SOURCE,
                    VALUATION_PROJECT)
from load_data import iter_days, official_daily, session_date

ADR = VALUATION_PROJECT / "research" / "adr"
STOCK_CHECK = VALUATION_PROJECT / "research" / "stock_history_check_20260915"
COPIES = {
    "adr_dividend_ledger.csv": ADR / "dividend_ledger_v1" / "adr_dividend_ledger.csv",
    "rights_valuation.json": ADR / "rights_2025_adr_evidence" / "rights_valuation.json",
    "ggal_cash_dividends_2016_2026.csv": VALUATION_PROJECT / "research" / "ggal_cash_dividends_2016_2026.csv",
    "alpaca_corporate_actions.json": STOCK_CHECK / "alpaca_corporate_actions.json",
    "alpaca_ggal_sip_raw.json": STOCK_CHECK / "alpaca_ggal_sip_raw.json",
}
# Before the ledger starts, the Alpaca list is the only source with USD per ADS and ADS ex-dates.
PRE_LEDGER_EX_DATES = ["2016-05-19", "2017-05-10"]
# Alpaca also lists USD 0.000413 on 2017-09-26. No local dividend matches it, so it is left out.
EXCLUDED_ALPACA_EX_DATES = {"2017-09-26": "no matching local dividend; amount USD 0.000413"}


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def alpaca_actions(name: str) -> pd.DataFrame:
    payload = json.loads((SOURCE / "alpaca_corporate_actions.json").read_text())
    rows = [row for page in payload["pages"] for row in page["corporate_actions"].get(name, [])]
    return pd.DataFrame(rows)


def build_cash_events() -> pd.DataFrame:
    ledger = pd.read_csv(SOURCE / "adr_dividend_ledger.csv")
    from_ledger = pd.DataFrame({"ex_date": ledger["ads_ex_date"], "kind": "dividend", "usd_per_ads": ledger["cash_usd_per_ads"],
                                "source": "adr_dividend_ledger", "basis": ledger["cash_usd_basis"], "date_status": "ledger"})
    alpaca = alpaca_actions("cash_dividends")
    early = alpaca[alpaca["ex_date"].isin(PRE_LEDGER_EX_DATES)]
    if len(early) != len(PRE_LEDGER_EX_DATES):
        raise ValueError("A pre-ledger dividend is missing from the Alpaca list")
    from_alpaca = pd.DataFrame({"ex_date": early["ex_date"], "kind": "dividend", "usd_per_ads": early["rate"], "source": "alpaca_corporate_actions",
                                "basis": "vendor_rate_unconfirmed", "date_status": "vendor date, no record date"})
    rights = json.loads((SOURCE / "rights_valuation.json").read_text())
    published = alpaca_actions("rights_distributions")
    if published["ex_date"].tolist() != [rights["ex_date"]]:
        raise ValueError("The rights ex-date differs between the valuation record and Alpaca")
    from_rights = pd.DataFrame([{"ex_date": rights["ex_date"], "kind": "rights", "usd_per_ads": rights["value_usd_per_ads"], "source": "rights_valuation",
                                 "basis": "theoretical_value", "date_status": "Alpaca ex_date agrees with the T+1 inference"}])
    events = pd.concat([from_alpaca, from_ledger, from_rights], ignore_index=True).sort_values("ex_date", kind="stable").reset_index(drop=True)
    if events["ex_date"].duplicated().any() or (events["usd_per_ads"] <= 0).any():
        raise ValueError("The cash event table has a duplicate date or a non-positive amount")
    return events


def build_official() -> pd.DataFrame:
    frames = []
    for _, frame in iter_days(EQUITY_STATISTICS, DEVELOPMENT_START, DATA_END):
        frame["session_date"] = session_date(frame["ts_recv"])
        frames.append(frame)
    return official_daily(pd.concat(frames, ignore_index=True))


def main() -> None:
    SOURCE.mkdir(parents=True, exist_ok=True)
    for name, path in COPIES.items():
        shutil.copy2(path, SOURCE / name)

    events = build_cash_events()
    events.to_csv(ADR_CASH_EVENTS, index=False)

    official = build_official()
    official.to_parquet(EQUITY_OFFICIAL_DAILY, index=False)

    (DATA / "input_manifest.json").write_text(json.dumps({
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "copies": {name: {"from": str(path), "sha256": sha256(SOURCE / name)} for name, path in COPIES.items()},
        "outputs": {path.name: {"rows": rows, "sha256": sha256(path)}
                    for path, rows in [(ADR_CASH_EVENTS, len(events)), (EQUITY_OFFICIAL_DAILY, len(official))]},
        "excluded_alpaca_ex_dates": EXCLUDED_ALPACA_EX_DATES,
    }, indent=2))
    print(f"cash events {len(events)}, official sessions {len(official)}")


if __name__ == "__main__":
    main()
