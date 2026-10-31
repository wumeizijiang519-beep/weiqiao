# Online V1 Scientific Stop

- V1 completed 13 registered scene-arm tasks before stopping.
- Task 006 (scene 1, uniform-random arm) reached a decision where candidate0
  was outside the frozen critic support and the shared shadow scorer raised the
  registered fail-closed error.
- This is a deployment-contract failure, not evidence for or against QGF
  success. The task produced no completion receipt; all partial artifacts and
  Slurm exit code 1 are retained.
- Because the V1 analysis required all 64 scenes and four arms, its confirmatory
  endpoint became unavailable. The remaining V1 lanes were stopped to avoid
  consuming further held-out scenes.
- V2 was registered before touching scenes 4 through 63. It changes only the
  support-abstention contract: baselines do not require critic support, while
  Q-based arms use supported candidates and otherwise fall back to candidate0.
  Support limits, models, seeds, budgets, and statistical thresholds are fixed.
