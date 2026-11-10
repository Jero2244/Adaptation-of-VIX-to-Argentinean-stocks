"""Paths and the one date gate of the study. See PROTOCOL.md for the rules."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "databento_ggal_20261031"
DATA = ROOT / "data"
SOURCE = DATA / "source"
REPORTS = ROOT / "reports"
VALUATION_PROJECT = ROOT.parent / "options-valuation-model"

OPTION_CBBO = ARCHIVE / "options" / "OPRA-cbbo_1m.zip"
OPTION_DEFINITIONS = ARCHIVE / "options" / "OPRA-Definition.zip"
OPTION_STATISTICS = ARCHIVE / "options" / "OPRA-Statistics.zip"
EQUITY_OHLCV = ARCHIVE / "equity" / "XNAS-ohlc.zip"
EQUITY_BBO = ARCHIVE / "equity" / "XNAS-bbo.zip"
EQUITY_STATISTICS = ARCHIVE / "equity" / "XNAS-statistics.zip"

EQUITY_OFFICIAL_DAILY = DATA / "equity_official_daily.parquet"
ADR_CASH_EVENTS = DATA / "adr_cash_events.csv"
ALPACA_BARS = SOURCE / "alpaca_ggal_sip_raw.json"

OPTION_ROOT = "GGAL"  # User decision 2026-11-03: use the Databento GGAL root as given.
CONTRACT_MULTIPLIER = 100  # OPRA leaves the field undefined.

STUDY_START = pd.Timestamp("2016-01-01")
DEVELOPMENT_START = pd.Timestamp("2018-05-01")
TEST_END = pd.Timestamp("2018-04-30")
DATA_END = pd.Timestamp("2026-10-29")  # 2026 is open in this study (user decision 2026-11-03).

# Step A of the one-time test reads options. Step B reads outcomes. Each step has its own marker, and only the user approves one.
OPTIONS_MARKER = REPORTS / "backward_test_options_unlocked.json"
OUTCOMES_MARKER = REPORTS / "backward_test_outcomes_unlocked.json"
SCOPE_OPTIONS = "options"
SCOPE_OUTCOMES = "outcomes"
MARKER_PURPOSE = "stage5_one_time_test"
RUN_RECORD = REPORTS / "backward_test_run.json"
RESULT = REPORTS / "stage5_result.json"


class BlockedPeriod(ValueError):
    """A read touches dates that the date gate blocks."""


class DataFault(ValueError):
    """The closes or the cash rows have a fault in the data. The message holds no value, and the dates of the faulty rows stay in an attribute."""

    def __init__(self, message: str, dates=()):
        super().__init__(message)
        self.dates = list(dates)


def marker_opens(marker: Path | None, scope: str) -> bool:
    """A marker opens a scope only if it holds the purpose, that scope, and a record of the user's approval. An empty file opens nothing."""
    if marker is None or not Path(marker).is_file():
        return False
    try:
        content = json.loads(Path(marker).read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return False
    if not isinstance(content, dict):
        return False
    try:
        date.fromisoformat(str(content.get("approved_on")))
    except ValueError:
        return False
    return content.get("purpose") == MARKER_PURPOSE and content.get("scope") == scope and content.get("approved_by") == "user"


def require_open(start, end, marker: Path | None = None, scope: str = SCOPE_OUTCOMES) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return the dates if a read may touch them. Dates before 2018-05 need a valid marker for the scope of the read."""
    first, last = pd.Timestamp(start), pd.Timestamp(end)
    if first > last:
        raise ValueError(f"start {first.date()} is after end {last.date()}")
    if first < STUDY_START:
        raise BlockedPeriod(f"{first.date()} is before the study start. The plan drops 2013-2015.")
    if last > DATA_END:
        raise BlockedPeriod(f"{last.date()} is after the last data day {DATA_END.date()}.")
    if first < DEVELOPMENT_START and not marker_opens(marker, scope):
        raise BlockedPeriod(f"{first.date()} is in the 2016-01 to 2018-04 one-time test, which is locked for {scope}.")
    return first, last


def load_cash_events(start, end, marker: Path | None = None) -> pd.DataFrame:
    """Cash events with an ex-date from start to end. Cash is part of the outcome, so a locked date needs the outcomes marker."""
    first, last = require_open(start, end, marker, SCOPE_OUTCOMES)
    events = pd.read_csv(ADR_CASH_EVENTS, parse_dates=["ex_date"])
    return events[events["ex_date"].between(first, last)].reset_index(drop=True)
