# Advocate, round 2: response to the critic

All checks are exploratory, on open pre-2025-03 panel rows. No locked data, no Alpaca file, no marker. `reports/` has no `backward_test` file (checked after the runs).

**Summary:** The critic is right on most points. I withdraw three of my round 1 positions: the fixed-step gate, Rule 2 as a gate, and "both factors" in Rule 3. I also drop "Not supported". I keep one difference: Rule 1 needs both block lengths. I change one critic rule: the crash rule.

## New scripts and data

| Script | Output | Content |
|---|---|---|
| `a6_round2.py` | `a6_round2.txt` | SE check, option tables, labels, Rule 3, floors. Reads `a2_sim_*.csv`, `a1_dryrun.csv`, `a5_amended.csv`, and `data/forecast_panel.parquet` |
| `a7_outer126.py`, `a7_summary.py` | `a7_20*.csv`, `a7_summary.txt` | Rule 1 options at 126-session residual blocks, and near the 300-origin floor. 80 replications per cell, 240 pooled. Monte Carlo error about +/-1.5 points at b = 0, and +/-3 at b = .37 |
| `a8_final.py` | `a8_final.txt` | Rates of the final rules. Reads `a2_sim_*.csv`, `a5_amended.csv` |

Also read: the critic's `round1.md`, `c4.out`, and `c2_dryrun.csv`. Code read as text: `build_snapshot.py`, `load_data.py`, and matching lines of `build_inputs.py`, `build_series.py`, `realized.py`, `tests/test_inputs.py`. New data file read: none.

## 1. Rule 1

**The SE claim holds, and it is stronger than the critic says.** My simulation holds real inputs fixed and b constant, so the spread of b is sampling only.

| Design | SD of b / median 21-block SE | SD of b / median 63-block SE |
|---|---|---|
| `a2_sim`, by base window | 1.35, 1.39, 1.47 (cells 1.29 to 1.54) | 1.22, 1.32, 1.28 |
| `a7`, 63-session residual blocks | 1.47 | 1.35 |
| `a7`, 126-session residual blocks | 1.51 | 1.33 |
| `a7`, coverage .53 | 1.52 | 1.39 |

**Where the critic is wrong:** The critic says that part of the gap is real period variation. My design has no period variation, and the ratio is the same. So the block bootstrap itself is too narrow.

**Effect:** Each tail misses 5.3% to 8.3% with 21-session blocks (`a2_sim`), against 2.5% nominal. So the "95%" interval covers about 85% to 88%. With 63-session blocks, it covers about 88% to 91%. The verdict text must not present it as a true 95% interval.

**Rates, lower bound above zero:**

| Option | b = 0 | b = .37 | b = .62 |
|---|---|---|---|
| 21-block only (critic), `a2` | 5.7% | 40.7% | 70.8% |
| 21-block only, `a7` 63 / 126 outer | 7.1% / 5.4% | 41.7% / 41.7% | 73.8% / 65.8% |
| **21 and 63 both (mine)**, `a2` | **4.0%** | **34.8%** | **65.5%** |
| 21 and 63 both, `a7` 63 / 126 outer | 5.8% / 3.8% | 35.4% / 38.3% | 65.8% / 60.4% |
| 21 and 63 both, coverage .53, `a7` | 5.4% | 28.8% | 50.8% |
| Interval and fixed-step t 1.30 (my round 1), `a2` | 1.7% | 22.8% | 51.8% |

**I withdraw the fixed-step t.**
- The critic is right that it has no known null distribution, and that it decides Rule 1.
- Its power depends strongly on the window. At b = .62, it is 34.5% to 66% by base window. With both intervals, it is 61% to 74%.
- I picked 1.30 after a dry run. This does not contaminate the test, but the number has no other source.

**I do not accept the 21-block interval alone.** The false-pass rate is 5% to 8%, and the critic reports 4% to 8%. Requiring both block lengths gives 4% to 6%.
- Both lengths are in `PLAN.md` and in the Stage 3 protocol, so this choice is not tuned to the dry run.
- The target windows overlap for about 21 sessions, so a 21-session block is short on its face. The critic notes that it gives the largest t in development.
- **Limit:** The gain is 1 to 2.5 points at b = 0, near the Monte Carlo error on any one row. All three designs point the same way. The cost is 3 to 6 points of power at b = .37. The judge can fairly choose either.

