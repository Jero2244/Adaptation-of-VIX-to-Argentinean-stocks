"""Summary of a7_*.csv and the critic fixed-step row counts. Reads no project data."""
import glob
import pandas as pd
pd.set_option("display.width", 250, "display.max_columns", 40)
r = pd.concat(pd.read_csv(f) for f in glob.glob("a7_20*.csv"))
r["i21"] = r.lo21 > 0
r["i63"] = r.lo63 > 0
r["both"] = r.i21 & r.i63
r["below21"] = r.hi21 < .37
r["below_both"] = (r.hi21 < .37) & (r.hi63 < .37)
print(r.groupby(["cover", "outer", "true_b"]).agg(n=("n", "median"), reps=("b", "size"), sd=("b", "std"), se21=("se21", "median"), se63=("se63", "median"), i21=("i21", "mean"), i63=("i63", "mean"), both=("both", "mean"), below21=("below21", "mean"), below_both=("below_both", "mean")).round(3).to_string())
g = r.groupby(["start", "cover", "outer", "true_b"]).agg(sd=("b", "std"), se21=("se21", "median"), se63=("se63", "median"))
print("sd over se21", (g.sd / g.se21).groupby(["cover", "outer"]).mean().round(2).to_dict(), "sd over se63", (g.sd / g.se63).groupby(["cover", "outer"]).mean().round(2).to_dict())
s = pd.read_csv("../critic/c2_dryrun.csv")
print("critic windows: fixed-step median rows min", s.fsn_med.min(), "below 20:", int((s.fsn_med < 20).sum()), "below 17:", int((s.fsn_med < 17).sum()), "of", len(s), "| Supported below 17:", int(((s.fsn_med < 17) & s.S).sum()))
