# Independent code review

A separate reviewer read the contract, readers, matching/semantics, spawned worker, CLI/report/Web boundaries and browser code, and ran real-byte counterexamples. The first assigned review stopped at an agent quota limit; it did not produce a completed review. A replacement reviewer completed the bounded independent review.

| Finding | Actual reproduction | Resolution | Verification |
| --- | --- | --- | --- |
| P2: valid numeric header display-format change falsely EQUIVALENT | Same XLSX numeric header raw `123`, format `00000` versus `General` | Emit UNKNOWN / HEADER_DISPLAY_FORMAT_CHANGED and retain both formats | Literal regression failed before fix; passed after; reviewer independently repeated original bytes |
| P2: duplicate inline-string payload silently discarded | Schema-invalid cell with two `<is>` children compared with original | Reject duplicate payload | Literal regression failed before fix; passed after; reviewer independently repeated original bytes |
| CSV projected cell cap enforced too late, identified during first partial review | Instrumented low-cap actual CSV and observed row allocations | Check projected rectangular cells before allocating extra row cell dictionaries | Focused regression plus complete suites |

The malformed XLSX case is robustness evidence; no claim that a standard spreadsheet application generates it. Review recheck: **77 tests passed in 8.364 s**, both demonstrated findings resolved; no unresolved demonstrated P1/P2 remained within its scope. Root separately inspected the changes and reran fresh Windows/Linux acceptance with 77 tests each.

Raw independent notes, scripts, pre-fix JSON, source hashes, RED/GREEN logs and re-review output remain in the sibling local evidence directory `importproof-evidence-20261018/review-fallback/`; original failures were not rewritten or deleted. Original review base was c451bf17271be69219c65e2512ce37c36c4d36d9; fixes were subsequently committed as f1b04b2ce5df1c77c51acb561fe7e0536c7b2188, the fresh-tested implementation.

Residual findings: output caps are checked after serialization/rendering and are not peak-allocation caps; HTTP socket timeouts constrain inactivity, not total request duration; Windows has no hard RAM quota. This was a bounded correctness/security-boundary review, not a complete vulnerability assessment or a guarantee of spreadsheet semantic coverage. No formula execution, production conversion or public deployment was certified.

## Real-conversion release-candidate review

A new independent reviewer reproduced all ten actual Calc reports exactly. It found one additional P2: literal CSV `=1+1\nplain\n` falsely returned EQUIVALENT because the formula-like text check only covered data cells. Parent reproduced five failing header spellings before the minimal fix; the shared existing predicate now also checks nonignored matched headers, retaining row1/header source evidence. Numeric/scientific headers and explicit ignore behavior remain unchanged.

The reviewer independently rechecked the same header bytes to UNKNOWN and original data control unchanged, reran report injection/CSV scalar guards and duplicate-key evidence checks, and found no unresolved demonstrated P1/P2. Its immediate recheck had78 tests; one subsequent real-export compatibility method brought the final fresh Windows/Linux suites to79. Final publication-document review is recorded separately in the RC raw archive. Concurrent RED-test observations were preserved and not mislabeled as frozen-baseline failures. Raw archive: importproof-rc-evidence-20261018/independent-review/.
