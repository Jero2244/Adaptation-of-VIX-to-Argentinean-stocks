"""replace_manifest on a copy, in a temporary folder. Synthetic files only."""
import hashlib, json, shutil, sys, tempfile
from pathlib import Path
from unittest import mock
from common import make_copy
d = make_copy("rm"); sys.path.insert(0, str(d))
import freeze
t = Path(tempfile.mkdtemp(dir=str(d)))
a = t / "a.py"; a.write_text("x=1\n"); m = t / "m.json"; rec = t / "run.json"; res = t / "res.json"
h = freeze.write_manifest(m, [a], t)
raw = m.read_bytes()
print("1. hash matches sha256 of bytes:", h == hashlib.sha256(raw).hexdigest(), "| CR bytes:", raw.count(b"\r"), "| hash equals text hash:", hashlib.sha256(freeze.manifest_text([a], t).encode()).hexdigest() == h, "| partial left:", (t / "m.partial").exists())
freeze.verify_manifest(m, [a], t); print("2. verify passes")
real = Path.replace
def fail(self, target):
    if self.name == "m.partial":
        raise PermissionError(13, "locked")
    return real(self, target)
a.write_text("x=2\n")
rec.write_text(json.dumps(dict(status="crashed", attempts=[])))
with mock.patch.object(Path, "replace", fail):
    try:
        freeze.after_crash("note", m, rec, res, [a], t)
    except PermissionError as e:
        print("3. after_crash rename fails:", type(e).__name__)
r = json.loads(rec.read_text())
print("   manifest bytes unchanged:", m.read_bytes() == raw, "| leftover partial:", (t / "m.partial").exists(), "| refreeze entries:", len(r["refreezes"]), "| backups:", [p.name for p in t.glob("m_*")])
try:
    freeze.verify_manifest(m, [a], t); print("   verify passes (WRONG)")
except freeze.ManifestMismatch as e:
    print("   verify refuses:", e)
(t / "m.partial").write_text("garbage")
new = freeze.after_crash("note", m, rec, res, [a], t)
r = json.loads(rec.read_text())
print("4. retry with garbage leftover: new hash = file:", new == freeze.sha256(m), "| partial gone:", not (t / "m.partial").exists(), "| refreeze entries:", len(r["refreezes"]), "| two entries same new hash:", r["refreezes"][0]["new_sha256"] == r["refreezes"][1]["new_sha256"])
freeze.verify_manifest(m, [a], t); print("   verify passes after retry")
print("5. frozen list holds a .partial?", any(p.suffix == ".partial" for p in freeze.frozen_files(d, [])))
with mock.patch.object(Path, "replace", fail):
    try:
        freeze.write_manifest(m, [a], t)
    except PermissionError as e:
        print("6. normal freeze rename fails: raises, old manifest intact:", json.loads(m.read_text()) is not None, "| no retry in replace_manifest")
shutil.rmtree(t, ignore_errors=True)
