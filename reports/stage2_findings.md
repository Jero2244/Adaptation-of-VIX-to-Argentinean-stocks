# Stage 2 findings

Exploratory. The numbers are in `stage2_coverage.md`, and the plots are in `atm30_inspection.png`.

## Plan checks

| Check | Plan | Study | Result |
|---|---|---|---|
| `ATM30` coverage, 2018-2024 | .91 .90 .85 .72 .78 .85 .91 | .911 .901 .854 .718 .781 .852 .913 | Match |
| Listed bracket, the "95%" | 95% | 95.2% to 2024 | Match |
| Two-sided pair on both terms, the "83%" | 83% | 84.5% to 2024, 86.4% in all | About 1.5 points are not explained |
| Tier 1 on both terms | 729 days | 878 to 2024, 1,285 in all | Not reproduced. 679 to 2024 with a 15% strike limit, so the debate rule was probably tighter |
| `ATM30`/`MF30`, 2024 | 1.07 | 0.946 (`MF30`/`ATM30` is 1.057) | The plan's ratio is probably inverted. This is not confirmed |

## The 95% and 83% gap

- 95.3% of sessions have two listed expiries that bracket 30 days. The other 101 sessions fall just after a monthly expiry, when the next expiry is more than 30 days away.
- 86.4% have a two-sided pair on both terms. Most of the loss is on the near term, which has 0-6 days on many of these sessions.
- Coverage is .677 with 0-6 days to the near expiry, and .94 to .97 with more days. So missing days depend on the expiry cycle.

## Quote format break

- The most common flag value changes from 200 to 192 on 2025-02-20. Rows per contract fall from 390 to about 100-200.
- Coverage does not fall at the break. Removing the age limit changes the value on only 1.7% of the six months after the break.
- Near-money spreads do not jump at the break: the monthly median is .133 in February 2025 and .154 in March 2025. They rise from April 2025.

## Limits

- Median near-money relative spread is .634 in 2026, .43 in 2022, and .48 in 2023, against .209 in 2024. This is the widest value across the strikes and terms used, so one wide quote can set it.
- Tier 1 share is low in 2021-2022 (.28 and .13).
- Quote noise can produce large one-day moves. Examples are 2026-03-19 (log change -.384) and 2026-10-01 (+.326), both with a spread above .9.
- The median share of `MF30` variance outside the quoted range is .18 in 2024 and .25 in 2026.

## Event windows

- 2019-08-12: `ATM30` rises from 76.5 to 105.0, on a Tier 2 value, then falls back to 92.0. The near term has 4 days.
- Rights date: `ATM30` is missing from 2025-01-17 to 2025-01-22, and the values on each side show no break (48.5 and 48.6).
- Four sessions have a near forward more than 5% from the stock mid. Three have a dividend ex-date in the front term. 2022-07-08 has none, so it needs a review.
