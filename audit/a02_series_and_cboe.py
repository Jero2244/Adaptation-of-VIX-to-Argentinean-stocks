"""Audit step 2: quality of the stored series, and an independent CBOE-style (discrete strike) variance on every open session.

Reads data/*.parquet and data/source/fred_rates.csv only. Writes audit/a02_cboe_by_session.csv.
The CBOE-style number follows the Cboe VIX white paper per term:
  sigma^2 = (2/T) * sum_i dK_i / K_i^2 * exp(rT) * Q(K_i) - (1/T) * (F/K0 - 1)^2
with F from parity at the strike with the smallest |C - P|, K0 the first listed strike at or below F, OTM puts below K0
and OTM calls above K0 (mid quotes), the put/call average at K0, a stop after two consecutive zero bids, and dK as half
the gap between the neighbours (the simple gap at each end).
"""
from math import erf, exp, log, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "data"
OUT = Path(__file__).resolve().parent
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 300)
YEAR_MIN = 525600.0
T30 = 30 * 1440.0


def ncdf(x):
    return 0.5 * (1 + erf(x / sqrt(2)))


def black_otm(F, K, tv):
    d1 = log(F / K) / tv + tv / 2
    d2 = d1 - tv
    call = F * ncdf(d1) - K * ncdf(d2)
    return call if K >= F else call - F + K


def cboe_term(chain, minutes, r, flat_iv=None):
    """Return dict with the CBOE-style variance of one expiry, or reason. chain: strike, right, bid, ask."""
    T = minutes / YEAR_MIN
    g = exp(r * T)
    c = chain[chain.right == "C"].set_index("strike").sort_index()
    p = chain[chain.right == "P"].set_index("strike").sort_index()
    if c.index.has_duplicates or p.index.has_duplicates:
        return dict(reason="dup")
    both = c.index.intersection(p.index)
    ok = [(k) for k in both if c.bid[k] > 0 and p.bid[k] > 0 and c.ask[k] >= c.bid[k] and p.ask[k] >= p.bid[k]]
    if not ok:
        return dict(reason="no pair")
    cm = (c.bid + c.ask) / 2
    pm = (p.bid + p.ask) / 2
    kstar = min(ok, key=lambda k: abs(cm[k] - pm[k]))
    F = kstar + g * (cm[kstar] - pm[kstar])
    strikes = np.array(sorted(set(c.index) | set(p.index)))
    below = strikes[strikes <= F]
    if len(below) == 0:
        return dict(reason="no K0", F=F)
    K0 = below[-1]
    sel = {}  # strike -> Q
    # K0: average of put and call mids when both exist with a bid; else whichever exists
    q0 = [m[K0] for m, t in ((cm, c), (pm, p)) if K0 in t.index and t.bid[K0] > 0 and t.ask[K0] >= t.bid[K0]]
    k0_ok = len(q0) == 2
    if q0:
        sel[K0] = float(np.mean(q0))
    nput = ncall = 0
    zero = 0
    for k in strikes[strikes < K0][::-1]:
        if k not in p.index or not (p.bid[k] > 0):  # NaN or zero bid
            zero += 1
            if zero == 2:
                break
            continue
        zero = 0
        sel[k] = float(pm[k]); nput += 1
    zero = 0
    for k in strikes[strikes > K0]:
        if k not in c.index or not (c.bid[k] > 0):
            zero += 1
            if zero == 2:
                break
            continue
        zero = 0
        sel[k] = float(cm[k]); ncall += 1
    ks = np.array(sorted(sel))
    if len(ks) < 2:
        return dict(reason="one strike", F=F, K0=K0, nput=nput, ncall=ncall, k0_ok=k0_ok)
    dk = np.empty(len(ks))
    dk[1:-1] = (ks[2:] - ks[:-2]) / 2
    dk[0] = ks[1] - ks[0]
    dk[-1] = ks[-1] - ks[-2]
    q = np.array([sel[k] for k in ks])
    var = (2 / T) * float(np.sum(dk / ks ** 2 * g * q)) - (1 / T) * (F / K0 - 1) ** 2
    out = dict(reason="ok", var=var, F=F, K0=K0, nput=nput, ncall=ncall, n=len(ks), k0_ok=k0_ok, kmin=ks[0], kmax=ks[-1], T=T,
               max_dk_rel=float(np.max(np.diff(ks)) / F))
    if flat_iv is not None and flat_iv > 0:
        tv = flat_iv * sqrt(T)
        qf = np.array([black_otm(F, k, tv) if k != K0 else 0.5 * (black_otm(F, k, tv) + (black_otm(F, k, tv) + (F - k if k < F else k - F))) for k in ks])
        # at K0 (<= F): put is OTM price, call = put + F - K0 ; average = put + (F-K0)/2
        qf = np.array([black_otm(F, k, tv) for k in ks])
        i0 = int(np.where(ks == K0)[0][0]) if K0 in ks else None
        if i0 is not None:
            put0 = black_otm(F, K0, tv) if K0 < F else black_otm(F, K0, tv)
            qf[i0] = put0 + (F - K0) / 2
        var_flat = (2 / T) * float(np.sum(dk / ks ** 2 * qf)) - (1 / T) * (F / K0 - 1) ** 2
        out["flat_ratio"] = var_flat / flat_iv ** 2  # 1.0 means no truncation or discreteness error under a flat smile
    return out


