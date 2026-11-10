import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import forecasts as fc
import inference as inf
import realized as rz
import stage4_rules as rules


def synthetic_panel(n=620, true_b=0.8, seed=3):
    """A panel with a known coefficient on log IV, on a business-day grid. It has no market data."""
    rng = np.random.default_rng(seed)
    dates = pd.bdate_range("2021-01-04", periods=n)
    close = 50 * np.exp(np.cumsum(rng.normal(0, 0.03, n)))
    frame = pd.DataFrame(dict(session_date=dates, open=close, close=close, dividend_cash=0.0, rights_cash=0.0))
    panel = rz.trailing_realized(rz.forward_realized(rz.total_returns(frame)))
    state = np.zeros(n)
    for i in range(1, n):
        state[i] = 0.97 * state[i - 1] + rng.normal(0, 0.15)
    panel["atm30"] = 0.6 * np.exp(state / 2)
    panel["tier"] = 1
    panel = rules.add_inputs(panel)
    mask = panel["log_rv30"].notna()
    panel.loc[mask, "log_rv30"] = -1 + true_b * panel.loc[mask, "log_iv2"] + rng.normal(0, 0.3, mask.sum())
    panel.loc[mask, "rv30"] = np.exp(panel.loc[mask, "log_rv30"])
    return panel


class FixedSteps(unittest.TestCase):
    def test_samples_start_at_first_valid_and_keep_the_step(self):
        valid = np.array([False, False] + [True] * 60)
        samples = inf.fixed_step_samples(valid, 22)
        self.assertEqual(len(samples), 22)
        self.assertEqual(samples[0].tolist(), [2, 24, 46])
        self.assertEqual(samples[3].tolist(), [5, 27, 49])

    def test_paths_do_not_merge_across_missing_days(self):
        valid = np.ones(200, dtype=bool)
        valid[::7] = False
        valid[0] = True
        sets = [set(s.tolist()) for s in inf.fixed_step_samples(valid, 23)]
        for i in range(len(sets)):
            for j in range(i + 1, len(sets)):
                self.assertFalse(sets[i] & sets[j])

    def test_steps_of_22_sessions_do_not_share_a_return(self):
        panel = synthetic_panel(300)
        for sample in inf.fixed_step_samples(panel["primary"].to_numpy(), 22):
            chosen = panel.iloc[sample]
            self.assertTrue((chosen["session_date"].to_numpy()[1:] >= chosen["window_end"].to_numpy()[:-1]).all())

    def test_short_sample_has_no_estimate(self):
        panel = synthetic_panel(150)
        table = inf.fixed_step_table(panel, "log_rv30", rules.FULL, rules.IV, panel["primary"].to_numpy(), (22,), min_rows=7)
        self.assertEqual(len(table), 22)
        self.assertTrue(table.loc[table["n"] < 7, "coefficient"].isna().all())


class ClarkWest(unittest.TestCase):
    def test_equal_forecasts_give_zero(self):
        y, f = np.array([1.0, 2.0]), np.array([1.5, 1.5])
        np.testing.assert_allclose(inf.clark_west(y, f, f), 0.0)

    def test_known_value(self):
        # y=1, small=0, big=2: 1 - (1 - 4) = 4.
        self.assertAlmostEqual(float(inf.clark_west(np.array([1.0]), np.array([0.0]), np.array([2.0]))[0]), 4.0)


class Floor(unittest.TestCase):
    def test_passes_with_full_coverage(self):
        result = rules.data_floor(np.ones(450, dtype=bool))
        self.assertTrue(result["passed"])
        # 450 rows give 21 full spans. The last 9 rows do not fill a span.
        self.assertEqual(result["filled_spans"], 21)

    def test_too_few_origins(self):
        valid = np.zeros(600, dtype=bool)
        valid[:299] = True
        self.assertFalse(rules.data_floor(valid)["passed"])

    def test_spans_can_fail_with_enough_origins(self):
        valid = np.zeros(600, dtype=bool)
        valid[:399] = True
        result = rules.data_floor(valid)
        self.assertEqual((result["origins"], result["filled_spans"]), (399, 19))
        self.assertFalse(result["passed"])

    def test_nine_rows_do_not_fill_a_span(self):
        valid = np.zeros(21 * 30, dtype=bool)
        for start in range(0, 21 * 30, 21):
            valid[start:start + 9] = True
        self.assertEqual(rules.data_floor(valid)["filled_spans"], 0)

    def test_empty(self):
        self.assertFalse(rules.data_floor(np.zeros(10, dtype=bool))["passed"])


FLOOR_OK = dict(origins=400, filled_spans=22, passed=True)


def rule(low21, low63, high21=1.0, high63=1.0):
    return dict(b=0.5 if low21 > 0 else -0.1, low21=low21, low63=low63, high21=high21, high63=high63)


def race(cw_t=0.0, qlike_high=1.0, scored=300):
    return dict(scored=scored, clark_west=dict(t=cw_t), qlike_duan=dict(mean=-0.1, high=qlike_high), qlike_no_factor=dict(mean=-0.1))


