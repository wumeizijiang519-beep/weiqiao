# Failure-Critical Boundary V1 Proposal

## Motivation

The fixed boundary-100 diagnostics produced diverse actions and divergent
physical states but no stable candidate-specific feedback, even with N8 and a
full 32-step native chunk. This proposal changes one factor only: it places
training-only causal interventions immediately before an observed official
success transition. It does not relabel the negative boundary-100 results.

## Prospective population rule

Use only the already frozen and independently audited 288-episode training
cohort. Validation and formal episodes are forbidden. An episode is eligible
only when it is audit-passed, officially successful, has exactly one first
positive-reward transition, and an archived replan boundary exists 16--32
actually executed steps before that first reward. The boundary is the earliest
replan boundary whose inclusive logged distance to first reward is at most 32
steps, maximizing the pre-success intervention span without exceeding one
native chunk.

Within each physical group, retain the lexicographically first eligible episode.
Within each of the four task families, sort retained physical groups by
`sha256("failure-critical-boundary-v1:" + physical_group)` and select the first
four. The resulting 16 groups are frozen before candidate generation. Missing
eligibility is fail-closed; no replacement is allowed after execution starts.
This rule uses historical training success only to locate a training boundary;
it never observes outcomes of the new candidates.

## Frozen intervention

- Reconstruct the official initial state with the archived environment seed,
  30 dummy waits, and the exact archived executed-action prefix.
- Verify every archived prefix action, reward, terminal, success, MuJoCo state,
  boundary proprioception, dual-camera policy input, and RNG receipt.
- From the single archived boundary policy input, generate native N8 using
  seeds `[10000,11000,12000,13000,14000,15000,16000,17000]`.
- Execute every candidate in an independent fresh environment for the full
  32-step open-loop native chunk, stopping early only on official terminal or
  success. Branches make no WAM call and no outcome selects an action.
- Preserve step16/step32 official success, reward, BDDL goal fraction, full
  state, committed actions, video, RNG, and candidate hashes. Commit error must
  be at most `1e-6`.

## Admission and interpretation

At least 12/16 groups must complete. Signal admission requires either at least
four binary-discordant groups spanning at least two families at step16 or
step32, or at least two families whose 10,000-draw physical-group bootstrap
95% lower bound for candidate goal-fraction range is above zero. Bootstrap seed
is `202641401`. A pass authorizes only a separately preregistered paired critic;
it is not online QGF benefit. A failure freezes this boundary design without
adding groups, seeds, horizon, or retries.

## Staging and budget

After CPU cohort audit and explicit scientific approval, run one fixed pilot
group. Only a clean eight-branch pilot may release the other 15 groups. Use one
validated gpu1 WAM at a time. Pilot plus remaining cap is 14,400 GPU seconds,
including failures. No automatic scientific retry. Source, cohort, environment,
assets, budget, and thresholds must be SHA-frozen before the pilot.

