"""The plain-language final report. Run from the project folder, with reportlab on PYTHONPATH."""
import common as c
import final_common as f

f.check_numbers()
f.check_open_data()
f.check_fixes()
c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
f.timeline_final(c.FIGURES / "timeline_final.png")
medians = f.series_chart(c.FIGURES / "series_final.png", (7.2, 3.0))
f.comparison_chart(c.FIGURES / "compare_plain.png", [
    ("All open days", .622, .337, .916, "dev"),
    ("Open, no elections, before 2025-03", .366, -.018, .682, "dev"),
    ("Test, all days", .281, -.209, .845, "test"),
    ("Test, no elections", .351, -.121, .916, "test"),
], (7.2, 2.5))
c.forest_chart(c.FIGURES / "forest_plain_final.png", [
    ("All days", (.622, .337, .916), None),
    ("All days, no elections", (.459, .152, .715), None),
    ("Before 2025-03, no elections", (.366, -.018, .682), None),
    ("From 2025-03, no elections", (.781, .227, 1.244), None),
    ("2026 only", (.423, -.387, 1.569), None),
], (7.2, 2.9), show_legend=False)

p = c.Paper("Sans", 10.5, "Can option prices see bumpy days coming?", f.FOOTER, c.HERE / "GGAL_study_plain_final.pdf")

p.add("Can option prices see bumpy days coming?", "title")
p.add("The full GGAL volatility study, explained simply. Final report draft of 2026-11-05, written with Claude Code from the project files.", "subtitle")
p.add("<b>Revision history.</b> " + f.REVISION_NOTE + " The test result is unchanged. Section 10 adds checks made after the test.", "subtitle")
p.callout("<b>The short version.</b> We asked if option prices warn us about big future moves in the GGAL stock, beyond what recent moves already tell us. The data that we used to build the method says \"yes, but unevenly\". Then we ran a fair one-time test on older data that the method had never used. <b>The test result is \"Inconclusive\".</b> The score was positive, but the data was too limited to separate a real effect from no effect. So the idea is neither proved nor rejected. <b>Read three numbers together.</b> The score b is .62 on all open data. It is .37 on ordinary days before 2025, and there the range includes zero. It is .28 in the fair test. The good score is fragile.")

p.add("1. The big question", "h1")
p.add("Think of a weather forecast. To guess next month's storms, you can look at last week's weather. You can also look at what storm insurance costs today. If the insurance is expensive, the people who sell it probably expect storms.")
p.add("GGAL is the stock of Grupo Financiero Galicia, an Argentine bank group, and it trades in New York. Its options act like insurance against big moves. So their price holds a guess about how bumpy the next 30 days will be. We call this guess <b>implied volatility</b>. How bumpy the days really turn out is <b>realized volatility</b>.")
p.add("The question is not \"are option prices perfect?\" The question is: <b>once you know how bumpy the recent past was, do option prices still tell you something more?</b> Argentina makes this interesting, because its elections can shake the stock on one known date.")

p.add("2. Words in this report", "h1")
p.table([
    ["Word", "Simple meaning"],
    ["Volatility", "How much a price jumps around. It is the \"bumpiness\"."],
    ["Option", "A contract that pays if the price moves far enough. It works like insurance."],
    ["ATM30", "Our gauge: the bumpiness that near-the-money options imply for the next 30 days."],
    ["b", "Our main score. If b is 0, option prices add nothing beyond the recent past. If b is .62 and the option gauge for variance is 10% higher, the next 30 days average about 6% higher variance, with the recent past held equal."],
    ["Interval", "A range of values that fits the data. If it includes 0, we cannot rule out \"no added information\". We call the ranges \"95%\" ranges, but in simulation they hold the true value only about 87% to 91% of the time, so they are too narrow."],
    ["PASO", "Argentina's primary election. The 2019 PASO caused a huge crash in GGAL."],
    ["Open data", "Data from 2018-05 to 2026-10. We looked at it and used it to build the method."],
    ["Test data", "Data from 2016-01 to 2018-04. We kept it locked until the final test."],
], [1, 4.6])

