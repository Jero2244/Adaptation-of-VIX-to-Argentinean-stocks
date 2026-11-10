# Stage 3 findings

Exploratory. No verdict rule exists until Stage 4, and the method changed during this stage after contact with the results. The numbers are in `stage3_results.md`, and the plots are in `stage3_figures.png`.

**Corrected on 2026-11-04 after a two-round review by a defender and an attacker.** The section "Corrections after the review" lists the changes. The review checks came after the results too, so they are exploratory.

**Source of the numbers:** Numbers marked "review check" are not in the study code or in `stage3_results.md`. Their scripts and outputs are in `review/`, and `review/README.md` explains how to rerun them. Unless marked, I reproduced each review check from `data/forecast_panel.parquet`. "One agent" means that a number has only that agent's check. "Both agents" means that both agents checked it, and I did not.

## Main result

> In-sample, pooled, `ATM30` adds information beyond past RV. The size is not stable: event windows, mainly the 2019 PASO, supply about a quarter of the coefficient. Evidence on ordinary days before 2025-03 is weak. Out-of-sample, the sign favors `ATM30` on later dates, but the size depends on training and level choices, and no dependable forecast gain is shown.

## Primary question, in-sample

The regression is log RV30 on log RV over 1, 5, and 22 sessions, plus log `ATM30` squared, on 1,806 origins.

| Measure | Result |
|---|---|
| Coefficient on IV | .622 |
| 95% interval, 21-day blocks | .337 to .916 (t 4.1) |
| 95% interval, 63-day blocks | .309 to .946 (t 3.8) |
| R2, HAR alone and with IV | .097 and .177 |
| Non-overlapping samples, first-valid-session step | 17 distinct of 21. b is .354 to .705. 12 of 17 distinct samples have t above 2 |
| Review check: fixed step of 22 sessions | Mean b .611, range .171 to 1.095, median t 2.7. Without the 2019 PASO row: mean .500, median t 2.4 |
| Review check: fixed step of 23 sessions | Mean b .602, range .352 to .837, median t 2.7. Without the 2019 PASO row: mean .493, median t 2.6 |

- **First-valid-session step:** This step is a design flaw. The paths merge, and all 21 offsets share one path in the second half of the sample (one agent). So do not use its median (.43) as a lower bound. The fixed steps have no overlap, and they do not merge. They replace my earlier "plausible range of .43 to .62" as the better evidence, but their ranges are wide.
- **Other baselines (review checks):**
  - 5-minute HAR inputs give about .53 (both agents).
  - Stronger baselines give .73 to .79 on 1,599 rows (one agent).

## Where the gain sits

| Sample, study HAR | b | Note |
|---|---|---|
| All origins | .622 | |
| All listed events dropped | .459 | Random drops of the same size: 95% range .512 to .706. Only .4% fall below .459 |
| 2019 PASO dropped | .507 | |
| No events, before 2025-03 | .366 | 1,300 origins. Review check: 21-day interval -.037 to .703 (one agent) |
| From 2025-03 | 1.190 | 375 origins, including the two 2025 events |
| From 2025-03, no events | .781 | So part of the 1.190 comes from the 2025 events |

- **Fair use of the drop:** Dropping events shows where the gain comes from. It does not test whether `ATM30` adds information, because IV should price scheduled events.
- **Share of the in-sample gain (review check, one agent):** Event rows are 9% of the rows and supply 57% of the squared-error gain. Non-event rows after the break are 19% and supply 31%. Non-event rows before the break are 72% and supply 11%.
- **With 5-minute HAR and no events:** b is .278 and .30 (both agents, a different overnight rule is the probable cause). The 21-day interval includes zero in the first estimate, and t is 2.1 in the second. For 2018-2023 only, b is .167 and .23, with t at most 1.25.
- **Limit:** Nobody can yet separate the quote format break of 2025 from a real market change.

## Stability

| Period | b on IV, HAR+IV | 95% interval, 21-day blocks | R2 gain |
|---|---|---|---|
| 2018-2023 | .526 | .192 to .875 | .051 |
| 2024-2025 | 1.185 | .588 to 1.469 | .237 |
| 2026 (9 windows) | .423 | -.387 to 1.569 | .033 |

- **By year:** b runs from -.380 in 2022 to 1.379 in 2025. So the relation is not stable.
- **Leave one year out:** b stays from .542 to .707.
- **Year-demeaned:** b is .644, with an interval of .309 to 1.015.

## Forecast race

This stage does not settle the forecast question, and no reported number is clean. The cause is level bias plus the training and date choices, not calibration alone.

Two questions need separate answers.

**1. Does `ATM30` hold information out-of-sample? (review check)** HAR is nested in HAR+ATM30, and the t in the race tables is known to be undersized for nested models. Clark-West on log loss gives this result:

| Rows and training | t, 21-day blocks | t, 63-day blocks |
|---|---|---|
| 1,460 rows, common training days | 5.2 | 4.5 |
| 1,460 rows, training from 2018-06 | 4.2 | 3.4 |
| 1,599 raw-race rows | 2.7 | 2.1 |

