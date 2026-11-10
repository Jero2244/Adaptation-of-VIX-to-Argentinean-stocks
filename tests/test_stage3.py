import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import events as ev
import forecasts as fc
import inference as inf
import realized as rz


def synthetic_sessions(n=60, seed=1):
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n)
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    return pd.DataFrame(dict(session_date=dates, open=close * (1 + rng.normal(0, 0.005, n)), close=close, dividend_cash=0.0, rights_cash=0.0))


def full_panel(frame):
    return rz.trailing_realized(rz.forward_realized(rz.total_returns(frame)))


class TotalReturn(unittest.TestCase):
    def test_ex_date_adds_the_dividend(self):
        frame = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=3), open=[100.0, 98.5, 99.0], close=[100.0, 98.0, 99.0], dividend_cash=[0.0, 2.0, 0.0], rights_cash=0.0))
        out = rz.total_returns(frame)
        self.assertAlmostEqual(out["return_total"].iloc[1], 0.0)
        self.assertAlmostEqual(out["return_price"].iloc[1], np.log(0.98))
        self.assertAlmostEqual(out["return_overnight"].iloc[1], np.log(100.5 / 100))
        self.assertAlmostEqual(out["return_total"].iloc[2], np.log(99 / 98))

    def test_rights_value_enters_on_its_ex_date(self):
        frame = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=2), open=[50.0, 45.0], close=[50.0, 46.0], dividend_cash=0.0, rights_cash=[0.0, 4.0]))
        self.assertAlmostEqual(rz.total_returns(frame)["return_total"].iloc[1], 0.0)

    def test_ex_date_on_a_non_session_stops_the_run(self):
        events = pd.DataFrame(dict(ex_date=pd.to_datetime(["2021-01-09"]), kind=["dividend"], usd_per_ads=[1.0]))
        with self.assertRaises(ValueError):
            rz.attach_cash(synthetic_sessions()[["session_date", "open", "close"]], events)

    def test_real_data_across_ex_date_and_rights_date(self):
        frame = rz.total_returns(rz.load_sessions()).set_index("session_date")
        self.assertEqual(int((frame["dividend_cash"] > 0).sum()), 31)
        rights = frame.loc["2025-01-21"]
        self.assertGreater(rights["rights_cash"], 0)
        previous = frame["close"].shift(1).loc["2025-01-21"]
        self.assertAlmostEqual(rights["return_total"], np.log((rights["close"] + rights["rights_cash"]) / previous))
        self.assertGreater(rights["return_total"], rights["return_price"])
        ex = frame[frame["dividend_cash"] > 0].index[5]
        self.assertGreater(frame.loc[ex, "return_total"], frame.loc[ex, "return_price"])
        quiet = frame[(frame["dividend_cash"] == 0) & (frame["rights_cash"] == 0)].iloc[1:]
        np.testing.assert_allclose(quiet["return_total"], quiet["return_price"])
        np.testing.assert_allclose(quiet["return_overnight"] + quiet["return_intraday"], quiet["return_total"], atol=1e-12)


class RealizedWindow(unittest.TestCase):
    def test_window_is_exact_and_excludes_the_origin(self):
        out = full_panel(synthetic_sessions())
        origin = 5
        end = out["session_date"].iloc[origin] + pd.Timedelta(days=30)
        chosen = out[(out["session_date"] > out["session_date"].iloc[origin]) & (out["session_date"] <= end)]
        self.assertAlmostEqual(out["rv30"].iloc[origin], (chosen["return_total"] ** 2).sum() * 365 / 30)
        self.assertEqual(out["window_sessions"].iloc[origin], len(chosen))

    def test_incomplete_window_is_blank(self):
        out = full_panel(synthetic_sessions())
        complete = out["session_date"] + pd.Timedelta(days=30) <= out["session_date"].iloc[-1]
        self.assertTrue(out.loc[complete, "rv30"].notna().all())
        self.assertTrue(out.loc[~complete, "rv30"].isna().all())

    def test_rv21_uses_the_next_21_sessions(self):
        out = full_panel(synthetic_sessions())
        expected = (out["return_total"].iloc[4:25] ** 2).sum() * 12
        self.assertAlmostEqual(out["rv21"].iloc[3], expected)
        self.assertTrue(np.isnan(out["rv21"].iloc[-21]))
        self.assertFalse(np.isnan(out["rv21"].iloc[-22]))

    def test_real_data_last_full_origin(self):
        out = rz.build_realized()
        self.assertEqual(out.loc[out["rv30"].notna(), "session_date"].max(), pd.Timestamp("2026-09-29"))

    def test_zero_return_uses_the_floor(self):
        frame = pd.DataFrame(dict(session_date=pd.bdate_range("2021-01-04", periods=3), open=[10.0, 10.0, 10.0], close=[10.0, 10.0, 11.0], dividend_cash=0.0, rights_cash=0.0))
        out = rz.trailing_realized(rz.total_returns(frame), floor=1e-6)
        self.assertAlmostEqual(out["log_rv1"].iloc[1], np.log(252 * 1e-6))


