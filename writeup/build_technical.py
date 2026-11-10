"""The technical status paper. Run from the project folder, with reportlab on PYTHONPATH."""
import common as c

c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
c.timeline_chart(c.FIGURES / "timeline.png")
c.forest_chart(c.FIGURES / "forest_technical.png", [
    ("All", (0.622, 0.337, 0.916), (0.459, 0.152, 0.715)),
    ("Before 2025-03", (0.525, 0.208, 0.862), (0.366, -0.018, 0.682)),
    ("From 2025-03", (1.190, 0.488, 1.516), (0.781, 0.227, 1.244)),
    ("2018-2023", (0.526, 0.192, 0.875), (0.364, -0.030, 0.721)),
    ("2024-2025", (1.185, 0.588, 1.469), (0.891, 0.429, 1.223)),
    ("2026 (no listed event)", (0.423, -0.387, 1.569), None),
], (7.2, 3.9))
c.outcomes_chart(c.FIGURES / "outcomes_technical.png", [("True b = 0", 4.0, 39.8, 56.2), ("True b = .25", 22.2, 12.3, 65.5), ("True b = .37", 34.8, 4.8, 60.3), ("True b = .50", 54.0, 1.7, 44.3), ("True b = .62", 65.5, 0.2, 34.3)], (7.2, 2.5))

p = c.Paper("Serif", 9.2, "Does implied volatility add information for GGAL ADR realized variance?", c.STATUS_LINE, c.HERE / "GGAL_study_technical_version.pdf")

p.add("Does implied volatility add information for GGAL ADR realized variance?", "title")
p.add("Design, development results, and status of a pre-specified one-time test. Working paper, draft of 2026-11-05, prepared with Claude Code from the project records. Not peer reviewed.", "subtitle")
p.add("Abstract", "h2")
p.add("We build a 30-day near-the-money implied volatility series (<font name='Serif-Italic'>ATM30</font>) for GGAL ADR options and test whether it adds information about 30-day realized variance beyond a HAR baseline. On open data from 2018-05 to 2026-10 (1,806 origins), the coefficient on log implied variance is .622, with a 95% block-bootstrap interval of .337 to .916. The estimate is unstable. It falls to .459 with election windows dropped and to .366, with an interval that includes zero, for non-event origins before 2025-03. On same-row, out-of-sample comparisons, Clark-West t is 2.70 with 21-session blocks, but the QLIKE gain has an interval that includes zero (-.0187, from -.0444 to .0115). These results are exploratory, because the method changed after contact with the data. We therefore froze the method and verdict rules before a one-time test on 2016-01 to 2018-04. Its options-only step passed the data floor on 2026-11-05, with 492 <font name='Serif-Italic'>ATM30</font> days and 455 valid origins. <b>The outcome step has not run, so this paper reports no confirmatory result.</b>")

p.add("1. Introduction", "h1")
p.add("The information content of implied volatility is a long-standing question (Canina and Figlewski, 1993; Christensen and Prabhala, 1998). GGAL ADR is a useful case. It has large scheduled political risk and an option chain whose depth varies strongly over time. The project began as an adaptation of a VIX-style model-free index. Data checks in a two-agent plan debate changed the headline: at least 5 out-of-the-money bids per wing on both expiries occurred on 0% to 1% of days in 2018-2023. The primary series therefore became <font name='Serif-Italic'>ATM30</font>. The model-free series <font name='Serif-Italic'>MF30</font> stays descriptive, with 512 sessions from 2024 onward, and it enters no regression.")
p.add("The contribution of this paper is mainly procedural at this stage. It records a method, a development evidence base, and a frozen verdict rule before the only unused data are read. This matters because the development analysis shows strong sensitivity to event windows, training start, and level correction.")

p.add("2. Data", "h1")
p.table([
    ["Source", "Use", "Coverage and notes"],
    ["Databento cbbo-1m, definitions, GGAL root", "Option quotes", "Open 2018-05-01 to 2026-10-29. Test 2016-01 to 2018-04. Adjusted roots are out of scope by user decision"],
    ["Official equity daily table", "Development closes", "2,137 sessions"],
    ["Alpaca SIP daily bars", "Test closes", "2,689 bars. Compared with official closes on open dates only"],
    ["FRED DGS1MO, DGS3MO", "Discount rates", "Continuous, linear in days, flat outside 30 and 91 days, prior observation only"],
    ["<font name='Serif-Italic'>adr_cash_events.csv</font>", "Total return", "33 dividends and the 2025 rights value, in USD per ADS. Two dividends fall in the test. Their rate and date come from a vendor, with no record date or tax basis"],
], [2.2, 1.1, 3.6], "<b>Table 1. Inputs.</b> Nasdaq bbo-1m data supported 5-minute review checks only.")
p.figure(c.FIGURES / "timeline.png", "<b>Figure 1. Period roles.</b> The 2026 data are open and reported separately. They are not a blind forward test.", 1.75 / 7.2)

