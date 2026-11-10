# Stage 3: development results

All results are exploratory. This run read 2018-05-01 to 2026-10-29, and the 2016-01 to 2018-04 test stays locked. No verdict rule exists until Stage 4. `1806` origins are in the primary sample, from 2018-06-01 to 2026-09-29.

## Primary question: does log `ATM30` add information beyond log RV over 1, 5, and 22 sessions?

The target is log RV over the next 30 calendar days. All models use identical dates. `log_iv2` is log `ATM30` squared. Newey-West (`nw_t`, 21 lags) is for comparison only. Bootstrap: 2000 resamples. `boot63` is blank when fewer than three blocks fit.

### Coefficients in the HAR+IV regression

| period | coefficient | n | estimate | boot21_t | boot21_low | boot21_high | boot63_t | boot63_low | boot63_high | nw_t | r2 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| all | const | 1806 | -0.480 | -3.915 | -0.730 | -0.267 | -3.387 | -0.818 | -0.255 | -4.022 | 0.177 |
| all | log_rv1 | 1806 | 0.008 | 1.083 | -0.007 | 0.021 | 1.027 | -0.008 | 0.022 | 1.045 | 0.177 |
| all | log_rv5 | 1806 | 0.100 | 2.674 | 0.025 | 0.169 | 3.137 | 0.034 | 0.158 | 2.753 | 0.177 |
| all | log_rv22 | 1806 | -0.025 | -0.236 | -0.234 | 0.179 | -0.227 | -0.243 | 0.185 | -0.248 | 0.177 |
| all | log_iv2 | 1806 | 0.622 | 4.133 | 0.337 | 0.916 | 3.778 | 0.309 | 0.946 | 4.126 | 0.177 |
| 2018-2023 | const | 1165 | -0.548 | -4.087 | -0.863 | -0.331 | -3.340 | -0.965 | -0.317 | -4.384 | 0.135 |
| 2018-2023 | log_rv1 | 1165 | 0.015 | 1.619 | -0.004 | 0.034 | 1.592 | -0.004 | 0.033 | 1.594 | 0.135 |
| 2018-2023 | log_rv5 | 1165 | 0.110 | 2.206 | 0.013 | 0.206 | 2.518 | 0.016 | 0.190 | 2.267 | 0.135 |
| 2018-2023 | log_rv22 | 1165 | -0.025 | -0.193 | -0.299 | 0.213 | -0.178 | -0.279 | 0.268 | -0.207 | 0.135 |
| 2018-2023 | log_iv2 | 1165 | 0.526 | 2.995 | 0.192 | 0.875 | 2.606 | 0.123 | 0.916 | 2.980 | 0.135 |
| 2024-2025 | const | 464 | 0.043 | 0.173 | -0.664 | 0.319 | 0.152 | -0.774 | 0.287 | 0.242 | 0.346 |
| 2024-2025 | log_rv1 | 464 | 0.001 | 0.098 | -0.027 | 0.023 | 0.089 | -0.029 | 0.025 | 0.094 | 0.346 |
| 2024-2025 | log_rv5 | 464 | 0.077 | 1.118 | -0.077 | 0.198 | 1.456 | -0.040 | 0.169 | 1.188 | 0.346 |
| 2024-2025 | log_rv22 | 464 | -0.156 | -0.821 | -0.421 | 0.375 | -1.008 | -0.421 | 0.235 | -1.031 | 0.346 |
| 2024-2025 | log_iv2 | 464 | 1.185 | 5.293 | 0.588 | 1.469 | 4.882 | 0.523 | 1.471 | 6.568 | 0.346 |
| 2026 | const | 177 | -0.708 | -1.234 | -2.077 | 0.265 |  |  |  | -1.823 | 0.129 |
| 2026 | log_rv1 | 177 | -0.021 | -1.507 | -0.049 | 0.005 |  |  |  | -1.561 | 0.129 |
| 2026 | log_rv5 | 177 | 0.029 | 0.409 | -0.116 | 0.166 |  |  |  | 0.482 | 0.129 |
| 2026 | log_rv22 | 177 | 0.207 | 0.671 | -0.416 | 0.800 |  |  |  | 0.904 | 0.129 |
| 2026 | log_iv2 | 177 | 0.423 | 0.857 | -0.387 | 1.569 |  |  |  | 1.011 | 0.129 |

### Fit

| period | HAR | HAR+IV | MZ | delta_r2 |
|---|---|---|---|---|
| all | 0.097 | 0.177 | 0.163 | 0.081 |
| 2018-2023 | 0.084 | 0.135 | 0.117 | 0.051 |
| 2024-2025 | 0.109 | 0.346 | 0.330 | 0.237 |
| 2026 | 0.096 | 0.129 | 0.094 | 0.033 |

### Non-overlapping samples across 21 offsets

Each sample has no shared returns between target windows, so its classical t fits these rows. The samples share many of the same periods, so they are not independent evidence.

| spec | samples | distinct_samples | median_n | median_b | min_b | max_b | median_t | share_t_above_2 |
|---|---|---|---|---|---|---|---|---|
| HAR+IV | 21 | 17 | 99.000 | 0.428 | 0.354 | 0.705 | 2.195 | 0.571 |
| MZ | 21 | 17 | 99.000 | 0.487 | 0.452 | 0.610 | 3.029 | 1.000 |

### By year: coefficient on `log_iv2`

| year | HAR+IV | MZ | n | har_iv_boot21_t |
|---|---|---|---|---|
| 2018 | -0.064 | -0.129 | 132 | -0.116 |
| 2019 | 0.810 | 0.418 | 227 | 0.925 |
| 2020 | 0.686 | 0.688 | 216 | 1.150 |
| 2021 | 0.821 | 0.586 | 181 | 3.615 |
| 2022 | -0.380 | -0.370 | 196 | -1.485 |
| 2023 | 0.075 | 0.167 | 213 | 0.365 |
| 2024 | 0.607 | 0.684 | 230 | 1.357 |
| 2025 | 1.379 | 1.132 | 234 | 5.860 |
| 2026 | 0.423 | 0.612 | 177 | 0.869 |

About 10 to 12 independent windows exist in each year, so these estimates are weak.

## Mincer-Zarnowitz in logs (reported, not the headline)

| period | n | estimate | boot21_t | boot21_low | boot21_high | boot63_t | boot63_low | boot63_high | nw_t | r2 |
|---|---|---|---|---|---|---|---|---|---|---|
| all | 1806 | 0.697 | 6.153 | 0.468 | 0.902 | 5.718 | 0.411 | 0.891 | 6.136 | 0.163 |
| 2018-2023 | 1165 | 0.623 | 4.422 | 0.308 | 0.863 | 3.751 | 0.224 | 0.875 | 4.507 | 0.117 |
| 2024-2025 | 464 | 1.081 | 5.257 | 0.530 | 1.329 | 5.565 | 0.521 | 1.269 | 7.049 | 0.330 |
| 2026 | 177 | 0.612 | 1.300 | -0.386 | 1.452 |  |  |  | 1.457 | 0.094 |

Debate targets: pooled log b near .55, and near .97 in 2024. This study has 0.697 and 0.684.

### Reconciliation with the debate numbers

The debate numbers are: log b .55 pooled, .58 and .57 without 2019-08-12, .97 in 2024, level b .79 and .22 without 2019-08-12, and implied variance above RV in 79% of observations. The plan does not record the debate rules, so this table can show only which rules come close. `no_paso` drops each origin with 2019-08-12 in its window.

