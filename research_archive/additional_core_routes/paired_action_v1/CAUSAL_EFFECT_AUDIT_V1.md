# Frozen Causal Effect Audit V1

This is a read-only post-stop audit of the 16 fixed boundary-anchored groups.
It does not execute a robot, regenerate a WAM candidate, or alter a label.

For every group it verifies the saved bank and the four committed 10-step
trajectories byte-for-byte at the action boundary, then measures:

- pairwise native action-prefix distance;
- pairwise final MuJoCo-state distance;
- pairwise full state-path distance;
- official return, success, and BDDL goal-fraction variation.

Classification is deterministic with tolerance `1e-6`:

1. `NO_ACTION_DIVERSITY` if any pair of prefixes is not separated;
2. `NO_PHYSICAL_EFFECT` if actions separate but endpoints do not;
3. `PHYSICAL_DIVERGENCE_WITH_FEEDBACK_INSENSITIVITY` if physical states
   separate but all registered feedback endpoints remain equal;
4. `IDENTIFIABLE_FEEDBACK_EFFECT` otherwise.

The audit is descriptive. It cannot authorize critic training or establish
QGF efficacy.
