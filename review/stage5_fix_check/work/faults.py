import json
from common import *
from pathlib import Path
d = make_copy("faults")
for fault in ("double", "serialize", "disk", "rename", "last_record", "interrupt", "blank_note", "no_fix_note"):
    p = run(d, fault, script="faults_child.py")
    print(f"=== {fault}: exit {p.returncode}")
    all_text = p.stdout + p.stderr
    print("   verdict printed:", "THE VERDICT LINE" in all_text, "| synthetic secret on screen:", SECRET in all_text, "| 'During handling' chain:", "During handling" in all_text)
    for line in all_text.strip().splitlines()[-4:]:
        print("   ", line[:200])
    T = d / f"t_{fault}"
    rec = json.loads((T/"run.json").read_text()) if (T/"run.json").exists() else {}
    print("   status:", rec.get("status"), "| result:", (T/"result.json").exists(), "| partial:", (T/"result.partial").exists())
    if fault == "double":
        for line in all_text.splitlines():
            if SECRET in line:
                print("    LEAK LINE:", line[:200])

# After each stranded state: can anything go forward?
import sys
sys.path.insert(0, str(d))
import freeze, run_tests_once as rt
for fault in ("serialize", "disk", "rename", "last_record"):
    T = d / f"t_{fault}"
    outcome = {}
    try:
        rt.run_test("a note", T/"run.json", T/"result.json", T/"opt.json", T/"out.json", lambda: None, lambda: 1/0, lambda s: 1/0, lambda p, t: None, lambda: "h", T/"sa.json")
        outcome["rerun"] = "ran"
    except rt.RunRefused:
        outcome["rerun"] = "refused"
    m = T/"m.json"; c = T/"c.py"; c.write_text("x=1"); freeze.write_manifest(m, [c], T)
    try:
        freeze.after_crash("note", m, T/"run.json", T/"result.json", [c], T); outcome["after_crash"] = "ran"
    except freeze.FreezeRefused:
        outcome["after_crash"] = "refused"
    print(fault, outcome, "| result text anywhere:", (T/"result.json").exists() or (T/"result.partial").exists())

# after_crash: record write fails after the manifest was rewritten.
T = d / "t_ac"; T.mkdir(exist_ok=True)
c = T/"c.py"; c.write_text("x=1"); m = T/"m.json"; old = freeze.write_manifest(m, [c], T)
(T/"run.json").write_text(json.dumps(dict(status="crashed", attempts=[])))
c.write_text("x=2")
holder = open(T/"run.json", "rb")   # A viewer holds the record.
try:
    freeze.after_crash("real fix", m, T/"run.json", T/"result.json", [c], T)
except Exception as e:
    print("after_crash with a locked record:", type(e).__name__)
holder.close()
print("  manifest moved:", freeze.sha256(m) != old, "| refreezes in record:", json.loads((T/"run.json").read_text()).get("refreezes"), "| old hash kept anywhere:", old in (T/"run.json").read_text())
new2 = freeze.after_crash("real fix", m, T/"run.json", T/"result.json", [c], T)
e = json.loads((T/"run.json").read_text())["refreezes"][0]
print("  retry entry: old==new:", e["old_sha256"] == e["new_sha256"], "| first hash kept:", old in (T/"run.json").read_text())

# Guard edge cases.
base = pd.DataFrame(dict(close=np.full(100, 50.0), near_forward=np.full(100, 50.0)))
for name, f in dict(neg_all=-50.0, zero_one=None).items():
    x = base.copy()
    if name == "neg_all":
        x["near_forward"] = -50.0
    else:
        x.loc[0, "near_forward"] = 0.0
    try:
        rt.input_guard(x, 0, 0); print("guard", name, "passed")
    except rt.InputGuardFailed as e:
        print("guard", name, "stopped:", e)
