import sys
sys.dont_write_bytecode = True
import json, unittest
from pathlib import Path
import numpy as np, pandas as pd
P = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.path.insert(0, str(P / "calibration")); sys.path.insert(0, str(P))
import calib_core as cc, calib_run as run, calib_post as post
import events as ev, test_calib
res = json.loads((P/"reports/calib_results.json").read_text(encoding="utf-8"))
c2,c3,po=res["c2"],res["c3"],res["post_result"]
print("PIT 21 outside 10%", [(i,round(l,3),round(h,3)) for i,(l,h) in enumerate(zip(c2["pit"]["low21"],c2["pit"]["high21"])) if not l<=.1<=h])
print("PIT 63 outside", [(i) for i,(l,h) in enumerate(zip(c2["pit"]["low63"],c2["pit"]["high63"])) if not l<=.1<=h])
print("base rate", json.dumps(po["brier_against_base_rate"],indent=0)[:900])
for x in ("0.1","0.2"):
    print("nopaso rel",x,[(g["n"],round(g["mean_probability"],3),round(g["observed"],3)) for g in po["reliability_no_2019_paso"][x]["groups"]], po["reliability_no_2019_paso"][x]["brier"])
m=c3["benchmarks"]["methods"]
for n,e in m.items():
    print(n,"mean_s",round(e["mean_s"],4),"pit",[round(v,3) for v in e["pit"]])
    print("  scores",{k:(round(v["mean"],4),round(v["difference"],4),round(v["low21"],4),round(v["high21"],4),round(v["low63"],4),round(v["high63"],4)) for k,v in e["scores"].items()})
    print("  brier",{k:(round(v["mean"],4),round(v["difference"],4),round(v["low21"],4),round(v["high21"],4)) for k,v in e["brier"].items()})
    print("  inner",{k:round(v,3) for k,v in e["inner"].items()}, "outer",{k:round(v,3) for k,v in e["outer"].items()})
print("no paso table", {k:(po["no_2019_paso"][k]["value"],po["no_2019_paso"][k]["low63"],po["no_2019_paso"][k]["high63"]) for k in cc.MEASURES})

op=run.load_period("open")
paso=post.one_event(op,ev.EVENTS,"2019 PASO")
found,common=run.benchmark_predictives(op)
rows=op[common]; R=rows.R.to_numpy(); pos=rows.position.to_numpy()
r=op.r.to_numpy(); s=op.s.to_numpy()
# scaled with PASO windows removed from the fit of k
f2=op.copy(); f2.loc[paso,"valid"]=False
k2=cc.expanding_scale(f2)
# k undefined at PASO origins now; fill from original rule on those rows
k2=np.where(np.isfinite(k2),k2,found["k"])
print("k without PASO quantiles", np.nanpercentile(k2[common],[0,50,100]), "final", k2[common][-1])
for name,k in (("orig k",found["k"]),("k no PASO in fit",k2)):
    p=cc.normal_band(r,k*s).take(common)
    z=(R-p.loc)/p.s
    print(name, "inner",np.mean(abs(z)<1),"outer",np.mean(abs(z)<2),"z2",np.mean(z**2))
    base=cc.row_scores(found["methods"]["ATM30"].take(common),R); sc=cc.row_scores(p,R)
    for key in sc:
        d=sc[key]-base[key]; part=cc.intervals_for(lambda i:np.array([d[i].mean()]),pos,reps=500)
        print("  ",key,round(d.mean(),4),round(float(part[63]["low"][0]),4),round(float(part[63]["high"][0]),4))
# common rows excl PASO: ATM30 z2 vs HAR Duan
keep=~paso[common]
for n in found["methods"]:
    p=found["methods"][n].take(common); z=(R-p.loc)/p.s
    print(n,"common no PASO inner",round(np.mean(abs(z[keep])<1),3),"outer",round(np.mean(abs(z[keep])<2),3),"z2",round(np.mean(z[keep]**2),3))
# scores on common rows without PASO
base=cc.row_scores(found["methods"]["ATM30"].take(common),R)
for n in found["methods"]:
    if n=="ATM30": continue
    sc=cc.row_scores(found["methods"][n].take(common),R)
    print(n,"score diff no PASO",{k:round((sc[k]-base[k])[keep].mean(),4) for k in sc})
# t quantile facts
from scipy import stats
for nu in (5,6):
    print("nu",nu,"unit-t half widths at inner/outer",stats.t.ppf(.5+cc.INNER/2,nu)*cc.unit_t_scale(nu),stats.t.ppf(.5+cc.OUTER/2,nu)*cc.unit_t_scale(nu))
# exact expected inner in the simulator, from window lengths on the bdate grid
import calib_synthetic as syn
rng=np.random.default_rng(1)
fr=syn.simulate(rng); v=fr[fr.valid]
days=(v.outcome_end-v.session_date).dt.days.to_numpy()
tau=days/365; sd=.6*np.sqrt(tau); mean=(.03-.18)*tau; m=v.m.to_numpy(); s0=v.s.to_numpy()
pin=stats.norm.cdf((m+s0-mean)/sd)-stats.norm.cdf((m-s0-mean)/sd); pout=stats.norm.cdf((m+2*s0-mean)/sd)-stats.norm.cdf((m-2*s0-mean)/sd)
print("simulator mean days",days.mean(),"exact inner",pin.mean(),"exact outer",pout.mean(),"exact z2",np.mean((sd**2+(mean-m)**2)/s0**2))
print("note test 4*se tolerance inner", 4*0.00221)
# test
suite=unittest.defaultTestLoader.loadTestsFromModule(test_calib)
r=unittest.TextTestRunner(verbosity=0).run(suite); print("tests",r.testsRun,len(r.failures),len(r.errors))
# selection difference bootstrap
f=op
ok=f.R.notna().to_numpy()&~f.flag_half_day.to_numpy()
big=(np.abs(np.exp(f.R.to_numpy())-1)>.2)
blank=f.atm30.isna().to_numpy()
idx=np.flatnonzero(ok); b=blank[idx]; g=big[idx].astype(float); p2=f.position.to_numpy()[idx]
for bl in (21,63):
    d=cc.inf.block_bootstrap(lambda i:np.array([g[i][b[i]].mean()-g[i][~b[i]].mean()]),p2,bl,1000,cc.SEED+bl)[:,0]
    print("blank minus valid share >20% move",g[b].mean()-g[~b].mean(),bl,np.percentile(d,[2.5,97.5]))
