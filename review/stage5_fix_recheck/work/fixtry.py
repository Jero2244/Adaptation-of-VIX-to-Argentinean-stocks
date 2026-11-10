"""Try the proposed fix on a copy, to show that it closes the paths and breaks nothing. The project stays unedited."""
import json, os, shutil, subprocess, sys
from pathlib import Path
from common import make_copy, HERE
d = make_copy("fixtry")
p = d / "run_tests_once.py"
s = p.read_text(encoding="utf-8")
def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
rep('''    except Exception as write_error:
        print(f"The run record was not updated: {safe_error(write_error)}", file=sys.stderr)
    print(message, file=sys.stderr)
    raise SystemExit(1) from None
''', '''    except BaseException as write_error:
        say(f"The run record was not updated: {safe_error(write_error)}", sys.stderr)
    say(message, sys.stderr)
    raise SystemExit(1) from None
''')
rep('''def stop_run(record''', '''def say(text: str, stream=None) -> None:
    """A print that cannot raise."""
    try:
        print(text, file=stream, flush=True)
    except BaseException:
        pass


def safe_hook(kind, error, trace) -> None:
    """Python prints the context of an uncaught error, and that context can hold a value. So an uncaught error prints only safe text."""
    shown = str(error) if isinstance(error, (RunRefused, freeze.ManifestMismatch)) else ""
    say(f"{safe_error(error)} {shown}".strip(), sys.stderr)


def stop_run(record''')
rep('''    except Exception as error:
        print(f"The result write did not finish: {safe_error(error)}", file=sys.stderr)
    if not result_path.exists():''', '''    except BaseException as error:
        say(f"The result write did not finish: {safe_error(error)}", sys.stderr)
    if not result_path.exists():''')
rep('''        except OSError:
            kept = False
        if kept:
            print(f"The full result is in {partial.name}. Under PROTOCOL.md, this file is the result.", file=sys.stderr)
        else:
            print("No file holds the result. Save the text below. Under PROTOCOL.md, it is the result.", file=sys.stderr)
            print(result_text)
    print(result["line"])
    print(result["disclosure"], flush=True)
''', '''        except (OSError, ValueError):
            kept = False
        if kept:
            say(f"The full result is in {partial.name}. Under PROTOCOL.md, this file is the result.", sys.stderr)
        else:
            say("No file holds the result. Save the text below. Under PROTOCOL.md, it is the result.", sys.stderr)
            say(result_text)
    say(result["line"])
    say(result["disclosure"])
''')
rep('''def main() -> None:
    parser = argparse.ArgumentParser()''', '''def main() -> None:
    sys.excepthook = safe_hook
    parser = argparse.ArgumentParser()''')
p.write_text(s, encoding="utf-8")
env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
t = subprocess.run([sys.executable, "-m", "unittest", "test_run_once", "test_inputs.DateGate"], cwd=d/"tests", capture_output=True, text=True, env=env)
print("tests on the patched copy:", t.stderr.strip().splitlines()[-3:], flush=True)
ROOT = HERE / "fixtry_cases"
if ROOT.exists():
    shutil.rmtree(ROOT)
SECRET = "987.654"
def case(name, kind, spec):
    f = ROOT / name
    e = dict(env, P=str(d), CASE=name, PATHK=kind, F=str(f), SPEC=json.dumps(spec), HOOK="1")
    q = subprocess.run([sys.executable, str(HERE/"fchild.py")], capture_output=True, text=True, env=e, cwd=str(HERE))
    txt = q.stdout + q.stderr
    rec = json.loads((f/"run.json").read_text()) if (f/"run.json").exists() else {}
    print(f"{name:36s} exit={q.returncode} line={int('THE VERDICT LINE' in txt or 'Inconclusive' in txt)} discl={int('format break' in txt)} fulltext={int(chr(34)+'line'+chr(34) in q.stdout)} frames={int((f/'frames_saved').exists())} SECRET={int(SECRET in txt)} chain={int('During handling' in txt)} status={rec.get('status')} result={int((f/'result.json').exists())} partial={int((f/'result.partial').exists())}", flush=True)
    return q
for kind in ("secret_a", "secret_b"):
    case(f"{kind}_ctrlc_in_record_write", kind, [["KW", "run.partial", "crashed"]])
    case(f"{kind}_ctrlc_in_rename", kind, [["KN", "run.json", "crashed"]])
    case(f"{kind}_stderr_fails_once", kind, [["EP", "The run stopped", None]])
    case(f"{kind}_notupdated_print_fails", kind, [["W", "run.partial", "crashed"], ["EP", "The run record was not updated", None]])
for path in ("normal", "floor", "stop"):
    target = "VERDICT" if path == "normal" else "Inconclusive"
    case(f"{path}_ctrlc_result_partial", path, [["KW", "result.partial", None]])
    case(f"{path}_ctrlc_result_rename", path, [["KN", "result.json", None]])
    case(f"{path}_stdout_fails_on_line", path, [["OP", target, None]])
q = case("normal_plain", "normal", [])
print("plain tail:", q.stdout.strip().splitlines()[-1][:80])
# A real refusal through main(): the message must still show with the hook.
w = make_copy("fixtry2")
shutil.copy(d/"run_tests_once.py", w/"run_tests_once.py")
e = dict(env, DRIVER_PROJECT=str(w), DRIVER_MODE="good")
q = subprocess.run([sys.executable, str(HERE/"driver.py"), "--run"], capture_output=True, text=True, env=e, cwd=w)
print("refusal through main:", q.returncode, (q.stdout+q.stderr).strip()[-200:])
