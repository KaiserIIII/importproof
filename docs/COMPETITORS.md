# Existing tools and executed comparisons

Observed2026-10-18. CSV/table diff, keyed alignment, ordering policies, semantic comparison, validation, joins and visual inspection are established capabilities. ImportProof is an integrated evidence-review workflow; **no algorithmic novelty, market gap or general superiority is established**. Baseline configurations and verdicts differ; a finding here is not proof that another tool is broken.

## Official sources read

Eight pinned repositories and55 actual source/documentation files were inspected. Head/activity is a snapshot, not a maintenance-quality score. Implementation/release versions actually executed are distinguished below.

| Project | Reviewed repository commit | License | Coverage/overlap |
| --- | --- | --- | --- |
|[csv-diff](https://github.com/simonw/csv-diff/tree/26903b74eefcd65be761810f51b0e55c033bde66)|26903b74eefcd65be761810f51b0e55c033bde66|Apache2.0|Text/keyedCSV differences and machine output; directly overlaps common changes.|
|[daff](https://github.com/paulfitz/daff/tree/ad5a02efd58ea7a2a70bb888f65ab610d136db28)|ad5a02efd58ea7a2a70bb888f65ab610d136db28|MIT|Table alignment/diff, order, duplicates, tolerance, several output formats.|
|[Frictionless](https://github.com/frictionlessdata/frictionless-py/tree/c08fa29cb0708427ae65bb689ded8e2691078a82)|c08fa29cb0708427ae65bb689ded8e2691078a82|MIT|Schema validation, parsing, transform and **table_diff**, not merely validation.|
|[CleverCSV](https://github.com/alan-turing-institute/CleverCSV/tree/e80acaa5c324889416a5727ad9929d5b2f8bccb6)|e80acaa5c324889416a5727ad9929d5b2f8bccb6|MIT|Robust dialect detection andCSV parsing; ImportProof chooses conservative explicit interpretation rather than reimplementing dialect research.|
|[VisiData](https://github.com/saulpw/visidata/tree/131d7492a02a22f0b72a014ec904955187ad8852)|131d7492a02a22f0b72a014ec904955187ad8852|GPL3.0|Interactive table exploration, joins/diffs and type-aware operations.|
|[csvkit](https://github.com/wireservice/csvkit/tree/6d19c625214977ab2988e674441ca24638bc12d3)|6d19c625214977ab2988e674441ca24638bc12d3|MIT|Mature data import/conversion tools, explicit no-inference mode.|
|[qsv](https://github.com/dathere/qsv/tree/ba0b67429f4a5c0714170b0b112ef25452d867fe)|ba0b67429f4a5c0714170b0b112ef25452d867fe|MIT notices reviewed|Diff/schema/validation/sniff and data-processing workflow.|
|[data-diff](https://github.com/datafold/data-diff/tree/1410c6cd0b915ae24a15e03a7de15ff41beebaf0)|1410c6cd0b915ae24a15e03a7de15ff41beebaf0|MIT|Database dataset comparison; archived/unsupported per upstream, not thisCSV/XLSX baseline.|

The first seven were not archived at observation. Source review does not certify correctness or complete capability. Frictionless/CleverCSV/VisiData/csvkit/qsv/data-diff runtime comparisons were **NOT RUN**; no claims of their measured performance are made.

## Executable baseline setup

Windows11 build26200, Python3.13.0, dedicated wheel-only venv, pinned hashes and inspected import/CLI source before execution. csv-diff1.2 at26903b74eefcd65be761810f51b0e55c033bde66; daff1.4.2 release commit6dbb7510b097369ac33b9126a88881f067f07a20. Other baseline dependencies were separately locked, not added to ImportProof. Original controlled before/after files and hashes are included in [tests/compatibility/manifest.json](../tests/compatibility/manifest.json); no real data or upstream source implementation copied.

Commands:

```text
csv-diff before.csv after.csv --key id --format csv --json
daff diff --no-color --fail-if-diff --id id before.csv after.csv
```

csv-diff exits0 even when its JSON reports changes; output was inspected. Daff uses0same/1difference/2error. A difference exit is an expected result, not a failed comparison.

| Controlled case |csv-diff1.2|daff1.4.2 ordered|ImportProof strict keyed policy|
| --- | --- | --- | --- |
|Leadingzero00123→123|Detects text change|Detects text change|CONFIRMED_LOSS + suspected mechanism|
|Long digits changed|Detects text change|Detects text change|CONFIRMED_LOSS, exact Decimal evidence|
|Scientific spelling|Detects text change|Detects text change|CONFIRMED_LOSS + suspected mechanism|
|Row reorder|No difference|Reorder detected|CONFIRMED_LOSS unless caller ignores order|
|Earlier duplicate-key row changed|No difference in tested fixture|Change detected|UNKNOWN identity, no arbitrary pairing|
|Earlier duplicate-name column changed|No difference in tested fixture|Difference detected; inferred alignment unusual|UNKNOWN header identity, retained evidence|
|Unquotedempty→quotedempty|No difference|No difference|CONFIRMED_LOSS representation distinction|
|Decimal scale1.00→1.0|Detects text change|Detects text change|CONFIRMED_LOSS; numeric rule can explicitly allow|
|Decimal value1.00→1.01|Detects text change|Detects text change|CONFIRMED_LOSS|
|Date text spelling|Detects text change|Detects text change|CONFIRMED_LOSS; unique declared date interpretation may allow|
|Duplicate row count2→1|No difference in tested keyed/unkeyed fixture|Deletion detected|UNKNOWN ambiguous key, duplicates retained|
|UnquotedNULL→quotedNULL|No difference|Special null/string difference|EQUIVALENT literaltext; no NULL meaning guessed|

Daff unordered mode ignores reordering while preserving tested duplicate changes. Its explicitly selected `--ignore-epsilon 0.001` ignored decimal spelling **and the tested changed long integer** because tolerance uses floating parsing; default daff did detect that integer change. This supports transparent rules, not a broad claim about unsafe default behavior.

**30 baseline comparisons** ran on12 controlled pairs:24 main paired runs,3daffunordered,1csv-diffunkeyed,2dafftolerance. Five environment/help commands made35loggedcommands. No comparison errors/timeouts; all comparisonstderr empty. Daff help exits1 and prints usage tostderr; retained separately, not hidden as a test failure. ImportProof ran the same12 byte-pairs under its declared policy and all12 matched independently chosen verdict oracles. One unittest method rechecks these12; they are not12additional test methods.

## Value and limits

These results support a usable combination of explicit text/numeric/date policies, blank/empty provenance, XLSX lexical digits/types/formulas, conservative matching, original coordinates/hashes and separate observed/suspected findings. They do not establish that every competitor/extension lacks these capabilities or that this workflow improves real user outcomes. Baselines do not measure recall/precision, large-file ranking, XLSX performance or production conversion prevalence. Real application causality remains unidentifiable from a pair alone.

Full commands, exact versions, source/license snapshots, wheel/source hashes, independent baseline setup failures and actual outputs remain in the separate maintainer evidence archive. Public comparison summary and the original synthetic fixtures are sufficient to repeat the narrow tests; no private material is required.
