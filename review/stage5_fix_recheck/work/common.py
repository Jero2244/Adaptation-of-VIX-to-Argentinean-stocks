"""Scratch helpers. Build a copy of the code with synthetic inputs. No real data enters the copy."""
import json, os, shutil, subprocess, sys
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent
REAL = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
SECRET = "987.654"
DATES = pd.bdate_range("2016-01-04", "2018-04-30")


def closes():
    rng = np.random.default_rng(11)
    return pd.Series(50 * np.exp(np.cumsum(rng.normal(0, 0.03, len(DATES)))), index=DATES)


def make_copy(name):
    dest = HERE / name
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "tests").mkdir(parents=True)
    for p in REAL.glob("*.py"):
        shutil.copy(p, dest / p.name)
    for p in (REAL / "tests").glob("*.py"):
        shutil.copy(p, dest / "tests" / p.name)
    for n in ("PROTOCOL.md", "STAGE4_PLAN.md"):
        shutil.copy(REAL / n, dest / n)
    (dest / "reports").mkdir()
    (dest / "data" / "source").mkdir(parents=True)
    (dest / "databento_ggal_20261031" / "options").mkdir(parents=True)
    (dest / "databento_ggal_20261031" / "options" / "OPRA-cbbo_1m.zip").write_bytes(b"synthetic")
    (dest / "databento_ggal_20261031" / "options" / "OPRA-Definition.zip").write_bytes(b"synthetic")
    (dest / "data" / "source" / "fred_rates_test.csv").write_text("synthetic\n")
    pd.DataFrame(dict(ex_date=["2017-05-10"], kind=["dividend"], usd_per_ads=[0.1])).to_csv(dest / "data" / "adr_cash_events.csv", index=False)
    write_bars(dest)
    return dest


def write_bars(dest, c=None):
    c = closes() if c is None else c
    bars = [dict(t=f"{d.date()}T05:00:00Z", c=float(v)) for d, v in c.items()]
    (dest / "data" / "source" / "alpaca_ggal_sip_raw.json").write_text(json.dumps(dict(pages=[dict(bars=dict(GGAL=bars))])))


def marker(dest, scope):
    (dest / "reports" / f"backward_test_{scope}_unlocked.json").write_text(json.dumps(dict(purpose="stage5_one_time_test", scope=scope, approved_by="user", approved_on="2026-11-04")))


def run(dest, mode, *argv, script="driver.py"):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", DRIVER_MODE=mode, DRIVER_PROJECT=str(dest))
    return subprocess.run([sys.executable, str(HERE / script), *argv], capture_output=True, text=True, env=env, cwd=dest)


def show(title, p, tail=6):
    print(f"--- {title}: exit {p.returncode}")
    text = (p.stdout + p.stderr).strip().splitlines()
    for line in text[-tail:]:
        print("   ", line[:230])
    if SECRET in p.stdout + p.stderr:
        print("    >>> SYNTHETIC SECRET VISIBLE ON SCREEN")


def state(dest):
    rep = dest / "reports"
    rec = json.loads((rep / "backward_test_run.json").read_text()) if (rep / "backward_test_run.json").exists() else None
    print("    status:", rec and rec["status"], "| attempts:", rec and len(rec["attempts"]), "| refreezes:", rec and len(rec.get("refreezes", [])),
          "| result:", (rep / "stage5_result.json").exists(), "| partial:", (rep / "stage5_result.partial").exists(), "| step_a:", (rep / "stage5_step_a.json").exists(), "| frames:", (dest / "data" / "test").exists())
    return rec