p.add("3. Method", "h1")
p.add("3.1 Implied volatility series", "h2")
p.add("At 15:45 New York, take the last quote per contract from 09:30, with a quote age of at most 30 minutes for the primary series. A valid pair has a call and a put at one strike, each with 0 &lt; bid ≤ ask. Parity at the two-sided strike with the smallest |C − P| gives the forward:")
p.add("F = K + e<super>rT</super> (C − P)", "equation")
p.add("Term IV inverts Black (1976) on the discount-adjusted call-put average, with linear interpolation of IV in log strike between the two strikes nearest F. Each strike is at most 25% in absolute log distance from F. Total variance is interpolated to 30 days between the two listed expiries that bracket 30 days, with no extrapolation. A failed expiry leaves the day missing, and no missing day is imputed. Tier 1 has a bracketed forward, or a strike at the forward, on each term. Tier 2 has one strike on at least one term.")
p.add("3.2 Realized variance and primary regression", "h2")
p.add("With total log returns r, including cash on the ex-date, the target for origin t uses sessions in (t, t + 30 calendar days]:")
p.add("RV30<sub>t</sub> = (365 / 30) Σ<sub>s ∈ (t, t+30d]</sub> r<sub>s</sub>²", "equation")
p.add("log RV30<sub>t</sub> = c + β<sub>1</sub> log RV<sub>1,t</sub> + β<sub>5</sub> log RV<sub>5,t</sub> + β<sub>22</sub> log RV<sub>22,t</sub> + b log ATM30<sub>t</sub>² + ε<sub>t</sub>", "equation")
p.add("This is a HAR specification (Corsi, 2009) with implied variance added. HAR inputs are log annualized RV through the origin close, with a floor of 1e-6 on mean daily variance. Inference uses circular block bootstraps of 21 and 63 sessions on the full session grid, with 2,000 resamples of row pairs, and 2.5th and 97.5th percentiles. Overlap makes the effective sample small. Newey-West errors with 21 lags are for comparison only. Fixed-step samples of 22 and 23 sessions are reported, and they replaced a first-valid-session scheme whose paths merged.")
p.add("3.3 Forecast comparison", "h2")
p.add("Models refit by OLS in logs at each origin, using rows whose target window ends on or before the origin. Scoring starts at position 252, with at least 126 training rows. The level correction is the Duan (1983) smearing factor, and the no-factor result is reported beside it. Information uses Clark and West (2007) on log loss, because HAR is nested in HAR+ATM30. Usable gain uses QLIKE (Patton, 2011), L = y/f − log(y/f) − 1, on the same rows.")
p.add("3.4 Events", "h2")
p.add("The event list was set in advance: nine elections in 2019-2025 for open data, and the 2017 PASO and midterm for the test. Event work compares forward variance between expiries that straddle an event with placebo dates. It reports no p-values, and the placebos share dates.")

