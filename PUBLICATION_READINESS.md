# Publication readiness — experimental source candidate

**Decision: READY_WITH_LIMITATIONS.** The experimental source is public at [KaiserIIII/importproof](https://github.com/KaiserIIII/importproof) following the owner's explicit authorization. It is usable and reproducible within the scope below, not an unqualified workbook-fidelity certification. No official Release, PyPI package or public service was published/deployed.

| Gate | Actual result |
| --- | --- |
| Original acceptance preservation | 0f5fde9667b036cf1965e1b34c45d804b3ea2846 retained in Git and verified complete baseline bundle; original evidence/ZIP untouched |
| Real application conversion | PASS: signed LibreOffice 26.2.5.2, 5 imports / 10 exports; headless UNO, no synthetic software output |
| Known original changes / normal control | All 28 observed CSV lexical differences retain cell evidence; normal CSV control EQUIVALENT; no real-world error-rate claim |
| Ambiguity | Duplicate identity UNKNOWN; text-protected empty distinction only equivalent under explicit caller rule |
| Actual Calc XLSX | UNKNOWN including normal control; confirmed numeric/type changes retained. This is a significant supported-scope limitation |
| Minimal actual defect fix | Formula-like header false equality fixed; ordinary numeric/ignored-header behavior preserved; input/output schema unchanged |
| Fresh Windows / Linux | **79 / 79 tests passed**, normal package installation, pip check, CLI 0/2/1, Unicode/hash/coordinate checks |
| Cross-platform consistency | 4 controlled CLI reports plus 10 actual Calc saved reports identical; 10 resource cases agree |
| Browser and reports | Both installed platform servers exercised through Windows Chromium: 6 checks each; original values, downloads, inert hostile HTML, actual 5MiB+1 rejection HTTP413 |
| Independent review | One demonstrated P2 resolved and rechecked; no unresolved demonstrated P1/P2 in bounded review |
| Identity | Authenticated GitHub user KaiserIIII id104786001 matches local Author/Committer noreply identity; no dummy authors |
| License/privacy | MIT original project; retained dependency notices; actual XLSX creator fields empty; no private dataset or Office binaries bundled |
| CI | Approved e2869e9 candidate passed hosted Windows2022/Ubuntu24.04 checks: 79 tests per platform plus installed CLI, Unicode and evidence checks. [Executed run](https://github.com/KaiserIIII/importproof/actions/runs/39089694800); [latest source checks](https://github.com/KaiserIIII/importproof/actions/workflows/tests.yml) |

Tested implementation/data/tool commit: `296e0bf8d19ef65bdc288d948fbfb934aa3c0dbd`. Accepted publication baseline: `e2869e99b154434862d84c61aa2c9ba82f0a042c`. Publication changes improve documentation/status and refresh the inventory; executable files and tests are unchanged. Public scope remains exactly 171 paths in PUBLIC_FILES.json, which excludes itself from its digest list to avoid recursion. External publication records retain final SHA, remote tree/path checks, CI results and author association. Earlier bundle/restoration records remain preserved. These are bounded checks, not security certification.

## Remaining limitations, not hidden passes

- Ordinary real Calc XLSX often returns UNKNOWN because presentation/metadata and missing-cell semantics are intentionally not certified. This prevents a general XLSX equivalence promise and is why the decision remains READY_WITH_LIMITATIONS.
- Windows has no hard worker RAM quota. Output limits are after rendering/serialization, not peak allocations. HTTP timeout is inactivity-based. The local server is not a public service or OS sandbox.
- One application/build and small generated dataset; headless automation is not interactive Office GUI acceptance. Excel, other locales/versions, native Linux browser and production data are NOT RUN.
- A confirmed representation/type difference may be intentional. No application attribution, algorithmic novelty, scientific innovation, general false-positive/recall estimate or production migration guarantee.
- Hosted CI passed on the approved source candidate. CI replays frozen real-export fixtures; it does not install/run Calc or prove a GUI workflow. Each later documentation head is separately checked on Actions.

No unresolved demonstrated critical/important code defect blocks this explicitly limited source candidate. Broad XLSX certification and production deployment remain unsupported. Do not reclassify UNKNOWN as equivalent to obtain a stronger readiness label. Feature development stops at this candidate.