class NoLookAhead(unittest.TestCase):
    """No forecast input uses a return after the origin date."""

    @classmethod
    def setUpClass(cls):
        cls.base = synthetic_sessions(420, seed=3)
        cls.cut = 330
        changed = cls.base.copy()
        rng = np.random.default_rng(9)
        factors = np.exp(np.cumsum(rng.normal(0, 0.15, len(changed) - cls.cut - 1)))
        changed.loc[cls.cut + 1:, "close"] = changed.loc[cls.cut + 1:, "close"].to_numpy() * factors
        changed.loc[cls.cut + 1:, "open"] = changed.loc[cls.cut + 1:, "open"].to_numpy() * factors
        cls.changed = changed
        cls.panel_base, cls.panel_changed = full_panel(cls.base), full_panel(changed)

    def test_the_change_reaches_the_future(self):
        self.assertFalse(np.isclose(self.panel_base["return_total"].iloc[self.cut + 5], self.panel_changed["return_total"].iloc[self.cut + 5]))
        self.assertFalse(np.isclose(self.panel_base["rv30"].iloc[self.cut - 3], self.panel_changed["rv30"].iloc[self.cut - 3]))

    def test_trailing_inputs(self):
        for name in ("log_rv1", "log_rv5", "log_rv22"):
            np.testing.assert_array_equal(self.panel_base[name].iloc[:self.cut + 1], self.panel_changed[name].iloc[:self.cut + 1])

    def test_ewma(self):
        np.testing.assert_array_equal(rz_ewma(self.panel_base)[:self.cut + 1], rz_ewma(self.panel_changed)[:self.cut + 1])

    def test_garch(self):
        # Returns with volatility clustering, so that the fit has alpha above zero and the forecast reacts to new returns.
        rng = np.random.default_rng(5)
        returns, variance = np.full(420, np.nan), 4e-4
        for position in range(1, 420):
            returns[position] = np.sqrt(variance) * rng.normal()
            variance = 2e-5 + 0.15 * returns[position] ** 2 + 0.8 * variance
        changed = returns.copy()
        changed[self.cut + 1:] = rng.normal(0, 0.15, 420 - self.cut - 1)
        sessions = np.full(420, 21)
        one, fits = fc.garch_forecasts(returns, sessions, start=252)
        two = fc.garch_forecasts(changed, sessions, start=252)[0]
        self.assertGreater(fits["alpha"].iloc[0], 0.01)
        np.testing.assert_array_equal(one[:self.cut + 1], two[:self.cut + 1])
        self.assertTrue(np.isfinite(one[300]))
        self.assertFalse(np.isclose(one[self.cut + 5], two[self.cut + 5]))

    def test_garch_recursion_matches_a_hand_calculation(self):
        fit = dict(omega=0.1, alpha=0.1, beta=0.8, persistence=0.9, last_variance=4.0, fit_rows=300)
        original = fc.fit_garch
        fc.fit_garch = lambda fit_returns, dist: fit
        self.addCleanup(setattr, fc, "fit_garch", original)
        returns = np.r_[np.nan, np.full(9, 0.01), 0.02, 0.03]
        out = fc.garch_forecasts(returns, np.full(12, 2), start=11, refit=21)[0]
        # The fit gives h(10) = 4. The return at position 10 (2%) gives h(11) = .1 + .1 * 2^2 + .8 * 4 = 3.7.
        # The return at position 11 (3%) gives h(12) = .1 + .1 * 3^2 + .8 * 3.7 = 3.96, and h(13) = .1 + .9 * 3.96 = 3.664.
        h_next = 0.1 + 0.1 * 3 ** 2 + 0.8 * (0.1 + 0.1 * 2 ** 2 + 0.8 * 4.0)
        expected = (h_next + (0.1 + 0.9 * h_next)) / 100 ** 2 * 365 / 30
        self.assertAlmostEqual(out[11], expected)

    def test_expanding_regression_uses_only_mature_targets(self):
        forecast = []
        for panel in (self.panel_base, self.panel_changed):
            valid = panel[["log_rv1", "log_rv5", "log_rv22", "rv30"]].notna().all(axis=1).to_numpy()
            forecast.append(fc.expanding_forecasts(panel, ["log_rv1", "log_rv5", "log_rv22"], valid, valid, start=200, min_rows=100))
        np.testing.assert_array_equal(forecast[0][:self.cut + 1], forecast[1][:self.cut + 1])
        self.assertTrue(np.isfinite(forecast[0][self.cut]))

    def test_training_stops_when_the_target_is_not_mature(self):
        panel = self.panel_base.copy()
        valid = panel[["log_rv5", "rv30"]].notna().all(axis=1).to_numpy()
        origin = 300
        panel_cut = panel.copy()
        immature = panel["window_end"].to_numpy() > panel["session_date"].to_numpy()[origin]
        panel_cut.loc[immature, "rv30"] = 1e6
        one = fc.expanding_forecasts(panel, ["log_rv5"], valid, valid, start=origin, min_rows=100)[origin]
        two = fc.expanding_forecasts(panel_cut, ["log_rv5"], valid, valid, start=origin, min_rows=100)[origin]
        self.assertEqual(one, two)


