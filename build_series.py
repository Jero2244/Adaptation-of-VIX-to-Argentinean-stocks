"""Stage 2, part 2: build ATM30 and MF30 from the snapshot, with variants, flags, and the coverage report.

Run from this folder, after build_snapshot.py: conda run -n py4fi python build_series.py
Output: data/atm_terms.parquet, data/index_series.parquet, reports/index_series.csv, reports/coverage_*.csv, reports/stage2_coverage.md
Missing days stay missing. Nothing is imputed.
"""
from __future__ import annotations

from math import log, sqrt

import numpy as np
import pandas as pd

from atm_index import TARGET_MINUTES, bracket_terms, constant_maturity, expiry_minutes, term_iv
from config import DATA, DATA_END, DEVELOPMENT_START, EQUITY_BBO, OPTION_CBBO, REPORTS, SOURCE, load_cash_events
from load_data import day_conditions
from model_free_index import term_variance

MAX_AGE = 30.0
FLOOR_MINUTES = 7 * 1440
ONE_MONTH_DAYS, THREE_MONTH_DAYS = 30.0, 91.0
PARITY_OUTLIER = 0.05


def session_rates(sessions: pd.DatetimeIndex, path=SOURCE / "fred_rates.csv") -> pd.DataFrame:
    """Continuous rates from Treasury yields. Each session uses the last observation before that session."""
    raw = pd.read_csv(path, parse_dates=["observation_date"], index_col="observation_date").apply(pd.to_numeric, errors="coerce")
    continuous = np.log1p(raw.dropna(how="all").ffill() / 100)
    return continuous.shift(1).reindex(sessions, method="ffill")


def rate_for(rates_row: pd.Series, minutes: int) -> float:
    days = minutes / 1440
    weight = min(max((days - ONE_MONTH_DAYS) / (THREE_MONTH_DAYS - ONE_MONTH_DAYS), 0.0), 1.0)
    return float((1 - weight) * rates_row["DGS1MO"] + weight * rates_row["DGS3MO"])


def build_terms(chain: pd.DataFrame, minutes_by_expiry: dict, rates_row: pd.Series) -> dict:
    groups = dict(tuple(chain.groupby("expiry"))) if len(chain) else {}
    terms = {}
    for expiry, minutes in minutes_by_expiry.items():
        if minutes <= 0:
            continue
        group = groups.get(expiry, chain.iloc[0:0])
        term = term_iv(group, minutes, rate_for(rates_row, minutes))
        terms[expiry] = dict(term, quoted=len(group))
    return terms


def combine(terms: dict, pair: tuple | None) -> dict:
    """Variance at 30 days from a bracket. Empty values if the bracket is absent or a term has no IV."""
    if pair is None:
        return dict(variance=None, reason="no listed bracket")
    near, far = pair
    near_term = terms.get(near)
    far_term = terms.get(far) if far is not None else None
    if near_term is None or near_term["iv"] is None:
        return dict(variance=None, reason="near: " + (near_term["reason"] if near_term else "no term"))
    if far is None:
        return dict(variance=near_term["iv"] ** 2, reason="ok", near=near, far=None)
    if far_term is None or far_term["iv"] is None:
        return dict(variance=None, reason="far: " + (far_term["reason"] if far_term else "no term"))
    variance = constant_maturity(near_term["minutes"], near_term["iv"] ** 2, far_term["minutes"], far_term["iv"] ** 2)
    return dict(variance=variance, reason="ok", near=near, far=far)


def vol(result: dict) -> float:
    return sqrt(result["variance"]) if result.get("variance") else np.nan


