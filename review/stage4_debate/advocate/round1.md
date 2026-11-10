# Advocate, round 1: Stage 4 draft plan

All checks are exploratory. The dry run uses seen data, so it shows the behaviour of the rules. It is not evidence for the claim.

**Position:** The structure of the draft holds. Its thresholds do not all hold. The draft needs five small amendments, and the rule set stays low-powered after them. The most probable outcome at a true b of .37 is "Inconclusive".

## Data contact

- Read: `data/forecast_panel.parquet`. `a0_panel.py` loaded all columns and printed column names, row counts, coverage by year, and dates. All other scripts loaded only the `CALC` columns in `rules.py`, and they filter to rows before 2025-03.
- Read as text: the draft, `HANDOFF.md`, `PROTOCOL.md`, part of `PLAN.md`, `reports/stage3_findings.md`, `review/README.md`, `review/verify_debate.txt`, `review/verify_debate.py`, `forecasts.py`, `inference.py`, `events.py`, `config.py`, and matching lines of `run_development.py`.
- Not read: any 2016-01 to 2018-04 data, the Alpaca file, raw Databento files, `data/index_series.parquet`, `data/atm_terms.parquet`, and `data/adr_cash_events.csv`. I did not create the marker. I printed no dividend rows.

## Scripts and outputs (in this folder)

| Script | Output | Content |
|---|---|---|
| `rules.py` | | Exact rules of sections C and D |
| `a0_panel.py` | console only | Panel structure and coverage by year |
| `a1_dryrun.py` | `a1_dryrun.txt`, `a1_dryrun.csv` | Draft rules on 55 rolling 28-month windows |
| `a2_sim.py` | `a2_sim_*.csv` | Size and power with a known true b |
| `a3_counts.py` | `a3_counts.txt` | Row counts by arithmetic, no data read |
| `a4_summary.py` | `a4_summary.txt` | Dry-run and simulation tables |
| `a5_amended.py` | `a5_amended.txt`, `a5_amended.csv` | Amended rules |

## Choices that I had to make because the draft is silent

- "Mean b over fixed-step samples": I pooled the 45 samples (22 offsets at step 22, 23 offsets at step 23).
- "Non-overlapping windows" in the floor: the median row count of those 45 samples.
- "Upper 95% bound": the 97.5th percentile, like the Stage 3 intervals.
- The first 22 sessions of each window have blank HAR inputs, to copy the warm-up in the test.
- "Not supported" and "Supported" can overlap. I gave "Supported" precedence.

## Section C: verdict rules

### Dry run: 55 overlapping windows, draft rules (`a1_dryrun.py`)

The windows start monthly from 2018-05 to 2022-11. They hold about three independent periods, so 55 is not a sample size.

| Outcome | All 55 | With 2019-08-12 (16) | Without (39) |
|---|---|---|---|
| Supported, with usable gain | 1 | 1 | 0 |
| Supported | 5 | 0 | 5 |
| Inconclusive | 38 | 15 | 23 |
| Inconclusive, floor | 11 | 0 | 11 |
| Not supported | 0 | 0 | 0 |

| Rule part | Pass rate, all 55 |
|---|---|
| 1a: b above zero, interval excludes zero | 52.7% |
| 1b: fixed-step mean above zero, median t above 1.65 | 18.2% |
| 1 (both) | 18.2% |
| 2: Clark-West t above 1.65 | 30.9% |
| 3: QLIKE gain under both level rules | 1.8% |

The three near-disjoint windows (2018-05, 2020-09, 2022-11) all give "Inconclusive". The middle one fails the floor, with 19 fixed-step rows and 422 origins.

Other results:
- b runs from .132 to 1.119. No window has b at or below zero.
- The interval width is .638 at minimum, and .817 at the median.
- No window has an upper bound below .25.
- Clark-West t runs from -3.13 to 3.26. Its correlation with b is .894.

**Limit:** This dry run has one path of real data, and true b in it is not known and probably changes. So I also ran a simulation with a known b.

### Simulation: known true b (`a2_sim.py`, `a4_summary.py`, `a5_amended.py`)

