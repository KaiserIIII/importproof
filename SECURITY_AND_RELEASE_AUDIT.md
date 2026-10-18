# Source delivery and security audit

Scope: local source edition 0.1.0. No remote repository, push, Release, PyPI upload, public server or installer was created. This audit defines a distributable source boundary; it is not authorization to publish.

## Included and excluded material

Included: original MIT source, tests, controlled compatibility fixtures, nonprivate generated examples, actual selected tool reports and browser screenshot, English/Chinese documentation, exact dependency inventory and retained license notices, pinned source CI and reproduction tools. `PUBLIC_FILES.json` records Git-blob byte hashes and sizes, excluding itself to avoid a circular digest.

Excluded: `.venv`, Python caches, build outputs, private-input directories, dependency wheels/source archives, browser traces and original raw research/experiment logs. The latter live in the separate sibling evidence directory and must not be automatically published. Test ZIP/XML/formula payloads are deliberate inert adversarial fixtures, not real targets or private workbooks. Examples and reports have no customer data.

The project source is MIT. openpyxl/et-xmlfile retain their MIT/Python notices; defusedxml retains PSF licensing; setuptools and bundled notices retain their individual terms. Exact license files and hashes are in `docs/DEPENDENCIES.json`; no competitor implementation was copied. Competitor fixture data was generated for the comparisons, not copied from private user files. VisiData GPL source was read externally and is not bundled or linked into the tool.

## Dependency and source checks

- Four exact wheel artifacts are version/hash locked. Upstream Git/Mercurial changesets, source/license review and installation times are recorded. Initial wheel installation occurred before exact source-node lookup finished; correspondence was audited before final validation. This sequence is retained rather than represented as pre-install source review.
- Official openpyxl and et-xmlfile source archives matched all 193 Python wheel members. The implementation source is not vendored into this repository.
- Four executed OSV package/version queries returned no known matching advisories on 18 October 2026. [Raw query results](docs/evidence/dependency-osv.json). This does not prove the absence of vulnerabilities. No installed Codex Security scanner was available in this session; bounded manual, test, dependency and independent review checks were used.
- GitHub checkout/setup-python action full SHA references were verified through the official upstream API. CI uses read-only repository permissions, no persisted checkout credentials, no pull_request_target or remote publication. Hosted CI execution remains NOT RUN.
- The final delivery check scans staged blobs and all existing Git history blobs for private-key/token/access-ID/credential-URL patterns, rejects local account identifiers and prohibited build/cache/private paths, checks relative Markdown file links, verifies license hashes and compares executable paths with the fresh-tested commit. Machine output is preserved as `release-checks.json` in the external evidence directory. It is a bounded pattern check, not a complete credential or legal/privacy audit.

## Runtime trust and residual risks

Files stay local and are never rewritten. Uploaded filenames are hints, not trusted provenance. Reported hashes identify received bytes; callers must trust their own source files, alignment keys and policy. Two snapshots cannot prove which app caused a conversion. Reports contain original data and should be treated as sensitive when input is sensitive.

Formulas/macros/external links are not executed or fetched. Restricted ZIP/XML handling, exact input limits, spawned workers and failure-to-UNKNOWN/error behavior reduce exposure; this is not an OS security sandbox. Windows has no hard RAM quota. Output limits are checked after serialization/rendering and do not cap peak allocations. HTTP socket timeout is based on inactivity, not total request duration. Bind only to loopback; do not publish/proxy the service.

Independent review's demonstrated issues were resolved and rechecked; see [review](docs/CODE_REVIEW.md). Fresh Windows/Linux installation and tests, final installed-package browser acceptance and actual SQLite generated-data conversion are recorded in [acceptance](docs/ACCEPTANCE.md). Real headless Calc conversion now ran; Excel, interactive Office GUI and production migrations remain NOT RUN. No broad accuracy, causal or research-innovation claim is warranted.

Delivery decision: **READY WITH LIMITATIONS for bounded local source use**. No known demonstrated P1/P2 remains from the completed review. No source publication is performed or automatically scheduled. The final SHA, clean status, source inventory verification, recoverable bundle verification and ZIP hash are recorded in the external `DELIVERY.json` after the final local commit.

## Current RC additions

Original verified baseline bundle is retained separately. GitHub authenticated account id104786001/loginKaiserIIII matches all local noreply Author/Committer identities. Added material is original formula-header fix/tests, optional real-Calc replay tools, generated source CSVs and actual software exports/selected reports. All five XLSX package creator/lastModifiedBy fields are empty; decompressed members were checked for local account/path strings before inclusion. No Calc/Excel binaries, profiles or personal files are bundled. Native installed Calc signatures were valid and source build recorded. The default import setting allowing formula interpretation was observed, but all submitted fixture cells were formula-free; macros were disabled. No hostile formula was executed in Office.

Both installed Web platform servers passed actual browser escaping/standalone HTML checks and actual 5MiB+1 input rejection HTTP413. Scalar CSV guards were checked on actual downloaded reports and independently with seven adversarial values. Windows RAM and output-allocation limitations remain disclosed. The current release audit and final restoration records are in importproof-rc-evidence-20261018/, while original acceptance audits remain intact. No full security certification or third-party scanner pass is claimed.
