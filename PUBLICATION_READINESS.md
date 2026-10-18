# Publication readiness — experimental source candidate

**Decision: READY_WITH_LIMITATIONS.** The source candidate is usable and reproducible within the explicit scope below. It is not an unqualified workbook-fidelity certification. No remote repository, push, Release, PyPI upload or deployment was performed. The user must separately authorize any publication.

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
| CI | Windows2022/Ubuntu24.04 Python3.13 source checks configured with pinned Actions. Hosted execution **NOT RUN** |

Tested implementation/data/tool commit: `296e0bf8d19ef65bdc288d948fbfb934aa3c0dbd`. Final delivery documentation/inventory commits do not change executable files or tests; external DELIVERY.json records final SHA, clean status, ZIP/bundle hashes and restoration checks. Public scope is exactly PUBLIC_FILES.json, which excludes itself from its digest list to avoid recursion. The final release audit verifies source/history patterns, licenses, links, bundle and archive; it is bounded, not security certification.

## Remaining limitations, not hidden passes

- Ordinary real Calc XLSX often returns UNKNOWN because presentation/metadata and missing-cell semantics are intentionally not certified. This prevents a general XLSX equivalence promise and is why the decision remains READY_WITH_LIMITATIONS.
- Windows has no hard worker RAM quota. Output limits are after rendering/serialization, not peak allocations. HTTP timeout is inactivity-based. The local server is not a public service or OS sandbox.
- One application/build and small generated dataset; headless automation is not interactive Office GUI acceptance. Excel, other locales/versions, native Linux browser and production data are NOT RUN.
- A confirmed representation/type difference may be intentional. No application attribution, algorithmic novelty, scientific innovation, general false-positive/recall estimate or production migration guarantee.
- GitHub-hosted workflow results cannot be claimed before an authorized remote exists. CI replays frozen real-export fixtures; it does not install/run Calc or prove a GUI workflow.

No unresolved demonstrated critical/important code defect blocks this explicitly limited source candidate. Broad XLSX certification and production deployment remain unsupported. Do not reclassify UNKNOWN as equivalent to obtain a stronger readiness label. Feature development stops at this candidate.
