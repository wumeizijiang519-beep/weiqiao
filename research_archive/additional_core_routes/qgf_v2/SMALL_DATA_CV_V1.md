# Result-first Small-data Diagnostic Protocol v1

User2026-10-24 explicitly authorized prioritizing a method conclusion, updating
30minute supervision, and proceeding with the newly proposed small-data CV.
This is a separate protocol, NOT a silent relaxation of stopped standard60.
Original six-failure admission, old data/results and failed runs remain frozen.

## Data and interpretation

Use exact retained60 episodes56S4F, source audit SHA256
bde57dcd15dddfd07d63fe5209a3faded3e8b7f1e63ddb217a84718e33e74483.
CV seed202621500. Four deterministic stratified folds, each45train=42S3F,
15validation=14S1F. Every episode appears in held-out data exactly once per
training seed. Scaling uses fold TRAIN only. No engineering smoke, historical
formal/gate episodes or future online/formal seeds enter the data.

All60 labels/counts were inspected before design; disclose this diagnostic
post-selection. Four independent failures are NOT enough for a strong efficacy
claim or reliable calibration confidence intervals. Three training seeds are
not three independent datasets; never treat chunks or seed repeats as independent
robot episodes. This stage asks whether the current feature/critic setup shows
any action-value signal, NOT whether QGF improves online success.

## Fixed comparisons

Four folds x three seeds0/1/2 x three objectives =36 fixed10000-step runs:
TD099, calibrated1 (gamma1/MCweight.5), calibrated1 state-only. Other training
settings unchanged:width256,batch32,Adam3e-4,expectile.7,targetrate.005,
episode-equal stratified bootstrap. No TD1 expansion or parameter search now.
Explicit --small-data-cv gate validates the new schema/source/fold/counts;
ordinary training still enforces original4/2 failure minima and cannot admit60.

PRIMARY reporting uses the FINAL10000-step checkpoint, no held-out checkpoint
selection/early stopping. Periodic validation and exploratory best files can be
written but MUST NOT select the primary report or a fold/objective for deployment.
Report matched-discount MC MSE and a separately labelled common undiscounted
success target MSE; different discount objectives are NOT equal target scales.
Per-class/episode metrics, state-only comparison, action-shuffle sensitivity,
fold/training-seed variation and compute costs are required. AUC/shuffle deltas
are NOT causal same-state action ranking. Native WAM action normalization and
full10x16 chunk remain intact; no corruption/imagined action failure labels.

## Bounded autonomous execution

First TD099 fold0 seed0 pilot:10000steps,3600second/oneGPU-hour hard cap.
Measure first1000step and final wall time. Conservatively forecast remaining35
runs at1.5x measured pilot time each BEFORE further dispatch. If estimated
remainingGPU-hours exceeds8, STOP_BUDGET_REVIEW. Otherwise use4 independent
assigned GPUs,one worker/GPU,4CPUs each, hard3hour/12GPU-hour parallel-stage cap.
Never duplicate tasks. Each run has3600second cap and refuses overwrite.
Prepare complete fold data before GPU admission, persist manifests/scalers/SHA,
config,metrics,latest/best and COMPLETE/FAILED. No new trajectory collection.

After all36 final results, write summary.json and METHOD_CONCLUSION.md. Describe
whether calibrated action-conditioned critic improves over SAME-TARGET state-only
per fold/seed, whether action dependence is nonzero, how unstable estimates are,
and what cannot be inferred. Null/negative/inconclusive are valid deliverables.
Do not promise a positive result. Do not spend another day accumulating tests.

## Next online decision, not automatic formal admission

Only after artifacts/finite actions/real-checkpoint parity and single-seed safety
checks may a NEW bounded matched10-seed online feasibility protocol be frozen.
Preselect fold0 (not best fold) for any small-data ensemble pilot, seeds0/1/2,
fixed selectorlambda2/minadvantage0/RMS1. No CV threshold tuning. Candidate0N4,
randomN4 and v2 share fresh accepted scene seeds and paired fresh runtimes.
Freeze seed exclusions,methods,budget before launch; record all negative outcomes.
Offline state-only superiority or shuffle sensitivity alone never admits formal
success claims. Only online rescues/regressions decide subsequent independent
formal confirmation. Old legacy service baseline must not be mixed in.