p.add("4. Development results", "h1")
p.callout("All results in this section are exploratory. The method and the review checks came after contact with these data.", edge=c.ORANGE)
p.figure(c.FIGURES / "forest_technical.png", "<b>Figure 2. Coefficient on log implied variance.</b> The intervals use 21-session blocks. Simulation puts their real coverage at about 80% to 91%, so they are too narrow. Source: <font name='Serif-Italic'>reports/stage4_descriptive.md</font>.", 3.9 / 7.2)
p.table([
    ["Sample", "n", "b", "Interval, 21 blocks", "Interval, 63 blocks"],
    ["All, with events", "1,806", ".622", ".337 to .916", ".309 to .946"],
    ["All, no events", "1,643", ".459", ".152 to .715", ".060 to .761"],
    ["Before 2025-03, with events", "1,431", ".525", ".208 to .862", ".152 to .922"],
    ["Before 2025-03, no events", "1,300", ".366", "-.018 to .682", "-.131 to .717"],
    ["From 2025-03, with events", "375", "1.190", ".488 to 1.516", ".330 to 1.516"],
    ["From 2025-03, no events", "343", ".781", ".227 to 1.244", ".149 to 1.415"],
], [2.7, .7, .7, 1.5, 1.5], "<b>Table 2. Primary coefficient.</b> R² rises from .097 for HAR to .177 with IV on all rows.")
p.bullets([
    "<b>Concentration (review check, one agent).</b> Event rows are 9% of rows and supply 57% of the in-sample squared-error gain. Non-event rows before the break are 72% of rows and supply 11%.",
    "<b>Fixed-step samples.</b> Mean b is .611 and .602 for steps of 22 and 23 sessions, and .500 and .493 with no 2019 PASO windows. These samples share periods, so they are not independent.",
    "<b>Instability.</b> Yearly b runs from -.380 in 2022 to 1.379 in 2025. Leave-one-year-out b stays from .542 to .707.",
    "<b>Quote quality.</b> b is .703 on Tier 1 and .435 on Tier 2. Within years, spread terciles give .884, .698, and .373. The cause is open. Short-lived noise looks small, and persistent quote error is untested.",
    "<b>Events.</b> The event ratio is above the placebo median at all nine events, with a margin of only .004 at the 2025 midterm. Around the 2019 PASO, forward vol was .576 and realized vol between the same expiries was 3.04.",
    "<b>Variance risk premium.</b> ATM30² minus RV has a mean of -.041 and a median of +.105.",
])
p.table([
    ["Same-row race, 1,599 rows from 2019-05-02", "Estimate", "Interval or t"],
    ["QLIKE, HAR+ATM30 minus HAR, Duan factor", "-.0187", "-.0444 to .0115"],
    ["QLIKE, HAR+ATM30 minus HAR, no factor", ".0002", "-.0339 to .0375"],
    ["Clark-West on log loss, no factor, 21-session blocks", ".0624", "t 2.70"],
    ["Clark-West on log loss, no factor, 63-session blocks", ".0624", "t 2.07"],
], [4, 1, 1.5], "<b>Table 3. Out-of-sample comparison.</b> A negative QLIKE difference favors HAR+ATM30. Mean target .484. Mean Duan forecasts about .625. Mean no-factor forecasts .352 and .368. So each level rule has a bias.")
p.add("Earlier QLIKE differences ranged from -.077 to .000 across smearing, training, and row choices. The training start alone moved one value from -.043 to -.077 on the same rows, because common training days removed 2018-06 to 2019-04 from HAR. We read this as evidence of information, with no dependable usable gain.")

p.add("5. The frozen test", "h1")
p.add("The test falls entirely before the 2025-03 quote format break. It can therefore test the weak ordinary-day evidence, but it cannot explain the change after the break. The verdict depends only on Rule 1.")
p.table([
    ["Element", "Rule"],
    ["Rule 1 (verdict)", "b in HAR+IV has a lower bound above zero in both percentile intervals: 21-session and 63-session blocks, 2,000 resamples"],
    ["Rule 2 (label)", "Clark-West on log loss, no level factor, 21-session blocks, t above 1.65 on at least 180 scored rows. Adds \"also out-of-sample\""],
    ["Rule 3 (label)", "QLIKE difference with the Duan factor has a 97.5th percentile below zero. Adds \"with usable gain\""],
    ["Data floor", "At least 300 valid origins, and at least 20 of the 21-session spans hold 10 or more valid origins"],
    ["Input stop", "Before any result, the near forward is compared with the close. Stop if the median absolute log gap is above .02, more than 5% of rows are above 5%, the largest gap is above .15, or more than 3 sessions are in one source only. Listed data faults also stop the run"],
    ["No-forward check", "Stop only if a close on a no-forward session is above .15 from the nearest forward on both sides and above .15 from both adjacent closes"],
    ["Outcomes, first match wins", "(0) Inconclusive, inputs failed. (1) Inconclusive, data floor. (2) Supported. (3) Smaller than .37, if both upper bounds are below .37. (4) Inconclusive, with the sign of b"],
    ["Verdict line", "States the period and the real coverage of about 80% to 91%. Adds \"With events only; the ordinary-day question stays open\" if \"Supported\" holds and a no-event interval includes zero"],
], [1.25, 5], "<b>Table 4. Frozen rules.</b> <font name='Serif-Italic'>PROTOCOL.md</font> holds the full text. Clark-West is a label by user decision.")
p.add("<b>Power.</b> The two simulations in the Stage 4 plan assume constant b and use development rows. Figure 3 shows the advocate's run with 600 replications per value. The separate judge run gives \"Supported\" at 3.8%, 34.6%, and 69.2% for b of 0, .37, and .62. Both debate agents agree that the bootstrap standard error is too small, with SD of b over median SE near 1.3 to 1.5. Since 0 and .37 are only about 1.0 to 1.25 SD apart, no rule removes the low power. The user accepted this.")
p.figure(c.FIGURES / "outcomes_technical.png", "<b>Figure 3. Simulated outcome rates by true b, at full coverage.</b> Segments below 3.5% carry no number: 1.7% at .50 and 0.2% at .62. Rows can sum to 99.9% or 100.1% after rounding. Labels are subsets of \"Supported\". Source: <font name='Serif-Italic'>STAGE4_PLAN.md</font>.", 2.5 / 7.2)

