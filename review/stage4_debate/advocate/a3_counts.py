"""Row-count arithmetic for the locked period. It reads no data file. Sessions are an assumption: 585, position 0 = 2016-01-04.
NYSE had 252 sessions in 2016, so position 252 is about 2017-01-03. 2017 PASO is 2017-08-13, midterm is 2017-10-22."""
import numpy as np

N, START, WARM = 585, 252, 22
TAIL = 21  # about 21 sessions in a 30-day target window
print("coverage | valid origins | scored, windows may cross 2018-04-30 | scored, windows end by 2018-04-30 | first-origin training rows | position where 126 rows reached | scored indep windows (cross/strict) | fixed-step rows step 22/23")
for c in (1.0, .92, .864, .78, .72, .60, .50):
    origins = (N - WARM) * c
    origins_strict = (N - WARM - TAIL) * c
    scored = (N - START) * c
    scored_strict = (N - START - TAIL) * c
    train0 = (START - WARM - TAIL) * c
    reach = int(np.ceil(126 / c)) + WARM + TAIL
    print(f"{c:.3f} | {origins:.0f} (strict {origins_strict:.0f}) | {scored:.0f} | {scored_strict:.0f} | {train0:.0f} | {max(reach, START)} | {(N - START) / 21.7:.1f}/{(N - START - TAIL) / 21.7:.1f} | {(N - WARM) / 22 * c:.1f}/{(N - WARM) / 23 * c:.1f}")
print("scored share of valid origins:", round((N - START) / (N - WARM), 3))
print("fixed-step df with 5 coefficients at 20 rows:", 20 - 5, "one-sided 5% t critical:", 1.753)
print("c at which step-22 and step-23 rows reach 20:", round(20 / ((N - WARM) / 22), 3), round(20 / ((N - WARM) / 23), 3))
print("c at which valid origins reach 300:", round(300 / (N - WARM), 3))
print("Blocks of 21 in scored span:", round((N - START) / 21, 1), "strict", round((N - START - TAIL) / 21, 1))
print("Blocks of 63 in scored span:", round((N - START) / 63, 1), "strict", round((N - START - TAIL) / 63, 1))
