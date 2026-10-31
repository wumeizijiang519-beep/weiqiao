# Setwise-Contrastive Development Execution V1

- Development data are the prospectively frozen 12 groups only. Locked
  confirmation labels remain unread until the complete model-selection gate.
- Seeds are `202642301`, `202642302`, and `202642303`; folds are the frozen
  family-balanced ranks 0, 1, and 2. Every worker runs exactly 3000 updates.
- Each worker jointly fits the proposed permutation-equivariant N8 set model
  and matched state-only, within-bank action-label permutation, and independent
  candidate/no-set-context controls. All use the same frozen outcome-blind
  action encoder for the corresponding seed.
- The primary metric is physical-group-equal pairwise binary cross-entropy on
  non-tie horizon-32 progress pairs (`abs(delta) > 1e-6`). Improvement is
  control loss minus proposed loss.
- For every seed, proposed pooled OOF loss must be below every control. For
  every control, a 10,000-draw physical-group bootstrap of the pooled
  improvement must have lower 95% bound above zero. Mean cyclic within-bank
  action sensitivity must be at least `1e-3` for every seed.
- Only a complete 9-worker clean result satisfying every gate freezes the
  model, normalizer, support rule, and allows one locked-confirmation read.
  Failure is scientific stop for this configuration; no added seed, update,
  architecture search, or threshold change is allowed.
- Development qualification and any later confirmation metric are critic
  evidence, not online QGF efficacy.