p.add("6. Integrity controls and review history", "h1")
p.bullets([
    "<b>Date gate.</b> Readers call a gate that blocks the test period. It opens only with a valid marker of the right scope: options for Step A, and outcomes for Step B.",
    "<b>Freeze.</b> A SHA-256 manifest covers all code, tests, rules, and inputs. The rules were not filed with an outside registry. The current manifest hash is 9214a2205f7a6078af41c3d8650b77a1d53bfa772bf14228be6d9d21ae883abc. The folder has no git history, so the manifest gives evidence of a change, and it does not prevent one.",
    "<b>Leak control.</b> Step B calculates in memory and writes one result. Errors print type and code location only. An input stop keeps dates, with no values.",
    "<b>Run rules.</b> A logged fix is allowed until an outcome is displayed or written. After that, a method change makes the period development data.",
])
p.table([
    ["Review", "Main effect"],
    ["Plan debate, two agents, two rounds", "Moved the primary series to ATM30, added the backward test, and set RV on the exact 30-day window"],
    ["Stage 3 review, defender and attacker", "Corrected the reading of the race, the merged samples, and the smearing claims"],
    ["Stage 4 debate and judge simulation", "Set the verdict rules, the floor, and the \"Smaller than .37\" outcome"],
    ["Four independent checks of Stage 5", "Found blockers and gaps in failure paths, such as the input stop, the floor end path, and leaks under write faults. Each one reported \"Ready after listed fixes\""],
    ["Round of 2026-11-05", "Added the adjacent-close condition, three failure-path notes, and 21 tests. 247 tests pass, and 25 of 25 injected faults are caught. No independent agent reviewed this round"],
], [2.5, 5], "<b>Table 5. Review history.</b> The agents' reads of locked data are self-reported and unaudited.")
p.add("<b>The no-forward decision.</b> The earlier check stopped on clean closes in 16.7% of 600 random 585-session windows when the real blank pattern was moved. With the adjacent-close condition, this fell to 0.0%. Moving the pattern breaks any link between blank days and quiet periods, so the 16.7% can be too high. The cost is real. For one bad close multiplied by 1.15, detection falls from 19.2% to 9.8%. For two adjacent bad closes with the same factor, on 193 blank pairs, detection falls from 87.6%-100% to 0.5%. The user kept the condition with this information.")

p.section("7. Current status: Step A", 7)
p.table([
    ["Year", "Sessions", "ATM30 present", "No two-sided pair", "No listed bracket", "Coverage"],
    ["2016", "252", "200", "38", "14", "79.4%"],
    ["2017", "251", "214", "25", "12", "85.3%"],
    ["2018, to April", "82", "78", "1", "3", "95.1%"],
    ["All", "585", "492", "64", "29", "84.1%"],
], [1.5, 1, 1.2, 1.3, 1.3, 1], "<b>Table 6. Step A, read from options only.</b> Floor: 455 origins and 26 filled spans, so it passed. Tier 1 and Tier 2 days: 273 and 219. No duplicate quotes, unmatched quotes, other roots, blank rates, or null-bid last rows.")
p.add("The closes and returns stay unread. One count deserves attention before Step B. Tier 2 is 44.5% of test days, against 30.4% of open days (561 of 1,846). On open data, b is lower on Tier 2 days. The simulated power does not include this. This comparison is descriptive, and it does not change any rule.")

