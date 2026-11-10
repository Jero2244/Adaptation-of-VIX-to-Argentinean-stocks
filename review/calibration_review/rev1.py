import sys
sys.dont_write_bytecode = True
import json, hashlib
from pathlib import Path
import numpy as np, pandas as pd
P = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.path.insert(0, str(P / "calibration")); sys.path.insert(0, str(P))
import calib_core as cc, calib_run as run, calib_post as post
import forecasts as fc, stage4_rules as rules, events as ev

print("== hashes vs manifest")
man = json.loads((P/"reports/calib_freeze_manifest.json").read_text(encoding="utf-8"))["files"]
now = run.manifest_now()
for k in man: print(k, man[k] == now[k])
res = json.loads((P/"reports/calib_results.json").read_text(encoding="utf-8"))
print("changed", res["changed_since_freeze"], "keys", list(res))
print("c1 open", {k:v for k,v in res["c1"]["open"].items()})
print("c1 test", {k:v for k,v in res["c1"]["test"].items()})

op = run.load_period("open"); te = run.load_period("test")
for name, f in (("open",op),("test",te)):
    print(name, "pos contiguous", (np.diff(f["position"])==1).all(), "pos0", f["position"].iloc[0], "index==pos", (f.index.to_numpy()==f["position"].to_numpy()).all(), f["session_date"].iloc[0], f["session_date"].iloc[-1], len(f))
    print(" tier values", f["tier"].value_counts(dropna=False).to_dict())
    gaps = pd.Series(f["session_date"]).diff().dt.days
    print(" max session gap days", gaps.max())
    print(" median atm30 valid", f.loc[f.valid,"atm30"].median(), "mean", f.loc[f.valid,"atm30"].mean())

print("== recompute primary")
z, pos = run.rows_of(op)
print(len(z), cc.measures_from_z(z))
rows = op[op.valid].copy()
# compare with saved panel
pan = pd.read_parquet(P/"data/calibration_panel.parquet")
print("panel z same", np.allclose(pan.loc[pan.valid,"z"], z), len(pan))

print("== independent z from raw daily closes")
daily = pd.read_parquet(P/"data/equity_official_daily.parquet")
print(daily.columns.tolist()[:8])
cash = pd.read_csv(P/"data/adr_cash_events.csv")
print(cash.columns.tolist(), len(cash))
d = daily.sort_values("session_date").reset_index(drop=True)
d["session_date"] = pd.to_datetime(d["session_date"])
cash["ex_date"] = pd.to_datetime(cash["ex_date"])
c = cash.groupby("ex_date")["usd_per_ads"].sum()
d["cash"] = d["session_date"].map(c).fillna(0.0)
d["tr"] = (d["official_close_price"] + d["cash"]) / d["official_close_price"].shift(1)
d["ci"] = np.log(d["tr"]).fillna(0).cumsum()
mm = d.set_index("session_date")["ci"]
sess = d["session_date"]
out = []
for i, row in rows.sample(400, random_state=1).iterrows():
    t = row.session_date; e = t + pd.Timedelta(days=30)
    last = sess[sess <= e].iloc[-1]
    R = mm[last] - mm[t]
    out.append(R - row.R)
print("indep R diff max", np.max(np.abs(out)))
print("cash kinds", cash.get("kind").value_counts().to_dict() if "kind" in cash else None)
print("cash on ex in panel total", op[["dividend_cash","rights_cash"]].sum().to_dict() if "dividend_cash" in op else None, "csv", cash[(cash.ex_date>=op.session_date.iloc[0])&(cash.ex_date<=op.session_date.iloc[-1])].usd_per_ads.sum())
print("outcome_days dist", pd.Series((rows["outcome_end"]-rows["session_date"]).dt.days).describe().to_dict())
print("mean days ratio", ((rows["outcome_end"]-rows["session_date"]).dt.days/30).mean())
rows["z_true_T"] = (rows.R - (rows.r*(rows.outcome_end-rows.session_date).dt.days/365 - rows.atm30**2*(rows.outcome_end-rows.session_date).dt.days/365/2))/(rows.atm30*np.sqrt((rows.outcome_end-rows.session_date).dt.days/365))
print("z with actual window T", cc.measures_from_z(rows.z_true_T.to_numpy()))

print("== conditional calibration by ATM30 quintile")
rows["q"] = pd.qcut(rows.atm30, 5, labels=False)
rows["abs"] = rows.z.abs()
g = rows.groupby("q").agg(n=("z","size"), atm=("atm30","mean"), inner=("abs",lambda x:(x<1).mean()), outer=("abs",lambda x:(x<2).mean()), z2=("z",lambda x:(x**2).mean()), absz=("abs","mean"), medabs=("abs","median"))
print(g.round(3).to_string())
for lab, mask in (("no PASO", ~post.one_event(op, ev.EVENTS,"2019 PASO")[op.valid.to_numpy()]),):
    r2 = rows[mask]; print(lab); print(r2.groupby("q").agg(n=("z","size"), inner=("abs",lambda x:(x<1).mean()), outer=("abs",lambda x:(x<2).mean()), z2=("z",lambda x:(x**2).mean())).round(3).to_string())
