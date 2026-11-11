"""The plain-language calibration report. Run from the project folder, with reportlab on PYTHONPATH."""
import calib_common as f
import common as c
from calib_common import BENCH, C1, C2, CUTS, M, METHODS, POST, Q, QS, SYN, pct, span

f.check_claims()
c.register_fonts()
c.setup_matplotlib()
c.FIGURES.mkdir(exist_ok=True)
FIG = c.FIGURES
f.bell_chart(FIG / "calib_bell.png")
f.quintile_chart(FIG / "calib_quintiles_plain.png")
f.z_chart(FIG / "calib_z_plain.png")
f.rolling_chart(FIG / "calib_rolling_plain.png")
f.reliability_chart(FIG / "calib_reliability_plain.png", compare=False)
f.forward_timeline(FIG / "calib_forward_plain.png")

base = POST["brier_against_base_rate"]
power = {row["sessions"]: row for row in SYN["forward_power"]}
years = POST["by_year"]
paso = POST["no_2019_paso"]
selection = POST["selection"]
rel20 = C2["reliability"]["0.2"]["groups"]
no_event, event = CUTS["No event in window"], CUTS["Event in window"]

p = c.Paper("Sans", 10.5, "Do GGAL option prices get the odds right?", f.FOOTER, c.HERE / "GGAL_calibration_plain.pdf")

p.add("Do GGAL option prices get the odds right?", "title")
p.add("A side study of GGAL price moves, explained simply. Draft of 2026-11-05, written with Claude Code from the project files.", "subtitle")
p.add("<b>Revision history.</b> " + f.REVISION_NOTE + " No result changed. The edits concern wording on option math and wide quotes.", "subtitle")
p.callout(f"<b>The short version.</b> Option prices imply a range for where the GGAL stock will be in 30 days. We checked if the stock really stayed inside that range as often as the options imply. <b>Over all days together, the answer looks like yes:</b> {pct(M['inner']['value'])} against 68.3% for the inner range. <b>But this average hides errors that cancel out.</b> When options priced GGAL as calm, the stock stayed in the inner range only about {pct(QS[0]['inner']['value'], 0)} of the time. All of this is exploratory. Only new data can confirm it, so we froze a 36-month test for the future.")

p.add("1. The big question", "h1")
p.add("Think of a weather forecaster who says \"70% chance of rain\". You cannot judge that from one day. But collect all the days with that forecast, and it should rain on about 70 of each 100. A forecaster who does this is <b>calibrated</b>.")
p.add("Option prices make the same kind of forecast. From the price of GGAL options, we can work out a range for the stock 30 days from now, and the odds of landing inside it. Then we can wait 30 days and check. We did this for every trading day that has a usable option price.")
p.add("The main study asked a different question: <b>do option prices carry useful information about future bumpiness?</b> This side study asks: <b>are the odds that they imply the right size?</b> A forecast can hold useful information and still have the wrong odds.")

p.section("2. Words in this report", 12)
p.table([
    ["Word", "Simple meaning"],
    ["ATM30", "Our gauge from the main study: the bumpiness that near-the-money options imply for the next 30 days."],
    ["Inner band", "The range that should hold 68.3% of 30-day moves, if the option odds are right. It is one band width on each side of the centre."],
    ["Outer band", "The range that should hold 95.4% of moves. It is two band widths on each side."],
    ["Hit rate", "The share of days on which the 30-day move stayed inside a band."],
    ["z", "The size of a move, counted in band widths. A z of -2 is a fall to the edge of the outer band."],
    ["Interval", "A range of values that fits the data. If it includes the calibrated value, we cannot rule out that the odds were right."],
    ["HAR", "A simple forecast of bumpiness from recent price moves only. It uses no option prices."],
    ["Open data", "Data from 2018-05 to 2026-10. It also built the gauge, so it cannot confirm anything about the gauge."],
    ["Post-result", "A check that we chose after we saw results. It can give ideas, but it proves nothing."],
], [1, 4.6])
p.figure(FIG / "calib_bell.png", "<b>Figure 1. What the option prices imply.</b> If the odds are right, moves spread like this bell curve. The band width changes each day with ATM30.", 2.5 / 7.2)

p.add("3. What we did, step by step", "h1")
p.add("<b>Step 1: Write the rules first.</b> We wrote down the measures and sealed the rules with a fingerprint, called a hash, before we computed any real result.")
p.add("<b>Step 2: Test the method on fake prices.</b> We simulated prices with a known bumpiness and ran the whole method on them. The hit rates came out as they should. A planted price jump also showed that the code would catch a one-day shift in the dates.")
p.add(f"<b>Step 3: Measure real moves.</b> For each day, we took the ATM30 band and the stock's real move over the next 30 calendar days, with dividends included. This gave {M['n']:,} days of open data.")
p.add("<b>Step 4: Compare.</b> We compared the options with a band from recent price moves (HAR) and with two adjusted versions of the option band. We also split the days by elections, by date, and by quote quality.")
p.add("<b>Step 5: Ask a critic.</b> An independent AI reviewer tried to break the work. It found no calculation error, but it found that our first summary claimed too much. We rewrote the summary, and this report uses the new one.")
p.callout("<b>A warning about overlap.</b> Each 30-day move shares most of its days with the move that starts one day later. So 1,828 days hold only about 102 truly separate months. The data is much thinner than it looks.", edge=c.ORANGE)

