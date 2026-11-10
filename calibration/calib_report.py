"""C4: write reports/calib_descriptive.md from the result files. The numbers come from the files. The wording is fixed text, so check it again if a result changes.

Run from the project folder: conda run --no-capture-output -n py4fi python calibration/calib_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"
INNER, OUTER = 0.6827, 0.9545


def pct(value, digits=1):
    return "n/a" if value is None else f"{100 * value:.{digits}f}%"


def span(row, block, digits=1, scale=100, suffix="%"):
    low, high = row.get(f"low{block}"), row.get(f"high{block}")
    if low is None or high is None:
        return "blank"
    return f"{scale * low:.{digits}f} to {scale * high:.{digits}f}{suffix}" if scale == 100 else f"{low:.{digits}f} to {high:.{digits}f}"


def table(header, rows):
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(lines)


def measure_rows(m):
    rows = []
    for key, label, nominal in (("inner", "Inner hit rate", "68.3%"), ("outer", "Outer hit rate", "95.4%"), ("down_tail", "Down-tail breach", "2.3%"), ("up_tail", "Up-tail breach", "2.3%")):
        rows.append([label, pct(m[key]["value"]), nominal, span(m[key], 21), span(m[key], 63)])
    for key, label, nominal in (("mean_z2", "Mean z squared", "1.00"), ("mean_abs_z", "Mean absolute z", "0.80")):
        rows.append([label, f"{m[key]['value']:.2f}", nominal, span(m[key], 21, 2, 1, ""), span(m[key], 63, 2, 1, "")])
    return rows


def cut_rows(cuts):
    rows = []
    for name, c in cuts.items():
        rows.append([name, c["n"], pct(c["inner"]["value"]), span(c["inner"], 63), pct(c["outer"]["value"]), span(c["outer"], 63), pct(c["down_tail"]["value"]), pct(c["up_tail"]["value"]), f"{c['mean_z2']['value']:.2f}"])
    return rows


def benchmark_rows(methods):
    rows = []
    for name, m in methods.items():
        rows.append([name, pct(m["inner"]["value"]), span(m["inner"], 63), pct(m["outer"]["value"]), span(m["outer"], 63), pct(m["down_tail"]["value"]), pct(m["up_tail"]["value"]), f"{m['mean_z2']:.2f}"])
    return rows


def score_rows(methods):
    rows = []
    for name, m in methods.items():
        if name == "ATM30":
            continue
        s = m["scores"]
        rows.append([name, *(f"{s[key]['difference']:+.4f} ({s[key]['low63']:+.4f} to {s[key]['high63']:+.4f})" for key in ("crps", "interval_inner", "interval_outer")), *(f"{m['brier'][x]['difference']:+.4f} ({m['brier'][x]['low63']:+.4f} to {m['brier'][x]['high63']:+.4f})" for x in ("0.1", "0.2"))])
    return rows


def reliability_rows(groups):
    return [[g["n"], pct(g["mean_probability"]), pct(g["observed"])] for g in groups]


def power_rows(synthetic):
    rows = []
    for row in synthetic["forward_power"]:
        months = round(row["sessions"] / 21)
        rows.append([row["sessions"], months, pct(row["no_error"]["verdict_fires"], 0), pct(row["no_error"]["cover21"], 0), pct(row["no_error"]["cover63"], 0), pct(row["bands_25pct_too_wide"]["verdict_fires"], 0), pct(row["wandering_error"]["verdict_fires"], 0), pct(row["wandering_error"]["cover63"], 0)])
    return rows


def main():
    results = json.loads((REPORTS / "calib_results.json").read_text(encoding="utf-8"))
    synthetic = json.loads((REPORTS / "calib_synthetic.json").read_text(encoding="utf-8"))
    manifest = json.loads((REPORTS / "calib_freeze_manifest.json").read_text(encoding="utf-8"))
    c1, c2, c3, post = results["c1"], results["c2"], results["c3"], results["post_result"]
    m = c2["measures"]
    bench = c3["benchmarks"]
    methods = bench["methods"]
    cuts = c3["cuts"]
    paso = post["no_2019_paso"]
    base = post["brier_against_base_rate"]
    full = synthetic["coverage_full_sample"]
    worst = post["by_event"]
    q, years, shape, selection, actual, k_out = post["atm30_quintiles"], post["by_year"], post["tail_shape"], post["selection"], post["actual_window"], post["k_without_2019_paso"]
    qs = q["groups"]
    nu_low = sum(count for value, count in shape["nu_counts"].items() if float(value) <= 6)
    outside = sum(not (low <= 0.10 <= high) for low, high in zip(c2["pit"]["low63"], c2["pit"]["high63"]))
    pit_note = "Every bin interval includes 10% under 63-session blocks." if outside == 0 else f"{outside} bin intervals exclude 10% under 63-session blocks."
    text = f"""# GGAL implied move calibration: descriptive results

