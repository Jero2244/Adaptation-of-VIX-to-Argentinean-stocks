"""Implied move calibration on real data. Rules are in CALIBRATION_PLAN.md. All results are exploratory, with no verdict.

Run from the project folder:
    conda run --no-capture-output -n py4fi python calibration/calib_run.py --freeze    Write the manifest, before any result
    conda run --no-capture-output -n py4fi python calibration/calib_run.py --stage c1  Row counts and checks, with no result
    conda run --no-capture-output -n py4fi python calibration/calib_run.py --stage c2  Primary measures
    conda run --no-capture-output -n py4fi python calibration/calib_run.py --stage c3  Benchmarks and cuts
Output stays local under the Databento license. This script reads the study's files and never writes them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_core as cc  # noqa: E402
import events as ev  # noqa: E402
import forecasts as fc  # noqa: E402
import stage4_rules as rules  # noqa: E402
from build_series import session_rates  # noqa: E402
from config import DATA, REPORTS, SOURCE  # noqa: E402

PLAN = cc.ROOT / "CALIBRATION_PLAN.md"
HERE = Path(__file__).resolve().parent
MANIFEST = REPORTS / "calib_freeze_manifest.json"
RESULTS = REPORTS / "calib_results.json"
Z_PANEL = DATA / "calibration_panel.parquet"
FROZEN_CODE = ("calib_core.py", "calib_run.py", "calib_synthetic.py", "test_calib.py")
LOG_HEADING = "## Post-result log"
BREAK = pd.Timestamp("2025-03-01")
STATUS = "Exploratory. Open data and 2016-01 to 2018-04 are development data. No verdict."


def to_plain(value):
    if isinstance(value, dict):
        return {str(k): to_plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_plain(v) for v in value]
    if isinstance(value, np.ndarray):
        return [to_plain(v) for v in value.tolist()]
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    return value


def plan_rules_text() -> str:
    """The plan without its post-result log, because that log grows after the freeze."""
    return PLAN.read_text(encoding="utf-8").split(LOG_HEADING)[0]


def manifest_now() -> dict:
    files = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in FROZEN_CODE}
    files["CALIBRATION_PLAN.md, text before the post-result log"] = hashlib.sha256(plan_rules_text().encode("utf-8")).hexdigest()
    return files


def write_freeze() -> None:
    if MANIFEST.exists():
        raise SystemExit("The manifest exists. Log a later change in the plan instead of writing a new manifest.")
    if RESULTS.exists():
        raise SystemExit("Results exist, so a freeze now would not come first.")
    synthetic = json.loads((REPORTS / "calib_synthetic_pipeline.json").read_text(encoding="utf-8"))
    if not synthetic["passed"]:
        raise SystemExit("The synthetic check did not pass.")
    text = json.dumps(dict(written_at=datetime.now(timezone.utc).isoformat(), files=manifest_now(), verdict_horizon=None), indent=2)
    MANIFEST.write_text(text, encoding="utf-8", newline="\n")
    print(f"Manifest: {MANIFEST}\nKeep this SHA-256 outside this folder: {hashlib.sha256(text.encode('utf-8')).hexdigest()}")


def require_freeze() -> list[str]:
    """Refuse a real run with no manifest. Return the changed files, which the result must disclose."""
    if not MANIFEST.exists():
        raise SystemExit("No manifest. Run --freeze first.")
    frozen = json.loads(MANIFEST.read_text(encoding="utf-8"))["files"]
    current = manifest_now()
    return sorted(name for name in set(frozen) | set(current) if frozen.get(name) != current.get(name))


def rates_for(frame: pd.DataFrame, path: Path) -> np.ndarray:
    dates = pd.DatetimeIndex(frame["session_date"])
    return cc.rate_30d(frame["session_date"], session_rates(dates, path))


def load_period(name: str) -> pd.DataFrame:
    if name == "open":
        frame = pd.read_parquet(DATA / "forecast_panel.parquet")
        stock = pd.read_parquet(DATA / "session_diagnostics.parquet")[["session_date", "stock_mid"]]
        frame = frame.merge(stock, on="session_date", how="left", validate="one_to_one")
        path = SOURCE / "fred_rates.csv"
    else:
        frame = pd.read_parquet(DATA / "test" / "test_panel.parquet")
        frame["stock_mid"] = np.nan
        path = SOURCE / "fred_rates_test.csv"
    frame = frame.sort_values("session_date").reset_index(drop=True)
    return cc.build_calibration(frame, rates_for(frame, path))


def stage_c1(panels: dict[str, pd.DataFrame]) -> dict:
    """Row counts and identities. This prints no hit rate, z, or return."""
    out = {}
    for name, frame in panels.items():
        rv = frame["rv30"].notna().to_numpy()
        atm = frame["atm30"].notna().to_numpy()
        half = frame["flag_half_day"].to_numpy(dtype=bool)
        rate = frame["r"].notna().to_numpy()
        valid = frame["valid"].to_numpy()
        returns = frame["return_total"].to_numpy(dtype=float)
        squares = np.concatenate([[0.0], np.cumsum(np.nan_to_num(returns) ** 2)])
        index = np.arange(len(frame))
        last = index + frame["outcome_sessions"].to_numpy(dtype=int)
        window_rv = (365 / 30) * (squares[last + 1] - squares[index + 1])
        gap = np.abs(window_rv[rv] - frame["rv30"].to_numpy()[rv])
        out[name] = dict(
            sessions=len(frame), first_session=frame["session_date"].iloc[0], last_session=frame["session_date"].iloc[-1],
            atm30_days=int(atm.sum()), rv30_days=int(rv.sum()), r_values=int(rate.sum()), half_days=int(half.sum()), half_days_with_atm30=int((half & atm).sum()),
            valid_z=int(valid.sum()), expected_valid_z=int((atm & rv & rate & ~half).sum()), z_where_no_rv30=int((valid & ~rv).sum()), rv30_where_no_outcome=int((rv & frame["R"].isna().to_numpy()).sum()),
            primary_rows=int(frame["primary"].sum()), primary_not_valid=int((frame["primary"].to_numpy() & ~valid).sum()), valid_not_primary=int((valid & ~frame["primary"].to_numpy()).sum()),
            window_sessions_mismatch=int((frame["outcome_sessions"].to_numpy()[rv] != frame["window_sessions"].to_numpy()[rv]).sum()), largest_rv30_identity_gap=float(gap.max()),
            tier1_valid=int((valid & (frame["tier"] == 1).to_numpy()).sum()), tier2_valid=int((valid & (frame["tier"] == 2).to_numpy()).sum()), stock_mid_on_valid=int((valid & frame["stock_mid"].notna().to_numpy()).sum()),
            first_valid=frame.loc[valid, "session_date"].iloc[0], last_valid=frame.loc[valid, "session_date"].iloc[-1],
        )
    return out


def rows_of(frame: pd.DataFrame, mask=None, z_name: str = "z"):
    use = frame["valid"].to_numpy() if mask is None else frame["valid"].to_numpy() & mask
    return frame[z_name].to_numpy(dtype=float)[use], frame["position"].to_numpy()[use]


def event_mask(frame: pd.DataFrame, event_list) -> np.ndarray:
    days = frame["session_date"].to_numpy()
    inside = np.zeros(len(frame), dtype=bool)
    for _, date in event_list:
        if np.datetime64(pd.Timestamp(date)) > days[-1]:
            continue
        day = ev.first_session(date, days)
        inside |= ((frame["session_date"] < day) & (frame["session_date"] + pd.Timedelta(days=cc.WINDOW_DAYS) >= day)).to_numpy()
    return inside


def pit_table(z: np.ndarray, positions: np.ndarray) -> dict:
    u = cc.stats.norm.cdf(z)
    found = cc.intervals_for(lambda index: cc.pit_shares(u[index]), positions)
    out = dict(shares=cc.pit_shares(u))
    for block, part in found.items():
        out[f"low{block}"] = None if part is None else part["low"]
        out[f"high{block}"] = None if part is None else part["high"]
    return out


def stage_c2(open_frame: pd.DataFrame) -> dict:
    z, positions = rows_of(open_frame)
    rows = open_frame[open_frame["valid"]]
    pred = cc.normal_band(rows["r"].to_numpy(), rows["s"].to_numpy())
    R = rows["R"].to_numpy()
    reliability = {}
    for x in cc.THRESHOLDS:
        p, happened = pred.move_probability(x), cc.move_happened(R, x)
        reliability[str(x)] = dict(groups=cc.reliability_groups(p, happened), brier=cc.brier(p, happened).mean(), mean_probability=p.mean(), observed=happened.mean())
    return dict(period="2018-05 to 2026-10, all open data, events included, Tier 1 and Tier 2", nominal=dict(inner=cc.INNER, outer=cc.OUTER, tail=cc.TAIL, mean_z2=1.0, mean_abs_z=cc.MEAN_ABS),
                measures=cc.measure_table(z, positions), mean_z=z.mean(), sd_z=z.std(ddof=1), median_atm30=open_frame.loc[open_frame["valid"], "atm30"].median(), pit=pit_table(z, positions), fixed_steps=cc.fixed_step_table(open_frame), reliability=reliability,
                largest_abs_z=[dict(session_date=row.session_date, z=row.z) for row in rows.assign(abs_z=np.abs(z)).nlargest(5, "abs_z").itertuples()])


def benchmark_predictives(frame: pd.DataFrame) -> tuple[dict, np.ndarray]:
    """Each predictive on all rows, and the mask of rows where every method has a value."""
    primary = frame["primary"].to_numpy()
    score = primary & (frame["position"].to_numpy() >= fc.START_SESSIONS)
    har_duan = fc.expanding_forecasts(frame, rules.HAR, primary, score, smearing=True)
    har_plain = fc.expanding_forecasts(frame, rules.HAR, primary, score, smearing=False)
    k, nu = cc.expanding_scale(frame), cc.expanding_nu(frame)
    r, s, m = frame["r"].to_numpy(), frame["s"].to_numpy(), frame["m"].to_numpy()
    with np.errstate(invalid="ignore"):
        methods = {"ATM30": cc.normal_band(r, s), "HAR, Duan": cc.normal_band(r, np.sqrt(har_duan * cc.T)), "HAR, no factor": cc.normal_band(r, np.sqrt(har_plain * cc.T)), "Scaled ATM30": cc.normal_band(r, k * s), "Fat-tailed ATM30": cc.Predictive(m, s, np.where(np.isfinite(nu), nu, 1000.0))}
    common = frame["valid"].to_numpy() & np.isfinite(har_duan) & np.isfinite(har_plain) & np.isfinite(k) & np.isfinite(nu)
    return dict(methods=methods, k=k, nu=nu), common


def benchmark_tables(frame: pd.DataFrame) -> dict:
    found, common = benchmark_predictives(frame)
    rows = frame[common]
    R, positions = rows["R"].to_numpy(), rows["position"].to_numpy()
    preds = {name: pred.take(common) for name, pred in found["methods"].items()}
    base_scores = cc.row_scores(preds["ATM30"], R)
    base_brier = {x: cc.brier(preds["ATM30"].move_probability(x), cc.move_happened(R, x)) for x in cc.THRESHOLDS}
    out = dict(rows=int(common.sum()), first_origin=rows["session_date"].iloc[0], last_origin=rows["session_date"].iloc[-1], k=dict(first=found["k"][common][0], last=found["k"][common][-1], median=np.median(found["k"][common])), nu=dict(first=found["nu"][common][0], last=found["nu"][common][-1], median=np.median(found["nu"][common])), methods={})
    for name, pred in preds.items():
        hits = {key: value.astype(float) for key, value in cc.hit_rows(pred, R).items()}
        names = list(hits)
        matrix = np.column_stack([hits[key] for key in names])
        intervals = cc.intervals_for(lambda index: matrix[index].mean(axis=0), positions)
        entry = dict(mean_s=pred.s.mean(), pit=cc.pit_shares(pred.cdf(R)))
        for where, key in enumerate(names):
            entry[key] = dict(value=matrix[:, where].mean(), **{f"low{b}": None if p is None else p["low"][where] for b, p in intervals.items()}, **{f"high{b}": None if p is None else p["high"][where] for b, p in intervals.items()})
        z = (R - pred.loc) / pred.s
        entry["mean_z2"] = np.mean(z ** 2)
        entry["mean_abs_z"] = np.mean(np.abs(z))
        scores = cc.row_scores(pred, R)
        entry["scores"] = {}
        for key, values in scores.items():
            difference = values - base_scores[key]
            part = cc.intervals_for(lambda index: np.array([difference[index].mean()]), positions)
            entry["scores"][key] = dict(mean=values.mean(), difference=difference.mean(), **{f"low{b}": None if p is None else p["low"][0] for b, p in part.items()}, **{f"high{b}": None if p is None else p["high"][0] for b, p in part.items()})
        entry["brier"] = {}
        for x in cc.THRESHOLDS:
            values = cc.brier(pred.move_probability(x), cc.move_happened(R, x))
            difference = values - base_brier[x]
            part = cc.intervals_for(lambda index: np.array([difference[index].mean()]), positions)
            entry["brier"][str(x)] = dict(mean=values.mean(), difference=difference.mean(), groups=cc.reliability_groups(pred.move_probability(x), cc.move_happened(R, x)), **{f"low{b}": None if p is None else p["low"][0] for b, p in part.items()}, **{f"high{b}": None if p is None else p["high"][0] for b, p in part.items()})
        out["methods"][name] = entry
    return out


def cut_tables(frame: pd.DataFrame, test_frame: pd.DataFrame) -> dict:
    inside = event_mask(frame, ev.EVENTS)
    dates = frame["session_date"]
    near = frame["near_days"].to_numpy(dtype=float)
    frame = frame.copy()
    frame["z_zero"] = frame["R"] / frame["s"]
    frame["z_mid"] = (frame["R"] + np.log(frame["close"] / frame["stock_mid"]) - frame["m"]) / frame["s"]
    cuts = {
        "Event in window": rows_of(frame, inside), "No event in window": rows_of(frame, ~inside),
        "Before 2025-03": rows_of(frame, (dates < BREAK).to_numpy()), "From 2025-03": rows_of(frame, (dates >= BREAK).to_numpy()),
        "Tier 1": rows_of(frame, (frame["tier"] == 1).to_numpy()), "Tier 2": rows_of(frame, (frame["tier"] == 2).to_numpy()),
        "Near expiry under 7 days": rows_of(frame, near < 7), "Near expiry 7 days or more": rows_of(frame, near >= 7),
        "Centre at zero": rows_of(frame, None, "z_zero"),
    }
    out = {name: cc.measure_table(z, positions) for name, (z, positions) in cuts.items()}
    mid_use = frame["valid"].to_numpy() & frame["z_mid"].notna().to_numpy()
    out["Start at the 15:45 stock mid"] = cc.measure_table(frame["z_mid"].to_numpy()[mid_use], frame["position"].to_numpy()[mid_use])
    same = rows_of(frame, mid_use)
    out["Same rows as the 15:45 start, at the close"] = cc.measure_table(*same)
    z, positions = rows_of(test_frame)
    inside_test = event_mask(test_frame, ev.TEST_EVENTS)
    out["2016-01 to 2018-04"] = cc.measure_table(z, positions)
    out["2016-01 to 2018-04, event in window"] = cc.measure_table(*rows_of(test_frame, inside_test))
    out["2016-01 to 2018-04, no event in window"] = cc.measure_table(*rows_of(test_frame, ~inside_test))
    return dict(cuts=out, test_period_fixed_steps=cc.fixed_step_table(test_frame), not_run=dict(american_exercise="The tree sensitivity is not done."))


def save(key: str, value, changed: list[str]) -> None:
    results = json.loads(RESULTS.read_text(encoding="utf-8")) if RESULTS.exists() else dict(status=STATUS)
    results[key] = to_plain(value)
    results["changed_since_freeze"] = changed
    RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--stage", choices=("c1", "c2", "c3"))
    args = parser.parse_args()
    if args.freeze:
        write_freeze()
        return
    changed = require_freeze()
    if changed:
        print(f"Changed since the freeze, and disclosed in the results: {changed}")
    if cc.alignment_failures():
        raise SystemExit("The alignment check failed")
    panels = dict(open=load_period("open"), test=load_period("test"))
    if args.stage == "c1":
        value = stage_c1(panels)
        save("c1", value, changed)
        print(json.dumps(to_plain(value), indent=1))
    elif args.stage == "c2":
        value = stage_c2(panels["open"])
        save("c2", value, changed)
        columns = ["position", "session_date", "atm30", "tier", "r", "s", "m", "R", "z", "valid", "outcome_end", "near_days"]
        panels["open"][columns].to_parquet(Z_PANEL, index=False)
        print(json.dumps(to_plain(value), indent=1))
    elif args.stage == "c3":
        value = dict(benchmarks=benchmark_tables(panels["open"]), **cut_tables(panels["open"], panels["test"]))
        save("c3", value, changed)
        print(json.dumps(to_plain(value), indent=1))


if __name__ == "__main__":
    main()