**False-pass rate that I accept:** about 5% one-sided, shown to the user as 4% to 6% from simulation, not as a nominal number.

## 2. Outcome labels

**Pick the critic's label: "Below the development size".**

| True b | Upper bound below .37 (both blocks) | 21-block only | b at or below zero (mine) |
|---|---|---|---|
| 0 | 39.8% | 47.3% | 50.8% |
| .25 | 12.3% | 16.8% | 22.3% |
| .37 | 4.8% | 8.2% | 12.5% |
| .50 | 1.7% | 2.0% | 6.0% |
| .62 | .2% | .5% | 2.3% |

- It fires less often at every true b above zero, and it still fires about 40% of the time at b = 0.
- It states an alternative. A value of b = -.01 with an interval of -.5 to .5 is "Inconclusive", which is correct.
- My disclaimer repaired a label that says more than the sign can support. A true label is better.
- **One change:** apply it to both upper bounds, for the same reason as Rule 1.
- **Limit:** The .37 is a no-event value, and the verdict has events in. So the comparison is generous to the claim. I accept this, and the text states the source of .37.
- `a7` rates at b = .37 are 5.4% to 7.9%. At nominal, the rate would be 2.5%. Say this in the operating table.

## 3. Rule 2

**The critic is right. Report it, with no gate.**

The deciding number is the pass rate of Rule 2 given that the 21-block interval passes: **52.9% at b = 0, 58.6% at b = .37, 73.2% at b = .62**. So near the size that matters, the gate removes true and false passes at almost the same rate. It costs 40% of "Supported" at .37, and it gains 2 to 3 points of false-pass rate.

- Its false-pass rate alone is 9.2% in my simulation, and 10 to 12% in the critic's. On about 14 to 15 windows this is a weak test.
- **This changes a recommendation in `HANDOFF.md`** (Clark-West as the information rule). That choice used 1,460 rows. The test has about 270.
- Keep the added phrase "also out-of-sample". With both intervals its rate is 2.0%, 21.5%, and 50.0% at b = 0, .37, .62.
- Add a condition: the phrase needs at least 180 scored rows.

## 4. Rule 3

**Duan alone, gated by Rule 1. The critic is right.**

- The algebra holds. The k that minimizes training QLIKE of k x F is mean(RV/F), and this is the Duan factor. So no factor is a misscaled forecast.
- My "both" rule held false passes down only when Rule 3 stood alone. Duan alone is 7.7% at b = 0 (critic: 4 to 9%). Gated, it is 1.5%.

| Rule 3, gated by both intervals | b = 0 | b = .37 | b = .62 |
|---|---|---|---|
| Duan alone | 1.5% | 8.2% | 20.0% |
| Duan and no factor, 21-block gate | .5% | 3.5% | 11.8% |

- **Keep the critic's reported items.** Given a gated Duan pass, the no-factor sign differs in 7% to 20% of cases. The verdict line must say so. Stage 3 found that smearing supplies about 71% of the -.077, so the disclosure matters.

## 5. Floor

**The critic is right about the draft's 20-row reading, and wrong as an attack on my floor.**

| Floor on real windows | Fails |
|---|---|
| Fixed-step median below 20, critic's 28 windows | 13, including all 4 Supported |
| Fixed-step median below 20, my 55 windows, strict ends | 23, including 13 of 29 interval passes |
| **Fixed-step median below 17 (mine)**, 28 windows and 55 windows | **0 and 0** (minimum 18) |
| Span of 21 sessions below 20 (critic), 55 windows | 0 (minimum 25.3) |
| 21-session spans with 10 or more origins below 20 (below), 55 windows | 0 (minimum 24) |

**I still give up my reading.** The floor should measure what the rule uses. With no fixed-step gate, a fixed-step row count is the wrong measure.

