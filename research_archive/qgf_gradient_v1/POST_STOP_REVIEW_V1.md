# Post-stop review and next-decision brief

## Frozen observations

The288-episode training cohort and12218transitions passed independent data and
feature audits. Random native-bank collection yielded188successes/100failures.
All nine registered seed/fold fits reached20000updates. No seed's action model
beat both same-target controls; action permutation sensitivity was unstable.
The physical-group confidence interval gates failed. The frozen result is
NO_STABLE_EXECUTION_ALIGNED_ACTION_VALUE_EVIDENCE, SHA256
6983ac676414cbc18ea3d4ac27b9368ab99d18e2b28bbb8ecf078343086f4200.

This is an offline critic qualification failure, not an online QGF failure.
No validation/formal QGF deployment was executed. Dataset integrity does not
establish critic quality or the causal effect of changing an action.

## What the present evidence cannot distinguish

1. Native candidates may be numerically different but outcome-equivalent.
2. Sparse terminal feedback may supply little within-state action information.
3. Current representations or TD estimation may hide useful action differences.
4. State features may predict episode outcome without identifying a better action.

These are hypotheses, not measured causes. More updates, seeds, or a different
backbone would not by themselves resolve these ambiguities.

## Recommended next scientific decision (not authorized or launched)

Keep the frozen WAM and QGF objective, but first test whether its native action
support contains a learnable causal signal. Propose a new, separately registered,
training-only paired-intervention diagnostic on fixed physical states. Execute
alternative native prefixes from validated identical simulator/controller/RNG
snapshots, measure only actual rollouts, and assess paired return dispersion
with physical-group inference and explicit cost/stop rules. No use of these
labels, expert feasibility, or simulator branches at deployment.

This changes the data design and requires explicit user approval. Exact full
simulator/controller restoration is a prerequisite; the previous recovery of
original sensor snapshots is not sufficient proof of counterfactual equivalence.
Do not reuse old validation/formal scenes or cherry-pick states for large effects.

If paired outcomes do not differ reliably, stop action-value guidance on this
native support rather than force a critic. If they do, preregister a new critic
study contrasting MC and semi-MDP TD targets, current action encoding, and
state-only/permuted controls under group-disjoint evaluation. All choices and
budgets must be fixed before seeing new outcomes. Only a qualified critic may
lead to matched-compute online QGF comparisons. Positive results are not assured.

## Immediate authorized work

Evidence preservation and CPU-only review only. D-drive source/corpus/nine-fit
export completed and59listed files rehashed without mismatches. This is not
a claim that all upstream assets are saved. Raw archive343 remains pending;
no third automatic archive attempt and no new GPU scientific work.