The log MSE difference on the 1,460 rows is -.074 (t -2.8). On the raw-race rows, it is about -.007 (t -.2, both agents).

**2. Does `ATM30` give a dependable forecast gain? Not shown.** QLIKE is the primary loss. A negative difference favors `ATM30`.

| HAR+ATM30 minus HAR | Common training, 1,460 rows | Training from 2018-06, 1,460 rows | Raw-race rows, 1,599 |
|---|---|---|---|
| With smearing | -.077 (t -5.0) | -.043 (t -4.2) | -.019 (t -1.3) |
| No smearing | -.022 (t -1.2) | -.027 (t -1.9) | .000 (t .0) |

Only the first column and the raw smearing value come from `stage3_results.md`. The others are review checks.

- **Training start (a choice that I did not flag):** The common training days drop 2018-06 to 2019-04 from HAR, for GARCH. This raises the weight of the 2019 PASO, and it moves the gain from -.043 to -.077 on the same rows.
- **Rows:** My first table compared races with different rows and training days, and it credited calibration only. That was wrong. The sign is negative for all calibrations on the 1,460 rows. On the raw-race dates, the no-smearing gain vanishes. The 119 rows from 2019-05 to 2019-12, outside the PASO windows, contribute +30.6 to the QLIKE sum. The 20 PASO rows contribute +8.8, and the later 1,460 rows contribute -39.1. Short training and high IV after the PASO occur together in these rows, so nobody can separate them.
- **Smearing:** The factor returns the mean of the training target, and the 2019 windows inflate it. Pooled, calibrated forecasts average .66 against a target of .38, and QLIKE is lower without smearing for every model.
- **Smearing, by period:** In 2024-2025, no smearing is worse for 4 of 6 models. Its forecasts average .26 for `ATM30` and HAR+ATM30, and .31 for HAR, against a target of .41. This low bias hits the better model harder, so -.022 is also contaminated. In 2024-2025, the no-smearing gain is only -.006, while the in-sample R2 gain is largest.
- **"Use or drop" is a false choice (review checks, both agents):** A lognormal factor gives -.046, a winsorized factor gives -.054, and a factor without PASO rows gives -.037. Smearing accounts for about 71% of the -.077 (one agent).
- **`ATM30` against HAR+ATM30:** The difference is close to zero in both calibrated races. So HAR adds little once `ATM30` is present.
- **Raw `ATM30`:** It has the lowest QLIKE in the raw race (.418), with no calibration. GARCH with t errors is next (.470), and the interval for the difference includes zero.
- **GARCH:** With normal errors, the 2019-08-12 return (-.82) sets the fit for years. So the normal-error result says little about GARCH in general. I added t errors after I saw this problem. They do not change the HAR+ATM30 and HAR comparison, because the common days are the same with or without them (one agent).
- **EWMA (review check, one agent):** I ran no lambda sensitivity. Raw QLIKE is .707 at .94 and .584 at .98. Raw `ATM30` stays lower.
- **2026 t values:** They are unreliable. About 9 blocks fit in that period, so values such as t = -5.0 overstate the evidence.
- **Duplicate rows:** The calibrated rows for "no 2019 PASO windows" duplicate the "all" rows, because that race scores no PASO origin.

## Quote noise and measurement error

- **Short-lived noise looks small.** On identical days, OLS gives .685 and IV lag 1 gives .682. A Roll-type estimate gives a reliability of about .96 (one agent), and an attenuation of about 4% (the other agent).
- **Persistent quote error is untested.** My earlier statement, "no sign that quote noise weakens b", was too broad.
- **Longer lags do not test noise.** IV lag 5 gives .513, and the estimate keeps falling at longer lags. Noise would raise the estimate, not lower it. The long lags probably isolate the slow part of IV (one agent, argued). So the lag-5 instrument is probably not valid for this purpose.
- **Spread gradient:** b is .753 in the lowest pooled spread tercile, and .441 in the highest. Within years, with year controls, the terciles give .884, .698, and .373. So period mix does not explain the gradient, and my earlier caveat was wrong. Noise explains only about 3 points of it (one agent). With events dropped, the gradient is no longer monotonic (one agent). The cause stays open.
- **Tier:** b is .703 on Tier 1, and .435 on Tier 2.
- **Other series and flags:** `atm30_floor7`, `atm30_usable`, and `atm30_session_last` give .616 to .650. Dropping all flagged days gives .708. `atm30_floor7` is the same as dropping days with a front term under 7 days.

## Selection

- Coverage is .675 with 0-6 days to the near expiry, and .94 to .97 with more days.
- Mean log RV30 is -1.27 on days without `ATM30`, and -1.18 on days with it. So the missing days are slightly calmer, not more volatile.
- The HAR weights differ on the 287 missing days, but this group is small.

## Argentina events

