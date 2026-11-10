"""Stage 3: run the primary question and all development tests. All results are exploratory.

Run from this folder: conda run --no-capture-output -n py4fi python run_development.py
Output: reports/stage3_results.md, reports/stage3_*.csv, reports/eviews_regressions.csv, data/forecast_panel.parquet
This run reads 2018-05-01 to 2026-10-29 only. It does not touch the locked 2016-01 to 2018-04 test. MF30 stays out of the regressions.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import events as ev
import forecasts as fc
import inference as inf
import realized as rz
import report_stage4
import stage4_rules as rules
from config import DATA, REPORTS

REPS = 2000
SENSITIVITY_REPS = 1000
BLOCKS = (21, 63)
NW_LAGS = 21
SEED = 20261104
HAR = ["log_rv1", "log_rv5", "log_rv22"]
IV = "log_iv2"
PERIODS = {"2018-2023": ("2018-05-01", "2023-12-31"), "2024-2025": ("2024-01-01", "2025-12-31"), "2026": ("2026-01-01", "2026-12-31")}
SPECS = {"MZ": [IV], "HAR": HAR, "HAR+IV": HAR + [IV]}
FLOORS = (1e-8, 1e-5)
NO_PASO = "all, no 2019 PASO windows"
PASO_SESSION = "2019-08-12"


def build_panel(floor: float = rz.DAILY_VARIANCE_FLOOR) -> pd.DataFrame:
    series = pd.read_parquet(DATA / "index_series.parquet")
    panel = rz.build_realized(floor).merge(series, on="session_date", how="left", validate="one_to_one")
    if panel["year"].isna().any():
        raise ValueError("A session has no index row")
    panel["year"] = panel["year"].astype(int)
    return rules.add_inputs(panel)


def period_rows(frame: pd.DataFrame, period: str) -> pd.DataFrame:
    if period == "all":
        return frame
    if period == NO_PASO:
        return frame[~((frame["session_date"] < PASO_SESSION) & (frame["window_end"] >= PASO_SESSION))]
    first, last = PERIODS[period]
    return frame[frame["session_date"].between(first, last)]


def design(frame: pd.DataFrame, names: list[str]) -> np.ndarray:
    return np.column_stack([np.ones(len(frame))] + [frame[name].to_numpy(dtype=float) for name in names])


def regression_rows(frame: pd.DataFrame, names: list[str], label: dict, y_name: str = "log_rv30", blocks=BLOCKS, reps: int = REPS) -> list[dict]:
    """One row per coefficient. A block longer than a third of the sample has no bootstrap, because few blocks fit."""
    y, X = frame[y_name].to_numpy(dtype=float), design(frame, names)
    fit = inf.ols(y, X)
    newey = inf.newey_west_se(X, fit["residuals"], NW_LAGS)
    positions = frame["position"].to_numpy()
    span = int(positions[-1] - positions[0] + 1)
    rows = [dict(label, coefficient=name, estimate=fit["beta"][i], nw_se=newey[i], nw_t=fit["beta"][i] / newey[i], n=len(frame), r2=fit["r2"], first=frame["session_date"].iloc[0].date(), last=frame["session_date"].iloc[-1].date()) for i, name in enumerate(["const"] + names)]

    def estimator(index: np.ndarray) -> np.ndarray:
        return np.linalg.lstsq(X[index], y[index], rcond=None)[0]

    for block in blocks:
        if block * 3 > span:
            continue
        summary = inf.bootstrap_summary(fit["beta"], inf.block_bootstrap(estimator, positions, block, reps, SEED + block))
        for i, row in enumerate(rows):
            row.update({f"boot{block}_se": summary["se"][i], f"boot{block}_t": summary["t"][i], f"boot{block}_low": summary["low"][i], f"boot{block}_high": summary["high"][i]})
    return rows


def primary_tables(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    sample = panel[panel["primary"]]
    rows = []
    for period in ["all", *PERIODS]:
        chosen = period_rows(sample, period)
        for spec, names in SPECS.items():
            rows += regression_rows(chosen, names, dict(period=period, spec=spec))
    yearly = []
    for year, chosen in sample.groupby("year"):
        for spec, names in SPECS.items():
            yearly += regression_rows(chosen, names, dict(year=year, spec=spec), blocks=(21,), reps=SENSITIVITY_REPS)
    offsets = []
    for spec, names in (("MZ", [IV]), ("HAR+IV", HAR + [IV])):
        table = inf.non_overlapping_table(panel, "log_rv30", names, IV, panel["primary"].to_numpy())
        offsets.append(table.assign(spec=spec))
    return pd.DataFrame(rows), pd.DataFrame(yearly), pd.concat(offsets, ignore_index=True)


def iv_row(frame: pd.DataFrame, label: str, group: str, iv_name: str = IV, y_name: str = "log_rv30", extra: list[str] | None = None, instrument: str | None = None, reps: int = SENSITIVITY_REPS) -> dict:
    """The coefficient on the IV input in the HAR regression, on rows that have every input."""
    names = HAR + (extra or [])
    needed = [y_name, iv_name] + names + ([instrument] if instrument else [])
    chosen = frame.dropna(subset=needed)
    y = chosen[y_name].to_numpy(dtype=float)
    base = design(chosen, names)
    X = np.column_stack([base, chosen[iv_name].to_numpy(dtype=float)])
    positions = chosen["position"].to_numpy()
    span = int(positions[-1] - positions[0] + 1)
    fit_har, fit_full = inf.ols(y, base), inf.ols(y, X)
    row = dict(group=group, label=label, n=len(chosen), windows=round(span / 21, 1), b_iv=fit_full["beta"][-1], r2_har=fit_har["r2"], r2_full=fit_full["r2"], delta_r2=fit_full["r2"] - fit_har["r2"])
    if instrument:
        z = chosen[instrument].to_numpy(dtype=float)
        result = inf.two_stage(y, base, chosen[iv_name].to_numpy(dtype=float), z)
        row.update(b_iv=result["beta"][-1], first_stage_f=result["first_stage_f"], delta_r2=np.nan, r2_full=np.nan)

        def estimator(index: np.ndarray) -> np.ndarray:
            return inf.two_stage(y[index], base[index], X[index, -1], z[index])["beta"][-1:]
    else:
        newey = inf.newey_west_se(X, fit_full["residuals"], NW_LAGS)
        row["nw_t"] = fit_full["beta"][-1] / newey[-1]

        def estimator(index: np.ndarray) -> np.ndarray:
            return np.linalg.lstsq(X[index], y[index], rcond=None)[0][-1:]
    for block in BLOCKS:
        if block * 3 > span:
            continue
        summary = inf.bootstrap_summary(np.array([row["b_iv"]]), inf.block_bootstrap(estimator, positions, block, reps, SEED + block))
        row.update({f"boot{block}_t": summary["t"][0], f"boot{block}_low": summary["low"][0], f"boot{block}_high": summary["high"][0]})
    return row


def sensitivity_table(panel: pd.DataFrame) -> pd.DataFrame:
    sample = panel[panel["primary"]].copy()
    rows = [iv_row(sample, "primary", "base")]
    # Quote noise.
    rows.append(iv_row(sample[sample["tier"] == 1], "Tier 1 only", "quote noise"))
    rows.append(iv_row(sample[sample["tier"] == 2], "Tier 2 only", "quote noise"))
    for cut in (0.25, 0.5):
        rows.append(iv_row(sample[sample["relative_spread"] <= cut], f"spread at most {cut}", "quote noise"))
    rows.append(iv_row(sample[sample["relative_spread"] > 0.5], "spread above 0.5", "quote noise"))
    terciles = pd.qcut(sample["relative_spread"], 3, labels=["low", "middle", "high"])
    for name in ("low", "middle", "high"):
        rows.append(iv_row(sample[terciles == name], f"spread tercile {name}", "quote noise"))
    # Flags.
    for flag in ("flag_ex_in_front", "flag_front_under_7d", "flag_rights_in_bracket"):
        rows.append(iv_row(sample[~sample[flag].astype(bool)], f"drop {flag}", "flags"))
    degraded = sample["flag_option_degraded"].astype(bool) | sample["flag_equity_degraded"].astype(bool)
    rows.append(iv_row(sample[~degraded], "drop degraded days", "flags"))
    clean = ~(sample["flag_ex_in_front"].astype(bool) | sample["flag_front_under_7d"].astype(bool) | sample["flag_rights_in_bracket"].astype(bool) | degraded)
    rows.append(iv_row(sample[clean], "drop all flags", "flags"))
    # Sensitivity series, each on its own available days.
    for name in ("atm30_floor7", "atm30_usable", "atm30_session_last"):
        frame = panel.assign(**{f"log_{name}": np.log(panel[name] ** 2)})
        rows.append(iv_row(frame, name, "series", iv_name=f"log_{name}"))
    # Target and HAR input.
    rows.append(iv_row(panel[panel["primary"]], "target rv21", "target", y_name="log_rv21"))
    for floor in FLOORS:
        alternative = build_panel(floor)
        rows.append(iv_row(alternative[alternative["primary"]], f"daily variance floor {floor:g}", "target"))
    # Measurement error.
    same_days = sample.dropna(subset=["log_iv2_lag5", "log_iv2_lag1"])
    rows.append(iv_row(same_days, "OLS on the instrument days", "instrument"))
    rows.append(iv_row(same_days, "instrument: IV lag 1 session", "instrument", instrument="log_iv2_lag1"))
    rows.append(iv_row(same_days, "instrument: IV lag 5 sessions", "instrument", instrument="log_iv2_lag5"))
    # Year effects.
    dummies = pd.get_dummies(sample["year"], prefix="y", drop_first=True, dtype=float)
    rows.append(iv_row(pd.concat([sample, dummies], axis=1), "year-demeaned", "stability", extra=list(dummies.columns)))
    return pd.DataFrame(rows)


def point_estimate(frame: pd.DataFrame, names: list[str], key: str) -> float:
    return float(inf.ols(frame["log_rv30"].to_numpy(dtype=float), design(frame, names))["beta"][1 + names.index(key)])


def leave_out_tables(panel: pd.DataFrame) -> pd.DataFrame:
    sample = panel[panel["primary"]]
    rows = [dict(kind="none", dropped="none", n=len(sample), mz_b=point_estimate(sample, [IV], IV), har_iv_b=point_estimate(sample, HAR + [IV], IV))]
    for year in sorted(sample["year"].unique()):
        chosen = sample[sample["year"] != year]
        rows.append(dict(kind="year", dropped=str(year), n=len(chosen), mz_b=point_estimate(chosen, [IV], IV), har_iv_b=point_estimate(chosen, HAR + [IV], IV)))
    sessions = panel["session_date"].to_numpy()
    for name, date in ev.EVENTS:
        day = ev.first_session(date, sessions)
        # Drop every origin with the event in its target window or in its IV window. So the event leaves both IV and RV.
        chosen = sample[~((sample["session_date"] < day) & (sample["window_end"] >= day))]
        rows.append(dict(kind="event", dropped=name, n=len(chosen), mz_b=point_estimate(chosen, [IV], IV), har_iv_b=point_estimate(chosen, HAR + [IV], IV)))
    days = [ev.first_session(date, sessions) for _, date in ev.EVENTS]
    inside = np.zeros(len(sample), dtype=bool)
    for day in days:
        inside |= ((sample["session_date"] < day) & (sample["window_end"] >= day)).to_numpy()
    chosen = sample[~inside]
    rows.append(dict(kind="event", dropped="all listed events", n=len(chosen), mz_b=point_estimate(chosen, [IV], IV), har_iv_b=point_estimate(chosen, HAR + [IV], IV)))
    return pd.DataFrame(rows)


def debate_reconciliation(panel: pd.DataFrame) -> pd.DataFrame:
    """Try the plausible debate rules against the debate numbers. The plan does not record the rules, so this cannot confirm one."""
    def fit(frame: pd.DataFrame, y: str, x: str) -> float:
        return float(inf.ols(frame[y].to_numpy(dtype=float), np.column_stack([np.ones(len(frame)), frame[x].to_numpy(dtype=float)]))["beta"][1])

    work = panel.assign(iv2=panel["atm30"] ** 2)
    price = rz.forward_realized(panel[["session_date", "return_total", "return_overnight", "return_intraday"]].assign(return_total=panel["return_price"]))
    work["rv30_price"], work["rv21_price"] = price["rv30"], price["rv21"]
    for name in ("rv30_price", "rv21_price"):
        work[f"log_{name}"] = np.log(work[name])
    last_day = {"to 2024": "2024-12-31", "to 2025": "2025-12-31", "all": "2026-12-31"}
    targets = {"rv30 total return": "rv30", "rv21 total return": "rv21", "rv30 price return": "rv30_price", "rv21 price return": "rv21_price"}
    rows = []
    for period, last in last_day.items():
        for target_label, target in targets.items():
            for tier_label, tier_mask in (("all tiers", work["tier"].notna()), ("Tier 1", work["tier"] == 1)):
                y_log = "log_rv30" if target == "rv30" else "log_rv21" if target == "rv21" else f"log_{target}"
                chosen = work[(work["session_date"] <= last) & work["atm30"].notna() & work[target].notna() & tier_mask]
                calm = chosen[~((chosen["session_date"] < PASO_SESSION) & (chosen["window_end"] >= PASO_SESSION))]
                year = chosen[chosen["year"] == 2024]
                rows.append(dict(sample_end=period, target=target_label, tier=tier_label, n=len(chosen), log_b=fit(chosen, y_log, IV), log_b_no_paso=fit(calm, y_log, IV), log_b_2024=fit(year, y_log, IV), level_b=fit(chosen, target, "iv2"), level_b_no_paso=fit(calm, target, "iv2"), share_iv_above=float((chosen["iv2"] > chosen[target]).mean())))
    return pd.DataFrame(rows)


def add_forecasts(panel: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    out = panel.copy()
    returns = out["return_total"].to_numpy()
    sessions = out["window_sessions"].to_numpy()
    out["f_ewma_raw"] = fc.ewma_forecasts(returns, sessions)
    garch, fits = fc.garch_forecasts(returns, sessions)
    garch_t, fits_t = fc.garch_forecasts(returns, sessions, dist="t")
    fits = pd.concat([fits.assign(dist="normal"), fits_t.assign(dist="t")], ignore_index=True)
    out["f_garch_raw"], out["f_garch_t_raw"] = garch, garch_t
    out["log_garch_t"] = np.log(out["f_garch_t_raw"])
    out["f_atm_raw"] = out["atm30"] ** 2
    out["log_ewma"], out["log_garch"] = np.log(out["f_ewma_raw"]), np.log(out["f_garch_raw"])

    # Raw race: the first origin is session 252. The fitted models train on the days with ATM30.
    raw_mask = out["primary"].to_numpy() & (out["position"].to_numpy() >= fc.START_SESSIONS)
    raw_train = out["primary"].to_numpy()
    out["f_har"] = fc.expanding_forecasts(out, HAR, raw_train, raw_mask)
    out["f_har_atm"] = fc.expanding_forecasts(out, HAR + [IV], raw_train, raw_mask)

    # Calibrated race: each model has its own log regression, on one common set of training days.
    common = out["primary"].to_numpy() & out["log_garch"].notna().to_numpy() & out["log_garch_t"].notna().to_numpy() & out["log_ewma"].notna().to_numpy()
    for name, inputs in (("atm", [IV]), ("ewma", ["log_ewma"]), ("garch", ["log_garch"]), ("garch_t", ["log_garch_t"]), ("har", HAR), ("har_atm", HAR + [IV])):
        out[f"c_{name}"] = fc.expanding_forecasts(out, inputs, common, common)
        out[f"m_{name}"] = fc.expanding_forecasts(out, inputs, common, common, smearing=False)
    return out, fits


RAW_MODELS = {"ATM30 raw": "f_atm_raw", "EWMA raw": "f_ewma_raw", "GARCH raw": "f_garch_raw", "GARCH t raw": "f_garch_t_raw", "HAR": "f_har", "HAR+ATM30": "f_har_atm"}
CAL_MODELS = {"ATM30": "c_atm", "EWMA": "c_ewma", "GARCH": "c_garch", "GARCH t": "c_garch_t", "HAR": "c_har", "HAR+ATM30": "c_har_atm"}
NO_SMEAR_MODELS = {"ATM30": "m_atm", "EWMA": "m_ewma", "GARCH": "m_garch", "GARCH t": "m_garch_t", "HAR": "m_har", "HAR+ATM30": "m_har_atm"}


def race_table(panel: pd.DataFrame, models: dict[str, str], benchmark: str, race: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    columns = list(models.values())
    scored = panel.dropna(subset=columns + ["rv30"])
    target = scored["rv30"].to_numpy()
    losses = {("qlike", name): fc.qlike(target, scored[col].to_numpy()) for name, col in models.items()}
    losses.update({("mse", name): fc.squared_error(target, scored[col].to_numpy()) for name, col in models.items()})
    level_rows, diff_rows = [], []
    pairs = [(name, benchmark) for name in models if name != benchmark]
    if ("HAR+ATM30", "HAR") not in pairs:
        pairs.append(("HAR+ATM30", "HAR"))
    for period in ["all", NO_PASO, *PERIODS]:
        chosen = period_rows(scored, period)
        if chosen.empty:
            continue
        where = scored.index.get_indexer(chosen.index)
        positions = chosen["position"].to_numpy()
        for name in models:
            level_rows.append(dict(race=race, period=period, model=name, n=len(chosen), first=chosen["session_date"].iloc[0].date(), qlike=losses[("qlike", name)][where].mean(), mse=losses[("mse", name)][where].mean(), mean_forecast=scored[models[name]].iloc[where].mean(), mean_target=target[where].mean()))
        for name, other in pairs:
            for metric in ("qlike", "mse"):
                difference = losses[(metric, name)][where] - losses[(metric, other)][where]
                row = dict(race=race, period=period, metric=metric, model=name, against=other, n=len(chosen), mean_difference=difference.mean())
                for block in BLOCKS if period in ("all", NO_PASO) else (21,):
                    if block * 3 > positions[-1] - positions[0] + 1:
                        continue
                    draws = inf.block_bootstrap(lambda index: np.array([difference[index].mean()]), positions, block, REPS, SEED + block)
                    summary = inf.bootstrap_summary(np.array([difference.mean()]), draws)
                    row.update({f"boot{block}_t": summary["t"][0], f"boot{block}_low": summary["low"][0], f"boot{block}_high": summary["high"][0]})
                diff_rows.append(row)
    return pd.DataFrame(level_rows), pd.DataFrame(diff_rows)


def descriptive_tables(panel: pd.DataFrame) -> dict[str, pd.DataFrame]:
    sample = panel[panel["primary"]].copy()
    sample["vrp_var"] = sample["atm30"] ** 2 - sample["rv30"]
    sample["vrp_vol"] = sample["atm30"] - np.sqrt(sample["rv30"])
    sample["iv_above_rv"] = sample["vrp_var"] > 0
    rows = []
    for period in ["all", *PERIODS]:
        chosen = period_rows(sample, period)
        rows.append(dict(period=period, n=len(chosen), mean_iv2=chosen["atm30"].pow(2).mean(), mean_rv=chosen["rv30"].mean(), mean_vrp_var=chosen["vrp_var"].mean(), median_vrp_var=chosen["vrp_var"].median(), mean_vrp_vol=chosen["vrp_vol"].mean(), median_vrp_vol=chosen["vrp_vol"].median(), share_iv_above_rv=chosen["iv_above_rv"].mean()))
    vrp = pd.DataFrame(rows)

    # Level form: appendix only.
    level_rows = []
    for period in ["all", *PERIODS]:
        chosen = period_rows(sample, period)
        fit = inf.ols(chosen["rv30"].to_numpy(), np.column_stack([np.ones(len(chosen)), chosen["atm30"].to_numpy() ** 2]))
        level_rows.append(dict(period=period, n=len(chosen), a=fit["beta"][0], b=fit["beta"][1], r2=fit["r2"]))
    without = sample[~((sample["session_date"] < "2019-08-12") & (sample["window_end"] >= "2019-08-12"))]
    fit = inf.ols(without["rv30"].to_numpy(), np.column_stack([np.ones(len(without)), without["atm30"].to_numpy() ** 2]))
    level_rows.append(dict(period="all, no 2019-08-12 windows", n=len(without), a=fit["beta"][0], b=fit["beta"][1], r2=fit["r2"]))
    level = pd.DataFrame(level_rows)

    split_rows = []
    known = panel.dropna(subset=["rv30"])
    for period in ["all", *PERIODS]:
        chosen = period_rows(known, period)
        parts = chosen["rv30_overnight"].sum() + chosen["rv30_intraday"].sum()
        split_rows.append(dict(period=period, n=len(chosen), overnight_share=chosen["rv30_overnight"].sum() / parts, intraday_share=chosen["rv30_intraday"].sum() / parts, sum_parts_to_rv=parts / chosen["rv30"].sum()))
    split = pd.DataFrame(split_rows)

    known = known.assign(has_iv=known["atm30"].notna(), near_bucket=pd.cut(known["near_days"], [-1, 7, 14, 21, 30.01], right=False, labels=["0-6", "7-13", "14-20", "21-30"]))
    selection = known.groupby("has_iv").agg(n=("rv30", "size"), mean_log_rv30=("log_rv30", "mean"), mean_abs_same_day_return=("return_total", lambda s: s.abs().mean())).reset_index()
    bucket = known.groupby("near_bucket", observed=True).agg(n=("rv30", "size"), coverage=("has_iv", "mean"), mean_log_rv30=("log_rv30", "mean")).reset_index()
    har_days = known.dropna(subset=HAR)
    selection_fit = []
    for label, chosen in (("all days", har_days), ("days with ATM30", har_days[har_days["has_iv"]]), ("days without ATM30", har_days[~har_days["has_iv"]])):
        fit = inf.ols(chosen["log_rv30"].to_numpy(), design(chosen, HAR))
        selection_fit.append(dict(sample=label, n=len(chosen), **dict(zip(["const"] + HAR, fit["beta"])), r2=fit["r2"]))

    mf = panel[(panel["session_date"] >= "2024-01-01") & panel["mf30"].notna() & panel["atm30"].notna()]
    mf_table = mf.groupby("year").agg(n=("mf30", "size"), median_atm30=("atm30", "median"), median_mf30=("mf30", "median"), median_extrapolated=("mf_extrapolated_share", "median")).reset_index()
    mf_table["median_atm_over_mf"] = mf.groupby("year").apply(lambda f: (f["atm30"] / f["mf30"]).median(), include_groups=False).to_numpy()
    return dict(debate=debate_reconciliation(panel), vrp=vrp, level=level, split=split, selection=selection, selection_bucket=bucket, selection_fit=pd.DataFrame(selection_fit), mf30=mf_table)


def export_eviews(panel: pd.DataFrame) -> None:
    columns = ["session_date", "rv30", "log_rv30", "log_rv21", "atm30", IV] + HAR + ["log_iv2_lag1", "log_iv2_lag5", "primary", "tier", "relative_spread", "flag_ex_in_front", "flag_front_under_7d", "flag_rights_in_bracket", "flag_option_degraded", "flag_equity_degraded", "year"]
    out = panel[columns].copy()
    for name in ["primary"] + [c for c in columns if c.startswith("flag_")]:
        out[name] = out[name].astype(bool).astype(int)
    out["session_date"] = out["session_date"].dt.strftime("%Y-%m-%d")
    out.to_csv(REPORTS / "eviews_regressions.csv", index=False)


def markdown(frame: pd.DataFrame, digits: int = 3) -> str:
    table = frame.copy()
    for column in table.columns:
        if pd.api.types.is_datetime64_any_dtype(table[column]):
            table[column] = table[column].dt.strftime("%Y-%m-%d")
        elif pd.api.types.is_float_dtype(table[column]):
            table[column] = table[column].map(lambda v: "" if pd.isna(v) else f"{v:.{digits}f}")
    lines = ["| " + " | ".join(map(str, table.columns)) + " |", "|" + "---|" * len(table.columns)]
    lines += ["| " + " | ".join(map(str, row)) + " |" for row in table.itertuples(index=False)]
    return "\n".join(lines)


def iv_coefficient_view(primary: pd.DataFrame) -> pd.DataFrame:
    keep = ["period", "spec", "coefficient", "n", "estimate", "boot21_t", "boot21_low", "boot21_high", "boot63_t", "boot63_low", "boot63_high", "nw_t", "r2"]
    return primary.reindex(columns=keep)


def write_report(panel, primary, yearly, offsets, sensitivity, leave_out, levels, differences, event_rows, placebo_rows, tables, fits) -> str:
    sample = panel[panel["primary"]]
    view = iv_coefficient_view(primary)
    har_iv = view[(view["spec"] == "HAR+IV")]
    mz = view[(view["spec"] == "MZ") & (view["coefficient"] == IV)]
    r2 = primary[primary["coefficient"] == "const"].pivot(index="period", columns="spec", values="r2").reindex(["all", *PERIODS]).reset_index()
    r2["delta_r2"] = r2["HAR+IV"] - r2["HAR"]
    offset_summary = offsets.groupby("spec").agg(samples=("n", "size"), distinct_samples=("sample_id", "nunique"), median_n=("n", "median"), median_b=("coefficient", "median"), min_b=("coefficient", "min"), max_b=("coefficient", "max"), median_t=("classical_t", "median"), share_t_above_2=("classical_t", lambda s: (s > 2).mean())).reset_index()
    year_iv = yearly[yearly["coefficient"] == IV].pivot(index="year", columns="spec", values="estimate").reset_index()
    year_t = yearly[(yearly["coefficient"] == IV) & (yearly["spec"] == "HAR+IV")].set_index("year")
    year_iv["n"] = year_iv["year"].map(year_t["n"])
    year_iv["har_iv_boot21_t"] = year_iv["year"].map(year_t["boot21_t"]) if "boot21_t" in year_t else np.nan
    failures = int((fits["reason"] != "").sum())
    debate_2024 = float(year_iv.loc[year_iv["year"] == 2024, "MZ"].iloc[0])
    pooled = float(mz.loc[mz["period"] == "all", "estimate"].iloc[0])
    event_columns = ["event", "event_session", "first_return", "observed", "near_expiry", "far_expiry", "near_days", "gap_days", "tier", "near_vol", "forward_vol", "ratio", "realized_vol_between", "placebo_count", "placebo_median_ratio", "share_placebos_below"]
    text = f"""# Stage 3: development results

