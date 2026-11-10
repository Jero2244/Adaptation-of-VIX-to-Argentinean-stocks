# Stage 2: series and coverage

Exploratory. This report covers 2018-05-01 to 2026-10-29. The 2016-01 to 2018-04 test stays locked. Missing days stay missing.

## Coverage by year

| year | sessions | listed_bracket | any_quote_both | pair_both | atm30 | tier1 | tier2 | atm30_floor7 | atm30_usable | atm30_session_last | mf30 | atm30_share |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2018 | 169 | 160 | 157 | 154 | 154 | 137 | 17 | 127 | 154 | 157 | 79 | 0.911 |
| 2019 | 252 | 241 | 238 | 227 | 227 | 193 | 34 | 193 | 227 | 230 | 77 | 0.901 |
| 2020 | 253 | 242 | 240 | 216 | 216 | 108 | 108 | 196 | 216 | 218 | 10 | 0.854 |
| 2021 | 252 | 238 | 237 | 182 | 181 | 51 | 130 | 168 | 183 | 182 | 2 | 0.718 |
| 2022 | 251 | 239 | 239 | 196 | 196 | 25 | 171 | 177 | 199 | 196 | 0 | 0.781 |
| 2023 | 250 | 239 | 237 | 213 | 213 | 152 | 61 | 188 | 214 | 215 | 65 | 0.852 |
| 2024 | 252 | 240 | 237 | 230 | 230 | 212 | 18 | 193 | 230 | 233 | 174 | 0.913 |
| 2025 | 250 | 239 | 236 | 234 | 234 | 220 | 14 | 194 | 234 | 238 | 176 | 0.936 |
| 2026 | 208 | 198 | 198 | 195 | 195 | 187 | 8 | 161 | 195 | 195 | 162 | 0.938 |
| all | 2137 | 2036 | 2019 | 1847 | 1846 | 1285 | 561 | 1597 | 1852 | 1864 | 745 | 0.864 |

- `listed_bracket`: two listed expiries bracket 30 days.
- `any_quote_both`: both bracketing expiries have a quote within 30 minutes.
- `pair_both`: both bracketing expiries have a two-sided call-put pair at one strike.
- `atm30`: the primary series. `tier1` means both terms have a bracketed forward or a strike at the forward.
- `atm30_floor7`: the near term has at least 7 days.
- `atm30_usable`: the nearest expiries with an IV bracket 30 days, so a failed expiry can be skipped.
- `atm30_session_last`: no quote-age limit, so the quote can be from any time from 09:30 to 15:45.

## The coverage ladder for all sessions

| Step | Sessions |
|---|---|
| All sessions | 2137 |
| Listed bracket | 2036 (95.3%) |
| A quote on both terms | 2019 (94.5%) |
| A two-sided pair on both terms | 1847 (86.4%) |
| `ATM30` | 1846 (86.4%) |
| `ATM30` Tier 1 | 1285 (60.1%) |
| `atm30_usable` | 1852 (86.7%) |
| `atm30_session_last` | 1864 (87.2%) |

## Coverage against the debate check

The debate rule is not fully recorded in the plan, so differences can come from the rule.

| index | debate | study |
|---|---|---|
| 2018 | 0.91 | 0.911 |
| 2019 | 0.9 | 0.901 |
| 2020 | 0.85 | 0.854 |
| 2021 | 0.72 | 0.718 |
| 2022 | 0.78 | 0.781 |
| 2023 | 0.85 | 0.852 |
| 2024 | 0.91 | 0.913 |

## Coverage by days to the near expiry

| near_days | sessions | atm30 | tier1 | tier2 | atm30_share |
|---|---|---|---|---|---|
| 0-6 | 368 | 249 | 111 | 138 | 0.677 |
| 7-13 | 504 | 474 | 307 | 167 | 0.94 |
| 14-20 | 483 | 464 | 346 | 118 | 0.961 |
| 21-30 | 681 | 659 | 521 | 138 | 0.968 |

## Reasons for missing `ATM30`

| status | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|
| far: no pair within the strike distance | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| far: no two-sided pair | 0 | 0 | 0 | 1 | 3 | 1 | 0 | 0 | 0 |
| near: no two-sided pair | 6 | 14 | 26 | 55 | 40 | 25 | 10 | 5 | 3 |
| no listed bracket | 9 | 11 | 11 | 14 | 12 | 11 | 12 | 11 | 10 |

