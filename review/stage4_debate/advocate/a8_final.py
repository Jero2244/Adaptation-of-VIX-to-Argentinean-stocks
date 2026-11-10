"""Operating table of the final recommended outcomes, from a2_sim_*.csv and a5_amended.csv. Reads no project data."""
import glob
import numpy as np
import pandas as pd
pd.set_option("display.width", 200, "display.max_columns", 20)
s = pd.concat(pd.read_csv(f) for f in glob.glob("a2_sim_*.csv")).reset_index(drop=True)


def final(d):
    gate = (d.lo > 0) & (d.lo63 > 0)
    gain = gate & (d.q_duan < 0) & (d.q_duan_hi < 0)
    below = (d.hi < .37) & (d.hi63 < .37)
    return pd.Series(np.where(gain, "Sup+gain", np.where(gate, "Sup", np.where(below, "Below", "Inc"))), index=d.index), gate & (d.cw_t > 1.65)


for name, d in (("full coverage", s[~s.thin]), ("thin 70%", s[s.thin])):
    o, phrase = final(d)
    print(name)
    print(d.assign(o=o).groupby("true_b").o.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())
    print("also out-of-sample phrase", d.assign(p=phrase).groupby("true_b").p.mean().round(3).to_dict())
u = s[~s.thin]
o, _ = final(u)
print("by base window, Supported of any kind")
print(u.assign(sup=o.isin(["Sup", "Sup+gain"])).groupby(["start", "true_b"]).sup.mean().unstack().round(3).to_string())
a = pd.read_csv("a5_amended.csv")
o, phrase = final(a)
print("dry run, 55 overlapping seen windows:", o.value_counts().to_dict(), "phrase", int(phrase.sum()))
print("starts supported:", a.start[o.isin(["Sup", "Sup+gain"])].tolist())
