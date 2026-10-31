# Raster Contract V2

Status: active after explicit user approval on 2026-10-27 CST.

This amendment changes one measurement condition only. The dual-camera tensors
returned by the environment and consumed by the policy remain bitwise-exact
admission fields. Complete MuJoCo integration and simulator state,
proprioception, reward, terminal and success values, Python/NumPy/Torch
CPU/CUDA and caller RNG state, and archived actions remain exact; action replay
maximum absolute error remains at most `1e-6`.

An additional direct call to the renderer is retained as diagnostic metadata,
including every mismatch location, but is not an admission field. It is not a
policy input and can advance renderer-internal state independently of the
environment observation returned to the policy.

No model, checkpoint, task, physical group, seed, action, horizon, success
criterion, sample, or budget changes are made. Strict replay V1 and V2 remain
frozen failures and are never relabelled. This contract can admit the fixed
16-group paired-action diagnostic only; it does not establish QGF benefit or
authorize critic retraining, validation, or formal evaluation.