**I amend the critic's text.** A span from first to last valid origin passes on 300 origins in two clumps. So I count filled spans. The maximum gap in real windows is 16 sessions, and this count allows a thin period without voiding the test.

**Support for 300 origins:** At coverage .53 (286 rows), the false-pass rate is 5.4%, and b = .62 passes 50.8%. So the rule stays valid there, with less power. I tested no lower.

**Keep the 180 scored rows only for the out-of-sample phrase.**

## 6. Build path and freeze

| Finding | Position | Check or change |
|---|---|---|
| `build_snapshot.py` | **Accept. Verified** | See below |
| Alpaca has no gated reader | **Accept. Verified** | `alpaca_ggal_sip_raw.json` occurs only in `build_inputs.py`, as a copy source. `build_series.py:78` and `realized.py:25` also read `adr_cash_events.csv` with no gate |
| Any empty file opens the marker | **Accept. Verified** | `config.py:47` uses `.exists()`. The fix must also change `tests/test_inputs.py:32,36`, which write `"{}"` as a marker |
| `iter_days` has no marker argument | **Accept. Verified** | `load_data.py:49` calls `require_open(start, end)` |
| No crash rule | **Accept, with a change** | See below |
| No external anchor | **Accept** | It gives evidence, not prevention. Say this in the text |
| Two-step run, dress rehearsal, `TEST_EVENTS`, "only clean data" wording | **Accept** | Step A counts need the session grid from option days. Step B rechecks the floor after Alpaca |

**`build_snapshot.py`, what the code shows:**
- `main()` calls `fetch_rates()` first. It writes `data/source/fred_rates.csv`, with `cosd=2018-01-01` fixed in `FRED_URL`.
- `main()` fixes the range to `DEVELOPMENT_START`..`DATA_END`, so the script as written cannot reach the locked period. The critic's point applies to any reuse, and this reuse is the draft's implied path.
- If the start moves to 2016 and the end to 2018-04-30, `zip` is empty if XNAS starts on 2018-05-01. `pd.concat` then raises an error, after the rates are overwritten.
- If the end stays at `DATA_END`, the first pair has an equity day of 2018-05-01 against an option day of 2016-01-04, and the "out of step" error fires instead. The critic did not state this case. The result is the same.
- I rely on the critic's reading of the XNAS start date in the README. I did not open that zip.
- **Addition:** The rates rule uses the last observation before each session. So the new rates file must start before 2016-01-04, for example at 2015-12-01. Draft text "must cover 2016-2018" misses this.

**Crash rule, my change.** The critic ends the test at a crash after "the first outcome is computed". A value in memory that nobody saw does not fork a path. So a bug in a late step would lose the only test for no reason. I recommend that the script holds all outcomes in memory, suppresses values in tracebacks, and writes one result file at the end. The line is then "any outcome is displayed or written". Otherwise I accept the critic's text.

## 7. Bridge reader

The reader must not show locked rows, and nobody may inspect the file to learn its layout.

1. **One function:** `load_alpaca_closes(start, end, marker=...)` in `load_data.py`. No other code opens the file.
2. **Gate first.** It calls `require_open(start, end)` before it opens the file.
3. **Filter inside the function.** The file is one JSON document, so a full parse is necessary. Filter to the dates right after the parse, by New York date. Convert from the raw timestamp, because a UTC date can be wrong by a session at the boundary. Delete the unfiltered object before return.
4. **Assert before return:** minimum date is at or after `start`, and maximum is at or before `end`. If this fails, raise an error that holds no values.
5. **Layout check with no values:** A separate helper prints only key names, value types, and row counts. It prints no dates and no prices. Write the field names into the reader as constants after this step.
6. **No values in errors.** Catch parse errors, and raise a fixed message, so that a traceback cannot print a row.
7. **Saved extract:** Write the filtered rows once to `data/alpaca_open_closes.parquet`. The bridge reads only this file. Check that its first date is on or after 2018-05-01.
8. **Unit test:** A synthetic JSON with 2017 and 2018 rows. It confirms that a 2017 request is blocked with no marker, that a 2018-05 request returns no earlier row, and that a boundary bar on 2018-04-30 at a late UTC time is out.
9. **Do not open** the other files in `research/stock_history_check_20260915/`.
10. **Log the contact.** State that the parse held locked rows in memory, and that no value was shown.

