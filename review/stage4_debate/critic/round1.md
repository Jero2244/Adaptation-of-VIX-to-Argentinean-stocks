# Critic, round 1: attack on the Stage 4 draft

All checks are exploratory. They add contact with open data only. No locked data was read. `reports/backward_test_unlocked.json` does not exist.

## Method of the checks

Scripts are in this folder. Outputs have the same stem.

| Script | Purpose | Output |
|---|---|---|
| `sim_core.py`, `c1_power.py`, `c1_summary.py` | Applies every draft rule to block-resampled pre-2025-03 panel rows, with b forced to 0, .25, .37, .62 | `c1_summary.out` |
| `c2_dryrun.py` | Applies the draft rules, unchanged, to 28 contiguous 585-session real windows | `c2.out`, `c2_dryrun.csv` |
| `c3_mismatch.py` | Close noise and tier sensitivity. Row counts | `c3.out` |
| `c4_candidates.py` | Operating table of replacement rules | `c4.out` |

**Simulation design.** The grid has 542 sessions: 585, less 21 with no full target window, less 22 for HAR inputs. Rows come from 63-session outer blocks (126 as a check). Missing rows stay missing, so coverage is about .84. The target is y + (b_target - b_pool) x log IV. Each sample gets the study `block_sample` with 21-session blocks, 250 inner resamples. Sims: 500 per pool at 63-session blocks, and 300 at 126. Monte Carlo error is about +/-2 points.

**Pools.** "All" is every pre-2025-03 row (b .525). "No PASO" cuts 2019-07-10 to 2019-09-15 (b .39). The test has no event known to be like 2019, so "No PASO" is probably closer. I report both as a range.

**Limits.**
- The dev rows may not resemble 2016-2018. A calmer IV gives a larger standard error, so power may be lower than shown.
- Forced b is a global shift. Local b still varies by period, and this adds spread. This variation is real, but it is not sampling error in one period.
- The training gap is a fixed 21 sessions, not 30 calendar days.
- I read "upper 95% bound" as the 97.5th percentile.
- The dry-run windows overlap, so only about three are independent.

## Objections, by consequence

### 1. The verdict is close to empty, and the fixed-step t decides it

| True b | "Supported" | "With usable gain" | "Not supported" | "Inconclusive" |
|---|---|---|---|---|
| 0 | 0 to 1% | 0 to .3% | 50 to 57% | 43 to 49% |
| .25 | 1 to 6% | 0 to 2% | 21 to 31% | 68 to 73% |
| .37 | 3 to 13% | 1 to 5% | 12 to 20% | 74 to 77% |
| .62 | 20 to 36% | 6 to 11% | 2 to 5% | 61 to 75% |

So at b = .37, "Not supported" is at least as likely as "Supported" in the two 63-block pools.

**Dry run on real windows (28, about 3 independent):** "Supported" 4, "usable gain" 0, "Not supported" 0, "Inconclusive" 24. The four "Supported" windows all start from 2020-04 to 2020-10, so they are about one result. Local b there is .66 to 1.12.

**Cause.** The rule parts do not have equal weight:

| Part | b = 0 | b = .37 | b = .62 | Dry run, of 28 |
|---|---|---|---|---|
| R1a: interval excludes zero | 4 to 8% | 33 to 44% | 58 to 70% | 14 |
| R1b: fixed-step median t above 1.65 | .6 to 1% | 4 to 15% | 24 to 42% | 4 |
| R1a and R1b | .4 to 1% | 4 to 15% | 24 to 42% | 4 |

- R1b nearly implies R1a: R1b without R1a occurs in at most .4% of sims. So the interval adds almost nothing, and R1b decides Rule 1.
- The median t is not a test statistic. It is the t of a typical single sample of about 20 rows with 5 parameters. Taking a median over 45 samples does not pool their data. It does not have a known null distribution: its false-pass rate is .6 to 1%, not the 5% that "1.65" suggests.
- In the dry run, the median fixed-step t is 1.46 in windows where the interval excludes zero.

**Answer on one-sided against two-sided:** 1.65 and the two-sided interval do not match on paper, but this is not the real defect. The interval's actual false-pass rate is 4 to 8% one-sided, against 2.5% nominal. The fixed-step rate is about 1%. The joint rate is about 1%.

