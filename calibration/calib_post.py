"""Checks chosen after seeing the C2 and C3 results. They are post-result work, are logged in CALIBRATION_PLAN.md, and are not primary.

Run from the project folder: conda run --no-capture-output -n py4fi python calibration/calib_post.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import calib_core as cc  # noqa: E402
import calib_run as run  # noqa: E402
import events as ev  # noqa: E402


def one_event(frame: pd.DataFrame, event_list, name: str) -> np.ndarray:
    return run.event_mask(frame, [item for item in event_list if item[0] == name])


def past_base_rate(frame: pd.DataFrame, happened: np.ndarray) -> np.ndarray:
    """The past share of moves at each origin, from valid past rows only, with the rules of the benchmarks."""
    valid = frame["valid"].to_numpy(dtype=bool)
    hits = np.concatenate([[0.0], np.cumsum(np.where(valid, happened, 0.0))])
    count = np.concatenate([[0], np.cumsum(valid)])
    ends = cc.past_end_positions(frame)
    out = np.full(len(frame), np.nan)
    use = cc.eligible_origin(frame, count[ends]) & valid
    out[use] = hits[ends[use]] / count[ends[use]]
    return out


def base_rate_table(frame: pd.DataFrame) -> dict:
    """Brier scores of ATM30 against a past base rate, on the rows where the past rate exists, and against the base rate of the whole sample, which uses hindsight."""
    out = {}
    R = frame["R"].to_numpy(dtype=float)
    pred = cc.normal_band(frame["r"].to_numpy(), frame["s"].to_numpy())
    for x in cc.THRESHOLDS:
        with np.errstate(invalid="ignore"):
            happened = cc.move_happened(R, x)
        past = past_base_rate(frame, happened)
        use = np.isfinite(past)
        positions = frame["position"].to_numpy()[use]
        atm = cc.brier(pred.move_probability(x)[use], happened[use])
        difference = atm - cc.brier(past[use], happened[use])
        part = cc.intervals_for(lambda index: np.array([difference[index].mean()]), positions)
        share = happened[use].mean()
        out[str(x)] = dict(rows=int(use.sum()), atm30=atm.mean(), past_base_rate=cc.brier(past[use], happened[use]).mean(), hindsight_base_rate=cc.brier(np.full(use.sum(), share), happened[use]).mean(), atm_minus_past=difference.mean(), **{f"low{b}": None if p is None else p["low"][0] for b, p in part.items()}, **{f"high{b}": None if p is None else p["high"][0] for b, p in part.items()})
    return out


def quintile_table(frame: pd.DataFrame) -> dict:
    """Primary measures by ATM30 quintile. The cut points use the whole sample, so this is hindsight and is descriptive."""
    rows = frame[frame["valid"]]
    z, positions, atm = rows["z"].to_numpy(), rows["position"].to_numpy(), rows["atm30"].to_numpy()
    order = np.argsort(atm, kind="stable")
    group = np.empty(len(z), dtype=int)
    for number, part in enumerate(np.array_split(order, 5)):
        group[part] = number
    out = dict(groups=[])
    for number in range(5):
        use = group == number
        table = cc.measure_table(z[use], positions[use])
        out["groups"].append(dict(quintile=number + 1, low_atm30=float(atm[use].min()), high_atm30=float(atm[use].max()), **table))

    def contrast(index):
        hits, chosen = np.abs(z[index]) < 1, group[index]
        return np.array([hits[chosen == 0].mean() - hits[chosen == 4].mean()])

    part = cc.intervals_for(contrast, positions)
    out["lowest_minus_highest_inner"] = dict(value=float(contrast(np.arange(len(z)))[0]), **{f"low{b}": float(p["low"][0]) for b, p in part.items()}, **{f"high{b}": float(p["high"][0]) for b, p in part.items()})
    paso = one_event(frame, ev.EVENTS, "2019 PASO")[frame["valid"].to_numpy()]
    out["lowest_inner_no_2019_paso"] = float(np.mean(np.abs(z[(group == 0) & ~paso]) < 1))
    out["lowest_rows_in_2019_paso"] = int(((group == 0) & paso).sum())
    return out


def year_table(frame: pd.DataFrame) -> dict:
    rows = frame[frame["valid"]]
    return {str(year): dict(n=len(part), inner=float(np.mean(np.abs(part["z"]) < 1)), outer=float(np.mean(np.abs(part["z"]) < 2)), mean_z2=float(np.mean(part["z"] ** 2))) for year, part in rows.groupby(rows["session_date"].dt.year)}


def selection_table(frame: pd.DataFrame) -> dict:
    """Outcomes on rows with a complete window and a blank ATM30, against valid rows. Half days are left out."""
    complete = frame["R"].notna().to_numpy()
    blank = complete & frame["atm30"].isna().to_numpy() & ~frame["flag_half_day"].to_numpy(dtype=bool)
    valid = frame["valid"].to_numpy()
    use = blank | valid
    R, is_blank, positions = frame["R"].to_numpy()[use], blank[use], frame["position"].to_numpy()[use]
    big = cc.move_happened(R, 0.20)

    def difference(index):
        return np.array([big[index][is_blank[index]].mean() - big[index][~is_blank[index]].mean()])

    part = cc.intervals_for(difference, positions)
    return dict(blank_rows=int(is_blank.sum()), valid_rows=int((~is_blank).sum()), big_move_blank=float(big[is_blank].mean()), big_move_valid=float(big[~is_blank].mean()), mean_abs_R_blank=float(np.abs(R[is_blank]).mean()), mean_abs_R_valid=float(np.abs(R[~is_blank]).mean()), difference=float(difference(np.arange(len(R)))[0]), **{f"low{b}": float(p["low"][0]) for b, p in part.items()}, **{f"high{b}": float(p["high"][0]) for b, p in part.items()})


def actual_window_table(frame: pd.DataFrame) -> dict:
    """The primary measures with T from the actual days to the last session in the window, not the fixed 30 days."""
    rows = frame[frame["valid"]]
    days = (rows["outcome_end"] - rows["session_date"]).dt.days.to_numpy(dtype=float)
    T = days / 365
    s = rows["atm30"].to_numpy() * np.sqrt(T)
    z = (rows["R"].to_numpy() - (rows["r"].to_numpy() * T - s ** 2 / 2)) / s
    return dict(mean_days=float(days.mean()), inner=float(np.mean(np.abs(z) < 1)), outer=float(np.mean(np.abs(z) < 2)), mean_z2=float(np.mean(z ** 2)))


def tail_shape(frame: pd.DataFrame, common_nu: np.ndarray) -> dict:
    z = frame.loc[frame["valid"], "z"].to_numpy()
    values, counts = np.unique(common_nu, return_counts=True)
    return dict(median_abs_z_over_normal=float(np.median(np.abs(z)) / cc.stats.norm.ppf(0.75)), nu_counts={str(v): int(c) for v, c in zip(values, counts)}, half_width_95_at_nu={str(nu): float(cc.stats.t.ppf(0.5 + cc.OUTER / 2, nu) * cc.unit_t_scale(nu)) for nu in (5.0, 6.0)}, half_width_95_normal=float(cc.stats.norm.ppf(0.5 + cc.OUTER / 2)))


def k_without_paso(frame: pd.DataFrame, common: np.ndarray) -> dict:
    """Scaled ATM30 with the 2019 PASO windows out of the k fit. This uses hindsight, so it is a sensitivity and not a benchmark."""
    paso = one_event(frame, ev.EVENTS, "2019 PASO")
    changed = frame.copy()
    changed["valid"] = frame["valid"].to_numpy() & ~paso
    k = np.full(len(frame), np.nan)
    z2 = np.where(changed["valid"], frame["z"].to_numpy(dtype=float) ** 2, 0.0)
    total, count = np.concatenate([[0.0], np.cumsum(z2)]), np.concatenate([[0], np.cumsum(changed["valid"])])
    ends = cc.past_end_positions(frame)
    use = common & (count[ends] > 0)
    k[use] = np.sqrt(total[ends[use]] / count[ends[use]])
    R, r, s = frame["R"].to_numpy()[common], frame["r"].to_numpy()[common], frame["s"].to_numpy()[common]
    pred, base = cc.normal_band(r, k[common] * s), cc.normal_band(r, s)
    hits = cc.hit_rows(pred, R)
    scores, base_scores = cc.row_scores(pred, R), cc.row_scores(base, R)
    z = (R - pred.loc) / pred.s
    return dict(median_k=float(np.median(k[common])), inner=float(hits["inner"].mean()), outer=float(hits["outer"].mean()), mean_z2=float(np.mean(z ** 2)), score_differences={key: float((scores[key] - base_scores[key]).mean()) for key in scores})


def main() -> None:
    frame = run.load_period("open")
    results = {}
    names = [name for name, _ in ev.EVENTS]
    by_event = {}
    for name in names:
        inside = one_event(frame, ev.EVENTS, name)
        z, _ = run.rows_of(frame, inside)
        by_event[name] = dict(n=len(z), share_of_all_z2=float(np.sum(z ** 2) / np.nansum(frame.loc[frame["valid"], "z"] ** 2)), inner=float(np.mean(np.abs(z) < 1)), outer=float(np.mean(np.abs(z) < 2)), mean_z=float(z.mean()), mean_z2=float(np.mean(z ** 2)))
    results["by_event"] = by_event
    paso = one_event(frame, ev.EVENTS, "2019 PASO")
    results["no_2019_paso"] = cc.measure_table(*run.rows_of(frame, ~paso))
    rows = frame[frame["valid"].to_numpy() & ~paso]
    pred = cc.normal_band(rows["r"].to_numpy(), rows["s"].to_numpy())
    results["reliability_no_2019_paso"] = {str(x): dict(groups=cc.reliability_groups(pred.move_probability(x), cc.move_happened(rows["R"].to_numpy(), x)), brier=cc.brier(pred.move_probability(x), cc.move_happened(rows["R"].to_numpy(), x)).mean()) for x in cc.THRESHOLDS}
    results["brier_against_base_rate"] = base_rate_table(frame)
    results["atm30_quintiles"] = quintile_table(frame)
    results["by_year"] = year_table(frame)
    results["selection"] = selection_table(frame)
    results["actual_window"] = actual_window_table(frame)
    found, common = run.benchmark_predictives(frame)
    results["tail_shape"] = tail_shape(frame, found["nu"][common])
    results["k_without_2019_paso"] = k_without_paso(frame, common)
    run.save("post_result", results, run.require_freeze())
    print(json.dumps(run.to_plain(results), indent=1))


if __name__ == "__main__":
    main()
