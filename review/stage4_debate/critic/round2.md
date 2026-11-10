# Critic, round 2

**Two round 1 positions change.** I withdraw "interval only" (point 1) and "Rule 2 reported only" (point 3). I also withdraw the .37 label (point 2) and my floor (point 5). The advocate is right on these last two. The advocate is wrong to keep the fixed-step t.

**New script:** `c5_round2.py`, output `c5.out`. It applies each rule to the same stored samples: my three settings (`c1_main_*.pkl`) and the advocate's constant-b runs (`a2_sim_*.csv`, read-only, floor 17, 3,000 rows). It also has a short 63-block run (200 sims) and an in-memory `first_session` check. The first three settings below are my pools, and the fourth is the advocate's simulation.

## Point 1: Rule 1 conflict

**The interval alone is not a sound sole rule. The advocate is right on this.** Its false-pass rate is 4.4, 6.4, 7.7, 5.7% against 2.5% one-sided.

The advocate's simulation also confirms the small SE with a constant b: SD of b / median SE is 1.35 (1.33 to 1.49 by window). So my round 1 remark, "part of the gap is period variation", does not explain all of it.

**A corrected interval does not help:**

| Option | Result | Problem |
|---|---|---|
| Multiply SE by k | k for a 2.5% false-pass rate is .96, 1.28, 1.44, 1.17 | k depends on the pool, so any frozen k is arbitrary |
| 63-session blocks | SE only 1.08 to 1.10 times larger. False-pass 4.7% (advocate), 3.5 and 7.0% (short run) | Small change, and about 8 blocks |
| 21 and 63 both | 4.0% (advocate), 2.0 and 6.5% (short run) | Small change |

**The fixed-step t is not needed for the margin. The advocate's own table shows this.**

| Rule | b = 0 | b = .25 | b = .37 | b = .62 |
|---|---|---|---|---|
| Draft: interval, t 1.65, Rule 2 | 0, .6, 1.0, .7 | 1.4, 5.0, 6.0, 4.5 | 3.2, 12.2, 12.7, 9.5 | 20, 34, 36, 33 |
| Advocate: interval, t 1.30, Rule 2 | .4, 2.0, 1.0, 1.2 | 3.6, 10, 10, 9 | 9.4, 19, 17, 16 | 34, 45, 46, 43 |
| **Mine: interval, Rule 2** | **2.0, 3.8, 3.7, 3.0** | **9, 16, 15, 15** | **19, 25, 26, 24** | **44, 50, 52, 52** |
| Corrected interval only, k = 1.25 | .6, 3.2, 4.3, 1.8 | 8, 16, 17, 13 | 14, 27, 30, 25 | 40, 57, 59, 57 |

- Interval with Rule 2 has a stable false-pass rate of 2 to 4%, near the 2.5% nominal. Its power is about the same as the k = 1.25 interval, and it needs no new number.
- The t adds a threshold with no known null distribution. The 1.30 came from seen dry runs. Its effect is to lower the false-pass rate to about 1% and to cut power at .37 by about a quarter to a half.

**The advocate has a fair case.** A false-pass rate of about 1% is safer. If the user wants at most 2%, keep t 1.30, or use the corrected interval with Rule 2 (k = 1.25: .2, 2.4, 2.7, 1.2 at b = 0; 10, 22, 20, 17 at .37). My position is that the 2 to 4% rate spends the stated budget and the t spends power for no stated reason.

Dry run, 28 windows, about 3 independent: draft 4, advocate 9, mine 12.

## Point 2: the .37 label

**.37 is not like-for-like, so I withdraw it as a verdict threshold.**
- It has events dropped, and the test keeps events in.
- The like-for-like development value is pre-break with events: .525. Without the 2019 PASO it is .39.
- .459 and .622 include rows after the break, and the test has none. So neither is a fair reference for this test.

Rate at which each rule fires:

| Rule | b = 0 | b = .37 | b = .62 |
|---|---|---|---|
| b at or below zero | 57, 50, 52, 51 | 20, 14, 12, 13 | 4.6, 3.0, 2.3, 2.3 |
| Upper below .37 | 48, 47, 46, 47 | 16, 12, 12, 8 | 4.2, 1.6, 1.3, .5 |
| Upper below .459 | 56, 58, 58, 58 | 25, 20, 16, 15 | 6.8, 4.8, 3.0, 1.5 |
| Upper below .525 | 60, 66, 69, 65 | 30, 26, 21, 22 | 10, 6, 6, 4 |
| Upper below .622 | 67, 79, 79, 73 | 38, 34, 31, 36 | 16, 12, 12, 9 |