**Design:**
- It keeps the real inputs of three base windows (2018-05, 2020-09, 2022-11).
- It rebuilds the target from a true b, and from 63-session blocks of the pooled pre-break residuals.
- It uses 200 replications per window and true b without thinning, 100 with thinning, and 499 bootstrap draws.
- HAR trains on the primary rows here.

**Limits:**
- True b is constant, and residuals are independent of the inputs. Real data can be worse.
- These runs allow target windows past the end of the frame, so scored rows run about 6% above amendment 2.
- Power depends on the base window. At true b of .62 and draft thresholds, Supported is 48.5%, 16.5%, and 35.0%. The IV variance of the test period is unknown, so I cannot say which base window it resembles.

**Share of replications with "Supported" (with or without gain), floor set at 17 so that the threshold effect is visible:**

| True b | Rule 1b t 1.65 (draft) | t 1.30 | t 1.00 | No fixed-step t |
|---|---|---|---|---|
| 0 | .7% | 1.1% | 2.2% | 3.0% |
| .25 | 4.5% | 9.0% | 11.3% | 14.5% |
| .37 | 9.5% | 16.2% | 21.4% | 23.8% |
| .50 | 20.2% | 30.6% | 37.8% | 41.1% |
| .62 | 33.4% | 43.4% | 49.5% | 51.8% |

**"Not supported" (same for all columns):** 50.8% at true b of 0, 22.7% at .25, 12.5% at .37, 6.0% at .50, 2.3% at .62.

**Rule parts at true b of 0 (actual against nominal):**

| Rule part | Actual | Nominal |
|---|---|---|
| 1a with 21-session blocks, lower bound above zero | 5.7% | 2.5% |
| 1a with 63-session blocks | 4.7% | 2.5% |
| 1b | .8% | about 5% |
| 2 | 9.2% | 5% |
| Rules 1 and 2 together | .7% | none stated |

**What the numbers show:**
1. The rules can be passed and failed. False "Supported" is rare (.7%).
2. The draft is too strict for its own data. It spends far less than a 5% false-positive budget, and power is only about one third at the pooled Stage 3 b, and about one tenth at the no-event pre-break b of .366.
3. Rule 1b is the binding part. The median of correlated t values is much stricter than one t test.
4. The two 21-session bootstrap tests are too liberal by themselves. Their conjunction with 1b gives the margin. So I do not propose to remove 1b.
5. No threshold gives good power. At true b of .37, "Inconclusive" is 64% to 78% across the variants that I tested. The user should know this before deciding on Stage 5.

### Defects in the outcome logic (concessions)

1. **The outcomes overlap.** An interval of .05 to .20 with Rule 2 passing is both "Supported" and "Not supported". This never occurred in 55 windows and 4,500 replications, but a frozen rule must not depend on that.
2. **The .25 clause does almost no work.** In the simulation, 5 of 4,500 replications have an upper bound below .25 with b above zero. So the clause adds an unexplained number and the overlap above. Delete it.
3. **"Not supported" is a weak statement.** It fires on the sign of b alone. At true b of .37, it fires 12.5% of the time. I defend it because a wrong-sign estimate cannot get any other label, but the text must say that it is not evidence of no information.
4. **The verdict does not answer the ordinary-day question** in findings item 8. In the dry run, Rule 1a passes in all 16 windows with 2019-08-12, and in 33% of the other windows. I still defend events in the verdict, because IV should price them. The no-event result stays beside it, and the text must say that the verdict does not settle ordinary days.
5. **Rule 3 will almost never pass:** 1.8% in the dry run, and 12% at true b of .62. I defend it as a label only. It does not change the "Supported" outcome, and Stage 3 shows no dependable gain.

### Choice of Rule 1b threshold

| Threshold | For | Against |
|---|---|---|
| 1.65 | No change. Lowest false positives | Power 33% at .62 |
| 1.30 (my proposal) | Power 43% at .62, false positives 1.1% | Chosen after the dry run, on seen data only |
| 1.00 | Power 50% at .62, false positives 2.2% | Weak guard. Windows that hold the 2019 shock start to pass |

