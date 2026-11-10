"""Fix step 1: reproduce the stored baseline with the variant engine before anything else. DEVELOPMENT work on open data."""
from common import *  # noqa
import build_series as bs
import config as cfg
from load_data import day_conditions

if __name__ == "__main__":
    print(LABEL)
    snapshot = pd.read_parquet(DATA / "option_snapshot_1545.parquet")
    listed = pd.read_parquet(DATA / "option_listed.parquet")
    diagnostics = pd.read_parquet(DATA / "session_diagnostics.parquet").set_index("session_date")
    events = cfg.load_cash_events(cfg.DEVELOPMENT_START, cfg.DATA_END)
    div = events.loc[events.kind == "dividend", "ex_date"].values
    rts = events.loc[events.kind == "rights", "ex_date"].values
    rates = bs.session_rates(diagnostics.index.sort_values())
    series, terms, dups = bs.series_tables(snapshot, listed, diagnostics, rates, div, rts, day_conditions(cfg.OPTION_CBBO), day_conditions(cfg.EQUITY_BBO))
    stored = pd.read_parquet(DATA / "index_series.parquet")
    m = series.merge(stored[["session_date", "atm30", "atm30_floor7"]], on="session_date", suffixes=("", "_stored"))
    both = m.atm30.notna() & m.atm30_stored.notna()
    print("sessions", len(m), " valid mine", int(m.atm30.notna().sum()), " valid stored", int(m.atm30_stored.notna().sum()), " presence mismatch", int((m.atm30.notna() != m.atm30_stored.notna()).sum()))
    print("max |mine - stored| ATM30:", float((m.atm30[both] - m.atm30_stored[both]).abs().max()))
    series.to_parquet(FDATA / "baseline_rebuilt_series.parquet", index=False)
    panel = make_panel(series)
    p = panel[panel.primary]
    print("primary origins", len(p))
    r = fit_b(p)
    print({k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()})
    print("stored: b .622, intervals .337 to .916 (21), .309 to .946 (63)")
