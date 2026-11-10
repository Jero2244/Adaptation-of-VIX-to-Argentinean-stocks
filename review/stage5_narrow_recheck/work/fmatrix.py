import io, json, os, shutil, subprocess, sys, re
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from common import make_copy, HERE
d = make_copy("fm")
sys.path.insert(0, str(d))
import freeze, run_tests_once as rt
ROOT = HERE / "fm_cases"
if ROOT.exists():
    shutil.rmtree(ROOT)
SECRET = "987.654"
def probe(folder):
    """On a copy of the state: which legal moves exist?"""
    out = {}
    for name, kw in (("rerun", dict(crash_fix_note="note")), ("floorok", dict(accept_floor_failure=True)), ("stopok", dict(accept_input_stop=True))):
        t = folder.parent / (folder.name + "_probe")
        if t.exists():
            shutil.rmtree(t)
        shutil.copytree(folder, t)
        ran = []
        def a():
            ran.append(1); raise rt.RunRefused("sentinel ran")
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                rt.run_test(kw.pop("crash_fix_note", None), t/"run.json", t/"result.json", t/"opt.json", t/"out.json", lambda: None, a, lambda s: 1/0, lambda p, q: None, lambda: "h", t/"sa.json", **kw)
            out[name] = "OK"
        except rt.RunRefused as e:
            out[name] = "OK" if ran else "no"
        except SystemExit:
            out[name] = "OK"
        except Exception as e:
            out[name] = type(e).__name__
        shutil.rmtree(t)
    t = folder.parent / (folder.name + "_probe"); shutil.copytree(folder, t)
    c = t/"c.py"; c.write_text("x=1"); m = t/"m.json"; freeze.write_manifest(m, [c], t); c.write_text("x=2")
    try:
        if (t/"run.json").exists():
            freeze.after_crash("n", m, t/"run.json", t/"result.json", [c], t); out["refreeze"] = "OK"
        else:
            out["refreeze"] = "norec"
    except freeze.FreezeRefused:
        out["refreeze"] = "no"
    except Exception as e:
        out["refreeze"] = type(e).__name__
    shutil.rmtree(t)
    return out

def case(name, kind, spec, env_extra=None):
    f = ROOT / name
    env = dict(os.environ, HOOK="1", P=str(d), CASE=name, PATHK=kind, F=str(f), SPEC=json.dumps(spec), PYTHONDONTWRITEBYTECODE="1")
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, str(HERE/"fchild.py")], capture_output=True, text=True, env=env, cwd=str(f.parent) if f.parent.exists() else str(HERE))
    txt = p.stdout + p.stderr
    rec = json.loads((f/"run.json").read_text()) if (f/"run.json").exists() else {}
    res_ok = (f/"result.json").exists()
    full = '"line"' in p.stdout
    moves = probe(f)
    line = "THE VERDICT LINE" in txt or "Inconclusive" in txt
    print(f"{name:34s} exit={p.returncode} line={int(line)} discl={int(rt.DISCLOSURE[:60] in txt)} fulltext={int(full)} ptr={int('The full result is in' in txt)} frames={int((f/'frames_saved').exists())} SECRET={int(SECRET in txt)} chain={int('During handling' in txt)} date={int('2017-03-01' in txt)} status={rec.get('status')} result={int(res_ok)} partial={int((f/'result.partial').exists())} moves={moves}", flush=True)
    return p

