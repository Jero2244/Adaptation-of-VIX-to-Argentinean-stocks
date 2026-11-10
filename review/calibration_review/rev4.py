"""Rerun the result functions in memory and compare to the saved JSON. Nothing is written."""
import sys
sys.dont_write_bytecode = True
import json
from pathlib import Path
import numpy as np
P = Path(r"C:\Users\HP Laptop\.spyder-py3\2024-1\vix_ggal_adaptation")
sys.path.insert(0, str(P / "calibration")); sys.path.insert(0, str(P))
import calib_core as cc, calib_run as run, calib_post as post
res = json.loads((P/"reports/calib_results.json").read_text(encoding="utf-8"))
op, te = run.load_period("open"), run.load_period("test")

def diff(a, b, path=""):
    out = []
    if isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b: out.append((path+"/"+k, "missing")); continue
            out += diff(a[k], b[k], path+"/"+k)
    elif isinstance(a, list):
        if len(a) != len(b): out.append((path, "len"))
        for i, (x, y) in enumerate(zip(a, b)): out += diff(x, y, f"{path}/{i}")
    elif isinstance(a, float) or isinstance(b, float):
        if a is None or b is None or abs(a-b) > 1e-12: out.append((path, a, b))
    elif a != b: out.append((path, a, b))
    return out

c1 = run.to_plain(run.stage_c1(dict(open=op, test=te)))
print("c1 diffs", diff(c1, res["c1"])[:10])
c2 = run.to_plain(run.stage_c2(op))
print("c2 diffs", len(diff(c2, res["c2"])), diff(c2, res["c2"])[:5])
b = run.to_plain(run.benchmark_tables(op))
print("bench diffs", len(diff(b, res["c3"]["benchmarks"])), diff(b, res["c3"]["benchmarks"])[:5])
c = run.to_plain(run.cut_tables(op, te))
saved = {k: v for k, v in res["c3"].items() if k != "benchmarks"}
print("cut diffs", len(diff(c, saved)), diff(c, saved)[:5])
t = run.to_plain(post.base_rate_table(op))
print("base diffs", len(diff(t, res["post_result"]["brier_against_base_rate"])))
print("largest", c2["largest_abs_z"])
print("fixed test", [ (f["step"],f["samples"],round(f["inner"]["mean"],3)) for f in c["test_period_fixed_steps"]])
for cut in ("2016-01 to 2018-04, event in window",):
    print(cut, c["cuts"][cut]["inner"])