p.add("4. What we found", "h1")
p.table([
    ["Measure", "Result", "If the odds are right", "Interval"],
    ["Inner band hit rate", pct(M["inner"]["value"]), "68.3%", span(M["inner"])],
    ["Outer band hit rate", pct(M["outer"]["value"]), "95.4%", span(M["outer"])],
    ["Big falls past the outer band", pct(M["down_tail"]["value"]), "2.3%", span(M["down_tail"])],
    ["Big rises past the outer band", pct(M["up_tail"]["value"]), "2.3%", span(M["up_tail"])],
], [2.6, 1, 1.6, 1.6], f"<b>Table 1. The main result, on all {M['n']:,} open days.</b> Elections and lower-quality quotes are included. All intervals include the calibrated value.")
p.add("At this level, the option odds look about right. But this does not prove that they are right. The inner interval is about 11 points wide, and these intervals are too narrow: in our simulation, a \"95%\" interval really worked about 86% to 92% of the time.")
p.add("Three things sit under this average.")
p.add("<b>First: the error depends on what options expect (post-result).</b> We split the days into five equal groups by ATM30. In the calmest-priced group, the stock stayed in the inner band only about half the time. In the two most bumpy-priced groups, it stayed inside more often than 68.3%. The groups average out, and the problem hides.")
p.figure(FIG / "calib_quintiles_plain.png", f"<b>Figure 2. Hit rate by option gauge level.</b> Only the lowest group has an interval entirely below 68.3%. We chose this split after we saw the results, and it uses hindsight. No 2019 PASO days are in the lowest group, so that crash does not explain the low score.", 2.9 / 7.2)
p.add(f"<b>Second: the score changes from year to year.</b> The inner hit rate was {pct(years['2024']['inner'])} in 2024 and {pct(years['2022']['inner'])} in 2022. A forecaster with a good ten-year score can still have long bad stretches.")
p.figure(FIG / "calib_rolling_plain.png", "<b>Figure 3. The hit rate moves a lot over time.</b> Each point covers the past 12 months. Early points hold about six months. Nearby points share most of their days.", 3.0 / 7.2)
p.add(f"<b>Third: elections carry the extreme moves.</b> We measure extreme moves with an average of squared z values, which should be about 1. It is {no_event['mean_z2']['value']:.2f} on days with no election in the next 30 days, and {event['mean_z2']['value']:.2f} on days with one. In the days before the 2019 PASO, every 30-day move went past the outer band. But elections differ: for the 2019 general and for the 2023 PASO and general, all moves stayed in the inner band.")
p.figure(FIG / "calib_z_plain.png", "<b>Figure 4. Every 30-day move, in band widths.</b> The solid lines are the outer band, and the dashed lines are the inner band. The lines of dots are overlapping moves that share the same days.", 3.0 / 7.2)

p.add("5. Did anything beat the options?", "h1")
p.add(f"No, not clearly. We compared all methods on the same {BENCH['rows']:,} days.")
p.bullets([
    f"<b>A band from recent moves (HAR).</b> With no correction, we could not show a score difference from the options. Its inner hit rate was {pct(METHODS['HAR, no factor']['inner']['value'])} and its outer hit rate was {pct(METHODS['HAR, no factor']['outer']['value'])}. A common correction made its bands wider and its inner score worse.",
    f"<b>A wider option band.</b> We scaled the option band using past errors. This made it too wide: {pct(METHODS['Scaled ATM30']['inner']['value'])} of moves fell in the inner band. The 2019 PASO pushed up the scale, so this result depends largely on one event.",
    "<b>An option band with fatter tails.</b> We could not show a score difference here either. At the outer band, this test has almost no power, because its edge is nearly the same as the normal band's edge by construction.",
])
p.add("<b>Move odds (post-result).</b> We also asked: what are the odds of a move beyond 10% or 20%? A simple rule that uses only the past share of such moves did about as well as the options. A modest gain for options cannot be excluded.")
p.figure(FIG / "calib_reliability_plain.png", f"<b>Figure 5. Forecast odds against what happened.</b> A perfect forecaster sits on the dashed line. For moves beyond 20%, the lowest group forecast {pct(rel20[0]['mean_probability'], 0)} and saw {pct(rel20[0]['observed'], 0)}. The highest group forecast {pct(rel20[-1]['mean_probability'], 0)} and saw {pct(rel20[-1]['observed'], 0)}.", 3.3 / 7.2)

