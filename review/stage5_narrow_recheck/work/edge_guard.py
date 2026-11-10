"""Edge cases of no_forward_gaps and input_guard on a code copy. Synthetic values only."""
import sys, warnings
from common import make_copy, HERE
d = make_copy("eg"); sys.path.insert(0, str(d))
import numpy as np, pandas as pd
import run_tests_once as rt
SECRET = 987.654
def base(n=100, f=50.0, c=50.0):
    return pd.DataFrame(dict(session_date=pd.bdate_range("2017-01-02", periods=n), near_forward=f, close=c))
def go(p, name):
    try:
        rt.input_guard(p, 0, 0); print(f"{name:52s} pass")
    except rt.InputGuardFailed as e:
        print(f"{name:52s} STOP [{str(e)[:44]}] dates={e.dates[:6]}{'...' if len(e.dates)>6 else ''} n={len(e.dates)} secret={'987' in str(e)}")
def oracle(p):
    o = p.sort_values("session_date").reset_index(drop=True); out = {}
    fw, cl, dt = o.near_forward.to_numpy(), o.close.to_numpy(), o.session_date.to_numpy()
    for i in range(len(o)):
        if np.isnan(fw[i]) and not np.isnan(cl[i]):
            gaps = []
            for j in range(i-1, -1, -1):
                if not np.isnan(fw[j]): gaps.append(abs(np.log(cl[i]/fw[j]))); break
            for j in range(i+1, len(o)):
                if not np.isnan(fw[j]): gaps.append(abs(np.log(cl[i]/fw[j]))); break
            out[pd.Timestamp(dt[i])] = min(gaps) if gaps else np.nan
    return out
rng = np.random.default_rng(1); bad = 0; n_checked = 0; fires = 0
for trial in range(1500):
    n = int(rng.integers(2, 60))
    c = 50*np.exp(np.cumsum(rng.normal(0, .08, n)))
    f = c*np.exp(rng.normal(0, .002, n))
    blank = rng.random(n) < rng.choice([.1, .5, .9, .98])
    f = np.where(blank, np.nan, f)
    if rng.random() < .1: c[rng.integers(n)] = np.nan
    p = pd.DataFrame(dict(session_date=pd.bdate_range("2017-01-02", periods=n), near_forward=f, close=c))
    if trial % 3 == 1: p = p.sample(frac=1, random_state=trial)
    if trial % 3 == 2: p = p.sample(frac=1, random_state=trial).set_axis(rng.permutation(n)*7+3)
    got = rt.no_forward_gaps(p); want = oracle(p)
    g = {pd.Timestamp(p.loc[i, "session_date"]): v for i, v in got.items()}
    n_checked += 1
    if set(g) != set(want) or any(not (np.isclose(g[k], want[k]) or (np.isnan(g[k]) and np.isnan(want[k]))) for k in g):
        bad += 1
    fires += sum(v > .15 for v in g.values())
print("oracle trials", n_checked, "disagreements", bad, "sessions above limit", fires)
p = base(); p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = SECRET
go(p, "one stray")
go(p.sample(frac=1, random_state=3), "one stray, shuffled")
q = p.sample(frac=1, random_state=3).set_axis(range(1000, 1100)); go(q, "one stray, shuffled, odd index")
q = p.copy(); q.index = [0]*100; go(q, "one stray, all index labels equal (not reachable)")
p = base()
for i in (10, 11, 40, 41, 42, 80): p.loc[i, "near_forward"] = np.nan
p.loc[11, "close"] = 75; p.loc[41, "close"] = 30; go(p, "several blank runs, two strays")
p = base().assign(near_forward=np.nan); p.loc[50, "near_forward"] = 50.0; go(p, "all blank but one, all near")
p.loc[0, "close"] = 75.0; p.loc[99, "close"] = 75.0; go(p, "all blank but one, strays at both edges")
p = base().assign(near_forward=np.nan); p.loc[0, "near_forward"] = 50.0; p.loc[99, "close"] = 75.0; go(p, "only forward first, stray last")
p = base(); p.loc[0:2, "near_forward"] = np.nan; p.loc[0, "close"] = 75.0; go(p, "leading run, stray first")
p = base(); p.loc[97:99, "near_forward"] = np.nan; p.loc[99, "close"] = 75.0; go(p, "trailing run, stray last")
p = base(); p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = 50*np.exp(.15); go(p, "gap equal to .15 (float)")
p = base(); p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = np.inf; go(p, "inf close on no-forward session")
p = base(); p.loc[50, "close"] = np.inf; go(p, "inf close with forward")
p = base(); p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = np.nan; go(p, "NaN close and NaN forward")
warnings.simplefilter("ignore")
p = base(); p.loc[50, "near_forward"] = -50.0; go(p, "negative forward")
p = base(); p.loc[50, "near_forward"] = 0.0; go(p, "zero forward")
p = base(); p.loc[50, "near_forward"] = np.inf; go(p, "inf forward")
p = base(); p.loc[49, "near_forward"] = -50.0; p.loc[51, "near_forward"] = -50.0; p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = 75; go(p, "stray between two negative forwards")
p = base(); p.loc[49, "near_forward"] = 0.0; p.loc[50, "near_forward"] = np.nan; go(p, "no-forward next to zero forward")
p = base(); p.loc[50, "near_forward"] = np.nan; p.loc[50, "close"] = 75; p["near_forward"] = p["near_forward"]*1.03; go(p, "median and stray both: first check names")
p = base(n=61); c = 50*np.exp(np.r_[np.linspace(0, .4, 31), np.linspace(.4, .0, 30)]); p["close"] = c; p["near_forward"] = c; p.loc[1:59, "near_forward"] = np.nan; go(p, "long blank run, real up and down move .40")
p = base(); p["near_forward"] = p["near_forward"].astype(object); p.loc[50, "near_forward"] = None
try:
    go(p, "object dtype forward")
except Exception as e:
    print("object dtype forward raises", type(e).__name__)