The sign rule and "upper below .37" disagree on only 10 to 15% of samples at b = 0, and 5 to 8% at .37. So .37 buys little, and it costs a number that needs a defense. **The advocate's sign rule with its disclaimer is better.** Report the upper bound against .37 and .525 as description.

## Point 3: Rule 2

**Keep Rule 2 as a verdict rule. The advocate is right, for a different reason from the one that the advocate gives.**

Without Rule 2, nothing in the verdict is out-of-sample inside the test. The regression fits the whole period. The test is out-of-period only in the sense that the rules were frozen before any contact.

Does this matter?
- **To the literal claim, little.** "Adds information" is a valid in-sample question. Across real windows, Clark-West t and b correlate at .88 (advocate: .894). So Rule 2 is not much separate evidence.
- **To the study, yes.** `HANDOFF.md` names Clark-West as the recommended information rule.
- **To the error rate, yes.** It halves the false-pass rate (from 4 to 8% to 2 to 4%), at a power cost of about 40% at .37. No new number is needed.

**Limit:** Rule 2 has about 15 windows, and its own false-pass rate is 9 to 12%. So it does not stand alone, as the advocate says.

## Point 4: Rule 3

**Duan numbers confirmed.** With interval only: 1.4, 1.2, .7, 1.7 at b = 0; 10, 9.6, 6.7, 9.5 at .37; 21, 20, 20, 21 at .62. With the final rule (interval and Rule 2): 1.0, 1.0, .7, 1.5 at b = 0; 8.8, 9.6, 6.3, 8.8 at .37; 20, 20, 20, 21 at .62.

"Both" under the final rule: .2, .8, .7, .5 at b = 0; 10, 16, 14, 12 at .62. So once Rule 1 and Rule 2 gate it, "both" saves at most 1.0 point of false pass, and it loses 4 to 10 points of power. Duan alone is the better form.

**Should the outcome exist? Yes, as a one-way qualifier, and not as a separate outcome.** A pass is informative: about 20% against about 1%. A fail says almost nothing: 80% fail even at b = .62. So the text must say that a fail is not evidence of no gain. It has about 15 windows and Stage 3 shows no dependable gain, so the qualifier will probably not appear.

## Point 5: floor

**The advocate's floor is better. I withdraw 21-session spans.** Spans stay at 25.8 at any coverage with no long gap, so they do almost nothing.