p.add("6. Is this a market mistake?", "h1")
p.callout("<b>Not necessarily.</b> Option prices are not pure forecasts. They include the price of insurance. People pay extra to protect against crashes, so option odds can differ from real-world odds even when nobody is wrong. This study cannot separate the insurance price from a forecast error.", edge=c.ORANGE)

p.add("7. The test for the future", "h1")
p.add("All the data so far has been used, so it can give ideas but not proof. Only data from after 2026-10-29 can confirm a result. You chose a 36-month test, and we fixed it before any such data existed.")
p.figure(FIG / "calib_forward_plain.png", "<b>Figure 6. How we use each period.</b> The verdict uses days from 2026-10-30 through 2029-10-30. The last 30-day window closes about 2029-11-29.", 1.75 / 7.2)
p.bullets([
    "<b>The rule.</b> If the interval for the inner hit rate excludes 68.3% under both block sizes, the verdict is \"Miscalibrated\". If not, the verdict is \"No miscalibration shown\". That second verdict does not prove that the odds are right.",
    f"<b>The power.</b> In simulation, the rule catches bands that are 25% too wide about {pct(power[504]['bands_25pct_too_wide']['verdict_fires'], 0)} to {pct(power[756]['bands_25pct_too_wide']['verdict_fires'], 0)} of the time at this length. It also gives a false alarm about {pct(power[756]['no_error']['verdict_fires'], 0)} of the time.",
    "<b>What the test checks.</b> It checks the overall hit rate only. The low-gauge pattern in Figure 2 came from hindsight, so the frozen test does not cover it. It would need its own rule, written before any forward data is read.",
    "<b>A look at 12 months.</b> We will look at the numbers in about a year, with no verdict. Those early intervals will be unreliable.",
])

p.add("8. What we learned", "h1")
p.numbered([
    "<b>An average can look perfect and still hide errors.</b> The overall hit rates are close to the targets, but the error changes with the gauge level and with time.",
    "<b>The middle of the range looks fine, and the extremes do not.</b> Typical moves fit the band well. Rare, large moves carry the excess.",
    "<b>Options did not clearly beat simple alternatives.</b> We compared them with a plain band from recent moves, and with a simple past share of big moves.",
    "<b>One election can move the numbers a lot.</b> Without the 2019 PASO, the extreme-move average falls from " + f"{M['mean_z2']['value']:.2f} to {paso['mean_z2']['value']:.2f}.",
])

p.add("9. What could be wrong", "h1")
p.bullets([
    "<b>Used data.</b> This data built the gauge, so a good score on it means little.",
    "<b>Chosen after the fact.</b> The low-gauge result is striking, but we looked for it after seeing results. Such patterns often shrink in new data.",
    f"<b>Missing days.</b> The gauge is blank on some days, and those days had bigger moves: {pct(selection['big_move_blank'])} moved more than 20%, against {pct(selection['big_move_valid'])}. So the hit rates may look better than they really are.",
    f"<b>A calmer older period.</b> In 2016-01 to 2018-04, the inner hit rate is {pct(CUTS['2016-01 to 2018-04']['inner']['value'])}, but that period was used once already. It is a separate result on calmer data, not a confirmation.",
    "<b>Simple option math.</b> We use a formula for European options, but these options are American, and dividends can matter. In a simulation, a dividend inside the option term made the volatility read from one option expiry too high by about 2% to 13%. The 30-day gauge is affected less. On real data, a later check did not change the main-study score. We did not run it for this study.",
    "<b>Wide option quotes.</b> Many quotes have a large gap between the buy price and the sell price. The gauge uses the middle of the gap and has no filter for wide gaps.",
    "<b>A small date mismatch.</b> Real windows average 29.35 days, not 30. With the real length, the inner rate is about 68.9%. The ATM30 price is from 15:45, and the move starts at the 16:00 close. A check with the 15:45 price changed little.",
    "<b>No history of the order.</b> A hash shows if the sealed files changed. The project is now in git, but its first commit came after the results. So neither git nor the file dates can prove that the rules came first. You have the hash, and you can check it.",
])

p.add("10. What is not done", "h1")
p.bullets([
    "<b>Your review of this draft.</b>",
    "<b>Forward test code.</b> It needs a loader for new data and a fix to the verdict function, before anyone reads forward data.",
    "<b>The American-option check.</b> It was done for the main study as extra exploration. It was not done for this study.",
    "<b>The main-study reports.</b> They do not include these results, and they still wait for your review.",
])
p.callout(f"<b>What to remember.</b> Over {M['n']:,} days, the option odds look right on average, but the average is misleading. They seem too confident when options price GGAL as calm, and some elections break them completely. All of this is exploratory. In about three years, the frozen test can say more about the overall hit rate.")
p.build()
print("plain calibration report written")
