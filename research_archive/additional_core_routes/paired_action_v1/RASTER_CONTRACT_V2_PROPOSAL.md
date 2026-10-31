# Raster Contract V2 Proposal

Status: proposal only; not approved and not active.

## Evidence motivating the amendment

Fresh-environment replay V2 used one excluded cold-start environment and then
ran measured branches A0, B0, A1, and A2. A1 and A2 reproduced the policy's
returned dual-camera observations, full MuJoCo state, proprioception, rewards,
terminal flags, RNG state, and actions exactly. A2 differed from A0 only in an
additional audit-only direct renderer call at step 4.

The extra direct renderer call is not consumed by the policy and can mutate or
observe renderer-internal state independently of the environment observation
returned to the policy. Requiring it to be bitwise identical is therefore a
renderer diagnostic, not a counterfactual-policy validity condition.

## Proposed preregistered contract

Keep exact, bitwise equality for:

- the dual-camera tensors actually returned to and consumed by the policy;
- complete MuJoCo integration and simulator state;
- proprioception, reward, terminal, and success values;
- Python, NumPy, Torch CPU/CUDA, simulator, selection, and caller RNG state;
- archived/replayed actions with maximum absolute error at most 1e-6.

Record direct-render images and their mismatch locations as audit metadata, but
do not use audit-only direct-render equality as an admission criterion.

No model, action, task, seed, success criterion, sample, or budget changes are
proposed. The old strict V1/V2 failures remain failures and are not relabeled.

## Consequence

If explicitly approved, this contract permits the already fixed 16-group
paired-action diagnostic to proceed. It does not establish QGF benefit and does
not authorize critic retraining, validation, or formal evaluation.
