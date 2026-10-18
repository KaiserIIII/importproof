# Example provenance

All source datasets here are nonprivate, controlled examples authored for this project. None is a real customer dataset or production import. The original examples below are distinguished from the actual LibreOffice exports added under real-calc/.

- before.csv / after-controlled.tsv contain deliberately edited leading zeros, long digits, decimal spelling, whitespace, Unicode and date spelling. Policies demonstrate strict versus explicitly permitted semantics. The main text identifiers remain protected in both policies.
- two-sheets.xlsx / rounded-controlled.xlsx are small valid OOXML packages authored as test fixtures, containing Data and Notes. One exact XML numeric token is deliberately changed. No spreadsheet application generated the mutation; no formulas were evaluated.
- sqlite-before.csv / sqlite-after.csv come from an **actually executed controlled SQLite3 typed import/export**. The first file's text values were inserted by bound parameters into `CREATE TABLE imported(id TEXT PRIMARY KEY,value REAL)`, queried and written by Python csv.writer. SQLite3.45.3 stored `00123` as123.0 and `12345678901234567` as1.2345678901234568e+16. This is a real engine conversion with known setup, not an Excel/LibreOffice workflow and not representative prevalence data. ImportProof itself cannot infer that provenance from the two files alone.

Reports in reports/ are actual tool executions on these documented examples, not hand-authored conclusions. Raw commands and environment remain in a separate maintainer evidence directory. No input is overwritten.

## Actual LibreOffice exports

`real-calc/risk-source.csv` and `control-source.csv` are deliberately authored nonprivate inputs. The five case subdirectories contain **actual CSV/XLSX outputs saved by LibreOffice Calc 26.2.5.2**, not manually reconstructed workbook packages. `conversion.json` records real UNO cell observations and requested/returned options. `audit-*` and `audit.html/csv` are actual ImportProof reports. The manifest records original file hashes; XLSX creator/lastModifiedBy fields are empty and package bytes were not sanitized after export.

These are real headless application conversions of controlled data, not interactive Office GUI acceptance or evidence of production prevalence. Default/text/special-number modes and UNKNOWN XLSX limitations are documented in [REAL_CONVERSION_RESULTS](../REAL_CONVERSION_RESULTS.md). The optional replay tool opens only these frozen source fixtures in an independent Calc profile. No third-party software binaries are bundled.
