"""The technical calibration report. Run from the project folder, with reportlab on PYTHONPATH."""
import hashlib

import calib_common as f
import common as c
from calib_common import BENCH, C1, C2, C3, CUTS, HORIZON, M, MANIFEST_TEXT, METHODS, POST, Q, QS, SYN, nspan, pct, span

f.check_claims()
c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
FIG = c.FIGURES
f.pit_chart(FIG / "calib_pit.png")
f.quintile_chart(FIG / "calib_quintiles.png")
f.z_chart(FIG / "calib_z.png")
f.rolling_chart(FIG / "calib_rolling.png")
f.reliability_chart(FIG / "calib_reliability.png", compare=True)
f.benchmark_chart(FIG / "calib_benchmarks.png")
f.forward_timeline(FIG / "calib_forward.png")

I = "<font name='Serif-Italic'>%s</font>"
base = POST["brier_against_base_rate"]
paso = POST["no_2019_paso"]
shape, selection, actual, k_out = POST["tail_shape"], POST["selection"], POST["actual_window"], POST["k_without_2019_paso"]
years = POST["by_year"]
full = SYN["coverage_full_sample"]
manifest_hash = hashlib.sha256(MANIFEST_TEXT).hexdigest()
nu_low = sum(count for value, count in shape["nu_counts"].items() if float(value) <= 6)
no_event, event = CUTS["No event in window"], CUTS["Event in window"]
assert manifest_hash == HORIZON["manifest_sha256"]

p = c.Paper("Serif", 9.2, "Is the GGAL ADR implied move calibrated?", f.FOOTER, c.HERE / "GGAL_calibration_technical.pdf")

p.add("Is the GGAL ADR implied move calibrated?", "title")
p.add("Coverage, shape, and benchmark evidence on development data, with a frozen forward test. Working paper, draft of 2026-11-05, prepared with Claude Code from the project records. Not peer reviewed.", "subtitle")
p.add("<b>Revision history.</b> " + f.REVISION_NOTE + " No calibration result changed. The edits concern wording on the HAR label, exercise style and dividends, wide quotes, and interval labels.", "subtitle")
p.add("Abstract", "h2")
p.add(f"We read {I % 'ATM30'}, a 30-day near-the-money implied volatility, as a risk-neutral normal distribution of the 30-day total log return of the GGAL ADR, and we test its calibration. On {M['n']:,} daily origins from 2018-05 to 2026-09, the inner (|z| &lt; 1) hit rate is {pct(M['inner']['value'])} against {pct(f.INNER)}, with a 63-session block-bootstrap interval of {span(M['inner'])}. The outer (|z| &lt; 2) hit rate is {pct(M['outer']['value'])} against {pct(f.OUTER)} ({span(M['outer'])}), and mean z² is {M['mean_z2']['value']:.2f} ({nspan(M['mean_z2'])}). Pooled coverage is therefore near nominal, but this hides offsetting errors. In post-result cuts, the inner rate is {pct(QS[0]['inner']['value'])} in the lowest {I % 'ATM30'} quintile and {pct(QS[3]['inner']['value'])} and {pct(QS[4]['inner']['value'])} in the top two, and mean z² is {no_event['mean_z2']['value']:.2f} on origins with no event in the window against {event['mean_z2']['value']:.2f} with one. No benchmark clearly beats {I % 'ATM30'} on scores, and implied move probabilities show no gain over a past base rate. All results are exploratory. A frozen 36-month forward test is the only route to confirmation.")

p.add("1. Introduction", "h1")
p.add(f"The main study asks if {I % 'ATM30'} adds information about 30-day realized variance beyond a HAR baseline. Its one-time test ended \"Inconclusive\". This side investigation asks a separate question: are the level and shape of the implied distribution right? Information and calibration can differ. A series can rank future variance well and still give wrong probabilities.")
p.add("This work does not change the Stage 5 result, and it is not a second test of that period. Calibration here means unconditional coverage plus descriptive conditional cuts, in the spirit of density-forecast evaluation (Diebold, Gunther and Tay, 1998) and proper scoring (Gneiting and Raftery, 2007). Skew and model-free distributions are out of scope for the primary series, because deep out-of-the-money quotes are rare before 2024. Trading rules are out of scope.")
p.callout("Status of the evidence: open data shaped the method, and 2016-01 to 2018-04 has been used once by the frozen test. So every result here is development evidence. Only data from after 2026-10-29 can confirm a result. Items marked post-result were chosen after C2 and C3 results existed.", edge=c.ORANGE)