| sample_end | target | tier | n | log_b | log_b_no_paso | log_b_2024 | level_b | level_b_no_paso | share_iv_above |
|---|---|---|---|---|---|---|---|---|---|
| to 2024 | rv30 total return | all tiers | 1417 | 0.581 | 0.554 | 0.684 | 0.521 | 0.475 | 0.735 |
| to 2024 | rv30 total return | Tier 1 | 878 | 0.431 | 0.374 | 0.589 | 0.552 | 0.357 | 0.682 |
| to 2024 | rv21 total return | all tiers | 1417 | 0.570 | 0.543 | 0.633 | 0.504 | 0.460 | 0.730 |
| to 2024 | rv21 total return | Tier 1 | 878 | 0.414 | 0.357 | 0.541 | 0.512 | 0.320 | 0.685 |
| to 2024 | rv30 price return | all tiers | 1417 | 0.582 | 0.555 | 0.686 | 0.521 | 0.476 | 0.735 |
| to 2024 | rv30 price return | Tier 1 | 878 | 0.431 | 0.374 | 0.592 | 0.552 | 0.358 | 0.683 |
| to 2024 | rv21 price return | all tiers | 1417 | 0.571 | 0.544 | 0.635 | 0.505 | 0.460 | 0.731 |
| to 2024 | rv21 price return | Tier 1 | 878 | 0.414 | 0.357 | 0.543 | 0.512 | 0.321 | 0.683 |
| to 2025 | rv30 total return | all tiers | 1651 | 0.650 | 0.622 | 0.684 | 0.649 | 0.596 | 0.720 |
| to 2025 | rv30 total return | Tier 1 | 1098 | 0.605 | 0.553 | 0.589 | 0.798 | 0.635 | 0.673 |
| to 2025 | rv21 total return | all tiers | 1651 | 0.633 | 0.606 | 0.633 | 0.632 | 0.580 | 0.715 |
| to 2025 | rv21 total return | Tier 1 | 1098 | 0.579 | 0.528 | 0.541 | 0.766 | 0.605 | 0.673 |
| to 2025 | rv30 price return | all tiers | 1651 | 0.651 | 0.624 | 0.686 | 0.649 | 0.596 | 0.720 |
| to 2025 | rv30 price return | Tier 1 | 1098 | 0.606 | 0.554 | 0.592 | 0.798 | 0.635 | 0.673 |
| to 2025 | rv21 price return | all tiers | 1651 | 0.634 | 0.607 | 0.635 | 0.632 | 0.580 | 0.715 |
| to 2025 | rv21 price return | Tier 1 | 1098 | 0.580 | 0.529 | 0.543 | 0.766 | 0.606 | 0.672 |
| all | rv30 total return | all tiers | 1828 | 0.673 | 0.642 | 0.684 | 0.682 | 0.608 | 0.714 |
| all | rv30 total return | Tier 1 | 1267 | 0.669 | 0.613 | 0.589 | 0.871 | 0.670 | 0.672 |
| all | rv21 total return | all tiers | 1829 | 0.656 | 0.625 | 0.633 | 0.667 | 0.595 | 0.710 |
| all | rv21 total return | Tier 1 | 1268 | 0.645 | 0.589 | 0.541 | 0.844 | 0.646 | 0.674 |
| all | rv30 price return | all tiers | 1828 | 0.674 | 0.643 | 0.686 | 0.682 | 0.609 | 0.715 |
| all | rv30 price return | Tier 1 | 1267 | 0.670 | 0.614 | 0.592 | 0.872 | 0.671 | 0.674 |
| all | rv21 price return | all tiers | 1829 | 0.658 | 0.627 | 0.635 | 0.668 | 0.595 | 0.711 |
| all | rv21 price return | Tier 1 | 1268 | 0.647 | 0.591 | 0.543 | 0.845 | 0.646 | 0.674 |

## Sensitivity runs of the coefficient on IV in the HAR regression

| group | label | n | windows | b_iv | delta_r2 | nw_t | boot21_t | boot21_low | boot21_high | boot63_t | boot63_low | boot63_high | first_stage_f |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | primary | 1806 | 99.700 | 0.622 | 0.081 | 4.126 | 4.079 | 0.337 | 0.914 | 3.803 | 0.310 | 0.940 |  |
| quote noise | Tier 1 only | 1245 | 99.700 | 0.703 | 0.102 | 3.674 | 3.731 | 0.354 | 1.068 | 3.744 | 0.356 | 1.095 |  |
| quote noise | Tier 2 only | 561 | 96.900 | 0.435 | 0.036 | 2.512 | 2.539 | 0.095 | 0.765 | 2.133 | -0.016 | 0.780 |  |
| quote noise | spread at most 0.25 | 822 | 99.700 | 0.703 | 0.068 | 2.516 | 2.461 | 0.232 | 1.331 | 2.305 | 0.223 | 1.420 |  |
| quote noise | spread at most 0.5 | 1346 | 99.700 | 0.702 | 0.084 | 3.696 | 3.582 | 0.344 | 1.111 | 3.460 | 0.327 | 1.125 |  |
| quote noise | spread above 0.5 | 460 | 97.000 | 0.420 | 0.077 | 3.512 | 3.343 | 0.182 | 0.661 | 3.129 | 0.176 | 0.687 |  |
| quote noise | spread tercile low | 603 | 99.600 | 0.753 | 0.071 | 2.120 | 2.030 | 0.176 | 1.569 | 1.926 | 0.192 | 1.692 |  |
| quote noise | spread tercile middle | 601 | 99.500 | 0.683 | 0.100 | 3.858 | 4.227 | 0.350 | 0.967 | 3.622 | 0.290 | 1.012 |  |
| quote noise | spread tercile high | 602 | 97.100 | 0.441 | 0.078 | 3.578 | 3.411 | 0.176 | 0.678 | 3.142 | 0.159 | 0.707 |  |
| flags | drop flag_ex_in_front | 1576 | 99.700 | 0.665 | 0.089 | 4.258 | 4.101 | 0.387 | 0.984 | 3.768 | 0.336 | 1.034 |  |
| flags | drop flag_front_under_7d | 1564 | 99.700 | 0.650 | 0.088 | 4.215 | 4.138 | 0.362 | 0.963 | 3.862 | 0.334 | 0.988 |  |
| flags | drop flag_rights_in_bracket | 1789 | 99.700 | 0.624 | 0.080 | 4.089 | 3.996 | 0.323 | 0.916 | 3.823 | 0.308 | 0.938 |  |
| flags | drop degraded days | 1803 | 99.700 | 0.625 | 0.082 | 4.153 | 4.025 | 0.334 | 0.917 | 3.849 | 0.311 | 0.937 |  |
| flags | drop all flags | 1323 | 99.700 | 0.708 | 0.099 | 4.340 | 4.130 | 0.418 | 1.057 | 3.897 | 0.373 | 1.097 |  |
| series | atm30_floor7 | 1564 | 99.700 | 0.650 | 0.088 | 4.215 | 4.138 | 0.362 | 0.963 | 3.862 | 0.334 | 0.988 |  |
| series | atm30_usable | 1812 | 99.700 | 0.616 | 0.079 | 4.089 | 3.929 | 0.331 | 0.919 | 3.748 | 0.309 | 0.948 |  |
| series | atm30_session_last | 1824 | 99.700 | 0.620 | 0.081 | 4.130 | 3.958 | 0.339 | 0.939 | 3.793 | 0.303 | 0.941 |  |
| target | target rv21 | 1806 | 99.700 | 0.611 | 0.078 | 4.066 | 4.031 | 0.329 | 0.899 | 3.756 | 0.298 | 0.926 |  |
| target | daily variance floor 1e-08 | 1806 | 99.700 | 0.622 | 0.081 | 4.127 | 4.080 | 0.338 | 0.914 | 3.804 | 0.310 | 0.940 |  |
| target | daily variance floor 1e-05 | 1806 | 99.700 | 0.622 | 0.081 | 4.125 | 4.078 | 0.337 | 0.914 | 3.802 | 0.310 | 0.940 |  |
| instrument | OLS on the instrument days | 1499 | 99.700 | 0.685 | 0.093 | 4.071 | 3.981 | 0.381 | 1.030 | 3.716 | 0.342 | 1.066 |  |
| instrument | instrument: IV lag 1 session | 1499 | 99.700 | 0.682 |  |  | 3.794 | 0.362 | 1.039 | 3.551 | 0.328 | 1.074 | 8556.193 |
| instrument | instrument: IV lag 5 sessions | 1499 | 99.700 | 0.513 |  |  | 3.098 | 0.195 | 0.824 | 2.877 | 0.153 | 0.838 | 2745.434 |
| stability | year-demeaned | 1806 | 99.700 | 0.644 | 0.064 | 3.677 | 3.562 | 0.309 | 1.015 | 3.149 | 0.254 | 1.037 |  |

## Leave-out estimates

Dropping an event drops each origin with that event in its 30-day window. So the event leaves both the IV and the RV.

| kind | dropped | n | mz_b | har_iv_b |
|---|---|---|---|---|
| none | none | 1806 | 0.697 | 0.622 |
| year | 2018 | 1674 | 0.742 | 0.707 |
| year | 2019 | 1579 | 0.723 | 0.542 |
| year | 2020 | 1590 | 0.613 | 0.544 |
| year | 2021 | 1625 | 0.688 | 0.638 |
| year | 2022 | 1610 | 0.694 | 0.667 |
| year | 2023 | 1593 | 0.755 | 0.685 |
| year | 2024 | 1576 | 0.703 | 0.624 |
| year | 2025 | 1572 | 0.644 | 0.553 |
| year | 2026 | 1629 | 0.677 | 0.606 |
| event | 2019 PASO | 1786 | 0.667 | 0.507 |
| event | 2019 general | 1786 | 0.713 | 0.641 |
| event | 2021 PASO | 1790 | 0.703 | 0.627 |
| event | 2021 midterm | 1789 | 0.698 | 0.623 |
| event | 2023 PASO | 1788 | 0.725 | 0.663 |
| event | 2023 general | 1786 | 0.712 | 0.651 |
| event | 2023 runoff | 1786 | 0.683 | 0.592 |
| event | 2025 PBA | 1791 | 0.719 | 0.635 |
| event | 2025 midterm | 1789 | 0.639 | 0.569 |
| event | all listed events | 1643 | 0.661 | 0.459 |

## Forecast race

