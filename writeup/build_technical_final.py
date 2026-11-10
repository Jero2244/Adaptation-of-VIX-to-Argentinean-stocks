"""The technical final report. Run from the project folder, with reportlab on PYTHONPATH."""
import common as c
import final_common as f

f.check_numbers()
f.check_open_data()
f.check_fixes()
c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
f.timeline_final(c.FIGURES / "timeline_final.png")
m = f.series_chart(c.FIGURES / "series_final.png", (7.2, 3.0))
f.comparison_chart(c.FIGURES / "compare_technical.png", [
    ("All, with events", .622, .337, .916, "dev"),
    ("Before 2025-03, with events", .525, .208, .862, "dev"),
    ("Before 2025-03, no events", .366, -.018, .682, "dev"),
    ("Test, with events (verdict)", .281, -.209, .845, "test"),
    ("Test, no events", .351, -.121, .916, "test"),
    ("Test, Tier 1 only", .411, -.110, 1.162, "test"),
], (7.2, 3.1))
c.forest_chart(c.FIGURES / "forest_technical.png", [
    ("All", (.622, .337, .916), (.459, .152, .715)),
    ("Before 2025-03", (.525, .208, .862), (.366, -.018, .682)),
    ("From 2025-03", (1.190, .488, 1.516), (.781, .227, 1.244)),
    ("2018-2023", (.526, .192, .875), (.364, -.030, .721)),
    ("2024-2025", (1.185, .588, 1.469), (.891, .429, 1.223)),
    ("2026 (no listed event)", (.423, -.387, 1.569), None),
], (7.2, 3.9))
c.outcomes_chart(c.FIGURES / "outcomes_technical.png", [("True b = 0", 4.0, 39.8, 56.2), ("True b = .25", 22.2, 12.3, 65.5), ("True b = .37", 34.8, 4.8, 60.3), ("True b = .50", 54.0, 1.7, 44.3), ("True b = .62", 65.5, .2, 34.3)], (7.2, 2.5))

I = "<font name='Serif-Italic'>%s</font>"
p = c.Paper("Serif", 9.2, "Does implied volatility add information for GGAL ADR realized variance?", f.FOOTER, c.HERE / "GGAL_study_technical_final.pdf")

p.add("Does implied volatility add information for GGAL ADR realized variance?", "title")
p.add("Evidence from development data and a frozen one-time test. Working paper, final report draft of 2026-11-05, prepared with Claude Code from the project records. Not peer reviewed.", "subtitle")
p.add("<b>Revision history.</b> " + f.REVISION_NOTE + " The pre-registered Stage 5 result is unchanged. Section 12 reports development checks made after the one-time test.", "subtitle")
assert (round(m["test_atm"], 3), round(m["open_atm"], 3), round(m["test_rv"], 3), round(m["open_rv"], 3)) == (.334, .609, .311, .520)
p.add("Abstract", "h2")
p.add(f"We build a 30-day at-the-money implied volatility index ({I % 'ATM30'}) for GGAL ADR options and test whether it adds information about 30-day realized variance beyond a HAR-type baseline. {I % 'ATM30'} is a Black at-the-money implied volatility interpolated to 30 days. It is not the CBOE VIX strip formula. The positive in-sample result is fragile, so read three numbers together. The coefficient on log implied variance is <b>.622</b> on all 1,806 development origins (2018-05 to 2026-10), with a nominal 95% block-bootstrap interval of .337 to .916. It is <b>.366</b> for non-event origins before 2025-03, with an interval of -.018 to .682 that includes zero. It is <b>.281</b> in the one-time test, whose outcome is \"Inconclusive\". It is also .459 with event windows dropped. No dependable out-of-sample gain appears. The nominal 95% intervals cover less than 95%: 80% to 91% in the study's own simulation, and 87% to 91% in a later one. We froze the method and verdict rules, then ran a one-time test on 2016-01 to 2018-04 (455 origins). <b>The pre-specified outcome is \"Inconclusive\", with a positive sign: b = .281, with intervals of -.209 to .845 (21-session blocks) and -.232 to .937 (63-session blocks).</b> The interval includes zero and all development sizes. Clark-West t is -.30, and no QLIKE gain appears. The test neither confirms nor rejects the development result, and its power is low.")

p.add("1. Introduction", "h1")
p.add("The information content of implied volatility is a long-standing question (Canina and Figlewski, 1993; Christensen and Prabhala, 1998). GGAL ADR is a useful case. It has large scheduled political risk and an option chain whose depth varies strongly over time.")
p.add(f"The project began as an attempt to adapt the CBOE VIX method (Cboe white paper), and the project folder keeps the name \"vix_ggal_adaptation\". Data checks in a two-agent plan debate changed the headline: at least 5 out-of-the-money bids per wing on both expiries occurred on 0% to 1% of days in 2018-2023. The primary series therefore became {I % 'ATM30'}. The audit of 2026-11-10 made the name exact. {I % 'ATM30'} is a Black (1976) at-the-money implied volatility, interpolated in total variance to 30 days. It is not a VIX-style index. It has no part of the CBOE strip formula: no strip sum, no K0, no strike step, and no correction term.")
p.add(f"A literal CBOE calculation needs 3 or more out-of-the-money strikes on each wing in both terms. The chain has this on 245 sessions, almost all from 2024 (README.md; audit/a02_series_and_cboe.py). Before 2024 the strip sum overstates variance: the yearly median ratio of the CBOE-style volatility to {I % 'ATM30'} runs from 1.10 to 1.83 in 2018-2023 (1.30 in 2021, 1.83 in 2022), against 1.00 to 1.02 in 2024-2026, and its daily log changes have a standard deviation of 12.4% against 7.3% for {I % 'ATM30'}. The choice of an at-the-money series is right for this chain. The earlier name was wrong. The series {I % 'MF30'} is a descriptive integral of a fitted smile with flat wings, not the CBOE formula. It has 512 sessions from 2024 onward. Its median share of variance outside the quoted range is .18 in 2024 and .25 in 2026. An {I % 'MF30'} term added little in the debate checks (bootstrap t at most 1.57 with {I % 'ATM30'} present), and it enters no regression.")
p.add("The paper separates three kinds of evidence: exploratory development results, one frozen confirmatory result, and post-result descriptive notes. Only the second can support a verdict.")

