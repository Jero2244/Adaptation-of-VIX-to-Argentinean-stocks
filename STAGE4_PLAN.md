# Stage 4 plan: freeze the method and the verdict rules

Written 2026-11-04. **Status: the user approved this plan on 2026-11-04, and steps 2 to 9 are done.** Step 10 waits for the user. The rules are in `PROTOCOL.md`, which overrides this file where they differ. After an independent check, the user added an input stop and changed the run procedure. Those changes are only in `PROTOCOL.md` and the code. The expected rates below do not include the input stop, which should not fire on clean data.

Stage 4 does not run the one-time test, and it does not create an unlock marker.

## Source

A draft went through two debate rounds between an advocate and a critic. I judged the disputes and ran a separate simulation. All these checks are exploratory, and they read open pre-2025-03 panel rows. Files are in `review/stage4_debate/`.

## Questions for the user

Get these answers before any other step.

1. **Do you accept the power, and should Stage 5 run at all?** Recommendation: run it, because it is the only unused data. Expect "Inconclusive" as a likely result.
2. **Should Clark-West be a label or a requirement?** Recommendation: a label. This changes the recommendation in `HANDOFF.md` and `reports/stage3_findings.md`. A requirement fits better if the user wants a false-pass rate near 2%, but "Supported" then falls to 21.5% at a true `b` of .37.
3. **Did you or anyone else see 2016-2018 prices?** The Alpaca file came from another project, so the test may not be fully clean. If someone saw them, the verdict must say so. The files cannot answer this.
4. **Do you accept the outcome "Smaller than .37"?** Recommendation: yes. The alternative is a sign rule: "Not supported" if `b` is at or below zero.
5. **Do you accept the method rules?** These are the Stage 2 rules, the Stage 3 rules in `PROTOCOL.md`, and the choices in the section "Method choices".

The user has also not yet reviewed the Stage 3 results. Show `reports/stage3_findings.md` first.

## Role of each period

- 2018-05 to 2026-10 is seen data. It gets a frozen descriptive report and no verdict.
- 2016-01 to 2018-04 is the only period that gets a verdict.
- The test falls entirely before the 2025-03 format break, so it cannot explain the change after that date.
- It has at most 25 to 26 non-overlapping windows in each fixed-step sample, and about 14 to 15 in Clark-West. The earlier "about 28 windows" overstates the sample.

## Verdict rules

All rules apply to 2016-01 to 2018-04 only.

**Rule 1, information (decides the verdict).** Pass if `b` on `log_iv2` (log `ATM30` squared) in HAR+IV has a lower bound above zero in both percentile bootstrap intervals: 21-session and 63-session blocks, 2,000 resamples, 2.5th and 97.5th percentiles, seed 20261104. Fixed-step samples (22 and 23 sessions, 45 samples) are reported as mean `b`, range, and median t. They do not decide the verdict.

**Rule 2, out-of-sample information (label).** Clark-West on log loss, with HAR nested in HAR+ATM30. Both models train on the same `primary` rows, and each target window ends on or before the origin. Start at position 252, with at least 126 training rows and 21-session blocks. The label needs t above 1.65 on at least 180 scored rows.

**Rule 3, usable gain (label).** It applies only if Rule 1 passes. The QLIKE difference of HAR+ATM30 minus HAR with the Duan factor has a 97.5th percentile below zero. Report the no-factor result and mean forecast over mean target beside it. If the two signs differ, the verdict line says so. A fail is not evidence of no gain.

**Data floor.** At least 300 valid origins. Divide the sessions from the first valid origin into consecutive 21-session spans. At least 20 spans must hold 10 or more valid origins. Each target window ends on or before 2018-04-30. The test frame is not joined to data from 2018-05 onward. Check the floor from flags, before any return is read.

**Outcomes.** Apply in order. The first match is the outcome.

1. "Inconclusive, data floor" if the floor fails.
2. "Supported" if Rule 1 passes. Add "also out-of-sample" if Rule 2 passes. Add "with usable gain" if Rule 3 passes.
3. "Smaller than .37" if both upper bounds of `b` are below .37. This says that the test does not reach the lowest development estimate (.37, no events, before 2025-03). It does not say that `b` is zero. The development value with events is .525, and the report shows the upper bounds against both values.
4. "Inconclusive" in all other cases. State the sign of `b`.

**Each verdict line states:**
- "2016-01 to 2018-04 only".
- That the "95%" intervals really cover about 80% to 91% in simulation.
- "With events only; the ordinary-day question stays open", if "Supported" holds and either no-event interval includes zero.

Events stay in for the verdict, because IV should price scheduled events. The no-event result has equal rank in the report.

**Reported, with no effect on the verdict:** fixed-step mean `b` and median t, upper bounds against .37 and .525, no-factor QLIKE, Tier 1 only, and each 2017 event dropped.

## Expected results

