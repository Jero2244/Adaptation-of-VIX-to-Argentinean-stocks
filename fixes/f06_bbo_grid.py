"""Fix step 5 (F5), part 1: read the Nasdaq bbo-1m quotes and keep a 1-minute grid of mid and relative spread for 09:30 to 16:00 New York.

For each grid time t, the value is the last valid quote row with ts_recv <= t (a valid row has 0 < bid <= ask, no nulls). The file is update-only,
so a grid point can carry a quote that is minutes old. The age of that quote in minutes is kept. DEVELOPMENT work on open data (rawio refuses < 2018-05-01).
Output: fixes/data/bbo_grid.parquet (session_date, minute index 0..390, mid, rel_spread, age_min) and fixes/f06_bbo_rows.csv (row-level stats per day).
"""
from common import *  # noqa
from rawio import read_day

NY = "America/New_York"

if __name__ == "__main__":
    print(LABEL)
    sessions = pd.read_parquet(DATA / "equity_official_daily.parquet").sort_values("session_date").session_date
    out, stats = [], []
    for i, day in enumerate(sessions):
        ds = day.strftime("%Y-%m-%d")
        q = read_day("eq", ds)
        t = q.ts_recv.dt.tz_convert(NY)
        raw_rows = len(q)
        reg = (t >= pd.Timestamp(f"{ds} 09:30", tz=NY)) & (t <= pd.Timestamp(f"{ds} 16:00", tz=NY))
        valid = q.bid_px_00.notna() & q.ask_px_00.notna() & (q.bid_px_00 > 0) & (q.ask_px_00 >= q.bid_px_00)
        crossed = int((q.bid_px_00 > q.ask_px_00).sum())
        v = q[valid].assign(t=t[valid]).sort_values("t", kind="stable")
        grid = pd.date_range(f"{ds} 09:30", f"{ds} 16:00", freq="1min", tz=NY)
        tv = v.t.astype("int64").to_numpy() if len(v) else np.array([], dtype="int64")
        idx = np.searchsorted(tv, grid.astype("int64").to_numpy(), side="right") - 1
        ok = idx >= 0
        bid = np.where(ok, v.bid_px_00.to_numpy()[np.clip(idx, 0, None)] if len(v) else np.nan, np.nan)
        ask = np.where(ok, v.ask_px_00.to_numpy()[np.clip(idx, 0, None)] if len(v) else np.nan, np.nan)
        age = np.where(ok, (grid.astype("int64").to_numpy() - (tv[np.clip(idx, 0, None)] if len(v) else 0)) / 6e10, np.nan)
        mid = (bid + ask) / 2
        out.append(pd.DataFrame(dict(session_date=day, minute=np.arange(len(grid)), mid=mid, rel_spread=(ask - bid) / mid, age_min=age)))
        stats.append(dict(session_date=day, rows=raw_rows, rows_regular=int(reg.sum()), null_rows=int((q.bid_px_00.isna() | q.ask_px_00.isna()).sum()), crossed=crossed, zero_bid=int((q.bid_px_00 == 0).sum()),
                          first_quote=t.min().strftime("%H:%M"), last_quote=t.max().strftime("%H:%M")))
        if (i + 1) % 200 == 0:
            print(i + 1, "days", flush=True)
    pd.concat(out, ignore_index=True).to_parquet(FDATA / "bbo_grid.parquet", index=False)
    pd.DataFrame(stats).to_csv(HERE / "f06_bbo_rows.csv", index=False)
    print("done", len(sessions))