p.add("2. Data", "h1")
p.table([
    ["Source", "Use", "Coverage and notes"],
    ["Databento cbbo-1m, definitions, GGAL root", "Option quotes", "Open 2018-05-01 to 2026-10-29. Test 2016-01 to 2018-04. Adjusted roots are out of scope by user decision"],
    ["Official equity daily table", "Development closes", "2,137 sessions"],
    ["Alpaca SIP daily bars", "Test closes", "2,689 bars. 585 test sessions, all matched to option sessions"],
    ["FRED DGS1MO, DGS3MO", "Discount rates", "Continuous, linear in days, flat outside 30 and 91 days, prior observation only"],
    [I % "adr_cash_events.csv", "Total return", "33 dividends and the 2025 rights value, in USD per ADS. Two dividends fall in the test. Their rate and date come from a vendor, with no record date or tax basis"],
], [2.2, 1.1, 3.6], "<b>Table 1. Inputs.</b> Nasdaq bbo-1m data supported 5-minute review checks in the study, and the stronger HAR baseline in Section 12 (development work in " + I % "fixes/" + ").")
p.bullets([
    "<b>Data inventory.</b> The data folder holds cbbo-1m (options), bbo-1m (Nasdaq stock), ohlcv-1d, statistics, definition, and tcbbo. It does not hold MBP-1, MBP-10, or BBO-1s. The 2013-2015 option data is dropped. OPRA statistics and TCBBO are not used.",
    "<b>Deliverable.</b> In the OPRA definitions, " + I % "contract_multiplier" + " is undefined (the value is INT_MAX), and " + I % "unit_of_measure_qty" + " is blank. The 100-share deliverable is assumed, not verified (" + I % "fixes/f11_check_multiplier.out" + ", 12 sample days). The code cannot detect a non-standard deliverable. The question of an adjusted root stays closed by user decision.",
])
p.table([
    ["Year", "Sessions", "ATM30", "Coverage", "Tier 1", "Tier 2"],
    ["2016 (test)", "252", "200", ".794", "", ""],
    ["2017 (test)", "251", "214", ".853", "", ""],
    ["2018, to April (test)", "82", "78", ".951", "", ""],
    ["2018, from May", "169", "154", ".911", "137", "17"],
    ["2019", "252", "227", ".901", "193", "34"],
    ["2020", "253", "216", ".854", "108", "108"],
    ["2021", "252", "181", ".718", "51", "130"],
    ["2022", "251", "196", ".781", "25", "171"],
    ["2023", "250", "213", ".852", "152", "61"],
    ["2024", "252", "230", ".913", "212", "18"],
    ["2025", "250", "234", ".936", "220", "14"],
    ["2026, to 10-29", "208", "195", ".938", "187", "8"],
], [2, 1, 1, 1, 1, 1], "<b>Table 2. Coverage.</b> Test totals: 492 of 585 sessions, with 273 Tier 1 and 219 Tier 2 days. Open totals: 1,846 of 2,137 sessions, with 1,285 Tier 1 and 561 Tier 2 days. Of open sessions, 95.3% have two expiries that bracket 30 days, and 86.4% have a two-sided pair on both terms.")
p.figure(c.FIGURES / "series_final.png", "<b>Figure 1. Implied volatility and the realized volatility of the next 30 days.</b> Lines connect across missing days, and no value is imputed. Shaded: the test period. Stored panels; descriptive only.", 3.0 / 7.2)

