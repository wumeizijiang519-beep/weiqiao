# Action-Conditioned Dynamics Auxiliary V1

## Purpose

Use otherwise idle EGL-incompatible GPUs to test whether the frozen training
features contain an execution-aligned action-effect signal. This is an
auxiliary representation diagnostic, not a QGF result and not a replacement
for the preregistered Causal Signal V2 gate.

## Frozen data and split

- Read only the independently audited 288-episode training corpus.
- Never read Causal Signal V2, validation, or formal results.
- Use the existing physical-group-disjoint folds 0, 1, and 2.
- Run seeds 202641201, 202641202, and 202641203 for all three held folds.
- Each worker trains for exactly 5,000 updates with batch size 256.

## Models and targets

The target is the measured next-observation feature delta. Training-fold-only
normalization is followed by a fixed 128-dimensional signed random projection.
The current observation uses a separate fixed 256-dimensional signed random
projection. All projections are generated from the worker seed and saved.

Each worker jointly trains equal-capacity MLPs:

1. `action`: current state plus the actually executed ten-step action prefix.
2. `state_only`: the same current state with all action inputs zeroed.
3. `within_bank`: the same state with a fixed non-selected candidate from the
   archived same-observation bank. This candidate has no outcome label.

No model receives future execution length, reward, terminal, success, Causal
Signal V2 labels, validation data, or formal data. The planned-prefix mask is
known at decision time and is shared by action-bearing models.

## Frozen evaluation

Report episode-equal and physical-group-equal held-fold MSE. Also evaluate the
trained action model after replacing its true action with the within-bank
control action. A seed passes only after its three held folds cover every
nonempty episode exactly once and all of the following hold on pooled
episode-equal metrics:

- action MSE is lower than state-only MSE;
- action MSE is lower than within-bank-control MSE;
- replacing the true action increases the action model's MSE;
- 10,000-draw physical-group bootstrap 95% lower bounds for both control
  improvements and permutation sensitivity are greater than zero.

The auxiliary gate passes only if all three seeds pass. Failure is retained as
a negative representation diagnostic; do not add seeds, updates, or selected
tasks. Passing may justify using the frozen action encoder as an initializer in
a separately preregistered paired critic only if Causal Signal V2 independently
admits critic research.

## Budget and ownership

- Use only job 1598338 on gpu22, whose two A800 UUIDs are explicitly checked.
- At most two workers run concurrently; each has a 900-second hard limit.
- Total cap is 8,100 GPU seconds including failures.
- No robot environment, EGL, WAM inference, or policy action is run.

