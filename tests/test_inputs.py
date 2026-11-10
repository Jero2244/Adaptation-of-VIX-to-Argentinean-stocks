import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import (EQUITY_OFFICIAL_DAILY, MARKER_PURPOSE, SCOPE_OPTIONS, SCOPE_OUTCOMES, VALUATION_PROJECT,
                    BlockedPeriod, load_cash_events, require_open)
from load_data import iter_days, member_day, parse_occ

DECODED_OFFICIAL = VALUATION_PROJECT / "research" / "adr" / "ggal_adr_decoded_v1" / "equity_official_daily.parquet"


class DateGate(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.marker = Path(self.folder.name) / "marker.json"

    def test_backward_test_is_blocked_without_marker(self):
        with self.assertRaises(BlockedPeriod):
            require_open("2017-01-03", "2017-01-04", self.marker)

    def test_range_that_starts_in_the_backward_test_is_blocked(self):
        with self.assertRaises(BlockedPeriod):
            require_open("2018-04-30", "2018-05-02", self.marker)

    def write_marker(self, scope=SCOPE_OUTCOMES, **changes):
        self.marker.write_text(json.dumps(dict(dict(purpose=MARKER_PURPOSE, scope=scope, approved_by="user", approved_on="2026-11-04"), **changes)))

    def test_valid_marker_opens_backward_test(self):
        self.write_marker()
        require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OUTCOMES)

    def test_no_marker_argument_stays_blocked(self):
        with self.assertRaises(BlockedPeriod):
            require_open("2017-01-03", "2017-01-04")

    def test_empty_or_bad_marker_opens_nothing(self):
        for text in ("", "{}", "[]", "not json", '"outcomes"'):
            self.marker.write_text(text)
            with self.assertRaises(BlockedPeriod):
                require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OUTCOMES)

    def test_marker_needs_each_field(self):
        for changes in (dict(purpose="other"), dict(approved_by="agent"), dict(approved_on=""), dict(approved_on="YYYY-MM-DD")):
            self.write_marker(**changes)
            with self.assertRaises(BlockedPeriod):
                require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OUTCOMES)

    def test_options_marker_does_not_open_outcomes(self):
        self.write_marker(SCOPE_OPTIONS)
        require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OPTIONS)
        with self.assertRaises(BlockedPeriod):
            require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OUTCOMES)

    def test_outcomes_marker_does_not_open_options(self):
        self.write_marker(SCOPE_OUTCOMES)
        with self.assertRaises(BlockedPeriod):
            require_open("2017-01-03", "2017-01-04", self.marker, SCOPE_OPTIONS)

    def test_iter_days_gate_uses_the_marker_argument(self):
        with self.assertRaises(BlockedPeriod):
            next(iter_days(self.folder.name + "/absent.zip", "2017-01-03", "2017-01-04", marker=self.marker))

    def test_cash_events_are_gated_and_filtered(self):
        with self.assertRaises(BlockedPeriod):
            load_cash_events("2016-01-04", "2018-04-30")
        self.assertTrue((load_cash_events("2018-05-01", "2026-10-29")["ex_date"] >= "2018-05-01").all())

    def test_dropped_period_stays_blocked_with_marker(self):
        self.write_marker()
        with self.assertRaises(BlockedPeriod):
            require_open("2015-12-31", "2016-01-04", self.marker, SCOPE_OUTCOMES)

    def test_development_and_2026_are_open(self):
        require_open("2018-05-01", "2026-10-29", self.marker)

    def test_after_data_end_is_blocked(self):
        with self.assertRaises(BlockedPeriod):
            require_open("2026-10-29", "2026-10-30", self.marker)


class Parsing(unittest.TestCase):
    def test_parse_occ(self):
        self.assertEqual(parse_occ("GGAL  260116P00020000"), ("GGAL", date(2026, 1, 16), "P", 20.0))

    def test_member_day(self):
        self.assertEqual(member_day("opra-pillar-20240603.cbbo-1m.dbn.zst"), date(2024, 6, 3))
        self.assertIsNone(member_day("xnas-itch-20180501-20261029.ohlcv-1d.dbn.zst"))


class BuiltInputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = load_cash_events("2018-05-01", "2026-10-29")  # Open dates only, through the gate.
        cls.official = pd.read_parquet(EQUITY_OFFICIAL_DAILY)

    def test_official_table_covers_every_session(self):
        self.assertEqual(len(self.official), 2137)
        self.assertEqual(int(self.official["official_close_price"].isna().sum()), 0)

    def test_official_table_matches_decoded_table(self):
        decoded = pd.read_parquet(DECODED_OFFICIAL).sort_values("session_date").reset_index(drop=True)
        built = self.official.sort_values("session_date").reset_index(drop=True)
        self.assertTrue((pd.to_datetime(built["session_date"]) == pd.to_datetime(decoded["session_date"])).all())
        self.assertLess((built["official_close_price"] - decoded["official_close_price"]).abs().max(), 1e-9)

    def test_event_counts(self):
        self.assertEqual(self.events["kind"].value_counts().to_dict(), {"dividend": 31, "rights": 1})

    def test_one_dividend_for_each_local_dividend_by_year(self):
        local = pd.read_csv(VALUATION_PROJECT / "research" / "ggal_cash_dividends_2016_2026.csv", parse_dates=["ex_date"])
        local_years = local.loc[local["ex_date"] >= "2018-05-01", "ex_date"].dt.year.value_counts().sort_index()
        dividends = self.events[self.events["kind"] == "dividend"]
        ads_years = pd.to_datetime(dividends["ex_date"]).dt.year.value_counts().sort_index()
        self.assertEqual(local_years.to_dict(), ads_years.to_dict())

    def test_ex_dates_from_2018_05_are_sessions(self):
        sessions = set(pd.to_datetime(self.official["session_date"]))
        dates = pd.to_datetime(self.events["ex_date"])
        self.assertTrue(dates[dates >= "2018-05-01"].isin(sessions).all())


if __name__ == "__main__":
    unittest.main()
