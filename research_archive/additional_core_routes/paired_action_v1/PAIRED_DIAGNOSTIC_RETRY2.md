# Paired Diagnostic V1 Retry 2

Authorized explicitly by the user on 2026-10-27 CST after Retry 1 was frozen
as an invalid infrastructure result.

The only scientific-code change is the initial-state validation operation:

- Retry 1: `data_contract.array_hash(initial)` (incorrect for this manifest).
- Retry 2: `sha256(initial.tobytes()).hexdigest()` (the manifest operation).

Retry 1 source and outputs remain immutable. Before GPU dispatch, a CPU-only
audit must check the raw-byte hash for every one of the fixed 16 entries and
freeze its report. Model, checkpoint, task entries, physical groups, seeds,
branch order, actions, horizon, Raster Contract V2, labels, signal thresholds,
and the no-replacement rule are unchanged. There is no automatic Retry 3.