def series_tables(snapshot: pd.DataFrame, listed: pd.DataFrame, diagnostics: pd.DataFrame, rates: pd.DataFrame, dividends: np.ndarray, rights: np.ndarray, option_condition: dict, equity_condition: dict) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Build the series and the term table from one set of input tables. diagnostics has session_date as its index. Writes nothing."""
    duplicates = int(snapshot.duplicated(["session_date", "expiry", "right", "strike"]).sum())
    snapshot = snapshot.sort_values("age", kind="stable").drop_duplicates(["session_date", "expiry", "right", "strike"], keep="first")
    sessions = diagnostics.index.sort_values()
    by_session = dict(tuple(snapshot.groupby("session_date")))
    listed_by_session = dict(tuple(listed.groupby("session_date")))

    rows, term_rows = [], []
    for session in sessions:
        chain_all = by_session.get(session, snapshot.iloc[0:0])
        chain = chain_all[chain_all["age"] <= MAX_AGE]
        expiries = pd.to_datetime(listed_by_session[session]["expiry"]) if session in listed_by_session else []
        minutes = {pd.Timestamp(e): expiry_minutes(e, session) for e in expiries}
        rates_row = rates.loc[session]

        terms = build_terms(chain, minutes, rates_row)
        strict_pair = bracket_terms(minutes)
        strict = combine(terms, strict_pair)
        floor7 = combine(terms, bracket_terms(minutes, floor_minutes=FLOOR_MINUTES))
        usable = {e: m for e, m in minutes.items() if m > 0 and terms[e]["iv"] is not None}
        usable_result = combine(terms, bracket_terms(usable))
        session_last = combine(build_terms(chain_all, minutes, rates_row), strict_pair)

        for expiry, term in terms.items():
            term_rows.append(dict(session_date=session, expiry=expiry, **{k: term[k] for k in ("minutes", "forward", "iv", "tier", "strike_low", "strike_high", "max_distance", "max_age", "relative_spread", "pairs", "quoted", "reason")}))

        row = dict(session_date=session, atm30=vol(strict), status=strict["reason"], atm30_floor7=vol(floor7), atm30_usable=vol(usable_result), atm30_session_last=vol(session_last), mf30=np.nan, mf30_status="no bracket", mf_extrapolated_share=np.nan)
        near, far = strict_pair if strict_pair else (None, None)
        near_term, far_term = terms.get(near), terms.get(far)
        row.update(listed_bracket=strict_pair is not None, near_expiry=near, far_expiry=far,
                   near_quoted=near_term["quoted"] if near_term else 0, far_quoted=far_term["quoted"] if far_term else 0,
                   near_pairs=near_term["pairs"] if near_term else 0, far_pairs=far_term["pairs"] if far_term else 0,
                   near_days=near_term["minutes"] / 1440 if near_term else np.nan, far_days=far_term["minutes"] / 1440 if far_term else np.nan)
        if strict["reason"] == "ok":
            used = [t for t in (near_term, far_term) if t is not None]
            row.update(tier=max(t["tier"] for t in used), near_iv=near_term["iv"], far_iv=far_term["iv"] if far_term else np.nan,
                       near_forward=near_term["forward"], far_forward=far_term["forward"] if far_term else np.nan,
                       max_distance=max(t["max_distance"] for t in used), quote_age=max(t["max_age"] for t in used), relative_spread=max(t["relative_spread"] for t in used))
            stock = diagnostics.loc[session, "stock_mid"]
            row["log_forward_to_stock"] = log(near_term["forward"] / stock) if stock > 0 else np.nan
            if near_term["minutes"] and far_term:
                row["near_weight"] = (far_term["minutes"] - TARGET_MINUTES) / (far_term["minutes"] - near_term["minutes"])
            parts = []
            for expiry, term in ((near, near_term), (far, far_term)):
                if term is None:
                    continue
                group = chain[chain["expiry"] == expiry]
                parts.append(term_variance(group, term["minutes"], rate_for(rates_row, term["minutes"]), term["forward"]))
            if all(p["variance"] is not None for p in parts):
                variance = parts[0]["variance"] if len(parts) == 1 else constant_maturity(near_term["minutes"], parts[0]["variance"], far_term["minutes"], parts[1]["variance"])
                row.update(mf30=sqrt(variance), mf30_status="ok", mf_extrapolated_share=max(p["extrapolated_share"] for p in parts))
            else:
                row["mf30_status"] = next(p["reason"] for p in parts if p["variance"] is None)
        front_end = pd.Timestamp(near) if near is not None else None
        in_front = lambda dates: bool(front_end is not None and ((dates > np.datetime64(session)) & (dates <= np.datetime64(front_end))).any())
        day = session.strftime("%Y-%m-%d")
        row.update(flag_front_under_7d=bool(near_term and near_term["minutes"] < FLOOR_MINUTES), flag_ex_in_front=in_front(dividends), flag_rights_in_front=in_front(rights),
                   flag_rights_in_bracket=bool(far is not None and ((rights > np.datetime64(session)) & (rights <= np.datetime64(pd.Timestamp(far)))).any()),
                   flag_option_degraded=option_condition.get(day) == "degraded", flag_equity_degraded=equity_condition.get(day) == "degraded",
                   flag_half_day=diagnostics.loc[session, "last_bar"] is not None and diagnostics.loc[session, "last_bar"] < "15:45")
        rows.append(row)

    series = pd.DataFrame(rows)
    series["year"] = series["session_date"].dt.year
    return series, pd.DataFrame(term_rows), duplicates


def main() -> None:
    REPORTS.mkdir(exist_ok=True)
    snapshot = pd.read_parquet(DATA / "option_snapshot_1545.parquet")
    listed = pd.read_parquet(DATA / "option_listed.parquet")
    diagnostics = pd.read_parquet(DATA / "session_diagnostics.parquet").set_index("session_date")
    events = load_cash_events(DEVELOPMENT_START, DATA_END)
    dividends = events.loc[events["kind"] == "dividend", "ex_date"].values
    rights = events.loc[events["kind"] == "rights", "ex_date"].values
    rates = session_rates(diagnostics.index.sort_values())
    series, terms, duplicates = series_tables(snapshot, listed, diagnostics, rates, dividends, rights, day_conditions(OPTION_CBBO), day_conditions(EQUITY_BBO))
    terms.to_parquet(DATA / "atm_terms.parquet", index=False)
    series.to_parquet(DATA / "index_series.parquet", index=False)
    series.drop(columns="year").to_csv(REPORTS / "index_series.csv", index=False)
    write_report(series, diagnostics, duplicates)


def coverage_tables(series: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    by_year = series.groupby("year").agg(
        sessions=("atm30", "size"), listed_bracket=("listed_bracket", "sum"),
        any_quote_both=("near_quoted", lambda s: int(((s > 0) & (series.loc[s.index, "far_quoted"] > 0)).sum())),
        pair_both=("near_pairs", lambda s: int(((s > 0) & (series.loc[s.index, "far_pairs"] > 0)).sum())),
        atm30=("atm30", "count"), tier1=("tier", lambda s: int((s == 1).sum())), tier2=("tier", lambda s: int((s == 2).sum())),
        atm30_floor7=("atm30_floor7", "count"), atm30_usable=("atm30_usable", "count"), atm30_session_last=("atm30_session_last", "count"), mf30=("mf30", "count"))
    by_year.loc["all"] = by_year.sum()
    by_year["atm30_share"] = (by_year["atm30"] / by_year["sessions"]).round(3)
    buckets = pd.cut(series["near_days"], [-1, 7, 14, 21, 30.01], right=False, labels=["0-6", "7-13", "14-20", "21-30"])
    by_days = series.groupby(buckets, observed=True).agg(sessions=("atm30", "size"), atm30=("atm30", "count"), tier1=("tier", lambda s: int((s == 1).sum())), tier2=("tier", lambda s: int((s == 2).sum())))
    by_days["atm30_share"] = (by_days["atm30"] / by_days["sessions"]).round(3)
    return by_year, by_days


def markdown(frame: pd.DataFrame) -> str:
    table = frame.reset_index()
    lines = ["| " + " | ".join(map(str, table.columns)) + " |", "|" + "---|" * len(table.columns)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in table.itertuples(index=False)]
    return "\n".join(lines)


def write_report(series: pd.DataFrame, diagnostics: pd.DataFrame, duplicates: int) -> None:
    by_year, by_days = coverage_tables(series)
    by_year.to_csv(REPORTS / "coverage_by_year.csv")
    by_days.to_csv(REPORTS / "coverage_by_near_days.csv")
    reasons = series.loc[series["atm30"].isna()].groupby(["year", "status"]).size().unstack("year", fill_value=0)
    reasons.to_csv(REPORTS / "coverage_missing_reasons.csv")

    monthly = series[(series["session_date"] >= "2024-10-01") & (series["session_date"] <= "2025-06-30")].copy()
    monthly["month"] = monthly["session_date"].dt.strftime("%Y-%m")
    diag = diagnostics.reset_index()
    diag["month"] = diag["session_date"].dt.strftime("%Y-%m")
    diag["rows_per_instrument"] = diag["cbbo_rows"] / diag["cbbo_instruments"].replace(0, np.nan)
    format_break = monthly.groupby("month").agg(sessions=("atm30", "size"), atm30=("atm30", "count"), session_last=("atm30_session_last", "count"), median_age=("quote_age", "median"), tier1=("tier", lambda s: int((s == 1).sum()))).join(
        diag.groupby("month").agg(rows_per_instrument=("rows_per_instrument", "median"), flag_mode=("flag_mode", "median"), null_bid_share=("null_bid_share", "median")))
    format_break = format_break.round(3)
    format_break.to_csv(REPORTS / "coverage_format_break.csv")
    flags = diag.sort_values("session_date")["flag_mode"].values
    changes = diag.sort_values("session_date").loc[np.r_[False, flags[1:] != flags[:-1]], ["session_date", "flag_mode"]]

    both = series.dropna(subset=["atm30", "atm30_session_last"])
    before, after = both[both["session_date"] < "2025-02-01"], both[both["session_date"] >= "2025-04-01"]
    gap = lambda f: float((np.log(f["atm30_session_last"] / f["atm30"]).abs()).median())
    ratio = series[(series["year"] >= 2024)].dropna(subset=["atm30", "mf30"])
    ratio_2024 = series[series["year"] == 2024].dropna(subset=["atm30", "mf30"])
    outliers = series[series["log_forward_to_stock"].abs() > PARITY_OUTLIER]
    rule = {2018: .91, 2019: .90, 2020: .85, 2021: .72, 2022: .78, 2023: .85, 2024: .91}
    compare = pd.DataFrame({"debate": pd.Series(rule), "study": by_year.loc[list(rule), "atm30_share"]})
    all_row = by_year.loc["all"]
    sessions = int(all_row["sessions"])
    share = lambda column: f"{int(all_row[column])} ({all_row[column] / sessions:.1%})"
    flags_total = series[["flag_front_under_7d", "flag_ex_in_front", "flag_rights_in_front", "flag_rights_in_bracket", "flag_option_degraded", "flag_equity_degraded", "flag_half_day"]].sum()
    flags_with_value = series.loc[series["atm30"].notna(), flags_total.index].sum()

    text = f"""# Stage 2: series and coverage

