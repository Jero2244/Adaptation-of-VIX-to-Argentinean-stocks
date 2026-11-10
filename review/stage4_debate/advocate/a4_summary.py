"""Summaries from a1_dryrun.csv and a2_sim_*.csv only. It reads no project data file."""
import glob
import numpy as np
import pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)


def outcomes(d, floor_n=20, medt=1.65, cw=1.65, not_b=True):
    f = (d.origins >= 300) & (d.fs_n >= floor_n)
    r1 = d.r1a & (d.fs_mean > 0) & (d.fs_medt > medt)
    r2 = d.cw_t > cw
    sup = r1 & r2
    no = (d.b <= 0) | (d.hi < .25)
    o = np.where(~f, "Inc(floor)", np.where(sup & d.r3, "Sup+gain", np.where(sup, "Sup", np.where(no, "NotSup", "Inc"))))
    return pd.Series(o, index=d.index)


r = pd.read_csv("a1_dryrun.csv")
print("DRY RUN, 55 overlapping windows. Variants on the rule thresholds")
for name, kw in (("draft", {}), ("floor 18", dict(floor_n=18)), ("floor 18, med t 1.30", dict(floor_n=18, medt=1.30)), ("floor 18, med t 1.00", dict(floor_n=18, medt=1.00))):
    print(name, outcomes(r, **kw).value_counts().to_dict())
print("disjoint windows 2018-05, 2020-09, 2022-11 (2 months shared by the last two):")
print(r[r.start.isin(["2018-05", "2020-09", "2022-11"])][["start", "origins", "scored", "fs_n", "b", "lo", "hi", "fs_medt", "cw_t", "q_duan", "q_none", "outcome"]].round(3).to_string())
print("share of windows: b>0 and lo>0", r.r1a.mean().round(3), "fs t>1.65", (r.fs_medt > 1.65).mean().round(3), "fs t>1.3", (r.fs_medt > 1.3).mean().round(3), "cw>1.65", (r.cw_t > 1.65).mean().round(3))
print("corr b vs cw_t", r.b.corr(r.cw_t).round(3), "strict floor-fail count", (r.strict_outcome == "Inconclusive (floor)").sum())
print("median fs t / b ratio: implied fixed-step se", round((r.fs_mean / r.fs_medt).median(), 3), "block se", round(r.se.median(), 3))

files = glob.glob("a2_sim_*.csv")
if files:
    s = pd.concat(pd.read_csv(f) for f in files)
    print("\nSIMULATION rows", len(s), "reps by cell", s.groupby(["start", "thin", "true_b"]).size().min(), "to", s.groupby(["start", "thin", "true_b"]).size().max())
    s["lo63ok"] = s.lo63 > 0
    def table(g):
        return pd.Series(dict(n=len(g), origins=g.origins.median(), scored=g.scored.median(), fs_n=g.fs_n.median(), floor_fail=(~g.floor).mean(), r1a=g.r1a.mean(), r1a63=g.lo63ok.mean(), r1b=g.r1b.mean(), r1=g.r1.mean(), r2=g.r2.mean(), r3=g.r3.mean(), Sup=g.sup.mean(), NotSup=g.notsup.mean(), hi_lt25=(g.hi < .25).mean(), both=g.both.mean(), bmean=g.b.mean(), bsd=g.b.std(), medse=g.se.median()))
    print(s.groupby(["thin", "true_b"]).apply(table).round(3).to_string())
    print(s.groupby(["start", "thin", "true_b"]).apply(table)[["n", "fs_n", "floor_fail", "r1a", "r1", "r2", "r3", "Sup", "NotSup"]].round(3).to_string())
    for thin in (False, True):
        t = s[s.thin == thin]
        for name, kw in (("draft", {}), ("floor 18", dict(floor_n=18)), ("floor 18, med t 1.30", dict(floor_n=18, medt=1.30)), ("floor 18, med t 1.00", dict(floor_n=18, medt=1.00))):
            v = t.assign(o=outcomes(t.reset_index(drop=True), **kw).values if False else outcomes(t, **kw))
            print("thin", thin, name)
            print(v.groupby("true_b").o.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())