The locked data is unseen, so this change does not contaminate the test.

## Section C, Rule 2: expanding training (`a3_counts.py`)

Assumption: 585 sessions, position 0 on 2016-01-04, so position 252 is about 2017-01-03. These are arithmetic results, with no read of locked data.

| Coverage | Valid origins | Scored rows | Scored rows, windows end by 2018-04-30 | Training rows at first origin |
|---|---|---|---|---|
| 100% | 563 | 333 | 312 | 209 |
| 86.4% | 486 | 288 | 270 | 181 |
| 72% | 405 | 240 | 225 | 150 |
| 60% | 338 | 200 | 187 | 125 |
| 50% | 282 | 166 | 156 | 104 |

- **Workable, but thin.** The scored span holds about 14 to 15 independent windows. It has about 15 to 16 blocks of 21 sessions, and 5 blocks of 63.
- **Both 2017 events are in the scored rows.** The 2017 PASO is 2017-08-13 and the midterm is 2017-10-22.
- **The 126-row floor binds only below about 60% coverage.** At 50%, scoring starts near position 295.
- **The dry run agrees with this arithmetic:** 246 to 307 scored rows.
- **Concession:** Rule 2 rests on 16 months, with first coefficients from about 10 months of 2016. Its actual size is 9.2%, and its t swings widely. It is a confirmation rule, and it should not stand alone.
- **I defend expanding training** because no other choice keeps the test causal and inside the locked period.

## Section B

| Item | Position | Evidence |
|---|---|---|
| Fixed steps | Holds | 22 sessions are 4 weeks plus 2 sessions, so 30 calendar days at minimum. Holidays only lengthen this. `review/verify_debate.txt` shows minimum gaps of 30 and 31 |
| Training start | **Amend** | "Longest for each model" has two readings. HAR on all HAR-valid rows against HAR on primary rows changes Clark-West t by .34 at the median and 1.31 at most. Different rows also add a difference that does not come from `ATM30`. The review's -.043 used primary rows for both |
| Level rule | Holds | Both factors must pass, and Stage 3 shows that neither is clean. It names no year |
| GARCH t, EWMA .94 | Holds, with a note | Neither enters a verdict rule. The "after results" objection to t errors has no effect on the verdict. Say this in the plan |
| Training and variance floors | Holds | See the table above. Stage 3 shows little effect from the variance floor |
| Stage 2 rules | Holds, with a concession | Tier 1 b is .703, and Tier 2 is .435. If thin chains raise the Tier 2 share, b falls and power falls. This direction is against the claim, so it does not create a false pass. Persistent quote error stays untested |
| Headline scope | Holds | Findings item 5 |

**Section A correction:** "About 28 windows" overstates the sample. After the warm-up, a fixed-step sample has at most 25 to 26 rows, and about 22 at 86% coverage. Rule 2 has about 14 to 15 windows.

## Section D: data floor

**The floor is not sensible as written.**
- The 300-origin floor corresponds to 53% coverage. It never binds in the dry run (minimum 422).
- The 20-window floor corresponds to about 78% to 82% coverage. It binds first.
- Open-data coverage by year is .72 to .92, and PLAN says the test has thinner chains. So the floor can void the test on an ordinary coverage level.
- In the dry run, it fails 11 of 55 windows. With target windows that end inside the frame, it fails 23 of 55.
- It does not protect much. With coverage thinned to about 70% (17 fixed-step rows), false "Supported" is 1.6% at t 1.00, and power at .62 falls only from 49.5% to 47.3%.

**Limit:** I tested 17 rows, not fewer. So I propose 17 and no lower number.

**Other items:**
- The floor has no term for Rule 2. I propose 180 scored rows, which is about 54% coverage. The dry-run minimum is 228.
- Target windows are not limited. Windows that cross 2018-04-30 use May 2018 returns, which are seen data. I propose to end them by 2018-04-30. It costs about 18 to 21 scored rows.
- The other items hold (Alpaca closes, two dividend rows, 2017 events, FRED), with the additions below.