These are case studies with no p-values. `ratio` is the forward vol between the two expiries, over the near-term vol. The event list was set in advance in `PLAN.md`.

- The event ratio is above the placebo median at all 9 events. The margin is only .004 at the 2025 midterm.
- At 7 of 9 events, more than 85% of the placebo ratios are below the event ratio.
- The 2021 PASO has a 17-day near term, and few of its placebos match it (one agent). So its share of .90 is not like for like.
- The two 2025 events sit near the middle of their placebos. The near-term vol before the 2025 midterm was already 1.13, after the PBA shock. So that ratio has a high base.
- **2019 PASO:** The forward vol was .576, and the realized vol between the same expiries was 3.04. The options showed an event premium, but it was far too small.
- The placebos share dates across events, so these comparisons are not independent.

## Variance risk premium

Mean and median differ in sign, as the plan expected. `ATM30` squared minus RV has a mean of -.041 and a median of +.105. Implied variance exceeds RV on 72% of origins. In 2026, the mean and the median are both positive (.061 and .069).

## Overnight split

The overnight share of RV is .32 in all periods, .36 in 2024-2025, and .18 in 2026.

## Target noise (review check, one agent)

A target from 5-minute mids raises R2 from .177 to .294. The 2026 b becomes .77 (interval .19 to 1.19), against .423 with an interval that includes zero. So part of the weak 2026 result can be target noise.

## Debate checks

| Debate number | Study | Result |
|---|---|---|
| Pooled log b .55 (.58 and .57 without 2019-08-12) | .581 and .554, with the sample cut at 2024 | Close, so the debate sample may have ended in 2024. Evidence for: the debate yearly range tops at .97, and the study has 1.132 in 2025. Evidence against: `PLAN.md` says the advocate read 2025 in its first-round regressions. Not confirmed |
| Log b .97 in 2024 | .684 on all 2024 rows. .31 to 1.10 across non-overlapping samples of 11-12 windows | Not explained. .97 is inside this range, but a range that wide can contain almost any value, so this explanation has little content |
| Level b .79 and .22 without 2019-08-12 | .686 and .616 | Not reproduced. No tested rule gives .22. The level R2 does rise, from .031 to .146, without these windows |
| Implied variance above RV in 79% | 67% to 74% across the tested rules | Not reproduced |

`reports/stage3_debate.csv` has all the rule combinations. Total or price return makes almost no difference.

## Bugs that this stage found

The results include all these fixes. The tests caught the first one, and my review of the output caught the others.

1. The `rv21` rolling sum lost the first 20 origins.
2. All 21 non-overlapping samples were identical, because each offset moved to the same first valid session.
3. One selection column had the label "next return", but it held the same-day return.
4. The instrument rows used different days, so they could not be compared.

The review checked the window arithmetic, `rv21`, the GARCH recursion, the training cutoff, `block_sample`, and the non-overlap logic. It found no other code bug. One agent changed all future targets and inputs at three origins, and the forecasts did not change.

## Corrections after the review

| Earlier statement | Correction |
|---|---|
| "Treat .43 to .62 as the plausible range" | The .43 comes from merged paths. Use the fixed-step results, and report them with and without the PASO row |
| "57% of samples have t above 2" | 12 of 17 distinct samples (71%) |
| The race table credited calibration | The races differ in rows and training days too |
| "QLIKE is lower for every model" without smearing | True for the pooled period only |
| -.022 as the cleaner number | It is also contaminated by low bias |
| "Use or drop" smearing | Other level rules exist |
| "No sign that quote noise weakens b" | Short-lived noise looks small. Persistent quote error is untested |
| The spread gradient "also changes with the period" | It remains within years. The cause is open |
| Implied variance "72% to 74%" | 67% to 74% across the tested rules |
| "The debate sample probably ended in 2024" | Not confirmed. `PLAN.md` has evidence against it |
| ".97 can be sample noise" | Not explained |

**Process limit:** With no git history, nobody can check my statement that I chose smearing before the run.

## Decisions for Stage 4

These are open items, and Stage 4 has not started. The review changed my earlier recommendations, and I no longer recommend a simple drop of the smearing factor.

1. Use two verdict rules: one for information, and one for usable forecast gain.
2. Choose the level rule. The candidates are the Duan factor, no factor, a lognormal factor, and a winsorized factor. A rule should not name 2019.
3. Choose the training start. The choice is common training days, or the longest available training for each model on the same scored rows.
4. Replace the first-valid-session step with fixed steps of 22 and 23 sessions.
5. Require every headline to state its scope: with and without events, and before and after 2025-03.
6. Use normal or t errors in GARCH, and choose the EWMA lambda.
7. Keep or change the 126-row training floor, and the daily variance floor of 1e-6. The variance floor has almost no effect.
8. Decide how to treat the locked 2016-01 to 2018-04 test. It falls entirely before the format break, so it can test the weak result on ordinary days. It cannot explain the change after 2025-03, and it has only about 28 windows.