**Status:** {results['status']} Results stay local under the Databento license. The rules are in `CALIBRATION_PLAN.md`. `reports/calib_results.json` holds all numbers. The manifest was written at {manifest['written_at']}, before any calibration result. Changed since the freeze, at the last run: {results['changed_since_freeze'] or 'none'}. After that run, the plan text changed once, to record the owner's horizon (`reports/calib_horizon.json`).

## Main reading

On open data, pooled coverage of the ATM30 band is near nominal, but this average hides offsetting errors. The inner hit rate is {pct(m['inner']['value'])} against 68.3%, and the outer hit rate is {pct(m['outer']['value'])} against 95.4%. Both intervals include the nominal value under both block sizes. So the pooled result does not show that the move probabilities are right at each origin.

- **The error depends on the level of ATM30 (post-result).** The inner rate is {pct(qs[0]['inner']['value'])} in the lowest ATM30 quintile ({span(qs[0]['inner'], 63)}), and {pct(qs[3]['inner']['value'])} and {pct(qs[4]['inner']['value'])} in the top two. The lowest minus the highest is {100 * q['lowest_minus_highest_inner']['value']:.1f} points ({100 * q['lowest_minus_highest_inner']['low63']:.1f} to {100 * q['lowest_minus_highest_inner']['high63']:.1f}). The lowest quintile has {q['lowest_rows_in_2019_paso']} rows in the 2019 PASO windows, so that event does not explain this result. The cut points use hindsight.
- **The error also changes with time.** The yearly inner rate runs from {pct(min(v['inner'] for v in years.values()))} to {pct(max(v['inner'] for v in years.values()))} (post-result).
- **This does not prove calibration, even when pooled.** The inner interval is about {100 * (m['inner']['high63'] - m['inner']['low63']):.0f} points wide, and the method was developed on this same period.
- **The "95%" intervals are too narrow.** In the frozen simulation, they hold the true inner rate in about {100 * min(full['wandering']['cover21'], full['constant']['cover21']):.0f}% to {100 * max(full['wandering']['cover63'], full['constant']['cover63']):.0f}% of runs at this sample size. The review's own simulation gives about 89% to 92% for the outer rate and 84% to 91% for mean z squared. It rests on one assumed jump model.
- **Large moves carry the excess.** Mean z squared is {m['mean_z2']['value']:.2f}, with an interval of {span(m['mean_z2'], 63, 2, 1, '')}. It is {cuts['No event in window']['mean_z2']['value']:.2f} on {cuts['No event in window']['n']} origins with no event in the window, and {cuts['Event in window']['mean_z2']['value']:.2f} on {cuts['Event in window']['n']} origins with an event. These {cuts['Event in window']['n']} origins cover only {len(worst)} events.
- **The centre shows no level error (post-result).** Median absolute z is {shape['median_abs_z_over_normal']:.3f} times its normal value. So the excess in mean z squared comes from the tails, and not from a band that is too narrow everywhere.
- **One event has a large effect (post-result).** Without the 2019 PASO windows, mean z squared is {paso['mean_z2']['value']:.2f} and the outer hit rate is {pct(paso['outer']['value'])}.
- **No score difference is shown for two benchmarks.** On {bench['rows']} common rows, intervals include zero for HAR with no factor and fat-tailed ATM30. This does not show that they are equal, and their coverage differs from ATM30. HAR with the Duan factor and scaled ATM30 have wider bands and worse inner interval scores.
- **No gain over a past base rate is shown (post-result).** At the 10% threshold, ATM30 has a Brier score of {base['0.1']['atm30']:.4f}, and a past base rate has {base['0.1']['past_base_rate']:.4f}. At the 20% threshold, the scores are {base['0.2']['atm30']:.4f} and {base['0.2']['past_base_rate']:.4f}. Both differences have intervals that include zero, so a modest gain is not excluded.