**Root limit, which no rule can fix.** The spread of b across samples is .30 to .38. So b = 0 and b = .37 are only 1.0 to 1.25 SD apart. The bootstrap SE is .21 to .24, which is 1.34 to 1.56 times too small against this spread. Part of the gap is real period variation: b across real windows has SD .35 and a range of .12 to 1.12. So a result describes this period's b, and it does not measure a stable parameter.

**Fix, replace Rule 1:**

> **Rule 1, information (primary).** Pass if b on log `ATM30` squared (`log_iv2`) in HAR+IV has a 95% block-bootstrap interval (21-session blocks, 2,000 resamples, percentile, seed 20261104) with a lower bound above zero. The fixed-step samples (22 and 23) are reported beside it as mean b, range, and median t. They do not decide the verdict.

Effect: pass rate 4 to 8% at b = 0, 33 to 44% at .37, 47 to 62% at .525, 58 to 70% at .62. **Cost:** the false-pass rate rises from about 1% to 4 to 8%. The user must accept this cost knowingly.

### 2. "Not supported" is a sign test, and its .25 clause is dead

- The clause "upper bound below .25" adds at most .3 points beyond "b at or below zero" (`NS` against `NS_b`, all pools at b = 0 to .37). Median interval width is .82 to .95. In the dry run, the lowest upper bound is .444.
- So the label is "b came out negative". At b = .37, it fires 12 to 20% of the time. A value of b = -.01 with interval -.5 to .5 gets "Not supported", which says more than the data does.
- The draft gives no source for .25.
- **Label logic.** A sample with b above zero, a lower bound above zero, and an upper bound below .25 meets both "Supported" and "Not supported". No precedence is stated. This case never occurred in the sims, so it is a text defect only. "Supported" and "with usable gain" also overlap as written.

Falsification is reachable, and I do not claim otherwise. The defect is the meaning. A rule with a stated alternative has about the same rates and a true meaning. "Upper bound below .37" fires 46 to 48% at b = 0, 12 to 16% at .37, and 3 to 7% at .525.

**Fix, replace the outcomes:**

> Apply these in order. The first match is the outcome.
> 1. "Inconclusive, data floor" if the test fails section D.
> 2. "Supported" if Rule 1 passes. Add "with usable gain" if Rule 3 also passes.
> 3. "Below the development size" if the upper bound of b is below .37. This outcome says that the test period does not show the development size (.37, no events before 2025-03). It does not say that b is zero.
> 4. "Inconclusive" otherwise. State the sign of b.
>
> Before the test, the user accepts this table of rates: [insert the final operating table]. Each verdict line states the period: "2016-01 to 2018-04 only".

Effect: "Inconclusive" falls from 74 to 77% to about 41 to 46% at b = .37, and from 61 to 75% to about 27 to 36% at b = .62.

### 3. The data floor can decide the verdict, and it is undefined

"20 non-overlapping windows" has three readings:

| Reading | Value | Result |
|---|---|---|
| Whole grid, 21-session spans | 25.8 | Never binds |
| Fixed-step rows, median | 22 at 92% coverage, 20 at 81%, 18 at 75% | Binds below about 81% coverage |
| Rule 2 scored span | 14.9 | Always fails |

- Under the fixed-step reading, 13 of 28 real windows fail, and **all 4 "Supported" windows are among them**. So the floor would remove every pass in the dry run. In sims, it fails 14 to 22% of the time.
- Fixed-step rows are also lost by chance of phase. A step near the monthly cycle meets missing days just after expiry. Minimum rows across offsets fall to 11 in real windows.
- The draft's "about 28 windows" is 585/21. The usable number is 25.8 by grid and about 20 by fixed-step rows.
- The 300-origin floor never binds. Coverage would need to fall to .55.

**Fix, replace the floor in section D:**

> Floor: at least 300 valid origins, and at least 20 spans of 21 sessions from the first to the last valid origin. Fixed-step row counts are reported, and they do not decide the floor. The target frame ends on 2018-04-30, so the last origin has a full window inside the test. The frame is not joined to data from 2018-05 onward.

### 4. No step builds the test series, and the current builders cannot do it

Item E4 says that `run_tests_once.py` "reads the locked period". No item builds `ATM30` for that period. From the code, not run:

- `build_snapshot.py` zips definitions, quotes, and `EQUITY_BBO`. XNAS starts on 2018-05-01 (data README). So `zip` gives no days for the locked period, and `pd.concat` raises an error.
- Its `fetch_rates()` runs first, with `cosd=2018-01-01`. So it overwrites `data/source/fred_rates.csv` before the error. This changes a file that the open data uses, and it breaks any hash of that file.
- It writes to `data/option_snapshot_1545.parquet`, `option_listed.parquet`, and `session_diagnostics.parquet`. `build_series.py` writes `index_series.parquet`. A test build at these paths overwrites the open series.
- `build_series.py` uses `stock_mid` for the forward check and `day_conditions(EQUITY_BBO)` for a flag. The test has no stock mid, so the forward check that found 2022-07-08 is absent.

The floor also comes too late. As drafted, a floor failure is known only after outcomes are read.

**Fix, add to section E:**

> 4a. Write `build_test_series.py`. It uses a separate output folder, `data/test/`, and a separate rates file. The equity input is optional. The forward check uses the prior Alpaca close only in the outcome step.
> 4b. Split the run into two steps, each with its own log entry and user approval.
> - **Step A, options only.** Read definitions and quotes. Build `ATM30`. Print only counts by year: sessions, listed bracket, valid days, tier, missing reason, near-term days. Do not read Alpaca. Do not print IV values. Check the floor here. If the floor fails, stop, and report "Inconclusive, data floor", with no RV read.
> - **Step B, outcomes.** Read Alpaca, compute RV, and apply the frozen rules.

This needs the gate to separate the two steps. See objection 5.

### 5. Freeze integrity

The gate works for current code. No current code passes a date before 2018-05 by accident, and the unit tests use a temporary marker. The gaps are these:

- **The gate does not cover Alpaca.** `data/source/alpaca_ggal_sip_raw.json` has no reader, and nothing stops a plain `json.load`. The same is true of the 2016-2017 rows in `adr_cash_events.csv`, and `build_series.py` loads them today (for flags). So "reads the locked period through `require_open`" is not yet true.
- **The marker only needs to exist.** An empty file opens every read, permanently, for every script. The draft does not state the order of the unlock marker and the test-run marker, or who creates each.
- **No crash rule.** "It refuses a second run" does not say what follows a crash after a read. One reading loses the test to a bug. The other allows reruns, which are forking paths.
- **The manifest checks itself.** It is in the same folder, with no git history, so anyone can rewrite it and the marker. The check runs inside the script that it protects.
- **Synthetic data cannot catch real schema errors.** Item E5 will not find an Alpaca date format, a missing session, or an ex-date that `attach_cash` rejects.
- **Shared event list.** `events.py` loops over `EVENTS` on the session grid. A 2017 date maps to the first dev session in `first_session`, so adding it there changes the dev event table, and it conflicts with item E3. `tests/test_stage3.py:266` also loops over this list.

**Fix, replace E4, E5, and E7:**

> E4. `run_tests_once.py` runs Step B only. Before any read it: (a) checks the manifest, (b) writes `reports/test_run_started.json` with the time and the manifest hash, (c) refuses to run if that file exists. All Alpaca reads go through one function, `load_alpaca_closes(start, end)`, which calls `require_open`.
> E5. Test with synthetic data. Then run the same code, unchanged except for its date range, on the first 585 sessions from 2018-05-01 with Alpaca closes. This is the dress rehearsal. It must reproduce the panel within the bridge limits (objection 8).
> E7. Write the SHA-256 manifest, including `conda list` output. Give the manifest hash to the user before Step A. The user keeps it outside this folder, for example in an email to themselves.
> Crash rule: A crash before the first outcome is computed allows one rerun after a logged code fix that changes no method. A crash after this point ends the test: the result is "Not run", and the code fix and any rerun are reported as exploratory. Any change of method makes the period development data.
> Use two markers. `reports/backward_test_options_unlocked.json` opens options reads for Step A. `reports/backward_test_unlocked.json` also opens `load_alpaca_closes` for Step B. `iter_days` gets a marker argument, because it now always uses the default. Each marker holds the manifest hash, and `require_open` checks that the marker parses and that the hash is present. The events of the test are in a new constant, `TEST_EVENTS`.

### 6. Rule 2 adds little, and it adds noise

- **Rows.** 263 scored rows (median) on a span of 14.9 windows. The first fit has about 126 to 170 rows, about 9 windows, for 5 parameters.
- **Size.** Clark-West above 1.65 occurs 10 to 12% at b = 0, against 5% nominal.
- **Power.** 23 to 29% at b = .37, 46 to 55% at b = .62.
- **Start at the 126-row floor, with no position 252:** adds about 50 rows, and rates do not improve (20 to 27% at .37).