The target is `rv30`, the variance level. QLIKE is primary, and MSE is secondary. A training row needs a target window that ends on or before the origin. All models in one race use identical dates.

- **Raw race:** The first origin is session 252. `ATM30`, EWMA, and GARCH have no calibration. So `ATM30` carries the variance risk premium, and EWMA and GARCH do not.
- **Calibrated race:** Each model has an expanding log regression with a smearing factor, on one common set of training days. It needs 126 training rows, so it starts later than the raw race.
- **Calibrated, no smearing:** This race is the same, without the smearing factor. The factor returns the mean level of the training target, so the 2019 windows can inflate it.
- **`all, no 2019 PASO windows`:** This period drops each scored origin with 2019-08-12 in its target window. Training rows do not change.

GARCH refits every 21 sessions. 180 fits ran across normal and t errors, and 0 failed. A failed fit keeps the prior parameters. With normal errors, the -0.82 return of 2019-08-12 sets the fit for years: `alpha` is near .9 and `beta` is near 0 just after it. So the race also has GARCH with t errors.

### Loss levels

| race | period | model | n | first | qlike | mse | mean_forecast | mean_target |
|---|---|---|---|---|---|---|---|---|
| raw | all | ATM30 raw | 1599 | 2019-05-02 | 0.4183 | 1.0686 | 0.4489 | 0.4840 |
| raw | all | EWMA raw | 1599 | 2019-05-02 | 0.7067 | 1.5949 | 0.4807 | 0.4840 |
| raw | all | GARCH raw | 1599 | 2019-05-02 | 0.8772 | 3.0079 | 1.2704 | 0.4840 |
| raw | all | GARCH t raw | 1599 | 2019-05-02 | 0.4697 | 1.1809 | 0.4463 | 0.4840 |
| raw | all | HAR | 1599 | 2019-05-02 | 0.5753 | 1.1610 | 0.6267 | 0.4840 |
| raw | all | HAR+ATM30 | 1599 | 2019-05-02 | 0.5566 | 1.2120 | 0.6246 | 0.4840 |
| raw | all, no 2019 PASO windows | ATM30 raw | 1579 | 2019-05-02 | 0.2265 | 0.1536 | 0.4484 | 0.3755 |
| raw | all, no 2019 PASO windows | EWMA raw | 1579 | 2019-05-02 | 0.3104 | 0.6337 | 0.4836 | 0.3755 |
| raw | all, no 2019 PASO windows | GARCH raw | 1579 | 2019-05-02 | 0.6641 | 2.1009 | 1.2812 | 0.3755 |
| raw | all, no 2019 PASO windows | GARCH t raw | 1579 | 2019-05-02 | 0.2499 | 0.2503 | 0.4467 | 0.3755 |
| raw | all, no 2019 PASO windows | HAR | 1579 | 2019-05-02 | 0.3574 | 0.2314 | 0.6293 | 0.3755 |
| raw | all, no 2019 PASO windows | HAR+ATM30 | 1579 | 2019-05-02 | 0.3341 | 0.2817 | 0.6272 | 0.3755 |
| raw | 2018-2023 | ATM30 raw | 958 | 2019-05-02 | 0.5791 | 1.7311 | 0.5175 | 0.5651 |
| raw | 2018-2023 | EWMA raw | 958 | 2019-05-02 | 0.9936 | 2.5562 | 0.5487 | 0.5651 |
| raw | 2018-2023 | GARCH raw | 958 | 2019-05-02 | 1.2068 | 4.8785 | 1.7048 | 0.5651 |
| raw | 2018-2023 | GARCH t raw | 958 | 2019-05-02 | 0.6286 | 1.8890 | 0.4935 | 0.5651 |
| raw | 2018-2023 | HAR | 958 | 2019-05-02 | 0.7649 | 1.8414 | 0.7045 | 0.5651 |
| raw | 2018-2023 | HAR+ATM30 | 958 | 2019-05-02 | 0.7824 | 1.9539 | 0.7528 | 0.5651 |
| raw | 2024-2025 | ATM30 raw | 464 | 2024-01-02 | 0.2032 | 0.1027 | 0.3637 | 0.4095 |
| raw | 2024-2025 | EWMA raw | 464 | 2024-01-02 | 0.3430 | 0.2143 | 0.4232 | 0.4095 |
| raw | 2024-2025 | GARCH raw | 464 | 2024-01-02 | 0.3784 | 0.2414 | 0.6308 | 0.4095 |
| raw | 2024-2025 | GARCH t raw | 464 | 2024-01-02 | 0.2620 | 0.1615 | 0.3852 | 0.4095 |
| raw | 2024-2025 | HAR | 464 | 2024-01-02 | 0.3048 | 0.1762 | 0.5291 | 0.4095 |
| raw | 2024-2025 | HAR+ATM30 | 464 | 2024-01-02 | 0.2331 | 0.1299 | 0.4503 | 0.4095 |
| raw | 2026 | ATM30 raw | 177 | 2026-01-02 | 0.1117 | 0.0150 | 0.3005 | 0.2401 |
| raw | 2026 | EWMA raw | 177 | 2026-01-02 | 0.1075 | 0.0115 | 0.2631 | 0.2401 |
| raw | 2026 | GARCH raw | 177 | 2026-01-02 | 0.4011 | 0.1360 | 0.5956 | 0.2401 |
| raw | 2026 | GARCH t raw | 177 | 2026-01-02 | 0.1539 | 0.0209 | 0.3512 | 0.2401 |
| raw | 2026 | HAR | 177 | 2026-01-02 | 0.2583 | 0.0598 | 0.4612 | 0.2401 |
| raw | 2026 | HAR+ATM30 | 177 | 2026-01-02 | 0.1826 | 0.0328 | 0.3876 | 0.2401 |
| calibrated | all | ATM30 | 1460 | 2019-12-11 | 0.3364 | 0.2890 | 0.6595 | 0.3771 |
| calibrated | all | EWMA | 1460 | 2019-12-11 | 0.3989 | 0.3025 | 0.6988 | 0.3771 |
| calibrated | all | GARCH | 1460 | 2019-12-11 | 0.4191 | 0.2845 | 0.6655 | 0.3771 |
| calibrated | all | GARCH t | 1460 | 2019-12-11 | 0.3853 | 0.3090 | 0.6831 | 0.3771 |
| calibrated | all | HAR | 1460 | 2019-12-11 | 0.4048 | 0.3141 | 0.7115 | 0.3771 |
| calibrated | all | HAR+ATM30 | 1460 | 2019-12-11 | 0.3281 | 0.2870 | 0.6461 | 0.3771 |
| calibrated | all, no 2019 PASO windows | ATM30 | 1460 | 2019-12-11 | 0.3364 | 0.2890 | 0.6595 | 0.3771 |
| calibrated | all, no 2019 PASO windows | EWMA | 1460 | 2019-12-11 | 0.3989 | 0.3025 | 0.6988 | 0.3771 |
| calibrated | all, no 2019 PASO windows | GARCH | 1460 | 2019-12-11 | 0.4191 | 0.2845 | 0.6655 | 0.3771 |
| calibrated | all, no 2019 PASO windows | GARCH t | 1460 | 2019-12-11 | 0.3853 | 0.3090 | 0.6831 | 0.3771 |
| calibrated | all, no 2019 PASO windows | HAR | 1460 | 2019-12-11 | 0.4048 | 0.3141 | 0.7115 | 0.3771 |
| calibrated | all, no 2019 PASO windows | HAR+ATM30 | 1460 | 2019-12-11 | 0.3281 | 0.2870 | 0.6461 | 0.3771 |
| calibrated | 2018-2023 | ATM30 | 819 | 2019-12-11 | 0.4404 | 0.4424 | 0.8558 | 0.3883 |
| calibrated | 2018-2023 | EWMA | 819 | 2019-12-11 | 0.4776 | 0.4251 | 0.8438 | 0.3883 |
| calibrated | 2018-2023 | GARCH | 819 | 2019-12-11 | 0.4932 | 0.3847 | 0.7952 | 0.3883 |
| calibrated | 2018-2023 | GARCH t | 819 | 2019-12-11 | 0.4718 | 0.4454 | 0.8575 | 0.3883 |
| calibrated | 2018-2023 | HAR | 819 | 2019-12-11 | 0.4883 | 0.4445 | 0.8628 | 0.3883 |
| calibrated | 2018-2023 | HAR+ATM30 | 819 | 2019-12-11 | 0.4251 | 0.4362 | 0.8336 | 0.3883 |
| calibrated | 2024-2025 | ATM30 | 464 | 2024-01-02 | 0.2175 | 0.1179 | 0.4232 | 0.4095 |
| calibrated | 2024-2025 | EWMA | 464 | 2024-01-02 | 0.3150 | 0.1804 | 0.5354 | 0.4095 |
| calibrated | 2024-2025 | GARCH | 464 | 2024-01-02 | 0.3375 | 0.1901 | 0.5046 | 0.4095 |
| calibrated | 2024-2025 | GARCH t | 464 | 2024-01-02 | 0.2906 | 0.1689 | 0.4706 | 0.4095 |
| calibrated | 2024-2025 | HAR | 464 | 2024-01-02 | 0.3116 | 0.1802 | 0.5382 | 0.4095 |
| calibrated | 2024-2025 | HAR+ATM30 | 464 | 2024-01-02 | 0.2185 | 0.1225 | 0.4203 | 0.4095 |
| calibrated | 2026 | ATM30 | 177 | 2026-01-02 | 0.1670 | 0.0276 | 0.3707 | 0.2401 |
| calibrated | 2026 | EWMA | 177 | 2026-01-02 | 0.2548 | 0.0552 | 0.4569 | 0.2401 |
| calibrated | 2026 | GARCH | 177 | 2026-01-02 | 0.2905 | 0.0686 | 0.4869 | 0.2401 |
| calibrated | 2026 | GARCH t | 177 | 2026-01-02 | 0.2330 | 0.0452 | 0.4328 | 0.2401 |
| calibrated | 2026 | HAR | 177 | 2026-01-02 | 0.2624 | 0.0614 | 0.4655 | 0.2401 |
| calibrated | 2026 | HAR+ATM30 | 177 | 2026-01-02 | 0.1663 | 0.0282 | 0.3702 | 0.2401 |
| calibrated, no smearing | all | ATM30 | 1460 | 2019-12-11 | 0.2368 | 0.1559 | 0.3227 | 0.3771 |
| calibrated, no smearing | all | EWMA | 1460 | 2019-12-11 | 0.2610 | 0.1715 | 0.3450 | 0.3771 |
| calibrated, no smearing | all | GARCH | 1460 | 2019-12-11 | 0.3146 | 0.1851 | 0.3454 | 0.3771 |
| calibrated, no smearing | all | GARCH t | 1460 | 2019-12-11 | 0.2720 | 0.1722 | 0.3278 | 0.3771 |
| calibrated, no smearing | all | HAR | 1460 | 2019-12-11 | 0.2587 | 0.1691 | 0.3551 | 0.3771 |
| calibrated, no smearing | all | HAR+ATM30 | 1460 | 2019-12-11 | 0.2368 | 0.1548 | 0.3381 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | ATM30 | 1460 | 2019-12-11 | 0.2368 | 0.1559 | 0.3227 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | EWMA | 1460 | 2019-12-11 | 0.2610 | 0.1715 | 0.3450 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | GARCH | 1460 | 2019-12-11 | 0.3146 | 0.1851 | 0.3454 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | GARCH t | 1460 | 2019-12-11 | 0.2720 | 0.1722 | 0.3278 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | HAR | 1460 | 2019-12-11 | 0.2587 | 0.1691 | 0.3551 | 0.3771 |
| calibrated, no smearing | all, no 2019 PASO windows | HAR+ATM30 | 1460 | 2019-12-11 | 0.2368 | 0.1548 | 0.3381 | 0.3771 |
| calibrated, no smearing | 2018-2023 | ATM30 | 819 | 2019-12-11 | 0.2334 | 0.1889 | 0.3759 | 0.3883 |
| calibrated, no smearing | 2018-2023 | EWMA | 819 | 2019-12-11 | 0.2668 | 0.2057 | 0.3783 | 0.3883 |
| calibrated, no smearing | 2018-2023 | GARCH | 819 | 2019-12-11 | 0.3190 | 0.2197 | 0.3888 | 0.3883 |
| calibrated, no smearing | 2018-2023 | GARCH t | 819 | 2019-12-11 | 0.2666 | 0.2020 | 0.3680 | 0.3883 |
| calibrated, no smearing | 2018-2023 | HAR | 819 | 2019-12-11 | 0.2661 | 0.2019 | 0.3951 | 0.3883 |
| calibrated, no smearing | 2018-2023 | HAR+ATM30 | 819 | 2019-12-11 | 0.2325 | 0.1857 | 0.4025 | 0.3883 |
| calibrated, no smearing | 2024-2025 | ATM30 | 464 | 2024-01-02 | 0.2985 | 0.1536 | 0.2600 | 0.4095 |
| calibrated, no smearing | 2024-2025 | EWMA | 464 | 2024-01-02 | 0.3131 | 0.1730 | 0.3117 | 0.4095 |
| calibrated, no smearing | 2024-2025 | GARCH | 464 | 2024-01-02 | 0.3854 | 0.1904 | 0.2892 | 0.4095 |
| calibrated, no smearing | 2024-2025 | GARCH t | 464 | 2024-01-02 | 0.3486 | 0.1818 | 0.2793 | 0.4095 |
| calibrated, no smearing | 2024-2025 | HAR | 464 | 2024-01-02 | 0.3049 | 0.1717 | 0.3121 | 0.4095 |
| calibrated, no smearing | 2024-2025 | HAR+ATM30 | 464 | 2024-01-02 | 0.2994 | 0.1558 | 0.2610 | 0.4095 |
| calibrated, no smearing | 2026 | ATM30 | 177 | 2026-01-02 | 0.0911 | 0.0089 | 0.2410 | 0.2401 |
| calibrated, no smearing | 2026 | EWMA | 177 | 2026-01-02 | 0.0977 | 0.0095 | 0.2785 | 0.2401 |
| calibrated, no smearing | 2026 | GARCH | 177 | 2026-01-02 | 0.1091 | 0.0110 | 0.2920 | 0.2401 |
| calibrated, no smearing | 2026 | GARCH t | 177 | 2026-01-02 | 0.0965 | 0.0091 | 0.2688 | 0.2401 |
| calibrated, no smearing | 2026 | HAR | 177 | 2026-01-02 | 0.1028 | 0.0106 | 0.2832 | 0.2401 |
| calibrated, no smearing | 2026 | HAR+ATM30 | 177 | 2026-01-02 | 0.0925 | 0.0092 | 0.2421 | 0.2401 |

