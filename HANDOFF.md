# ImportProof handoff

Delivery: experimental source edition 0.1.0, now public at [KaiserIIII/importproof](https://github.com/KaiserIIII/importproof) after owner authorization. The approved e2869e9 source passed hosted Windows/Linux checks, 79 tests each; [latest CI](https://github.com/KaiserIIII/importproof/actions/workflows/tests.yml). No hosted application deployment, installer, PyPI package or official Release was created. Development is frozen. The original preparation/evidence instructions below remain available; newer publication records are in the separate maintainer publication evidence directory.

Start with [README](README.md) / [中文说明](docs/USER_GUIDE_ZH.md), then [comparison contract](docs/COMPARISON_CONTRACT.md), [architecture](docs/ARCHITECTURE.md), [acceptance](docs/ACCEPTANCE.md), [security](docs/SECURITY.md) and [limitations](docs/KNOWN_LIMITATIONS.md).

## Install, use and reproduce

Use Python 3.13, a new venv, hash-locked dependencies, then normal project installation exactly as in README. Start `python -m importproof serve` at localhost:8766 or run `python -m importproof compare examples/before.csv examples/after-controlled.tsv --policy examples/strict-policy.json --output new-report`. The example deliberately returns exit 2 (findings); identical supported input returns 0; invalid file/processing/output returns 1. Command syntax errors return 2.

To reproduce: `python tools/verify.py new-acceptance`, then `python tools/resource_checks.py new-resources`. Both output paths must be new. The runners preserve exact commands and outputs. Standard output from compare is the canonical JSON; HTML/CSV are secondary presentations. After code edits reinstall the normal package before testing it; changing source alone does not update an installed wheel.

## Structure and contracts

- `src/importproof/readers.py`: strict bounded CSV/TSV and safe XLSX byte/metadata extraction.
- `compare.py`: explicit policy validation, exact matching, semantic equivalence and diagnostic evidence.
- `worker.py`: spawned comparison process, deadline and result caps; Linux address-space limit.
- `cli.py`, `web.py`, `static/`: installed CLI and local Web interface using the same worker.
- `reports.py`: JSON, inert HTML and formula-guarded findings CSV.
- `tests/`: 79 unittest methods, including 12 compatibility cases in one method.
- `examples/`: nonprivate controlled inputs, actual SQLite conversion files, and real generated reports; provenance is explicit.
- `docs/evidence/`: actual selected portable acceptance records. Full raw experiments are deliberately outside public source.
- `requirements.lock`, `docs/DEPENDENCIES.json`, `third_party/licenses/`: exact dependencies, upstream revisions, licenses.
- `.github/workflows/tests.yml`: pinned Windows/Linux source checks, now executed on GitHub; they do not run Office or replace application acceptance.
- `PUBLIC_FILES.json`: SHA-256/size inventory of distributable Git blobs, excluding itself to avoid recursion.

## Evidence and restoration

Implementation tested: `296e0bf8d19ef65bdc288d948fbfb934aa3c0dbd`. Final documentation commits retain those implementation bytes. Current raw archive is importproof-rc-evidence-20261018/; earlier evidence remains separately preserved. Final Git SHA and bundle/ZIP paths are recorded in the external `DELIVERY.json` because a commit cannot contain its own SHA. Raw evidence sibling: `importproof-evidence-20261018/`; it includes fresh environment commands, original failures, external research, dependency audits, browser trace, independent review and adversarial inputs. Do not upload this directory automatically.

The local source ZIP and verified Git bundle are recovery copies, not released packages. A new checkout/archive was installed and tested without the original source path. `PUBLIC_FILES.json` describes the final source tree; verify its SHA-256 values after extraction. Source checkout excludes venvs, caches, private inputs, wheel archives and external research snapshots.

## Limits for a successor

No result identifies which app caused a change. CONFIRMED_LOSS means an observed disallowed difference conditional on alignment/policy, not proof of accidental business loss. UNKNOWN is not a pass. Formula/macros never execute; complete workbook rendering and formula correctness are not certified. Windows has no hard RAM ceiling; output caps are not peak-memory caps. Reports expose original values and should stay private for private data.

The earlier planned real-application validation has now been completed for one LibreOffice build through headless UNO. Excel, another application version/locale and interactive Office GUI remain unverified. Do not add heuristic causal attribution or claim broad accuracy based on controlled examples. Do not publish remotely without separate authorization.

## Current candidate

Read PUBLICATION_READINESS.md and REAL_CONVERSION_RESULTS.md before use. Decision READY_WITH_LIMITATIONS; normal actual Calc XLSX can be UNKNOWN. Actual five-case Calc campaign is complete; optional tools/replay_real_calc.py reproduces only frozen nonprivate fixtures with an installed UNO-capable Calc. A future separately authorized validation could cover another app/version/locale; no further feature work is scheduled. Current DELIVERY.json and final bundle/ZIP are in the RC evidence sibling, not the historical evidence directory.
