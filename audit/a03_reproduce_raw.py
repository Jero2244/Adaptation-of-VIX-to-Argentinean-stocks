"""Audit step 3: rebuild ATM30 from the raw Databento quotes with independent code, and compare with the stored series.

Independent parts: zip read, 15:45 snapshot, pairing, parity forward, Black inversion (scipy brentq on the discounted price),
strike and term interpolation, rate rule. Two snapshot rules are run:
  'study'  = last NON-NULL value of each column per instrument (what build_snapshot.last_quotes does)
  'strict' = the last ROW per instrument (a null bid stays null, so the quote is not two-sided)
Usage: python a03_reproduce_raw.py samples      -> a fixed list of sample days, with detail
       python a03_reproduce_raw.py postbreak    -> every session from 2025-03-01 (the format with null bids)
Open dates only. Writes audit/a03_*.csv.
"""
import sys
from math import exp, log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import brentq
from scipy.stats import norm

from rawio import ROOT, parse_osi, read_day

NY = "America/New_York"
OUT = Path(__file__).resolve().parent
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300)
YEAR_MIN = 365 * 1440
SAMPLES = ["2018-06-01", "2018-12-24", "2019-08-09", "2019-08-12", "2020-03-16", "2021-06-15", "2022-03-15", "2022-07-08", "2023-05-30", "2024-06-03",
           "2024-06-18", "2024-06-21", "2025-02-14", "2025-06-02", "2025-10-24", "2026-03-10", "2026-09-15"]

_rates = pd.read_csv(ROOT / "data" / "source" / "fred_rates.csv", parse_dates=["observation_date"], index_col="observation_date").apply(pd.to_numeric, errors="coerce").dropna(how="all").ffill()


def rate(day: pd.Timestamp, days: float) -> float:
    prior = _rates[_rates.index < day].iloc[-1]  # last observation before the session
    r1, r3 = np.log1p(prior["DGS1MO"] / 100), np.log1p(prior["DGS3MO"] / 100)
    w = min(max((days - 30) / 61, 0), 1)
    return float((1 - w) * r1 + w * r3)


