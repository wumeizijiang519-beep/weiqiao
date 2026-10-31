# Runtime-Anchored QGF V1

## Motivation

Progress-Pairwise V2 cannot reach its preregistered collection gate because
legacy archived policy images are not bitwise reproducible after deterministic
physics replay. This is an availability failure before candidate evaluation,
not evidence about QGF efficacy. This prospective contract removes the legacy
image equality requirement without weakening physical replay or action commit.

## Frozen Population

- Use exactly the 16 `development` groups already selected by the V2 manifest.
  The rule was fixed before V2 candidate outcomes and uses training-only data.
- Do not use V2 confirmation groups, validation, formal data, replacements, or
  result-dependent sampling.
- Pilot is the lowest manifest index among these 16 groups. A clean pilot and
  independent audit automatically release the other 15 groups once.

## Runtime-Anchored Boundary

1. Recreate the frozen task, initial state, 30 dummy actions, and archived
   executed prefix. Reward, terminal, official success, complete MuJoCo state,
   prefix action hashes, proprioception, task identity, and caller seeds remain
   fail-closed and exact.
2. Capture the resulting current runtime observation once. This exact
   deployment-visible observation is the sole input used to generate one
   frozen N8 candidate bank. The legacy archived observation hash is retained
   as metadata, but image equality to that legacy file is not a gate.
3. For every candidate, construct an independent fresh environment and replay
   the same frozen prefix. Before execution, require exact task, prefix, full
   simulator state, proprioception, and deterministic control history. Record
   the branch image hash and whether it matches the source image, but do not
   use branch images for policy inference or candidate selection.
4. Execute the frozen candidate open-loop for at most 32 real environment
   steps. No WAM call, critic, oracle, or replanning occurs inside a branch.
   Commit error must be at most `1e-6`; early stop is allowed only for official
   terminal or success. Save trajectory, reward, success, state, progress,
   video, RNG receipts, and hashes for all eight candidates.

## Candidates And Endpoints

- Candidate bank, native seeds, support PCA, action normalization, structured
  support bounds, branch order, progress metrics, and horizon 16/32 endpoints
  are byte-identical to V1/V2 where applicable.
- Candidate0 native/raw replay must be at most `1e-6`; all eight hashes must be
  unique and finite.
- Official binary success is the primary endpoint. The frozen continuous
  progress range is a training-only auxiliary endpoint and is not an online
  QGF benefit.

## Admission And Stop Rules

- At least 12 of 16 groups must complete all eight real branches.
- Signal requires either at least four binary-discordant groups across two task
  families, or a positive candidate progress range whose 10,000-draw
  physical-group bootstrap lower 95% bound exceeds zero in at least two
  families. Bootstrap seed is `202642201`.
- Failure freezes `NO_RUNTIME_ANCHORED_ACTION_VALUE_SIGNAL`; no replacement,
  added group, horizon, seed, or threshold relaxation is allowed.
- Passing only admits a separately frozen three-seed, group-disjoint critic
  study with state-only and within-bank permutation controls. It is not an
  online QGF efficacy result.

## Budget

- One pilot plus at most 15 remaining groups, one WAM at a time.
- Hard collection cap: 14,400 allocated GPU seconds including failures.
- Infrastructure retries are limited to one minimal repair that leaves every
  scientific byte and threshold unchanged. Scientific failure is not retried.
