"""Checks on the variant engine. DEVELOPMENT work on open data. Stdout only.
1. The engine with no option (series_base) equals the stored series (ATM30, ATM30 floor7, tier).
2. Strict snapshot: days lost, largest changes, against audit/a03_postbreak.csv (independent rebuild).
3. Which sessions the 7-day floor, the spread filter, and Tier 1 remove, by year, as a share of stored valid days.
4. How many valid days have a far term above 65 days (F10) and how many stored valid days have a near term below 7 days (F9).
"""
from common import *  # noqa

if __name__ == "__main__":
    print(LABEL)
    st = pd.read_parquet(DATA / "index_series.parquet").set_index("session_date")
    b = pd.read_parquet(FDATA / "series_base.parquet").set_index("session_date")
    for c in ("atm30", "atm30_floor7", "atm30_usable", "tier", "near_iv", "far_iv"):
        d = (b[c] - st[c]).abs().max()
        print(f"1. {c}: max |engine - stored| = {d}; presence mismatches {int((b[c].notna() != st[c].notna()).sum())}")
    s = pd.read_parquet(FDATA / "series_strict.parquet").set_index("session_date")
    both = pd.DataFrame(dict(strict=s.atm30, stored=st.atm30))
    lost = both[both.stored.notna() & both.strict.isna()]
    print("\n2. strict rule: days lost", len(lost), [str(d.date()) for d in lost.index])
    rel = (both.strict / both.stored - 1).dropna()
    ch = rel[rel.abs() > 1e-9]
    print("   days changed:", len(ch), "; >1%:", int((ch.abs() > .01).sum()), "; >5%:", int((ch.abs() > .05).sum()), "; largest:", ch.loc[ch.abs().idxmax()].round(4), ch.abs().idxmax().date(), "; mean change on changed days %.4f" % ch.mean())
    pb = pd.read_csv(ROOT / "audit" / "a03_postbreak.csv", parse_dates=["day"]).set_index("day")
    j = pd.DataFrame(dict(mine=s.atm30, audit=pb.mine_strict_rule)).dropna()
    print("   against the audit's independent strict rebuild (post-2025-03, %d days): max |diff| = %.2e" % (len(j), (j.mine - j.audit).abs().max()))
    print("\n3. share of stored valid days removed, by filter and period")
    for name, col in (("floor7", "atm30_floor7"), ("spread50", "atm30"), ("tier1", "atm30")):
        v = pd.read_parquet(FDATA / f"series_{'base' if name == 'floor7' else name}.parquet").set_index("session_date")[col]
        removed = st.atm30.notna() & v.isna()
        yr = removed.groupby(removed.index.year).sum()
        base = st.atm30.notna().groupby(st.index.year).sum()
        print(f"   {name}: removed {int(removed.sum())} of {int(st.atm30.notna().sum())}; by year (share):", (yr / base).round(2).to_dict())
    ok = st[st.atm30.notna()]
    print("\n4. stored valid days with near term < 7 days: %d; far term > 65 days: %d; far term > 90 days: %d" % ((ok.near_days < 7).sum(), (ok.far_days > 65).sum(), (ok.far_days > 90).sum()))
    pan = make_panel(st.reset_index())
    pr = pan[pan.primary]
    print("   primary origins by year (stored):", pr.groupby(pr.session_date.dt.year).size().to_dict())
