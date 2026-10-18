# Real LibreOffice conversion results

Executed 18 October 2026 on Windows 11 build 26200. **Five actual Calc imports and ten actual CSV/XLSX exports completed**, using signed installed LibreOffice **26.2.5.2**, source build **cd7284b4cbbfeb507e630c1aac019f4157393acb**. Binary signature: The Document Foundation; exact executable hashes, version.ini, signature check and upstream build response remain in the raw evidence archive. The signed installation was already present, so no software installation was required. Excel 16.0.20430.20146 was found but **NOT RUN**; the requested Calc alternative was used. No private/user workbook was opened.

This is **real headless Calc through its official UNO API**, not a simulated export, renderer or synthetic spreadsheet application. It is not an interactive mouse/dialog GUI acceptance. Each import used a fresh independent profile; existing Office instances and personal profiles were not reused. The CSV source data is deliberately authored and nonprivate. Only the files actually saved by Calc are called real exports. Original source/export bytes, cell observations and hashes are included under [examples/real-calc](examples/real-calc/).

## Input and independently observed changes

The risk CSV has stable unique `row_id`, duplicate `business_id`, leading-zero identifiers, 20-digit integers, scientific-notation text, ISO/ambiguous/slash date text, Chinese/emoji/Unicode, unquoted blanks, quoted empty strings, literal NULL and surrounding whitespace. A separate fully populated nonnumeric control CSV tests ordinary preservation.

| Field at source row 2 | Original | Default Calc CSV | Explicit-text Calc CSV |
| --- | --- | --- | --- |
| leading_zero | `00123` | `123` | `00123` |
| twenty_digit | `12345678901234567890` | `1.23456789012346E+019` | Original 20 digits |
| scientific_text | `1E10` | `10000000000` | `1E10` |
| date_text | `2026-10-18` text | Same CSV spelling; actual Calc/XLSX value is a stored date | Text retained |
| quoted_empty | CSV `""` | Unquoted empty | Unquoted empty |
| Chinese / surrounding spaces | Source Unicode / ` padded ` | Preserved | Preserved |

Actual UNO observations record numeric/text/empty type, displayed string, numeric repr and format before saving. Independent stdlib OOXML inspection confirmed a changed stored numeric token for the 20-digit value. Source/export CSV lexical comparison found 12 default, 3 explicit-text and 13 special-number changes; all 28 have stable original-row/cell evidence in ImportProof. These are narrow cell observations, not a recall/precision estimate. Counts below are **findings**, not necessarily distinct damaged values.

Explicit text columns preserved all tested nonempty risk strings, but Calc merged quoted-empty and unquoted-empty representations. Strict ImportProof therefore reports three EMPTY_NULL_CHANGE observations, not three invented software failures. When the caller explicitly declares `null_tokens: [""]`, that text CSV pair becomes EQUIVALENT. The source distinction cannot be recovered from the export alone.

Both normal-control CSV exports are EQUIVALENT with no findings. All five actual XLSX exports, including the normal control, return **UNKNOWN** because Calc writes workbook/sheet/row or rich-string metadata not interpreted by this prototype; absent empty cells add uncertainty. Normal control has zero confirmed-loss findings. Known numeric/type changes in default/special XLSX remain visible alongside UNKNOWN. We did not remove conservative warnings to manufacture an XLSX pass.

## Recorded options and reproduction

1. `loadComponentFromURL` with Hidden=true, ReadOnly=true, CSV FilterName, MacroExecutionMode=NEVER_EXECUTE and UpdateDocMode=NO_UPDATE.
2. Default: **omit FilterOptions**, then record returned settings. Actual settings: `44,34,76,1,,0,false,false,true,false,false,0,true,true,true`. Defaults are for this fresh profile/build/locale only, not every user's GUI session.
3. Explicit text: token 5 is `1/2/2/2/3/2/4/2/5/2/6/2/7/2/8/2/9/2/10/2`, protecting all ten columns as text. UTF-8/comma/quotes, language 1033; special/scientific detection off.
4. Special-number case: a separately named **nondefault** mode, language 1033 with special/scientific detection on. In this case `01/02/2026` was a date and CSV displayed `26/1/2`; the inferred date is not guessed by ImportProof.
5. Actual `storeToURL`: `Calc MS Excel 2007 XML` for XLSX; CSV filter `44,34,76,1,,1033,false,true,true,false,false,0,false,false` for UTF-8/comma/export-as-shown. Returned import settings and all cell observations are in each `conversion.json`. Originals were not sanitized or reconstructed; creator/lastModifiedBy are empty in all five output packages.

Safety-setting exception: omitted default options returned Import-as-formulas=true. The pre-execution preference was to disable that option, but doing so would replace the default being measured. **All submitted source values were formula-free**, and macros were disabled. Explicit text/special modes set formula interpretation false. No hostile formula was passed to Calc. The exception is retained in raw PROTOCOL_DEVIATIONS.md; default formula disabling is not falsely claimed.

