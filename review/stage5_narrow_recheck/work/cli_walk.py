"""Real main() on copies with synthetic bars. Only step_a is replaced. Secret 987.654 is synthetic."""
import hashlib, json, re, subprocess, sys, os
import numpy as np, pandas as pd
import common
from common import make_copy, marker, run, write_bars, closes, DATES, SECRET, HERE
def bars(c):
    return [dict(t=f"{d.date()}T05:00:00Z", c=float(v)) for d, v in c.items()]
def put(dest, b):
    (dest/"data"/"source"/"alpaca_ggal_sip_raw.json").write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=b))])))
def rec(dest): return json.loads((dest/"reports"/"backward_test_run.json").read_text())
def fz(dest, *a):
    return run(dest, "x", *a, script="freeze_cli.py")
D = DATES[100]
def case(name, make, mode="ok"):
    dest = make_copy("cw_"+name)
    make(dest)
    f = fz(dest); assert f.returncode == 0, f.stderr
    marker(dest, "options"); marker(dest, "outcomes")
    p = run(dest, mode, "--run")
    out = p.stdout + p.stderr
    r = rec(dest); a = r["attempts"][-1]
    print(f"== {name}: exit {p.returncode} status {r['status']} stop={json.dumps(a.get('input_stop'))} error={str(a.get('error'))[:150]}")
    print("   stderr tail:", [l[:170] for l in p.stderr.strip().splitlines()][-2:])
    print("   secret on screen:", SECRET in out, "| in record:", SECRET in (dest/"reports"/"backward_test_run.json").read_text(), "| date on screen:", bool(re.search(r"20\d\d-\d\d-\d\d", out)))
    if r["status"] == "input_stopped":
        x = run(dest, mode, "--run"); print("   rerun no note: exit", x.returncode, x.stderr.strip()[:110])
        x = run(dest, mode, "--run", "--crash-fix-note", "n"); print("   rerun note, nothing changed: exit", x.returncode, x.stderr.strip()[:110])
        x = run(dest, mode, "--run", "--accept-floor-failure"); print("   wrong accept: exit", x.returncode, x.stderr.strip()[:90])
        x = run(dest, mode, "--run", "--accept-input-stop")
        res = json.loads((dest/"reports"/"stage5_result.json").read_text())
        print("   accept: exit", x.returncode, "status", rec(dest)["status"], "| outcome", res["decision"]["outcome"], "| input_stop", json.dumps(res["input_stop"])[:150], "| keys", sorted(res))
        print("   secret in result:", SECRET in json.dumps(res), "| attempts in history:", len(res["history"]["attempts"]), "| attempts in record:", len(rec(dest)["attempts"]), "| stop sentence:", "a person read the failing dates" in res["disclosure"], "| shown:", "Inconclusive, inputs failed" in x.stdout)
    sys.stdout.flush()
def dup(d):
    b = bars(closes()); b.append(dict(t=f"{D.date()}T06:00:00Z", c=float(SECRET))); put(d, b)
def setc(val):
    def f(d):
        b = bars(closes()); b[100]["c"] = val; put(d, b)
    return f
def setraw(token):
    def f(d):
        b = bars(closes()); b[100]["c"] = "@@"; (d/"data"/"source"/"alpaca_ggal_sip_raw.json").write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=b))])).replace('"@@"', token))
    return f
def nokey(d):
    b = bars(closes()); del b[100]["c"]; put(d, b)
def cash(*days):
    def f(d):
        pd.DataFrame(dict(ex_date=list(days), kind=["dividend"]*len(days), usd_per_ads=[float(SECRET)]*len(days))).to_csv(d/"data"/"adr_cash_events.csv", index=False)
    return f
