# QGF v4 Randomized-Intervention Train32 Protocol

Date frozen: 2026-10-24 (Asia/Shanghai)

## Admission and purpose

The four-episode pilot passed its preregistered gate with four audited episodes,
three successes and one failure. Across 274 replans, every selected action exactly
matched the committed chunk, all N=4 proposals were finite and non-degenerate,
and only the uniformly selected executed candidate received observed return.
This protocol authorizes a bounded training-only dataset. It is not online QGF
efficacy evidence.

## Fixed collection

- Backbone/task: frozen UNITAS checkpoint on `open_microwave/demo_randomized`.
- Behavior: uniformly random selection among four same-observation native WAM
  proposals at each replan; execute horizon 10; no oracle or synthetic labels.
- Total: 32 accepted episodes, four independent eight-episode shards.
- Candidate seed windows: `[202622300,202622350)`, `[202622400,202622450)`,
  `[202622500,202622550)`, and `[202622600,202622650)`.
- Selection RNG seeds: `202622601`, `202622602`, `202622603`, `202622604`.
- All feasibility attempts, accepted seeds, outcomes, trajectories, selection
  records, videos, logs, nonzero teardown statuses and failures are retained.
- No result-dependent stopping, seed replacement, window extension or task change.

## Resource budget

The pilot measured approximately 3.62 seconds per replan. A success used about
40-44 replans and the observed failure used 150. At the prior 8/10 outcome-blind
task mix, eight episodes per shard are estimated at about 130 minutes. Four
isolated server/simulator pairs run the four shards in parallel on eight assigned
A800s. Hard cap: 3.5 hours wall per shard and 28 GPU-hours total. Exceeding the
cap freezes partial evidence and does not authorize more collection.

## Dataset and method gate

All 32 episodes must pass transition, candidate-diversity and selected-commit
audits. Dataset preparation requires at least six successes and six failures.
Use an episode-disjoint 24/8 train/validation split fixed before critic training,
with at least four failures in train and two in validation. If the class gate is
not met, stop this task/config rather than adding episodes.

If admitted, compare an action-aware finite-horizon critic, same-target
state-only critic, and action-shuffled control with fixed final-step reporting
and three independent bootstrap seeds. Only stable OOF action evidence over the
state-only and shuffled controls can freeze a selector for fresh matched online
candidate0/random/QGF evaluation.
