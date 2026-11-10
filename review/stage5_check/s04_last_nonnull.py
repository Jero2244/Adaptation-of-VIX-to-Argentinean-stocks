"""build_snapshot.last_quotes uses groupby.last(), which takes the last NON-NULL value per column. PROTOCOL says "last quote per contract".
Part 1 shows this on a synthetic frame. Part 2 rebuilds ATM30 on open dates with a strict last row, and compares. Open dates only."""
import _common
from _common import ROOT, HERE
import numpy as np, pandas as pd
import build_snapshot as bs
from build_series import session_rates, series_tables
from load_data import day_conditions
from config import OPTION_CBBO
NY = "America/New_York"
t = lambda s: pd.Timestamp(f"2019-03-04 {s}", tz=NY)
f = pd.DataFrame(dict(instrument_id=[1,1], ts_recv=[t("10:00"), t("15:44")], bid_px_00=[1.0, np.nan], ask_px_00=[1.2, 3.0], bid_sz_00=[5,0], ask_sz_00=[5,5]))
print("PART 1 input\n", f.drop(columns=["bid_sz_00","ask_sz_00"]).to_string())
print("frozen last_quotes\n", bs.last_quotes(f, "2019-03-04")[["instrument_id","ts_recv","bid_px_00","ask_px_00","age"]].to_string())

frozen_lq = bs.last_quotes
stats = []
def strict_lq(frame, day):
    opening, cutoff = pd.Timestamp(f"{day} 09:30", tz=NY), pd.Timestamp(f"{day} 15:45", tz=NY)
    inside = frame[(frame["ts_recv"]>=opening)&(frame["ts_recv"]<=cutoff)]
    last = inside.sort_values("ts_recv", kind="stable").groupby("instrument_id", as_index=False).tail(1).reset_index(drop=True)
    last["age"] = (cutoff-last["ts_recv"]).dt.total_seconds()/60
    stats.append(dict(day=pd.Timestamp(day), n=len(last), bid_null=int(last["bid_px_00"].isna().sum()), ask_null=int(last["ask_px_00"].isna().sum())))
    return last

START, END = "2018-05-01", "2026-10-29"
def build(fn):
    bs.last_quotes = fn
    snap, listed, diag = bs.snapshot_tables(START, END, None, use_equity=False, progress=False)
    diag = diag.set_index("session_date")
    rates = session_rates(diag.index.sort_values())
    e = np.array([], dtype="datetime64[ns]")
    s, _, _ = series_tables(snap, listed, diag, rates, e, e, day_conditions(OPTION_CBBO), {})
    return s
a = build(frozen_lq); b = build(strict_lq)
st = pd.DataFrame(stats); st["year"] = st.day.dt.year
print("share of last rows at or before 15:45 with null bid or ask, by year")
print(st.groupby("year")[["n","bid_null","ask_null"]].sum().assign(bid_share=lambda d:d.bid_null/d.n, ask_share=lambda d:d.ask_null/d.n).round(4).to_string())
j = a[["session_date","atm30","tier"]].merge(b[["session_date","atm30","tier"]], on="session_date", suffixes=("_frozen","_strict"))
j["year"] = j.session_date.dt.year
j["both"] = j.atm30_frozen.notna()&j.atm30_strict.notna()
j["changed"] = j.both & (np.log(j.atm30_frozen/j.atm30_strict).abs()>1e-9)
j["abs_log"] = np.log(j.atm30_frozen/j.atm30_strict).abs()
g = j.groupby("year").agg(sessions=("atm30_frozen","size"), frozen=("atm30_frozen","count"), strict=("atm30_strict","count"), changed=("changed","sum"), median_abs_log_changed=("abs_log", lambda s: s[s>1e-9].median()), max_abs_log=("abs_log","max"))
print(g.round(4).to_string())
print("tier1 frozen, strict:", int((j.tier_frozen==1).sum()), int((j.tier_strict==1).sum()))
p = pd.read_parquet(ROOT/"data/forecast_panel.parquet", columns=["session_date","log_rv30","log_rv1","log_rv5","log_rv22","rv30"])
x = p.merge(j[["session_date","atm30_frozen","atm30_strict"]], on="session_date")
pre = x[x.session_date<"2025-03-01"]
for name, frame in (("all",x),("before 2025-03",pre),("2018-05 to 2020-08",x[x.session_date<"2020-09-01"])):
    for col in ("atm30_frozen","atm30_strict"):
        r = frame.dropna(subset=[col,"log_rv30","log_rv1","log_rv5","log_rv22"])
        X = np.column_stack([np.ones(len(r)), r.log_rv1, r.log_rv5, r.log_rv22, np.log(r[col]**2)])
        print(name, col, "n", len(r), "b", round(np.linalg.lstsq(X, r.log_rv30.to_numpy(), rcond=None)[0][4],4))
j.to_parquet(HERE/"s04_atm30_frozen_vs_strict.parquet", index=False)
