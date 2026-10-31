# QGF v6 Native Diverse-Bank Protocol

Frozen: 2026-10-24 12:14 CST, after the frozen v5 negative conclusion and
before any v6 model query, rollout, or result inspection.

## Motivation

V4 and v5 both fail action-sensitive controls, while the audited native first-
four proposal deviation is only 0.001126. V6 changes proposal coverage rather
than fitting another critic to the same weak candidate set.

## Candidate Construction

- Query 16 native UNITAS samples from the same current observation, memory and
  replan boundary. Candidate generation still uses the frozen WAM checkpoint;
  no action is perturbed after decoding.
- Preserve native sample 0 as candidate0. Select the remaining three candidates
  by deterministic farthest-point sampling over train-only normalized 10x16
  action chunks. Ties resolve by lower native sample index.
- The deployed set remains N=4. Candidate0, random and QGF controls all pay the
  same N=16 generation plus deterministic subset cost.
- Every action must remain finite and within the official translation/rotation
  converter limits. Candidate commit must regenerate the selected native sample
  exactly, with max error at most 1e-6. Model history advances exactly once.

## Zero-Action Diversity Gate

- Use four fresh training-only initial observations and execute zero policy
  actions. Save all 16 chunks, selected subset indices, source/config SHA and
  latency.
- Compare the diverse subset with native samples [0,1,2,3] on mean pairwise
  normalized L1 distance. The median ratio across observations must be at least
  2.0, every selected set must contain four non-identical finite chunks, and
  candidate0/commit parity must pass. Otherwise freeze a negative result and
  stop this UNITAS configuration.

## Intervention And Critic Gate

- Only after the zero-action gate passes, collect a four-episode randomized
  intervention pilot on open_microwave/demo_randomized using fresh training-only
  seeds. Uniformly choose one of the four diverse-bank candidates and label only
  the executed candidate with its observed finite-horizon return.
- Pilot requires full transition/commit audit and at least one success and one
  failure. A passing pilot admits a separately budgeted 32-episode collection.
- Critic qualification uses collection-shard OOF folds, three fixed bootstrap
  seeds, state-only and within-set selected-index permutation controls, fixed
  final checkpoints and episode-equal metrics. No unexecuted candidate receives
  a target.

## Online Decision

Only stable OOF action evidence admits fresh matched online candidate0, random
and QGF comparison. Report success, Wilson 95% CI, rescue/regression/net,
McNemar, margins, switch rate, uncertainty, latency and GPU hours. No online
improvement stops the configuration. Positive validation is required before
30+ paired formal seeds, a second task and a second executable WAM.
