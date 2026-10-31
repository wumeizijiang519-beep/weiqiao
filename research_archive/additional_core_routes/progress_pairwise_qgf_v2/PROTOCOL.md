# Progress-Pairwise QGF V2

## Purpose

V1 is frozen as `NO_STABLE_PROGRESS_PAIRWISE_CRITIC`. V2 is a new prospective
study, not a rerun: it increases independent physical-group coverage and adds
a locked confirmatory split so architecture development cannot reuse its final
evaluation labels.

## Cohort

- Read only the frozen admitted 288-episode training dataset.
- Exclude every physical group used by Failure-Critical Boundary V1 and
  Progress-Pairwise V1. Validation and formal cohorts remain unread.
- Reuse the V1 boundary eligibility and criticality formula without change.
- Re-rank remaining eligible groups by
  `sha256("progress-pairwise-qgf-v2:" + physical_input_group)`.
- Select eight groups per task family, 32 total. The first four ranked groups
  per family form `development`; the next four form locked `confirmation`.
- No replacement, task switching, seed search, or result-dependent boundary
  change is allowed after registration.

## Candidate And Rollout Contract

Reuse the byte-identical V1 N8 construction, action-support bases, WAM,
normalization, seeds, 32-step horizon, progress formulas, branch receipts,
commit threshold `1e-6`, and official early-stop contract. Every candidate is
executed in an independent fresh environment. The confirmation labels may not
be read by model selection or hyperparameter development.

## Learning Contract

- V1's 14 complete groups plus the 16 V2 development groups may train the V2
  critic. V2 confirmation groups are held out in full.
- The V2 action-aware model must use a preregistered state-conditioned action
  interaction (FiLM/bilinear), not merely repeat V1 with more updates.
- Same-target state-only and within-group action-permutation controls receive
  identical capacity, optimizer, updates, and seeds.
- Three fixed seeds and physical-group-disjoint development OOF are required.
- A single frozen ensemble is evaluated once on the 16 confirmation groups.

## Gates

Collection needs at least 24/32 complete groups and at least 12/16 complete
confirmation groups. Development OOF must pass all V1 critic control gates.
On confirmation, every seed must beat state-only and permutation, and the
physical-group bootstrap lower confidence bounds of both differences must be
greater than zero. Failure freezes V2 without extra groups, seeds, updates,
architectures, or threshold relaxation.

Passing admits a separately preregistered same-compute online QGF validation.
Neither paired progress nor critic accuracy is itself online QGF efficacy.

## Budget

The full 32-group N8 diagnostic is capped at 28,800 allocated GPU seconds,
including failures. Critic development and confirmation are capped at 14,400
allocated GPU seconds. Existing global costs and the 128 GPU-hour cap remain.