def rz_ewma(panel):
    return fc.ewma_forecasts(panel["return_total"].to_numpy(), np.full(len(panel), 21))


class Forecasts(unittest.TestCase):
    def test_ewma_on_constant_returns(self):
        returns = np.r_[np.nan, np.full(50, 0.02)]
        self.assertAlmostEqual(fc.ewma_variance(returns)[-1], 0.0004)

    def test_horizon_total_at_the_fixed_point(self):
        fit = dict(omega=0.5, persistence=0.9)
        self.assertAlmostEqual(fc.horizon_total(fit, 5.0, 21), 21 * 5.0 / 10000)

    def test_qlike_is_zero_at_the_target_and_penalizes_a_low_forecast_more(self):
        self.assertAlmostEqual(float(fc.qlike(np.array([0.3]), np.array([0.3]))[0]), 0.0)
        self.assertGreater(float(fc.qlike(np.array([1.0]), np.array([0.5]))[0]), float(fc.qlike(np.array([1.0]), np.array([2.0]))[0]))

    def test_smearing_returns_the_level(self):
        rng = np.random.default_rng(2)
        noise = rng.normal(0, 0.5, 20000)
        design = np.ones((20000, 1))
        beta, smear = fc.fit_log_ols(design, noise)
        self.assertAlmostEqual(float(np.exp(beta[0]) * smear), float(np.mean(np.exp(noise))), places=8)


