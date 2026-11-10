"""The plain-language status paper. Run from the project folder, with reportlab on PYTHONPATH."""
import common as c

c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
c.timeline_chart(c.FIGURES / "timeline.png")
c.forest_chart(c.FIGURES / "forest_plain.png", [
    ("All days", (0.622, 0.337, 0.916), None),
    ("All days, no elections", (0.459, 0.152, 0.715), None),
    ("Before 2025-03, no elections", (0.366, -0.018, 0.682), None),
    ("From 2025-03, no elections", (0.781, 0.227, 1.244), None),
    ("2026 only", (0.423, -0.387, 1.569), None),
], (7.2, 2.9), show_legend=False)
c.outcomes_chart(c.FIGURES / "outcome_plain.png", [("If the true b is .37", 34.8, 4.8, 60.3)], (7.2, 1.25))

p = c.Paper("Sans", 10.5, "Can option prices see bumpy days coming?", c.STATUS_LINE, c.HERE / "GGAL_study_plain_version.pdf")

p.add("Can option prices see bumpy days coming?", "title")
p.add("The GGAL volatility study, explained simply. Draft of 2026-11-05, written with Claude Code from the project files.", "subtitle")
p.callout("<b>The short version.</b> We asked if option prices warn us about big future moves in the GGAL stock, beyond what recent moves already tell us. On the data we studied, the answer looks like \"yes, but unevenly\". That data helped us build the method, so it cannot give a fair final answer. We keep one older stretch of data, from 2016 to 2018, locked for a one-time test. <b>That final test has not run, so the study has no verdict yet.</b>")

p.add("1. The big question", "h1")
p.add("Think of a weather forecast. To guess next month's storms, you can look at last week's weather. You can also look at what storm insurance costs today. If the insurance is expensive, the people who sell it probably expect storms.")
p.add("GGAL is the stock of Grupo Financiero Galicia, an Argentine bank group, and it trades in New York. Its options act like insurance against big moves. So their price holds a guess about how bumpy the next 30 days will be. We call this guess <b>implied volatility</b>. How bumpy the days really turn out is <b>realized volatility</b>.")
p.add("The question is not \"are option prices perfect?\" The question is: <b>once you know how bumpy the recent past was, do option prices still tell you something more?</b>")

p.add("2. Words in this paper", "h1")
p.table([
    ["Word", "Simple meaning"],
    ["Volatility", "How much a price jumps around. It is the \"bumpiness\"."],
    ["Option", "A contract that pays if the price moves far enough. It works like insurance."],
    ["ATM30", "Our gauge: the bumpiness that near-the-money options imply for the next 30 days."],
    ["b", "Our main score. If b is 0, option prices add nothing beyond the recent past. If b is .62 and the option gauge for variance is 10% higher, the next 30 days average about 6% higher variance, with the recent past held equal."],
    ["Interval", "A range of values that fits the data. If it includes 0, we cannot rule out \"no added information\"."],
    ["PASO", "Argentina's primary election. The 2019 PASO caused a huge crash in GGAL."],
], [1, 4.6])

p.add("3. What we did, and why", "h1")
p.add("<b>Step 1: Build a gauge.</b> We first wanted a copy of the famous VIX index. The VIX needs many far-from-the-money option quotes. GGAL rarely had these before 2024. So we built a simpler gauge from near-the-money options, once a day at 15:45 New York time. We do not fill in missing days. We got a value on 1,846 of 2,137 trading days from 2018 to 2026.")
p.add("<b>Step 2: Measure what really happened.</b> For each day, we measured how bumpy the next 30 calendar days were. We include dividends, so a dividend does not look like a price drop.")
p.add("<b>Step 3: Compare.</b> We asked a statistical model to predict bumpiness from the recent past. Then we added our gauge and measured how much it helped. We also ran a forecast race, where models predict only with data they could have had at that time.")
p.add("<b>Step 4: Check the elections.</b> Argentine elections are scheduled shocks, so we studied them one by one. We compared them with ordinary dates.")

p.add("4. What we found so far", "h1")
c_note = "Each line is the range for b. A line that crosses 0 does not rule out \"no added information\". Source: reports/stage4_descriptive.md."
p.figure(c.FIGURES / "forest_plain.png", "<b>Figure 1. The score changes a lot with the days we use.</b> " + c_note, 2.9 / 7.2)
p.bullets([
    "<b>On the open data, option prices added information overall.</b> The score b is .62, and its range stays above zero.",
    "<b>Elections supply a large part of it.</b> With no election windows, b falls to .46.",
    "<b>Ordinary days before 2025 are the weak spot.</b> There, b is .37, and the range includes zero.",
    "<b>The link is not stable.</b> From year to year, b goes from -.38 in 2022 to 1.38 in 2025.",
    "<b>A better score does not mean a better forecast.</b> In the fair forecast race, we could not show a dependable gain.",
    "<b>Options saw the 2019 PASO, but not its size.</b> They priced some extra risk, about .58 in volatility terms. What happened was about 3.04.",
])
p.callout("<b>Why this is not the final answer.</b> We tried ideas on this data and changed the method after we saw results. That is normal when you build a method. But it is like a student who sees the exam while writing the study guide. A good score on that exam proves little.", edge=c.ORANGE)

