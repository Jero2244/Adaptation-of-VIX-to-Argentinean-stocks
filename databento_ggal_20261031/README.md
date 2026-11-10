# GGAL ADR and option data from Databento, 2013-04-01 to 2026-10-29

Batch exports from Databento for the GGAL ADR (Nasdaq) and all listed GGAL options (OPRA). Downloaded by the user on 2026-10-30/31 and added on 2026-10-31 as the raw input for the ADR restart of the model. The folder `databento ggal data/` was moved here unchanged (the SHA-256 of each zip was checked before and after the move). The data is licensed, so the zips are ignored by git. Only this README and the manifest are versioned.

`manifest.json` is built by [`../build_databento_manifest.py`](../build_databento_manifest.py). It has each zip's hash, Databento job id and query, and the session dates. The builder also checks every file inside every zip against the SHA-256 that Databento ships in the zip's own `manifest.json`. All eight zips pass.

## Files

All files are DBN (Databento binary encoding), zstd-compressed, with raw integer prices (`pretty_px` off) and `instrument_id` as the output symbology. Each zip also holds Databento's `metadata.json`, `manifest.json` and `condition.json`.

| Zip | Dataset, schema | Symbols | Days | Size (zst) |
|---|---|---|---|---|
| `equity/XNAS-ohlc.zip` | `XNAS.ITCH` `ohlcv-1d` | `GGAL` | 2018-05-01 to 2026-10-29, one file | 61 KB |
| `equity/XNAS-bbo.zip` | `XNAS.ITCH` `bbo-1m` | `GGAL` | 2018-05-01 to 2026-10-29, 2,137 daily files | 25 MiB |
| `equity/XNAS-definition.zip` | `XNAS.ITCH` `definition` | `GGAL` | same | <1 MiB |
| `equity/XNAS-statistics.zip` | `XNAS.ITCH` `statistics` | `GGAL` | same | <1 MiB |
| `options/OPRA-cbbo_1m.zip` | `OPRA.PILLAR` `cbbo-1m` | `GGAL.OPT` (parent) | 2013-04-01 to 2026-10-29, 3,418 daily files | 956 MiB |
| `options/OPRA-Definition.zip` | `OPRA.PILLAR` `definition` | `GGAL.OPT` | same | 13 MiB |
| `options/OPRA-Statistics.zip` | `OPRA.PILLAR` `statistics` | `GGAL.OPT` | same | 81 MiB |
| `options/OPRA-TCBBO.zip` | `OPRA.PILLAR` `tcbbo` | `GGAL.OPT` | 2023-03-28 to 2026-10-29, 902 daily files | 6 MiB |

## Known points (before decoding)

- **The underlying starts in 2018.** Databento's Nasdaq ITCH history begins 2018-05-01. The options go back to 2013-04-01, so 2013-04 to 2018-04 has no underlying from this vendor.
- **Equity is one venue.** `XNAS.ITCH` is Nasdaq's own feed, not the consolidated tape. Volume is Nasdaq-only, and the bars' close can differ from the official consolidated close. The `statistics` schema carries the official values.
- **Options are consolidated.** `cbbo-1m` is the consolidated best bid and offer across the options exchanges, with sizes, sampled each minute. `tcbbo` (trades with the BBO before each trade) exists only from 2023-03-28.
- **Prices are unadjusted.** Dividends (USD per ADR, net of withholding, 1 ADR = 10 ordinary shares) and the 2025 rights offering must be handled explicitly. Options listed after a corporate action may be adjusted contracts with a non-standard deliverable. The definitions carry this.
- **Calendar.** Within the overlap the equity and option files cover exactly the same 2,137 days. The dates come from file names and are not yet checked against an exchange calendar.
- **Exposure.** 2025-2026 was used during development of the local model, and the ADR tracks the local share closely. Treat it as exposed here too.
- **Decoded tables.** The parquet version, with row counts and checks, is [`../ggal_adr_decoded_v1/`](../ggal_adr_decoded_v1/README.md).