p.add("3. What we did, step by step", "h1")
p.add("<b>Step 1: Check the data.</b> We used option quotes and stock prices from Databento, stock prices from Alpaca, and US interest rates from the Federal Reserve data site, FRED. We also collected dividends. One full row-count match stays unfinished.")
p.add("<b>Step 2: Build a gauge.</b> We first wanted a copy of the famous VIX index. The VIX needs many far-from-the-money option quotes, and GGAL rarely had these before 2024. So we built a simpler gauge from near-the-money options, once a day at 15:45 New York time. The gauge is the implied volatility of the options closest to the stock price, interpolated to 30 days. It is not a VIX-style calculation. We do not fill in missing days. It has a value on 1,846 of 2,137 open trading days.")
p.add("<b>Step 3: Measure what really happened.</b> For each day, we measured how bumpy the next 30 calendar days were. We include dividends, so a dividend does not look like a price drop.")
p.add("<b>Step 4: Study the open data.</b> We asked a statistical model to predict bumpiness from the recent past. Then we added our gauge and measured how much it helped. We also ran a forecast race, where models predict only with data they could have had at that time. We studied each election too.")
p.add("<b>Step 5: Freeze the rules.</b> We wrote down what each result would mean, and we sealed the code. Outside AI checkers then tried to break the plan, and we fixed what they found.")
p.add("<b>Step 6: Run the one-time test.</b> We opened the locked data in two steps. We ran it once.")
p.figure(c.FIGURES / "series_final.png", "<b>Figure 1. The gauge and what really happened, 2016 to 2026.</b> Blue is the guess from options. Orange is the bumpiness that came after. The lines connect across missing days. The big orange spike is the 2019 PASO.", 3.0 / 7.2)

p.section("4. What the open data showed", 9)
p.figure(c.FIGURES / "forest_plain_final.png", "<b>Figure 2. On open data, the score changes a lot with the days we use.</b> A line that crosses 0 does not rule out \"no added information\".", 2.9 / 7.2)
p.bullets([
    "<b>Option prices added information overall.</b> The score b is .62, and its range stays above zero.",
    "<b>Elections supply a large part of it.</b> With no election windows, b falls to .46.",
    "<b>Ordinary days before 2025 are the weak spot.</b> There, b is .37, and the range includes zero.",
    "<b>The link is not stable.</b> From year to year, b goes from -.38 in 2022 to 1.38 in 2025.",
    "<b>Options saw the 2019 PASO, but not its size.</b> They priced some extra risk, about .58 in volatility terms. What happened was about 3.04.",
    "<b>A better score does not mean a better forecast.</b> In the fair forecast race, we could not show a dependable gain.",
])
p.callout("<b>Why this was not the final answer.</b> We tried ideas on this data and changed the method after we saw results. That is normal when you build a method. But it is like a student who sees the exam while writing the study guide. A good score on that exam proves little.", edge=c.ORANGE)

p.add("5. The locked box", "h1")
p.figure(c.FIGURES / "timeline_final.png", "<b>Figure 3. How we used each period.</b> Only the orange period could give a verdict.", 1.75 / 7.2)
p.add("We locked away one stretch that had not built the method: January 2016 to April 2018. It was a fresh exam, and the rule was simple: <b>we can open it only once.</b> To keep it fair, we did these things first:")
p.bullets([
    "<b>Wrote the grading rules down first.</b> The rules said what counts as \"Supported\" before anyone saw a result.",
    "<b>Sealed the code.</b> A fingerprint, called a hash, covered every code file and rule file. If someone changed a file, the run would refuse to start.",
    "<b>Split the opening into two steps.</b> Step A read only option data and showed counts. Step B read the stock prices and gave the result.",
    "<b>Asked outside checkers.</b> They found real problems in the failure paths, and we fixed them.",
    "<b>Practiced on open data.</b> We ran the same code on 2020 to 2022, from start to end.",
])
p.add("<b>Why use older data?</b> It was the only unused data left. No later price entered the test. But we did design the method after we saw 2018 to 2026. So the test can show if the method works on older, unseen data. It cannot show that someone in 2016 could have known this method.")

p.add("6. The one-time test result", "h1")
p.callout("<b>Result: Inconclusive, with a positive sign.</b> For 2016-01 to 2018-04 only. The score b is .28. Its range goes from about -.21 to .85.", edge=c.ORANGE)
p.figure(c.FIGURES / "compare_plain.png", "<b>Figure 4. The test range is wide.</b> It includes 0, and it also includes every earlier score in this figure.", 2.5 / 7.2)
p.add("Think of a blurry photo of a far-away animal. You cannot say that it is a dog, and you cannot say that it is not a dog. A blurry photo is not evidence that no dog exists.")
p.bullets([
    "<b>Not \"Supported\".</b> The range includes zero, so we cannot say that option prices added information in this period.",
    "<b>Not \"Smaller than .37\".</b> The range goes far above .37, so we also cannot say that the effect is small.",
    "<b>No forecast gain.</b> In the forecast race, adding the gauge did not help in this period. The small difference favored the model with no gauge, but its range includes zero too.",
    "<b>Elections did not drive this result.</b> The score was .35 with no election windows. That is the opposite direction from the open data, but this period has only two elections, so this tells us little.",
])
p.add("This result was the most likely one. Before the test, a simulation said that \"Inconclusive\" would appear about 60% of the time if the true b was .37.")