p.add("3. Method", "h1")
p.add("3.1 Implied volatility series", "h2")
p.add("At 15:45 New York, take the last quote per contract from 09:30, with a quote age of at most 30 minutes for the primary series. A valid pair has a call and a put at one strike, each with 0 &lt; bid ≤ ask. Parity at the two-sided strike with the smallest |C − P| gives the forward, so the primary series needs no dividend input:")
p.add("F = K + e<super>rT</super> (C − P)", "equation")
p.add("Term IV inverts Black (1976) on the discount-adjusted call-put average, with linear interpolation of IV in log strike between the two strikes nearest F. Each strike is at most 25% in absolute log distance from F. Total variance is interpolated to 30 days between the two listed expiries that bracket 30 days, with no extrapolation. A failed expiry leaves the day missing, and no missing day is imputed. Half days have no value, because the market closes before 15:45. Tier 1 has a bracketed forward, or a strike at the forward, on each term. Tier 2 has one strike on at least one term.")
p.add("The audit of 2026-11-10 found the following limits of these rules. They are described here and not corrected in the primary series. Section 12 reports development tests of several.")
p.bullets([
    "<b>Snapshot rule (F7).</b> The code takes the last non-null value of each column. After 2025-03 a null bid means \"no bid\", so an old bid can join a new ask. Under a strict last-row rule 9 days lose their value, 35 days change, and the largest change is +14.2% (2025-07-11) (" + I % "fixes/f13_checks.out" + ").",
    "<b>Age rule (F8).</b> The 30-minute age rule is not a staleness control before 2025-03. Before then each instrument has exactly 390 rows per day, one per minute. On valid days the quote age is 0 on 99.5% of days, and the largest age is 8 minutes, so the rule has no effect on those days. From 2025-03 rows appear on updates only, and the rule removes 7.0% of snapshot rows. The rule changes meaning at the format break.",
    "<b>Near term (F9).</b> The near term is used down to 15 minutes before expiry. On 249 valid days it is under 7 days, and the index horizon drifts toward about 35 days. The " + I % "atm30_floor7" + " series is the 7-day alternative.",
    "<b>No extrapolation (F10).</b> 101 sessions have no listed bracket, mostly just after a monthly expiry. On 21 valid days the far term is more than 65 days away. Missing days follow the expiry cycle.",
    "<b>Wide quotes, no spread filter (F3).</b> The mid of wide quotes sets the index. The half-width of the bid-ask band on the IV is ±13.7% (median), ±25.6% (75th percentile), and ±39.8% (90th percentile), against a daily standard deviation of 7.3% for log " + I % "ATM30" + " changes. The relative spread of the call-put pair (worst of the two terms) is above .25 on 55% of valid days, above .50 on 25%, and above 1.0 on 5%. The median is .24 before 2025-03 and .55 from 2025-04. Example: on 2023-05-30 a 12.5 put was quoted 0.05 / 3.30.",
    "<b>Single-strike days (F4).</b> 561 of 1,846 valid days (30%) are Tier 2. One strike, up to 25% from the forward (median 11.8%), stands in for \"at the money\". There the IV is a point on the skew. Tier 2 is 50% to 87% of days in 2020-2022.",
    "<b>Rate, stock quote, half days (F18, F19, F20).</b> The rate is log(1 + y) on a bond-equivalent Treasury yield, linear between 1 and 3 months. CBOE converts to an annual percentage yield and uses a spline. The effect is about 6 bp at a 5% yield. The stock mid comes from the Nasdaq book only (XNAS.ITCH), not the consolidated quote. It feeds diagnostics and one calibration cut, and in the regular session its median gap to the official close is 5 bp. 17 half days have no value, because the snapshot time stays at 15:45. A fix would sample 15 minutes before the early close.",
])
p.add("3.2 Realized variance and primary regression", "h2")
p.add("With total log returns r, including cash on the ex-date, the target for origin t uses sessions in (t, t + 30 calendar days]:")
p.add("RV30<sub>t</sub> = (365 / 30) Σ<sub>s ∈ (t, t+30d]</sub> r<sub>s</sub>²", "equation")
p.add("log RV30<sub>t</sub> = c + β<sub>1</sub> log RV<sub>1,t</sub> + β<sub>5</sub> log RV<sub>5,t</sub> + β<sub>22</sub> log RV<sub>22,t</sub> + b log ATM30<sub>t</sub>² + ε<sub>t</sub>", "equation")
p.add("The window ends on average 29.37 days after the origin, so RV is about 2% low against a 30-day IV. The constant in the log regression absorbs this offset. A premium level does not absorb it.")
p.add("This is a HAR-type regression on squared daily returns, with implied variance added. Corsi (2009) builds HAR on intraday realized variance. Here RV1 is one squared daily return, and the floor binds on 47 sessions. So the label \"HAR (Corsi)\" is not exact. HAR inputs are log annualized RV through the origin close, with a floor of 1e-6 on mean daily variance. Inference uses circular block bootstraps (Politis and Romano, 1992) of 21 and 63 sessions on the full session grid, with 2,000 resamples of row pairs, and 2.5th and 97.5th percentiles. These are nominal 95% intervals, and their real coverage is lower (Section 4). Newey-West (1987) errors with 21 lags are for comparison only. Fixed-step samples of 22 and 23 sessions are reported. They replaced a first-valid-session scheme whose paths merged.")
p.add("3.3 Forecast comparison", "h2")
p.add("Models refit by OLS in logs at each origin, using rows whose target window ends on or before the origin. Scoring starts at position 252, with at least 126 training rows. The level correction is the Duan (1983) smearing factor, and the no-factor result is reported beside it. Information uses Clark and West (2007) on log loss, because HAR is nested in HAR+ATM30. Usable gain uses QLIKE (Patton, 2011), L = y/f − log(y/f) − 1, on the same rows. GARCH with t errors and EWMA with a lambda of .94 are benchmarks, and they do not affect a verdict.")
p.add("3.4 Events", "h2")
p.add("The event list was set in advance: nine elections in 2019-2025 for open data, and the 2017 PASO and midterm for the test. Event work compares forward variance between expiries that straddle an event with placebo dates at multiples of 28 days. It reports no p-values, and the placebos share dates.")
p.add("3.5 Sample design", "h2")
p.figure(c.FIGURES / "timeline_final.png", "<b>Figure 2. Period roles.</b> 2013-04 to 2015-12 is dropped. The 2026 data are open and reported separately. They are not a blind forward test.", 1.75 / 7.2)

