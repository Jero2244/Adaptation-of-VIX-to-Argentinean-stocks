"""Edges on synthetic data and temporary paths. No real marker and no locked member is read: the 2017 names below are in a fake zip made here."""
import _common, json, tempfile, zipfile
from pathlib import Path
import numpy as np, pandas as pd
import build_snapshot as bs, load_data as ld, stage4_rules as rules, realized as rz
from build_series import series_tables, session_rates
from config import MARKER_PURPOSE, BlockedPeriod, require_open

NY = "America/New_York"
tmp = Path(tempfile.mkdtemp())

print("== A. iter_days with a fake zip and a valid or invalid marker")
z = tmp / "fake.zip"
with zipfile.ZipFile(z, "w") as a:
    a.writestr("opra-pillar-20170301.cbbo-1m.dbn.zst", b"x")
    a.writestr("opra-pillar-20180501.cbbo-1m.dbn.zst", b"x")
    a.writestr("condition.json", "[]")
seen = []
orig = ld.read_member
ld.read_member = lambda archive, name, map_symbols=True: seen.append(name) or pd.DataFrame()
m = tmp / "m.json"
m.write_text(json.dumps(dict(purpose=MARKER_PURPOSE, scope="options", approved_by="user", approved_on="2026-11-04")))
print("valid options marker:", [d for d, _ in ld.iter_days(z, "2016-01-01", "2018-04-30", marker=m)])
n = tmp / "o.json"
n.write_text(json.dumps(dict(purpose=MARKER_PURPOSE, scope="outcomes", approved_by="user", approved_on="2026-11-04")))
for label, marker in (("no marker", None), ("outcomes marker on the options scope", n), ("directory as marker", tmp)):
    try:
        list(ld.iter_days(z, "2016-01-01", "2018-04-30", marker=marker))
        print(label, "OPENED")
    except BlockedPeriod:
        print(label, "blocked")
print("open read with no marker sees only the open member:", [d for d, _ in ld.iter_days(z, "2018-05-01", "2018-05-02")])
ld.read_member = orig
for start in ("2018-04-30", pd.Timestamp("2018-04-30 23:59"), "2018-05-01"):
    try:
        print("require_open", start, require_open(start, "2018-05-02")[0].date())
    except BlockedPeriod:
        print("require_open", start, "blocked")

print("== B. An option day with no rows, or no definitions")


def defs(symbols):
    return pd.DataFrame(dict(ts_recv=pd.Timestamp("2017-03-01 10:00", tz=NY), instrument_id=range(1, len(symbols) + 1), raw_symbol=symbols))


syms = ["GGAL  170317C00030000", "GGAL  170317P00030000", "GGAL  170421C00030000", "GGAL  170421P00030000"]
empty = pd.DataFrame(dict(ts_recv=pd.to_datetime([], utc=True), instrument_id=np.array([], dtype=int), bid_px_00=np.array([], dtype=float), ask_px_00=np.array([], dtype=float), bid_sz_00=np.array([], dtype=int), ask_sz_00=np.array([], dtype=int), flags=np.array([], dtype=int)))


def quotes():
    t = pd.Timestamp("2017-03-01 15:45", tz=NY).tz_convert("UTC")
    return pd.DataFrame(dict(ts_recv=[t] * 4, instrument_id=[1, 2, 3, 4], bid_px_00=[1.0, 1.0, 1.5, 1.5], ask_px_00=[1.1, 1.1, 1.6, 1.6], bid_sz_00=[1] * 4, ask_sz_00=[1] * 4, flags=[200] * 4))


def run(day_frames, label):
    orig_iter = bs.iter_days

    def fake(path, start, end, map_symbols=True, marker=None, scope="options"):
        for day, d, q in day_frames:
            yield day, (d if "Definition" in str(path) else q)

    bs.iter_days = fake
    try:
        snap, listed, diag = bs.snapshot_tables("2017-03-01", "2017-03-02", None, use_equity=False, progress=False)
        diag = diag.set_index("session_date")
        rates = pd.DataFrame(dict(DGS1MO=.005, DGS3MO=.006), index=diag.index)
        e = np.array([], dtype="datetime64[ns]")
        series, terms, dup = series_tables(snap, listed, diag, rates, e, e, {}, {})
        print(label, "-> no crash:", series[["session_date", "atm30", "status", "flag_half_day"]].to_dict("records"))
    except Exception as error:
        print(label, "-> crash:", type(error).__name__, str(error)[:80])
    finally:
        bs.iter_days = orig_iter


from datetime import date
good = (date(2017, 3, 1), defs(syms), quotes())
run([good, (date(2017, 3, 2), defs(syms), empty)], "one day with no quotes")
run([good, (date(2017, 3, 2), defs([]), empty)], "one day with no definitions and no quotes")
run([good, (date(2017, 3, 2), defs(["GGAL160115C00030000"]), empty)], "non-OSI symbol")
unmatched = quotes().assign(instrument_id=[11, 12, 13, 14])
run([(date(2017, 3, 1), defs(syms), unmatched)], "all quotes unmatched to definitions")

print("== C. A wrong Alpaca date on some sessions")
print("See s07_accidental_date_shift.out: the first s07 run used a fixed 04:00Z stamp, so winter bars fell on the prior New York date.")
print("That run gave only_alpaca 43, only_options 43, and a different outcome, with no stop.")
