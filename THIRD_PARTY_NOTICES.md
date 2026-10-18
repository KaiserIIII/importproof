# Third-party notices

ImportProof source is MIT. Runtime dependencies and build tooling remain separate replaceable installed packages; no upstream implementation, wheel, browser or OS image is bundled. Exact wheel hashes/source revisions/times and copied license-file hashes are in [docs/DEPENDENCIES.json](docs/DEPENDENCIES.json); notices in [third_party/licenses](third_party/licenses/).

| Package | Version | Source revision | License |
| --- | --- | --- | --- |
|openpyxl|3.1.5|Mercurial13627b03ca25a1a98becf40e533b955615b13429|MIT|
|et_xmlfile|2.0.0|Mercurial683e1aecb8273371f409857b20e971110d97c3ec|MIT/Python notices retained|
|defusedxml|0.7.1|Git ebff1b493751e2f0775314bdd4188d64f07ea184|PSF-2.0|
|setuptools|84.0.0|Git72e919a8b10aaafc041205d4e3ae0e6a2e1e5f87|MIT and vendored notices retained|

Official Heptapod archive .hg_archival.txt identifies openpyxl/et_xmlfile tags and changesets; all190+3 Python files in installed wheels matched those upstream archives. This is source-file correspondence, not a complete reproducible-build assertion. Initial wheel resolution was hash-pinned; source-revision correspondence was completed before final acceptance and is recorded in maintainer audit. No recursive Skill or arbitrary source setup script was installed.

Independent baseline tools csv-diff1.2 (Apache2.0) and daff1.4.2(MIT), plus dependencies, were installed in a separate audit environment after source/entry review; not runtime dependencies or copied implementations. Fixture pairs are original controlled nonprivate data. Official competitor documentation/source snapshots remain outside this distribution and are linked in [COMPETITORS.md](docs/COMPETITORS.md).

Browser acceptance uses preexisting Playwright1.62.1(Microsoft,Apache2.0,source26a9e470a7b3c7822084b09fb7f13902c5f37b51) and Chromium149.0.7827.55, not bundled. GitHubActions checkout3d3c42e5aac5ba805825da76410c181273ba90b1 and setup-python5fda3b95a4ea91299a34e894583c3862153e4b97 are exact reviewed official MIT revisions. Hosted CI has not run because no remote publication is authorized. LocalLinux acceptance reuses an existing isolated AlpineWSL Python3.13.16 interpreter; OS/runtime assets stay outside the source.