p.add("4. Development results", "h1")
p.callout("All results in this section are exploratory. The method and the review checks came after contact with these data.", edge=c.ORANGE)
p.figure(c.FIGURES / "forest_technical.png", "<b>Figure 3. Coefficient on log implied variance, open data.</b> The intervals are nominal 95%. The study's simulation puts their real coverage at about 80% to 91%, and a later simulation at 87% to 91% (" + I % "fixes/f09_coverage.csv" + "), so they are too narrow. Source: " + I % "reports/stage4_descriptive.md" + ".", 3.9 / 7.2)
p.table([
    ["Sample", "n", "b", "Interval, 21 blocks", "Interval, 63 blocks"],
    ["All, with events", "1,806", ".622", ".337 to .916", ".309 to .946"],
    ["All, no events", "1,643", ".459", ".152 to .715", ".060 to .761"],
    ["Before 2025-03, with events", "1,431", ".525", ".208 to .862", ".152 to .922"],
    ["Before 2025-03, no events", "1,300", ".366", "-.018 to .682", "-.131 to .717"],
    ["From 2025-03, with events", "375", "1.190", ".488 to 1.516", ".330 to 1.516"],
    ["From 2025-03, no events", "343", ".781", ".227 to 1.244", ".149 to 1.415"],
], [2.7, .7, .7, 1.5, 1.5], "<b>Table 3. Primary coefficient, open data.</b> R² rises from .097 for HAR to .177 with IV on all rows. Intervals are nominal 95%. Measured coverage is 87% to 91% in the later simulation (Section 12), and 80% to 91% in the study's own. Source: " + I % "reports/stage4_coefficients.csv" + ".")
p.bullets([
    "<b>Concentration (review check, one agent).</b> Event rows are 9% of rows and supply 57% of the in-sample squared-error gain. Non-event rows after the break are 19% and supply 31%. Non-event rows before the break are 72% and supply 11%.",
    "<b>Fixed-step samples.</b> Mean b is .611 and .602 for steps of 22 and 23 sessions, and .500 and .493 with no 2019 PASO windows. These samples share periods, so they are not independent.",
    "<b>Instability.</b> Yearly b runs from -.380 in 2022 to 1.379 in 2025. Leave-one-year-out b stays from .542 to .707. Year-demeaned b is .644 (.309 to 1.015).",
    "<b>Other baselines (review checks).</b> 5-minute HAR inputs give about .53. With 5-minute HAR and no events, b is near .28 to .30. A 5-minute target raises R² from .177 to .294.",
    "<b>Quote quality.</b> b is .703 on Tier 1 and .435 on Tier 2. Within years, spread terciles give .884, .698, and .373. The cause is open. On identical days, OLS gives .685 and IV lag 1 gives .682, so short-lived noise looks small. Persistent quote error is untested.",
    "<b>Selection.</b> Coverage is .675 with 0-6 days to the near expiry, and .94 to .97 with more days. Mean log RV30 is -1.27 on missing days and -1.18 on present days, so missing days are slightly calmer.",
    "<b>ATM variance minus realized variance.</b> ATM30² minus RV has a mean of -.041 and a median of +.105. Implied variance exceeds RV on 72% of origins. ATM30² is not a model-free implied variance. Where both exist, the median of MF30² / ATM30² is 1.15, so ATM variance understates model-free variance. The 72% is therefore a lower bound for a premium. The mean is negative only because of the 2019 PASO. This is not an estimate of the variance risk premium.",
    "<b>Overnight share.</b> The overnight share of RV is .32 in all periods, .36 in 2024-2025, and .18 in 2026.",
])
p.table([
    ["Same-row race, 1,599 rows from 2019-05-02", "Estimate", "Interval or t"],
    ["QLIKE, HAR+ATM30 minus HAR, Duan factor", "-.0187", "-.0444 to .0115"],
    ["QLIKE, HAR+ATM30 minus HAR, no factor", ".0002", "-.0339 to .0375"],
    ["Clark-West on log loss, no factor, 21-session blocks", ".0624", "t 2.70"],
    ["Clark-West on log loss, no factor, 63-session blocks", ".0624", "t 2.07"],
], [4, 1, 1.5], "<b>Table 4. Out-of-sample comparison, open data.</b> A negative QLIKE difference favors HAR+ATM30. Mean target .484. Mean Duan forecasts about .625. Mean no-factor forecasts .352 and .368.")
p.add("Earlier QLIKE differences ranged from -.077 to .000 across smearing, training, and row choices. The training start alone moved one value from -.043 to -.077 on the same rows, because common training days removed 2018-06 to 2019-04 from HAR. In the raw race, unscaled ATM30 has the lowest QLIKE (.418), and GARCH with t errors is next (.470), with an interval for the difference that includes zero. We read the development evidence as information with no dependable usable gain.")
p.table([
    ["Scale (realized on implied)", "a", "b", "R²", "Joint p, a = 0 and b = 1"],
    ["Logs: log RV30 on log ATM30²", "-.541", ".698", ".163", "&lt; .0001"],
    ["Variance levels: RV30 on ATM30²", ".181", ".686", ".031", ".064"],
    ["Volatility levels: √RV30 on ATM30", ".163", ".683", ".100", ".027"],
], [3, .7, .7, .7, 1.6], "<b>Table 4a. Mincer-Zarnowitz (1969) regression, open data, 1,806 origins.</b> Newey-West errors with 21 lags, joint Wald test. Source: " + I % "fixes/f09_mincer_zarnowitz.csv" + " (development work). The test rejects \"a = 0 and b = 1\" in logs and in volatility levels. It does not reject at the 5% level in variance levels (p = .064). A part of this is expected from the variance risk premium, because ATM30 is a risk-neutral measure. The test does not support the claim of information beyond HAR. On the 936 origins of the all-four series (Section 12), the joint p is .10, .31, and .48, with a much smaller sample.")
p.table([
    ["Event", "First return", "Near vol", "Forward vol", "Ratio", "Realized vol between", "Placebos below"],
    ["2019 PASO", "-.824", ".460", ".576", "1.251", "3.038", "1.000"],
    ["2019 general", "-.121", ".895", ".925", "1.034", ".673", ".864"],
    ["2021 PASO", ".089", ".493", ".553", "1.122", ".668", ".900"],
    ["2021 midterm", "-.011", ".521", ".673", "1.291", ".605", "1.000"],
    ["2023 PASO", "-.060", ".732", ".923", "1.261", ".518", ".857"],
    ["2023 general", ".013", ".779", ".949", "1.219", ".509", ".905"],
    ["2023 runoff", ".159", ".577", ".725", "1.256", ".910", ".905"],
    ["2025 PBA", "-.269", ".474", ".491", "1.034", "1.033", ".591"],
    ["2025 midterm", ".327", "1.129", "1.123", ".995", "1.194", ".545"],
], [1.5, .9, .8, .9, .7, 1.2, 1], "<b>Table 5. Election case studies.</b> Ratio is forward vol over near vol. The ratio is above the placebo median at all nine events, by only .004 at the 2025 midterm. The 2021 PASO has a 17-day near term, so its placebo share is not like for like. These comparisons are not independent. Source: " + I % "reports/stage3_results.md" + ".")