Simulation with a known `b`, advocate's runs, `advocate/a8_final.txt`. 600 replications per true `b`, full coverage.

| True `b` | Supported, any form | Also out-of-sample | With usable gain | Smaller than .37 | Inconclusive |
|---|---|---|---|---|---|
| 0 | 4.0% | 2.0% | 1.5% | 39.8% | 56.2% |
| .25 | 22.2% | 12.2% | 6.2% | 12.3% | 65.5% |
| .37 | 34.8% | 21.5% | 8.2% | 4.8% | 60.3% |
| .50 | 54.0% | 38.8% | 17.3% | 1.7% | 44.3% |
| .62 | 65.5% | 50.0% | 20.0% | .2% | 34.3% |

The labels are subsets of "Supported", and they can overlap.

My separate simulation (`judge/j1_check.py`, `judge/j1.out`, 240 replications per true `b`, other windows, a 42-session residual block, and the study's `block_sample`) gives "Supported" 3.8%, 34.6%, 69.2%, and "Smaller than .37" 38.3%, 5.0%, .8%, at `b` = 0, .37, .62.

**Limits:**
- These rates assume a constant `b` and use development rows. 2016-2018 can behave differently, and its IV variance is unknown.
- At coverage .53, the rates are 5.4% at `b` = 0, 28.8% at .37, and 50.8% at .62.
- The dry runs on seen windows show rule behaviour only. They are not evidence for the claim. They hold about two or three independent results.

## Why the rules changed from the draft

| Issue | Draft | Result | Reason |
|---|---|---|---|
| Rule 1 | Interval and fixed-step t | Both intervals | The t has no known null distribution, and it drove the verdict. The threshold 1.30 came from a dry run |
| Clark-West | Required | Label | See below |
| Usable gain | Duan and no factor | Duan only, no factor beside it | Duan is the QLIKE-best scale in training. No-factor forecasts are too low |
| Negative outcome | "Not supported" | "Smaller than .37" | At a true `b` of .37, it fires about 5% of the time. A sign rule fires about 13% |
| Data floor | 20 windows, not defined | 300 origins and 20 filled spans | The draft floor failed 13 of 28 real windows, including all 4 "Supported" results |

**Clark-West, my ruling:** A required pass cuts false passes from 4.0% to 2.0%, but it also cuts "Supported" from 34.8% to 21.5% at a true `b` of .37. Given that both intervals pass, it passes 50% at `b` = 0, 62% at .37, and 76% at .62. So it adds some evidence but not much, and Clark-West t and `b` correlate at about .88 across real windows. The label keeps both levels of evidence visible.

**The .37 limit, my ruling:** The critic objected that .37 has events dropped while the test keeps events in. This makes the limit cautious, so I kept it and report .525 too.

**Agreed by both agents:** The bootstrap standard error is too small (SD of `b` over median SE is about 1.3 to 1.5). A fixed correction does not work, because the factor depends on the setting (.96 to 1.44). So no rule removes the low power: 0 and .37 are only about 1.0 to 1.25 SD apart.

## Method choices

| Item | Choice | Note |
|---|---|---|
| Non-overlapping samples | Fixed steps of 22 and 23 sessions | Replaces first-valid-session, because those paths merge |
| Training | HAR and HAR+ATM30 train on the same rows: all `primary` rows with a target window that ends on or before the origin. No row needs a GARCH or EWMA value | Avoids dropping 2018-06 to 2019-04 from HAR |
| Level rule | Duan factor decides. No factor is reported | Must not name 2019 |
| GARCH | t errors primary, normal errors reported | No effect on the verdict |
| EWMA | Lambda .94. .98 is a sensitivity run | No effect on the verdict |
| Floors | 126 training rows, daily variance 1e-6 | Unchanged |
| Stage 2 rules | Accepted as written | 25% strike limit, log-strike IV, prior-day yield, no skip of a failed expiry |
| Headlines | Each states with and without events, and the period | Findings item 5 |

These choices touched development results, not test outcomes. So a freeze keeps the test clean, even though the choices came after contact with the open data.

## Work steps

1. **Get answers.** Show the user `reports/stage3_findings.md`, and get answers to the questions above. Do not continue before this step.
2. **Update the study code.** Add these with unit tests: fixed steps of 22 and 23 sessions, Clark-West, same-row training, and Duan and no-factor races side by side. Rerun `run_development.py` on the open data, and match `review/verify_debate.txt`. Explain any difference. Write the frozen descriptive report.
3. **Fix the gate.**
   - `config.py:47` uses `.exists()`, so any empty file opens the marker. Require valid marker content.
   - Use two markers: one for options (Step A) and one for outcomes (Step B).
   - Update `tests/test_inputs.py:32,36`, which write `{}` as a marker.
   - `iter_days` has no marker argument (`load_data.py:49`). Pass the marker through.
   - `build_series.py:78` and `realized.py:25` read `adr_cash_events.csv` with no gate. Filter by ex-date.
4. **Add the Alpaca reader.** `data/source/alpaca_ggal_sip_raw.json` has no gated reader, and nobody may inspect it to learn its layout.
   - Write one function, `load_alpaca_closes(start, end, marker=...)`, in `load_data.py`. No other code opens the file.
   - Call `require_open` before the file opens.
   - The file is one JSON document, so a full parse is necessary. Filter by New York date right after the parse, and delete the unfiltered object. So the blindness comes from the code path, and it is not physical.
   - Assert the minimum and maximum dates before return. Errors hold no values, so a traceback cannot print a row.
   - A separate layout helper prints only key names, value types, and row counts. It prints no dates or prices.
   - Write the filtered open rows once to `data/alpaca_open_closes.parquet`. The comparison reads only this file.
   - Test on a synthetic file with 2017 and 2018 rows, including a boundary bar on 2018-04-30 at a late UTC time.
   - Log the contact in the access log. State that the parse held locked rows in memory, and that no value was shown.
   - Do not open other files in `research/stock_history_check_20260915/`.
5. **Compare Alpaca with official closes, on open dates only.** Compute on all overlap dates, and again on 2018-05 to 2019-07 for the close and RV limits.

   | ID | Measure | Limit | If it fails |
   |---|---|---|---|
   | B1 | Sessions in one source only | At most 3 | Find the cause, fix the reader, rerun, log |
   | B2 | Signed median log(Alpaca / official) | At most 5 bp in size | Same as B1. It catches an adjusted series |
   | B3 | Absolute median | At most 10 bp | Stage 4 stops, and the user decides |
   | B4 | Absolute 99th percentile | At most 100 bp | Stage 4 stops, and the user decides |
   | B5 | Median absolute log(RV30 ratio) | At most .05 | Stage 4 stops, and the user decides |
   | B6 | Change in `b`, pre-break primary rows, Alpaca RV and HAR | At most .03 | No verdict with Alpaca RV. The user drops Stage 5, or reports the test as descriptive only |

   These limits use assumed noise sizes, because nobody has read the Alpaca file. Any change of a limit needs a logged user decision. A pass on open dates does not prove the same fit in 2016-2017, and the verdict line says this.
6. **Build the test series separately.** `build_snapshot.py` cannot do this. It overwrites `data/source/fred_rates.csv` first, its outputs overwrite open files, and it zips with XNAS data that starts in 2018-05.
   - Write a separate build with separate output files and a separate test panel. `run_development.py:504` writes the open panel, and it must not change.
   - Fetch rates into a separate file that starts before 2016-01-04, for example at 2015-12-01. Each session uses the last prior observation. `FRED_URL` starts at 2018-01-01.
   - Add a separate `TEST_EVENTS` list for the 2017 PASO and midterm. `first_session` (`events.py:28`) moves 2017 dates to 2018-05-01 on the open session grid.
   - Use the two 2016 and 2017 dividend rows from `adr_cash_events.csv`.
7. **Write `run_tests_once.py`.**
   - Check the manifest before the run.
   - **Step A:** Read options only, and print counts only. Check the floor. If it fails, the Alpaca outcomes stay unread, and `PROTOCOL.md` ("Floor failure in Step A") states when "Inconclusive, data floor" becomes final. Step A needs the session grid from option days.
   - **Step B:** Read Alpaca, and recheck the floor, session counts, and gaps. Print counts only. Calculate all outcomes in memory, suppress values in tracebacks, and write one result file at the end.
   - Allow one test-run marker, and refuse a second run.
   - **Crash rule:** A logged fix is allowed until any outcome is displayed or written. After that, a method change makes the period development data.
   - Freeze the seeds, resamples, percentile type, and descriptive list.
8. **Rehearse.** Run the same code on synthetic data and on one open 28-month window, for example by date arguments that a unit test covers.
9. **Freeze.** Record the rules in `PROTOCOL.md`, and mark it frozen. Write a SHA-256 manifest of the code, `PROTOCOL.md`, and input files, because this folder has no git history. The user keeps the hash of the manifest outside this folder. This gives evidence of changes, but it does not prevent them.
10. **Stop.** Ask the user before Stage 5. Do not create a marker without the user's approval.

## Do not do

- Do not read 2016-01 to 2018-04 data, or open the Alpaca file, before the steps above permit it.
- Do not reopen the `GGAL1` question. Do not add a 2026 gate.
- Do not publish or commit Databento data, or files derived from it. This includes the debate outputs in `review/stage4_debate/`.

## Limits of this plan

- A "Supported" verdict can come from the 2017 events, so it may not answer the ordinary-day question.
- Nobody has built the test series, so its coverage and chain quality are unknown.
- The agents report that they read no locked data. I checked that the marker does not exist, but I did not audit their reads.
- I did not rerun the debate scripts from their new folder. `judge/j1_check.py` has an absolute path to the session scratchpad, so it needs a path change.
