# Progress-Pairwise Critic V1 Execution

The user explicitly authorized direct training on 2026-10-28. This execution
does not require per-worker approval. Minimal infrastructure repair is allowed
only when corpus, splits, seeds, model definitions, update count, metrics and
thresholds remain byte-identical and all failed GPU cost is retained.

The immutable corpus contains 14 physical groups and 112 real branches. Its
SHA is `20bf3b471dec931d4f7fe3787ecb446fee730da67b135c9911885568c460b290`.
The corrected independent audit has SHA
`3ecf593b87915daa1adbb780eb7c1273e6309769b15490e4dcfe48a55ae70c6a`.
Both earlier auditor outputs remain preserved: the first exposed a row/matrix
comparison bug, and the second exposed a shadowed expected-inventory variable.
Neither changed corpus bytes or scientific settings.

Exactly twelve workers are authorized: three frozen seeds by four frozen
physical-group-disjoint folds. Each worker trains matched action-aware,
state-only and within-group permutation models for exactly 3,000 updates with
batch size 64, Adam learning rate 3e-4 and width 128. There is no
performance-based early stopping. Each worker has a 900 GPU-second hard limit;
the aggregate hard ceiling is 10,800 GPU seconds including failures.

After all workers finish cleanly, the independent qualifier pools out-of-fold
predictions. Every seed must beat both controls and reach at least 90% action
sensitivity. Physical-group bootstrap lower bounds for action-aware minus each
control must exceed zero using seed 202641701 and 10,000 draws. Failure freezes
`NO_STABLE_PROGRESS_PAIRWISE_CRITIC`; no additional seeds, updates, folds,
groups or thresholds are permitted. Passing admits a separately frozen online
same-compute validation and is not itself online QGF efficacy.
