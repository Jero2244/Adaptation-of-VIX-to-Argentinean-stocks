"""Run the real main() of a code copy. Only step_a is replaced, because the copy has no zips. step_b and the gate are real, on synthetic bars."""
import os, sys
project = os.environ["DRIVER_PROJECT"]; mode = os.environ["DRIVER_MODE"]
sys.path.insert(0, project); sys.path.insert(1, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, pandas as pd
import common
import run_tests_once as rt


def fake_step_a(start, end, marker, rates):
    assert rt.marker_opens(marker, rt.SCOPE_OPTIONS)
    if mode == "crash":
        raise ValueError(f"forward was {common.SECRET}")
    rng = np.random.default_rng(3)
    c = common.closes()
    series = pd.DataFrame(dict(session_date=c.index, atm30=0.6 * np.exp(rng.normal(0, .2, len(c))), tier=1, near_forward=c.to_numpy() * np.exp(rng.normal(0, .003, len(c))), status="ok", year=c.index.year))
    if mode == "wrongmap":
        series["near_forward"] *= 1.5
    if mode == "thin":
        series["atm30"] = np.nan; series["status"] = "no two-sided pair"
    counts = dict(sessions=len(series), atm30_days=int(series["atm30"].notna().sum()), mode=mode)
    return series, pd.DataFrame(dict(a=[1])), counts


rt.step_a = fake_step_a
orig = rt.step_b
rt.step_b = lambda series, s, e, m, ev: orig(series, s, e, m, ev, 50)
sys.argv = ["run_tests_once.py", *sys.argv[1:]]
rt.main()
