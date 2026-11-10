"""Unit tests of the calibration code. Run from the project folder: conda run -n py4fi python -m unittest calibration/test_calib.py"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import integrate, stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_core as cc  # noqa: E402


def frame_from(dates, returns=None, atm=0.5, half=None):
    dates = pd.DatetimeIndex(dates)
    returns = np.zeros(len(dates)) if returns is None else np.asarray(returns, dtype=float)
    returns = returns.copy()
    returns[0] = np.nan
    return pd.DataFrame({"position": np.arange(len(dates)), "session_date": dates, "return_total": returns, "atm30": atm, "flag_half_day": False if half is None else half})


class Outcome(unittest.TestCase):
    def test_window_end_on_a_non_session_day(self):
        # 2021-02-05 + 30 days is Sunday 2021-03-07, so the window ends on Friday 2021-03-05.
        dates = pd.bdate_range("2021-01-04", periods=70)
        returns = np.full(len(dates), 0.01)
        got = cc.outcome_returns(frame_from(dates, returns))
        where = list(dates).index(pd.Timestamp("2021-02-05"))
        self.assertEqual(got["outcome_end"].iloc[where], pd.Timestamp("2021-03-05"))
        self.assertEqual(got["outcome_sessions"].iloc[where], 20)
        self.assertAlmostEqual(got["R"].iloc[where], 0.20)

    def test_window_includes_a_session_on_the_exact_end_date(self):
        dates = pd.bdate_range("2021-01-04", periods=70)
        got = cc.outcome_returns(frame_from(dates))
        where = list(dates).index(pd.Timestamp("2021-02-01"))  # 30 days later is Wednesday 2021-03-03.
        self.assertEqual(got["outcome_end"].iloc[where], pd.Timestamp("2021-03-03"))

    def test_cash_on_the_ex_date_counts_once(self):
        import realized as rz
        dates = pd.bdate_range("2021-01-04", periods=60)
        closes = np.full(len(dates), 100.0)
        closes[30:] = 98.0
        events = pd.DataFrame({"ex_date": [dates[30]], "kind": ["dividend"], "usd_per_ads": [2.0]})
        panel = rz.realized_from_closes(pd.DataFrame({"session_date": dates, "close": closes}), events)
        got = cc.outcome_returns(panel)["R"].to_numpy()
        self.assertAlmostEqual(got[29], 0.0)  # The stock falls by the cash, so the total return is zero.
        self.assertAlmostEqual(got[30], 0.0)
        self.assertAlmostEqual(np.nansum(panel["return_total"].to_numpy()), 0.0)

    def test_no_imputation_of_a_blank_return(self):
        dates = pd.bdate_range("2021-01-04", periods=60)
        returns = np.zeros(len(dates))
        returns[10] = np.nan
        with self.assertRaises(ValueError):
            cc.outcome_returns(frame_from(dates, returns))

    def test_open_window_stays_blank(self):
        dates = pd.bdate_range("2021-01-04", periods=60)
        got = cc.outcome_returns(frame_from(dates))["R"].to_numpy()
        self.assertTrue(np.isnan(got[-1]))
        self.assertTrue(np.isfinite(got[0]))

    def test_alignment_check_passes_the_real_builder(self):
        self.assertEqual(cc.alignment_failures(), [])

    def test_alignment_check_catches_a_one_session_shift(self):
        def later(frame):
            out = cc.outcome_returns(frame)
            out["R"] = out["R"].shift(-1)
            return out

        def earlier(frame):
            out = cc.outcome_returns(frame)
            out["R"] = out["R"].shift(1)
            return out

        self.assertTrue(cc.alignment_failures(later))
        self.assertTrue(cc.alignment_failures(earlier))


class Standardize(unittest.TestCase):
    def test_formula(self):
        dates = pd.bdate_range("2021-01-04", periods=60)
        returns = np.full(len(dates), 0.01)
        frame = cc.build_calibration(frame_from(dates, returns, atm=0.6), np.full(len(dates), 0.02))
        s = 0.6 * np.sqrt(30 / 365)
        m = 0.02 * 30 / 365 - s ** 2 / 2
        expected = (frame["R"].iloc[0] - m) / s
        self.assertAlmostEqual(frame["z"].iloc[0], expected)

    def test_half_day_has_no_value(self):
        dates = pd.bdate_range("2021-01-04", periods=60)
        half = np.zeros(len(dates), dtype=bool)
        half[3] = True
        frame = cc.build_calibration(frame_from(dates, atm=0.6, half=half), np.zeros(len(dates)))
        self.assertTrue(np.isnan(frame["z"].iloc[3]))
        self.assertTrue(np.isfinite(frame["z"].iloc[4]))

    def test_blank_atm_and_rate_stay_blank(self):
        dates = pd.bdate_range("2021-01-04", periods=60)
        atm = np.full(len(dates), 0.6)
        atm[2] = np.nan
        r = np.zeros(len(dates))
        r[5] = np.nan
        frame = cc.build_calibration(frame_from(dates, atm=atm), r)
        self.assertFalse(frame["valid"].iloc[2])
        self.assertFalse(frame["valid"].iloc[5])
        self.assertTrue(frame["valid"].iloc[6])

    def test_measures(self):
        got = cc.measures_from_z(np.array([0.5, -1.5, 2.5, -3.0]))
        np.testing.assert_allclose(got, [0.25, 0.5, 0.25, 0.25, (0.25 + 2.25 + 6.25 + 9) / 4, 7.5 / 4])

    def test_hit_is_strict_at_the_edge(self):
        self.assertEqual(cc.measures_from_z(np.array([1.0]))[0], 0.0)


class Scores(unittest.TestCase):
    def numeric_crps(self, cdf, y):
        below = integrate.quad(lambda x: cdf(x) ** 2, -np.inf, y, limit=400)[0]
        above = integrate.quad(lambda x: (1 - cdf(x)) ** 2, y, np.inf, limit=400)[0]
        return below + above

    def test_normal_crps_matches_the_integral(self):
        for y in (-1.0, 0.1, 2.0):
            exact = self.numeric_crps(lambda x: stats.norm.cdf(x, 0.1, 0.5), y)
            self.assertAlmostEqual(float(cc.normal_crps(y, 0.1, 0.5)), exact, places=6)

    def test_t_crps_matches_the_integral(self):
        for nu in (2.5, 4.0, 30.0):
            for y in (-1.0, 0.1, 2.0):
                exact = self.numeric_crps(lambda x: stats.t.cdf((x - 0.1) / 0.5, nu), y)
                self.assertAlmostEqual(float(cc.t_crps(y, 0.1, 0.5, nu)), exact, places=5)

    def test_unit_t_has_unit_variance(self):
        for nu in (2.5, 4.0, 30.0):
            self.assertAlmostEqual(stats.t.var(nu) * cc.unit_t_scale(nu) ** 2, 1.0)

    def test_t_approaches_normal(self):
        t = cc.Predictive(np.array([0.0]), np.array([1.0]), np.array([1000.0]))
        n = cc.Predictive(np.array([0.0]), np.array([1.0]))
        self.assertAlmostEqual(float(t.half_width(cc.OUTER)[0]), float(n.half_width(cc.OUTER)[0]), places=2)

    def test_interval_score_by_hand(self):
        self.assertAlmostEqual(float(cc.interval_score(0.0, -1.0, 1.0, 0.5)), 2.0)
        self.assertAlmostEqual(float(cc.interval_score(2.0, -1.0, 1.0, 0.5)), 2.0 + 4.0)
        self.assertAlmostEqual(float(cc.interval_score(-3.0, -1.0, 1.0, 0.5)), 2.0 + 8.0)

    def test_normal_band_hits_the_primary_rule(self):
        s, r, R = np.array([0.1, 0.1]), np.array([0.0, 0.0]), np.array([0.095, -0.2])
        pred = cc.normal_band(r, s)
        z = (R - pred.loc) / s
        got = cc.hit_rows(pred, R)
        np.testing.assert_array_equal(got["inner"], np.abs(z) < 1)
        np.testing.assert_array_equal(got["outer"], np.abs(z) < 2)

    def test_move_probability(self):
        pred = cc.Predictive(np.array([0.0]), np.array([0.1]))
        expected = stats.norm.cdf(np.log(0.9) / 0.1) + 1 - stats.norm.cdf(np.log(1.1) / 0.1)
        self.assertAlmostEqual(float(pred.move_probability(0.1)[0]), expected)

    def test_move_happened_uses_simple_return(self):
        np.testing.assert_array_equal(cc.move_happened(np.log(np.array([1.11, 1.09, 0.89, 0.91])), 0.1), [True, False, True, False])


class PastRowsOnly(unittest.TestCase):
    def panel(self, seed=1, rows=600):
        rng = np.random.default_rng(seed)
        dates = pd.bdate_range("2015-01-05", periods=rows)
        frame = frame_from(dates, rng.normal(0, 0.03, rows), atm=0.6)
        return cc.build_calibration(frame, np.zeros(rows))

    def test_past_count_excludes_open_windows(self):
        frame = self.panel()
        ends = cc.past_end_positions(frame)
        dates = frame["session_date"].to_numpy()
        for origin in (300, 450):
            rows = ends[origin]
            self.assertLessEqual(dates[rows - 1] + np.timedelta64(30, "D"), dates[origin])
            self.assertGreater(dates[rows] + np.timedelta64(30, "D"), dates[origin])

    def test_scale_ignores_later_rows(self):
        frame = self.panel()
        base = cc.expanding_scale(frame)
        changed = frame.copy()
        ends = cc.past_end_positions(frame)
        origin = 400
        changed.loc[changed.index[ends[origin]:], "z"] = 99.0
        got = cc.expanding_scale(changed)
        self.assertEqual(base[origin], got[origin])
        self.assertNotEqual(base[origin + 40], got[origin + 40])

    def test_nu_ignores_later_rows(self):
        frame = self.panel()
        base = cc.expanding_nu(frame)
        changed = frame.copy()
        ends = cc.past_end_positions(frame)
        origin = 400
        changed.loc[changed.index[ends[origin]:], "z"] = 99.0
        self.assertEqual(base[origin], cc.expanding_nu(changed)[origin])

    def test_start_rules(self):
        frame = self.panel()
        k = cc.expanding_scale(frame)
        self.assertTrue(np.isnan(k[251]))
        self.assertTrue(np.isfinite(k[252]))

    def test_scale_recovers_a_known_level(self):
        rows = 1500
        rng = np.random.default_rng(3)
        dates = pd.bdate_range("2015-01-05", periods=rows)
        frame = cc.build_calibration(frame_from(dates, rng.normal(0, 0.02, rows), atm=0.02 * np.sqrt(365 / 30 * 21) * 1.5), np.zeros(rows))
        self.assertAlmostEqual(np.nanmedian(cc.expanding_scale(frame)[700:]), 1 / 1.5, delta=0.1)


class Forward(unittest.TestCase):
    def rows(self, size=504, hit=True):
        rng = np.random.default_rng(5)
        z = rng.normal(0, 0.3 if hit else 1, size)
        return z, np.arange(size)

    def test_refuses_without_a_horizon(self):
        z, positions = self.rows()
        with self.assertRaises(RuntimeError):
            cc.forward_verdict(z, positions, None, "2028-12-31", reps=50)

    def test_refuses_before_the_horizon(self):
        z, positions = self.rows()
        with self.assertRaises(RuntimeError):
            cc.forward_verdict(z, positions, "2028-10-29", "2028-01-01", reps=50)

    def test_verdict_rule(self):
        z, positions = self.rows()
        self.assertEqual(cc.forward_verdict(z, positions, "2028-10-29", "2028-10-29", reps=200)["verdict"], cc.MISCALIBRATED)
        z, positions = self.rows(hit=False)
        self.assertEqual(cc.forward_verdict(z, positions, "2028-10-29", "2028-10-29", reps=200)["verdict"], cc.NOT_SHOWN)

    def test_too_few_rows(self):
        z, positions = self.rows(size=100)
        self.assertEqual(cc.forward_verdict(z, positions, "2028-10-29", "2028-10-29", reps=50)["verdict"], cc.TOO_FEW)


class Reliability(unittest.TestCase):
    def test_groups_are_equal_count_and_ordered(self):
        p = np.linspace(0, 1, 100)
        rows = cc.reliability_groups(p, p > 0.5)
        self.assertEqual([row["n"] for row in rows], [20] * 5)
        self.assertLess(rows[0]["mean_probability"], rows[-1]["mean_probability"])


if __name__ == "__main__":
    unittest.main()