p.add("2. Data", "h1")
p.table([
    ["Input", "Source", "Use"],
    [I % "ATM30" + ", tier, flags", I % "data/forecast_panel.parquet" + ", " + I % "data/test/test_panel.parquet", "Band width and cuts"],
    ["Total-return closes", "Official daily table (open), Alpaca (2016-18), with " + I % "adr_cash_events.csv", "30-day outcome, with the same returns as RV30"],
    ["DGS1MO", "FRED, " + I % "session_rates" + " and " + I % "rate_for" + " at 30 days", "Drift. Last observation before the session"],
    ["HAR forecasts", I % "forecasts.expanding_forecasts", "Benchmark band"],
    ["Stock mid at 15:45", I % "data/session_diagnostics.parquet", "Timing sensitivity, open data only"],
    ["Event list", I % "events.EVENTS" + " and " + I % "TEST_EVENTS", "Event cuts"],
], [1.5, 3.2, 2.2], "<b>Table 1. Inputs.</b> No new data was fetched.")
o, t = C1["open"], C1["test"]
p.table([
    ["Period", "Sessions", "ATM30 days", "Complete windows", "Valid z", "Tier 1", "Tier 2", "Half days with ATM30"],
    ["Open, 2018-05 to 2026-10", f"{o['sessions']:,}", f"{o['atm30_days']:,}", f"{o['rv30_days']:,}", f"{o['valid_z']:,}", f"{o['tier1_valid']:,}", o["tier2_valid"], o["half_days_with_atm30"]],
    ["2016-01 to 2018-04", t["sessions"], t["atm30_days"], t["rv30_days"], t["valid_z"], t["tier1_valid"], t["tier2_valid"], t["half_days_with_atm30"]],
], [2.2, .95, .9, 1, .8, .7, .7, 1.1], f"<b>Table 2. Row reconciliation.</b> The {o['valid_z']:,} open rows are the study's {o['primary_rows']:,} primary rows plus {o['valid_not_primary']} rows with no HAR inputs. The rebuilt window matches study RV30 with a largest gap of {o['largest_rv30_identity_gap']:.1f}, and no window length differs. The two periods are never pooled.")

p.add("3. Method", "h1")
p.add("3.1 Standardized move", "h2")
p.add("With T = 30/365, band width s and centre m, the outcome R is the sum of total log returns on sessions in (t, t + 30 calendar days]:")
p.add("s<sub>t</sub> = ATM30<sub>t</sub> √T, &nbsp;&nbsp; m<sub>t</sub> = r<sub>t</sub> T − s<sub>t</sub>²/2, &nbsp;&nbsp; z<sub>t</sub> = (R<sub>t</sub> − m<sub>t</sub>) / s<sub>t</sub>", "equation")
p.add("Dividends are inside the total return, so the centre needs no forward adjustment. The owner chose the risk-neutral centre, the 16:00 close as the start, Tier 2 days in the primary sample, and thresholds of 10% and 20%. Nothing is imputed, half days have no z, and windows past the last session stay blank.")
p.table([
    ["Measure", "Definition", "If calibrated"],
    ["Inner hit rate (primary)", "share with |z| &lt; 1", pct(f.INNER)],
    ["Outer hit rate (primary)", "share with |z| &lt; 2", pct(f.OUTER)],
    ["Down-tail and up-tail breach", "share with z &lt; −2, share with z &gt; 2", "2.3% each"],
    ["Mean z², mean |z|", "averages", "1.00, 0.80"],
    ["PIT", "u = Φ(z), 10 equal bins", "10% per bin"],
    ["Reliability", "Implied P(|exp(R) − 1| &gt; x) for x = .10, .20, in 5 equal-count groups, with a Brier score (Brier, 1950)", "Forecast = observed"],
], [2.2, 3.8, 1], "<b>Table 3. Measures.</b> One primary result: inner and outer hit rates on all open data, events included.")
p.add("3.2 Benchmarks", "h2")
p.add("All benchmarks use past rows only: a position before the origin and a window end on or before the origin date. They need position 252 and 126 past rows. Comparisons use the rows where every method has a value.")
p.bullets([
    "<b>HAR band.</b> s = √(f T), with f from the expanding log regression of RV30 on HAR-type inputs, which are squared daily returns over 1, 5, and 22 sessions (after Corsi, 2009, who uses intraday realized variance), with and without the Duan (1983) factor. The centre rule is the same.",
    "<b>Scaled ATM30.</b> k² is the past mean of z². The band uses ks, and the centre uses the new s.",
    "<b>Fat-tailed ATM30.</b> The same s and m, with a unit-variance Student-t. Degrees of freedom come from a grid likelihood on past z, refit at each origin. The past rows overlap, so this is a working fit.",
    "<b>Scores.</b> Interval score (Gneiting and Raftery, 2007) at coverages .6827 and .9545, CRPS in log-return units with the closed form of Jordan, Krüger and Lerch (2019) for the t, and Brier scores. Differences are the benchmark minus ATM30.",
])
p.add("3.3 Inference", "h2")
p.add("Daily origins overlap by about 21 sessions, so open data holds about 102 independent months. Intervals are nominal 95% percentile intervals from circular blocks (Politis and Romano, 1992) of 21 and 63 sessions on the full session grid, with 2,000 resamples, as in the study. A block longer than a third of the span stays blank. Fixed-step samples of 22 and 23 sessions are reported. They share periods, so they are not independent of each other. Tails expect only about 2 to 3 cases per side, so tail results are descriptive.")