All results are exploratory. This run read 2018-05-01 to 2026-10-29, and the 2016-01 to 2018-04 test stays locked. No verdict rule exists until Stage 4. `{len(sample)}` origins are in the primary sample, from {sample["session_date"].min().date()} to {sample["session_date"].max().date()}.

## Primary question: does log `ATM30` add information beyond log RV over 1, 5, and 22 sessions?

The target is log RV over the next 30 calendar days. All models use identical dates. `{IV}` is log `ATM30` squared. Newey-West (`nw_t`, {NW_LAGS} lags) is for comparison only. Bootstrap: {REPS} resamples. `boot63` is blank when fewer than three blocks fit.

### Coefficients in the HAR+IV regression

{markdown(har_iv.drop(columns="spec"))}

### Fit

{markdown(r2)}

### Non-overlapping samples across 21 offsets

Each sample has no shared returns between target windows, so its classical t fits these rows. The samples share many of the same periods, so they are not independent evidence.

{markdown(offset_summary)}

### By year: coefficient on `{IV}`

{markdown(year_iv)}

About 10 to 12 independent windows exist in each year, so these estimates are weak.

## Mincer-Zarnowitz in logs (reported, not the headline)

{markdown(mz.drop(columns=["spec", "coefficient"]))}

Debate targets: pooled log b near .55, and near .97 in 2024. This study has {pooled:.3f} and {debate_2024:.3f}.