## Quote format break

| month | sessions | atm30 | session_last | median_age | tier1 | rows_per_instrument | flag_mode | null_bid_share |
|---|---|---|---|---|---|---|---|---|
| 2024-10 | 23 | 23 | 23 | 0.0 | 22 | 390.0 | 200.0 | 0.0 |
| 2024-11 | 20 | 15 | 16 | 0.0 | 12 | 390.0 | 200.0 | 0.0 |
| 2024-12 | 21 | 20 | 21 | 0.0 | 19 | 390.0 | 200.0 | 0.0 |
| 2025-01 | 20 | 17 | 17 | 0.0 | 16 | 390.0 | 200.0 | 0.0 |
| 2025-02 | 19 | 19 | 19 | 0.0 | 16 | 390.0 | 200.0 | 0.0 |
| 2025-03 | 21 | 21 | 21 | 0.0 | 20 | 101.354 | 192.0 | 0.094 |
| 2025-04 | 21 | 21 | 21 | 1.0 | 21 | 168.261 | 192.0 | 0.101 |
| 2025-05 | 21 | 18 | 18 | 1.0 | 16 | 205.515 | 194.0 | 0.107 |
| 2025-06 | 20 | 20 | 20 | 1.0 | 18 | 204.716 | 194.0 | 0.129 |

Changes in the most common flag value:

| session_date | flag_mode |
|---|---|
| 2023-05-30 00:00:00 | 194 |
| 2023-05-31 00:00:00 | 200 |
| 2024-04-12 00:00:00 | 198 |
| 2024-04-15 00:00:00 | 200 |
| 2024-04-26 00:00:00 | 194 |
| 2024-04-29 00:00:00 | 200 |
| 2024-06-12 00:00:00 | 194 |
| 2024-06-13 00:00:00 | 200 |
| 2024-06-14 00:00:00 | 194 |
| 2024-06-17 00:00:00 | 200 |
| 2024-09-09 00:00:00 | 194 |
| 2024-09-10 00:00:00 | 200 |
| 2025-02-20 00:00:00 | 192 |
| 2025-02-25 00:00:00 | 196 |
| 2025-02-27 00:00:00 | 192 |
| 2025-02-28 00:00:00 | 196 |
| 2025-03-03 00:00:00 | 192 |
| 2025-03-04 00:00:00 | 196 |
| 2025-03-10 00:00:00 | 192 |
| 2025-03-11 00:00:00 | 196 |
| 2025-03-14 00:00:00 | 192 |
| 2025-04-04 00:00:00 | 196 |
| 2025-04-08 00:00:00 | 192 |
| 2025-04-14 00:00:00 | 196 |
| 2025-04-15 00:00:00 | 192 |
| 2025-04-17 00:00:00 | 196 |
| 2025-04-21 00:00:00 | 192 |
| 2025-04-22 00:00:00 | 196 |
| 2025-04-28 00:00:00 | 192 |
| 2025-04-30 00:00:00 | 194 |
| 2025-07-30 00:00:00 | 192 |
| 2025-07-31 00:00:00 | 194 |
| 2025-08-04 00:00:00 | 192 |
| 2026-03-02 00:00:00 | 196 |
| 2026-03-03 00:00:00 | 192 |

Median absolute log gap between `atm30_session_last` and `atm30`: 0.0000 before 2025-02, and 0.0000 from 2025-04.

## Checks

- `ATM30`/`MF30` median vol ratio in 2024: 0.946, on 174 sessions. The debate check was near 1.07.
- `ATM30`/`MF30` median vol ratio from 2024: 0.930, on 512 sessions.
- Median share of `MF30` variance outside the quoted range from 2024: 0.204.
- Median log(near forward / stock mid): 0.0007. Absolute value above 0.05: 4 sessions.
- Duplicate quotes removed from the snapshot: 0. Quotes without a definition: 0. Other roots: 0.

## Flags

| index | sessions | with_atm30 |
|---|---|---|
| flag_front_under_7d | 368 | 249 |
| flag_ex_in_front | 245 | 238 |
| flag_rights_in_front | 0 | 0 |
| flag_rights_in_bracket | 19 | 17 |
| flag_option_degraded | 3 | 2 |
| flag_equity_degraded | 3 | 1 |
| flag_half_day | 17 | 0 |