p.add("4. Validation", "h1")
p.bullets([
    "<b>Synthetic pipeline.</b> On simulated prices with a known vol, all six measures match nominal within four simulation standard errors (200 runs). The review found that the exact inner rate on this calendar grid is about 68.8%, because real windows are shorter than 30 days. That tolerance cannot see the gap.",
    "<b>Alignment.</b> A planted jump defines exactly which origins must see it. Both one-session shifts of the outcome fail this check, in a unit test. All 30 unit tests pass.",
    "<b>Closed forms.</b> Normal and t CRPS match numerical integration in the tests.",
    "<b>Independent rebuild (review).</b> R rebuilt from raw closes and the cash file on 400 rows differs by 0.0. Replacing later outcomes at sampled origins does not change k, ν, HAR, or the past base rate.",
])
p.table([
    ["Case, about 2,100 rows", "True inner rate", "Cover, 21 blocks", "Cover, 63 blocks"],
    ["Constant vol", pct(full["constant"]["true_inner"]), pct(full["constant"]["cover21"], 0), pct(full["constant"]["cover63"], 0)],
    ["Slowly wandering implied-vol error", pct(full["wandering"]["true_inner"]), pct(full["wandering"]["cover21"], 0), pct(full["wandering"]["cover63"], 0)],
], [3, 1.2, 1.2, 1.2], "<b>Table 4. Real coverage of the nominal 95% interval for the inner rate.</b> 300 runs, 500 resamples per block. Simulation only: real data can differ. The stated truth for constant vol is the nominal value and not the exact 68.8%, with a small effect. The review's own simulation, with one assumed jump model, gives about 89% to 92% for the outer rate and 84% to 91% for mean z². The session did not rerun that simulation.")

p.add("5. Primary results", "h1")
p.callout("All results in Sections 5 to 8 are exploratory.", edge=c.ORANGE)
p.table([
    ["Measure", "Value", "If calibrated", "Interval, 21 blocks", "Interval, 63 blocks"],
    ["<b>Inner hit rate</b>", f"<b>{pct(M['inner']['value'])}</b>", pct(f.INNER), span(M["inner"], 21), span(M["inner"])],
    ["<b>Outer hit rate</b>", f"<b>{pct(M['outer']['value'])}</b>", pct(f.OUTER), span(M["outer"], 21), span(M["outer"])],
    ["Down-tail breach", pct(M["down_tail"]["value"]), "2.3%", span(M["down_tail"], 21), span(M["down_tail"])],
    ["Up-tail breach", pct(M["up_tail"]["value"]), "2.3%", span(M["up_tail"], 21), span(M["up_tail"])],
    ["Mean z²", f"{M['mean_z2']['value']:.2f}", "1.00", nspan(M["mean_z2"], 21), nspan(M["mean_z2"])],
    ["Mean |z|", f"{M['mean_abs_z']['value']:.2f}", "0.80", nspan(M["mean_abs_z"], 21), nspan(M["mean_abs_z"])],
], [2.2, .9, 1, 1.5, 1.5], f"<b>Table 5. Primary measures, open data, {M['n']:,} origins, {C1['open']['first_valid']} to {C1['open']['last_valid']}.</b> Mean z is {C2['mean_z']:.3f}, and the SD of z is {C2['sd_z']:.3f}. Fixed-step mean inner is {pct(C2['fixed_steps'][0]['inner']['mean'])} for both steps, with ranges of {pct(C2['fixed_steps'][0]['inner']['min'])} to {pct(C2['fixed_steps'][0]['inner']['max'])} (22) and {pct(C2['fixed_steps'][1]['inner']['min'])} to {pct(C2['fixed_steps'][1]['inner']['max'])} (23).")
p.add("Both primary intervals include the nominal value under both block sizes, and every PIT bin interval includes 10%. The result is a failure to detect a pooled error. It is not a demonstration of calibration. The next sections show why the pooled number is not a sufficient answer to the question.")
p.figure(FIG / "calib_pit.png", "<b>Figure 1. PIT histogram.</b> Bars are bin shares, with 63-session intervals. The mild tilt to the upper half is within the intervals.", 2.7 / 7.2)
p.figure(FIG / "calib_z.png", "<b>Figure 2. z over time.</b> Solid lines: ±2. Dashed lines: ±1. Adjacent points share most of their returns. The five largest |z| values are all 2019 PASO origins.", 3.0 / 7.2)
p.figure(FIG / "calib_rolling.png", "<b>Figure 3. Rolling hit rates.</b> Trailing 365 days, with at least 126 rows, so early points hold about six months. This figure was drawn after the results.", 3.0 / 7.2)