p.add("8. Limitations", "h1")
p.bullets([
    "<b>Exercise style and dividends.</b> Black inversion is applied to American options. The planned American tree sensitivity is not done.",
    "<b>Selection.</b> Missing days depend on the expiry cycle. Coverage is about .68 with 0-6 days to the near expiry, and .94 to .97 with more days.",
    "<b>Test closes.</b> Alpaca passed limits B1 to B6 on open dates: closes differ on 7 of 2,104 sessions, the largest gap is 17 bp, and b changes by .0002. This does not prove the same fit in 2016-2017.",
    "<b>2017 rights offering.</b> The offering ended on 2017-09-26. A summarized prospectus supplement says that the rights were not made available to ADS holders. Nasdaq and depositary records were not read, so the study has no cash row, and the close can show an unflagged step.",
    "<b>Contact with locked data.</b> The user states no contact with 2016-2018 prices. Dividend rows, bar counts, and dates were printed, and code parses held locked rows in memory. One agent saw 2017 prices in public sources and did not pass them on. The result discloses this.",
    "<b>Backward test.</b> No later price enters the test, because the frame ends at 2018-04-30, and b and the forecast labels use test rows only. But the method, the rules, and the .37 limit came after contact with 2018-2026. The test measures fit on unseen older data. It is not a real-time simulation, and known history cannot be removed.",
    "<b>Identification.</b> Nobody can yet separate the 2025 quote format break from a real market change.",
    "<b>Untested paths.</b> The rehearsal used open data. Step B has not run on the real 2016-2018 closes, so a layout problem there would fall under the crash rule.",
    "<b>Process.</b> Step A's run is recorded in the run record and <font name='Serif-Italic'>HANDOFF.md</font>, not in the frozen access log. The session wrote the options marker with the user's stated approval. The hash comparison used the manifest file, not the user's saved copy.",
])

p.add("9. Work not yet done", "h1")
p.numbered([
    "<b>Step B.</b> It needs the user's approval and a comparison of the saved hash. It gives one result or an input stop.",
    "<b>Final write-up (Stage 6).</b> It must include American exercise and dividends, missing-day selection, low power, and the disclosures above.",
    "<b>Open data items.</b> Review the forward on 2022-07-08, which is more than 5% below the stock mid with no dividend. Finish the Stage 1 row-count reconciliation.",
    "<b>Open method items.</b> The cause of the spread gradient, persistent quote error, the American tree sensitivity, and other level rules and 5-minute measures in study code.",
    "<b>Unresolved plan numbers.</b> These debate values are not reproduced: level b .79 and .22, implied variance above RV in 79%, and 729 Tier 1 days. The plan ratio of 1.07 for ATM30/MF30 is probably inverted (the study has .946).",
    "<b>Possible forward test.</b> Data from after 2026-10-29 did not exist at the freeze, so it would avoid the backward-test limit. It is not in the plan, and early results would have low power.",
    "<b>External question.</b> Databento has not answered how early cbbo-1m bars are built.",
])

p.add("10. Reproduction", "h1")
p.add("Environment: Conda <font name='Serif-Italic'>py4fi</font>. Rules: <font name='Serif-Italic'>PROTOCOL.md</font>. Tests: <font name='Serif-Italic'>python -m unittest discover -s tests</font>. Rehearsal: <font name='Serif-Italic'>run_tests_once.py --rehearse 2020-01-01 2022-04-30</font>. The Databento data is licensed, so these results and files stay local unless the license permits otherwise. <font name='Serif-Italic'>HANDOFF.md</font> holds the file map and the approval steps.")

p.add("References", "h1")
p.add("These citations come from memory and were not checked against the sources. Verify them before any submission.", "caption")
for reference in (
    "Black, F. (1976). The pricing of commodity contracts. <i>Journal of Financial Economics</i>, 3.",
    "Canina, L., and Figlewski, S. (1993). The informational content of implied volatility. <i>Review of Financial Studies</i>, 6.",
    "Christensen, B., and Prabhala, N. (1998). The relation between implied and realized volatility. <i>Journal of Financial Economics</i>, 50.",
    "Clark, T., and West, K. (2007). Approximately normal tests for equal predictive accuracy in nested models. <i>Journal of Econometrics</i>, 138.",
    "Corsi, F. (2009). A simple approximate long-memory model of realized volatility. <i>Journal of Financial Econometrics</i>, 7.",
    "Duan, N. (1983). Smearing estimate: a nonparametric retransformation method. <i>Journal of the American Statistical Association</i>, 78.",
    "Patton, A. (2011). Volatility forecast comparison using imperfect volatility proxies. <i>Journal of Econometrics</i>, 160.",
):
    p.add(reference, "reference")
p.build()
print("technical written")
