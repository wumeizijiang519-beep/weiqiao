# Stage 0 infrastructure retry

The first stage0 attempt, step1593640.307, stopped before model construction,
inference, environment creation or action execution. Saving the entire composed
Hydra config with resolve=True tried to resolve a hydra:runtime output-directory
interpolation, but the standalone compose API has no Hydra job context.

The only repair explicitly sets this run's evaluation output path and preserves
unresolved training-only interpolations in composed_config.yaml. The same official
model constructor resolves the model settings normally. Logging now announces
construction and exact checkpoint accounting. No seed, model, reward, action,
numerical tolerance, guidance parameter, method or scientific gate is changed.

The first attempt's executed source, hashes, process exit and Slurm accounting
remain in runs/qgf_gradient_zero_action_v1. The fresh directory is
runs/qgf_gradient_zero_action_v1_retry1. This is attempt2of2 under the existing
2GPUh aggregate and45minute per-attempt caps. No third attempt is automatic.
