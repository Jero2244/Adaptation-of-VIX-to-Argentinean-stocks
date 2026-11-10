"""Interval coverage and row counts in the stored simulations, against the verdict line and the frozen rows."""
import glob
import pandas as pd

D = "../stage4_debate/"
s = pd.concat(pd.read_csv(f) for f in glob.glob(D + "advocate/a2_sim_*.csv"))
u = s[~s.thin]
rows = []
for t, g in u.groupby("true_b"):
    rows.append(dict(true_b=t, cov21=((g.lo <= t) & (t <= g.hi)).mean(), cov63=((g.lo63 <= t) & (t <= g.hi63)).mean(), low_miss21=(g.lo > t).mean(), high_miss21=(g.hi < t).mean(), low_miss63=(g.lo63 > t).mean(), high_miss63=(g.hi63 < t).mean()))
print("a2_sim coverage of the true b, full coverage, 499 draws")
print(pd.DataFrame(rows).round(3).to_string(index=False))
print("by base window: sessions, origins, scored")
print(u.groupby("start")[["sessions", "origins", "scored"]].median().to_string())
j = pd.read_csv(D + "judge/j1_sim.csv")
print("judge coverage (21, 63)", {t: (round(((g.lo21 <= t) & (t <= g.hi21)).mean(), 3), round(((g.lo63 <= t) & (t <= g.hi63)).mean(), 3)) for t, g in j.groupby("true_b")})
a = pd.concat(pd.read_csv(f) for f in glob.glob(D + "advocate/a7_2*.csv"))
rows = []
for (cover, outer, t), g in a.groupby(["cover", "outer", "true_b"]):
    rows.append(dict(cover=cover, outer=outer, true_b=t, n=g.n.median(), reps=len(g), cov21=((g.lo21 <= t) & (t <= g.hi21)).mean(), cov63=((g.lo63 <= t) & (t <= g.hi63)).mean(), sup=((g.lo21 > 0) & (g.lo63 > 0)).mean(), small=((g.hi21 < .37) & (g.hi63 < .37)).mean()))
print("a7 coverage, by outer block and coverage setting")
print(pd.DataFrame(rows).round(3).to_string(index=False))