With the checked-in fixtures and an existing LibreOffice installation:

```powershell
python tools/replay_real_calc.py --soffice "C:\Program Files\LibreOffice\program\soffice.com" --uno-python "C:\Program Files\LibreOffice\program\python.exe" --output new-calc-run
python -m importproof compare examples/real-calc/risk-source.csv examples/real-calc/risk-default/export.csv --keys row_id --output new-calc-audit
```

Use the project's Python for the runner/ImportProof; LibreOffice's bundled Python is only the UNO client. `--case control-default` reran successfully using the distributed optional runner. The five original imports all ran with the preserved equivalent orchestration/worker. Linux Calc replay is NOT RUN. See official [CSV options](https://help.libreoffice.org/latest/en-US/text/shared/guide/csv_params.html) and the [exact installed-build option source](https://github.com/LibreOffice/core/blob/cd7284b4cbbfeb507e630c1aac019f4157393acb/sc/source/ui/dbgui/asciiopt.cxx).

## Actual ImportProof outcomes

| Case / policy | Format | Overall | Confirmed | Suspected | Unknown |
| --- | --- | --- | --- | --- | --- |
| risk-default | csv | CONFIRMED_LOSS | 12 | 8 | 0 |
| risk-default | xlsx | UNKNOWN | 10 | 8 | 16 |
| risk-text | csv | CONFIRMED_LOSS | 3 | 0 | 0 |
| risk-text | xlsx | UNKNOWN | 0 | 0 | 16 |
| risk-special | csv | CONFIRMED_LOSS | 13 | 7 | 0 |
| risk-special | xlsx | UNKNOWN | 11 | 9 | 16 |
| control-default | csv | EQUIVALENT | 0 | 0 | 0 |
| control-default | xlsx | UNKNOWN | 0 | 0 | 9 |
| control-text | csv | EQUIVALENT | 0 | 0 | 0 |
| control-text | xlsx | UNKNOWN | 0 | 0 | 9 |
| duplicates | csv | UNKNOWN | 4 | 2 | 1 |
| text-null-equivalent | csv | EQUIVALENT | 0 | 0 | 0 |

Duplicate business_id intentionally returns UNKNOWN for the ambiguous group and does not invent row pairings; unique `row_id` is used for the primary cell comparison. Two files cannot establish intermediate application state or causality. Actual Calc is known here from independently controlled execution, not inferred by ImportProof.

## Mature baseline results on the same real CSV exports

Used the existing independently audited csv-diff **1.2**, daff **1.4.2** environment and SQLite **3.45.3** explicit text/primary-key constraints plus an EXCEPT query. No new runtime dependencies were installed. Fifteen actual diff invocations and five SQLite constraint/query runs completed. [Versions and machine observations](docs/evidence/real-baselines.json).

| Case | csv-diff changed rows | daff exit raw / BOM-normalized | SQLite different source rows |
| --- | --- | --- | --- |
| risk-default | 3 | 1 / 1 | 3 |
| risk-text | 0 | 1 / 0 | 3 |
| risk-special | 3 | 1 / 1 | 3 |
| control-default | 0 | 1 / 0 | 0 |
| control-text | 0 | 1 / 0 | 0 |

csv-diff API decoded both originals with UTF-8-SIG. Raw daff saw a BOM-bearing source header versus a BOM-free export; both raw outcomes and a separately declared BOM-removal control are retained. After this explicit decoding-equivalent normalization it detects ordinary default/special changes and accepts the normal control. csv-diff/daff report no text-mode change when only quoted-empty provenance was lost. SQLite distinguishes it here because the small baseline explicitly used QUOTE_NOTNULL and mapped blank/empty to NULL/empty TEXT. This is not a turnkey SQLite fidelity product or unique ImportProof capability. Frictionless runtime remains NOT RUN; its earlier pinned-source review is not represented as an executed validation benchmark.

These observations do not prove superiority, general error rates, or production effectiveness. Normal files can receive UNKNOWN, particularly XLSX. A strict representation difference is not proof of unintended business damage.

## Preserved failures and limits

External analysis harness attempt 1 had module-scope directory creation that failed on Windows spawn reimport; attempt 2 over-assumed daff's BOM behavior. Browser harness attempts used a hidden filter control after changing files and then assumed HTTP400 instead of the endpoint's documented HTTP413. Original scripts/FAIL outputs remain outside public source; corrected runs passed without changing production behavior for those harness errors. Success criterion stayed actual safe rejection, not a particular guessed HTTP status. The one production change was an independently reproduced formula-like-header false EQUIVALENT, fixed with RED/GREEN regression evidence.

Raw archive: sibling `importproof-rc-evidence-20261018/` with protocol, commands, profiles, actual exports, UNO observations, pre-fix/header tests, independent review, fresh environments, browser traces and failed attempts. Selected public evidence excludes profiles, user paths, binaries and private files. Interactive Calc/Excel GUI, Excel conversions, other Office versions/locales and production migration remain NOT RUN.