**Report, by the critic's list:** sessions in one source only; median, 99th percentile, and maximum of |log(Alpaca close / official close)|, by year; and b before 2025-03 with Alpaca-based RV. I accept the critic's limits (median at most 10 bp, 99th percentile at most 100 bp, change in b at most .03). I have not seen this data, so I cannot test the limits. The check also confirms that the closes are raw: an adjusted series gives a ratio that drifts by date.

**Limit:** This check validates 2018-05 onward only. It cannot prove the quality of the 2016-2018 bars. Step B must also run the session-count and no-gap checks, and print counts only.

## Final recommended text

**Rule 1, information (decides the verdict).** Pass if b on `log_iv2` (log `ATM30` squared) in HAR+IV has a lower bound above zero in both percentile bootstrap intervals: 21-session and 63-session blocks, 2,000 resamples, 2.5th and 97.5th percentiles, seed 20261104. Simulation shows that these intervals are too narrow, and that they cover about 85% to 91%, so the rate of a false pass is about 4% to 6%. Fixed-step samples (22 and 23) are reported as mean b, range, and median t. They do not decide the verdict.

**Rule 2, out-of-sample information (reported).** Clark-West on log loss, HAR nested in HAR+ATM30, both trained on the same `primary` rows with a target window that ends on or before the origin, from position 252, with at least 126 training rows, and 21-session blocks. Report t, and state the scored rows and windows.

**Rule 3, usable gain (label only).** Applies only if Rule 1 passes. QLIKE of HAR+ATM30 minus HAR with the Duan factor has a 97.5th percentile below zero. The no-factor result and mean forecast over mean target are reported beside it. If the two signs differ, the verdict line says so.

**Outcomes.** Apply in order. The first match is the outcome.
1. "Inconclusive, data floor" if the test fails section D.
2. "Supported" if Rule 1 passes. Add "with usable gain" if Rule 3 passes. Add "also out-of-sample" if the Clark-West t is above 1.65 on at least 180 scored rows.
3. "Below the development size" if both upper bounds of b are below .37. This says that the test period does not show the development size (.37, no events before 2025-03). It does not say that b is zero.
4. "Inconclusive" otherwise. State the sign of b.

Each verdict line states "2016-01 to 2018-04 only". If "Supported" holds and either no-event interval includes zero, the line adds "with events only; the ordinary-day question stays open".

**Section D floor.** At least 300 valid origins. Divide the sessions from the first valid origin into consecutive 21-session spans. At least 20 spans must hold 10 or more valid origins. A target window must end on or before 2018-04-30. The test frame is not joined to data from 2018-05 onward.

**Operating table for the user (`a8_final.py`, 600 replications per true b, full coverage).**

| True b | Supported, any form | Of which, with gain | Below development size | Inconclusive |
|---|---|---|---|---|
| 0 | 4.0% | 1.5% | 39.8% | 56.2% |
| .25 | 22.2% | 6.2% | 12.3% | 65.5% |
| .37 | 34.8% | 8.2% | 4.8% | 60.3% |
| .50 | 54.0% | 17.3% | 1.7% | 44.3% |
| .62 | 65.5% | 20.0% | .2% | 34.3% |

- By base window at b = .62: 74.0%, 61.0%, 61.5%. At b = 0: 3.5%, 3.5%, 5.0%.
- With coverage thinned to 70%, b = 0 gives 4.4%, and b = .62 gives 60.7%.
- **Limit:** This simulation has constant b, and it uses development rows. The test period is calmer or different in ways that nobody can see yet. Period b can differ from any pooled value: across real windows it runs from .12 to 1.12.
- **Dry run on seen data (55 overlapping windows):** 28 Supported (7 with gain), 27 Inconclusive, 0 Below. All 28 windows start from 2018-05 to 2020-09. So they are about one or two results, not 28. This is rule behaviour only, and windows that start later do not pass.
