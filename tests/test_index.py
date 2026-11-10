import sys
import unittest
from math import exp, log, sqrt
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from atm_index import (TARGET_MINUTES, YEAR_MINUTES, black_call, bracket_terms, constant_maturity, expiry_minutes, solve_total_vol,
                       term_iv)
from model_free_index import term_variance

RATE = 0.04
VOL = 0.65
SPOT_FORWARD = 41.3


def flat_chain(minutes, vol=VOL, forward=SPOT_FORWARD, strikes=None, half_spread=0.0):
    strikes = strikes if strikes is not None else [15 + 2.5 * i for i in range(30)]
    years = minutes / YEAR_MINUTES
    discount = exp(-RATE * years)
    rows = []
    for strike in strikes:
        call = discount * black_call(forward, strike, vol * sqrt(years))
        put = call - discount * (forward - strike)
        for right, price in (("C", call), ("P", put)):
            rows.append(dict(strike=float(strike), right=right, bid=price - half_spread, ask=price + half_spread, age=1.0))
    return pd.DataFrame(rows)


class BlackSolver(unittest.TestCase):
    def test_round_trip(self):
        forward, strike, total_vol = 40.0, 44.0, 0.3
        price = black_call(forward, strike, total_vol) + (strike - forward) / 2
        self.assertAlmostEqual(solve_total_vol(price, forward, strike), total_vol, places=8)

    def test_price_at_intrinsic_has_no_solution(self):
        self.assertIsNone(solve_total_vol(2.0, 40.0, 44.0))


class AtmTerm(unittest.TestCase):
    def test_flat_chain_returns_input_vol_tier_1(self):
        term = term_iv(flat_chain(20000), 20000, RATE)
        self.assertEqual(term["tier"], 1)
        self.assertAlmostEqual(term["forward"], SPOT_FORWARD, places=8)
        self.assertAlmostEqual(term["iv"], VOL, places=6)

    def test_single_strike_is_tier_2(self):
        term = term_iv(flat_chain(20000, strikes=[40.0]), 20000, RATE)
        self.assertEqual(term["tier"], 2)
        self.assertAlmostEqual(term["iv"], VOL, places=6)

    def test_far_strike_is_refused(self):
        term = term_iv(flat_chain(20000, strikes=[10.0, 90.0]), 20000, RATE)
        self.assertIsNone(term["iv"])

    def test_one_sided_pair_is_not_used(self):
        chain = flat_chain(20000, strikes=[40.0, 42.5])
        chain.loc[(chain["strike"] == 42.5) & (chain["right"] == "C"), "bid"] = 0.0
        term = term_iv(chain, 20000, RATE)
        self.assertEqual(term["pairs"], 1)
        self.assertEqual(term["tier"], 2)


class Maturity(unittest.TestCase):
    def test_flat_variance_is_preserved(self):
        self.assertAlmostEqual(constant_maturity(20000, 0.25, 60000, 0.25), 0.25)

    def test_target_on_a_term_uses_that_term(self):
        self.assertAlmostEqual(constant_maturity(TARGET_MINUTES, 0.3, 60000, 0.5), 0.3)

    def test_no_extrapolation(self):
        self.assertIsNone(bracket_terms({"a": 50000, "b": 90000}))
        self.assertIsNone(bracket_terms({"a": 1000, "b": 20000}))

    def test_bracket(self):
        self.assertEqual(bracket_terms({"a": 1000, "b": 20000, "c": 60000, "d": 90000}), ("b", "c"))

    def test_floor_moves_the_near_term(self):
        self.assertEqual(bracket_terms({"a": 1000, "b": 60000}, floor_minutes=7 * 1440), None)

    def test_expiry_minutes_cross_dst(self):
        # 2024-03-10 has 23 hours in New York.
        self.assertEqual(expiry_minutes("2024-03-11", "2024-03-08"), 3 * 1440 + 15 - 60)


class ModelFree(unittest.TestCase):
    def test_flat_chain_returns_input_vol(self):
        minutes = 30 * 1440
        strikes = [2.5 * i for i in range(4, 60)]
        out = term_variance(flat_chain(minutes, strikes=strikes), minutes, RATE, SPOT_FORWARD)
        self.assertEqual(out["reason"], "ok")
        self.assertAlmostEqual(sqrt(out["variance"]), VOL, places=3)

    def test_thin_flat_chain_extrapolates_but_recovers_flat_vol(self):
        minutes = 30 * 1440
        out = term_variance(flat_chain(minutes, strikes=[35.0, 37.5, 45.0, 47.5]), minutes, RATE, SPOT_FORWARD)
        self.assertAlmostEqual(sqrt(out["variance"]), VOL, places=3)
        self.assertGreater(out["extrapolated_share"], 0.2)

    def test_one_quote_on_a_wing_is_refused(self):
        minutes = 30 * 1440
        out = term_variance(flat_chain(minutes, strikes=[35.0, 37.5, 45.0]), minutes, RATE, SPOT_FORWARD)
        self.assertIsNone(out["variance"])


if __name__ == "__main__":
    unittest.main()
