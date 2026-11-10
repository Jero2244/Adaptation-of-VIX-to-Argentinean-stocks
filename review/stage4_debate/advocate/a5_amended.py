"""Amended rules: target windows end inside the frame, HAR and HAR+ATM30 train on the same primary rows, floor 17, Rule 1 median t variants.
Dry run on SEEN pre-2025-03 panel rows, and a retabulation of a2_sim_*.csv. Behaviour of the rules only."""
import glob
from rules import *
pd.set_option("display.width", 250, "display.max_columns", 40, "display.max_rows", 200)


def tab(d, floor_n=17, medt=1.65, use_r1b=True, scored_min=180):
    f = (d.origins >= 300) & (d.fs_n >= floor_n) & (d.scored >= scored_min)
    r1 = d.r1a & (d.fs_mean > 0) & ((d.fs_medt > medt) if use_r1b else True)
    sup = r1 & (d.cw_t > 1.65)
    no = (d.b <= 0) | (d.hi < .25)
    return pd.Series(np.where(~f, "Inc(floor)", np.where(sup & d.r3, "Sup+gain", np.where(sup, "Sup", np.where(no, "NotSup", "Inc")))), index=d.index)


s = pd.concat(pd.read_csv(f) for f in glob.glob("a2_sim_*.csv")).reset_index(drop=True)
print("Sim: hi<.25 with b>0, share of all rows:", round(((s.hi < .25) & (s.b > 0)).mean(), 4), "count", int(((s.hi < .25) & (s.b > 0)).sum()), "of", len(s), "| hi<.25 and Rule 1a pass:", int(((s.hi < .25) & s.r1a).sum()))
print("Sim: b<=0 given hi<.25 share:", round((s.b[s.hi < .25] <= 0).mean(), 4), "min interval width", round((s.hi - s.lo).min(), 3))
for thin in (False, True):
    t = s[s.thin == thin]
    for name, kw in (("draft floor 20, t 1.65", dict(floor_n=20, scored_min=0)), ("floor 17, t 1.65", {}), ("floor 17, t 1.30", dict(medt=1.30)), ("floor 17, t 1.00", dict(medt=1.00)), ("floor 17, no fixed-step t", dict(use_r1b=False))):
        print("\nthin", thin, name)
        print(t.assign(o=tab(t, **kw)).groupby("true_b").o.value_counts(normalize=True).unstack(fill_value=0).round(3).to_string())

p = pd.read_parquet(ROOT + r"\data\forecast_panel.parquet", columns=CALC)
p = p[p.session_date < "2025-03-01"].reset_index(drop=True)
rows = []
for m in pd.period_range("2018-05", "2022-11", freq="M"):
    a, e = m.to_timestamp(), (m + 27).to_timestamp(how="end").normalize()
    w = p[(p.session_date >= a) & (p.session_date <= e)]
    rows.append(dict(start=str(m), **apply_rules(w, strict_end=e, har_train_all=False, block63=True)))
r = pd.DataFrame(rows)
r.to_csv("a5_amended.csv", index=False)
print("\nAMENDED DRY RUN, 55 overlapping windows, strict ends, same training rows")
print("origins min", r.origins.min(), "scored min/med/max", r.scored.min(), r.scored.median(), r.scored.max(), "fs_n min/med", r.fs_n.min(), r.fs_n.median())
for name, kw in (("floor 20, t 1.65", dict(floor_n=20, scored_min=0)), ("floor 17, t 1.65", {}), ("floor 17, t 1.30", dict(medt=1.30)), ("floor 17, t 1.00", dict(medt=1.00))):
    print(name, tab(r, **kw).value_counts().to_dict())
print("starts Supported at t 1.00:", r.start[tab(r, medt=1.00).isin(["Sup", "Sup+gain"])].tolist())
print("r1a", round(r.r1a.mean(), 3), "lo63>0", round((r.lo63 > 0).mean(), 3), "cw>1.65", round((r.cw_t > 1.65).mean(), 3), "cw_t range", round(r.cw_t.min(), 2), round(r.cw_t.max(), 2), "r3", round(r.r3.mean(), 3))