p.add("5. The locked box", "h1")
p.figure(c.FIGURES / "timeline.png", "<b>Figure 2. How we use each period.</b> Only the orange period can give a verdict.", 1.75 / 7.2)
p.add("So we locked away one stretch that the method never used: January 2016 to April 2018. It is a fresh exam. The code refuses to read it unless a special approval file exists. The rule is simple: <b>we can open this exam only once.</b> If we change the method after we see the answer, the exam stops being fair.")
p.add("To keep the exam fair, we did these things first:")
p.bullets([
    "<b>Wrote the grading rules down first.</b> The rules say what counts as \"Supported\" before anyone sees a result.",
    "<b>Sealed the code.</b> A fingerprint, called a hash, covers every code file and rule file. If someone changes a file, the run refuses to start.",
    "<b>Split the opening into two steps.</b> Step A reads only option data and shows counts. Step B reads the stock prices and gives the result. So we can check data quality without seeing the answer.",
    "<b>Asked outside checkers.</b> Separate AI agents tried to break the plan. They found real problems in the failure paths, and we fixed them.",
    "<b>Practiced on open data.</b> We ran the same code on 2020 to 2022, from start to end.",
])
p.add("Nobody can fully prove that the exam is unseen. Some code had to load files that contain locked rows for a moment, and one agent saw 2017 prices in public filings. It kept them out of its report. The result must state all of this.")

p.section("6. Where we are today", 7)
p.table([
    ["Stage", "Status"],
    ["1. Check the data", "Done, except for one full row-count match"],
    ["2. Build the gauge", "Done"],
    ["3. Study the open data", "Done, and you have read the results"],
    ["4. Freeze the rules and code", "Done. Latest freeze on 2026-11-05"],
    ["5A. One-time test: options only", "<b>Done on 2026-11-05. It passed</b>"],
    ["5B. One-time test: stock prices and result", "<b>Not run. It needs your approval</b>"],
    ["6. Final write-up", "Not started. It needs the result"],
], [1.6, 2])
p.add("<b>Step A passed.</b> The locked period has 585 trading days, and our gauge has a value on 492 of them, or 84%. The minimum was 300 usable start days, and we have 455. These are only counts. They say nothing about the answer.")

p.add("7. What the final test can say", "h1")
p.bullets([
    "<b>Supported:</b> In the locked period, option prices clearly added information.",
    "<b>Smaller than .37:</b> The effect looks smaller than even our lowest earlier estimate. This does not say the effect is zero.",
    "<b>Inconclusive:</b> The data cannot decide.",
    "<b>Inconclusive, inputs failed:</b> The safety check stopped the run, and nobody found a bug to fix.",
])
p.figure(c.FIGURES / "outcome_plain.png", "<b>Figure 3. \"Inconclusive\" is the most likely result.</b> This simulation assumes a true b of .37 and full data. The real chance can differ. Source: STAGE4_PLAN.md.", 1.25 / 7.2)
p.add("About 28 months is short, because each 30-day window overlaps its neighbors. So the exam has few truly separate questions. You accepted this earlier. An \"Inconclusive\" result would not be a failure of the study. It would be an honest statement of what this data can show.")

p.add("8. What could still be wrong", "h1")
p.bullets([
    "<b>Thinner data.</b> The locked period has more days with only one usable strike price. On open data, those days gave a lower score.",
    "<b>Different price source.</b> The test uses Alpaca stock closes. They matched official closes very well on open dates, but that does not prove the same fit in 2016 and 2017.",
    "<b>A hidden step.</b> A 2017 rights offering may show as a price step with no flag. The filing says that ADS holders did not get those rights, but nobody could read the Nasdaq or depositary records.",
    "<b>A gap in one safety check.</b> Two bad prices side by side, on days with no option forward, would usually pass the new check. You chose this trade to avoid false stops.",
    "<b>Simple option math.</b> We use a formula for European options, but these options are American. Dividends can also matter. We did not run the planned sensitivity test.",
    "<b>A review gap.</b> No outside agent checked the changes of 2026-11-05.",
    "<b>The method came from later years.</b> The test uses no later prices, but we designed the method after we saw 2018 to 2026. So the test can show if the method works on older, unseen data. It cannot show that someone in 2016 could have known this method.",
])

p.add("9. What is not done yet", "h1")
p.numbered([
    "<b>You decide on Step B.</b> First compare your saved hash with the one in HANDOFF.md.",
    "<b>Step B runs once</b> and writes one result, or stops at the safety check.",
    "<b>We write the final paper,</b> with the result and all the limits above.",
    "<b>A later test is possible.</b> Data from after 2026-10-29 did not exist at the freeze, so it would be free of the problem above. It would need time, and early results would have low power.",
    "<b>Open questions stay open.</b> Examples are why the score rose after 2025, and how Databento built its early option data. HANDOFF.md has the full list.",
])
p.callout("<b>What to remember.</b> The open data hints that option prices help, mostly around elections and in recent years. The fair test of that idea is still locked. Everything is ready, and only your decision is missing.")
p.build()
print("plain written")