p.add("6. Conditional evidence (post-result)", "h1")
p.callout("We chose these cuts after the results, and the quintile cut points use the whole sample. The review proposed the quintile cut, and the session reproduced it in " + I % "calibration/calib_post.py" + ". These results can suggest hypotheses, but they confirm nothing.", edge=c.ORANGE)
p.table([["Quintile", "ATM30", "Rows", "Inner", "Interval, 63 blocks", "Outer", "Interval, 63 blocks", "Mean z²"]] + [[g["quintile"], f"{g['low_atm30']:.2f} to {g['high_atm30']:.2f}", g["n"], pct(g["inner"]["value"]), span(g["inner"]), pct(g["outer"]["value"]), span(g["outer"]), f"{g['mean_z2']['value']:.2f}"] for g in QS], [.95, 1.2, .6, .8, 1.5, .8, 1.5, .8], f"<b>Table 6. Coverage by ATM30 quintile.</b> Lowest minus highest inner rate: {100 * Q['lowest_minus_highest_inner']['value']:.1f} points ({100 * Q['lowest_minus_highest_inner']['low63']:.1f} to {100 * Q['lowest_minus_highest_inner']['high63']:.1f}, 63-session blocks). The lowest quintile has {Q['lowest_rows_in_2019_paso']} rows in the 2019 PASO windows.")
p.figure(FIG / "calib_quintiles.png", "<b>Figure 4. Inner hit rate by ATM30 quintile, with 63-session intervals.</b> Only the lowest quintile lies entirely below nominal. Quintile 4 lies entirely above it under 63-session blocks.", 2.9 / 7.2)
p.add("The pattern fits a band that is too narrow when implied volatility is low and wider than needed when it is higher. One possible reading is that ATM30 moves more than later variance does. Another is that the low quintile reflects a few regimes, because ATM30 and calendar time are linked. We did not separate these readings.")
p.table([["Year"] + list(years), ["Rows"] + [v["n"] for v in years.values()], ["Inner"] + [pct(v["inner"]) for v in years.values()], ["Outer"] + [pct(v["outer"]) for v in years.values()], ["Mean z²"] + [f"{v['mean_z2']:.2f}" for v in years.values()]], [1.1] + [1] * len(years), "<b>Table 7. By origin year.</b> 2018 starts in May. 2026 ends in September.")
p.table([["Event", "Origins", "Inner", "Outer", "Mean z", "Mean z²", "Share of all z²"]] + [[name, v["n"], pct(v["inner"]), pct(v["outer"]), f"{v['mean_z']:.2f}", f"{v['mean_z2']:.2f}", pct(v["share_of_all_z2"])] for name, v in POST["by_event"].items()], [1.6, .7, .8, .8, .8, .8, 1.1], "<b>Table 8. By event.</b> Rows inside an event overlap heavily, so each event is about one independent case. Windows of adjacent events can share origins.")
p.bullets([
    f"<b>Centre of the distribution.</b> Median |z| is {shape['median_abs_z_over_normal']:.3f} times its normal value, so the centre shows no level error. The excess in mean z² comes from the tails.",
    f"<b>Without the 2019 PASO windows.</b> On {paso['n']:,} origins, mean z² is {paso['mean_z2']['value']:.2f} ({nspan(paso['mean_z2'])}), outer is {pct(paso['outer']['value'])}, and the down-tail breach is {pct(paso['down_tail']['value'])}. That one event is {pct(POST['by_event']['2019 PASO']['share_of_all_z2'])} of all z².",
    "<b>Events are mixed.</b> Three of nine events stayed inside the inner band on nearly all origins, while the 2019 PASO and both 2025 events did not. So ATM30 does not fail on all events.",
])