p.add("5. The frozen test", "h1")
p.add("The test falls entirely before the 2025-03 quote format break. It can therefore test the weak ordinary-day evidence, but it cannot explain the change after the break. The verdict depends only on Rule 1. Rules were frozen by SHA-256 manifest before any marker existed. No outside registry holds them.")
p.table([
    ["Element", "Rule"],
    ["Rule 1 (verdict)", "b in HAR+IV has a lower bound above zero in both percentile intervals: 21-session and 63-session blocks, 2,000 resamples"],
    ["Rule 2 (label)", "Clark-West on log loss, no level factor, 21-session blocks, t above 1.65 on at least 180 scored rows. Adds \"also out-of-sample\""],
    ["Rule 3 (label)", "QLIKE difference with the Duan factor has a 97.5th percentile below zero. Adds \"with usable gain\""],
    ["Data floor", "At least 300 valid origins, and at least 20 of the 21-session spans hold 10 or more valid origins"],
    ["Input stop", "Before any result, the near forward is compared with the close. Stop if the median absolute log gap is above .02, more than 5% of rows are above 5%, the largest gap is above .15, or more than 3 sessions are in one source only. Listed data faults also stop the run"],
    ["No-forward check", "Stop only if a close on a no-forward session is above .15 from the nearest forward on both sides and above .15 from both adjacent closes"],
    ["Outcomes, first match wins", "(0) Inconclusive, inputs failed. (1) Inconclusive, data floor. (2) Supported. (3) Smaller than .37, if both upper bounds are below .37. (4) Inconclusive, with the sign of b"],
], [1.25, 5], "<b>Table 6. Frozen rules.</b> " + I % "PROTOCOL.md" + " holds the full text. Clark-West is a label by user decision.")
p.add("<b>Power.</b> Figure 4 shows the advocate's simulation with 600 replications per value, at constant b and on development rows. A separate judge run gives \"Supported\" at 3.8%, 34.6%, and 69.2% for b of 0, .37, and .62. Both debate agents agree that the bootstrap standard error is too small, with SD of b over median SE near 1.3 to 1.5. Since 0 and .37 are only about 1.0 to 1.25 SD apart, no rule removes the low power. The owner accepted this before the run.")
p.figure(c.FIGURES / "outcomes_technical.png", "<b>Figure 4. Simulated outcome rates by true b, at full coverage.</b> Segments below 3.5% carry no number: 1.7% at .50 and 0.2% at .62. Source: " + I % "STAGE4_PLAN.md" + ".", 2.5 / 7.2)

p.add("6. Confirmatory result", "h1")
p.callout("<b>Verdict line, as printed by the frozen code:</b> \"Inconclusive. 2016-01 to 2018-04 only. The \"95%\" intervals really cover about 80% to 91% in simulation. The sign of b is positive.\"", edge=c.ORANGE)
p.add("Step A (options only) passed the floor with 455 origins and 26 filled spans. No duplicate quotes, unmatched quotes, other roots, blank rates, or null-bid last rows appeared. Step B found 585 sessions in each source, with none in one source only, and the input stop did not fire. The largest calendar gap is 4 days.")
p.table([
    ["Sample", "n", "b", "Interval, 21 blocks", "Interval, 63 blocks"],
    ["<b>With events (verdict)</b>", "<b>455</b>", "<b>.281</b>", "<b>-.209 to .845</b>", "<b>-.232 to .937</b>"],
    ["No events", "418", ".351", "-.121 to .916", "-.168 to .925"],
    ["Tier 1 only", "245", ".411", "-.110 to 1.162", "-.026 to 1.367"],
    ["2017 PASO window dropped", "437", ".362", "-.108 to .919", "-.160 to .972"],
    ["2017 midterm window dropped", "436", ".262", "-.247 to .849", "-.244 to .910"],
], [2.7, .7, .7, 1.5, 1.5], "<b>Table 7. Coefficient on log implied variance, test period.</b> Only the first row decides the verdict. Intervals are nominal 95%, and the frozen code reports their real coverage as about 80% to 91%. Fixed-step mean b is .396 (22 sessions, range -.187 to .985, median t .69) and .384 (23 sessions, range -.177 to 1.509, median t .64).")
p.table([
    ["Same-row race, 271 rows from 2017-01-03", "Estimate", "Interval or t"],
    ["QLIKE, HAR+ATM30 minus HAR, Duan factor", ".0066", "-.0082 to .0249"],
    ["QLIKE, HAR+ATM30 minus HAR, no factor", ".0113", "-.0065 to .0332"],
    ["Clark-West on log loss, no factor, 21-session blocks", "-.0041", "t -.30"],
    ["Clark-West on log loss, no factor, 63-session blocks", "-.0041", "t -.27"],
], [4, 1, 1.5], "<b>Table 8. Out-of-sample comparison, test period.</b> A positive QLIKE difference favors HAR alone. Mean target .113. Mean forecasts: Duan .098 and .093, no factor .089 and .085, so all sit below the target.")
p.figure(c.FIGURES / "compare_technical.png", "<b>Figure 5. Test estimates against development estimates.</b> The overlap is large, so the test does not separate these sizes.", 3.1 / 7.2)
p.add("<b>Reading.</b> Rule 1 fails, because both lower bounds are below zero. \"Smaller than .37\" fails, because the upper bounds are .845 and .937. The upper bounds also exceed .525. So the test does not show information, and it does not rule out the development sizes. It is not evidence of no effect. Under the simulation in Figure 4, \"Inconclusive\" is only about 1.6 times as likely at b = 0 (56.2%) as at b = .62 (34.3%). That comparison assumes constant b and full coverage, so it is a rough guide to how little this outcome moves the evidence.")
p.add("The labels fail too. Clark-West is near zero and slightly negative, against t = 2.70 on open data, on far fewer rows. Both QLIKE signs agree and favor HAR, and both intervals include zero. A failed label is not evidence of no gain.")