print("Legend: moves = what a next run could do: rerun with a note, accept floor, accept stop, refreeze.")
# Normal path, each write.
for path_kind in ("normal", "floor", "stop"):
    print(f"--- path {path_kind}")
    fin = [
        ("record_finishing_write", [["W", "run.partial", "finishing"]]),
        ("record_finishing_rename", [["N", "run.json", "finishing"]]),
        ("record_finishing+crashed_write", [["W", "run.partial", "finishing"], ["W", "run.partial", "crashed"]]),
        ("result_partial_write", [["W", "result.partial", None]]),
        ("result_partial_truncated", [["T", "result.partial", None]]),
        ("result_rename", [["N", "result.json", None]]),
        ("result_rename+read_fail", [["N", "result.json", None], ["RD", "result.partial", None]]),
        ("record_finished_write", [["W", "run.partial", "finished"]]),
        ("record_finished_rename", [["N", "run.json", "finished"]]),
        ("ctrlc_result_rename", [["KN", "result.json", None]]),
        ("ctrlc_result_partial", [["KW", "result.partial", None]]),
        ("ctrlc_record_finished", [["KW", "run.partial", "finished"]]),
        ("stdout_fails_on_line", [["OP", "VERDICT" if path_kind == "normal" else "Inconclusive", None]]),
    ]
    if path_kind != "normal":
        fin = [(a, [[k, t, s] for k, t, s in b]) for a, b in fin]
    for nm, spec in fin:
        case(f"{path_kind}_{nm}", path_kind, spec)
print("--- normal path, early writes")
for nm, spec in [("record_started_write", [["W", "run.partial", "started"]]),
                 ("stepa_write", [["W", "sa.partial", None]]),
                 ("stepa_rename", [["N", "sa.json", None]])]:
    case(f"early_{nm}", "normal", spec)
print("--- JSON failure")
case("badjson_plain", "badjson", [])
case("badjson+crashed_write", "badjson", [["W", "run.partial", "crashed"]])
print("--- double fault with a secret in the crash message")
for kind in ("secret_a", "secret_b"):
    case(f"{kind}_plain", kind, [])
    case(f"{kind}_crashed_write", kind, [["W", "run.partial", "crashed"]])
    case(f"{kind}_crashed_rename", kind, [["N", "run.json", "crashed"]])
    case(f"{kind}_ctrlc_in_record_write", kind, [["KW", "run.partial", "crashed"]])
    case(f"{kind}_ctrlc_in_rename", kind, [["KN", "run.json", "crashed"]])
    case(f"{kind}_stderr_fails_once", kind, [["EP", "The run stopped", None]])
    case(f"{kind}_notupdated_print_fails", kind, [["W", "run.partial", "crashed"], ["EP", "The run record was not updated", None]])
print("--- real Windows lock on the record, with a real wait of 1 s per retry")
os.environ["REALWAIT"] = "1"
case("secret_b_real_lock", "secret_b", [["LOCK", "run.json", None]])
print("--- input stop")
case("guard_plain", "guard", [])
case("guard_record_write", "guard", [["W", "run.partial", "input_stopped"]])
case("guard_record_rename", "guard", [["N", "run.json", "input_stopped"]])
case("guard_ctrlc", "guard", [["KW", "run.partial", "input_stopped"]])

print("--- new this round")
for kind in ("secret_a", "secret_b"):
    case(f"{kind}_ctrlc_in_print", kind, [["EPK", "The run stopped", None]])
    case(f"{kind}_ctrlc_in_handler", kind, [["SAFEKI", "x", None]])
    case(f"{kind}_ctrlc_handler_and_hook", kind, [["HOOKKI", "x", None]])
case("normal_ctrlc_during_a", "normal", [["KA", "x", None]])
case("normal_ctrlc_during_b", "normal", [["KB", "x", None]])
for path_kind, word in (("normal", "VERDICT"), ("floor", "Inconclusive"), ("stop", "Inconclusive")):
    case(f"{path_kind}_ctrlc_in_line_print", path_kind, [["OPK", word, None]])
    case(f"{path_kind}_ctrlc_in_finishing_write", path_kind, [["KW", "run.partial", "finishing"]])
    case(f"{path_kind}_ctrlc_in_finishing_rename", path_kind, [["KN", "run.json", "finishing"]])
case("stop_ctrlc_in_line_with_partial", "stop", [["N", "result.json", None], ["OPK", "Inconclusive", None]])