p.add("7. Probabilities and benchmarks", "h1")
p.add("7.1 Reliability", "h2")
r10, r20 = C2["reliability"]["0.1"], C2["reliability"]["0.2"]
p.table([["Group", "10%: forecast", "10%: observed", "20%: forecast", "20%: observed"]] + [[i + 1, pct(a["mean_probability"]), pct(a["observed"]), pct(b["mean_probability"]), pct(b["observed"])] for i, (a, b) in enumerate(zip(r10["groups"], r20["groups"]))], [.7, 1, 1, 1, 1], f"<b>Table 9. Reliability of ATM30, all {M['n']:,} origins.</b> Brier scores: {r10['brier']:.4f} and {r20['brier']:.4f}. Rows inside a group overlap in time. The lowest and highest group patterns stay without the 2019 PASO windows.")
p.table([["Threshold", "ATM30", "Past base rate", "Hindsight base rate", "ATM30 minus past", "63 blocks"]] + [[f"{int(float(x) * 100)}%", f"{base[x]['atm30']:.4f}", f"{base[x]['past_base_rate']:.4f}", f"{base[x]['hindsight_base_rate']:.4f}", f"{base[x]['atm_minus_past']:+.4f}", f"{base[x]['low63']:+.4f} to {base[x]['high63']:+.4f}"] for x in ("0.1", "0.2")], [.9, .9, 1.1, 1.3, 1.2, 1.7], f"<b>Table 10. Brier scores against a base rate (post-result), {base['0.1']['rows']:,} rows.</b> A negative difference favours ATM30. No forecaster could have the hindsight rate. No gain over the past base rate is shown, and a modest gain is not excluded.")
p.figure(FIG / "calib_reliability.png", f"<b>Figure 5. Reliability on {BENCH['rows']:,} common rows.</b> Forecast against observed share, in 5 equal-count groups per method. This figure was drawn after the results.", 3.3 / 7.2)
p.add("7.2 Benchmarks", "h2")
p.table([["Method", "Inner", "Interval", "Outer", "Interval", "Down", "Up", "Mean z²"]] + [[name, pct(m["inner"]["value"]), span(m["inner"]), pct(m["outer"]["value"]), span(m["outer"]), pct(m["down_tail"]["value"]), pct(m["up_tail"]["value"]), f"{m['mean_z2']:.2f}"] for name, m in METHODS.items()], [1.6, .7, 1.4, .7, 1.4, .6, .6, .7], f"<b>Table 11. Coverage on {BENCH['rows']:,} common rows, {BENCH['first_origin']} to {BENCH['last_origin']}.</b> Intervals use 63-session blocks. Past-only k has a median of {BENCH['k']['median']:.2f}, and past-only degrees of freedom have a median of {BENCH['nu']['median']:.0f}.")
p.figure(FIG / "calib_benchmarks.png", "<b>Figure 6. Hit rates by method, with 63-session intervals.</b>", 2.7 / 7.2)


def cell(row):
    return f"{row['difference']:+.4f}<br/>({row['low63']:+.4f} to {row['high63']:+.4f})"