class Outcomes(unittest.TestCase):
    def test_floor_comes_first(self):
        floor = dict(origins=10, filled_spans=1, passed=False)
        self.assertEqual(rules.decide(floor, rule(0.1, 0.1), race(3, -1))["outcome"], rules.NO_FLOOR)

    def test_supported_needs_both_lower_bounds(self):
        self.assertEqual(rules.decide(FLOOR_OK, rule(0.1, 0.1), race())["outcome"], rules.SUPPORTED)
        self.assertEqual(rules.decide(FLOOR_OK, rule(0.1, -0.1), race())["outcome"], rules.INCONCLUSIVE)
        self.assertEqual(rules.decide(FLOOR_OK, rule(-0.1, 0.1), race())["outcome"], rules.INCONCLUSIVE)

    def test_clark_west_is_a_label_only(self):
        passed = rules.decide(FLOOR_OK, rule(0.1, 0.1), race(cw_t=2.0))
        failed = rules.decide(FLOOR_OK, rule(0.1, 0.1), race(cw_t=1.0))
        self.assertEqual((passed["outcome"], failed["outcome"]), (rules.SUPPORTED, rules.SUPPORTED))
        self.assertTrue(passed["also_out_of_sample"])
        self.assertFalse(failed["also_out_of_sample"])

    def test_clark_west_needs_180_rows(self):
        self.assertFalse(rules.decide(FLOOR_OK, rule(0.1, 0.1), race(cw_t=3.0, scored=179))["also_out_of_sample"])
        self.assertTrue(rules.decide(FLOOR_OK, rule(0.1, 0.1), race(cw_t=3.0, scored=180))["also_out_of_sample"])

    def test_labels_are_absent_without_rule_1(self):
        decision = rules.decide(FLOOR_OK, rule(-0.1, -0.1), race(cw_t=3.0, qlike_high=-1.0))
        self.assertEqual(decision["outcome"], rules.INCONCLUSIVE)
        self.assertFalse(decision["also_out_of_sample"] or decision["usable_gain"])

    def test_usable_gain_uses_the_upper_percentile(self):
        self.assertTrue(rules.decide(FLOOR_OK, rule(0.1, 0.1), race(qlike_high=-0.01))["usable_gain"])
        self.assertFalse(rules.decide(FLOOR_OK, rule(0.1, 0.1), race(qlike_high=0.01))["usable_gain"])

    def test_smaller_needs_both_upper_bounds(self):
        self.assertEqual(rules.decide(FLOOR_OK, rule(-0.5, -0.5, 0.3, 0.36), race())["outcome"], rules.SMALLER)
        self.assertEqual(rules.decide(FLOOR_OK, rule(-0.5, -0.5, 0.3, 0.37), race())["outcome"], rules.INCONCLUSIVE)

    def test_blank_interval_cannot_pass(self):
        self.assertEqual(rules.decide(FLOOR_OK, rule(0.1, np.nan), race())["outcome"], rules.INCONCLUSIVE)

    def test_verdict_line_states_the_period_and_the_coverage(self):
        decision = rules.decide(FLOOR_OK, rule(0.1, 0.1), race(cw_t=2.0))
        line = rules.verdict_line(decision, rule(0.1, 0.1), rule(-0.1, 0.1), race(cw_t=2.0))
        self.assertIn("Supported, also out-of-sample", line)
        self.assertIn("2016-01 to 2018-04 only", line)
        self.assertIn("80% to 91%", line)
        self.assertIn("ordinary-day question stays open", line)

    def test_verdict_line_states_the_sign(self):
        decision = rules.decide(FLOOR_OK, rule(-0.1, -0.1), race())
        self.assertIn("sign of b is not positive", rules.verdict_line(decision, rule(-0.1, -0.1), None, race()))

    def test_verdict_line_states_opposite_qlike_signs(self):
        mixed = dict(race(), qlike_no_factor=dict(mean=0.1))
        decision = rules.decide(FLOOR_OK, rule(0.1, 0.1), mixed)
        self.assertIn("opposite signs", rules.verdict_line(decision, rule(0.1, 0.1), rule(0.1, 0.1), mixed))


class Evaluation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.panel = synthetic_panel()
        cls.result = rules.evaluate(cls.panel, [pd.Timestamp("2021-08-02")], reps=60)

    def test_recovers_a_known_coefficient(self):
        self.assertAlmostEqual(self.result["rule1"]["b"], 0.8, delta=0.15)

    def test_scoring_starts_at_position_252(self):
        self.assertGreaterEqual(self.result["race"]["scored"], rules.MIN_SCORED)
        self.assertEqual(self.result["race"]["first_scored"], self.panel["session_date"].iloc[252])

    def test_race_has_all_results(self):
        for name in ("clark_west", "clark_west_block63", "qlike_duan", "qlike_no_factor", "mean_target", "mean_forecast"):
            self.assertIn(name, self.result["race"])

    def test_event_drop_removes_windows_with_the_event(self):
        day = pd.Timestamp("2021-08-02")
        rows = self.panel[self.panel["primary"]]
        chosen = rules.without_events(rows, [day])
        self.assertFalse(((chosen["session_date"] < day) & (chosen["window_end"] >= day)).any())
        self.assertLess(len(chosen), len(rows))

    def test_same_seed_gives_the_same_result(self):
        again = rules.evaluate(self.panel, [pd.Timestamp("2021-08-02")], reps=60)
        self.assertEqual(self.result["rule1"], again["rule1"])

    def test_no_later_target_changes_a_forecast(self):
        origin = 400
        changed = self.panel.copy()
        later = changed["window_end"] > changed["session_date"].iloc[origin]
        changed.loc[later, "rv30"] = changed.loc[later, "rv30"] * 1.5
        changed.loc[later, "log_rv30"] = np.log(changed.loc[later, "rv30"])
        mask = np.zeros(len(changed), dtype=bool)
        mask[origin] = True
        one = fc.expanding_forecasts(self.panel, rules.FULL, self.panel["primary"].to_numpy(), mask)
        two = fc.expanding_forecasts(changed, rules.FULL, changed["primary"].to_numpy(), mask)
        self.assertEqual(one[origin], two[origin])


if __name__ == "__main__":
    unittest.main()