### Reconciliation with the debate numbers

The debate numbers are: log b .55 pooled, .58 and .57 without 2019-08-12, .97 in 2024, level b .79 and .22 without 2019-08-12, and implied variance above RV in 79% of observations. The plan does not record the debate rules, so this table can show only which rules come close. `no_paso` drops each origin with 2019-08-12 in its window.

{markdown(tables["debate"])}

## Sensitivity runs of the coefficient on IV in the HAR regression

{markdown(sensitivity.drop(columns=["r2_har", "r2_full"]))}

## Leave-out estimates

Dropping an event drops each origin with that event in its 30-day window. So the event leaves both the IV and the RV.

{markdown(leave_out)}

## Forecast race

The target is `rv30`, the variance level. QLIKE is primary, and MSE is secondary. A training row needs a target window that ends on or before the origin. All models in one race use identical dates.

- **Raw race:** The first origin is session {fc.START_SESSIONS}. `ATM30`, EWMA, and GARCH have no calibration. So `ATM30` carries the variance risk premium, and EWMA and GARCH do not.
- **Calibrated race:** Each model has an expanding log regression with a smearing factor, on one common set of training days. It needs {fc.MIN_TRAINING_ROWS} training rows, so it starts later than the raw race.
- **Calibrated, no smearing:** This race is the same, without the smearing factor. The factor returns the mean level of the training target, so the 2019 windows can inflate it.
- **`{NO_PASO}`:** This period drops each scored origin with 2019-08-12 in its target window. Training rows do not change.

