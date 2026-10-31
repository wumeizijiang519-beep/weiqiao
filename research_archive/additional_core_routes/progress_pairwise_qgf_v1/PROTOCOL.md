# Progress-Pairwise QGF V1

## Scope

This is a new prospective training-only diagnostic. It does not overwrite the
frozen negative results from the 288-episode IQL study, Causal Signal V2, or
Failure-Critical Boundary V1. It tests whether stronger but support-constrained
action alternatives at decision-critical boundaries produce measurable
continuous task progress before any new critic is trained.

## Frozen population

- Read only the independently admitted 288-episode training dataset with
  `DATASET_RESULT` SHA
  `baa8340ecbe48ce0240e6e46056ed4e00309ba42e998657cda53ca7ec8666b87`.
- Validation and formal episodes are forbidden.
- Exclude every physical group used by Failure-Critical Boundary V1.
- An episode must be audit-passed and officially successful, and must have an
  archived replan boundary 24--64 executed steps before first positive reward.
- At each eligible boundary, compute a criticality score from information that
  is already available at that boundary: the L2 change between the two most
  recent executed arm-action prefixes plus a binary gripper-transition bonus.
  The boundary with the largest score is retained; ties use the earlier replan.
- Keep one episode per physical group. Hash-rank groups independently within
  each of the four frozen task families and select four per family. There is no
  replacement after execution starts.

## Support-constrained alternatives

For every training transition, use the three archived normalized candidate
deltas relative to candidate 0. Exclude gripper from PCA and fit an SVD basis
separately for each task family over flattened 32-step, 6-DoF arm deltas.
Freeze the top three directions, singular values, empirical delta-norm
quantiles, source transition hashes, and basis hashes before a GPU run.

At a boundary, call the frozen WAM once for native candidate 0. Construct a
fixed N8 bank in normalized action space:

1. native candidate 0;
2. native candidates 1--3 from the same frozen WAM call;
3. candidate 0 plus/minus the first two family PCA directions, scaled to the
   frozen median native-delta norm.

The structured candidates preserve candidate-0 gripper exactly, are clipped
only to the official normalized action bounds, and must stay below the frozen
95th-percentile support norm. All eight candidates must be unique. No candidate
outcome may change the bank.

## Progress contract

Before intervention execution, a separate runtime-inventory gate must freeze
the exact MuJoCo bodies, sites, joints, and BDDL predicates used by each task
family. Continuous progress is computed from simulator state only after branch
execution and is never a critic input. It must be monotonic in task completion
and normalized using constants frozen by the inventory gate. The intended
components are object-to-target distance and the required articulated-state or
second-object completion term. Missing or ambiguous simulator names fail
closed.

## Execution and admission

- First run one environment-only inventory gate with zero WAM calls and zero
  robot actions.
- After inventory audit, run one fixed pilot group. Every N8 candidate executes
  in an independent fresh environment for 32 open-loop steps, with step16 and
  step32 receipts. Early stop is allowed only on official success or terminal.
- Commit error must be at most `1e-6`; all state, action, RNG, observation,
  feedback, and video receipts are mandatory.
- Only a clean pilot may release the remaining 15 frozen groups.
- Full diagnostic admission needs at least 12/16 complete groups and either
  four official-success discordant groups across two families or a positive
  physical-group bootstrap lower confidence bound for continuous candidate
  range in at least two families.

A pass authorizes a separately preregistered three-seed, physical-group-
disjoint pairwise critic with state-only and action-permutation controls. It is
not online QGF benefit. A failure freezes this branch without extra groups,
seeds, horizons, or relaxed thresholds.

## Budget and stopping

The CPU build and inventory do not train a model. The inventory gate is capped
at 300 GPU seconds. Pilot plus remaining intervention is capped at 14,400 GPU
seconds including failures. No automatic GPU retry is permitted. The existing
128 GPU-hour global cap and all prior failed costs remain in force.
