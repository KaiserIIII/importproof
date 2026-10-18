# Example provenance

All files here are nonprivate, controlled examples authored for this project. None is a real customer export, production import or proof of a spreadsheet application's behavior.

- before.csv / after-controlled.tsv contain deliberately edited leading zeros, long digits, decimal spelling, whitespace, Unicode and date spelling. Policies demonstrate strict versus explicitly permitted semantics. The main text identifiers remain protected in both policies.
- two-sheets.xlsx / rounded-controlled.xlsx are small valid OOXML packages authored as test fixtures, containing Data and Notes. One exact XML numeric token is deliberately changed. No spreadsheet application generated the mutation; no formulas were evaluated.
- sqlite-before.csv / sqlite-after.csv come from an **actually executed controlled SQLite3 typed import/export**. The first file's text values were inserted by bound parameters into `CREATE TABLE imported(id TEXT PRIMARY KEY,value REAL)`, queried and written by Python csv.writer. SQLite3.45.3 stored `00123` as123.0 and `12345678901234567` as1.2345678901234568e+16. This is a real engine conversion with known setup, not an Excel/LibreOffice workflow and not representative prevalence data. ImportProof itself cannot infer that provenance from the two files alone.

Reports in reports/ are actual tool executions on these documented examples, not hand-authored conclusions. Raw commands and environment remain in a separate maintainer evidence directory. No input is overwritten.