p.add("7. Post-result notes", "h1")
p.callout("These notes came after the result, so they are not tests. Any analysis of this period from now on is development work.", edge=c.ORANGE)
p.bullets([
    "<b>A calmer regime.</b> Median " + I % "ATM30" + " is .334 in the test and .609 in open data. Median realized volatility is .311 and .520. The test range of ATM30 is .258 to .546, against .380 to 1.600. Less variation in implied variance can widen the interval. The simulations used development rows, so they may not reflect this.",
    "<b>Tier mix.</b> Tier 2 is 44.5% of test days and 30.4% of open days. b is higher on the Tier 1 subset (.411), the same direction as open data, but the intervals overlap heavily.",
    "<b>Events.</b> b rises when events drop (.351 against .281), the reverse of open data. Two events cannot support a conclusion. The rule that keeps events in did not change the verdict in any listed row.",
])

p.add("8. Discussion", "h1")
p.add("The positive development result rests on data that also shaped the method. It is concentrated in event windows and in the period after 2025-03, and evidence on ordinary days before 2025-03 is weak. The one frozen test could have supported or bounded this result. It did neither. The defensible statement is therefore narrow: in-sample evidence suggests information on open data, the size is unstable, no dependable forecast gain appears, and one low-power test of older, calmer data is uninformative.")
p.add("The test is backward in time. No later price enters it: the frame ends at 2018-04-30, and b and the forecast labels use test rows only. But the method, the rules, and the .37 limit came after contact with 2018-2026. So the test measures fit on unseen older data. It is not a real-time simulation, and known history cannot be removed.")

p.add("9. Limitations", "h1")
p.bullets([
    "<b>Power.</b> In the test, the fixed-step samples have median sizes of 21 and 20 rows. Clark-West has 271 scored rows, or about 13 separate 21-session blocks.",
    "<b>Interval coverage.</b> The nominal 95% intervals really cover about 80% to 91% in the study's simulation, and 87% to 91% in a later one (Section 12).",
    "<b>Exercise style and dividends.</b> Black inversion and put-call parity are applied to American options, and GGAL pays dividends of about 2% to 3.7% of the price. In a tree simulation (" + I % "audit/a05_american_bias.out" + ") the mean term IV error is at most 0.16% with no dividend (worst case 0.47%). With a 2% dividend inside the term, term IV is too high by 1.7% (30 days), 2.6% (20 days), and 5.1% (10 days). With a 3.5% dividend, it is too high by 4.6%, 6.7%, and 12.6%. 238 valid days have an ex-date in the front term. The index error is smaller than the term error, because both terms enter with weights. On real data, a tree correction does not move b and adds noise (Section 12). The correction is development work in " + I % "fixes/" + ", not in the study code.",
    "<b>Wide quotes and single-strike days.</b> The study code has no spread filter, and 30% of valid days use one strike (Section 3.1). Section 12 tests filters. Persistent quote error is untested.",
    "<b>Missing days.</b> Missing days depend on the expiry cycle. The results condition on days with a value.",
    "<b>Test closes.</b> Alpaca passed limits B1 to B6 on open dates: closes differ on 7 of 2,104 sessions, the largest gap is 17 bp, and b changes by .0002. This does not prove the same fit in 2016-2017.",
    "<b>2017 rights offering.</b> The offering ended on 2017-09-26. A summarized prospectus supplement says that the rights were not made available to ADS holders. Nasdaq and depositary records were not read, so the study has no cash row, and the close can show an unflagged step. The owner chose not to check this outside the study.",
    "<b>Input stop gap.</b> The adjacent-close condition removed false stops in simulation (16.7% to 0.0%), but two adjacent bad closes that agree pass it (87.6%-100% detection falls to 0.5%). The stop did not fire, so such a pair cannot be excluded.",
    "<b>Identification.</b> Nobody can yet separate the 2025 quote format break from a real market change. The test cannot help, because it ends before the break.",
])

p.add("10. Integrity record", "h1")
p.table([
    ["Review", "Main effect"],
    ["Plan debate, two agents, two rounds", "Moved the primary series to ATM30, added the backward test, and set RV on the exact 30-day window"],
    ["Stage 3 review, defender and attacker", "Corrected the reading of the race, the merged samples, and the smearing claims"],
    ["Stage 4 debate and judge simulation", "Set the verdict rules, the floor, and the \"Smaller than .37\" outcome"],
    ["Four independent checks of Stage 5", "Found blockers and gaps in failure paths. Each one reported \"Ready after listed fixes\""],
    ["Round of 2026-11-05", "Added the adjacent-close condition, three failure-path notes, and 21 tests. 247 tests passed, and 25 of 25 injected faults were caught. No independent agent reviewed this round"],
], [2.5, 5], "<b>Table 9. Review history.</b> The agents' reads of locked data are self-reported and unaudited.")
p.add("<b>Bugs found in Stage 3.</b> The rv21 rolling sum lost 20 origins. All 21 non-overlapping samples were identical. One selection column held the same-day return under a next-return label. Instrument rows used different days. All were fixed before the freeze.")
p.add("<b>Run record.</b>")
p.bullets([
    "The manifest hash at the run is 9214a2205f7a6078af41c3d8650b77a1d53bfa772bf14228be6d9d21ae883abc. The session compared it with the value printed at the freeze. The owner has not yet confirmed a match with their saved copy.",
    "The run has two attempts on the same hash: Step A only, then Steps A and B. No crash fix or refreeze occurred.",
    "The owner approved Step A and later said \"Lets continue to Step B\". The session read this as approval and wrote both markers. It had recommended that the owner write them.",
    "These runs are not in the access log in " + I % "PROTOCOL.md" + ", because an edit would change a frozen file. The run record and " + I % "HANDOFF.md" + " hold them. After the result, the session read the test panel for Figure 1 and the medians in Section 7.",
    "The session wrote both unlock markers. The protocol says that only the owner approves a marker (audit F15).",
    "The manifest hash in " + I % "HANDOFF.md" + " matches " + I % "reports/freeze_manifest.json" + " on 2026-11-10, and " + I % "freeze.differences()" + " returns an empty list (" + I % "fixes/f10_check_manifest.out" + "). Only the owner can compare the saved copy. Run " + I % "fixes/f10_check_manifest.py --saved &lt;hash&gt;" + " and record the result outside the frozen files.",
    "The builder checks the coefficients of Table 3 and Figure 3 against " + I % "reports/stage4_coefficients.csv" + ", and the numbers of Section 12 and Table 4a against the files in " + I % "fixes/" + ", at each build (audit F22). Other typed open-data numbers are not yet checked this way.",
])

