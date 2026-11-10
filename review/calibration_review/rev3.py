"""Coverage of inner, outer, mean z2 intervals: real gap pattern; with and without rare event jumps. Forward rule with gaps. Read-only."""
import sys
sys.dont_write_bytecode = True
from pathlib import Path
import numpy as np, pandas as pd
P = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.path.insert(0, str(P / "calibration")); sys.path.insert(0, str(P))
import calib_core as cc, calib_synthetic as syn, inference as inf

panel = pd.read_parquet(P/"data/calibration_panel.parquet")
mask = panel["valid"].to_numpy()  # real pattern of usable origins, no values used
N = len(mask); print("N", N, "valid", mask.sum())
SIMS, REPS = 200, 500
J = 0.33

def sim_z(rng, sessions, jump=False):
    dates = pd.bdate_range("2018-05-01", periods=sessions)
    dt = (np.diff(dates.to_numpy())/np.timedelta64(1,"D"))/365
    ret = (syn.RATE-syn.VOL**2/2)*dt + syn.VOL*np.sqrt(dt)*rng.standard_normal(sessions-1)
    if jump:
        where = rng.choice(sessions-1, size=max(1, round(9*sessions/N)), replace=False)
        ret[where] += J*rng.standard_normal(len(where))
    f = pd.DataFrame({"position":np.arange(sessions),"session_date":dates,"return_total":np.r_[np.nan,ret],"atm30":syn.VOL,"flag_half_day":False})
    return cc.build_calibration(f, np.full(sessions, syn.RATE))["z"].to_numpy()

def measures(z): return np.array([np.mean(np.abs(z)<1), np.mean(np.abs(z)<2), np.mean(z**2)])

def run_case(name, jump, sessions, gaps, seed, sims=SIMS):
    rng = np.random.default_rng(seed)
    start_choices = np.arange(0, max(1, N-sessions))
    ests, draws = [], {21:[],63:[]}
    for s in range(sims):
        z = sim_z(rng, sessions, jump)
        use = np.isfinite(z)
        if gaps:
            st = rng.choice(start_choices) if sessions < N else 0
            use &= mask[st:st+sessions]
        zz, pos = z[use], np.flatnonzero(use)
        ests.append(measures(zz))
        for b in cc.BLOCKS:
            d = inf.block_bootstrap(lambda i: measures(zz[i]), pos, b, REPS, seed+1000*s+b)
            draws[b].append(np.percentile(d,[2.5,97.5],axis=0))
    ests = np.array(ests); truth = ests.mean(axis=0)
    out = {"truth":truth.round(4).tolist(),"sd_est":ests.std(axis=0).round(4).tolist(),"rows":int(use.sum())}
    for b in cc.BLOCKS:
        a = np.array(draws[b])  # sims,2,3
        out[f"cover{b}"] = ((a[:,0]<=truth)&(truth<=a[:,1])).mean(axis=0).round(3).tolist()
    fired = np.array([(draws[21][i][0,0]>cc.INNER or draws[21][i][1,0]<cc.INNER) and (draws[63][i][0,0]>cc.INNER or draws[63][i][1,0]<cc.INNER) for i in range(sims)])
    out["fires"]=float(fired.mean())
    print(name, out, flush=True)

run_case("const contiguous full", False, N, False, 11)
run_case("const real gaps full", False, N, True, 12)
run_case("jump real gaps full", True, N, True, 13)
run_case("const contiguous 252", False, 252+22, False, 14)
run_case("const real gaps 252", False, 252+22, True, 15)
run_case("jump real gaps 252", True, 252+22, True, 16)