### Loss differences

A negative value means that `model` has the lower loss.

| race | period | metric | model | against | n | mean_difference | boot21_t | boot21_low | boot21_high | boot63_t | boot63_low | boot63_high |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| raw | all | qlike | EWMA raw | ATM30 raw | 1599 | 0.2884 | 1.6571 | 0.0367 | 0.6943 | 1.4261 | 0.0142 | 0.7429 |
| raw | all | mse | EWMA raw | ATM30 raw | 1599 | 0.5264 | 1.5690 | 0.0399 | 1.2640 | 1.2214 | 0.0146 | 1.5492 |
| raw | all | qlike | GARCH raw | ATM30 raw | 1599 | 0.4590 | 6.6011 | 0.3187 | 0.5897 | 5.1256 | 0.2877 | 0.6331 |
| raw | all | mse | GARCH raw | ATM30 raw | 1599 | 1.9393 | 4.4263 | 1.1415 | 2.8724 | 2.7664 | 0.7729 | 3.4538 |
| raw | all | qlike | GARCH t raw | ATM30 raw | 1599 | 0.0514 | 1.3239 | -0.0104 | 0.1341 | 1.4343 | -0.0082 | 0.1303 |
| raw | all | mse | GARCH t raw | ATM30 raw | 1599 | 0.1123 | 1.0865 | -0.0145 | 0.3415 | 1.0815 | -0.0182 | 0.3485 |
| raw | all | qlike | HAR | ATM30 raw | 1599 | 0.1570 | 3.3755 | 0.0639 | 0.2475 | 3.2804 | 0.0567 | 0.2457 |
| raw | all | mse | HAR | ATM30 raw | 1599 | 0.0924 | 2.8472 | 0.0257 | 0.1539 | 2.5366 | 0.0119 | 0.1553 |
| raw | all | qlike | HAR+ATM30 | ATM30 raw | 1599 | 0.1383 | 2.9693 | 0.0440 | 0.2329 | 2.5337 | 0.0302 | 0.2470 |
| raw | all | mse | HAR+ATM30 | ATM30 raw | 1599 | 0.1434 | 2.4092 | 0.0408 | 0.2737 | 1.8218 | 0.0120 | 0.3175 |
| raw | all | qlike | HAR+ATM30 | HAR | 1599 | -0.0187 | -1.2771 | -0.0444 | 0.0115 | -0.9110 | -0.0539 | 0.0257 |
| raw | all | mse | HAR+ATM30 | HAR | 1599 | 0.0510 | 1.0300 | -0.0203 | 0.1665 | 0.8223 | -0.0280 | 0.1945 |
| raw | all, no 2019 PASO windows | qlike | EWMA raw | ATM30 raw | 1579 | 0.0839 | 2.0438 | 0.0102 | 0.1722 | 1.8285 | -0.0012 | 0.1794 |
| raw | all, no 2019 PASO windows | mse | EWMA raw | ATM30 raw | 1579 | 0.4802 | 1.4840 | 0.0306 | 1.2064 | 1.1948 | 0.0102 | 1.4345 |
| raw | all, no 2019 PASO windows | qlike | GARCH raw | ATM30 raw | 1579 | 0.4376 | 6.8774 | 0.3026 | 0.5572 | 5.2372 | 0.2709 | 0.6009 |
| raw | all, no 2019 PASO windows | mse | GARCH raw | ATM30 raw | 1579 | 1.9474 | 4.3895 | 1.1464 | 2.8752 | 2.7231 | 0.7566 | 3.5063 |
| raw | all, no 2019 PASO windows | qlike | GARCH t raw | ATM30 raw | 1579 | 0.0234 | 1.2363 | -0.0143 | 0.0611 | 1.1724 | -0.0142 | 0.0650 |
| raw | all, no 2019 PASO windows | mse | GARCH t raw | ATM30 raw | 1579 | 0.0967 | 1.0653 | -0.0159 | 0.3017 | 1.0644 | -0.0184 | 0.3005 |
| raw | all, no 2019 PASO windows | qlike | HAR | ATM30 raw | 1579 | 0.1310 | 3.4771 | 0.0491 | 0.1972 | 3.1545 | 0.0397 | 0.2049 |
| raw | all, no 2019 PASO windows | mse | HAR | ATM30 raw | 1579 | 0.0779 | 2.6571 | 0.0167 | 0.1303 | 2.2256 | -0.0029 | 0.1384 |
| raw | all, no 2019 PASO windows | qlike | HAR+ATM30 | ATM30 raw | 1579 | 0.1076 | 3.0818 | 0.0298 | 0.1673 | 2.5781 | 0.0168 | 0.1830 |
| raw | all, no 2019 PASO windows | mse | HAR+ATM30 | ATM30 raw | 1579 | 0.1282 | 2.1877 | 0.0251 | 0.2583 | 1.6994 | 0.0046 | 0.2956 |
| raw | all, no 2019 PASO windows | qlike | HAR+ATM30 | HAR | 1579 | -0.0234 | -1.6419 | -0.0488 | 0.0051 | -1.2366 | -0.0565 | 0.0180 |
| raw | all, no 2019 PASO windows | mse | HAR+ATM30 | HAR | 1579 | 0.0503 | 0.9996 | -0.0210 | 0.1659 | 0.7969 | -0.0297 | 0.1967 |
| raw | 2018-2023 | qlike | EWMA raw | ATM30 raw | 958 | 0.4145 | 1.3899 | 0.0029 | 1.1336 |  |  |  |
| raw | 2018-2023 | mse | EWMA raw | ATM30 raw | 958 | 0.8251 | 1.5531 | 0.0352 | 1.9872 |  |  |  |
| raw | 2018-2023 | qlike | GARCH raw | ATM30 raw | 958 | 0.6277 | 5.9698 | 0.4174 | 0.8327 |  |  |  |
| raw | 2018-2023 | mse | GARCH raw | ATM30 raw | 958 | 3.1474 | 4.7440 | 1.9333 | 4.4846 |  |  |  |
| raw | 2018-2023 | qlike | GARCH t raw | ATM30 raw | 958 | 0.0495 | 0.8077 | -0.0396 | 0.1930 |  |  |  |
| raw | 2018-2023 | mse | GARCH t raw | ATM30 raw | 958 | 0.1579 | 0.9415 | -0.0418 | 0.5364 |  |  |  |
| raw | 2018-2023 | qlike | HAR | ATM30 raw | 958 | 0.1858 | 2.5941 | 0.0454 | 0.3358 |  |  |  |
| raw | 2018-2023 | mse | HAR | ATM30 raw | 958 | 0.1103 | 2.1316 | 0.0016 | 0.2134 |  |  |  |
| raw | 2018-2023 | qlike | HAR+ATM30 | ATM30 raw | 958 | 0.2033 | 2.7492 | 0.0608 | 0.3626 |  |  |  |
| raw | 2018-2023 | mse | HAR+ATM30 | ATM30 raw | 958 | 0.2229 | 2.2711 | 0.0496 | 0.4319 |  |  |  |
| raw | 2018-2023 | qlike | HAR+ATM30 | HAR | 958 | 0.0175 | 0.9006 | -0.0190 | 0.0569 |  |  |  |
| raw | 2018-2023 | mse | HAR+ATM30 | HAR | 958 | 0.1126 | 1.3916 | -0.0039 | 0.2930 |  |  |  |
| raw | 2024-2025 | qlike | EWMA raw | ATM30 raw | 464 | 0.1398 | 2.4682 | 0.0351 | 0.2593 |  |  |  |
| raw | 2024-2025 | mse | EWMA raw | ATM30 raw | 464 | 0.1116 | 1.4868 | 0.0045 | 0.2852 |  |  |  |
| raw | 2024-2025 | qlike | GARCH raw | ATM30 raw | 464 | 0.1752 | 2.4862 | 0.0295 | 0.2994 |  |  |  |
| raw | 2024-2025 | mse | GARCH raw | ATM30 raw | 464 | 0.1387 | 2.9648 | 0.0606 | 0.2435 |  |  |  |
| raw | 2024-2025 | qlike | GARCH t raw | ATM30 raw | 464 | 0.0588 | 1.2473 | -0.0227 | 0.1677 |  |  |  |
| raw | 2024-2025 | mse | GARCH t raw | ATM30 raw | 464 | 0.0588 | 1.2869 | -0.0032 | 0.1677 |  |  |  |
| raw | 2024-2025 | qlike | HAR | ATM30 raw | 464 | 0.1016 | 1.8187 | -0.0144 | 0.2018 |  |  |  |
| raw | 2024-2025 | mse | HAR | ATM30 raw | 464 | 0.0736 | 2.1351 | 0.0140 | 0.1511 |  |  |  |
| raw | 2024-2025 | qlike | HAR+ATM30 | ATM30 raw | 464 | 0.0300 | 0.8451 | -0.0445 | 0.0911 |  |  |  |
| raw | 2024-2025 | mse | HAR+ATM30 | ATM30 raw | 464 | 0.0272 | 1.5702 | -0.0025 | 0.0663 |  |  |  |
| raw | 2024-2025 | qlike | HAR+ATM30 | HAR | 464 | -0.0716 | -3.1833 | -0.1142 | -0.0270 |  |  |  |
| raw | 2024-2025 | mse | HAR+ATM30 | HAR | 464 | -0.0464 | -2.5490 | -0.0870 | -0.0146 |  |  |  |
| raw | 2026 | qlike | EWMA raw | ATM30 raw | 177 | -0.0042 | -0.2159 | -0.0438 | 0.0326 |  |  |  |
| raw | 2026 | mse | EWMA raw | ATM30 raw | 177 | -0.0036 | -0.9235 | -0.0119 | 0.0029 |  |  |  |
| raw | 2026 | qlike | GARCH raw | ATM30 raw | 177 | 0.2894 | 5.1393 | 0.1873 | 0.4079 |  |  |  |
| raw | 2026 | mse | GARCH raw | ATM30 raw | 177 | 0.1210 | 8.5295 | 0.0934 | 0.1491 |  |  |  |
| raw | 2026 | qlike | GARCH t raw | ATM30 raw | 177 | 0.0421 | 1.5034 | -0.0067 | 0.1016 |  |  |  |
| raw | 2026 | mse | GARCH t raw | ATM30 raw | 177 | 0.0058 | 1.1541 | -0.0036 | 0.0160 |  |  |  |
| raw | 2026 | qlike | HAR | ATM30 raw | 177 | 0.1465 | 4.2002 | 0.0851 | 0.2188 |  |  |  |
| raw | 2026 | mse | HAR | ATM30 raw | 177 | 0.0447 | 6.0747 | 0.0311 | 0.0597 |  |  |  |
| raw | 2026 | qlike | HAR+ATM30 | ATM30 raw | 177 | 0.0709 | 3.2863 | 0.0312 | 0.1133 |  |  |  |
| raw | 2026 | mse | HAR+ATM30 | ATM30 raw | 177 | 0.0178 | 4.4092 | 0.0098 | 0.0253 |  |  |  |
| raw | 2026 | qlike | HAR+ATM30 | HAR | 177 | -0.0757 | -4.7649 | -0.1076 | -0.0473 |  |  |  |
| raw | 2026 | mse | HAR+ATM30 | HAR | 177 | -0.0270 | -5.4818 | -0.0366 | -0.0178 |  |  |  |
| calibrated | all | qlike | EWMA | ATM30 | 1460 | 0.0625 | 4.1704 | 0.0330 | 0.0920 | 3.4330 | 0.0264 | 0.0992 |
| calibrated | all | mse | EWMA | ATM30 | 1460 | 0.0135 | 0.5987 | -0.0337 | 0.0566 | 0.4162 | -0.0604 | 0.0687 |
| calibrated | all | qlike | GARCH | ATM30 | 1460 | 0.0827 | 3.6746 | 0.0408 | 0.1304 | 3.4216 | 0.0349 | 0.1317 |
| calibrated | all | mse | GARCH | ATM30 | 1460 | -0.0045 | -0.1174 | -0.0786 | 0.0725 | -0.1074 | -0.0933 | 0.0698 |
| calibrated | all | qlike | GARCH t | ATM30 | 1460 | 0.0489 | 3.2089 | 0.0204 | 0.0793 | 2.6515 | 0.0143 | 0.0872 |
| calibrated | all | mse | GARCH t | ATM30 | 1460 | 0.0201 | 1.1241 | -0.0138 | 0.0559 | 0.8255 | -0.0301 | 0.0686 |
| calibrated | all | qlike | HAR | ATM30 | 1460 | 0.0684 | 4.4998 | 0.0385 | 0.0969 | 3.9576 | 0.0342 | 0.1024 |
| calibrated | all | mse | HAR | ATM30 | 1460 | 0.0251 | 1.2621 | -0.0149 | 0.0620 | 0.9578 | -0.0329 | 0.0704 |
| calibrated | all | qlike | HAR+ATM30 | ATM30 | 1460 | -0.0083 | -1.5892 | -0.0191 | 0.0015 | -2.0511 | -0.0166 | -0.0002 |
| calibrated | all | mse | HAR+ATM30 | ATM30 | 1460 | -0.0019 | -0.1266 | -0.0320 | 0.0277 | -0.1488 | -0.0281 | 0.0243 |
| calibrated | all | qlike | HAR+ATM30 | HAR | 1460 | -0.0767 | -4.9520 | -0.1058 | -0.0464 | -4.2980 | -0.1117 | -0.0422 |
| calibrated | all | mse | HAR+ATM30 | HAR | 1460 | -0.0270 | -1.2245 | -0.0690 | 0.0172 | -0.9530 | -0.0770 | 0.0362 |
| calibrated | all, no 2019 PASO windows | qlike | EWMA | ATM30 | 1460 | 0.0625 | 4.1704 | 0.0330 | 0.0920 | 3.4330 | 0.0264 | 0.0992 |
| calibrated | all, no 2019 PASO windows | mse | EWMA | ATM30 | 1460 | 0.0135 | 0.5987 | -0.0337 | 0.0566 | 0.4162 | -0.0604 | 0.0687 |
| calibrated | all, no 2019 PASO windows | qlike | GARCH | ATM30 | 1460 | 0.0827 | 3.6746 | 0.0408 | 0.1304 | 3.4216 | 0.0349 | 0.1317 |
| calibrated | all, no 2019 PASO windows | mse | GARCH | ATM30 | 1460 | -0.0045 | -0.1174 | -0.0786 | 0.0725 | -0.1074 | -0.0933 | 0.0698 |
| calibrated | all, no 2019 PASO windows | qlike | GARCH t | ATM30 | 1460 | 0.0489 | 3.2089 | 0.0204 | 0.0793 | 2.6515 | 0.0143 | 0.0872 |
| calibrated | all, no 2019 PASO windows | mse | GARCH t | ATM30 | 1460 | 0.0201 | 1.1241 | -0.0138 | 0.0559 | 0.8255 | -0.0301 | 0.0686 |
| calibrated | all, no 2019 PASO windows | qlike | HAR | ATM30 | 1460 | 0.0684 | 4.4998 | 0.0385 | 0.0969 | 3.9576 | 0.0342 | 0.1024 |
| calibrated | all, no 2019 PASO windows | mse | HAR | ATM30 | 1460 | 0.0251 | 1.2621 | -0.0149 | 0.0620 | 0.9578 | -0.0329 | 0.0704 |
| calibrated | all, no 2019 PASO windows | qlike | HAR+ATM30 | ATM30 | 1460 | -0.0083 | -1.5892 | -0.0191 | 0.0015 | -2.0511 | -0.0166 | -0.0002 |
| calibrated | all, no 2019 PASO windows | mse | HAR+ATM30 | ATM30 | 1460 | -0.0019 | -0.1266 | -0.0320 | 0.0277 | -0.1488 | -0.0281 | 0.0243 |
| calibrated | all, no 2019 PASO windows | qlike | HAR+ATM30 | HAR | 1460 | -0.0767 | -4.9520 | -0.1058 | -0.0464 | -4.2980 | -0.1117 | -0.0422 |
| calibrated | all, no 2019 PASO windows | mse | HAR+ATM30 | HAR | 1460 | -0.0270 | -1.2245 | -0.0690 | 0.0172 | -0.9530 | -0.0770 | 0.0362 |
| calibrated | 2018-2023 | qlike | EWMA | ATM30 | 819 | 0.0372 | 2.1233 | 0.0035 | 0.0718 |  |  |  |
| calibrated | 2018-2023 | mse | EWMA | ATM30 | 819 | -0.0173 | -0.4789 | -0.0929 | 0.0514 |  |  |  |
| calibrated | 2018-2023 | qlike | GARCH | ATM30 | 819 | 0.0528 | 1.7764 | -0.0044 | 0.1126 |  |  |  |
| calibrated | 2018-2023 | mse | GARCH | ATM30 | 819 | -0.0577 | -0.9185 | -0.1832 | 0.0687 |  |  |  |
| calibrated | 2018-2023 | qlike | GARCH t | ATM30 | 819 | 0.0315 | 1.7163 | -0.0040 | 0.0691 |  |  |  |
| calibrated | 2018-2023 | mse | GARCH t | ATM30 | 819 | 0.0030 | 0.1182 | -0.0479 | 0.0529 |  |  |  |
| calibrated | 2018-2023 | qlike | HAR | ATM30 | 819 | 0.0479 | 2.6464 | 0.0130 | 0.0847 |  |  |  |
| calibrated | 2018-2023 | mse | HAR | ATM30 | 819 | 0.0021 | 0.0676 | -0.0603 | 0.0606 |  |  |  |
| calibrated | 2018-2023 | qlike | HAR+ATM30 | ATM30 | 819 | -0.0153 | -1.7368 | -0.0327 | 0.0011 |  |  |  |
| calibrated | 2018-2023 | mse | HAR+ATM30 | ATM30 | 819 | -0.0062 | -0.2327 | -0.0617 | 0.0445 |  |  |  |
| calibrated | 2018-2023 | qlike | HAR+ATM30 | HAR | 819 | -0.0632 | -3.2427 | -0.1019 | -0.0268 |  |  |  |
| calibrated | 2018-2023 | mse | HAR+ATM30 | HAR | 819 | -0.0083 | -0.2277 | -0.0778 | 0.0629 |  |  |  |
| calibrated | 2024-2025 | qlike | EWMA | ATM30 | 464 | 0.0975 | 3.1097 | 0.0345 | 0.1574 |  |  |  |
| calibrated | 2024-2025 | mse | EWMA | ATM30 | 464 | 0.0625 | 2.6942 | 0.0219 | 0.1111 |  |  |  |
| calibrated | 2024-2025 | qlike | GARCH | ATM30 | 464 | 0.1199 | 2.7226 | 0.0428 | 0.2189 |  |  |  |
| calibrated | 2024-2025 | mse | GARCH | ATM30 | 464 | 0.0722 | 2.0390 | 0.0228 | 0.1579 |  |  |  |
| calibrated | 2024-2025 | qlike | GARCH t | ATM30 | 464 | 0.0730 | 2.2108 | 0.0177 | 0.1464 |  |  |  |
| calibrated | 2024-2025 | mse | GARCH t | ATM30 | 464 | 0.0510 | 1.6403 | 0.0071 | 0.1260 |  |  |  |
| calibrated | 2024-2025 | qlike | HAR | ATM30 | 464 | 0.0941 | 2.9357 | 0.0291 | 0.1527 |  |  |  |
| calibrated | 2024-2025 | mse | HAR | ATM30 | 464 | 0.0623 | 2.5555 | 0.0198 | 0.1169 |  |  |  |
| calibrated | 2024-2025 | qlike | HAR+ATM30 | ATM30 | 464 | 0.0010 | 0.2237 | -0.0078 | 0.0106 |  |  |  |
| calibrated | 2024-2025 | mse | HAR+ATM30 | ATM30 | 464 | 0.0046 | 1.0884 | -0.0015 | 0.0145 |  |  |  |
| calibrated | 2024-2025 | qlike | HAR+ATM30 | HAR | 464 | -0.0931 | -2.9384 | -0.1504 | -0.0295 |  |  |  |
| calibrated | 2024-2025 | mse | HAR+ATM30 | HAR | 464 | -0.0577 | -2.6452 | -0.1054 | -0.0175 |  |  |  |
| calibrated | 2026 | qlike | EWMA | ATM30 | 177 | 0.0879 | 4.2796 | 0.0504 | 0.1297 |  |  |  |
| calibrated | 2026 | mse | EWMA | ATM30 | 177 | 0.0276 | 4.8897 | 0.0173 | 0.0388 |  |  |  |
| calibrated | 2026 | qlike | GARCH | ATM30 | 177 | 0.1235 | 3.7501 | 0.0641 | 0.1949 |  |  |  |
| calibrated | 2026 | mse | GARCH | ATM30 | 177 | 0.0410 | 4.3198 | 0.0238 | 0.0608 |  |  |  |
| calibrated | 2026 | qlike | GARCH t | ATM30 | 177 | 0.0661 | 2.8540 | 0.0244 | 0.1156 |  |  |  |
| calibrated | 2026 | mse | GARCH t | ATM30 | 177 | 0.0175 | 2.8346 | 0.0057 | 0.0299 |  |  |  |
| calibrated | 2026 | qlike | HAR | ATM30 | 177 | 0.0954 | 5.2720 | 0.0626 | 0.1318 |  |  |  |
| calibrated | 2026 | mse | HAR | ATM30 | 177 | 0.0338 | 5.9850 | 0.0234 | 0.0448 |  |  |  |
| calibrated | 2026 | qlike | HAR+ATM30 | ATM30 | 177 | -0.0006 | -0.1698 | -0.0083 | 0.0064 |  |  |  |
| calibrated | 2026 | mse | HAR+ATM30 | ATM30 | 177 | 0.0006 | 0.5759 | -0.0013 | 0.0027 |  |  |  |
| calibrated | 2026 | qlike | HAR+ATM30 | HAR | 177 | -0.0961 | -4.9562 | -0.1353 | -0.0616 |  |  |  |
| calibrated | 2026 | mse | HAR+ATM30 | HAR | 177 | -0.0332 | -5.9730 | -0.0441 | -0.0230 |  |  |  |
| calibrated, no smearing | all | qlike | EWMA | ATM30 | 1460 | 0.0242 | 1.3117 | -0.0109 | 0.0612 | 1.2968 | -0.0101 | 0.0620 |
| calibrated, no smearing | all | mse | EWMA | ATM30 | 1460 | 0.0157 | 2.0933 | 0.0018 | 0.0318 | 1.9631 | 0.0023 | 0.0334 |
| calibrated, no smearing | all | qlike | GARCH | ATM30 | 1460 | 0.0778 | 2.2367 | 0.0221 | 0.1538 | 2.0235 | 0.0140 | 0.1642 |
| calibrated, no smearing | all | mse | GARCH | ATM30 | 1460 | 0.0292 | 2.5048 | 0.0100 | 0.0547 | 2.0803 | 0.0062 | 0.0609 |
| calibrated, no smearing | all | qlike | GARCH t | ATM30 | 1460 | 0.0352 | 1.6111 | -0.0001 | 0.0845 | 1.5757 | -0.0013 | 0.0853 |
| calibrated, no smearing | all | mse | GARCH t | ATM30 | 1460 | 0.0164 | 1.9606 | 0.0037 | 0.0356 | 1.7623 | 0.0024 | 0.0372 |
| calibrated, no smearing | all | qlike | HAR | ATM30 | 1460 | 0.0218 | 1.0297 | -0.0188 | 0.0657 | 1.1397 | -0.0142 | 0.0601 |
| calibrated, no smearing | all | mse | HAR | ATM30 | 1460 | 0.0132 | 1.6297 | -0.0021 | 0.0306 | 1.7444 | 0.0003 | 0.0303 |
| calibrated, no smearing | all | qlike | HAR+ATM30 | ATM30 | 1460 | -0.0000 | -0.0031 | -0.0245 | 0.0165 | -0.0036 | -0.0208 | 0.0146 |
| calibrated, no smearing | all | mse | HAR+ATM30 | ATM30 | 1460 | -0.0011 | -0.1417 | -0.0182 | 0.0102 | -0.1433 | -0.0183 | 0.0108 |
| calibrated, no smearing | all | qlike | HAR+ATM30 | HAR | 1460 | -0.0219 | -1.1863 | -0.0594 | 0.0122 | -1.1337 | -0.0608 | 0.0140 |
| calibrated, no smearing | all | mse | HAR+ATM30 | HAR | 1460 | -0.0143 | -1.8179 | -0.0318 | -0.0008 | -1.5976 | -0.0341 | 0.0006 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | EWMA | ATM30 | 1460 | 0.0242 | 1.3117 | -0.0109 | 0.0612 | 1.2968 | -0.0101 | 0.0620 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | EWMA | ATM30 | 1460 | 0.0157 | 2.0933 | 0.0018 | 0.0318 | 1.9631 | 0.0023 | 0.0334 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | GARCH | ATM30 | 1460 | 0.0778 | 2.2367 | 0.0221 | 0.1538 | 2.0235 | 0.0140 | 0.1642 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | GARCH | ATM30 | 1460 | 0.0292 | 2.5048 | 0.0100 | 0.0547 | 2.0803 | 0.0062 | 0.0609 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | GARCH t | ATM30 | 1460 | 0.0352 | 1.6111 | -0.0001 | 0.0845 | 1.5757 | -0.0013 | 0.0853 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | GARCH t | ATM30 | 1460 | 0.0164 | 1.9606 | 0.0037 | 0.0356 | 1.7623 | 0.0024 | 0.0372 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | HAR | ATM30 | 1460 | 0.0218 | 1.0297 | -0.0188 | 0.0657 | 1.1397 | -0.0142 | 0.0601 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | HAR | ATM30 | 1460 | 0.0132 | 1.6297 | -0.0021 | 0.0306 | 1.7444 | 0.0003 | 0.0303 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | HAR+ATM30 | ATM30 | 1460 | -0.0000 | -0.0031 | -0.0245 | 0.0165 | -0.0036 | -0.0208 | 0.0146 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | HAR+ATM30 | ATM30 | 1460 | -0.0011 | -0.1417 | -0.0182 | 0.0102 | -0.1433 | -0.0183 | 0.0108 |
| calibrated, no smearing | all, no 2019 PASO windows | qlike | HAR+ATM30 | HAR | 1460 | -0.0219 | -1.1863 | -0.0594 | 0.0122 | -1.1337 | -0.0608 | 0.0140 |
| calibrated, no smearing | all, no 2019 PASO windows | mse | HAR+ATM30 | HAR | 1460 | -0.0143 | -1.8179 | -0.0318 | -0.0008 | -1.5976 | -0.0341 | 0.0006 |
| calibrated, no smearing | 2018-2023 | qlike | EWMA | ATM30 | 819 | 0.0334 | 1.4463 | -0.0131 | 0.0775 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | EWMA | ATM30 | 819 | 0.0168 | 1.8356 | -0.0014 | 0.0350 |  |  |  |
| calibrated, no smearing | 2018-2023 | qlike | GARCH | ATM30 | 819 | 0.0856 | 2.6737 | 0.0302 | 0.1565 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | GARCH | ATM30 | 819 | 0.0308 | 2.7538 | 0.0117 | 0.0551 |  |  |  |
| calibrated, no smearing | 2018-2023 | qlike | GARCH t | ATM30 | 819 | 0.0333 | 1.9178 | 0.0008 | 0.0685 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | GARCH t | ATM30 | 819 | 0.0131 | 2.5582 | 0.0032 | 0.0236 |  |  |  |
| calibrated, no smearing | 2018-2023 | qlike | HAR | ATM30 | 819 | 0.0328 | 1.2529 | -0.0188 | 0.0822 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | HAR | ATM30 | 819 | 0.0130 | 1.3076 | -0.0075 | 0.0313 |  |  |  |
| calibrated, no smearing | 2018-2023 | qlike | HAR+ATM30 | ATM30 | 819 | -0.0009 | -0.0474 | -0.0447 | 0.0272 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | HAR+ATM30 | ATM30 | 819 | -0.0032 | -0.2418 | -0.0345 | 0.0164 |  |  |  |
| calibrated, no smearing | 2018-2023 | qlike | HAR+ATM30 | HAR | 819 | -0.0337 | -1.5959 | -0.0749 | 0.0060 |  |  |  |
| calibrated, no smearing | 2018-2023 | mse | HAR+ATM30 | HAR | 819 | -0.0162 | -1.5943 | -0.0374 | 0.0010 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | EWMA | ATM30 | 464 | 0.0146 | 0.3444 | -0.0623 | 0.1034 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | EWMA | ATM30 | 464 | 0.0194 | 1.1076 | -0.0065 | 0.0615 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | GARCH | ATM30 | 464 | 0.0869 | 0.9074 | -0.0538 | 0.3128 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | GARCH | ATM30 | 464 | 0.0369 | 1.1589 | -0.0043 | 0.1136 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | GARCH t | ATM30 | 464 | 0.0501 | 0.7834 | -0.0458 | 0.2032 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | GARCH t | ATM30 | 464 | 0.0283 | 1.1069 | -0.0051 | 0.0899 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | HAR | ATM30 | 464 | 0.0064 | 0.1276 | -0.0843 | 0.1130 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | HAR | ATM30 | 464 | 0.0181 | 0.9246 | -0.0104 | 0.0644 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | HAR+ATM30 | ATM30 | 464 | 0.0009 | 0.1431 | -0.0113 | 0.0148 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | HAR+ATM30 | ATM30 | 464 | 0.0022 | 0.9035 | -0.0013 | 0.0081 |  |  |  |
| calibrated, no smearing | 2024-2025 | qlike | HAR+ATM30 | HAR | 464 | -0.0055 | -0.1194 | -0.1043 | 0.0762 |  |  |  |
| calibrated, no smearing | 2024-2025 | mse | HAR+ATM30 | HAR | 464 | -0.0159 | -0.9067 | -0.0580 | 0.0096 |  |  |  |
| calibrated, no smearing | 2026 | qlike | EWMA | ATM30 | 177 | 0.0065 | 0.3136 | -0.0316 | 0.0482 |  |  |  |
| calibrated, no smearing | 2026 | mse | EWMA | ATM30 | 177 | 0.0006 | 0.2604 | -0.0037 | 0.0054 |  |  |  |
| calibrated, no smearing | 2026 | qlike | GARCH | ATM30 | 177 | 0.0179 | 0.5945 | -0.0363 | 0.0832 |  |  |  |
| calibrated, no smearing | 2026 | mse | GARCH | ATM30 | 177 | 0.0021 | 0.5681 | -0.0045 | 0.0098 |  |  |  |
| calibrated, no smearing | 2026 | qlike | GARCH t | ATM30 | 177 | 0.0053 | 0.2669 | -0.0307 | 0.0479 |  |  |  |
| calibrated, no smearing | 2026 | mse | GARCH t | ATM30 | 177 | 0.0002 | 0.0961 | -0.0037 | 0.0048 |  |  |  |
| calibrated, no smearing | 2026 | qlike | HAR | ATM30 | 177 | 0.0116 | 0.6080 | -0.0228 | 0.0491 |  |  |  |
| calibrated, no smearing | 2026 | mse | HAR | ATM30 | 177 | 0.0017 | 0.7492 | -0.0024 | 0.0060 |  |  |  |
| calibrated, no smearing | 2026 | qlike | HAR+ATM30 | ATM30 | 177 | 0.0013 | 0.4112 | -0.0046 | 0.0081 |  |  |  |
| calibrated, no smearing | 2026 | mse | HAR+ATM30 | ATM30 | 177 | 0.0003 | 0.8086 | -0.0004 | 0.0010 |  |  |  |
| calibrated, no smearing | 2026 | qlike | HAR+ATM30 | HAR | 177 | -0.0103 | -0.5254 | -0.0498 | 0.0253 |  |  |  |
| calibrated, no smearing | 2026 | mse | HAR+ATM30 | HAR | 177 | -0.0014 | -0.6191 | -0.0058 | 0.0026 |  |  |  |

