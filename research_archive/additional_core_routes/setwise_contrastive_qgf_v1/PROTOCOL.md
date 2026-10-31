# Setwise-Contrastive QGF V1

## Motivation

Runtime-Anchored interventions established real candidate-dependent continuous
progress, but the independent candidate scorer did not beat within-bank action
permutation. This prospective branch tests whether candidate value is
identifiable only relative to the complete native N8 proposal set.

## Frozen cohort

- Read only the admitted 288-episode training cohort.
- Exclude all physical groups used by Failure-Critical Boundary V1,
  Progress-Pairwise V1, and Progress-Pairwise V2 (64 unique groups total).
- Rank remaining eligible groups within each of four task families by
  `sha256("setwise-contrastive-qgf-v1:" + physical_input_group)`.
- Select six groups per family. Family ranks 0-2 form development and 3-5 form
  locked confirmation, for 12+12 groups. No replacement after execution.
- Confirmation outcomes remain sealed until model, normalizer, support rule,
  seeds, updates, and all ablations are frozen from development only.

## Intervention contract

Reuse the audited Runtime-Anchored contract byte-for-byte: one current runtime
boundary observation generates one frozen N8 bank; every candidate executes in
an independent fresh environment for at most 32 real steps. Branch images are
metadata only. Full state, proprioception, prefix, RNG, candidate0 replay and
action commit remain fail-closed. Official terminal/success is the only early
stop. The Simple-WAM actor remains frozen.

## Learning contract

- The action encoder is the frozen outcome-blind masked-prefix encoder.
- The proposed model receives the entire N8 set and scores each candidate from
  state-conditioned, within-bank centered embeddings plus relative set
  attention. Candidate order is randomized with an equivariance audit.
- Matched controls are state-only, within-bank action-label permutation, and an
  independent-candidate model without set context.
- Three fixed seeds and physical-group-disjoint development OOF are required.
  All seeds must beat every control, be action/permutation sensitive, and have
  physical-group bootstrap lower 95% improvement above zero.
- Only then is one locked confirmation evaluation allowed. Every seed must pass
  the same controls on confirmation before any online QGF validation.

## Data gates and budget

- At least 12/12 development and 12/12 confirmation groups must be complete;
  each split must contain non-tie candidate pairs in at least two families.
- One fixed pilot precedes automatic remaining execution. Infrastructure
  repairs must preserve every scientific byte and are bounded; scientific
  failures are not retried.
- Collection cap is 21,600 allocated GPU seconds including failures. This is
  paired diagnostic evidence, not online QGF efficacy.
