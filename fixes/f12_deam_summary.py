"""Fix step 4 (F2): summary of the American-tree term IVs on real open-data terms. DEVELOPMENT work on open data.

Reads f03_deam_terms_NAME.csv (one row per term that has a cash dividend inside it) and the series files. Writes stdout only.
"""
import sys

from common import *  # noqa

if __name__ == "__main__":
    print(LABEL)
    base = pd.read_parquet(FDATA / "series_base.parquet").set_index("session_date")
    for name in sys.argv[1:] or ["deam", "deamC"]:
        path = HERE / f"f03_deam_terms_{name}.csv"
        if not path.exists():
            print(name, "log missing")
            continue
        t = pd.read_csv(path, parse_dates=["session_date", "expiry"])
        ser = pd.read_parquet(FDATA / f"series_{name}.parquet").set_index("session_date")
        print(f"\n===== {name}: {len(t)} term evaluations on {t.session_date.nunique()} sessions")
        print("spot source:", t.spot_source.value_counts().to_dict(), "; stock quote age (min) median %.1f, p90 %.1f" % (t.stock_age.median(), t.stock_age.quantile(.9)))
        print("tree solved (iv_new present): %d of %d; old recipe solved: %d" % (t.iv_new.notna().sum(), len(t), t.iv_old.notna().sum()))
        ok = t.dropna(subset=["iv_new", "iv_old"])
        rel = ok.iv_new / ok.iv_old - 1
        print("term IV, tree / frozen - 1 (all terms with both): mean %.4f, median %.4f, p10 %.4f, p90 %.4f" % (rel.mean(), rel.median(), rel.quantile(.1), rel.quantile(.9)))
        for lo, hi in ((0, 14), (14, 30), (30, 60), (60, 200)):
            s = ok[(ok.days >= lo) & (ok.days < hi)]
            r = s.iv_new / s.iv_old - 1
            if len(s):
                print(f"   term of {lo}-{hi} days: n {len(s)}, mean {r.mean():.4f}, median {r.median():.4f}")
        fr = np.log(ok.forward_tree / ok.forward_parity)
        print("log(model forward from Nasdaq spot / parity forward): mean %.4f, median %.4f, p10 %.4f, p90 %.4f" % (fr.mean(), fr.median(), fr.quantile(.1), fr.quantile(.9)))
        print("tier changes (old -> new):", pd.crosstab(ok.tier_old, ok.tier_new).to_dict())
        both = pd.DataFrame(dict(new=ser.atm30, old=base.atm30)).dropna()
        ch = np.log(both.new / both.old)
        aff = ch[ch.abs() > 1e-12]
        print("ATM30: valid days new %d, old %d; days whose value changed: %d; presence changes: %d" % (ser.atm30.notna().sum(), base.atm30.notna().sum(), len(aff), int((ser.atm30.notna() != base.atm30.notna()).sum())))
        print("   log change on the changed days: mean %.4f, median %.4f, p10 %.4f, p90 %.4f, min %.4f, max %.4f" % (aff.mean(), aff.median(), aff.quantile(.1), aff.quantile(.9), aff.min(), aff.max()))
        print("   log change over all common days: mean %.4f" % ch.mean())
        by = aff.groupby(aff.index.year).agg(["count", "mean"]).round(4)
        print("   changed days by year:\n", by.to_string())