p.table([["Method", "CRPS", "Interval score, .6827", "Interval score, .9545", "Brier, 10%", "Brier, 20%"]] + [[name, cell(m["scores"]["crps"]), cell(m["scores"]["interval_inner"]), cell(m["scores"]["interval_outer"]), cell(m["brier"]["0.1"]), cell(m["brier"]["0.2"])] for name, m in METHODS.items() if name != "ATM30"], [1.4, 1.2, 1.2, 1.2, 1.2, 1.2], "<b>Table 12. Score differences, benchmark minus ATM30, with 63-session intervals.</b> A negative value favours the benchmark.")
p.bullets([
    "<b>HAR, no factor, and fat-tailed ATM30.</b> All score intervals include zero. This does not show equality. Their coverage differs: HAR with no factor has a 4.2% up-tail breach, and fat-tailed ATM30 has an inner rate of " + pct(METHODS["Fat-tailed ATM30"]["inner"]["value"]) + ".",
    "<b>HAR with the Duan factor.</b> It is closer to nominal on mean z² and outer, but its inner rate is " + pct(METHODS["HAR, Duan"]["inner"]["value"]) + ", and its inner interval score is worse.",
    f"<b>Scaled ATM30.</b> The scale overshoots: mean z² falls to {METHODS['Scaled ATM30']['mean_z2']:.2f}, and the inner rate rises to {pct(METHODS['Scaled ATM30']['inner']['value'])}. The 2019 PASO inflates k. With those windows out of the fit, median k is {k_out['median_k']:.2f}, inner is {pct(k_out['inner'])}, and mean z² is {k_out['mean_z2']:.2f} (post-result, hindsight, not a benchmark). The review reports that no score interval excludes zero in that sensitivity. So the worse scores depend largely on one event.",
    f"<b>Fat tails at 2σ.</b> A unit-variance t has almost the same 2σ quantile as a normal: {shape['half_width_95_at_nu']['5.0']:.2f} at ν = 5, against {shape['half_width_95_normal']:.2f}. So the planned benchmark has almost no power to test tails at this quantile. The fitted ν is 6 or lower on {nu_low:,} of {BENCH['rows']:,} rows, which points to fat tails, with the caveats that the fit fixes the variance at one and the rows overlap.",
])

p.section("8. Subsamples and robustness", 14)
p.table([["Cut", "Rows", "Inner", "Interval", "Outer", "Interval", "Down", "Up", "z²"]] + [[name, f"{v['n']:,}", pct(v["inner"]["value"]), span(v["inner"]), pct(v["outer"]["value"]), span(v["outer"]), pct(v["down_tail"]["value"]), pct(v["up_tail"]["value"]), f"{v['mean_z2']['value']:.2f}"] for name, v in CUTS.items() if name != "Same rows as the 15:45 start, at the close"], [2.05, .72, .78, 1.42, .78, 1.42, .72, .72, .55], "<b>Table 13. Cuts set before the results.</b> The last column is mean z². Intervals use 63-session blocks. A blank interval means that the block is more than a third of the span. The 15:45 start has the same rows as the primary run. The American-exercise cut did not run. The tree inversion exists only as development work in " + I % "fixes/" + " for the main study, and it was not applied here.")
p.add(f"The drift rule and the timing gap have little effect: a zero centre gives {pct(CUTS['Centre at zero']['inner']['value'])}, and the 15:45 start gives {pct(CUTS['Start at the 15:45 stock mid']['inner']['value'])}. The period 2016-01 to 2018-04 is a separate, calmer sub-period with Alpaca closes. It does not confirm the open-data result. Its intervals are wide, and its one-sided tails (0.2% down, 5.9% up) reflect few independent episodes.")

p.add("9. Frozen forward test", "h1")
p.figure(FIG / "calib_forward.png", "<b>Figure 7. Period roles and the forward schedule.</b> No forward data exists in this project.", 1.75 / 7.2)
p.table([
    ["Element", "Rule"],
    ["Rows", "Origins from 2026-10-30 through the first origin on or after 2029-10-30, with complete windows. Events and Tier 2 days stay in"],
    ["Measure", "Inner hit rate, with the same centre, band, and bootstrap as the primary run"],
    ["Verdict", "\"Miscalibrated\" if the interval excludes .6827 under both block sizes. Otherwise \"No miscalibration shown\", which does not prove calibration. A blank interval gives \"Too few rows\""],
    ["Interim", "A descriptive look at origins through 2027-10-29, with no verdict"],
    ["Horizon", "36 months, fixed by the owner on 2026-11-05. The earliest verdict is about 2029-11-29, when the last window closes"],
], [1, 5.5], "<b>Table 14. Forward rules.</b> " + I % "CALIBRATION_PLAN.md" + " holds the full text, and " + I % "reports/calib_horizon.json" + " holds the horizon record.")
p.table([["Rows", "About months", "Fires, no error", "Cover 21, no error", "Cover 63, no error", "Fires, 25% too wide", "Fires, wandering", "Cover 63, wandering"]] + [[row["sessions"], round(row["sessions"] / 21), pct(row["no_error"]["verdict_fires"], 0), pct(row["no_error"]["cover21"], 0), pct(row["no_error"]["cover63"], 0), pct(row["bands_25pct_too_wide"]["verdict_fires"], 0), pct(row["wandering_error"]["verdict_fires"], 0), pct(row["wandering_error"]["cover63"], 0)] for row in SYN["forward_power"]], [.6, .8, .9, 1, 1, 1, 1, 1], "<b>Table 15. Simulated behaviour of the verdict rule.</b> Rows are consecutive. Real data has a value on about 86% of sessions, so 36 months gives about 650 rows, and the power lies between the 504-row and 756-row lines. The wandering case has a true inner rate near nominal, so its \"Fires\" column shows mostly false alarms.")
p.add("The rule has a false-alarm rate of about 9% to 13% in simulation, and not 5%. A verdict must quote this. The test covers the pooled inner rate only. It does not test the low-ATM30 pattern of Section 6. That needs its own frozen rule, written before any forward data is read. The review also found that the outer intervals cover only about 60% at 252 rows, so the 12-month look will have very unreliable outer intervals.")