**Frozen coefficients, tested.** Weights fit on dev rows and scored on all test rows.
- Leak: no locked outcome enters the weights. The weights use later calendar data, so this is not a real-time forecast.
- Without a level correction, the rate at b = 0 is 10 to 19%. The dev level does not fit, so plain Clark-West is not a valid test here.
- With a test-period mean removed: 6 to 13% at b = 0, and 46 to 59% at .37.
- But it is almost the same test as Rule 1. Passing R1a and frozen-weight together has nearly the same rate as R1a alone (33 to 44% at .37). So it adds no gate. Sim rows also come from the pool that fit the weights, so its power is optimistic.

**Fix, replace Rule 2:**

> **Rule 2, out-of-sample information (reported).** Clark-West on log loss, HAR nested in HAR+ATM30, both trained on the same rows (those with `primary` true), from position 252, with at least 126 rows and 21-session blocks. Report t, and state that about 15 windows support it. It does not decide the verdict. If Rule 1 passes and t is above 1.65, the verdict line adds "also out-of-sample".

The rate of this added phrase: 2 to 4% at b = 0, 19 to 26% at .37, 44 to 52% at .62. If the judge wants Rule 2 kept as a gate, these are the "Supported" rates, and they are still far above the draft's 3 to 13% at .37.

The phrase "longest available for each model" must go too. HAR could then train on days with no `ATM30`, and the models would not be nested on the same rows.

### 7. "Must hold under both" punishes a known bias, and it answers a problem that the test may not have

- **The Duan factor is the QLIKE-best scale in training.** The k that minimizes QLIKE of k x F is mean(RV/F), and that is the Duan factor. No factor is therefore a misscaled forecast, not a rival calibration. In sims, no-factor forecasts average .81 to .85 of the target, and Duan forecasts .97 to .98.
- **The reason for the no-factor leg comes from 2019.** It guards against one jump that inflates the factor. The test training set has only 2016-2017 rows. Nobody yet knows if a jump of that kind occurs there.
- **Result.** "With usable gain" is 6 to 11% at b = .62, and 0 of 28 in the dry run.

**What the draft gets right:** QLIKE with Duan alone has a false-pass rate of 4 to 9% at b = 0, and "both" holds it to 2 to 3%. The rule has a real benefit when it stands alone. But under my Rule 1 it does not stand alone. R1a and Duan together give about 1% at b = 0, 7 to 10% at .37, and 20% at .62.

**Fix, replace Rule 3:**

> **Rule 3, usable gain.** Applies only if Rule 1 passes. QLIKE of HAR+ATM30 minus HAR with the Duan factor has a 95% interval (97.5th percentile) with an upper bound below zero. The no-factor result and the mean of forecast over target are reported beside it. If the two signs differ, the verdict line says so. The largest single-row share of the training factor is reported at the first and last origin.

**Weakness that I accept:** One large training row can still set the factor. The reported share shows this if it occurs.

### 8. Input mismatch: run the bridge, but noise is not the danger

I did not read Alpaca. These runs add noise of an assumed size to official closes, on pre-2025-03 rows (b .525).

| Close noise | b | Correlation of `log_rv1` |
|---|---|---|
| 5 bp | .525 | .996 |
| 25 bp | .518 | .930 |
| 50 bp | .503 | .833 |
| 100 bp | .476 | .652 |
| 1% of closes off by 2% | .520 | |

So ordinary SIP-against-official differences do not change a verdict. **Gross errors are the risk:** dates, an adjusted series, missing sessions, a bar from a different session. Item E has no check for these.

**Tier share is a smaller worry than I expected. I drop it as a threat to the verdict.** Before 2025-03, b is .505 on Tier 1 and .454 on Tier 2. Without the 2019 PASO, it is .339 and .406. The gap of .703 and .435 in the findings comes mainly from after the break. Across real windows, correlation of b with Tier 2 share is .02, and with coverage .08. Report the share. Do not set a threshold.

**Fix, add to section D:**

> **Bridge check, before the freeze.** Load the Alpaca closes through the gated reader, for 2018-05-01 onward only. Filter by date before any statistic. Report: sessions in one source only, and the median, 99th percentile, and maximum of |log(Alpaca close / official close)|. Rebuild the panel with Alpaca closes and report b before 2025-03. Limits: no missing sessions except listed half days or holidays, median at most 10 bp, 99th percentile at most 100 bp, and a change in b of at most .03. A failure stops Stage 4 and returns to the user. Log this contact.