print("median |z| / .6745 =", rows["abs"].median()/0.67449, "no-event:", )
print("== by year")
rows["y"] = rows.session_date.dt.year
print(rows.groupby("y").agg(n=("z","size"), atm=("atm30","median"), inner=("abs",lambda x:(x<1).mean()), outer=("abs",lambda x:(x<2).mean()), z2=("z",lambda x:(x**2).mean()), mz=("z","mean")).round(3).to_string())
# rolling
rz = rows.set_index("session_date")["z"]
ri = (rz.abs()<1).astype(float).rolling("365D",min_periods=126).mean(); ro=(rz.abs()<2).astype(float).rolling("365D",min_periods=126).mean()
print("rolling inner range", ri.min(), ri.max(), "outer", ro.min(), ro.max())
print("share of time rolling inner outside +-10pts", ((ri-cc.INNER).abs()>0.10).mean())
# bootstrap test of inner by ATM bottom vs top quintile
pos_all = rows.position.to_numpy(); hit=(rows["abs"]<1).to_numpy().astype(float); q=rows.q.to_numpy()
for block in (21,63):
    draws = cc.inf.block_bootstrap(lambda i: np.array([hit[i][q[i]==0].mean()-hit[i][q[i]==4].mean()]), pos_all, block, 1000, cc.SEED+block)[:,0]
    print("inner q1 minus q5", hit[q==0].mean()-hit[q==4].mean(), block, np.percentile(draws,[2.5,97.5]))
for qi in (0,4):
    print("q",qi, cc.measure_table(rows.z.to_numpy()[q==qi], pos_all[q==qi], reps=500)["inner"])

print("== missing rows: selection")
f = op
hasR = f.R.notna() & ~f.flag_half_day
blank = f[hasR & f.atm30.isna()]
print("complete-window rows w/o z", (f.R.notna() & ~f.valid).sum(), "blank atm", len(blank))
print("mean |R| valid", f.loc[f.valid,"R"].abs().mean(), "blank", blank.R.abs().mean(), "rv30 median valid", f.loc[f.valid,"rv30"].median(), "blank", blank.rv30.median())
print("|R|>20% share valid", (np.exp(f.loc[f.valid,'R'])-1).abs().gt(.2).mean(), "blank", (np.exp(blank.R)-1).abs().gt(.2).mean())
print(blank.groupby(blank.session_date.dt.year).size().to_dict())
print("paso-window sessions", post.one_event(f, ev.EVENTS,"2019 PASO").sum(), "valid in", (post.one_event(f, ev.EVENTS,"2019 PASO")&f.valid.to_numpy()).sum())
for name,_ in ev.EVENTS:
    m=post.one_event(f,ev.EVENTS,name); print(name,m.sum(),(m&f.valid.to_numpy()).sum())

print("== event mask vs rules.without_events")
events = [ev.first_session(d, f.session_date.to_numpy()) for _,d in ev.EVENTS]
vf = f[f.valid]
print(len(rules.without_events(vf, events)), (~run.event_mask(f, ev.EVENTS)[f.valid.to_numpy()]).sum(), "events inside", run.event_mask(f, ev.EVENTS)[f.valid.to_numpy()].sum())

print("== common rows")
found, common = run.benchmark_predictives(f)
print("common", common.sum(), "first", f.session_date[common].iloc[0])
pastmask = np.isfinite(post.past_base_rate(f, cc.move_happened(f.R.to_numpy(),0.1)))
print("past base rows", pastmask.sum(), "same set as common", (pastmask==common).all(), "xor", (pastmask^common).sum())
print("k first/quantiles", np.nanpercentile(found["k"][common],[0,10,50,90,100]))
cu = f.session_date[common].to_numpy()
ks = pd.Series(found["k"][common], index=cu)
print(ks.resample("YE").last().round(3).to_dict())
print("nu dist", pd.Series(found["nu"][common]).value_counts().to_dict())

print("== look-ahead perturbation on real panel")
origins=[400,800,1200,1800]
ends=cc.past_end_positions(f)
for o in origins:
    pert=f.copy()
    # destroy everything not observable at origin o: R, z, rv30 of rows whose window ends after origin date; and all later rows' inputs
    later=np.arange(len(f))>=ends[o]
    pert.loc[later,"z"]=pert.loc[later,"z"]*0+50.0
    pert.loc[later,"R"]=9.0
    v=f.valid.to_numpy()
    k0,k1=cc.expanding_scale(f)[o],cc.expanding_scale(pert)[o]
    n0,n1=cc.expanding_nu(f)[o],cc.expanding_nu(pert)[o]
    h0=post.past_base_rate(f,cc.move_happened(f.R.to_numpy(),.1))[o]; h1=post.past_base_rate(pert,cc.move_happened(pert.R.to_numpy(),.1))[o]
    pr=f.copy(); fut=f["window_end"]>f.session_date.iloc[o]
    pr.loc[fut,"rv30"]=pr.loc[fut,"rv30"]*1000
    prim=f.primary.to_numpy(); sc=np.zeros(len(f),bool); sc[o]=prim[o]
    a=fc.expanding_forecasts(f,rules.HAR,prim,sc,smearing=True)[o]; b=fc.expanding_forecasts(pr,rules.HAR,prim,sc,smearing=True)[o]
    print(o, f.session_date.iloc[o].date(), "valid",v[o],"k",k0==k1,"nu",n0==n1,"base",h0==h1,"HAR",a==b, "last past end", f.outcome_end.iloc[ends[o]-1].date())
sel=f.index[f.R.notna()][:3]
print("window_end vs outcome rule", ((f.session_date+pd.Timedelta(days=30))==f.window_end).all())
print("primary uses atm:", (f.primary & f.atm30.isna()).sum())