**Caution:** A miss under real-world probabilities is not automatically a market error. Implied bands are risk-neutral and include the variance risk premium. This study cannot separate that premium from a forecast error.

## Primary measures

All open data, events included, Tier 1 and Tier 2, {m['n']} origins from {c1['open']['first_valid']} to {c1['open']['last_valid']}. Intervals are 95% block bootstrap percentile intervals.

{table(['Measure', 'Value', 'If calibrated', '21-session blocks', '63-session blocks'], measure_rows(m))}

Mean z is {c2['mean_z']:.3f}, and the standard deviation of z is {c2['sd_z']:.3f}. Tail results are descriptive, because each 2-sigma tail expects only about 2 to 3 cases in about 102 independent months.

**Fixed-step samples.** These samples share periods, so they are not independent of each other.

{table(['Step', 'Samples', 'Median rows', 'Inner: mean (range)', 'Outer: mean (range)', 'Mean z squared: mean (range)'], [[f['step'], f['samples'], f['median_n'], f"{pct(f['inner']['mean'])} ({pct(f['inner']['min'])} to {pct(f['inner']['max'])})", f"{pct(f['outer']['mean'])} ({pct(f['outer']['min'])} to {pct(f['outer']['max'])})", f"{f['mean_z2']['mean']:.2f} ({f['mean_z2']['min']:.2f} to {f['mean_z2']['max']:.2f})"] for f in c2['fixed_steps']])}

**PIT.** Shares per bin, from low to high: {', '.join(pct(v) for v in c2['pit']['shares'])}. {pit_note} See `reports/calib_figures/pit_histogram.png`.

## Coverage by ATM30 level and by year (post-result)

The quintile cut points use the whole sample, so this is hindsight. The intervals use 63-session blocks.

{table(['ATM30 quintile', 'ATM30 range', 'Rows', 'Inner', 'Interval', 'Outer', 'Interval', 'Mean z squared'], [[g['quintile'], f"{g['low_atm30']:.2f} to {g['high_atm30']:.2f}", g['n'], pct(g['inner']['value']), span(g['inner'], 63), pct(g['outer']['value']), span(g['outer'], 63), f"{g['mean_z2']['value']:.2f}"] for g in qs])}

{table(['Year', 'Rows', 'Inner', 'Outer', 'Mean z squared'], [[year, v['n'], pct(v['inner']), pct(v['outer']), f"{v['mean_z2']:.2f}"] for year, v in years.items()])}

## Reliability of implied move probabilities

The groups are 5 equal-count groups by implied probability, on all {m['n']} origins. Inside each group, the rows overlap in time.

**Moves beyond 10%.** Brier score {c2['reliability']['0.1']['brier']:.4f}.

{table(['Rows', 'Mean forecast', 'Observed'], reliability_rows(c2['reliability']['0.1']['groups']))}

**Moves beyond 20%.** Brier score {c2['reliability']['0.2']['brier']:.4f}.

{table(['Rows', 'Mean forecast', 'Observed'], reliability_rows(c2['reliability']['0.2']['groups']))}

The observed share does not rise steadily with the forecast. The lowest group has more moves than it forecasts, and the highest group has fewer. This shape stays without the 2019 PASO windows (post-result).

**Base-rate reference (post-result).** On {base['0.1']['rows']} rows. A negative difference favours ATM30. The hindsight rate uses the whole sample, so no forecaster could have it.