## Variance risk premium

| period | n | mean_iv2 | mean_rv | mean_vrp_var | median_vrp_var | mean_vrp_vol | median_vrp_vol | share_iv_above_rv |
|---|---|---|---|---|---|---|---|---|
| all | 1806 | 0.4461 | 0.4869 | -0.0408 | 0.1052 | 0.0426 | 0.0973 | 0.7220 |
| 2018-2023 | 1165 | 0.5010 | 0.5552 | -0.0543 | 0.1491 | 0.0566 | 0.1266 | 0.7605 |
| 2024-2025 | 464 | 0.3637 | 0.4095 | -0.0458 | 0.0491 | -0.0011 | 0.0455 | 0.6509 |
| 2026 | 177 | 0.3005 | 0.2401 | 0.0605 | 0.0686 | 0.0648 | 0.0640 | 0.6554 |

## Argentina events: forward variance between the expiries that straddle each event

These are case studies, with placebo dates and no p-values. `ratio` is the forward vol over the near-term vol. `share_placebos_below` is the share of placebo ratios below the event ratio. Each placebo date is a multiple of 28 days from the event, has a similar expiry gap, and has no listed event in its pair. Other shocks can be in the placebos.

| event | event_session | first_return | observed | near_expiry | far_expiry | near_days | gap_days | tier | near_vol | forward_vol | ratio | realized_vol_between | placebo_count | placebo_median_ratio | share_placebos_below |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2019 PASO | 2019-08-12 | -0.824 | 2019-07-12 | 2019-07-19 | 2019-08-16 | 7.010 | 28 | 1.000 | 0.460 | 0.576 | 1.251 | 3.038 | 22 | 0.935 | 1.000 |
| 2019 general | 2019-10-28 | -0.121 | 2019-10-11 | 2019-10-18 | 2019-11-15 | 7.010 | 28 | 1.000 | 0.895 | 0.925 | 1.034 | 0.673 | 22 | 0.960 | 0.864 |
| 2021 PASO | 2021-09-13 | 0.089 | 2021-08-03 | 2021-08-20 | 2021-09-17 | 17.010 | 28 | 2.000 | 0.493 | 0.553 | 1.122 | 0.668 | 20 | 0.969 | 0.900 |
| 2021 midterm | 2021-11-15 | -0.011 | 2021-10-08 | 2021-10-15 | 2021-11-19 | 7.010 | 35 | 2.000 | 0.521 | 0.673 | 1.291 | 0.605 | 19 | 0.982 | 1.000 |
| 2023 PASO | 2023-08-14 | -0.060 | 2023-07-14 | 2023-07-21 | 2023-08-18 | 7.010 | 28 | 1.000 | 0.732 | 0.923 | 1.261 | 0.518 | 21 | 0.970 | 0.857 |
| 2023 general | 2023-10-23 | 0.013 | 2023-10-13 | 2023-10-20 | 2023-11-17 | 7.010 | 28 | 1.000 | 0.779 | 0.949 | 1.219 | 0.509 | 21 | 0.980 | 0.905 |
| 2023 runoff | 2023-11-20 | 0.159 | 2023-11-10 | 2023-11-17 | 2023-12-15 | 7.010 | 28 | 1.000 | 0.577 | 0.725 | 1.256 | 0.910 | 21 | 0.996 | 0.905 |
| 2025 PBA | 2025-09-08 | -0.269 | 2025-08-08 | 2025-08-15 | 2025-09-19 | 7.010 | 35 | 1.000 | 0.474 | 0.491 | 1.034 | 1.033 | 22 | 1.001 | 0.591 |
| 2025 midterm | 2025-10-27 | 0.327 | 2025-10-10 | 2025-10-17 | 2025-11-21 | 7.010 | 35 | 1.000 | 1.129 | 1.123 | 0.995 | 1.194 | 22 | 0.991 | 0.545 |

