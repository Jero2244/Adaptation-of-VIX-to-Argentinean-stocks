"""Search derived files for rows before 2018-05-01. Prints only file name, row count before 2018-05-01 as a boolean, and never a value. Skips the forbidden files."""
import _common
from _common import ROOT
import pandas as pd, pyarrow.parquet as pq
SKIP = {"fred_rates_test.csv","adr_cash_events.csv","adr_dividend_ledger.csv","ggal_cash_dividends_2016_2026.csv","alpaca_corporate_actions.json","alpaca_ggal_sip_raw.json"}
LIM = pd.Timestamp("2018-05-01")
for folder in ["data","reports","review"]:
    for p in sorted((ROOT/folder).rglob("*")):
        if p.name in SKIP or "stage5_check" in str(p) or not p.is_file(): continue
        try:
            if p.suffix==".parquet":
                cols = pq.read_schema(p).names
                c = [x for x in cols if x in ("session_date","date","ts_recv","ex_date")]
                if not c: print("no date col", p.relative_to(ROOT)); continue
                d = pd.to_datetime(pd.read_parquet(p, columns=c[:1]).iloc[:,0])
                if d.dt.tz is not None: d=d.dt.tz_localize(None)
            elif p.suffix==".csv":
                h = pd.read_csv(p, nrows=0).columns
                c = [x for x in h if x in ("session_date","date","start","first","ex_date","observation_date")]
                if not c: continue
                d = pd.to_datetime(pd.read_csv(p, usecols=c[:1]).iloc[:,0], errors="coerce", format="mixed")
            else: continue
            if (d<LIM).any(): print("HAS EARLIER ROWS (values not shown):", p.relative_to(ROOT), c[:1])
        except Exception as e:
            print("skip", p.relative_to(ROOT), type(e).__name__)
print("done")
