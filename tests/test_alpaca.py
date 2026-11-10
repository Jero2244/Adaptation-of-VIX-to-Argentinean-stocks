import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import compare_alpaca as ca
import realized as rz
from alpaca_layout import layout
from config import MARKER_PURPOSE, SCOPE_OPTIONS, SCOPE_OUTCOMES, BlockedPeriod, DataFault
from load_data import load_alpaca_closes

SECRET_PRICE = 123.456


def bar(stamp: str, close: float = 10.0) -> dict:
    return dict(c=close, h=close, l=close, n=1, o=close, t=stamp, v=1, vw=close)


def write_file(path: Path, bars: list[dict]) -> None:
    path.write_text(json.dumps(dict(path="p", params=dict(start="s"), pages=[dict(bars=dict(GGAL=bars), next_page_token=None)], retrieved_at="r")))


class Reader(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "bars.json"
        self.marker = Path(self.folder.name) / "marker.json"
        write_file(self.path, [
            bar("2017-03-01T05:00:00Z", SECRET_PRICE),
            bar("2018-04-30T04:00:00Z", 11.0),
            # 23:30 New York on 2018-04-30: a late UTC stamp on the next UTC day. This bar is in the locked period.
            bar("2018-05-01T03:30:00Z", 12.0),
            bar("2018-05-02T04:00:00Z", 13.0),
            bar("2018-05-03T04:00:00Z", 14.0),
        ])

    def open_marker(self, scope=SCOPE_OUTCOMES):
        self.marker.write_text(json.dumps(dict(purpose=MARKER_PURPOSE, scope=scope, approved_by="user", approved_on="2026-11-04")))

    def test_locked_dates_need_the_marker_before_the_file_opens(self):
        with self.assertRaises(BlockedPeriod):
            load_alpaca_closes("2017-01-01", "2018-04-30", self.marker, Path(self.folder.name) / "absent.json")

    def test_options_marker_does_not_open_the_closes(self):
        self.open_marker(SCOPE_OPTIONS)
        with self.assertRaises(BlockedPeriod):
            load_alpaca_closes("2017-01-01", "2018-04-30", self.marker, self.path)

    def test_open_read_drops_locked_rows_by_new_york_date(self):
        frame = load_alpaca_closes("2018-05-01", "2018-05-31", path=self.path)
        self.assertEqual(frame["session_date"].dt.strftime("%Y-%m-%d").tolist(), ["2018-05-02", "2018-05-03"])
        self.assertNotIn(12.0, frame["close"].tolist())
        self.assertNotIn(SECRET_PRICE, frame["close"].tolist())

    def test_locked_read_with_marker_keeps_the_boundary_bar(self):
        self.open_marker()
        with self.assertRaises(ValueError):
            # Two bars fall on New York 2018-04-30 in this file, and the reader refuses duplicates.
            load_alpaca_closes("2016-01-04", "2018-04-30", self.marker, self.path)

    def test_boundary_bar_belongs_to_the_locked_side(self):
        write_file(self.path, [bar("2017-03-01T05:00:00Z", SECRET_PRICE), bar("2018-05-01T03:30:00Z", 12.0), bar("2018-05-02T04:00:00Z", 13.0)])
        self.open_marker()
        frame = load_alpaca_closes("2016-01-04", "2018-04-30", self.marker, self.path)
        self.assertEqual(frame["close"].tolist(), [SECRET_PRICE, 12.0])
        self.assertEqual(frame["session_date"].iloc[-1], pd.Timestamp("2018-04-30"))

    def test_zero_negative_or_null_close_is_a_data_fault_with_its_date(self):
        for close in (0.0, -1.0, None):
            with self.subTest(close=close):
                write_file(self.path, [bar("2018-05-01T04:00:00Z"), bar("2018-05-02T04:00:00Z", close)])
                with self.assertRaises(DataFault) as caught:
                    load_alpaca_closes("2018-05-01", "2018-05-31", path=self.path)
                self.assertEqual([str(pd.Timestamp(day).date()) for day in caught.exception.dates], ["2018-05-02"])

    def test_errors_hold_no_values(self):
        write_file(self.path, [dict(c=SECRET_PRICE, t="not a date 123.456")])
        with self.assertRaises(ValueError) as caught:
            load_alpaca_closes("2018-05-01", "2018-05-31", path=self.path)
        self.assertNotIn("123.456", str(caught.exception))

    def test_layout_shows_no_values(self):
        text = layout(self.path)
        self.assertNotIn("123.456", text)
        self.assertNotIn("2017", text)
        self.assertIn("list with 5 items", text)

    def test_layout_masks_a_date_key(self):
        self.path.write_text(json.dumps({"2017-03-01": SECRET_PRICE}))
        text = layout(self.path)
        self.assertNotIn("2017", text)
        self.assertIn("1 masked", text)


def sessions(n=400, seed=5):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2018-05-01", periods=n)
    return pd.DataFrame(dict(session_date=dates, close=50 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))))


NO_EVENTS = pd.DataFrame(dict(ex_date=pd.to_datetime([]), kind=[], usd_per_ads=[]))


class Comparison(unittest.TestCase):
    def setUp(self):
        self.official = sessions()
        rng = np.random.default_rng(9)
        self.series = pd.DataFrame(dict(session_date=self.official["session_date"], atm30=0.6 * np.exp(rng.normal(0, 0.2, len(self.official)))))

    def test_identical_sources_pass_every_limit(self):
        table, counts = ca.comparison(self.official.copy(), self.official, self.series, NO_EVENTS)
        self.assertTrue(table["passed"].all())
        self.assertEqual(counts["only_alpaca"], [])

    def test_adjusted_series_fails_b2(self):
        adjusted = self.official.assign(close=self.official["close"] * 0.99)
        table, _ = ca.comparison(adjusted, self.official, self.series, NO_EVENTS)
        self.assertFalse(table.loc[table["id"] == "B2", "passed"].all())

    def test_missing_sessions_fail_b1(self):
        missing = self.official.drop(index=[10, 20, 30, 40]).reset_index(drop=True)
        table, counts = ca.comparison(missing, self.official, self.series, NO_EVENTS)
        self.assertFalse(table.loc[table["id"] == "B1", "passed"].all())
        self.assertEqual(len(counts["only_official"]), 4)

    def test_close_only_returns_match_the_standard_path(self):
        frame = rz.realized_from_closes(self.official, NO_EVENTS)
        standard = rz.trailing_realized(rz.forward_realized(rz.total_returns(self.official.assign(open=self.official["close"], dividend_cash=0.0, rights_cash=0.0))))
        np.testing.assert_allclose(frame["rv30"], standard["rv30"], equal_nan=True)
        np.testing.assert_allclose(frame["log_rv22"], standard["log_rv22"], equal_nan=True)


if __name__ == "__main__":
    unittest.main()