GARCH refits every {fc.GARCH_REFIT_SESSIONS} sessions. {len(fits)} fits ran across normal and t errors, and {failures} failed. A failed fit keeps the prior parameters. With normal errors, the -0.82 return of 2019-08-12 sets the fit for years: `alpha` is near .9 and `beta` is near 0 just after it. So the race also has GARCH with t errors.

### Loss levels

{markdown(levels, 4)}

### Loss differences

A negative value means that `model` has the lower loss.

{markdown(differences, 4)}

## Variance risk premium

{markdown(tables["vrp"], 4)}

## Argentina events: forward variance between the expiries that straddle each event

These are case studies, with placebo dates and no p-values. `ratio` is the forward vol over the near-term vol. `share_placebos_below` is the share of placebo ratios below the event ratio. Each placebo date is a multiple of 28 days from the event, has a similar expiry gap, and has no listed event in its pair. Other shocks can be in the placebos.

{markdown(event_rows.reindex(columns=event_columns))}

## Selection: missing `ATM30` days

{markdown(tables["selection"], 4)}

{markdown(tables["selection_bucket"])}

HAR on all days and on each group:

{markdown(tables["selection_fit"])}

## Overnight and open-to-close split of RV

{markdown(tables["split"])}

Cash goes in the overnight part. The two parts do not sum to RV, because each part is squared separately and the cross term between them is left out. `sum_parts_to_rv` shows the size of this gap.

