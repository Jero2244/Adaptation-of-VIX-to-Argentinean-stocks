s = open("real_open2.py", encoding="utf-8").read()
s = s.replace('bad = window.copy(); bad.loc[200, "close"] *= 1.5\n', '''has_fw = window["session_date"].isin(series.loc[series["near_forward"].notna(), "session_date"]).to_numpy()
print("sessions with a near forward:", int(has_fw.sum()), "of", len(window))
ROW = int(np.flatnonzero(has_fw & (np.arange(len(window)) >= 200))[0])
NOF = int(np.flatnonzero(~has_fw & (np.arange(len(window)) >= 200))[0])
clean_b = new["rule1"]["b"]; print("clean b:", round(clean_b, 3), "| clean outcome:", new["decision"]["outcome"], "| low21/low63:", round(new["rule1"]["low21"], 3), round(new["rule1"]["low63"], 3))
for pct in (1.25, 1.5, 2.0, 0.5):
    nb = window.copy(); nb.loc[NOF, "close"] *= pct
    rootx, rx, tx, cx, gx = full_run(f"nofw_{int(pct*100)}", nb, reps=200)
    st = json.loads((rootx/"run.json").read_text())["status"]
    print(f"close x{pct} on a session with no near forward: status {st} | outcome {rx['decision']['outcome'] if rx else None} | b {round(rx['rule1']['b'], 3) if rx else None} | low21 {round(rx['rule1']['low21'], 3) if rx else None} | low63 {round(rx['rule1']['low63'], 3) if rx else None}")
bad = window.copy(); bad.loc[ROW, "close"] *= 1.5
''')
s = s.replace('b2 = window.copy(); b2.loc[200, "close"] *= pct', 'b2 = window.copy(); b2.loc[ROW, "close"] *= pct')
s = s.replace('''bool(re.search(r"20\d\d-\d\d-\d\d", text))''', '''bool(re.search(r"20\d\d-\d\d-\d\d", text.replace(rt.DISCLOSURE, "")))''')
s = s.replace('''print("    log gap at that row, near .15 limit:", round(abs(np.log(pct)), 4), "| final", r["decision"]["outcome"] if r else None)''', '''print("    log gap from the bad close alone:", round(abs(np.log(pct)), 4), "| final", r["decision"]["outcome"] if r else None, "| b", round(r["rule1"]["b"], 3) if r and "rule1" in r else None)''')
s = s.replace('''    last_a = rec["attempts"][-1]\n''', '''    last_a = rec["attempts"][-1]\n''')
s = s.replace('''print("    dates equal my own calculation:", a["input_stop"]["dates"] == own_dates(bad, .15), a["input_stop"]["dates"])''', '''print("    dates equal my own calculation:", a["input_stop"]["dates"] == own_dates(bad, .15), "| n", len(a["input_stop"]["dates"]))''')
s = s.replace('''print("    one-source dates:", a["input_stop"]["dates"], "| mine:", [str(window.loc[i, 'session_date'].date()) for i in (10, 20, 30, 40)])''', '''print("    one-source dates equal mine:", a["input_stop"]["dates"] == [str(window.loc[i, 'session_date'].date()) for i in (10, 20, 30, 40)])''')
open("real_open2.py", "w", encoding="utf-8").write(s)