p.add("7. What we learned", "h1")
p.numbered([
    "<b>The evidence for the idea comes only from the data that built the method.</b> The fair test did not confirm it, and it did not reject it.",
    "<b>Do not rely on this gauge for a better forecast.</b> We never showed a dependable forecast gain, in the open data or in the test.",
    "<b>A VIX copy does not work well for GGAL before 2024.</b> The option quotes far from the current price mostly do not exist.",
    "<b>Elections matter a lot, and options can underprice them.</b> The 2019 PASO is the clearest case.",
    "<b>Writing the rules first was useful.</b> The open-data score alone would have looked much stronger than the evidence allows.",
])
p.add("One thing we noticed only after the test: the 2016-2018 period was much calmer. The median gauge was .33, against .61 in the open data. Calm periods can make this kind of link harder to measure. This is an observation, not a test.")
assert round(medians["test_atm"], 2) == .33 and round(medians["open_atm"], 2) == .61

p.add("8. What could be wrong", "h1")
p.bullets([
    "<b>Too little data.</b> About 28 months gives few truly separate 30-day windows. This is the main limit.",
    "<b>Thinner data.</b> The test had more days with only one usable strike price. On open data, those days gave a lower score.",
    "<b>Different price source.</b> The test used Alpaca closes. They matched official closes very well on open dates, but that does not prove the same fit in 2016 and 2017.",
    "<b>A hidden step.</b> A 2017 rights offering may show as a price step with no flag. The filing says that ADS holders did not get those rights, but nobody could read the Nasdaq or depositary records.",
    "<b>A gap in one safety check.</b> Two bad prices side by side, on days with no option forward, would usually pass. You chose this trade to avoid false stops.",
    "<b>Simple option math.</b> We use a formula for European options, but these options are American. Dividends can also matter. In a simulation, a dividend inside the option term made the volatility read from one option expiry too high by about 2% to 13%. The 30-day gauge is affected less. On real data, a later check with a better pricing method did not change the score (Section 10).",
    "<b>Missing days.</b> The gauge is missing more often just before an option expiry. We do not fill these days.",
    "<b>Wide option quotes.</b> Many quotes have a large gap between the buy price and the sell price. The gauge uses the middle of that gap and has no filter for wide gaps. On days with only one usable strike price, the gauge uses a strike that can be far from the stock price.",
    "<b>The exam may not be fully unseen.</b> Some code had to load locked rows for a moment, and one agent saw 2017 prices in public filings. It kept them out of its report. Nobody audited the agents.",
    "<b>Review gap.</b> No outside agent checked the last code changes before the test. Your own saved hash is not yet compared with the run.",
])

p.add("9. What is not done", "h1")
p.bullets([
    "<b>Your review of this draft.</b> This report is the draft of the final write-up.",
    "<b>A hash comparison.</b> Please compare your saved hash with the one in HANDOFF.md.",
    "<b>A forward test.</b> Data from after 2026-10-29 did not exist when we froze the rules, so it would be the cleanest next test. It is not in the plan, it needs time, and early results would have low power.",
    "<b>Open checks.</b> The full row-count match is still open. The odd forward on 2022-07-08 is explained: it is quote noise from one strike with wide quotes.",
    "<b>Open questions.</b> Nobody knows yet why the score rose after 2025, or if the 2025 change in quote format explains it. Databento has also not explained how it built its early option data.",
])
p.add("10. Checks after the audit", "h1")
p.callout("<b>This is extra exploration on the open data, done after the one-time test.</b> It does not replace or change the test result.", edge=c.ORANGE)
p.add("We re-ran the open-data score with stricter rules for the option quotes. The score rose from .62 to .85, but only because the rules drop about half of the days. The old gauge gives almost the same .84 on the days that stay. So the rise comes from which days remain, and not from a better measure. A stronger model of past moves lowers the score a little, from .62 to .61, and a better pricing method for American options changes nothing (.62).")
p.add("The checks also show weak spots. The \"95%\" ranges really hold the true value only about 87% to 91% of the time. The score is large after 2025 and weaker before. A test of whether option prices match later bumpiness one for one also fails.")
p.callout("<b>What to remember.</b> Option prices look useful in the data that taught us the method, mostly around elections and in recent years. The one fair test could not say yes or no. Any change to the method from now on is new exploration, and it does not count as a second test of this period.")
p.build()
print("plain final written", medians)
