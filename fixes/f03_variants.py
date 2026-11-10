"""Fix steps 2 and 3 (F2, F3, F4, F7, F8, F9): build alternative ATM30 series on open dates. DEVELOPMENT work on open data.

Usage: python f03_variants.py NAME [NAME ...]
The frozen build_series.series_tables runs unchanged on in-memory inputs. Only the module-level name build_series.term_iv is replaced in memory
(no file is edited). Every variant writes fixes/data/series_NAME.parquet. Columns: atm30 (strict bracket), atm30_floor7 (near term >= 7 days).

Variant parts (chosen once, before any b was computed for them):
  strict   : snapshot where the last row at or before 15:45 sets BOTH bid and ask (fixes/data/strict_snapshot_partial.parquet replaces the stored rows
             on the 432 sessions with any null bid; on all other sessions the two rules are identical).
  spreadNN : keep only strikes whose call+put relative spread (the study's own pair measure) is <= NN/100. Primary NN = 50.
  tier1    : a term that would be Tier 2 gets no IV (so a day needs a bracketed forward in both terms).
  floor7   : use the column atm30_floor7 (the frozen 7-day rule).
  deam     : terms with a cash dividend inside them use the American tree (deam.py). deamC uses confirmed dividends only.
"""
import sys
from math import exp

from common import *  # noqa
import atm_index as atm
import build_series as bs
import config as cfg
import deam
from load_data import day_conditions

SPECS = {
    "base": dict(),
    "strict": dict(strict=True),
    "spread25": dict(cut=0.25), "spread50": dict(cut=0.50), "spread100": dict(cut=1.00),
    "tier1": dict(tier1=True),
    "core": dict(strict=True, cut=0.50, tier1=True),
    "core25": dict(strict=True, cut=0.25, tier1=True),
    "core100": dict(strict=True, cut=1.00, tier1=True),
    "deam": dict(deam="all"),
    "deamC": dict(deam="confirmed"),
    "core_deam": dict(strict=True, cut=0.50, tier1=True, deam="all"),
}

events = cfg.load_cash_events(cfg.DEVELOPMENT_START, cfg.DATA_END)
DIVS = events[events.kind == "dividend"].reset_index(drop=True)
DIVS["confirmed"] = DIVS.basis != "nasdaq_basis_unconfirmed"
diagnostics = pd.read_parquet(DATA / "session_diagnostics.parquet").set_index("session_date")


def load_inputs(strict: bool):
    snapshot = pd.read_parquet(DATA / "option_snapshot_1545.parquet")
    if strict:
        part = pd.read_parquet(FDATA / "strict_snapshot_partial.parquet")
        snapshot = pd.concat([snapshot[~snapshot.session_date.isin(part.session_date.unique())], part[snapshot.columns]], ignore_index=True)
    return snapshot


def tree_term(chain, minutes, rate, session, expiry, inside, orig, log):
    """American-tree term IV for a term with dividends inside it. None if the spot or the pairs are missing (then the frozen recipe runs)."""
    years = minutes / atm.YEAR_MINUTES
    ny = "America/New_York"
    divs = [((pd.Timestamp(f"{d.ex_date.date()} 09:30", tz=ny) - pd.Timestamp(f"{session.date()} 15:45", tz=ny)).total_seconds() / 60 / atm.YEAR_MINUTES, float(d.usd_per_ads))
            for _, d in inside.iterrows()]
    old = orig(chain, minutes, rate)
    stock, source = diagnostics.loc[session, "stock_mid"], "nasdaq_mid"
    if not (stock > 0):
        pairs = atm.two_sided_pairs(chain)
        if pairs.empty:
            return None
        F = atm.parity_forward(pairs, exp(rate * years))
        stock, source = F * exp(-rate * years) + sum(c * exp(-rate * t) for t, c in divs if 0 < t < years), "parity_fallback"
    new = deam.term_iv_american(chain, minutes, rate, float(stock), divs)
    log.append(dict(session_date=session, expiry=expiry, days=minutes / 1440, n_div=len(inside), all_confirmed=bool(inside.confirmed.all()), spot_source=source,
                    stock_age=float(diagnostics.loc[session, "stock_age"]), forward_tree=new["forward"], forward_parity=old["forward"],
                    iv_old=old["iv"], iv_new=new["iv"], tier_old=old["tier"], tier_new=new["tier"], reason_new=new["reason"]))
    return new


def make_term_iv(orig, spec, log):
    cut, tier1, mode = spec.get("cut"), spec.get("tier1", False), spec.get("deam")
    cache = {}

    def wrapped(chain, minutes, rate):
        if cut is not None and len(chain):
            pairs = atm.two_sided_pairs(chain)
            chain = chain[chain.strike.isin(pairs.loc[pairs.relative_spread <= cut, "strike"])]
        result = None
        if mode and len(chain):
            session, expiry = pd.Timestamp(chain.session_date.iloc[0]), pd.Timestamp(chain.expiry.iloc[0])
            inside = DIVS[(DIVS.ex_date > session) & (DIVS.ex_date <= expiry)]
            if len(inside) and (mode == "all" or inside.confirmed.all()):
                key = (session, expiry, len(chain))
                if key not in cache:
                    cache[key] = tree_term(chain, minutes, rate, session, expiry, inside, orig, log)
                result = cache[key]
        if result is None:
            result = orig(chain, minutes, rate)
        if tier1 and result["tier"] == 2:
            result = dict(result, iv=None, reason="tier 2 excluded")
        return result
    return wrapped


def run(name: str):
    spec = SPECS[name]
    log = []
    orig = atm.term_iv
    bs.term_iv = make_term_iv(orig, spec, log)
    bs.term_variance = lambda *a, **k: dict(variance=None, reason="skipped", extrapolated_share=np.nan)  # MF30 is not needed here; faster
    snapshot = load_inputs(spec.get("strict", False))
    listed = pd.read_parquet(DATA / "option_listed.parquet")
    rates = bs.session_rates(diagnostics.index.sort_values())
    ev = events
    series, terms, dups = bs.series_tables(snapshot, listed, diagnostics, rates, ev.loc[ev.kind == "dividend", "ex_date"].values, ev.loc[ev.kind == "rights", "ex_date"].values,
                                           day_conditions(cfg.OPTION_CBBO), day_conditions(cfg.EQUITY_BBO))
    series.to_parquet(FDATA / f"series_{name}.parquet", index=False)
    terms.to_parquet(FDATA / f"terms_{name}.parquet", index=False)
    if log:
        pd.DataFrame(log).to_csv(HERE / f"f03_deam_terms_{name}.csv", index=False)
    print(name, "done: valid atm30", int(series.atm30.notna().sum()), " valid floor7", int(series.atm30_floor7.notna().sum()), " deam terms", len(log), flush=True)


if __name__ == "__main__":
    print(LABEL)
    for nm in sys.argv[1:]:
        run(nm)