**Checks that need no outcome (all in Step A):**
- Definitions alone: listed expiries per session, days with a listed 30-day bracket, strikes per bracket term, and strike gaps as a share of the median strike.
- Quote rows: two-sided pairs per term, and quote age.
- Parity forward: only from the options, and counts only are printed.

### 9. The verdict does not test what the study says the test is for

`reports/stage3_findings.md`, item 8, says that the period "can test the weak result on ordinary days". The draft keeps events in, and the no-event result "does not change the verdict". In dev, a pass with events can come from event windows: events are 9% of rows and 57% of the gain. So "Supported" could rest on 2017 PASO and midterm rows, while the open question remains open.

Keeping events in has a sound reason, since IV should price events. But that choice came after results showed where the gain sits. It tilts toward a pass.

**Fix, add to section C:**

> The no-event result is reported at equal rank. If "Supported" holds with events and the no-event interval includes zero, the verdict line says "Supported, with events only; the ordinary-day question stays open".

### 10. Method choices: which are forking paths

**Main point:** Every choice in section B came after contact with dev results, but none came after contact with test outcomes. So a frozen choice does not contaminate the test. Forking affects which question is tested, not the clean state of the test. The descriptive report stays exploratory, as the draft says.

| Item | Status |
|---|---|
| GARCH errors, EWMA lambda | **Not needed for the verdict.** Neither model is in any rule. Keep them in the descriptive report only |
| Training start | **Moot in the test.** The -.043 and -.077 problem comes from GARCH common days, and GARCH is not in the test. See objection 6 for the wording |
| Fixed steps | Clean for reporting. Not valid as a gate (objection 1) |
| Level rule | Reacts to 2019, which is not in the test (objection 7) |
| Events in | Forking path that cannot be fully cleaned. Equal-rank reporting is the remedy (objection 9) |
| .25, 1.65, median t, 21-session block | Have no stated source. 21-session blocks give the largest t in dev. Report 63-session blocks (about 8 blocks) beside them |
| Stage 2 rules | Set before Stage 3 results. Low risk |

**Claim that cannot be made clean:** "the only clean data". Three contacts remain:
- The Alpaca file comes from `options-valuation-model/research/stock_history_check_20260915/`, which also holds `summary.json` and `quality_followup.json`. I did not open them. That project may have computed statistics on 2016-2018 closes.
- The access log records the dividend rows and the bar counts.
- The user knows the market history of that period.

**Fix, replace the second line of section A:**

> 2016-01 to 2018-04 is the only period that this study has not analyzed. Earlier contact: [list from the user, including any use of these closes in `options-valuation-model`]. Only this period gets a verdict.

### 11. Small wording items

- Rule 1 says "log ATM30". The study regresses on `log_iv2`, which is log `ATM30` squared. Coefficients differ by a factor of 2, so any threshold depends on this.
- Freeze these numbers: resamples, seed, percentile type, rounding, and the session calendar of the test.
- FRED rates: fetch once to a new file, and put that file in the manifest.
- Item E1 must show the user the operating table, not only the findings. The user cannot choose rules without the rates.
- The step at E3 is otherwise sound, and it is needed for the descriptive report.

## Objections that I tested and dropped

- **Outcome labels overlap in practice.** It never occurred in the sims. It is a text defect only.
- **Thin coverage breaks inference.** Across real windows with coverage .75 to .90, SE stays about .18 to .39, and it does not track coverage.
- **Close noise changes b.** Not at plausible sizes (objection 8).
- **The gate leaks through existing scripts.** No current script does this.

## Data files read

- `data/forecast_panel.parquet`: all rows printed or used are from 2018-05-01 onward. Yearly spread and pair medians include 2026.
- `reports/stage3_findings.md`, `reports/stage2_findings.md`, `reports/coverage_by_year.csv`, `coverage_missing_reasons.csv`, `coverage_by_near_days.csv`.
- `review/verify_debate.txt`, `review/README.md`.
- `data/input_manifest.json`: first 30 lines (hashes and paths).
- `databento_ggal_20261031/README.md`: matching lines only (coverage and exposure).
- Directory listings only: `data/source/`, `options-valuation-model/research/stock_history_check_20260915/`.

Not opened: `alpaca_ggal_sip_raw.json`, raw Databento files, `adr_cash_events.csv` rows, `fred_rates.csv`.