p.add("10. Discussion", "h1")
p.add("The pooled result and the conditional results answer different questions. Unconditional coverage asks if the band is right on average. The original question, whether ATM30 gives the right probabilities, also needs the band to be right given what is known at the origin. On that second reading the evidence is unfavourable, but it is post-result: the low-quintile inner rate, the flat reliability curve, and the absence of a shown Brier gain over a base rate all point the same way.")
p.add("A miss under real-world probabilities is not automatically a market error. The bands are risk-neutral and include the variance risk premium. Risk-neutral probabilities can differ from real-world ones in a well-functioning market, and this design cannot separate a premium from a forecast error. The tail excess is also not simple evidence that bands are too narrow, because one crash supplies 18.3% of all z², and the centre shows no level error.")

p.add("11. Limitations", "h1")
p.bullets([
    "<b>Development data.</b> Open data shaped the method, and the post-result cuts multiply the chances of a pattern by accident.",
    "<b>Effective size.</b> About 102 independent months, and nine events.",
    f"<b>Interval coverage.</b> The nominal 95% intervals cover about {100 * min(full['wandering']['cover21'], full['constant']['cover21']):.0f}% to {100 * max(full['wandering']['cover63'], full['constant']['cover63']):.0f}% in simulation for the inner rate. Many intervals here are shown without any multiple-comparison control.",
    f"<b>Selection.</b> On {selection['blank_rows']} rows with a complete window and a blank ATM30, moves above 20% occur in {pct(selection['big_move_blank'])}, against {pct(selection['big_move_valid'])} on valid rows ({100 * selection['low63']:.1f} to {100 * selection['high63']:.1f} points of difference). So pooled coverage may be overstated. The main study found missing days slightly calmer by mean log RV30, so the two measures point in different directions. We did not study why.",
    f"<b>Fixed T.</b> The plan uses 30/365, but windows average {actual['mean_days']:.2f} days to the last session. With the real length, inner is {pct(actual['inner'])} and mean z² is {actual['mean_z2']:.2f}, so the inner excess over nominal is about half of what it looks like (post-result).",
    "<b>Normal band.</b> A single near-the-money volatility ignores skew by design.",
    "<b>Exercise style and dividends.</b> Black inversion on American options can bias IV. This paper does not measure the effect on its own results. In the audit simulation (" + I % "audit/a05_american_bias.out" + "), a dividend inside the term makes term IV too high by 1.2% to 12.6% (dividends of 2% and 3.5%, terms of 45 to 10 days). A tree correction on real data does not move the main-study coefficient (" + I % "fixes/FIXES_REPORT.md" + "). We did not test the effect on the hit rates.",
    "<b>Wide quotes.</b> The band uses the mid of quotes that are often wide, and the code has no spread filter. The median relative spread of the call-put pair is .24 before 2025-03 and .55 from 2025-04 (audit F3). Tier 2 days stay in by design.",
    "<b>Regime mix.</b> Open data mixes calm years, crises, and the 2025-03 format break.",
])