Exploratory. This report covers 2018-05-01 to 2026-10-29. The 2016-01 to 2018-04 test stays locked. Missing days stay missing.

## Coverage by year

{markdown(by_year)}

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
| All sessions | {sessions} |
| Listed bracket | {share("listed_bracket")} |
| A quote on both terms | {share("any_quote_both")} |
| A two-sided pair on both terms | {share("pair_both")} |
| `ATM30` | {share("atm30")} |
| `ATM30` Tier 1 | {share("tier1")} |
| `atm30_usable` | {share("atm30_usable")} |
| `atm30_session_last` | {share("atm30_session_last")} |

## Coverage against the debate check

The debate rule is not fully recorded in the plan, so differences can come from the rule.

{markdown(compare)}

## Coverage by days to the near expiry

{markdown(by_days)}

## Reasons for missing `ATM30`

{markdown(reasons)}

## Quote format break

{markdown(format_break)}

Changes in the most common flag value:

{markdown(changes.set_index("session_date"))}

Median absolute log gap between `atm30_session_last` and `atm30`: {gap(before):.4f} before 2025-02, and {gap(after):.4f} from 2025-04.

## Checks

- `ATM30`/`MF30` median vol ratio in 2024: {float((ratio_2024["atm30"] / ratio_2024["mf30"]).median()):.3f}, on {len(ratio_2024)} sessions. The debate check was near 1.07.
- `ATM30`/`MF30` median vol ratio from 2024: {float((ratio["atm30"] / ratio["mf30"]).median()):.3f}, on {len(ratio)} sessions.
- Median share of `MF30` variance outside the quoted range from 2024: {float(ratio["mf_extrapolated_share"].median()):.3f}.
- Median log(near forward / stock mid): {float(series["log_forward_to_stock"].median()):.4f}. Absolute value above {PARITY_OUTLIER}: {len(outliers)} sessions.
- Duplicate quotes removed from the snapshot: {duplicates}. Quotes without a definition: {int(diagnostics["unmatched_quotes"].sum())}. Other roots: {int(diagnostics["other_roots"].sum())}.

## Flags

{markdown(pd.DataFrame({"sessions": flags_total, "with_atm30": flags_with_value}))}
"""
    (REPORTS / "stage2_coverage.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
