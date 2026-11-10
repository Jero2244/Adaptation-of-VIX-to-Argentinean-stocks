import json
from common import *
d = make_copy("walk_floor"); show("freeze", run(d,"good",script="freeze_cli.py"),1); marker(d,"options"); marker(d,"outcomes")
p = run(d,"thin","--run"); show("1. floor fails, both markers", p, 3); state(d); print("    step_a:", (d/"reports/stage5_step_a.json").read_text()[:200].replace("\n"," "))
show("2. rerun, no note", run(d,"thin","--run"),1)
p = run(d,"good","--run","--accept-floor-failure","--crash-fix-note","both flags"); show("3. accept + note", p, 2); rec=state(d)
res=json.loads((d/"reports/stage5_result.json").read_text()); print("    result:", {k:res[k] for k in ("decision","floor","line")}); print("    keys:", list(res)); print("    attempt:", rec["attempts"][-1]); print("    disclosure printed:", res["disclosure"] in p.stdout)
show("4. repeat", run(d,"good","--run"),1)
# Second copy: fix after floor failure, then accept without a rerun of Step A.
d = make_copy("walk_floor2"); show("freeze", run(d,"good",script="freeze_cli.py"),1); marker(d,"options")
run(d,"thin","--run")
with open(d/"build_series.py","a") as f: f.write("\n# fix\n")
show("5. after-crash on floor_failed", run(d,"good","--after-crash","fix",script="freeze_cli.py"),1)
p=run(d,"good","--run","--accept-floor-failure"); show("6. accept stale counts after a fix, Step A not rerun",p,1); rec=state(d)
print("    result manifest is the new hash:", json.loads((d/"reports/stage5_result.json").read_text())["manifest_sha256"]==rec["refreezes"][-1]["new_sha256"])
# Third copy: Step A file history on repeat.
d = make_copy("walk_floor3"); show("freeze", run(d,"good",script="freeze_cli.py"),1); marker(d,"options")
run(d,"thin","--run")
run(d,"good","--run","--crash-fix-note","fix"); b=(d/"reports/stage5_step_a.json").read_text(); rec=state(d)
print("7. first counts kept in Step A file:", '"mode": "thin"' in b, "| in the run record:", "thin" in json.dumps(rec))
# Fourth copy: refreeze at step_a_done with no crash, and an input swap, then no note.
d = make_copy("walk_floor4"); show("freeze", run(d,"good",script="freeze_cli.py"),1); marker(d,"options"); run(d,"good","--run")
c=closes(); c.iloc[5]*=1.01; write_bars(d,c)   # changes a frozen INPUT file
p=run(d,"good","--after-crash","no crash at all",script="freeze_cli.py"); show("8. after-crash at step_a_done, input swapped",p,1); rec=state(d); print("    entry:", {k:(v[:8] if 'sha' in k else v) for k,v in rec['refreezes'][0].items() if k!='at'})
marker(d,"outcomes"); p=run(d,"good","--run"); show("9. run, no --crash-fix-note",p,1); rec=state(d); print("    last attempt note:", rec["attempts"][-1]["crash_fix_note"])
