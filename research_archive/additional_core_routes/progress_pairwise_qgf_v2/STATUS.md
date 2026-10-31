# Progress-Pairwise QGF V2 Status

## 2026-10-28 12:17 CST - Collection gate is mathematically unreachable

- Exact step `1593640.407` remains healthy and is continuing the fixed,
  non-replaceable 32-group sequence for complete evidence accounting.
- Terminal receipts through entry 15 contain 7 complete groups and 9 strictly
  unavailable groups (`0 3 6 7 9 11 12 14 15`), all due to the frozen exact
  boundary-policy-observation mismatch rule.
- Even if every remaining group completes, the maximum is now 23/32, below
  the preregistered 24/32 admission threshold. Five locked-confirmation groups
  are already unavailable, so its maximum is 11/16, below the required 12/16.
- Therefore V2 cannot release development labels or train/evaluate its critic.
  The running collection is not interrupted or rewritten; after it exits,
  finalization and independent artifact audit will freeze the full denominator,
  failures, hashes, and actual cost as `V2_COLLECTION_INSUFFICIENT`.
- This is a prospective cohort/restoration-availability failure, not evidence
  that QGF is generally ineffective and not an online efficacy result.

## 2026-10-28 - Prospective population running

- V1 remains frozen as `NO_STABLE_PROGRESS_PAIRWISE_CRITIC`.
- V2 registered 32 new physical groups with zero overlap against the 16
  Failure-Critical and 16 V1 groups: 16 development and 16 locked confirmation.
- Registration manifest SHA:
  `00e49dd200ce4851de0678c6385616f12e9c1d82392e47c1c55393670ba18226`.
- Frozen support bases are byte-identical to V1, SHA:
  `1eb456cfc534e115fa907db2287f835643e066c7788efae7d3d99b4f5a9ff9f2`.
- Initial step `1593640.404` failed before WAM/model actions after 41 seconds
  because the manifest exposed only `v1_support_bases_sha256`, while the
  unchanged runner requires the standard `support_bases_sha256` alias.
- The metadata-only repair added that equal alias and changed no cohort,
  split, support basis, model, seed, action, horizon or threshold.
- The single bounded retry is exact step `1593640.405` on the assigned idle
  gpu1/GPU0. It is loading the frozen WAM and will execute entries 0--31
  sequentially with a remaining hard cap of 28,759 allocated GPU seconds.
- No V2 paired-action result or online QGF result exists yet.
