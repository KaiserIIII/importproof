# ImportProof delivery report

Decision: **READY WITH LIMITATIONS for local source use**. A working Windows/Linux auditor is delivered, not a research novelty claim or a production migration certification. No remote publication was performed.

Delivered: CSV/TSV/XLSX parsing with original values, explicit exact/composite keys, ambiguity handling, ordered/multiset comparison, protected text and declared Decimal/date semantics, four conservative verdicts, cell/source/hash evidence, local drag-and-drop Web interface, CLI and HTML/JSON/CSV exports. All workbook sheets are considered unless selection is explicit. Formula text/cache is inspected without execution; unsafe or unsupported content rejects or remains UNKNOWN. Processing is bounded rather than unlimited streaming.

Validation at `f1b04b2ce5df1c77c51acb561fe7e0536c7b2188`: fresh Windows Python 3.13.0 **77/77**; isolated Linux Python 3.13.16 **77/77**; four full diagnostic reports identical; CLI exits **0/2/1**, Unicode and evidence verified; ten predeclared resource/adverse cases per platform passed. Actual final installed-package Chromium acceptance passed five checks, with no observed external request/page error. Real generated-data SQLite REAL import/export was executed and audited. [Full evidence and commands](docs/ACCEPTANCE.md).

Competition: pinned-source review of eight projects; actual csv-diff and daff baselines, 30 comparison invocations over 12 controlled pairs. Both already detect common changes; daff already handles several duplicate/order cases. Distinctions observed on specific empty/duplicate/semantic-policy cases are bounded results, not proof of general superiority. [Detailed comparison](docs/COMPETITORS.md).

Independent review reproduced two P2 problems, fixed with pre-fix failing tests and independently rechecked. Fresh final acceptance includes these fixes. No unresolved demonstrated P1/P2 remained in that bounded review. [Review record](docs/CODE_REVIEW.md).

Important limits: Excel/LibreOffice workflows, production/private data, Linux browser and hosted GitHub Actions are **NOT RUN**. Windows has no hard worker RAM quota; caps after rendering/serialization are not peak-memory bounds; HTTP timeout is inactivity-based. Complex spreadsheet presentation/formulas are outside equivalence certification. Reports contain input data. No real-world precision/recall, causal application attribution, algorithmic novelty or scientific contribution is claimed.

MIT project source and retained dependency licenses; hash-locked four-package install, official source revisions recorded, four OSV version queries with zero known matching advisories at audit time. These checks do not establish absence of vulnerabilities. [Release audit](SECURITY_AND_RELEASE_AUDIT.md), [handoff](HANDOFF.md), [public inventory](PUBLIC_FILES.json).

Remaining work is optional independent real-application compatibility validation, not a blocker to the stated bounded local source tool. Feature development is frozen. Publication requires separate authorization; no account/repository/Release/PyPI action is pending automatically.
