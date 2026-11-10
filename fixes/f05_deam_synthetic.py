"""Fix step 4 (F2), validation on synthetic prices. DEVELOPMENT work. No project data is read.

Prices: CRR American tree with 1000 steps (generator), one cash dividend at mid-term, known flat vol. The frozen recipe (atm_index.term_iv on the
quotes) and the new recipe (deam.term_iv_american, 400 steps, known spot and dividend) are run on the same quotes. Tight quotes are price*(1 +- 0.0001).
Wide quotes (+-2% around the price) show how the new recipe copes with a band.
Criterion fixed before the run: recovered vol within 1% of true vol where the frozen recipe is off by 2% to 13% (absolute).
"""
from common import *  # noqa
import atm_index as atm
import deam

rows = []
for S, step in ((30.0, 1.0), (10.0, 2.5), (60.0, 5.0)):
    for sigma in (0.45, 0.65, 1.0):
        for days in (10, 20, 30, 45):
            for r in (0.02, 0.05):
                for dy in (0.0, 0.02, 0.035):
                    T = days / 365
                    div, t_div = dy * S, T / 2
                    divs = [(t_div, div)] if div > 0 else []
                    strikes = [k for k in np.arange(step, 3 * S, step) if abs(np.log(k / S)) < 0.25]
                    chain = []
                    for K in strikes:
                        for right in "CP":
                            p = deam.crr_american(S, K, T, r, sigma, divs, right, 1000)
                            chain.append(dict(strike=K, right=right, mid=p))
                    ch = pd.DataFrame(chain)
                    for band, label in ((1e-4, "tight"), (0.02, "wide")):
                        q = ch.assign(bid=ch.mid * (1 - band), ask=ch.mid * (1 + band), age=0.0)
                        old = atm.term_iv(q, int(days * 1440), r)
                        new = deam.term_iv_american(q, int(days * 1440), r, S, divs)
                        rows.append(dict(S=S, step=step, sigma=sigma, days=days, r=r, div_yield=dy, quotes=label,
                                         old_err=old["iv"] / sigma - 1 if old["iv"] else np.nan,
                                         new_err=new["iv"] / sigma - 1 if new["iv"] else np.nan, new_tier=new["tier"]))
out = pd.DataFrame(rows)
out.to_csv(HERE / "f05_deam_synthetic.csv", index=False)
print(LABEL)
t = out[out.quotes == "tight"]
print("\nMean relative error of term IV (recovered/true - 1), tight quotes, by dividend yield and days: OLD frozen recipe")
print(t.pivot_table(index="div_yield", columns="days", values="old_err", aggfunc="mean").round(4).to_string())
print("NEW American-tree recipe")
print(t.pivot_table(index="div_yield", columns="days", values="new_err", aggfunc="mean").round(4).to_string())
print("\nMax |error| by dividend yield and days: OLD, then NEW")
print(t.pivot_table(index="div_yield", columns="days", values="old_err", aggfunc=lambda s: s.abs().max()).round(4).to_string())
print(t.pivot_table(index="div_yield", columns="days", values="new_err", aggfunc=lambda s: s.abs().max()).round(4).to_string())
sel = t[(t.old_err.abs() >= 0.02) & (t.old_err.abs() <= 0.13)]
print(f"\nCases where the frozen recipe is off by 2% to 13%: {len(sel)} of {len(t)}")
print("  new recipe |error|: mean %.4f, median %.4f, 95th pct %.4f, max %.4f; share within 1%%: %.3f" % (sel.new_err.abs().mean(), sel.new_err.abs().median(), sel.new_err.abs().quantile(.95), sel.new_err.abs().max(), (sel.new_err.abs() <= 0.01).mean()))
print("  old recipe |error| in the same cases: mean %.4f, max %.4f" % (sel.old_err.abs().mean(), sel.old_err.abs().max()))
print("All tight cases: new |error| max %.4f, share within 1%%: %.3f; missing: %d" % (t.new_err.abs().max(), (t.new_err.abs() <= 0.01).mean(), int(t.new_err.isna().sum())))
bad = sel[sel.new_err.abs() > 0.01]
if len(bad):
    print("Cases outside 1%:\n", bad.round(4).to_string())
w = out[out.quotes == "wide"]
print("\nWide quotes (+-2%% around the American price): new |error| mean %.4f, max %.4f; old |error| mean %.4f, max %.4f" % (w.new_err.abs().mean(), w.new_err.abs().max(), w.old_err.abs().mean(), w.old_err.abs().max()))