def main():
    series = pd.read_parquet(D / "index_series.parquet")
    terms = pd.read_parquet(D / "atm_terms.parquet")
    snap = pd.read_parquet(D / "option_snapshot_1545.parquet")
    snap["session_date"] = snap["session_date"].astype("datetime64[ns]")
    rates = pd.read_csv(D / "source" / "fred_rates.csv", parse_dates=["observation_date"], index_col="observation_date").apply(pd.to_numeric, errors="coerce").dropna(how="all").ffill()
    r1 = np.log1p(rates["DGS1MO"] / 100).shift(1).reindex(series.session_date, method="ffill").to_numpy()

    print("=== A. Stored series quality")
    ok = series[series.atm30.notna()].copy()
    ok["post"] = ok.session_date >= "2025-03-01"
    print("valid days", len(ok))
    print("far_days > 65:", int((ok.far_days > 65).sum()), " > 90:", int((ok.far_days > 90).sum()))
    print(ok.loc[ok.far_days > 65].groupby("year").size().to_string())
    print("near_days < 1:", int((ok.near_days < 1).sum()), " < 3:", int((ok.near_days < 3).sum()), " < 7:", int((ok.near_days < 7).sum()))
    print("\nnear/far pairs (two-sided strikes) per term by year: median near, median far, share of days near_pairs<=2")
    print(ok.groupby("year").agg(near_med=("near_pairs", "median"), far_med=("far_pairs", "median"), near_le2=("near_pairs", lambda s: (s <= 2).mean()), far_le2=("far_pairs", lambda s: (s <= 2).mean()), near_eq1=("near_pairs", lambda s: (s == 1).mean())).round(2).to_string())
    print("\nrelative_spread (call+put spread over call+put mid, worst term) by year: median, p90")
    print(ok.groupby("year")["relative_spread"].describe(percentiles=[.5, .9])[["50%", "90%", "max"]].round(3).to_string())
    print("\nquote_age before/after 2025-03: share age==0, max")
    print(ok.groupby("post")["quote_age"].agg(lambda s: (s == 0).mean()).to_string(), ok.groupby("post")["quote_age"].max().to_string())
    print("\nTier 2 max_distance (abs log distance of the single strike from the forward):")
    print(ok.loc[ok.tier == 2, "max_distance"].describe(percentiles=[.5, .9, .99]).round(3).to_string())
    print("Tier 1 max_distance:")
    print(ok.loc[ok.tier == 1, "max_distance"].describe(percentiles=[.5, .9, .99]).round(3).to_string())

    # roll discontinuity: change of atm30 between consecutive valid sessions (adjacent on the grid) split by whether the near expiry changed
    s = series.reset_index(drop=True)
    s["d"] = np.log(s.atm30).diff()
    s["adjacent"] = s.atm30.notna() & s.atm30.shift(1).notna()
    s["roll"] = s.near_expiry != s.near_expiry.shift(1)
    adj = s[s.adjacent]
    print("\n=== B. Roll discontinuity: daily log change of ATM30 on adjacent valid sessions")
    print(adj.groupby("roll")["d"].agg(n="size", mean="mean", mean_abs=lambda x: x.abs().mean(), median_abs=lambda x: x.abs().median(), sd="std").round(4).to_string())
    # across the whole gap around a roll: last valid value before the near expiry changes vs first valid value after
    valid = s[s.atm30.notna()].reset_index(drop=True)
    valid["dv"] = np.log(valid.atm30).diff()
    valid["gap_sessions"] = valid.index.to_series().map(lambda i: np.nan)
    valid["rollv"] = valid.near_expiry != valid.near_expiry.shift(1)
    print("between consecutive valid values (gaps allowed):")
    print(valid.iloc[1:].groupby("rollv")["dv"].agg(n="size", mean="mean", mean_abs=lambda x: x.abs().mean(), median_abs=lambda x: x.abs().median()).round(4).to_string())
    print("\nmean log(near_iv / far_iv) by days to near expiry (term-structure noise at the short end):")
    ok["bucket"] = pd.cut(ok.near_days, [-1, 1, 3, 7, 14, 21, 31], right=False)
    ok["lr"] = np.log(ok.near_iv / ok.far_iv)
    print(ok.groupby("bucket", observed=True)["lr"].agg(n="size", mean="mean", sd="std", p05=lambda x: x.quantile(.05), p95=lambda x: x.quantile(.95)).round(3).to_string())
    print("near_iv extremes:", ok.near_iv.describe(percentiles=[.01, .99]).round(3).to_dict())

    print("\n=== C. Forward against the 15:45 Nasdaq stock mid")
    print(ok["log_forward_to_stock"].describe(percentiles=[.01, .05, .5, .95, .99]).round(4).to_string())
    print(ok.loc[ok.log_forward_to_stock.abs() > .03, ["session_date", "near_days", "near_forward", "log_forward_to_stock", "near_pairs", "tier", "flag_ex_in_front"]].to_string())
    print("by ex-date flag: ", ok.groupby("flag_ex_in_front")["log_forward_to_stock"].agg(["size", "mean", "median"]).round(4).to_string())

    print("\n=== D. CBOE-style discrete variance on every session (from the stored 15:45 snapshot, age <= 30 min)")
    snap = snap[snap.age <= 30]
    by = dict(tuple(snap.groupby("session_date")))
    tmap = {(a, b): (m, iv) for a, b, m, iv in zip(terms.session_date, terms.expiry, terms.minutes, terms.iv)}
    rows = []
    for i, row in series.iterrows():
        rec = dict(session_date=row.session_date, atm30=row.atm30, mf30=row.mf30, near_days=row.near_days, far_days=row.far_days)
        if pd.isna(row.near_expiry) or row.session_date not in by:
            rows.append(rec); continue
        ch = by[row.session_date]
        res = {}
        for tag, e in (("near", row.near_expiry), ("far", row.far_expiry)):
            if pd.isna(e):
                continue
            m, iv = tmap.get((row.session_date, e), (None, None))
            if m is None or m <= 0:
                continue
            res[tag] = cboe_term(ch[ch.expiry == e], m, r1[i] if np.isfinite(r1[i]) else 0.0, iv if iv is not None and np.isfinite(iv) else None)
            res[tag]["minutes"] = m
            for k in ("reason", "nput", "ncall", "n", "flat_ratio", "var", "k0_ok", "max_dk_rel"):
                rec[f"{tag}_{k}"] = res[tag].get(k)
        if all(res.get(t, {}).get("reason") == "ok" for t in ("near", "far")):
            n, f = res["near"], res["far"]
            w = (f["minutes"] - T30) / (f["minutes"] - n["minutes"])
            v = (w * n["minutes"] * n["var"] + (1 - w) * f["minutes"] * f["var"]) / T30
            rec["cboe30"] = sqrt(v) if v > 0 else np.nan
            if n.get("flat_ratio") and f.get("flat_ratio"):
                vf = (w * n["minutes"] * n["flat_ratio"] + (1 - w) * f["minutes"] * f["flat_ratio"]) / (w * n["minutes"] + (1 - w) * f["minutes"])
                rec["flat_ratio30"] = vf
        rows.append(rec)
    out = pd.DataFrame(rows)
    out["year"] = out.session_date.dt.year
    out.to_csv(OUT / "a02_cboe_by_session.csv", index=False)
    out["min_wing"] = out[["near_nput", "near_ncall", "far_nput", "far_ncall"]].min(axis=1)
    print("sessions:", len(out), " CBOE-style value computable (>=2 strikes on both terms):", int(out.cboe30.notna().sum()))
    print("\nBy year: sessions, ATM30 days, CBOE-computable, share of ALL sessions with >=1 / >=2 / >=3 / >=5 OTM strikes with a bid on each wing of both terms; median strikes used per term")
    g = out.groupby("year")
    tab = pd.DataFrame({"sessions": g.size(), "atm30": g.atm30.count(), "cboe": g.cboe30.count(),
                        "wing>=1": g.min_wing.apply(lambda s: (s >= 1).mean()), "wing>=2": g.min_wing.apply(lambda s: (s >= 2).mean()),
                        "wing>=3": g.min_wing.apply(lambda s: (s >= 3).mean()), "wing>=5": g.min_wing.apply(lambda s: (s >= 5).mean()),
                        "near_n_med": g.near_n.median(), "far_n_med": g.far_n.median()}).round(3)
    print(tab.to_string())
    both = out.dropna(subset=["cboe30", "atm30"])
    both = both.assign(ratio=both.cboe30 / both.atm30)
    print("\nCBOE-style / ATM30 (vol ratio) by year: n, median, p10, p90 ; and flat-smile recovery ratio of the VARIANCE (1 = no truncation/discreteness loss)")
    print(both.groupby("year").agg(n=("ratio", "size"), med=("ratio", "median"), p10=("ratio", lambda s: s.quantile(.1)), p90=("ratio", lambda s: s.quantile(.9)), flat_med=("flat_ratio30", "median"), flat_p10=("flat_ratio30", lambda s: s.quantile(.1)), flat_p90=("flat_ratio30", lambda s: s.quantile(.9))).round(3).to_string())
    print("\nSame, only sessions with >=3 strikes per wing on both terms:")
    deep = both[both.min_wing >= 3]
    print(deep.groupby("year").agg(n=("ratio", "size"), med=("ratio", "median"), flat_med=("flat_ratio30", "median")).round(3).to_string())
    m = out.dropna(subset=["cboe30", "mf30"])
    print("\nCBOE-style / MF30 where both exist: n", len(m), "median", round(float((m.cboe30 / m.mf30).median()), 3), "p10", round(float((m.cboe30 / m.mf30).quantile(.1)), 3), "p90", round(float((m.cboe30 / m.mf30).quantile(.9)), 3))
    print("corr of log daily changes, CBOE-style vs ATM30 (adjacent valid days):", round(float(np.corrcoef(np.log(both.cboe30).diff().dropna(), np.log(both.atm30).diff().dropna())[0, 1]), 3))
    print("sd of daily log change: cboe", round(float(np.log(both.cboe30).diff().std()), 4), "atm30", round(float(np.log(both.atm30).diff().std()), 4))
    print("max relative strike gap (largest dK/F among used strikes), median by year, near term:")
    print(out.groupby("year")["near_max_dk_rel"].median().round(3).to_string())


if __name__ == "__main__":
    main()
