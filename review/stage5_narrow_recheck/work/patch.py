s = open('fchild.py', encoding='utf-8').read()
s = s.replace('sys.excepthook = rt.safe_hook', 'sys.excepthook = rt.safe_excepthook')
s = s.replace('''    def __init__(self, base, text, once=True):
        self.base, self.text, self.once, self.fired = base, text, once, False''', '''    def __init__(self, base, text, once=True, exc=None):
        self.base, self.text, self.once, self.fired, self.exc = base, text, once, False, exc''')
s = s.replace('''            raise OSError(22, "Invalid argument")
        return self.base.write(s)''', '''            raise (self.exc or OSError(22, "Invalid argument"))
        return self.base.write(s)''')
s = s.replace('''    if kind == "LOCK":''', '''    if kind == "OPK":
        sys.stdout = Flaky(sys.stdout, target, once=False, exc=KeyboardInterrupt())
    if kind == "EPK":
        sys.stderr = Flaky(sys.stderr, target, exc=KeyboardInterrupt())
    if kind == "SAFEKI":  # Ctrl-C inside the except block of run_test, while the secret error is the context.
        real_safe = rt.safe_error
        calls = {"n": 0}
        def se(error, real_safe=real_safe, calls=calls):
            calls["n"] += 1
            if calls["n"] == 1:
                raise KeyboardInterrupt
            return real_safe(error)
        rt.safe_error = se
    if kind == "HOOKKI":  # Ctrl-C in the handler, and a second Ctrl-C inside the hook.
        def se2(error):
            raise KeyboardInterrupt
        rt.safe_error = se2
    if kind == "KA":
        def run_a():
            raise KeyboardInterrupt
    if kind == "KB":
        def run_b(s):
            raise KeyboardInterrupt
    if kind == "LOCK":''')
open('fchild.py', 'w', encoding='utf-8').write(s)
m = open('fmatrix.py', encoding='utf-8').read()
m = m.replace('env = dict(os.environ, P=str(d),', 'env = dict(os.environ, HOOK="1", P=str(d),')
m = m.replace('rt.DISCLOSURE in txt', 'rt.DISCLOSURE[:60] in txt')
m += '''
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
'''
open('fmatrix.py', 'w', encoding='utf-8').write(m)