## Section E: what is missing

1. **Alpaca bridge.** RV source changes only in the test. Before the freeze, compare Alpaca and official closes on open dates, and rerun b with Alpaca-based RV on open data. I did not run this, because rule 1 of this debate blocks that file for me. The filter must not read rows before 2018-05.
2. **Failure rule for the one-time run.** State what happens at a crash, and at a bug that appears after results. A code fix after any result is printed makes the period development data, as `PLAN.md` says. Check the floor before any estimate, and print no result if the floor fails.
3. **Two markers.** State that the unlock marker needs the user's approval, and that `run_tests_once.py` never creates it. The test-run marker is separate.
4. **Separate event list.** Do not add the 2017 dates to `EVENTS`. `first_session` uses `searchsorted`, so on open sessions it maps a 2017 date to 2018-05-01. `run_development.py` lines 182 to 187 and `event_table` would then change, and work item 3 would not reproduce `review/verify_debate.txt`. Use a separate `TEST_EVENTS`.
5. **Separate output.** `run_development.py` line 504 writes `data/forecast_panel.parquet`. The test must write to its own file. Create the manifest after work item 3, as the draft order does.
6. **Frozen numeric details.** Seeds, 2,000 draws, percentile intervals, the pooled reading of Rule 1b, and the two-sided reading of the upper bound.
7. **Descriptive list, frozen in advance, no effect on the verdict:** no-event b, 63-session interval, Tier 1 only, and each 2017 event dropped.
8. **Power statement to the user** before Stage 5 (section F): use the simulation table above.

## Proposed amendments: exact replacement text

**1. Section A, third bullet, replace "it has about 28 non-overlapping windows" with:**
> it has at most 25 to 26 non-overlapping windows in each fixed-step sample, and about 14 to 15 in Rule 2

**2. Section B, row "Training start", replace with:**
> | Training start | HAR and HAR+ATM30 train on the same rows: all primary rows with a target window that ends on or before the origin. No row needs a GARCH or EWMA value | Common training days drop 2018-06 to 2019-04 from HAR. Different rows for the two models add a difference that does not come from ATM30 |

**3. Section C, Rule 1, second bullet, replace with:**
> Pooled over the 45 fixed-step samples (22 offsets at step 22, 23 offsets at step 23), mean b is above zero, and median classical t is above 1.30.

**4. Section C, "Outcomes", replace with:**
> Apply these in order, and stop at the first match:
> 1. "Inconclusive" if the test fails the data floor in section D. Check the floor before any estimate.
> 2. "Supported, with usable gain" if Rules 1, 2, and 3 pass.
> 3. "Supported" if Rules 1 and 2 pass.
> 4. "Not supported" if b is at or below zero. This outcome means that the test gives no support. It is not evidence that ATM30 has no information.
> 5. "Inconclusive" otherwise.
>
> The verdict does not settle the question on ordinary days. The no-event result is reported beside it, and it does not change it.

**5. Section D, first bullet, replace with:**
> Floor: at least 300 valid origins, a median of at least 17 rows across the 45 fixed-step samples, and at least 180 scored rows in Rule 2. Below any of these, the verdict is "Inconclusive".
> A target window must end on or before 2018-04-30, so the test uses no return from the seen period.

**6. Section E, add after item 1:**
> 1a. Compare Alpaca and official closes on 2018-05 to 2026-10, with a filter that reads no earlier row. Rerun b with Alpaca-based RV on these dates. Record the result before the freeze.
> 1b. Show the user the power table.

**7. Section E, item 4, add:**
> The script never creates the unlock marker. It checks the floor first, and it prints no estimate if the floor fails. A code change after any printed result makes the period development data. Test events stay in a separate `TEST_EVENTS` constant, and the test writes to its own panel file.

**Amended dry run (`a5_amended.py`):** Amendments 2, 3, 4, and 5 on the same 55 windows give 40 Inconclusive, 10 Supported, 5 Supported with usable gain, and 0 Not supported. This is seen data, and the windows overlap.
