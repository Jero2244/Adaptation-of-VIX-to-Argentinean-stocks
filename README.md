# GGAL ADR 30-day at-the-money implied volatility study

**Read this page first. Then read `HANDOFF.md`.** This page describes what the project is, and what it is not.

## What the project is

The project builds a 30-day implied volatility series for the GGAL ADR (Nasdaq) from Databento OPRA option quotes. It then tests whether the series forecasts 30-day realized variance beyond a HAR-type baseline.

- **Main series, `ATM30`.** `ATM30` is a Black (1976) at-the-money implied volatility. The code takes a snapshot at 15:45 New York time. It finds the forward from put-call parity. It inverts the call-put average price at the two strikes next to the forward. It interpolates in strike. It interpolates the total variance of two expiries to 30 days.
- **Descriptive series, `MF30`.** `MF30` integrates a PCHIP smile with flat wings. It is descriptive only. It starts in 2024.
- **Target.** The target is the realized variance of the total return (price plus cash) over the next 30 calendar days.
- **Main test.** The regression is log `RV30` on three trailing log realized variances (1, 5, and 22 sessions) and log `ATM30` squared. The coefficient on `ATM30` is `b`. In-sample on 2018-05 to 2026-10, `b` is .622 on 1,806 origins.
- **One-time test.** The one-time test on 2016-01 to 2018-04 is finished. Its result is "Inconclusive", with a positive sign of `b` (.281). Do not run it again.

## What the project is not

**`ATM30` is not the CBOE VIX formula.** The folder name and some early notes say "VIX adaptation". That wording is wrong for the main series.

- The CBOE method sums `ΔK/K² · e^{RT} · Q(K)` over a strip of out-of-the-money options. `ATM30` has no strip sum, no `K0`, no `ΔK`, and no `(F/K0 − 1)²` term.
- `MF30` is also not the CBOE formula. It integrates a fitted smile.
- The name "VIX-style index" is therefore not correct for `ATM30`. Use "ATM implied volatility index".

**Why a literal CBOE calculation does not work on this chain.** The audit applied the white-paper formula to the stored 15:45 snapshot (`audit/a02_series_and_cboe.py`). The table shows the result.

| Year | Share of sessions with 2 or more out-of-the-money bids on each wing, both terms | Median strikes in the near term | CBOE-style / `ATM30` (median) |
|---|---|---|---|
| 2018 | 27% | 4 | 1.10 |
| 2019 | 12% | 3 | 1.12 |
| 2020 | 0% | 2 | 1.16 |
| 2021 | 0% | 2 | 1.30 |
| 2022 | 0% | 2 | 1.83 |
| 2023 | 15% | 3 | 1.11 |
| 2024 | 52% | 7 | 1.00 |
| 2025 | 38% | 6 | 1.02 |
| 2026 | 71% | 11 | 1.01 |

- Before 2024 the chain has too few strikes with a bid. The CBOE sum then overstates the variance, by up to 63% from the strike grid alone in 2022.
- Only 245 sessions have 3 or more strikes on each wing for both terms. Almost all are in 2024 or later.
- The daily standard deviation of log changes is 12.4% for the CBOE-style series and 7.3% for `ATM30`.
- So the choice of an ATM series is right for this chain. The error is the name.

## Known limits of the method (see `audit/AUDIT_REPORT.md`)

- The options are American. GGAL pays dividends of about 2% to 3.7% of the price. The frozen recipe uses European Black. When a dividend falls inside the term, it overstates term IV by about 2% to 13%.
- The quotes are wide. The bid-ask band puts a median uncertainty of about 14% on the IV. The frozen code has no spread filter.
- The Nasdaq stock quote is one venue only. It is not the consolidated quote.
- The HAR baseline is weak. Its inputs are squared daily returns, and R² is .097.
- `contract_multiplier` is undefined in the OPRA definitions. The code cannot detect a non-standard deliverable.
- The in-sample result is fragile. Elections and the 2025-03 quote format change drive part of it.

The folder `fixes/` holds development work on open data that tests each limit. See `fixes/FIXES_REPORT.md` and `fixes/ERRATA.md`. This work does not replace the pre-registered result.

## Data in `databento_ggal_20261031/`

The data is licensed. Keep it local. Do not publish it and do not commit it.

| File | Dataset, schema | What it holds | Used by the study |
|---|---|---|---|
| `options/OPRA-cbbo_1m.zip` | `OPRA.PILLAR`, `cbbo-1m` | Consolidated best bid and offer, one daily file per session, 2013-04 to 2026-10 | Yes. The 15:45 snapshot. The study uses 2016-01 onward |
| `options/OPRA-Definition.zip` | `OPRA.PILLAR`, `definition` | Contract definitions (expiry, strike, right) | Yes |
| `options/OPRA-Statistics.zip` | `OPRA.PILLAR`, `statistics` | OPRA statistics | No |
| `options/OPRA-TCBBO.zip` | `OPRA.PILLAR`, `tcbbo` | Trades with the BBO before each trade, 2023-03 onward | No |
| `equity/XNAS-bbo.zip` | `XNAS.ITCH`, `bbo-1m` | Nasdaq best bid and offer, update-only, with pre-market and after-hours rows | Stock mid for diagnostics only |
| `equity/XNAS-ohlc.zip` | `XNAS.ITCH`, `ohlcv-1d` | Nasdaq daily bars | Yes, for sessions |
| `equity/XNAS-statistics.zip` | `XNAS.ITCH`, `statistics` | Official open and close | Yes, for returns |
| `equity/XNAS-definition.zip` | `XNAS.ITCH`, `definition` | Equity definition | No |

