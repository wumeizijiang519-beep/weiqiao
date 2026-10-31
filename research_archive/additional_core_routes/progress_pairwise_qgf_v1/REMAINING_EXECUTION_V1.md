# Progress-Pairwise QGF V1 Remaining Execution

- Scope is exactly frozen manifest entries 1 through 15. Entry 0 pilot is not
  repeated. Each entry has an immutable authorization receipt derived only
  from its archived config and transition hashes.
- The single-group runner differs from the audited pilot runner only by making
  the frozen entry index an authorization field. Candidate generation,
  support constraints, environment replay, horizon, labels and thresholds are
  unchanged.
- Groups run sequentially with at most one WAM loaded on gpu1 GPU0. Process
  restarts between groups are engineering isolation, not new scientific seeds.
- Remaining hard allocation is 13,620 seconds; pilot plus remaining cap remains
  14,400 allocated GPU seconds including failures. Completed groups are never
  rerun. One bounded minimal infrastructure repair may resume only unfinished
  entries under byte-identical scientific contracts and the same total cap.
- After clean completion, an independent finalizer must combine entry0 plus
  entries1--15 exactly once and recompute all admission statistics. No critic
  or online result is authorized by execution alone.
