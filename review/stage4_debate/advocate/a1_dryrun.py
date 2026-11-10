"""Dry run on SEEN pre-2025-03 panel rows. Shows rule behaviour only, not evidence for the claim."""
from rules import *
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)
p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=CALC)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
PASO = pd.Timestamp("2019-08-12")
rows = []
for s in pd.period_range("2018-05", "2022-11", freq="M"):
    a, e = s.to_timestamp(), (s + 27).to_timestamp(how="end").normalize()
    w = p[(p.session_date >= a) & (p.session_date <= e)]
    o = apply_rules(w)
    o2 = apply_rules(w, strict_end=e, seed=20261105)
    o3 = apply_rules(w, har_train_all=False, seed=20261106)
    rows.append(dict(start=str(s), end=str(e.date()), has_paso=a <= PASO <= e, **o, strict_outcome=o2["outcome"], strict_scored=o2["scored"], strict_cw_t=o2["cw_t"], strict_r1=o2["r1"], strict_r2=o2["r2"], strict_origins=o2["origins"], sameT_cw_t=o3["cw_t"], sameT_qn=o3["q_none"], sameT_qd=o3["q_duan"], sameT_outcome=o3["outcome"]))
r = pd.DataFrame(rows)
r.to_csv("a1_dryrun.csv", index=False)
c = ["start", "sessions", "origins", "scored", "fs_n", "b", "lo", "hi", "fs_mean", "fs_medt", "cw_t", "q_duan", "q_duan_hi", "q_none", "q_none_hi", "r1", "r2", "r3", "outcome"]
print(r[c].round(3).to_string())
for name, g in (("all 55", r), ("with 2019-08-12", r[r.has_paso]), ("without 2019-08-12", r[~r.has_paso])):
    print("\n==", name, len(g))
    print(g.outcome.value_counts().to_dict())
    print("r1a", round(g.r1a.mean(), 3), "r1b", round(g.r1b.mean(), 3), "r1b strict", round(g.r1b_strict.mean(), 3), "r1", round(g.r1.mean(), 3), "r2", round(g.r2.mean(), 3), "r3", round(g.r3.mean(), 3), "both sup and notsup", int(g.both.sum()), "hi<.25", int((g.hi < .25).sum()), "b<=0", int((g.b <= 0).sum()))
    print("interval width median", round((g.hi - g.lo).median(), 3), "min", round((g.hi - g.lo).min(), 3), "b range", round(g.b.min(), 3), round(g.b.max(), 3), "se median", round(g.se.median(), 3))
    print("strict end", g.strict_outcome.value_counts().to_dict(), "scored median", g.strict_scored.median(), "same-train", g.sameT_outcome.value_counts().to_dict())
print("\nmedian abs diff CW t same vs long", round((r.cw_t - r.sameT_cw_t).abs().median(), 3), "max", round((r.cw_t - r.sameT_cw_t).abs().max(), 3))
print("origins min", r.origins.min(), "scored min/med/max", r.scored.min(), r.scored.median(), r.scored.max(), "fs_n min", r.fs_n.min(), "floor fail", int((~r.floor).sum()))