- The folder does not hold MBP-1, MBP-10, or BBO-1s data.
- The stock data starts on 2018-05-01. The 2013-2015 option data is dropped.
- Prices are unadjusted. Dividends and the 2025 rights offering enter through `data/adr_cash_events.csv`.
- Nineteen of the 32 open-period cash rows have the basis "nasdaq_basis_unconfirmed". No depositary notice backs them.

## How to run the pipeline

Run these commands from this folder. Use the `py4fi` Python. Put code in script files and do not pass multi-line code to `python -c`.

1. Run the tests: `python -m unittest discover -s tests -v`.
2. Build inputs: `python build_inputs.py`.
3. Build the 15:45 snapshot (about 2.5 minutes): `python build_snapshot.py`.
4. Build the series: `python build_series.py`.
5. Run the development analysis (several minutes): `python run_development.py`.
6. Check that no frozen file changed: `python -c "import freeze; print(freeze.differences())"` (a one-line command is fine). The result must be `[]`.

**Warning:** every `.py` file in this folder and in `tests/`, plus `PROTOCOL.md` and `STAGE4_PLAN.md`, is frozen and hashed (`freeze.py`, `reports/freeze_manifest.json`). An edit makes the checks fail. Put new code in a new folder.

**Warning:** do not run `run_tests_once.py`. The one-time test is finished.

## Folder map

| Path | Content |
|---|---|
| `HANDOFF.md` | Entry point, status, and rules |
| `PROTOCOL.md`, `STAGE4_PLAN.md` | Frozen rules and plan |
| `*.py` (root), `tests/` | Frozen pipeline and tests |
| `data/` | Derived tables (licensed data; keep local) |
| `reports/` | Stage reports, the freeze manifest, and the Stage 5 result |
| `writeup/` | Paper builders and PDFs |
| `calibration/` | Implied move calibration side study |
| `review/` | Earlier independent reviews |
| `audit/` | The audit of 2026-11-10: `AUDIT_REPORT.md`, scripts, and outputs |
| `fixes/` | Development fixes for the audit findings: code, outputs, `FIXES_REPORT.md`, `ERRATA.md` |

## References

All references were checked on 2026-11-11. Journal articles match Crossref records, Mincer and Zarnowitz matches the NBER record, and the Cboe document (version 5.0, revised 26 February 2026) matches the PDF. Politis and Romano (1992) has no online record, but three independent bibliographies give the same entry.

- Cboe Global Markets. *Cboe Volatility Index Mathematics Methodology* (version of 11 September 2025; checked on the Cboe site on 2026-11-11). The CBOE variance formula and the 30-day interpolation.
- Black, F. (1976). The pricing of commodity contracts. *Journal of Financial Economics* 3, 167–179.
- Corsi, F. (2009). A simple approximate long-memory model of realized volatility. *Journal of Financial Econometrics* 7(2), 174–196.
- Newey, W. K., and West, K. D. (1987). A simple, positive semi-definite, heteroskedasticity and autocorrelation consistent covariance matrix. *Econometrica* 55(3), 703–708.
- Clark, T. E., and West, K. D. (2007). Approximately normal tests for equal predictive accuracy in nested models. *Journal of Econometrics* 138(1), 291–311.
- Mincer, J., and Zarnowitz, V. (1969). The evaluation of economic forecasts. In J. Mincer (ed.), *Economic Forecasts and Expectations*. NBER.
- Politis, D. N., and Romano, J. P. (1992). A circular block-resampling procedure for stationary data. In R. LePage and L. Billard (eds.), *Exploring the Limits of Bootstrap*. Wiley.
- Carr, P., and Madan, D. (1998). Towards a theory of volatility trading. In R. Jarrow (ed.), *Volatility: New Estimation Techniques for Pricing Derivatives*, Risk Books, 417–427. (Corrected: the earlier entry, "Towering over the competition", *Risk* 11, was not found. Check the page range against the source.)
- Britten-Jones, M., and Neuberger, A. (2000). Option prices, implied price processes, and stochastic volatility. *Journal of Finance* 55(2), 839–866.
- Jiang, G. J., and Tian, Y. S. (2005). The model-free implied volatility and its information content. *Review of Financial Studies* 18(4), 1305–1342.
- Cox, J. C., Ross, S. A., and Rubinstein, M. (1979). Option pricing: a simplified approach. *Journal of Financial Economics* 7(3), 229–263. (Binomial tree used in `fixes/`.)

## What this public repository holds

This repository holds the code, the methodology documents, and aggregated results only.

- **Included:** all Python code, the plans and protocol, the audit report, the post-audit checks, and tables of aggregated results (coefficients, intervals, counts).
- **Not included:** the raw Databento and Alpaca data, every table derived from quotes with per-day or per-quote values (`data/`, `fixes/data/`, the daily index series), the figures, and the PDF papers.

The pipeline does not run from this repository alone. To run it, you need your own licensed copy of the data in the folders that `config.py` names. The file `.gitignore` is a whitelist that enforces this selection.
