"""Hash the code and rule files against the manifest. The five input files stay unopened: only their mtimes are shown."""
import _common, json, os, time
from _common import ROOT
import hashlib
m = json.loads((ROOT/"reports/freeze_manifest.json").read_text())
skip = [k for k in m if k.startswith("data/") or k.startswith("databento")]
bad = []
for k, v in m.items():
    if k in skip: continue
    if hashlib.sha256((ROOT/k).read_bytes()).hexdigest() != v: bad.append(k)
print("code and rule files:", len(m)-len(skip), "mismatches:", bad)
current = {str(p.relative_to(ROOT)).replace("\\","/") for p in list(ROOT.glob("*.py"))+list((ROOT/"tests").glob("*.py"))}
print("py files not in manifest:", sorted(current-set(m)))
mt = os.path.getmtime(ROOT/"reports/freeze_manifest.json")
print("manifest mtime", time.ctime(mt))
for k in skip:
    print(k, "mtime before manifest:", os.path.getmtime(ROOT/k) < mt)
