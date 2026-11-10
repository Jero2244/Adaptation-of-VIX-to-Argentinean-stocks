# Stage 4: descriptive report of the seen data

Period: 2018-05-01 to 2026-10-29. **This period has no verdict.** All results are exploratory, because the method came after contact with these data. Only the 2016-01 to 2018-04 test gets a verdict. That period stays locked, and this report did not read it.

The "95%" intervals really cover about 80% to 91% in simulation, so they are too narrow.

## Coefficient on `log_iv2` in HAR+IV

"No events" drops each origin with a listed election in its target window.

| period | events | n | b | low21 | high21 | low63 | high63 |
|---|---|---|---|---|---|---|---|
| All | with events | 1806 | 0.622 | 0.337 | 0.916 | 0.309 | 0.946 |
| All | no events | 1643 | 0.459 | 0.152 | 0.715 | 0.060 | 0.761 |
| Before 2025-03 | with events | 1431 | 0.525 | 0.208 | 0.862 | 0.152 | 0.922 |
| Before 2025-03 | no events | 1300 | 0.366 | -0.018 | 0.682 | -0.131 | 0.717 |
| From 2025-03 | with events | 375 | 1.190 | 0.488 | 1.516 | 0.330 | 1.516 |
| From 2025-03 | no events | 343 | 0.781 | 0.227 | 1.244 | 0.149 | 1.415 |
| 2018-2023 | with events | 1165 | 0.526 | 0.192 | 0.875 | 0.123 | 0.916 |
| 2018-2023 | no events | 1034 | 0.364 | -0.030 | 0.721 | -0.201 | 0.762 |
| 2024-2025 | with events | 464 | 1.185 | 0.588 | 1.469 | 0.523 | 1.471 |
| 2024-2025 | no events | 432 | 0.891 | 0.429 | 1.223 | 0.393 | 1.324 |
| 2026 | with events | 177 | 0.423 | -0.387 | 1.569 |  |  |
| 2026 | no events | 177 | 0.423 | -0.387 | 1.569 |  |  |

## Fixed-step non-overlapping samples

Steps of 22 and 23 sessions. Reported only. These samples share periods, so they are not independent evidence. "No 2019 PASO windows" drops only that event.

| step | samples | median_n | mean_b | min_b | max_b | median_t | events |
|---|---|---|---|---|---|---|---|
| 22 | 22 | 82.500 | 0.611 | 0.171 | 1.095 | 2.696 | with events |
| 23 | 23 | 78.000 | 0.602 | 0.352 | 0.837 | 2.677 | with events |
| 22 | 22 | 81.500 | 0.500 | 0.091 | 0.998 | 2.404 | no 2019 PASO windows |
| 23 | 23 | 78.000 | 0.493 | 0.238 | 0.729 | 2.583 | no 2019 PASO windows |

## Same-row race: HAR+ATM30 against HAR

Both models train on all `primary` rows with a target window that ends on or before the origin. 1599 rows are scored, from 2019-05-02. A negative difference favors HAR+ATM30. The Duan factor decides the level rule, and the no-factor result is beside it.

| level_rule | qlike_difference | low | high | mean_forecast_har | mean_forecast_har_atm | mean_target |
|---|---|---|---|---|---|---|
| Duan factor | -0.0187 | -0.0444 | 0.0115 | 0.6267 | 0.6246 | 0.4840 |
| No factor | 0.0002 | -0.0339 | 0.0375 | 0.3516 | 0.3679 | 0.4840 |

## Clark-West on log loss, without a level factor

HAR is nested in HAR+ATM30. A positive mean favors HAR+ATM30.

| blocks | mean | t | low | high |
|---|---|---|---|---|
| 21 | 0.0624 | 2.6967 | 0.0164 | 0.1080 |
| 63 | 0.0624 | 2.0685 | 0.0036 | 0.1210 |

## Other frozen sensitivity results

GARCH with t errors is primary, and normal errors are also reported. Both are in `reports/stage3_results.md`. Neither affects a verdict. EWMA with the lambda of .94 is primary, and .98 is a sensitivity run, on the common rows of the calibrated race:

| lam | n | qlike |
|---|---|---|
| 0.9400 | 1460 | 0.3989 |
| 0.9800 | 1460 | 0.3839 |

## Reconciliation with the review scripts

`review` holds the values in `review/verify_debate.txt`. `study_code` holds the values of this run.

| item | review | study_code | difference |
|---|---|---|---|
| fixed step 22, mean b | 0.6110 | 0.6113 | 0.0003 |
| fixed step 23, mean b | 0.6020 | 0.6021 | 0.0001 |
| fixed step 22, no PASO, mean b | 0.5000 | 0.5000 | 0.0000 |
| fixed step 23, no PASO, mean b | 0.4930 | 0.4928 | -0.0002 |
| no events, b | 0.4590 | 0.4586 | -0.0004 |
| no events before 2025-03, b | 0.3660 | 0.3658 | -0.0002 |
| from 2025-03, b | 1.1900 | 1.1902 | 0.0002 |
| from 2025-03, no events, b | 0.7810 | 0.7806 | -0.0004 |
| scored rows | 1599.0000 | 1599.0000 | 0.0000 |
| Clark-West mean | 0.0624 | 0.0624 | -0.0000 |
| Clark-West t, 21 blocks | 2.7000 | 2.6967 | -0.0033 |
| Clark-West t, 63 blocks | 2.0700 | 2.0685 | -0.0015 |
| QLIKE no factor mean | 0.0002 | 0.0002 | -0.0000 |