class Inference(unittest.TestCase):
    def test_ols_recovers_coefficients(self):
        rng = np.random.default_rng(1)
        x = rng.normal(size=5000)
        result = inf.ols(1 + 2 * x + rng.normal(0, 0.1, 5000), np.column_stack([np.ones(5000), x]))
        np.testing.assert_allclose(result["beta"], [1, 2], atol=0.01)

    def test_newey_west_at_lag_zero_is_white(self):
        rng = np.random.default_rng(1)
        X = np.column_stack([np.ones(200), rng.normal(size=200)])
        e = rng.normal(size=200)
        bread = np.linalg.inv(X.T @ X)
        white = np.sqrt(np.diag(bread @ (X * e[:, None]).T @ (X * e[:, None]) @ bread))
        np.testing.assert_allclose(inf.newey_west_se(X, e, 0), white)

    def test_two_stage_removes_measurement_error(self):
        rng = np.random.default_rng(4)
        truth = np.cumsum(rng.normal(size=20000)) * 0.0 + rng.normal(size=20000)
        noisy, instrument = truth + rng.normal(size=20000), truth + rng.normal(size=20000)
        y = 2 * truth + rng.normal(size=20000)
        one = np.ones((20000, 1))
        self.assertLess(inf.ols(y, np.column_stack([one, noisy]))["beta"][1], 1.2)
        result = inf.two_stage(y, one, noisy, instrument)
        self.assertAlmostEqual(result["beta"][-1], 2, delta=0.1)
        self.assertGreater(result["first_stage_f"], 100)

    def test_block_sample_has_the_row_count_and_keeps_order_inside_blocks(self):
        positions = np.array([0, 1, 2, 5, 6, 7, 8, 12, 13, 20, 21, 22, 30])
        sample = inf.block_sample(positions, 4, np.random.default_rng(1))
        self.assertEqual(len(sample), len(positions))
        self.assertTrue(((sample >= 0) & (sample < len(positions))).all())

    def test_block_sample_reaches_every_row(self):
        positions = np.arange(50)
        rng = np.random.default_rng(1)
        seen = np.concatenate([inf.block_sample(positions, 5, rng) for _ in range(200)])
        self.assertEqual(len(np.unique(seen)), 50)

    def test_block_bootstrap_is_repeatable(self):
        values = np.random.default_rng(1).normal(size=300)
        estimator = lambda idx: np.array([values[idx].mean()])
        np.testing.assert_array_equal(inf.block_bootstrap(estimator, np.arange(300), 21, 20, 7), inf.block_bootstrap(estimator, np.arange(300), 21, 20, 7))

    def test_block_bootstrap_widens_the_error_for_dependent_data(self):
        rng = np.random.default_rng(1)
        shocks = rng.normal(size=4000)
        values = np.convolve(shocks, np.ones(21), mode="valid")
        estimator = lambda idx: np.array([values[idx].mean()])
        positions = np.arange(len(values))
        narrow = inf.block_bootstrap(estimator, positions, 1, 200, 3).std()
        wide = inf.block_bootstrap(estimator, positions, 63, 200, 3).std()
        self.assertGreater(wide, 2.5 * narrow)

    def test_non_overlapping_windows_share_no_return(self):
        dates = pd.bdate_range("2021-01-04", periods=400).to_numpy()
        valid = np.random.default_rng(3).random(400) > 0.15
        samples = inf.non_overlapping_samples(dates, valid)
        self.assertEqual(len(samples), 21)
        for sample in samples:
            self.assertTrue(valid[sample].all())
            self.assertTrue(((dates[sample[1:]] - dates[sample[:-1]]) >= np.timedelta64(30, "D")).all())

    def test_offsets_start_from_the_first_valid_session(self):
        dates = pd.bdate_range("2021-01-04", periods=400).to_numpy()
        valid = np.ones(400, dtype=bool)
        valid[:22] = False
        samples = inf.non_overlapping_samples(dates, valid)
        self.assertEqual([int(s[0]) for s in samples], list(range(22, 43)))
        self.assertEqual(len({s.tobytes() for s in samples}), 21)


class Events(unittest.TestCase):
    def test_all_listed_elections_are_sundays_and_open(self):
        for name, date in ev.EVENTS:
            self.assertEqual(pd.Timestamp(date).dayofweek, 6, name)
            self.assertGreaterEqual(pd.Timestamp(date), pd.Timestamp("2018-05-01"), name)

    def test_flat_term_structure_has_a_flat_forward(self):
        self.assertAlmostEqual(ev.forward_variance(0.5, 10000, 0.5, 50000), 0.25)

    def test_forward_variance_rebuilds_the_far_total(self):
        forward = ev.forward_variance(0.4, 10000, 0.6, 40000)
        self.assertAlmostEqual(0.4 ** 2 * 10000 + forward * 30000, 0.6 ** 2 * 40000)

    def test_straddle_uses_expiries_on_each_side_of_the_event(self):
        sessions = pd.bdate_range("2021-01-04", "2021-03-31").to_numpy()
        event = pd.Timestamp("2021-02-15")
        rows = [dict(session_date=pd.Timestamp(day), expiry=pd.Timestamp(expiry), minutes=(pd.Timestamp(expiry) - pd.Timestamp(day)).days * 1440, iv=0.5, tier=1.0)
                for day in sessions for expiry in ("2021-01-15", "2021-02-12", "2021-03-19") if pd.Timestamp(expiry) > pd.Timestamp(day)]
        found = ev.straddle(pd.DataFrame(rows), event, sessions)
        self.assertEqual(found["near_expiry"], pd.Timestamp("2021-02-12"))
        self.assertEqual(found["far_expiry"], pd.Timestamp("2021-03-19"))
        self.assertGreaterEqual(found["near_days"], 7)
        self.assertLess(found["observed"], found["near_expiry"])
        self.assertAlmostEqual(found["ratio"], 1.0)


if __name__ == "__main__":
    unittest.main()
