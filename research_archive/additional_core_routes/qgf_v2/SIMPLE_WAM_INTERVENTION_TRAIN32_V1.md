# Simple-WAM Randomized Intervention Train32 V1

## Admission and scope

The frozen four-episode pilot passed with 3 successes and 1 failure plus complete candidate,
transition, and commit audits. This stage collects a bounded training-only randomized
intervention dataset. It is not validation, formal evaluation, or evidence of QGF gain.

## Frozen collection

- Benchmark/task/model/action settings are identical to the pilot: `libero_10` task0,
  native N4 seeds `[10000,11000,12000,13000]`, uniform random selected candidate, at most
  10 executed steps per replan, and labels only for the candidate actually executed.
- 32 episodes in two independent 16-episode shards on separate allocated nodes.
- Shard 0 environment seeds `[202635100,202635116)`, initial-state indices `[5,21)`,
  selection seeds `[202635500,202635516)`.
- Shard 1 environment seeds `[202635200,202635216)`, initial-state indices `[21,37)`,
  selection seeds `[202635600,202635616)`.
- These seeds and initial states are disjoint from engineering, pilot, future validation, and
  formal evaluation. No run is selected, discarded, or stopped according to its outcome.
- Budget: one A800 per shard on separate nodes, 60 minutes per shard, 2 GPU-hours total.

## Data and audit

Every replan saves current/next observations, all candidate chunks and hashes, selected index,
executed action prefix, reward sequence, finite-horizon return, terminal flag, diversity,
latency, and commit error. All attempts and videos are retained.

Collection admission requires all 32 episodes and transitions to pass finite/shape/hash/
diversity/commit audits and at least six successes plus six failures. Failure freezes this
task/configuration without changing seeds or extending the cap.

Only an admitted dataset may enter episode-disjoint out-of-fold training with fixed final-step
reporting and at least three bootstrap seeds. Action-aware must consistently beat same-target
state-only and within-set action permutation/shuffle controls before any online selector test.
