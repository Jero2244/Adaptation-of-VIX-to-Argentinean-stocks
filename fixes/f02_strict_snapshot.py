"""Fix step 3 (F7), part 1: strict last-row snapshot for every session where any row has a null bid.

Rule: the last row at or before 15:45 NY (and from 09:30) sets BOTH bid and ask. A null bid stays null, so no older bid is revived.
Sessions with null_bid_share == 0 in data/session_diagnostics.parquet have no null bid in any row, so the strict rule equals the stored
rule there (pandas last() only skips nulls). Those sessions are not re-read. The check on null asks is done on the re-read sessions only.
DEVELOPMENT work on open data. Reads raw quotes on dates >= 2018-05-01 only (rawio refuses earlier dates).
"""
from common import *  # noqa
from a03_reproduce_raw import snapshot  # audit helper, read-only import

if __name__ == "__main__":
    print(LABEL)
    d = pd.read_parquet(DATA / "session_diagnostics.parquet")
    days = [x.strftime("%Y-%m-%d") for x in d.loc[d.null_bid_share > 0, "session_date"]]
    print("sessions to re-read:", len(days), "first", days[0], "last", days[-1])
    frames, info = [], []
    for i, day in enumerate(days):
        snap, _ = snapshot(day, "strict")
        snap = snap.rename(columns={"raw_symbol": "symbol", "bid_sz_00": "bid_size", "ask_sz_00": "ask_size"})
        frames.append(snap.assign(session_date=pd.Timestamp(day)))
        study, _ = snapshot(day, "study"); study = study.rename(columns={"raw_symbol": "symbol"})
        s = snap.set_index("symbol"); t = study.set_index("symbol")
        info.append(dict(session_date=pd.Timestamp(day), instruments=len(s), last_row_null_bid=int(s.bid.isna().sum()), last_row_null_ask=int(s.ask.isna().sum()),
                         revived_bid=int((s.bid.isna() & t.bid.notna().reindex(s.index)).sum()), revived_ask=int((s.ask.isna() & t.ask.notna().reindex(s.index)).sum()),
                         changed_bid=int(((s.bid != t.bid.reindex(s.index)) & s.bid.notna()).sum()), changed_ask=int(((s.ask != t.ask.reindex(s.index)) & s.ask.notna()).sum())))
        if (i + 1) % 50 == 0:
            print(i + 1, "days", flush=True)
    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(FDATA / "strict_snapshot_partial.parquet", index=False)
    inf_df = pd.DataFrame(info)
    inf_df.to_csv(HERE / "f02_strict_snapshot_info.csv", index=False)
    print(inf_df.describe().round(3).to_string())
    print("by period: revived bids per instrument, mean")
    inf_df["post"] = inf_df.session_date >= "2025-03-01"
    print(inf_df.groupby("post").apply(lambda f: pd.Series(dict(days=len(f), revived_bid_share=(f.revived_bid.sum() / f.instruments.sum()), revived_ask=f.revived_ask.sum(), last_row_null_ask=f.last_row_null_ask.sum())), include_groups=False))
