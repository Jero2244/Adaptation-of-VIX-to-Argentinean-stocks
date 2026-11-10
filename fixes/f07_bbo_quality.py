"""Fix step 5 (F5, F19), part 2: data-quality check of the Nasdaq bbo-1m mids BEFORE any realized variance is built. DEVELOPMENT work on open data."""
from common import *  # noqa

if __name__ == "__main__":
    print(LABEL)
    rows = pd.read_csv(HERE / "f06_bbo_rows.csv", parse_dates=["session_date"])
    g = pd.read_parquet(FDATA / "bbo_grid.parquet")
    g["year"] = g.session_date.dt.year
    daily = pd.read_parquet(DATA / "equity_official_daily.parquet").sort_values("session_date")
    print("sessions", rows.session_date.nunique(), " rows per day (median)", rows.rows.median(), " regular-session rows per day (median)", rows.rows_regular.median(),
          " min", rows.rows_regular.min())
    print("null-price rows:", int(rows.null_rows.sum()), " zero-bid rows:", int(rows.zero_bid.sum()), " crossed rows:", int(rows.crossed.sum()))
    print("days with fewer than 100 regular rows:", int((rows.rows_regular < 100).sum()))
    print("\n=== grid points 09:30-16:00 (391 per day)")
    reg = g[(g.minute >= 5)]
    print("share with no valid quote yet:", float(g.mid.isna().mean()))
    print("quote age in minutes at grid points: median %.1f, p90 %.1f, p99 %.1f, share older than 5 min %.3f" % (g.age_min.median(), g.age_min.quantile(.9), g.age_min.quantile(.99), (g.age_min > 5).mean()))
    print("\nrelative spread (ask-bid)/mid at grid points, by year")
    t = g.groupby("year").rel_spread.agg(median="median", p90=lambda s: s.quantile(.9), p99=lambda s: s.quantile(.99), over1pct=lambda s: (s > .01).mean(), over5pct=lambda s: (s > .05).mean(), over10pct=lambda s: (s > .10).mean())
    print(t.round(4).to_string())
    # grids at 5 minutes: minute index 5, 10, ... 390
    five = g[g.minute % 5 == 0].copy()
    five = five.sort_values(["session_date", "minute"])
    five["ret"] = np.log(five.groupby("session_date").mid.transform(lambda s: s / s.shift(1)))
    five["maxspread_pair"] = np.maximum(five.rel_spread, five.groupby("session_date").rel_spread.shift(1))
    r = five.dropna(subset=["ret"])
    print("\n=== 5-minute mid returns:", len(r))
    print("std of 5-min returns (bp): %.1f ; share |ret|>2%%: %.5f, >5%%: %.5f, >10%%: %.5f" % (r.ret.std() * 1e4, (r.ret.abs() > .02).mean(), (r.ret.abs() > .05).mean(), (r.ret.abs() > .10).mean()))
    for cut in (.02, .05, .10):
        big = r[r.ret.abs() > cut]
        print(f"  |ret|>{cut:.0%}: {len(big)} returns; of these, one end has rel spread >5%: {(big.maxspread_pair > .05).mean():.2f}; at the first grid minutes (<=09:40): {(big.minute <= 10).mean():.2f}; at the last (>=15:55): {(big.minute >= 385).mean():.2f}")
    print("\n=== mid against the official prices")
    first = g[g.minute == 0].set_index("session_date").mid
    last = g[g.minute == 390].set_index("session_date").mid
    d = daily.set_index("session_date")
    gap_open = np.log(first / d.official_open_price).dropna()
    gap_close = np.log(last / d.official_close_price).dropna()
    print("log(mid 09:30 / official open): median abs %.4f, p90 %.4f, p99 %.4f" % (gap_open.abs().median(), gap_open.abs().quantile(.9), gap_open.abs().quantile(.99)))
    print("log(mid 16:00 / official close): median abs %.4f, p90 %.4f, p99 %.4f; share >1%% %.3f, >2%% %.3f" % (gap_close.abs().median(), gap_close.abs().quantile(.9), gap_close.abs().quantile(.99), (gap_close.abs() > .01).mean(), (gap_close.abs() > .02).mean()))
    print("by year, median abs gap to the official close:\n", gap_close.abs().groupby(gap_close.index.year).median().round(4).to_string())
    print("\n=== signature plot: mean daily squared mid return summed over the day (annualised x252, vol points), by sampling step, on days with data")
    sig = {}
    for step in (1, 5, 10, 15, 30):
        sub = g[g.minute % step == 0].sort_values(["session_date", "minute"])
        sub = sub.assign(ret=np.log(sub.groupby("session_date").mid.transform(lambda s: s / s.shift(1))))
        rv = (sub.ret ** 2).groupby(sub.session_date).sum(min_count=1)
        sig[step] = rv
    sigdf = pd.DataFrame(sig)
    c = np.log(d.official_close_price).diff()
    print("median daily RV (annualised vol) by step:", {k: round(float(np.sqrt(252 * v.median())), 3) for k, v in sig.items()})
    print("mean daily RV ratio to the 30-minute step:", {k: round(float(v.mean() / sig[30].mean()), 3) for k, v in sig.items()})
    print("lag-1 autocorrelation of 5-min mid returns: %.3f (bid-ask bounce would show negative); 1-min: " % r.ret.autocorr(), end="")
    one = g.sort_values(["session_date", "minute"]).assign(ret=lambda x: np.log(x.groupby("session_date").mid.transform(lambda s: s / s.shift(1)))).ret.dropna()
    print("%.3f" % one.autocorr())
    print("share of 1-minute returns equal to 0: %.3f ; 5-minute: %.3f" % ((one == 0).mean(), (r.ret == 0).mean()))