{table(['Threshold', 'ATM30', 'Past base rate', 'Hindsight base rate', 'ATM30 minus past', '63-session blocks'], [[f"{int(float(x) * 100)}%", f"{base[x]['atm30']:.4f}", f"{base[x]['past_base_rate']:.4f}", f"{base[x]['hindsight_base_rate']:.4f}", f"{base[x]['atm_minus_past']:+.4f}", f"{base[x]['low63']:+.4f} to {base[x]['high63']:+.4f}"] for x in ('0.1', '0.2')])}

## Benchmarks on common rows

{bench['rows']} rows, from {bench['first_origin']} to {bench['last_origin']}. Past-only k has a median of {bench['k']['median']:.2f}, and past-only degrees of freedom have a median of {bench['nu']['median']:.0f}.

{table(['Method', 'Inner', '63-session blocks', 'Outer', '63-session blocks', 'Down', 'Up', 'Mean z squared'], benchmark_rows(methods))}

**Score differences.** Each cell is the benchmark minus ATM30, with the 63-session interval. A negative value favours the benchmark.

{table(['Method', 'CRPS', 'Interval score, 68%', 'Interval score, 95%', 'Brier, 10%', 'Brier, 20%'], score_rows(methods))}

**Reading.**
- **Scaled ATM30:** the scale overshoots, and mean z squared falls to {methods['Scaled ATM30']['mean_z2']:.2f}. The inner rate rises to {pct(methods['Scaled ATM30']['inner']['value'])}. The 2019 PASO inflates k. With those windows out of the k fit, median k is {k_out['median_k']:.2f}, the inner rate is {pct(k_out['inner'])}, and mean z squared is {k_out['mean_z2']:.2f}. This sensitivity uses hindsight, so it is not a benchmark. The worse scores of scaled ATM30 depend largely on this event.
- **Fat-tailed ATM30:** a unit-variance t has almost the same 2-sigma quantile as a normal: {shape['half_width_95_at_nu']['5.0']:.2f} at 5 degrees of freedom, against {shape['half_width_95_normal']:.2f}. So its outer hit rate is close to ATM30 by construction, and this benchmark has almost no power to test tails at 2 sigma. Its inner rate falls because a unit-variance t is narrower in the centre.
- **Fitted tails:** past-only degrees of freedom are 6 or fewer on {nu_low} of {bench['rows']} rows. This points to fat tails, but the fit fixes the variance at one and the rows overlap.
- **Mean z squared:** fat-tailed ATM30 uses the same s, so this value equals the ATM30 value.

## Subsamples and robustness

These cuts are secondary and sit beside the primary result. Intervals use 63-session blocks. A blank interval means that the block is more than a third of the span.

{table(['Cut', 'Rows', 'Inner', 'Interval', 'Outer', 'Interval', 'Down', 'Up', 'Mean z squared'], cut_rows(cuts))}

- **Not run:** the American-exercise cut, because the tree sensitivity is not done.
- **2016-01 to 2018-04:** this period is development data now, and it is calmer. It has {cuts['2016-01 to 2018-04']['n']} origins with Alpaca closes, and it does not confirm the open-data result.
- **Timing gap:** the 15:45 start changes the inner rate from {pct(cuts['Same rows as the 15:45 start, at the close']['inner']['value'])} to {pct(cuts['Start at the 15:45 stock mid']['inner']['value'])}.
- **Centre:** a zero centre changes the inner rate from {pct(m['inner']['value'])} to {pct(cuts['Centre at zero']['inner']['value'])}.

**By event (post-result).** Rows inside one event overlap heavily, so each event is about one independent case.

{table(['Event', 'Origins', 'Inner', 'Outer', 'Mean z', 'Mean z squared', 'Share of all z squared'], [[name, v['n'], pct(v['inner']), pct(v['outer']), f"{v['mean_z']:.2f}", f"{v['mean_z2']:.2f}", pct(v['share_of_all_z2'])] for name, v in worst.items()])}

## Method checks

