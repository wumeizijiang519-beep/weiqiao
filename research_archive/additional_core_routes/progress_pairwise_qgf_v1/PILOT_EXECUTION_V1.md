# Progress-Pairwise QGF V1 Pilot Execution

- Scope: frozen cohort entry 0 only (`train_0042`, KITCHEN_SCENE4).
- Candidate bank: four native Simple-WAM chunks generated from the same frozen
  observation with seeds 10000/11000/12000/13000, plus candidate 0 perturbed
  along plus/minus the first two frozen family PCA directions.
- Structured perturbations preserve gripper, use the frozen median support
  norm, and must remain within the frozen p95 support radius and normalized
  action bounds.
- Each of the eight candidates is executed in an independent fresh environment
  after exact dummy and archived-prefix replay. Horizon is 32, with receipts at
  steps 16 and 32; only official terminal or success may stop early.
- Required receipts: exact boundary state/proprio/policy observation, complete
  candidate hashes, RNG snapshots, native/raw candidate-0 replay error at most
  1e-6, action commit error at most 1e-6, full state/action/reward/success
  trajectories, videos, and simulator-only progress labels.
- Pilot hard limit: 1,800 allocated GPU seconds. A scientific gate failure is
  final. One minimal infrastructure retry is allowed only if it preserves this
  exact registration, source, model, sample, seeds, actions, labels, thresholds
  and total 14,400-second diagnostic budget; the failed attempt is retained.
- A clean independent pilot audit releases only the remaining fixed 15-group
  diagnostic. It is not critic or online QGF efficacy evidence.