## Selection: missing `ATM30` days

| has_iv | n | mean_log_rv30 | mean_abs_same_day_return |
|---|---|---|---|
| False | 287 | -1.2725 | 0.0268 |
| True | 1828 | -1.1772 | 0.0291 |

| near_bucket | n | coverage | mean_log_rv30 |
|---|---|---|---|
| 0-6 | 363 | 0.675 | -1.170 |
| 7-13 | 499 | 0.940 | -1.178 |
| 14-20 | 480 | 0.960 | -1.219 |
| 21-30 | 675 | 0.967 | -1.209 |

HAR on all days and on each group:

| sample | n | const | log_rv1 | log_rv5 | log_rv22 | r2 |
|---|---|---|---|---|---|---|
| all days | 2093 | -0.785 | 0.007 | 0.111 | 0.201 | 0.100 |
| days with ATM30 | 1806 | -0.774 | 0.010 | 0.127 | 0.181 | 0.097 |
| days without ATM30 | 287 | -0.862 | -0.014 | 0.004 | 0.333 | 0.159 |

## Overnight and open-to-close split of RV

| period | n | overnight_share | intraday_share | sum_parts_to_rv |
|---|---|---|---|---|
| all | 2115 | 0.324 | 0.676 | 0.963 |
| 2018-2023 | 1427 | 0.323 | 0.677 | 0.941 |
| 2024-2025 | 502 | 0.360 | 0.640 | 1.032 |
| 2026 | 186 | 0.175 | 0.825 | 1.010 |

Cash goes in the overnight part. The two parts do not sum to RV, because each part is squared separately and the cross term between them is left out. `sum_parts_to_rv` shows the size of this gap.

## `MF30` (descriptive only)

| year | n | median_atm30 | median_mf30 | median_extrapolated | median_atm_over_mf |
|---|---|---|---|---|---|
| 2024 | 174 | 0.588 | 0.633 | 0.180 | 0.946 |
| 2025 | 176 | 0.560 | 0.604 | 0.170 | 0.941 |
| 2026 | 162 | 0.535 | 0.600 | 0.251 | 0.906 |

## Appendix: level form

The plan expects the level b to depend on 2019-08-12.

| period | n | a | b | r2 |
|---|---|---|---|---|
| all | 1806 | 0.1808 | 0.6863 | 0.0308 |
| 2018-2023 | 1165 | 0.3249 | 0.4597 | 0.0106 |
| 2024-2025 | 464 | -0.0669 | 1.3097 | 0.4456 |
| 2026 | 177 | 0.1695 | 0.2346 | 0.0355 |
| all, no 2019-08-12 windows | 1786 | 0.1166 | 0.6159 | 0.1463 |