p.add("11. Work not done", "h1")
p.numbered([
    "<b>Owner review.</b> Review this draft and compare the saved hash.",
    "<b>Forward test.</b> Data from after 2026-10-29 did not exist at the freeze, so a test on it would avoid the backward-test limit. It is not in the plan, and early results would have low power. It would need its own frozen rules.",
    "<b>Open data items.</b> Review the forward on 2022-07-08, which is more than 5% below the stock mid with no dividend. Finish the Stage 1 row-count reconciliation.",
    "<b>Open method items.</b> The cause of the spread gradient, persistent quote error, and other level rules. The American tree and the 5-minute HAR baseline were tested as development work in " + I % "fixes/" + " (Section 12). They are not in the study code, and the Clark-West and QLIKE races were not repeated with them.",
    "<b>Not done after the audit.</b> A literal CBOE-style series for 2024 onward, a real staleness rule (it needs the time of the last quote change, which the data does not give before 2025-03), the half-day fix, and calibrated intervals.",
    "<b>Unresolved plan numbers.</b> These debate values are not reproduced: level b .79 and .22, implied variance above RV in 79%, and 729 Tier 1 days. The plan ratio of 1.07 for ATM30/MF30 is probably inverted (the study has .946).",
    "<b>External question.</b> Databento has not answered how early cbbo-1m bars are built.",
])

p.add("12. Post-audit development checks", "h1")
p.callout("<b>This section is development work on open data (2018-05 to 2026-10), done after the one-time test.</b> It does not replace or modify the pre-registered Stage 5 result (\"Inconclusive\", b = .281). The numbers come from files in " + I % "fixes/" + ". The checks weaken the study as much as they support it, and the text reports both.", edge=c.ORANGE)
p.add("<b>Quote filters.</b> Each filter was set once before any b was computed. Table 10 shows the primary regression on the series that each filter leaves. The last column gives b of the stored series on the same origins.")
p.table([
    ["Series", "Valid days", "Origins", "b", "Newey-West t", "Interval, 21 blocks", "b, stored series, same origins"],
    ["Stored baseline", "1,846", "1,806", ".622", "4.13", ".337 to .916", ".622"],
    ["Near term at least 7 days (F9)", "1,597", "1,564", ".650", "4.21", ".368 to .965", ".650"],
    ["Strict last row (F7)", "1,837", "1,797", ".627", "4.14", ".340 to .924", ".627"],
    ["Spread at most .50 (F3)", "1,688", "1,650", ".668", "4.10", ".355 to 1.017", ".643"],
    ["Tier 1 only (F4)", "1,285", "1,245", ".703", "3.67", ".361 to 1.080", ".703"],
    ["Strict, spread .50, and Tier 1", "1,037", "1,003", ".835", "3.71", ".432 to 1.296", ".829"],
    ["All four filters", "966", "936", ".846", "3.66", ".440 to 1.324", ".840"],
    ["All four, spread .25 (sensitivity)", "728", "707", ".808", "2.73", ".312 to 1.478", ".811"],
    ["Stored series with the American tree", "1,846", "1,806", ".621", "4.17", ".342 to .912", ".622"],
], [2.6, .8, .8, .5, .9, 1.3, 1.3], "<b>Table 10. Quote-filter and American-tree variants.</b> Source: " + I % "fixes/f04_variants.csv" + ". Intervals are nominal 95%. Newey-West errors have 21 lags.")
p.bullets([
    "<b>Sample selection, not better measurement.</b> The filters remove days and leave the level of ATM30 almost unchanged. On the surviving days, the stored series gives almost the same b (.840 against .846 for all four filters). So the rise in b from .622 to .846 comes from the days that remain. It does not come from a better measure. The tests do not show that cleaning raises b.",
    "<b>Thinner sample, less precision.</b> The all-four series has 966 valid days against 1,846. Its Newey-West t falls from 4.13 to 3.66, and its bootstrap interval is wider (.440 to 1.324, against .337 to .916). With spread .25 it has 707 origins and t of 2.73. No variant gives a lower bound below zero in the 21-session bootstrap.",
    "<b>American tree (F2).</b> A tree inversion with the Nasdaq mid as spot and an escrowed dividend changes b very little: .621 with all dividends and .623 with confirmed dividends, against .622. On the all-four series plus tree, b is .848 on 931 origins, against .846 on 936. In simulation the tree removes the dividend bias. On real data the spot-based forward adds noise of about the same size as the effect, and the dividend amounts are partly unconfirmed.",
])
p.add("<b>Stronger HAR baseline (F5).</b> We rebuilt the HAR inputs from 5-minute mids of the Nasdaq " + I % "bbo-1m" + " file, plus the overnight return. The R² of the HAR baseline alone rises from .097 to .108. With IV added, b falls from .622 to .608. The Newey-West t falls from 4.13 to 3.35, and the 21-session interval widens from .337 to .916 to .283 to .970 (63-session blocks: .253 to .996). The result survives a stronger baseline, with less strength. We did not repeat the Clark-West and QLIKE races with this baseline.")
p.add("<b>Measured interval coverage (F13).</b> A Monte Carlo with 400 draws and fixed regressors gives the real coverage of the nominal 95% intervals in Table 11. The simulation error of each rate is about 1.6 points. Real regressors are random and persistent, so real coverage can differ.")
p.table([
    ["Series", "Bootstrap, 21 blocks", "Bootstrap, 63 blocks", "b ± 1.96 Newey-West"],
    ["Stored ATM30", "87.0%", "89.3%", "87.8%"],
    ["All four filters", "89.3%", "91.3%", "89.8%"],
], [2, 1.3, 1.3, 1.5], "<b>Table 11. Measured coverage of nominal 95% intervals.</b> Source: " + I % "fixes/f09_coverage.csv" + ". The study's own earlier simulation gave 80% to 91%.")
p.add("<b>Subsamples (F6).</b> The fragility remains after the fixes. The late period carries the large coefficient, and the early period is weaker.")
p.table([
    ["Period", "Stored: n", "Stored: b (t)", "All four: n", "All four: b (t)"],
    ["2018-2023", "1,165", ".526 (2.98)", "548", ".530 (1.99)"],
    ["2024-2025", "464", "1.185 (6.57)", "301", "1.362 (7.76)"],
    ["2026", "177", ".423 (1.01)", "87", "1.405 (2.63)"],
    ["Before 2025-03", "1,431", ".525 (3.25)", "729", ".646 (2.58)"],
    ["From 2025-03", "375", "1.190 (5.83)", "207", "1.619 (9.84)"],
], [1.6, 1, 1.4, 1, 1.4], "<b>Table 12. Coefficient b by period, Newey-West t in brackets.</b> Source: " + I % "fixes/f15_subsamples.csv" + ". HAR inputs are squared daily returns.")
p.add("<b>Reading.</b> The checks do not remove the main weaknesses. Filters raise b only by dropping days. A stronger baseline lowers b and its t-statistic. The Mincer-Zarnowitz test (Table 4a) rejects unbiasedness. The intervals cover less than 95%. The coefficient is large after 2025-03 and weak before. A tree correction for American exercise does not change b. The only clean confirmation is a forward test on data from after 2026-10-29, with rules frozen first.")