| Advocate's term | Approximate coverage where it binds | Dry run minimum |
|---|---|---|
| 300 origins | 55% | 408 |
| Median 17 fixed-step rows | 70% | 18 |
| 180 scored rows | 58% (180/312, with windows ended by 2018-04-30; the advocate's 54% counts later windows) | 226 |

**Limit:** 17 was tested only at 17. The fixed-step row count stays useful as a measure of independent rows, even with no t rule.

**All three terms are checkable before any outcome.** They need only flags: `ATM30` valid (options), a close exists on that session (dates only), HAR warm-up, and window end. No return is needed.

**The advocate's wording is weaker than the need.** "Before any estimate" in a script that has already loaded Alpaca is a promise, not a barrier. Keep my Step A: options only, counts only. The Alpaca date check runs inside the gated reader, and prints no price.

## Point 6: the advocate's additions

| Item | Decision | Note |
|---|---|---|
| `first_session` maps 2017 dates to 2018-05-01 | **Confirmed**, `events.py` line 28. Output: 2018-05-01 for both dates | Effect is smaller than stated. No-event b stays .459, because no origin is before that date. The random-drop range does change: .506 to .693 becomes .498 to .705 (300 draws), because it uses the list length. `event_table` also gets two blank rows |
| `TEST_EVENTS` | Accept | Also my round 1 fix |
| Separate test panel | Accept | `run_development.py` line 504 writes the panel |
| Frozen seeds, draws, percentile type | Accept | A result near a limit can change with the seed |
| Frozen descriptive list | Accept. Add fixed-step mean b and t, no-factor QLIKE, and upper bound against .37 and .525 | No effect on the verdict |
| Windows end by 2018-04-30 | Accept | Same as my round 1 text |

**Where the advocate is wrong, in addition to the t:**
- The Tier numbers .703 and .435 are pooled and include rows after the break. Before the break they are .505 and .454, and without the 2019 PASO, .339 and .406. So the stated threat to power is overstated.
- "Level rule holds" conflicts with point 4.
- A failure rule that covers only "a code change after any printed result" leaves a crash before results undefined. My crash rule covers this case.

## Point 7: bridge check

**Keep it blind:**
1. Write one function, `load_alpaca_closes(start, end)`. It calls `require_open(start, end)` first, parses the file in memory, and drops rows before `start` before it returns. It prints nothing.
2. The bridge calls it with `start` = 2018-05-01. The function asserts that the first returned date is on or after this date.
3. Print no whole-file count, date range, or first row.
4. Unit test it on a synthetic file.
5. Cash events: filter by ex-date from 2018-05-01 before use.
6. Record the contact in the access log.

The file must be parsed whole, so the blindness comes from the code path, and it is not physical. The overlap ends at the last Alpaca date, not at 2026-10-29.

**Limits.** Compute on all overlap dates. Compute the close limits and the RV limit again on 2018-05 to 2019-07, which is nearest to the test.

| ID | Measure | Limit | Basis |
|---|---|---|---|
| B1 | Sessions in one source only | At most 3 | Catches calendar errors |
| B2 | Median log(Alpaca / official), signed | At most 5 bp in size | Catches an adjusted series |
| B3 | Median, absolute | At most 10 bp | `c3.out` |
| B4 | 99th percentile, absolute | At most 100 bp | `c3.out` |
| B5 | Median abs log(RV30 ratio) | At most .05 | 25 bp noise gives .038, 50 bp gives .08 |
| B6 | Change in b, pre-break primary rows, Alpaca RV and HAR | At most .03 | About one tenth of the SD of b in a test. 50 bp gives -.022, 100 bp gives -.049 |

**If a limit fails:**
- **B1 or B2:** Find the cause, fix the reader, rerun, and log it.
- **B3, B4, or B5 only:** Stage 4 stops, and the user decides. To continue, the verdict line states the failed limit.
- **B6:** No verdict with Alpaca RV. The user chooses to drop Stage 5, or to report the test as descriptive only.
- Any change of a limit needs a logged user decision. The check touches open data only, so this does not touch the test.

**Limit of the check:** A pass on open dates does not prove the same fit in 2016-2017, when trading may be thinner. The verdict line says this.

## Final recommended verdict text

> **Rule 1, information.** b on `log_iv2` in HAR+IV has a 95% block-bootstrap interval (21-session blocks, 2,000 resamples, percentile, frozen seed) with a lower bound above zero.
>
> **Rule 2, out-of-sample information.** Clark-West on log loss, HAR nested in HAR+ATM30, t above 1.65, 21-session blocks. Both models train on the same `primary` rows, from position 252, with at least 126 training rows. Each target window ends on or before the origin.
>
> **Rule 3, usable gain.** QLIKE of HAR+ATM30 minus HAR with the Duan factor has an upper bound (97.5th percentile) below zero. No-factor QLIKE is reported beside it.
>
> **Floor.** At least 300 valid origins, a median of at least 17 rows across the 45 fixed-step samples, and at least 180 scored rows. Each target window ends on or before 2018-04-30. The floor is checked from flags, before any return is computed.
>
> **Outcomes.** Apply these in order, and stop at the first match:
> 1. "Inconclusive, data floor" if the floor fails.
> 2. "Supported" if Rules 1 and 2 pass. Add "with usable gain" if Rule 3 also passes. A fail of Rule 3 is not evidence of no gain.
> 3. "Not supported" if b is at or below zero. This means that the test gives no support. It is not evidence that `ATM30` has no information.
> 4. "Inconclusive" otherwise.
>
> Each verdict line states "2016-01 to 2018-04 only". The no-event result is reported at equal rank. If "Supported" holds and the no-event interval includes zero, the line adds "with events only; the ordinary-day question stays open".
>
> Reported, no effect on the verdict: fixed-step mean b and median t, 63-session interval, upper bound against .37 and .525, no-factor QLIKE, Tier 1 only, each 2017 event dropped.

**Operating table to show the user (all four settings, range):**

| True b | Supported | With usable gain | Not supported | Inconclusive |
|---|---|---|---|---|
| 0 | 2 to 4% | about 1% | 50 to 57% | 41 to 46% |
| .37 | 19 to 26% | 6 to 10% | 12 to 20% | 61 to 64% |
| .62 | 44 to 52% | about 20% | 2 to 5% | 45 to 52% |

"Inconclusive" stays the most likely outcome at .37. No rule fixes this, because 0 and .37 are only about 1.0 to 1.25 SD apart. The user should see this before deciding on Stage 5. The IV variance of 2016-2018 is unknown, and a smaller variance lowers these rates.

## Data files read in round 2

`data/forecast_panel.parquet` (rows from 2018-05-01 onward), my stored simulation outputs, and the advocate's report, scripts, and CSV outputs. No locked data, no Alpaca file, no marker, and no project edit.
