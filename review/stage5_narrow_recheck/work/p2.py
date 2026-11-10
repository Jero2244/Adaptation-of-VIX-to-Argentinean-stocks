s = open("cli_walk.py", encoding="utf-8").read()
s = s.replace('''    marker(dest, "options"); marker(dest, "outcomes")
    f = fz(dest); assert f.returncode == 0, f.stderr
''', '''    f = fz(dest); assert f.returncode == 0, f.stderr
    marker(dest, "options"); marker(dest, "outcomes")
''')
s = s.replace('''dest = make_copy("cw_fix"); marker(dest, "options"); marker(dest, "outcomes"); fz(dest)''', '''dest = make_copy("cw_fix"); fz(dest); marker(dest, "options"); marker(dest, "outcomes")''')
s = s.replace('''plain("--run")
fz(dest)
plain("--run", "--expected-hash", "abc")''', '''plain("--run")
for sc in ("options", "outcomes"):
    (dest/"reports"/f"backward_test_{sc}_unlocked.json").unlink()
fz(dest)
marker(dest, "options"); marker(dest, "outcomes")
plain("--run", "--expected-hash", "abc")''')
open("cli_walk.py", "w", encoding="utf-8").write(s)
