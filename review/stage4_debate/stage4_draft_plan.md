# Stage 4 draft plan (version 0, for debate)

Goal of Stage 4: freeze the method and verdict rules, and prepare a one-time test of 2016-01 to 2018-04 that can run later. Stage 4 does not run the test and does not create `reports/backward_test_unlocked.json`.

## A. Role of each period

- 2018-05 to 2026-10 is already seen. It gets a frozen descriptive report and no verdict.
- 2016-01 to 2018-04 is the only clean data. Only this period gets a verdict.
- The test falls entirely before the 2025-03 format break, and it has about 28 non-overlapping windows. So the claim under test is narrow: "On pre-break data, does ATM30 add information beyond past RV?" It includes the 2017 PASO and midterm events.

## B. Proposed method choices (user must approve)

| Item | Draft choice | Reason |
|---|---|---|
| Non-overlapping samples | Fixed steps of 22 and 23 sessions, replacing first-valid-session | Current paths merge |
| Training start | Longest available for each model, on identical scored rows | Common training days drop 2018-06 to 2019-04 from HAR |
| Level rule | Duan factor primary. No factor reported beside it. A usable gain must hold under both | No single factor is clean. A rule must not name 2019 |
| GARCH | t errors primary, normal as sensitivity | Normal fit is set by 2019-08-12 |
| EWMA | Lambda .94 stays. .98 is sensitivity only | .94 was fixed before results |
| Training floor, variance floor | 126 rows, 1e-6, unchanged | Little effect |
| Stage 2 rules | Accepted as written | 25% strike limit, log-strike IV, prior-day yield, no skip of a failed expiry |
| Headline scope | Each headline states with and without events, and period | From findings item 5 |

## C. Verdict rules, for the one-time test only

**Rule 1, information (primary).** Pass if both hold:
- b on log ATM30 in HAR+IV is above zero, and the 95% block-bootstrap interval (21-session blocks) excludes zero.
- Mean b over fixed-step samples (22 and 23) is above zero, with median t above 1.65.

**Rule 2, out-of-sample information.** Clark-West on log loss, HAR nested in HAR+ATM30, t above 1.65 with 21-session blocks. Training is expanding inside the test period, from position 252 with at least 126 training rows.

**Rule 3, usable gain.** QLIKE of HAR+ATM30 minus HAR is below zero, and the upper 95% bound is below zero, under both the Duan factor and no factor.

**Outcomes:**
- "Supported" if Rules 1 and 2 pass.
- "Supported, with usable gain" if Rules 1, 2, and 3 pass.
- "Not supported" if b is at or below zero, or the upper bound of b is below .25.
- "Inconclusive" otherwise, or if the test fails the data floor in section D.

Events stay in for the verdict, because IV should price scheduled events. The no-event result is reported beside it, and it does not change the verdict.

## D. Data floor and test-only inputs

- Floor: at least 300 valid origins and 20 non-overlapping windows. Below this, the verdict is "Inconclusive".
- RV uses Alpaca raw closes, because XNAS equity data does not cover the period. Cash events use the two dividend rows in `adr_cash_events.csv`.
- Add 2017 PASO and midterm dates to the event list before the unlock.
- FRED rates must cover 2016-2018.

## E. Work items

1. Show the user `reports/stage3_findings.md`, and get answers on sections B and C.
2. Move the review checks into study code, with unit tests: fixed-step samples, Clark-West, longest-training rows, no-factor and Duan races side by side.
3. Rerun `run_development.py` on 2018-05 to 2026-10, and confirm the moved checks match `review/verify_debate.txt`. Write the descriptive report.
4. Write `run_tests_once.py`. It reads the locked period through `require_open`, runs the frozen rules, and writes one test-run marker. It refuses a second run.
5. Test `run_tests_once.py` with a synthetic dataset that has no real data.
6. Update `PROTOCOL.md`, mark it frozen, and add an access-log entry.
7. Write a SHA-256 manifest of the code, `PROTOCOL.md`, and input files, because this folder has no git history. `run_tests_once.py` checks this manifest before it runs.
8. Stop. Ask the user before Stage 5.

## F. Decisions left to the user

- All of sections B and C.
- Whether Stage 5 runs at all.
</content>
</invoke>
