# Boundary-Anchored Paired Intervention V1

## Scope and frozen evidence

This is a new prospective diagnostic, not Retry 3. Retry 2 remains frozen as
`NO_IDENTIFIABLE_SIGNAL`: 5/16 groups complete, 11/16 unavailable, and zero
binary-discordant groups. Its failures, thresholds, samples, and costs are not
changed or reinterpreted.

The new design uses the same 16 physical groups, entries, environment seeds,
initial states, 30 dummy waits, and archived 100-action prefixes. There are no
replacement groups. Simple-WAM, its checkpoint, native N4 seeds
`[10000, 11000, 12000, 13000]`, native action representation, and official
success predicate remain frozen.

## Causal contract

At each archived boundary, create one authoritative policy input consisting of
the returned dual-camera observation, proprioception, instruction, and policy
history. Generate the four native candidate chunks exactly once from that input
and save the input, candidate hashes, WAM memory, and RNG receipts. Candidate 0
is always included. Candidate generation is never repeated inside a branch.

Each candidate branch creates a fresh official environment and deterministically
replays the same initial state, dummy waits, and archived prefix. Before action
execution it must exactly match every archived reward, terminal, success, and
MuJoCo state along the prefix and exactly match the bank environment's final
MuJoCo state and proprioception. A branch's newly rendered image is recorded as
audit metadata but is not used to regenerate or modify its candidate. This
isolates action effects without treating EGL renderer repeatability as physical
state equality.

Execute only the candidate's first 10 native actions, open loop. Do not invoke
the WAM again during the branch and do not select using outcomes. All four
candidates are actually executed in separate branches, so each may receive its
own measured labels. Save stepwise actions, official rewards, terminal/success,
MuJoCo states, returned observations, videos, and action commit error. Maximum
commit error must be at most `1e-6`.

## Auxiliary progress endpoint

Official binary success is the primary endpoint. Before execution, also freeze
the task-aligned auxiliary progress endpoint as the fraction of BDDL goal
predicates currently satisfied:

`goal_fraction = satisfied_goal_predicates / total_goal_predicates`.

It is evaluated through the official environment's parsed goal predicates and
is used only as a training label or diagnostic. It is never a policy input,
never available to deployment, and cannot itself establish online QGF benefit.
For each group the paired dense action effect is the range of final
`goal_fraction` across the four actually executed candidates.

## Admission and statistics

At least 12/16 fixed groups must complete all four branches. Binary signal passes
when at least four groups spanning at least two task families have discordant
official success outcomes. Alternatively, auxiliary signal may authorize only
a paired-critic study when at least two families have a predeclared 10,000-draw
physical-group bootstrap 95% lower confidence bound above zero for the family
mean dense action effect. Bootstrap seed is `202641001`; groups, not branches,
are the resampling unit.

If neither gate passes, freeze `NO_PAIRED_ACTION_VALUE_SIGNAL` and do not add
groups, extend prefixes, alter seeds, or train a critic. A pass is not QGF
efficacy; it only authorizes a separately preregistered paired ranking/value
critic with state-only and action-permutation controls.

## Execution staging and budget

Before GPU execution: independently audit Retry 2, run CPU unit tests for goal
fraction, signal aggregation, fixed population, and fail-closed receipts, then
freeze source/configuration hashes and verify an explicitly allocated idle GPU.
Run one bounded low-action pilot on the first frozen group. Only a clean pilot
may dispatch the remaining 15 groups without repeating the pilot. The complete
new branch is capped at 2 GPU hours including failures and retains all previous
costs.