p.add("13. Conclusion", "h1")
p.add("On open data, GGAL implied volatility appears to add information about 30-day realized variance beyond past realized variance, but the size depends on events and period, and no dependable forecast gain appears. The frozen one-time test on 2016-01 to 2018-04 is inconclusive, with a positive sign. A method change from here makes that period development data, so further evidence must come from new data.")

p.add("Reproduction", "h1")
p.add(f"Environment: Conda {I % 'py4fi'}. Rules: {I % 'PROTOCOL.md'}. Tests: {I % 'python -m unittest discover -s tests'}. Result: {I % 'reports/stage5_result.json'}. The one-time run must not repeat. {I % 'HANDOFF.md'} holds the file map. The Databento data is licensed, so these results and files stay local unless the license permits otherwise.")

p.add("Appendix: disclosure as printed by the frozen code", "h1")
p.add(f.RESULT["disclosure"], "caption")

p.add("Appendix: audit note on the rebuild", "h1")
p.add("An independent rebuild of " + I % "ATM30" + " from the raw quotes matches the stored series to 1e-10 on 16 sample days and to 2e-5 on all 393 valid days after 2025-03. On 3 of those 393 days the rebuild differs by 3e-6 to 1.8e-5 (2025-11-11, 2025-10-13, 2026-10-12). The probable cause is the order of rows with equal timestamps. The effect is nil (audit F24).")

p.add("References", "h1")
p.add("These citations come from memory and were not checked against the sources. Verify them before any submission.", "caption")
for reference in (
    "Black, F. (1976). The pricing of commodity contracts. <i>Journal of Financial Economics</i>, 3.",
    "Canina, L., and Figlewski, S. (1993). The informational content of implied volatility. <i>Review of Financial Studies</i>, 6.",
    "Cboe Global Markets. <i>Cboe Volatility Index: VIX Methodology</i> (white paper; year and version not checked).",
    "Christensen, B., and Prabhala, N. (1998). The relation between implied and realized volatility. <i>Journal of Financial Economics</i>, 50.",
    "Clark, T., and West, K. (2007). Approximately normal tests for equal predictive accuracy in nested models. <i>Journal of Econometrics</i>, 138.",
    "Corsi, F. (2009). A simple approximate long-memory model of realized volatility. <i>Journal of Financial Econometrics</i>, 7.",
    "Duan, N. (1983). Smearing estimate: a nonparametric retransformation method. <i>Journal of the American Statistical Association</i>, 78.",
    "Mincer, J., and Zarnowitz, V. (1969). The evaluation of economic forecasts. In J. Mincer (ed.), <i>Economic Forecasts and Expectations</i>. National Bureau of Economic Research.",
    "Newey, W., and West, K. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. <i>Econometrica</i>, 55.",
    "Patton, A. (2011). Volatility forecast comparison using imperfect volatility proxies. <i>Journal of Econometrics</i>, 160.",
    "Politis, D., and Romano, J. (1992). A circular block-resampling procedure for stationary data. In R. LePage and L. Billard (eds.), <i>Exploring the Limits of Bootstrap</i>. Wiley.",
):
    p.add(reference, "reference")
p.build()
print("technical final written", m)
