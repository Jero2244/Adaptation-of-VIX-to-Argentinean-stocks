"""C1b: run the full pipeline on simulated prices with a known vol, and measure how the intervals behave. No real data is read.

Run from the project folder: conda run --no-capture-output -n py4fi python calibration/calib_synthetic.py
Output: reports/calib_synthetic.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_core as cc  # noqa: E402
import inference as inf  # noqa: E402

OUTPUT = cc.ROOT / "reports" / "calib_synthetic.json"
VOL = 0.6
RATE = 0.03
SESSIONS = 2137
CHECK_SIMS = 200
COVER_SIMS = 300
COVER_REPS = 500
FORWARD_SESSIONS = (252, 504, 756, 1260)
DRIFT_RHO = 0.98
DRIFT_SD = 0.25


def simulate(rng, sessions=SESSIONS, vol=VOL, implied=None, r=RATE):
    """Prices in calendar time, so that z is exactly standard normal when implied equals vol."""
    dates = pd.bdate_range("2018-05-01", periods=sessions)
    days = np.diff(dates.to_numpy()) / np.timedelta64(1, "D")
    dt = days / 365
    returns = np.concatenate([[np.nan], (r - vol ** 2 / 2) * dt + vol * np.sqrt(dt) * rng.standard_normal(sessions - 1)])
    frame = pd.DataFrame({"position": np.arange(sessions), "session_date": dates, "return_total": returns, "atm30": vol if implied is None else implied, "flag_half_day": False})
    return cc.build_calibration(frame, np.full(sessions, r))


def wandering_implied(rng, sessions, level=VOL):
    """An implied vol whose error wanders slowly. The true hit rate is then below the nominal rate and is clustered in time."""
    shocks = rng.standard_normal(sessions)
    path = np.empty(sessions)
    path[0] = DRIFT_SD * shocks[0]
    scale = DRIFT_SD * np.sqrt(1 - DRIFT_RHO ** 2)
    for i in range(1, sessions):
        path[i] = DRIFT_RHO * path[i - 1] + scale * shocks[i]
    return level * np.exp(path)


def check_pipeline() -> dict:
    """Mean of the measures over independent simulations. Each must match its nominal value within simulation error."""
    rng = np.random.default_rng(cc.SEED)
    values = []
    for _ in range(CHECK_SIMS):
        frame = simulate(rng)
        values.append(cc.measures_from_z(frame.loc[frame["valid"], "z"].to_numpy()))
    values = np.array(values)
    nominal = np.array([cc.INNER, cc.OUTER, cc.TAIL, cc.TAIL, 1.0, cc.MEAN_ABS])
    means, errors = values.mean(axis=0), values.std(axis=0, ddof=1) / np.sqrt(CHECK_SIMS)
    return {name: dict(mean=float(means[i]), simulation_se=float(errors[i]), nominal=float(nominal[i]), passed=bool(abs(means[i] - nominal[i]) < 4 * errors[i])) for i, name in enumerate(cc.MEASURES)}


def interval_behaviour(z_maker, truth: float, sessions: int, seed: int) -> dict:
    """Share of simulations whose intervals hold the truth, and share in which the verdict rule fires against the nominal rate."""
    rng = np.random.default_rng(seed)
    held = {block: 0 for block in cc.BLOCKS}
    usable = 0
    fired = 0
    widths = {block: [] for block in cc.BLOCKS}
    for sim in range(COVER_SIMS):
        z = z_maker(rng, sessions)
        positions = np.arange(len(z))
        hits = (np.abs(z) < 1).astype(float)
        outside = True
        for block in cc.BLOCKS:
            draws = inf.block_bootstrap(lambda index: np.array([hits[index].mean()]), positions, block, COVER_REPS, seed + sim + block)[:, 0]
            low, high = np.percentile(draws, [2.5, 97.5])
            held[block] += low <= truth <= high
            widths[block].append(high - low)
            outside &= bool(low > cc.INNER or high < cc.INNER)
        usable += 1
        fired += outside
    return dict(sessions=sessions, true_inner=truth, cover21=held[21] / usable, cover63=held[63] / usable, width21=float(np.mean(widths[21])), width63=float(np.mean(widths[63])), verdict_fires=fired / usable)


def calibrated_z(rng, sessions):
    frame = simulate(rng, sessions + 30)
    return frame.loc[frame["valid"], "z"].to_numpy()[:sessions]


def scaled_z(factor):
    def make(rng, sessions):
        frame = simulate(rng, sessions + 30, implied=VOL * factor)
        return frame.loc[frame["valid"], "z"].to_numpy()[:sessions]
    return make


def wandering_z(rng, sessions):
    implied = wandering_implied(rng, sessions + 30)
    frame = simulate(rng, sessions + 30, implied=implied)
    return frame.loc[frame["valid"], "z"].to_numpy()[:sessions]


def true_inner(maker, sessions=4000, runs=100, seed=99) -> float:
    rng = np.random.default_rng(seed)
    return float(np.mean([np.mean(np.abs(maker(rng, sessions)) < 1) for _ in range(runs)]))


def pipeline_only() -> None:
    """The check that the freeze needs. It writes one small file and takes about a minute."""
    pipeline = check_pipeline()
    failures = cc.alignment_failures()
    passed = all(row["passed"] for row in pipeline.values()) and not failures
    (cc.ROOT / "reports" / "calib_synthetic_pipeline.json").write_text(json.dumps(dict(passed=passed, pipeline=pipeline, alignment_failures=failures), indent=2), encoding="utf-8")
    print(json.dumps(dict(passed=passed, pipeline=pipeline), indent=1))
    if not passed:
        raise SystemExit("The synthetic check failed")


def main() -> None:
    if "--pipeline-only" in sys.argv:
        pipeline_only()
        return
    out = dict(note="Simulated prices only. Constant vol is the kindest case for the intervals. The wandering case has a slow implied-vol error, and real data can differ from both.")
    out["pipeline"] = check_pipeline()
    print(json.dumps(out["pipeline"], indent=1), flush=True)
    out["alignment_failures"] = cc.alignment_failures()
    wandering_truth = true_inner(wandering_z)
    too_wide = scaled_z(1.25)
    wide_truth = true_inner(too_wide)
    out["coverage_full_sample"] = dict(constant=interval_behaviour(calibrated_z, cc.INNER, SESSIONS - 30, 101), wandering=interval_behaviour(wandering_z, wandering_truth, SESSIONS - 30, 102))
    print(json.dumps(out["coverage_full_sample"], indent=1), flush=True)
    out["forward_power"] = []
    for sessions in FORWARD_SESSIONS:
        row = dict(sessions=sessions)
        row["no_error"] = interval_behaviour(calibrated_z, cc.INNER, sessions, 200 + sessions)
        row["bands_25pct_too_wide"] = interval_behaviour(too_wide, wide_truth, sessions, 300 + sessions)
        row["wandering_error"] = interval_behaviour(wandering_z, wandering_truth, sessions, 400 + sessions)
        out["forward_power"].append(row)
        print(json.dumps(row, indent=1), flush=True)
    OUTPUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    if not all(row["passed"] for row in out["pipeline"].values()) or out["alignment_failures"]:
        raise SystemExit("The synthetic check failed")


if __name__ == "__main__":
    main()