- **Synthetic run:** with a known vol, all six measures match their nominal values within simulation error. See `reports/calib_synthetic_pipeline.json`.
- **Alignment:** a planted jump catches a one-session shift of the outcome, in both directions.
- **Row counts:** {c1['open']['valid_z']} open rows are the {c1['open']['primary_rows']} primary rows plus {c1['open']['valid_not_primary']} rows with no HAR inputs. The largest gap between the rebuilt RV30 window and the study's RV30 is {c1['open']['largest_rv30_identity_gap']:.1e}. No half day has an ATM30 value.

**How far to trust the intervals.** This simulation uses the frozen rules on simulated prices, with 300 runs and 500 resamples per block. Constant vol is the kindest case. The wandering case adds a slow error to the implied vol. Real data can differ from both. The review found that the true inner rate in the constant case is about 68.8% on this grid, not the 68.3% in the table. The effect on the coverage is small.

{table(['Case, about 2,100 sessions', 'True inner rate', 'Cover, 21-session blocks', 'Cover, 63-session blocks'], [['Constant vol', pct(full['constant']['true_inner']), pct(full['constant']['cover21'], 0), pct(full['constant']['cover63'], 0)], ['Wandering implied-vol error', pct(full['wandering']['true_inner']), pct(full['wandering']['cover21'], 0), pct(full['wandering']['cover63'], 0)]])}

## Forward test

The rules are frozen, and no forward data has been read. The owner fixed the horizon at 36 months: origins from 2026-10-30 through the first origin on or after 2029-10-30. So the earliest verdict is about 2029-11-29, when the last window closes. With about 86% of sessions usable, this gives about 650 rows, so the simulated power against bands 25% too wide lies between the 504-row and the 756-row lines below.

The table shows how the verdict rule behaves in simulation at each horizon. With no error, a higher share means more false alarms. "Fires" is the share of runs in which the rule says "Miscalibrated".

**Read this table with care.**
- "Rows" means consecutive rows. Real data has a value on about 86% of sessions, so each row count takes longer on the calendar.
- The wandering case has a true inner rate near nominal, so its "Fires" column shows mostly false alarms and not power.
- The review simulated the outer rate at 252 rows, and its intervals cover only about 60%. So the 12-month look gives very unreliable outer intervals.
- The plan's standard errors of 4.6 and 9.5 points are too high against the simulated widths. Do not reuse them.

{table(['Rows', 'About months', 'Fires, no error', 'Cover 21, no error', 'Cover 63, no error', 'Fires, bands 25% too wide', 'Fires, wandering error', 'Cover 63, wandering error'], power_rows(synthetic))}

## Limits

- All results here are exploratory. Open data shaped the ATM30 method, and only data after 2026-10-29 can confirm a result.
- ATM30 is a single near-the-money volatility, so a normal band ignores skew by design.
- Open data mixes calm years, crises, and the 2025-03 format break. One pooled hit rate can hide offsetting errors, as the rolling figure shows.
- Selection: an origin has no z when ATM30 is blank. On {selection['blank_rows']} such rows with a complete window, moves above 20% occur in {pct(selection['big_move_blank'])}, against {pct(selection['big_move_valid'])} on valid rows ({100 * selection['low63']:.1f} to {100 * selection['high63']:.1f} points of difference). So the pooled coverage may be overstated.
- Fixed T: the plan uses T = 30/365, but real windows average {actual['mean_days']:.2f} days to the last session. With the real length, the inner rate is {pct(actual['inner'])} and mean z squared is {actual['mean_z2']:.2f} (post-result).
- Black inversion on American options with dividends can bias IV. This is not measured here.
- Post-result checks came after the results. They can suggest ideas for a later test, but they confirm nothing. Several lines in the main reading rest on them, and each one carries the label.
- The rolling and reliability figures were drawn after the results.
- `reports/calib_results.json` also holds what the tables leave out: 21-session intervals of the cuts, mean absolute z of the cuts, and fixed steps of 2016-2018.

## Figures

- `reports/calib_figures/pit_histogram.png`
- `reports/calib_figures/reliability.png` (common rows)
- `reports/calib_figures/rolling_hit_rate.png`
- `reports/calib_figures/z_over_time.png`
"""
    (REPORTS / "calib_descriptive.md").write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {REPORTS / 'calib_descriptive.md'}")


if __name__ == "__main__":
    main()