## `MF30` (descriptive only)

{markdown(tables["mf30"])}

## Appendix: level form

The plan expects the level b to depend on 2019-08-12.

{markdown(tables["level"], 4)}
"""
    (REPORTS / "stage3_results.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    panel = build_panel()
    print(f"primary sample: {int(panel['primary'].sum())} origins", flush=True)
    primary, yearly, offsets = primary_tables(panel)
    print("primary tables done", flush=True)
    sensitivity = sensitivity_table(panel)
    print("sensitivity done", flush=True)
    leave_out = leave_out_tables(panel)
    panel, fits = add_forecasts(panel)
    print("forecasts done", flush=True)
    raw_levels, raw_differences = race_table(panel, RAW_MODELS, "ATM30 raw", "raw")
    cal_levels, cal_differences = race_table(panel, CAL_MODELS, "ATM30", "calibrated")
    median_levels, median_differences = race_table(panel, NO_SMEAR_MODELS, "ATM30", "calibrated, no smearing")
    levels = pd.concat([raw_levels, cal_levels, median_levels], ignore_index=True)
    differences = pd.concat([raw_differences, cal_differences, median_differences], ignore_index=True)
    print("race done", flush=True)
    event_rows, placebo_rows = ev.event_table(pd.read_parquet(DATA / "atm_terms.parquet"), panel)
    tables = descriptive_tables(panel)

    for name, frame in dict(primary=primary, yearly=yearly, offsets=offsets, sensitivity=sensitivity, leave_out=leave_out, race_levels=levels, race_differences=differences, events=event_rows, placebos=placebo_rows, garch_fits=fits, **tables).items():
        frame.to_csv(REPORTS / f"stage3_{name}.csv", index=False)
    export_eviews(panel)
    panel.to_parquet(DATA / "forecast_panel.parquet", index=False)
    print(write_report(panel, primary, yearly, offsets, sensitivity, leave_out, levels, differences, event_rows, placebo_rows, tables, fits))
    print(report_stage4.write(panel))


if __name__ == "__main__":
    main()