def snapshot(day: str, rule: str) -> pd.DataFrame:
    q = read_day("cbbo", day)
    d = read_day("defs", day).sort_values("ts_recv").drop_duplicates("instrument_id", keep="last")
    lo, hi = pd.Timestamp(f"{day} 09:30", tz=NY), pd.Timestamp(f"{day} 15:45", tz=NY)
    q = q[(q.ts_recv >= lo) & (q.ts_recv <= hi)].sort_values("ts_recv", kind="stable")
    if rule == "study":
        last = q.groupby("instrument_id", as_index=False).last()  # pandas: last non-null per column
    else:
        last = q.drop_duplicates("instrument_id", keep="last")
    last = last.assign(age=(hi - last.ts_recv).dt.total_seconds() / 60)
    m = last.merge(d[["instrument_id", "raw_symbol"]], on="instrument_id", how="inner")
    parsed = [parse_osi(s) for s in m.raw_symbol]
    m["root"], m["expiry"], m["right"], m["strike"] = zip(*parsed)
    m = m[m.root == "GGAL"]
    return m[["raw_symbol", "expiry", "right", "strike", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00", "age"]].rename(columns={"bid_px_00": "bid", "ask_px_00": "ask"}), sorted(set(parse_osi(s)[1] for s in d.raw_symbol if parse_osi(s)[0] == "GGAL"))


def iv_from_average(avg_price, F, K, T, r):
    """sigma such that exp(-rT) * [BlackCall(F,K) + (K-F)/2] = avg_price."""
    def f(s):
        tv = s * sqrt(T)
        d1 = log(F / K) / tv + tv / 2
        return exp(-r * T) * (F * norm.cdf(d1) - K * norm.cdf(d1 - tv) + (K - F) / 2) - avg_price
    if avg_price <= exp(-r * T) * abs(F - K) / 2:
        return None
    try:
        return brentq(f, 1e-6, 100.0, xtol=1e-12)
    except ValueError:
        return None


def term(chain, minutes, r):
    T = minutes / YEAR_MIN
    v = chain[(chain.bid > 0) & (chain.ask >= chain.bid) & (chain.age <= 30)]
    c = v[v.right == "C"].set_index("strike")
    p = v[v.right == "P"].set_index("strike")
    ks = sorted(set(c.index) & set(p.index))
    if not ks:
        return None
    cm = (c.bid + c.ask) / 2
    pm = (p.bid + p.ask) / 2
    kstar = min(ks, key=lambda k: abs(cm[k] - pm[k]))
    F = kstar + exp(r * T) * (cm[kstar] - pm[kstar])
    lowers = [k for k in ks if k <= F]
    uppers = [k for k in ks if k >= F]
    use = []
    if lowers:
        use.append(lowers[-1])
    if uppers and uppers[0] not in use:
        use.append(uppers[0])
    use = [k for k in use if abs(log(k / F)) <= 0.25]
    sol = [(k, iv_from_average((cm[k] + pm[k]) / 2, F, k, T, r)) for k in use]
    sol = [(k, s) for k, s in sol if s is not None]
    if not sol:
        return None
    if len(sol) == 2:
        (k1, s1), (k2, s2) = sol
        iv = s1 + (log(F / k1) / log(k2 / k1)) * (s2 - s1)
    else:
        iv = sol[0][1]
    detail = [(k, float(c.bid[k]), float(c.ask[k]), float(p.bid[k]), float(p.ask[k]), round(s, 4)) for k, s in sol]
    return dict(F=F, iv=iv, pairs=len(ks), detail=detail, minutes=minutes)


def atm30(day: str, rule: str, verbose=False):
    snap, expiries = snapshot(day, rule)
    start = pd.Timestamp(f"{day} 15:45", tz=NY)
    mins = {e: int((pd.Timestamp(f"{e.date()} 16:00", tz=NY) - start).total_seconds() // 60) for e in expiries}
    live = sorted((m, e) for e, m in mins.items() if m > 0)
    near = [e for m, e in live if m <= 43200]
    far = [e for m, e in live if m > 43200]
    if not near or not far:
        return dict(value=np.nan, why="no bracket"), snap
    en, ef = near[-1], far[0]
    tn = term(snap[snap.expiry == en], mins[en], rate(pd.Timestamp(day), mins[en] / 1440))
    tf = term(snap[snap.expiry == ef], mins[ef], rate(pd.Timestamp(day), mins[ef] / 1440))
    if verbose:
        print(f"   [{rule}] near {en.date()} {mins[en]/1440:.2f}d: {tn and {k: tn[k] for k in ('F','iv','pairs','detail')}}")
        print(f"   [{rule}] far  {ef.date()} {mins[ef]/1440:.2f}d: {tf and {k: tf[k] for k in ('F','iv','pairs','detail')}}")
    if tn is None or tf is None:
        return dict(value=np.nan, why="near fails" if tn is None else "far fails"), snap
    w = (mins[ef] - 43200) / (mins[ef] - mins[en])
    var = (w * mins[en] * tn["iv"] ** 2 + (1 - w) * mins[ef] * tf["iv"] ** 2) / 43200
    return dict(value=sqrt(var), why="ok", near_iv=tn["iv"], far_iv=tf["iv"], near_F=tn["F"], far_F=tf["F"]), snap


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "samples"
    series = pd.read_parquet(ROOT / "data" / "index_series.parquet").set_index("session_date")
    stored_snap = pd.read_parquet(ROOT / "data" / "option_snapshot_1545.parquet")
    stored_snap["session_date"] = stored_snap["session_date"].astype("datetime64[ns]")
    if mode == "samples":
        days = SAMPLES
    else:
        days = [d.strftime("%Y-%m-%d") for d in series.index if d >= pd.Timestamp("2025-03-01")]
    rows = []
    for day in days:
        ts = pd.Timestamp(day)
        a, snap_a = atm30(day, "study", verbose=(mode == "samples"))
        b, snap_b = atm30(day, "strict", verbose=False)
        st = series.loc[ts]
        rec = dict(day=day, stored=st.atm30, mine_study_rule=a["value"], mine_strict_rule=b["value"], why_study=a["why"], why_strict=b["why"],
                   stored_near_iv=st.near_iv, mine_near_iv=a.get("near_iv"), stored_near_F=st.near_forward, mine_near_F=a.get("near_F"), stored_status=st.status)
        # snapshot table check against the stored parquet
        mine = snap_a.rename(columns={"raw_symbol": "symbol"}).set_index("symbol")[["bid", "ask", "age"]]
        theirs = stored_snap[stored_snap.session_date == ts].set_index("symbol")[["bid", "ask", "age"]]
        j = mine.join(theirs, lsuffix="_m", rsuffix="_s", how="outer")
        rec["snap_rows_mine"], rec["snap_rows_stored"] = len(mine), len(theirs)
        rec["snap_mismatch"] = int(((j.bid_m.fillna(-1) != j.bid_s.fillna(-1)) | (j.ask_m.fillna(-1) != j.ask_s.fillna(-1)) | (j.age_m.fillna(-1) != j.age_s.fillna(-1))).sum())
        # how many instruments have a null bid in their last row but a bid under the study rule
        sa = snap_a.set_index("raw_symbol"); sb = snap_b.set_index("raw_symbol")
        rec["revived_bids"] = int((sb.bid.isna() & sa.bid.notna()).sum())
        rec["instruments"] = len(sa)
        rows.append(rec)
        if mode == "samples":
            print(f"{day}: stored {st.atm30:.6f}  mine(study rule) {a['value']:.6f}  mine(strict) {b['value']:.6f}  status {st.status}  snapshot mismatches {rec['snap_mismatch']}  revived bids {rec['revived_bids']}/{len(sa)}")
    out = pd.DataFrame(rows)
    out["diff_study"] = out.mine_study_rule - out.stored
    out["rel_strict"] = out.mine_strict_rule / out.stored - 1
    out.to_csv(OUT / f"a03_{mode}.csv", index=False)
    print(out[["day", "stored", "mine_study_rule", "mine_strict_rule", "diff_study", "rel_strict", "snap_mismatch", "revived_bids", "instruments", "why_strict"]].to_string())
    both = out.dropna(subset=["stored", "mine_study_rule"])
    print("\nmax |mine(study rule) - stored|:", float(both.diff_study.abs().max()), " on", len(both), "days; presence mismatch:", int((out.stored.isna() != out.mine_study_rule.isna()).sum()))
    s = out.dropna(subset=["stored"])
    print("strict rule: days lost", int(s.mine_strict_rule.isna().sum()), "of", len(s), "; days changed by >0.1%:", int((s.rel_strict.abs() > 1e-3).sum()), "; >1%:", int((s.rel_strict.abs() > 1e-2).sum()), "; >5%:", int((s.rel_strict.abs() > 5e-2).sum()))
    print("strict rule relative change describe:\n", s.rel_strict.describe(percentiles=[.01, .05, .5, .95, .99]).to_string())
    print("share of instruments with a revived bid, mean:", float((out.revived_bids / out.instruments).mean()))


if __name__ == "__main__":
    main()
