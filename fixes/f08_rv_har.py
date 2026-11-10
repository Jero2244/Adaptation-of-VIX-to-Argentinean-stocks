"""Fix step 4 (F5): a stronger HAR baseline from the Nasdaq bbo-1m mids. DEVELOPMENT work on open data.

Daily realized variance (RVhf) is the sum of squared log-return pieces that partition the close-to-close total return of the study:
  1. previous official close to official open, with the cash of the ex-date (the study's own return_overnight)
  2. official open to the 09:35 mid
  3. 5-minute mid returns, 09:35 to 15:55 (mid = last valid Nasdaq quote at or before the grid time; fixes/data/bbo_grid.parquet)
  4. 15:55 mid to the official close
On early-close days (the study's flag_half_day) the grid ends at 13:00 (last grid mid 12:55). No filter on wide quotes in the primary version.
Sensitivity: replace any grid mid with relative spread > 5% by the last mid with relative spread <= 5% (carry forward).
HAR inputs: log(252 * mean RVhf over 1, 5, 22 sessions), floor 1e-6 on the daily variance, as in realized.trailing_realized.
Targets: (A) log_rv30, the study target from squared close-to-close returns; (B) log_rv30_hf, the same 30-calendar-day window but summed RVhf.
Regression: the study's own (OLS, Newey-West 21, circular block bootstrap, seed SEED + block, 2000 resamples).
"""
from common import *  # noqa


def daily_rv(real: pd.DataFrame, grid: pd.DataFrame, half: set, filtered: bool = False) -> pd.Series:
    mids = grid.pivot(index="session_date", columns="minute", values="mid")
    sprd = grid.pivot(index="session_date", columns="minute", values="rel_spread")
    if filtered:
        mids = mids.where(sprd <= 0.05)
        mids = mids.ffill(axis=1)
    out = {}
    r = real.set_index("session_date")
    for day, row in mids.iterrows():
        end = 210 if day in half else 390
        pts = np.arange(5, end - 4, 5)  # 5, 10, ..., end-5
        m = row.to_numpy()
        pieces = [r.loc[day, "return_overnight"], np.log(m[5] / r.loc[day, "open"])]
        pieces += list(np.diff(np.log(m[pts])))
        pieces += [np.log(r.loc[day, "close"] / m[pts[-1]])]
        pieces = np.array(pieces, dtype=float)
        out[day] = float(np.nansum(pieces ** 2)) if np.isfinite(pieces).all() else np.nan
    return pd.Series(out)


def add_hf(real: pd.DataFrame, rv: pd.Series, floor: float = rz.DAILY_VARIANCE_FLOOR) -> pd.DataFrame:
    out = real.copy()
    out["rv_hf_day"] = out.session_date.map(rv)
    for n in rz.HAR_LENGTHS:
        out[f"hf_rv{n}"] = np.log(rz.SESSIONS_PER_YEAR * out.rv_hf_day.rolling(n, min_periods=n).mean().clip(lower=floor))
    dates = out.session_date.to_numpy()
    last = np.searchsorted(dates, dates + np.timedelta64(30, "D"), side="right")
    complete = dates + np.timedelta64(30, "D") <= dates[-1]
    run = np.concatenate([[0.0], np.cumsum(np.nan_to_num(out.rv_hf_day.to_numpy()))])
    tot = run[last] - run[np.arange(len(dates)) + 1]
    out["log_rv30_hf"] = np.log(np.where(complete, rz.CALENDAR_ANNUAL * tot, np.nan))
    return out


def main():
    print(LABEL)
    real = rz.build_realized()
    grid = pd.read_parquet(FDATA / "bbo_grid.parquet")
    base = pd.read_parquet(DATA / "index_series.parquet")
    half = set(base.loc[base.flag_half_day.fillna(False).astype(bool), "session_date"])
    print("early-close days handled:", len(half))
    rv = daily_rv(real, grid, half)
    rvf = daily_rv(real, grid, half, filtered=True)
    real2 = add_hf(real, rv)
    real2f = add_hf(real, rvf)
    c = real2[["session_date", "rv_hf_day", "return_total"]].dropna()
    print("daily RVhf vs squared close-to-close return: mean ratio %.3f, median ratio %.3f, corr of logs %.3f" % ((c.rv_hf_day / c.return_total ** 2).mean(), (c.rv_hf_day / c.return_total ** 2.0).median(), np.corrcoef(np.log(c.rv_hf_day), np.log(np.maximum(c.return_total ** 2, 1e-8)))[0, 1]))
    print("share of days with RVhf missing:", float(real2.rv_hf_day.isna().mean()), " (first session has no previous close)")
    real2.to_parquet(FDATA / "realized_hf.parquet", index=False)

    rows = []
    for label, series_name, col in (("stored ATM30", "base", "atm30"), ("all four fixes (strict+spread.50+Tier1+7d)", "core", "atm30_floor7")):
        path = FDATA / f"series_{series_name}.parquet"
        if not path.exists():
            print("missing", path.name)
            continue
        ser = pd.read_parquet(path)
        for rname, R in (("RVhf (no filter)", real2), ("RVhf (wide quotes carried over)", real2f)):
            panel = make_panel(ser, R, col)
            panel = panel.assign(**{k: panel[k] for k in ()})
            p = panel[panel.primary & panel[["hf_rv1", "hf_rv5", "hf_rv22", "log_rv30_hf"]].notna().all(axis=1)]
            for target in ("log_rv30", "log_rv30_hf"):
                y = p[target].to_numpy()
                old_names, new_names = HAR, ["hf_rv1", "hf_rv5", "hf_rv22"]

                def r2(names):
                    X = np.column_stack([np.ones(len(p))] + [p[n].to_numpy() for n in names])
                    return inf.ols(y, X)["r2"]

                for hlabel, hnames in (("HAR old (squared daily returns)", old_names), ("HAR new (bbo-1m RV)", new_names)):
                    fit = fit_b(p, names=hnames + [IV], y_name=target, reps=2000 if rname.startswith("RVhf (no") else 0)
                    rows.append(dict(iv_series=label, rv_version=rname, target=target, baseline=hlabel, n=len(p), r2_har=r2(hnames), r2_har_iv=fit["r2"], b=fit["b"], nw_t=fit["nw_t"],
                                     boot21_low=fit.get("boot21_low"), boot21_high=fit.get("boot21_high"), boot63_low=fit.get("boot63_low"), boot63_high=fit.get("boot63_high"),
                                     boot21_t=fit.get("boot21_t"), boot63_t=fit.get("boot63_t")))
    t = pd.DataFrame(rows)
    t.to_csv(HERE / "f08_rv_har.csv", index=False)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")
    print(t.to_string(index=False))
    # HAR coefficients
    p = make_panel(pd.read_parquet(FDATA / "series_base.parquet"), real2, "atm30")
    p = p[p.primary]
    for hlabel, names in (("old", HAR), ("new", ["hf_rv1", "hf_rv5", "hf_rv22"])):
        X = np.column_stack([np.ones(len(p))] + [p[n].to_numpy() for n in names])
        f = inf.ols(p.log_rv30.to_numpy(), X)
        print("HAR", hlabel, "coefficients (const, 1, 5, 22):", np.round(f["beta"], 3), " R2", round(f["r2"], 3))


if __name__ == "__main__":
    main()
