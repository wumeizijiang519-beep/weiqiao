# Current-Only Encoder Audit Preparation

Status: CPU harness preparation only. Not GPU admission, feature extraction,
critic fitting, data qualification or method performance evidence.

The full fixed 288-entry dataset must first pass aggregate_training_v2.py and
produce its immutable ADMIT_FOR_RL_QUALIFICATION result. A second loaded WAM
must never coexist with the present collector in the 50GB allocation. Actual
GPU audit dispatch still requires its run/source/config/seed/cost registration,
fresh allocation/PID check, and the preceding data gate. Charge the encoder
audit and any failures to the unchanged feature/critic budget, not free work.

audit_current_features.py selects the first and last training entries in fixed
episode-id order (not by outcomes), reads only observation_0000 and the current
task description, and calls CurrentWamFeatures in A-B-A order at known remaining
horizon700. It does not create an environment, sample an action, generate future
video, attach outcomes to features, or fit any model.

Requirements before any bulk extraction:

- Exact Python/NumPy/Torch CPU/CUDA caller RNG preservation and unchanged input.
- Finite float32 vectors with constant measured dimension and A-repeat maximum
  absolute difference at most1e-6 after intervening observation B.
- Exact registered-buffer byte hashes including scalar/int64/BF16 buffers;
  actor frozen and no actor gradients.
- Record actual latent/context/proprio feature specification, dtype, source/
  checkpoint/stats/observation/result hashes, per-call latency and encoder-phase
  peak CUDA memory. Never assume the latent channel count before this audit.
- Keep audit PASS and process exit status separate. No real GPU audit has been
  run by this CPU preparation. No data admission is inferred from test counts.

The existing FoldScaler remains training-fold-only. Planned action masks depend
only on the known horizon, never the later actual termination length. V2's
official neutral gripper value0 must remain valid; it is canonically mapped to
dataset-space0.5 before affine normalization, not converted into an open/close.