p.add("12. Integrity record", "h1")
p.bullets([
    f"<b>Freeze.</b> The manifest hash is {manifest_hash}. This folder has no git, so the manifest replaces the commit in C0. File times and a code guard fit the order \"rules, then results\", but they cannot prove it. The owner was asked to save this hash, and no comparison has been made.",
    "<b>Study freeze.</b> The main study's manifest shows no differences, and its Stage 5 files did not change. New code sits in " + I % "calibration/" + ", outside the folders that " + I % "freeze.py" + " hashes.",
    "<b>Horizon.</b> The owner chose 36 months after seeing the open-data results and the power table, and before any forward data existed. Recording it changed the plan text, so " + I % "calib_run.py" + " would now report the plan as changed. " + I % "reports/calib_horizon.json" + " holds the hash before and after. The manifest is unchanged.",
    "<b>Adversarial review.</b> One independent agent reviewed the work (" + I % "review/calibration_review/report.md" + "). It reran C1, C2, C3, and the base-rate table with zero differences, and it found no formula error, look-ahead, or row mismatch. It found that the first main reading overreached. That reading is rewritten here. The review has not seen this paper.",
    "<b>Not checked by the review.</b> The construction of ATM30, the accuracy of the cash file and the event dates, the test-period R against raw Alpaca closes, and the 300-run simulation.",
    "<b>Frozen faults left as they are.</b> A docstring in " + I % "calib_synthetic.py" + " says that z is exactly standard normal and that the wandering case is below nominal. Neither is exact.",
])

p.add("13. Work not done", "h1")
p.numbered([
    "<b>Owner review.</b> Review this draft and compare the saved hash.",
    "<b>Forward code.</b> " + I % "forward_verdict" + " checks only that a horizon argument exists. It does not read the horizon record or filter rows. It needs this fix and a data loader before any forward run, as a logged change.",
    "<b>American tree sensitivity.</b> Done for the main study as development work in " + I % "fixes/" + ". Not applied to the calibration.",
    "<b>Conditional forward rule.</b> The low-ATM30 pattern has no frozen test. If the owner wants one, it must be written before forward data is read.",
    "<b>Main-study drafts.</b> These results are not in them, and they still wait for review.",
])

p.add("14. Conclusion", "h1")
p.add(f"The {I % 'ATM30'} band has near-nominal pooled coverage on open data, but this result is not enough to call its probabilities calibrated. Post-result cuts show lower inner coverage when {I % 'ATM30'} is low, large tail excess around some events, and no shown gain over a past base rate for move probabilities. No benchmark clearly beats it on scores. All of this is exploratory, and the frozen 36-month forward test can address only the pooled inner rate.")

p.add("Reproduction", "h1")
p.add(f"Environment: Conda {I % 'py4fi'}. Rules: {I % 'CALIBRATION_PLAN.md'}. Tests: {I % 'python calibration/test_calib.py'}. Results: {I % 'reports/calib_results.json'}. Descriptive report: {I % 'reports/calib_descriptive.md'}. These papers: {I % 'writeup/build_calibration_plain.py'} and {I % 'writeup/build_calibration_technical.py'}, which need {I % 'reportlab'} on the path. The Databento data is licensed, so these results and files stay local unless the license permits otherwise.")

p.add("References", "h1")
p.add("These citations come from memory and were not checked against the sources. Verify them before any submission.", "caption")
for reference in (
    "Black, F. (1976). The pricing of commodity contracts. <i>Journal of Financial Economics</i>, 3.",
    "Brier, G. (1950). Verification of forecasts expressed in terms of probability. <i>Monthly Weather Review</i>, 78.",
    "Corsi, F. (2009). A simple approximate long-memory model of realized volatility. <i>Journal of Financial Econometrics</i>, 7.",
    "Diebold, F., Gunther, T., and Tay, A. (1998). Evaluating density forecasts with applications to financial risk management. <i>International Economic Review</i>, 39.",
    "Duan, N. (1983). Smearing estimate: a nonparametric retransformation method. <i>Journal of the American Statistical Association</i>, 78.",
    "Gneiting, T., and Raftery, A. (2007). Strictly proper scoring rules, prediction, and estimation. <i>Journal of the American Statistical Association</i>, 102.",
    "Jordan, A., Krüger, F., and Lerch, S. (2019). Evaluating probabilistic forecasts with scoringRules. <i>Journal of Statistical Software</i>, 90.",
    "Politis, D., and Romano, J. (1992). A circular block-resampling procedure for stationary data. In R. LePage and L. Billard (eds.), <i>Exploring the Limits of Bootstrap</i>. Wiley.",
):
    p.add(reference, "reference")
p.build()
print("technical calibration report written")