case("nobar", lambda d: put(d, []))
case("onlyoutside", lambda d: put(d, [dict(t="2019-01-02T05:00:00Z", c=float(SECRET))]))
case("dup", dup)
case("neg", setc(-float(SECRET)))
case("zero", setc(0.0))
case("null", setc(None))
case("nan", setraw("NaN"))
case("exdate", cash("2017-05-13"))
case("exdate2", cash("2017-05-13", "2017-05-14"))
case("layout_nokey", nokey)
case("layout_page", lambda d: (d/"data"/"source"/"alpaca_ggal_sip_raw.json").write_text(json.dumps(dict(pages=[dict(other=1)]))))
case("layout_text", setc("abc"))
case("inf", setraw("Infinity"))
case("step_a_secret", lambda d: None, "crash")
print("\n== Fix path: stop, refreeze, rerun to a verdict")
dest = make_copy("cw_fix"); fz(dest); marker(dest, "options"); marker(dest, "outcomes")
p = run(dest, "onegap", "--run"); print("first", p.returncode, rec(dest)["status"], rec(dest)["attempts"][-1]["input_stop"])
(dest/"realized.py").write_text((dest/"realized.py").read_text(encoding="utf-8")+"\n# fix\n", encoding="utf-8")
f = fz(dest, "--after-crash", "fixed the map"); print("refreeze", f.returncode, f.stdout.strip().splitlines()[-1][:90])
mh = hashlib.sha256((dest/"reports"/"freeze_manifest.json").read_bytes()).hexdigest()
print("record new hash = file hash:", rec(dest)["refreezes"][-1]["new_sha256"] == mh, "| leftover partial:", (dest/"reports"/"freeze_manifest.partial").exists(), "| backups:", [x.name for x in (dest/"reports").glob("freeze_manifest_*")])
p = run(dest, "ok", "--run", "--crash-fix-note", "fixed the map"); res = json.loads((dest/"reports"/"stage5_result.json").read_text())
print("second", p.returncode, rec(dest)["status"], res["decision"]["outcome"]); print("history", json.dumps(res["history"], indent=1)[:1500]); print("disclosure tail:", res["disclosure"][-170:]); print("attempts in record", len(rec(dest)["attempts"]), "in history", len(res["history"]["attempts"]))
print("\n== Plain command line on a copy, no driver")
dest = make_copy("cw_plain")
def plain(*a):
    x = subprocess.run([sys.executable, "run_tests_once.py", *a], cwd=dest, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    print(f"   {a}: exit {x.returncode} | stdout {x.stdout.strip()[-120:]!r} | stderr {x.stderr.strip()[-200:]!r}"); sys.stdout.flush()
plain("--run")
plain("--run", "--accept-input-stop")
plain("--run", "--accept-floor-failure")
marker(dest, "options"); marker(dest, "outcomes")
plain("--run")
for sc in ("options", "outcomes"):
    (dest/"reports"/f"backward_test_{sc}_unlocked.json").unlink()
fz(dest)
marker(dest, "options"); marker(dest, "outcomes")
plain("--run", "--expected-hash", "abc")
(dest/"realized.py").write_text((dest/"realized.py").read_text(encoding="utf-8")+"\n# edit\n", encoding="utf-8")
plain("--run")
fz2 = subprocess.run([sys.executable, "freeze.py"], cwd=dest, capture_output=True, text=True); print("   normal freeze with markers: exit", fz2.returncode, fz2.stderr.strip()[-120:])
for sc in ("options", "outcomes"):
    (dest/"reports"/f"backward_test_{sc}_unlocked.json").unlink()
fz2 = subprocess.run([sys.executable, "freeze.py"], cwd=dest, capture_output=True, text=True); print("   Fix before any run, markers removed: exit", fz2.returncode, fz2.stdout.strip()[-90:])
marker(dest, "options"); marker(dest, "outcomes")
plain("--run")  # The real step_a on a synthetic zip: an ordinary crash, safe message.
print("   status", rec(dest)["status"], rec(dest)["attempts"][-1].get("error", "")[:160])
(dest/"reports"/"stage5_result.json").write_text("{}")
plain("--run", "--crash-fix-note", "x")
