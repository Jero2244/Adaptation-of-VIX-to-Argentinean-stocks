# Stage 4: Alpaca against official closes, open dates only

Overlap: 2018-05-01 to 2026-09-14. Alpaca sessions: 2104. Official sessions: 2104.
Only in Alpaca: []. Only in the official table: [].
Signed median, bp: 0.000 on all dates, 0.000 on 2018-05 to 2019-07.
Pre-break b: 0.5254 with Alpaca on 1431 rows, 0.5252 with official closes on 1431 rows. Official closes here use the same close-only path, and the study value is .525.

| id | measure | sample | value | limit | passed | if_it_fails |
|---|---|---|---|---|---|---|
| B1 | Sessions in one source only | all overlap | 0.0000 | 3.0000 | True | Find the cause, fix the reader, rerun, log |
| B2 | Signed median log(Alpaca / official), bp | all overlap | 0.0000 | 5.0000 | True | Find the cause, fix the reader, rerun, log |
| B2 | Signed median log(Alpaca / official), bp | 2018-05 to 2019-07 | 0.0000 | 5.0000 | True | Find the cause, fix the reader, rerun, log |
| B3 | Absolute median, bp | all overlap | 0.0000 | 10.0000 | True | Stage 4 stops, and the user decides |
| B3 | Absolute median, bp | 2018-05 to 2019-07 | 0.0000 | 10.0000 | True | Stage 4 stops, and the user decides |
| B4 | Absolute 99th percentile, bp | all overlap | 0.0000 | 100.0000 | True | Stage 4 stops, and the user decides |
| B4 | Absolute 99th percentile, bp | 2018-05 to 2019-07 | 4.3346 | 100.0000 | True | Stage 4 stops, and the user decides |
| B5 | Median absolute log(RV30 ratio) | all overlap | 0.0000 | 0.0500 | True | Stage 4 stops, and the user decides |
| B5 | Median absolute log(RV30 ratio) | 2018-05 to 2019-07 | 0.0000 | 0.0500 | True | Stage 4 stops, and the user decides |
| B6 | Change in b, pre-break primary rows, Alpaca RV and HAR | before 2025-03 | 0.0002 | 0.0300 | True | No verdict with Alpaca RV. The user drops Stage 5, or reports the test as descriptive only |

A pass on open dates does not prove the same fit in 2016-2017. The limits use assumed noise sizes, because nobody had read the Alpaca file.
